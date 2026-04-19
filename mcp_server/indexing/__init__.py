from .lock_registry import IndexingLockRegistry, lock_registry

__all__ = [
    "IndexingLockRegistry",
    "lock_registry",
    "ReindexCheckpoint",
    "save",
    "load",
    "clear",
]

_CHECKPOINT_NAMES = {"ReindexCheckpoint", "save", "load", "clear"}


def __getattr__(name: str):
    if name in _CHECKPOINT_NAMES:
        from . import checkpoint
        return getattr(checkpoint, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
