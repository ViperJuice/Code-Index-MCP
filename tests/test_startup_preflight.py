import asyncio

import pytest


def test_gateway_startup_runs_preflight(monkeypatch):
    import mcp_server.gateway as gateway

    calls = []

    class SentinelError(Exception):
        pass

    def _fake_preflight():
        calls.append("run")
        return type("PreflightResult", (), {"status": "warning", "checks": []})()

    def _fake_format(result):
        calls.append("format")
        return ["warning"]

    monkeypatch.setattr(gateway, "run_startup_preflight", _fake_preflight)
    monkeypatch.setattr(gateway, "format_preflight_report", _fake_format)
    monkeypatch.setattr(
        gateway,
        "SecurityConfig",
        lambda **kwargs: (_ for _ in ()).throw(SentinelError("stop")),
    )

    with pytest.raises(SentinelError, match="stop"):
        asyncio.run(gateway.startup_event())

    assert calls == ["run", "format"]
