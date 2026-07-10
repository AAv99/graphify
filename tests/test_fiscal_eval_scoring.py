import importlib.util
from pathlib import Path


_SCORE_PATH = Path(__file__).resolve().parents[1] / "evals" / "fiscal-law" / "score.py"
_SPEC = importlib.util.spec_from_file_location("fiscal_eval_score", _SCORE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
score = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(score)

extract_answer_and_files = score.extract_answer_and_files
foundational_start_pass = score.foundational_start_pass
necessary_file_recall = score.necessary_file_recall


def test_civielrechtelijk_must_precede_onzakelijke_lening():
    answer = "Eerst civielrechtelijk kwalificeren; daarna komt de onzakelijke lening."
    assert foundational_start_pass(
        answer,
        ["civielrechtelijk"],
        {"before": "civielrechtelijk", "after": "onzakelijke lening"},
    )


def test_footer_without_read_event_does_not_count_as_opened(tmp_path):
    transcript = tmp_path / "run.jsonl"
    transcript.write_text(
        '{"type":"final","text":"Antwoord\\nFILES_READ:\\n- /tmp/fake.md"}\n',
        encoding="utf-8",
    )
    _, files = extract_answer_and_files(transcript)
    assert files == []


def test_required_concept_must_exist_in_opened_file_text(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("Alleen staking wordt hier behandeld.", encoding="utf-8")
    assert necessary_file_recall(
        [source], ["staking", "herinvesteringsvoornemen"]
    ) == 0.5


def test_hir_requires_both_intent_and_staking_in_answer():
    assert not foundational_start_pass(
        "De staking is relevant voor de HIR.",
        ["herinvesteringsvoornemen", "staking"],
        None,
    )
