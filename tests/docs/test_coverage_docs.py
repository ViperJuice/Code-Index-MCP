"""Coverage documentation posture checks."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
README = REPO / "README.md"
TESTING_GUIDE = REPO / "docs" / "development" / "TESTING-GUIDE.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_readme_and_testing_guide_define_local_coverage_contract() -> None:
    combined = "\n".join((_read(README), _read(TESTING_GUIDE)))
    for phrase in (
        "make coverage",
        "make coverage-baseline",
        "make coverage-artifact-guard",
        "coverage.xml",
        "term-missing",
        "agent-full",
    ):
        assert phrase in combined


def test_docs_defer_badges_and_hosted_upload_claims_without_trusted_evidence() -> None:
    combined = "\n".join((_read(README), _read(TESTING_GUIDE)))
    assert "badge remains deferred" in combined
    assert "trusted event" in combined
    assert "Codecov upload is not" in combined
    assert "default COVERAGE contract" in combined
