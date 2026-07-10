from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from score import correction_count, foundational_start_pass, score_run


ROOT = Path(__file__).resolve().parents[2]
EVAL_ROOT = ROOT / "evals" / "fiscal-law"
CASES = EVAL_ROOT / "cases"

HIR_CORPUS_ROOT = Path("/Users/adnanavdic/Documents/Projects")
HIR_GRAPH = Path("/Users/adnanavdic/Library/Mobile Documents/com~apple~CloudDocs/Graph giw .json")
VPB_CORPUS_ROOT = Path("/Users/adnanavdic/Documents/Kennisapparaat-fiscaal")
VPB_GRAPH = Path("/Users/adnanavdic/Documents/Kennisapparaat-fiscaal/graphify-out/graph.json")

REPAIR_PROMPTS = [
    "Je lijkt mogelijk te laat in de analyse in te stappen. Controleer of er een eerder liggende kwalificatie- of grondvraag is, lees de daarvoor relevante bestanden en herstel je analyse.",
    "Lees de fundamentele bronbestanden uit de gevonden omgeving opnieuw en bouw de analyse opnieuw op vanaf de eerste juridisch relevante vraag.",
]


def _case_context(case: dict[str, Any]) -> tuple[Path, Path]:
    if case["id"] == "hir-staking":
        return HIR_CORPUS_ROOT, HIR_GRAPH
    if case["id"] == "onzakelijke-lening":
        return VPB_CORPUS_ROOT, VPB_GRAPH
    raise ValueError(f"unknown case id: {case['id']}")


def _prompt(case: dict[str, Any], condition: str) -> str:
    corpus_root, graph_path = _case_context(case)
    verification = (
        "\n\nUse the Read tool for every source file you open. Do not use shell "
        "commands such as cat, sed, or python to read source-file contents, because "
        "the transcript must prove file reads through Read tool events."
    )
    if condition == "no-graph":
        return f"""You have access to {corpus_root}. Work with the user on this task:
{case['task']}
Find and read whatever files you need. Do not use graphify, graph.json,
GRAPH_REPORT.md, or any graph-derived artifact. Return the answer followed by
a machine-readable footer:
FILES_READ:
{verification}
"""
    if condition == "graph-locator":
        return f"""You have access to {corpus_root} and {graph_path}.
Work with the user on this task:
{case['task']}
1. Run graphify query on the user's exact task.
2. Collect the unique source_file paths returned by the nearest subgraph.
3. Resolve those paths against the corpus root and actually open the relevant files.
4. Treat node labels and edges only as navigation. Derive every substantive fiscal statement from files you opened.
5. If the first neighborhood is insufficient, expand the graph query once or use ordinary file search after graph orientation.
6. Return the answer followed by a machine-readable footer listing only files actually opened:
FILES_READ:
{verification}
"""
    raise ValueError(f"unknown condition: {condition}")


def _extract_turn(raw_events: list[dict[str, Any]]) -> tuple[str, list[str]]:
    texts: list[str] = []
    reads: list[str] = []
    for event in raw_events:
        if event.get("type") != "assistant":
            continue
        message = event.get("message") if isinstance(event.get("message"), dict) else event
        content = message.get("content", [])
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                texts.append(item["text"])
            if item.get("type") == "tool_use" and item.get("name") == "Read":
                tool_input = item.get("input")
                if isinstance(tool_input, dict) and isinstance(tool_input.get("file_path"), str):
                    reads.append(tool_input["file_path"])
    return "\n".join(texts).strip(), reads


def _run_claude_turn(prompt: str, transcript: Path, *, session_id: str, resume: bool, turn_index: int) -> tuple[str, list[str]]:
    cmd = [
        "claude",
        "--print",
        "--output-format",
        "stream-json",
        "--verbose",
        "--include-hook-events",
        "--permission-mode",
        "bypassPermissions",
        "--allowedTools",
        "Read,LS,Glob,Grep,Bash",
        "--add-dir",
        str(HIR_CORPUS_ROOT),
        "--add-dir",
        str(VPB_CORPUS_ROOT),
    ]
    if resume:
        cmd.extend(["--resume", session_id])
    else:
        cmd.extend(["--session-id", session_id])
    cmd.append(prompt)

    env = os.environ.copy()
    env["PATH"] = f"{ROOT / '.venv' / 'bin'}:{env.get('PATH', '')}"
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=900,
    )
    raw_events: list[dict[str, Any]] = []
    with transcript.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "user_turn", "turn_index": turn_index, "text": prompt}, ensure_ascii=False) + "\n")
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                event = {"type": "raw_stdout", "text": line}
            raw_events.append(event)
            fh.write(json.dumps({"type": "raw_event", "turn_index": turn_index, "event": event}, ensure_ascii=False) + "\n")
        if proc.stderr:
            fh.write(json.dumps({"type": "stderr", "turn_index": turn_index, "text": proc.stderr}, ensure_ascii=False) + "\n")
        fh.write(json.dumps({"type": "process_exit", "turn_index": turn_index, "returncode": proc.returncode}, ensure_ascii=False) + "\n")
    if proc.returncode != 0:
        raise RuntimeError(f"claude turn failed with {proc.returncode}: {proc.stderr[-1000:]}")

    text, reads = _extract_turn(raw_events)
    with transcript.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "assistant_turn", "turn_index": turn_index, "text": text}, ensure_ascii=False) + "\n")
        for path in reads:
            fh.write(json.dumps({"type": "file_read", "turn_index": turn_index, "path": path}, ensure_ascii=False) + "\n")
    return text, reads


