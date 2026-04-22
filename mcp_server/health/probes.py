"""Health probes: HealthView aggregator + FastAPI router factories for /ready and /liveness."""

import time
from typing import Any, Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse


class HealthView:
    def __init__(
        self,
        *,
        dispatcher=None,
        sqlite_store=None,
        registry=None,
        startup_time: float | None = None,
    ) -> None:
        self._dispatcher = dispatcher
        self._sqlite_store = sqlite_store
        self._registry = registry
        self._startup_time = startup_time

    def snapshot(self) -> dict[str, Any]:
        uptime = time.monotonic() - self._startup_time if self._startup_time is not None else 0.0
        return {
            "sqlite": self._sqlite_store is not None,
            "registry": self._registry is not None,
            "dispatcher": self._dispatcher is not None,
            "last_index_ms": None,
            "uptime_s": float(uptime),
        }


def make_ready_router(
    *,
    get_dispatcher: Callable[[], Any],
    get_sqlite_store: Callable[[], Any],
    get_registry: Callable[[], Any],
    get_startup_time: Callable[[], float | None],
) -> APIRouter:
    router = APIRouter()

    @router.get("/ready")
    async def ready() -> JSONResponse:
        hv = HealthView(
            dispatcher=get_dispatcher(),
            sqlite_store=get_sqlite_store(),
            registry=get_registry(),
            startup_time=get_startup_time(),
        )
        snap = hv.snapshot()
        ready_ok = snap["sqlite"] and snap["registry"] and snap["dispatcher"]
        code = 200 if ready_ok else 503
        return JSONResponse(content=snap, status_code=code)

    return router


def make_liveness_router() -> APIRouter:
    router = APIRouter()

    @router.get("/liveness")
    async def liveness() -> JSONResponse:
        import asyncio

        await asyncio.sleep(0)
        return JSONResponse(content={"status": "ok"}, status_code=200)

    return router
