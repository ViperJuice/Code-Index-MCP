"""Two-phase commit primitive for coupling durable (SQLite) and remote (Qdrant) ops."""

from typing import Callable, TypeVar

from ..core.errors import MCPError

T = TypeVar("T")


class TwoPhaseCommitError(MCPError):
    """Raised when shadow_op fails after primary_op has committed."""


def two_phase_commit(
    primary_op: Callable[[], T],
    shadow_op: Callable[[T], None],
    rollback: Callable[[T], None],
) -> T:
    """
    Invariant: after return, either BOTH primary and shadow succeeded,
    or NEITHER has visible side effects.
    primary_op runs first; its result is passed to shadow_op and rollback.
    If shadow_op raises, rollback(primary_result) is called and the
    shadow exception is re-raised wrapped in TwoPhaseCommitError.
    If primary_op raises, shadow_op is never invoked and the exception
    propagates unchanged.
    """
    primary_result = primary_op()

    try:
        shadow_op(primary_result)
    except Exception as shadow_exc:
        rollback_exc = None
        try:
            rollback(primary_result)
        except Exception as rb_exc:
            rollback_exc = rb_exc

        msg = f"shadow_op failed after primary committed: {shadow_exc}"
        err = TwoPhaseCommitError(
            msg,
            details=str(rollback_exc) if rollback_exc is not None else None,
        )
        raise err from shadow_exc

    return primary_result