def run_one(case_path: Path, condition: str, index: int, out_root: Path) -> Path:
    case = json.loads(case_path.read_text(encoding="utf-8"))
    out_dir = out_root / case["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    transcript = out_dir / f"{condition}-{index}.jsonl"
    if transcript.exists() and '"type": "run_summary"' in transcript.read_text(encoding="utf-8", errors="ignore"):
        return transcript
    transcript.unlink(missing_ok=True)
    session_id = str(uuid.uuid4())

    turns: list[str] = []
    prompt = _prompt(case, condition)
    for turn_index in range(3):
        answer, _reads = _run_claude_turn(
            prompt if turn_index == 0 else REPAIR_PROMPTS[turn_index - 1],
            transcript,
            session_id=session_id,
            resume=turn_index > 0,
            turn_index=turn_index,
        )
        turns.append(answer)
        if foundational_start_pass(
            answer,
            case.get("foundational_invariants", []),
            case.get("ordered_invariant"),
        ):
            break
    with transcript.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "run_summary", "correction_count": correction_count(turns, case)}, ensure_ascii=False) + "\n")
    return transcript


def _write_report(result_root: Path, report_path: Path) -> None:
    rows: list[dict[str, Any]] = []
    for case_path in sorted(CASES.glob("*.json")):
        for transcript in sorted((result_root / json.loads(case_path.read_text(encoding="utf-8"))["id"]).glob("*.jsonl")):
            score = score_run(transcript, case_path)
            score["condition"] = transcript.stem.rsplit("-", 1)[0]
            score["run"] = transcript.stem.rsplit("-", 1)[1]
            rows.append(score)

    def median(values: list[float]) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        mid = len(ordered) // 2
        if len(ordered) % 2:
            return ordered[mid]
        return (ordered[mid - 1] + ordered[mid]) / 2

    lines = ["# Pre-change Fiscal-law A/B Report", ""]
    lines.append("| case | condition | run | necessary_file_recall | foundational_start_pass | correction_count | files_read | evidence |")
    lines.append("|---|---|---:|---:|---|---:|---|---|")
    for row in rows:
        count = "failure" if row["correction_count"] is None else str(row["correction_count"])
        files = "<br>".join(row["files_read"]) if row["files_read"] else "(none)"
        lines.append(
            f"| {row['case']} | {row['condition']} | {row['run']} | "
            f"{row['necessary_file_recall']:.2f} | {row['foundational_start_pass']} | "
            f"{count} | {files} | {row['evidence_excerpt']} |"
        )

    lines.extend(["", "## Medians", ""])
    lines.append("| case | condition | median necessary_file_recall | pass rate | median correction_count |")
    lines.append("|---|---|---:|---:|---:|")
    for case in sorted({row["case"] for row in rows}):
        for condition in sorted({row["condition"] for row in rows if row["case"] == case}):
            subset = [row for row in rows if row["case"] == case and row["condition"] == condition]
            recalls = [float(row["necessary_file_recall"]) for row in subset]
            passes = [bool(row["foundational_start_pass"]) for row in subset]
            counts = [row["correction_count"] for row in subset if row["correction_count"] is not None]
            lines.append(
                f"| {case} | {condition} | {median(recalls):.2f} | "
                f"{sum(passes)}/{len(passes)} | "
                f"{median([float(c) for c in counts]):.1f} |"
            )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", default="pre-change", choices=["pre-change", "post-change"])
    parser.add_argument("--condition", choices=["no-graph", "graph-locator"])
    parser.add_argument("--case", choices=["hir-staking", "onzakelijke-lening"])
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args(argv)

    result_root = EVAL_ROOT / "results" / args.phase
    result_root.mkdir(parents=True, exist_ok=True)
    if not args.report_only:
        case_paths = sorted(CASES.glob("*.json"))
        if args.case:
            case_paths = [CASES / f"{args.case}.json"]
        conditions = [args.condition] if args.condition else ["no-graph", "graph-locator"]
        for case_path in case_paths:
            for condition in conditions:
                for index in range(1, args.repetitions + 1):
                    run_one(case_path, condition, index, result_root)
    report = EVAL_ROOT / "results" / ("PRE_CHANGE_REPORT.md" if args.phase == "pre-change" else "FINAL_REPORT.md")
    _write_report(result_root, report)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
