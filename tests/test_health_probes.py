"""Tests for SL-1 health probes: HealthView + /ready + /liveness endpoints."""

import importlib
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# SL-1.1 — HealthView standalone (no gateway import cycle)
# ---------------------------------------------------------------------------


def test_health_view_standalone_import():
    """HealthView must be importable and probes.py must not statically import gateway."""
    mod = importlib.import_module("mcp_server.health.probes")
    assert hasattr(mod, "HealthView")
    # Verify probes module source has no static gateway import (no circular dep at module load)
    import inspect

    source = inspect.getsource(mod)
    assert "from mcp_server.gateway" not in source
    assert "import mcp_server.gateway" not in source


def test_health_view_snapshot_five_keys_all_none():
    """snapshot() returns exactly the 5 stable keys when all kwargs are None."""
    from mcp_server.health.probes import HealthView

    hv = HealthView()
    snap = hv.snapshot()

    assert set(snap.keys()) == {"sqlite", "registry", "dispatcher", "last_index_ms", "uptime_s"}
    assert snap["sqlite"] is False
    assert snap["registry"] is False
    assert snap["dispatcher"] is False
    assert snap["last_index_ms"] is None
    assert isinstance(snap["uptime_s"], float)


def test_health_view_snapshot_all_present():
    """snapshot() returns True for all components when objects are provided."""
    from mcp_server.health.probes import HealthView

    class _Stub:
        pass

    hv = HealthView(
        dispatcher=_Stub(),
        sqlite_store=_Stub(),
        registry=_Stub(),
        startup_time=time.monotonic() - 5.0,
    )
    snap = hv.snapshot()

    assert snap["sqlite"] is True
    assert snap["registry"] is True
    assert snap["dispatcher"] is True
    assert snap["last_index_ms"] is None
    assert snap["uptime_s"] >= 5.0


def test_health_view_uptime_is_float_when_startup_none():
    """uptime_s must be float (0.0) even when startup_time is None."""
    from mcp_server.health.probes import HealthView

    snap = HealthView().snapshot()
    assert isinstance(snap["uptime_s"], float)
    assert snap["uptime_s"] == 0.0


# ---------------------------------------------------------------------------
# Minimal FastAPI app for route tests (avoids full gateway startup)
# ---------------------------------------------------------------------------


def _make_test_app(dispatcher=None, sqlite_store=None, registry=None, startup_time=None):
    """Build a minimal FastAPI with /ready and /liveness routes."""
    from mcp_server.health.probes import HealthView, make_liveness_router, make_ready_router

    app = FastAPI()
    app.include_router(
        make_ready_router(
            get_dispatcher=lambda: dispatcher,
            get_sqlite_store=lambda: sqlite_store,
            get_registry=lambda: registry,
            get_startup_time=lambda: startup_time,
        )
    )
    app.include_router(make_liveness_router())
    return app


# ---------------------------------------------------------------------------
# /ready tests
# ---------------------------------------------------------------------------


def test_ready_503_when_dispatcher_none():
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    resp = client.get("/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["dispatcher"] is False


def test_ready_503_when_only_dispatcher_present():
    class _Stub:
        pass

    client = TestClient(_make_test_app(dispatcher=_Stub()), raise_server_exceptions=False)
    resp = client.get("/ready")
    assert resp.status_code == 503


def test_ready_200_when_all_present():
    class _Stub:
        pass

    t0 = time.monotonic() - 2.0
    client = TestClient(
        _make_test_app(dispatcher=_Stub(), sqlite_store=_Stub(), registry=_Stub(), startup_time=t0),
        raise_server_exceptions=False,
    )
    resp = client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["dispatcher"] is True
    assert body["sqlite"] is True
    assert body["registry"] is True


def test_ready_completes_under_100ms():
    class _Stub:
        pass

    t0 = time.monotonic()
    client = TestClient(
        _make_test_app(dispatcher=_Stub(), sqlite_store=_Stub(), registry=_Stub(), startup_time=t0),
        raise_server_exceptions=False,
    )
    start = time.monotonic()
    client.get("/ready")
    elapsed_ms = (time.monotonic() - start) * 1000
    assert elapsed_ms < 100, f"/ready took {elapsed_ms:.1f}ms"


# ---------------------------------------------------------------------------
# /liveness tests
# ---------------------------------------------------------------------------


def test_liveness_200_when_loop_responsive():
    app = _make_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    start = time.monotonic()
    resp = client.get("/liveness")
    elapsed = time.monotonic() - start
    assert resp.status_code == 200
    assert elapsed < 1.0, f"/liveness took {elapsed:.2f}s"


def test_liveness_body_has_status_ok():
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    body = client.get("/liveness").json()
    assert body.get("status") == "ok"
