"""Remediation rerun (Task 2 Step 8): rerun HIR Condition B against the
bridge-enriched graph, reusing the exact run.py agent harness and scorer.

Only the HIR graph path changes (to the rebuilt, bridge-inclusive graph);
prompts, model, repair prompts, and scoring are identical to the pre-change run.
"""
from __future__ import annotations

import sys
from pathlib import Path

import run  # reuse the real claude-cli agent harness + scorer

EVAL_ROOT = Path(__file__).resolve().parent
CASES = EVAL_ROOT / "cases"


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: rerun_bridge.py <path-to-bridge-graph.json> [repetitions]")
        return 2
    bridge_graph = Path(argv[1])
    reps = int(argv[2]) if len(argv) > 2 else 3
    if not bridge_graph.exists():
        print(f"graph not found: {bridge_graph}")
        return 2

    # Point ONLY the HIR graph at the bridge-enriched rebuild. Everything else
    # (corpus root, prompts, model, scorer) is unchanged from run.py.
    run.HIR_GRAPH = bridge_graph

    out_root = EVAL_ROOT / "results" / "post-bridge"
    out_root.mkdir(parents=True, exist_ok=True)
    case_path = CASES / "hir-staking.json"
    for index in range(1, reps + 1):
        tr = run.run_one(case_path, "graph-locator", index, out_root)
        print(f"wrote {tr}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
