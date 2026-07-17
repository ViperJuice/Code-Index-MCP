"""INFERGATE verdict-report contract tests (IF-0-INFERGATE-1).

These assert the rollout report exists, records a valid verdict, binds the
frozen dataset/corpus/thresholds checksums exactly as MANIFEST.json records
them, records the code commit, states the holdout was not used for tuning, and
that SUPPORT_MATRIX keeps semantic/reranked as experimental / opt-in (learned
reranking not default-enabled).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
REPORT = REPO / "docs" / "status" / "INFERENCE_ROLLOUT.md"
MANIFEST = REPO / "benchmarks" / "retrieval_eval" / "MANIFEST.json"
SUPPORT_MATRIX = REPO / "docs" / "SUPPORT_MATRIX.md"

ALLOWED_VERDICTS = {"ready", "dark_opt_in", "rejected"}


@pytest.fixture(scope="module")
def report_text() -> str:
    assert REPORT.is_file(), f"missing rollout report: {REPORT}"
    return REPORT.read_text()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def test_report_exists_and_has_allowed_verdict(report_text: str) -> None:
    m = re.search(r"verdict:\s*(\w+)", report_text)
    assert m, "report must contain a machine-parseable 'verdict: <enum>' line"
    assert m.group(1) in ALLOWED_VERDICTS, (
        f"verdict {m.group(1)!r} not in allowed enum {ALLOWED_VERDICTS}"
    )


def test_report_binds_frozen_checksums(report_text: str, manifest: dict) -> None:
    for key in ("dataset_sha256", "corpus_sha256", "thresholds_sha256"):
        recorded = manifest[key]
        assert isinstance(recorded, str) and recorded
        assert recorded in report_text, (
            f"report must bind {key} == MANIFEST value {recorded}"
        )


def test_report_records_code_commit(report_text: str) -> None:
    # The report records the point-in-time run commit as a static 40-hex hash.
    # We assert it records *a* code commit rather than equality with live HEAD,
    # so the test survives being committed (HEAD moves; the recorded run commit
    # does not).
    m = re.search(r"code commit[^\n]*?\b([0-9a-f]{40})\b", report_text, re.I)
    assert m, "report must record a 40-char code commit hash"


def test_report_states_holdout_not_used_for_tuning(report_text: str) -> None:
    low = report_text.lower()
    assert "holdout" in low
    assert re.search(r"holdout[^\n]*not\s+(be\s+)?used", low) or (
        "not used for tuning" in low
    ), "report must explicitly state the holdout was NOT used for tuning"


def test_report_documents_collection_resident_provenance_precondition(report_text: str) -> None:
    """A live provider run's numbers count ONLY after the collection-resident
    provenance binding verifies against the frozen corpus (IF-0-INFERLIVEGATE-1).
    The report must document that precondition, the manifest schema, and the
    distinct not_run reason codes."""
    low = report_text.lower()
    assert "collection-resident provenance" in low, (
        "report must document the collection-resident provenance precondition"
    )
    assert "collection-provenance.v1" in report_text, (
        "report must cite the collection-provenance.v1 manifest schema"
    )
    # The four distinct not_run reason codes must be documented.
    for code in (
        "provenance_missing",
        "provenance_stale",
        "provenance_mixed_run",
        "provenance_tampered",
    ):
        assert code in report_text, f"report must document reason code {code!r}"
    # The verdict must stay dark_opt_in absent a passing, provenance-bound run.
    m = re.search(r"verdict:\s*(\w+)", report_text)
    assert m and m.group(1) == "dark_opt_in", "verdict must stay dark_opt_in here"


def test_report_documents_operator_run_procedure(report_text: str) -> None:
    """The report must land the operator run procedure for a live provider run."""
    low = report_text.lower()
    assert "operator run procedure" in low, "report must include an operator run procedure"
    assert "expected_point_set_id" in report_text.lower(), (
        "run procedure must document the EXPECTED_POINT_SET_ID expectation"
    )
    assert "run_inference_gate.py" in report_text


def test_support_matrix_keeps_semantic_and_rerank_experimental_optin() -> None:
    text = SUPPORT_MATRIX.read_text()
    sem = [l for l in text.splitlines() if l.startswith("| Semantic search")]
    rer = [l for l in text.splitlines() if l.startswith("| Reranking")]
    assert sem, "SUPPORT_MATRIX missing Semantic search row"
    assert rer, "SUPPORT_MATRIX missing Reranking row"
    assert "experimental" in sem[0], "semantic row must stay experimental"
    assert "experimental" in rer[0], "reranking row must stay experimental"
    # learned reranking must remain opt-in / not default-enabled.
    assert "opt-in" in rer[0].lower(), "reranking row must remain opt-in"
