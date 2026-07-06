from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Literal, NotRequired

from typing_extensions import TypedDict

SEARCH_SOURCE_METADATA_VERSION = "search_source_metadata.v1"
FRICTION_SOURCE_TYPE = "friction"
FRICTION_CATEGORIES = (
    "extraction_hint",
    "fixme",
    "hack",
    "todo",
    "workaround",
    "wish",
)

SourceType = Literal["friction"]
FrictionCategory = Literal[
    "extraction_hint",
    "fixme",
    "hack",
    "todo",
    "workaround",
    "wish",
]


class FrictionMarker(TypedDict):
    source_type: SourceType
    category: FrictionCategory
    line: int
    description: str
    pattern: str
    reference: NotRequired[str]


class SearchSourceMetadataEnvelope(TypedDict):
    schema_version: Literal["search_source_metadata.v1"]
    records: list[FrictionMarker]


def _sort_key(record: FrictionMarker) -> tuple[int, str, str, str, str]:
    return (
        int(record["line"]),
        record["category"],
        record["description"],
        record["pattern"],
        record.get("reference", ""),
    )


def normalize_friction_category(category: str) -> FrictionCategory:
    normalized = category.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in FRICTION_CATEGORIES:
        raise ValueError(f"Unknown friction category: {category}")
    return normalized  # type: ignore[return-value]


def normalize_friction_marker(record: dict[str, Any]) -> FrictionMarker:
    normalized: FrictionMarker = {
        "source_type": FRICTION_SOURCE_TYPE,
        "category": normalize_friction_category(str(record["category"])),
        "line": int(record["line"]),
        "description": str(record["description"]).strip(),
        "pattern": str(record["pattern"]).strip(),
    }
    reference = record.get("reference")
    if reference:
        normalized["reference"] = str(reference).strip()
    return normalized


def build_source_metadata(records: Iterable[dict[str, Any]]) -> SearchSourceMetadataEnvelope | None:
    normalized = [normalize_friction_marker(record) for record in records]
    if not normalized:
        return None
    normalized.sort(key=_sort_key)
    return {
        "schema_version": SEARCH_SOURCE_METADATA_VERSION,
        "records": normalized,
    }


def merge_source_metadata(
    metadata: dict[str, Any] | None,
    records: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    merged = deepcopy(metadata or {})
    envelope = build_source_metadata(records)
    if envelope is None:
        merged.pop("source_metadata", None)
        return merged
    merged["source_metadata"] = envelope
    return merged


def extract_matching_source_metadata(
    metadata: dict[str, Any] | None,
    *,
    source_type: str | None = None,
    friction_categories: Iterable[str] | None = None,
) -> SearchSourceMetadataEnvelope | None:
    if not metadata:
        return None
    envelope = metadata.get("source_metadata")
    if not isinstance(envelope, dict):
        return None
    if envelope.get("schema_version") != SEARCH_SOURCE_METADATA_VERSION:
        return None
    records = envelope.get("records")
    if not isinstance(records, list):
        return None

    normalized_categories = None
    if friction_categories is not None:
        normalized_categories = {normalize_friction_category(category) for category in friction_categories}

    matched: list[FrictionMarker] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        try:
            normalized = normalize_friction_marker(record)
        except (KeyError, TypeError, ValueError):
            continue
        if source_type and normalized["source_type"] != source_type:
            continue
        if normalized_categories and normalized["category"] not in normalized_categories:
            continue
        matched.append(normalized)

    if not matched:
        return None
    matched.sort(key=_sort_key)
    return {
        "schema_version": SEARCH_SOURCE_METADATA_VERSION,
        "records": matched,
    }
