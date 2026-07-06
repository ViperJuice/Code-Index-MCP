from .lock_registry import IndexingLockRegistry, lock_registry
from .friction import FRICTION_PATTERN_CONFIGS, FrictionPatternConfig, extract_friction_markers
from .source_metadata import (
    FRICTION_CATEGORIES,
    FRICTION_SOURCE_TYPE,
    SEARCH_SOURCE_METADATA_VERSION,
    FrictionCategory,
    FrictionMarker,
    SearchSourceMetadataEnvelope,
    SourceType,
    build_source_metadata,
    extract_matching_source_metadata,
    merge_source_metadata,
    normalize_friction_category,
)

__all__ = [
    "FRICTION_CATEGORIES",
    "FRICTION_PATTERN_CONFIGS",
    "FRICTION_SOURCE_TYPE",
    "IndexingLockRegistry",
    "FrictionCategory",
    "FrictionMarker",
    "FrictionPatternConfig",
    "SEARCH_SOURCE_METADATA_VERSION",
    "SearchSourceMetadataEnvelope",
    "SourceType",
    "build_source_metadata",
    "extract_friction_markers",
    "extract_matching_source_metadata",
    "lock_registry",
    "merge_source_metadata",
    "normalize_friction_category",
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
