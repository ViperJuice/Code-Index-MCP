#!/usr/bin/env python3
"""Fail if Markdown files contain box-drawing ASCII diagrams outside mermaid blocks."""

from __future__ import annotations

import argparse
from pathlib import Path

BOX_CHARS = {"├", "└", "┌", "┐", "└", "┘", "│", "─", "═", "╔", "╗", "╚", "╝", "║"}
ASCII_HINTS = ("+--", "|--", "└──", "├──", "->", "=>")


def detect_ascii_diagrams(file_path: Path) -> list[int]:
    """Return line numbers likely containing non-mermaid diagrams."""
    lines = file_path.read_text(encoding="utf-8").splitlines()
    violations: list[int] = []
    in_fence = False
    fence_lang = ""

    for index, line in enumerate(lines, start=1):
        stripped = line.strip()

        if stripped.startswith("```"):
            if not in_fence:
                in_fence = True
                fence_lang = stripped[3:].strip().lower()
            else:
                in_fence = False
                fence_lang = ""
            continue

        if in_fence and fence_lang == "mermaid":
            continue

        contains_box = any(char in line for char in BOX_CHARS)
        contains_ascii = any(hint in line for hint in ASCII_HINTS)
        is_untyped_or_text_fence = in_fence and fence_lang in {"", "text", "ascii"}

        if contains_box or (is_untyped_or_text_fence and contains_ascii):
            violations.append(index)

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        default=["architecture", "docs"],
        help="Directories or markdown files to scan.",
    )
    args = parser.parse_args()

    markdown_files: list[Path] = []
    for raw_path in args.paths:
        path = Path(raw_path)
        if path.is_file() and path.suffix.lower() == ".md":
            markdown_files.append(path)
        elif path.is_dir():
            markdown_files.extend(path.rglob("*.md"))

    has_violations = False
    for file_path in sorted(markdown_files):
        violations = detect_ascii_diagrams(file_path)
        if violations:
            has_violations = True
            line_list = ", ".join(str(line) for line in violations[:10])
            suffix = "..." if len(violations) > 10 else ""
            print(f"ASCII diagram detected in {file_path}: lines {line_list}{suffix}")

    if has_violations:
        print("\nPlease convert diagrams to Mermaid blocks (```mermaid ... ```).")
        return 1

    print(f"Scanned {len(markdown_files)} markdown files. No ASCII diagrams found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
