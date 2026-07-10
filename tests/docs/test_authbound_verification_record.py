"""AUTHBOUND verification record contract test."""

from __future__ import annotations

from pathlib import Path


def test_authbound_verification_record_contains_required_metadata() -> None:
    text = Path("docs/status/authbound-verification.md").read_text()
    for required in (
        "7741ebf13c8598c35f57eac09bfeccf8bbbec7e202d2709526256c1c99b8966e",
        "IF-0-AUTHBOUND-1",
        "IF-0-AUTHBOUND-2",
        "uv run pytest tests/security/test_auth_boundary.py -q --no-cov",
        "scripts/admin_browser_smoke.py",
        "no-new-failures baseline comparison",
        "metadata_only",
        "non-goals",
    ):
        assert required in text
