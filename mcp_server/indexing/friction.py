from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .source_metadata import FrictionMarker

_REFERENCE_RE = re.compile(r"(https?://\S+|#[0-9]+|\b[A-Z]{2,}-[0-9]+\b)")


@dataclass(frozen=True)
class FrictionPatternConfig:
    category: str
    label: str
    regex: re.Pattern[str]


def _compile_marker(marker: str) -> re.Pattern[str]:
    escaped = re.escape(marker)
    return re.compile(
        rf"(?i)\b{escaped}\b(?:\s*[:\-]\s*|\s+)?(?P<description>.*)$"
    )


FRICTION_PATTERN_CONFIGS: tuple[FrictionPatternConfig, ...] = (
    FrictionPatternConfig("hack", "HACK", _compile_marker("HACK")),
    FrictionPatternConfig("todo", "TODO", _compile_marker("TODO")),
    FrictionPatternConfig("fixme", "FIXME", _compile_marker("FIXME")),
    FrictionPatternConfig("workaround", "WORKAROUND", _compile_marker("WORKAROUND")),
    FrictionPatternConfig("wish", "WISH", _compile_marker("WISH")),
    FrictionPatternConfig("extraction_hint", "EXTRACTION_HINT", _compile_marker("EXTRACTION HINT")),
)

_ALTERNATE_CATEGORY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("workaround", re.compile(r"(?i)\bwork[- ]?around\b(?:\s*[:\-]\s*|\s+)?(?P<description>.*)$")),
    ("wish", re.compile(r"(?i)\bwish(?:es|ed)?\b(?:\s*[:\-]\s*|\s+)?(?P<description>.*)$")),
    (
        "extraction_hint",
        re.compile(r"(?i)\bextraction[_ -]?hint\b(?:\s*[:\-]\s*|\s+)?(?P<description>.*)$"),
    ),
)


def _clean_line(line: str) -> str:
    cleaned = line.strip()
    for prefix in ("<!--", "-->", "#", "//", "/*", "*/", "*", ";", "- [ ]", "- [x]", "-"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :].strip()
    return cleaned


def _extract_reference(text: str) -> str | None:
    match = _REFERENCE_RE.search(text)
    if match is None:
        return None
    return match.group(1)


def _iter_patterns() -> Iterable[tuple[str, str, re.Pattern[str]]]:
    for config in FRICTION_PATTERN_CONFIGS:
        yield config.category, config.label, config.regex
    for category, regex in _ALTERNATE_CATEGORY_PATTERNS:
        yield category, category.upper(), regex


def extract_friction_markers(content: str) -> list[FrictionMarker]:
    markers: list[FrictionMarker] = []
    for index, raw_line in enumerate(content.splitlines(), start=1):
        candidate = _clean_line(raw_line)
        if not candidate:
            continue
        for category, label, regex in _iter_patterns():
            match = regex.search(candidate)
            if match is None:
                continue
            description = (match.groupdict().get("description") or "").strip()
            if not description:
                description = candidate[match.end() :].strip() or label
            marker: FrictionMarker = {
                "source_type": "friction",
                "category": category,  # type: ignore[typeddict-item]
                "line": index,
                "description": description,
                "pattern": label,
            }
            reference = _extract_reference(description)
            if reference:
                marker["reference"] = reference
            markers.append(marker)
            break
    markers.sort(
        key=lambda item: (
            item["line"],
            item["category"],
            item["description"],
            item["pattern"],
            item.get("reference", ""),
        )
    )
    return markers
