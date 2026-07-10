from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any


def _norm(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _contains(text: str, pattern: str) -> bool:
    normalized = _norm(text)
    alternatives = [_norm(part.strip()) for part in pattern.split("|")]
    return any(alt and alt in normalized for alt in alternatives)


def _first_index(text: str, pattern: str) -> int:
    normalized = _norm(text)
    indexes = [
        normalized.find(_norm(part.strip()))
        for part in pattern.split("|")
        if part.strip()
    ]
    indexes = [idx for idx in indexes if idx >= 0]
    return min(indexes) if indexes else -1


def _text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if isinstance(item, dict):
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                parts.append(item["text"])
            elif isinstance(item.get("content"), str):
                parts.append(item["content"])
    return "\n".join(parts)


def _read_path_from_tool_use(item: dict[str, Any]) -> Path | None:
    name = item.get("name") or item.get("tool_name")
    if name != "Read":
        return None
    tool_input = item.get("input") or item.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return None
    path = tool_input.get("file_path") or tool_input.get("path")
    return Path(path) if isinstance(path, str) and path else None


def _iter_jsonl(transcript: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in transcript.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            events.append(obj)
    return events


def extract_answer_and_files(transcript: Path) -> tuple[str, list[Path]]:
    """Return final answer text and paths proven by file-read tool events."""

    events = _iter_jsonl(transcript)
    assistant_turns: list[str] = []
    files: list[Path] = []

    for obj in events:
        if obj.get("type") == "assistant_turn" and isinstance(obj.get("text"), str):
            assistant_turns.append(obj["text"])
        if obj.get("type") == "file_read" and isinstance(obj.get("path"), str):
            files.append(Path(obj["path"]))

        if obj.get("type") == "assistant":
            message = obj.get("message") if isinstance(obj.get("message"), dict) else obj
            text = _text_from_content(message.get("content"))
            if text:
                assistant_turns.append(text)
            for item in message.get("content", []) if isinstance(message.get("content"), list) else []:
                if isinstance(item, dict):
                    path = _read_path_from_tool_use(item)
                    if path is not None:
                        files.append(path)

        if obj.get("type") in {"tool_use", "tool_call"}:
            path = _read_path_from_tool_use(obj)
            if path is not None:
                files.append(path)

    unique_files: list[Path] = []
    seen: set[str] = set()
    for file in files:
        key = str(file)
        if key not in seen:
            seen.add(key)
            unique_files.append(file)
    return (assistant_turns[-1] if assistant_turns else "", unique_files)


def necessary_file_recall(files: list[Path], required_concepts: list[str]) -> float:
    """Fraction of required concepts found in the concatenated opened-file text."""

    texts: list[str] = []
    for file in files:
        try:
            if file.exists() and file.is_file():
                texts.append(file.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    corpus = _norm("\n".join(texts))
    if not required_concepts:
        return 1.0
    hits = sum(1 for concept in required_concepts if _contains(corpus, concept))
    return hits / len(required_concepts)


def foundational_start_pass(answer: str, invariants: list[str], ordered: dict | None) -> bool:
    """Check required foundational concepts and any required before/after order."""

    if not all(_contains(answer, invariant) for invariant in invariants):
        return False
    if ordered:
        before = _first_index(answer, str(ordered.get("before", "")))
        after = _first_index(answer, str(ordered.get("after", "")))
        if before < 0 or after < 0 or before > after:
            return False
    return True


def _assistant_turns(transcript: Path) -> list[str]:
    turns: list[str] = []
    for obj in _iter_jsonl(transcript):
        if obj.get("type") == "assistant_turn" and isinstance(obj.get("text"), str):
            turns.append(obj["text"])
        elif obj.get("type") == "assistant":
            message = obj.get("message") if isinstance(obj.get("message"), dict) else obj
            text = _text_from_content(message.get("content"))
            if text:
                turns.append(text)
    return turns


def correction_count(assistant_turns: list[str], case: dict) -> int | None:
    """Return index of first passing turn (0, 1, or 2), or None if no turn passes."""

    invariants = case.get("foundational_invariants", [])
    ordered = case.get("ordered_invariant")
    for index, turn in enumerate(assistant_turns[:3]):
        if foundational_start_pass(turn, invariants, ordered):
            return index
    return None


def score_run(transcript: Path, case_path: Path) -> dict:
    """Return condition-neutral scores and evidence."""

    case = json.loads(case_path.read_text(encoding="utf-8"))
    answer, files = extract_answer_and_files(transcript)
    turns = _assistant_turns(transcript)
    count = correction_count(turns, case)
    return {
        "transcript": str(transcript),
        "case": case["id"],
        "necessary_file_recall": necessary_file_recall(files, case["required_concepts"]),
        "foundational_start_pass": foundational_start_pass(
            answer,
            case.get("foundational_invariants", []),
            case.get("ordered_invariant"),
        ),
        "correction_count": count,
        "files_read": [str(file) for file in files],
        "assistant_turn_count": len(turns),
        "evidence_excerpt": re.sub(r"\s+", " ", answer).strip()[:500],
    }
