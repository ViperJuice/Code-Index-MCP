from __future__ import annotations

from pathlib import Path


def test_procenv_evidence_contract() -> None:
    evidence = Path("docs/status/procenv-subprocess-env.md").read_text(encoding="utf-8")

    required_fragments = [
        "# PROCENV Subprocess Environment Evidence",
        "Audit date: 2026-07-06",
        "Phase plan: `plans/phase-plan-v9-PROCENV.md`",
        "Helper symbol: `mcp_server/utils/subprocess_env.py::get_full_env`",
        "OS path separator behavior",
        "Virtualenv and conda preservation",
        "Indexed call-site adoption",
        "Server-adjacent and preflight adoption",
        "Redaction proof",
        "No raw environment values are printed in this evidence note.",
        "Verification commands",
        "Non-goals confirmed",
        "README/CHANGELOG decision: no public doc delta",
    ]

    for fragment in required_fragments:
        assert fragment in evidence

    assert "AGENT_REMOTE_HOST=" not in evidence
    assert "AGENT_REMOTE_COMMAND=" not in evidence
    assert "PATH=" not in evidence
