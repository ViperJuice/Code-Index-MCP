#!/usr/bin/env python3
"""Docs-catalog integrity checker and rescan tool."""
import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class IntegrityError:
    severity: str  # "error" | "warning"
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.message}"


def _repo_root(catalog_path: Path) -> Path:
    # catalog lives at <repo>/.claude/docs-catalog.json
    return catalog_path.resolve().parent.parent


def check_catalog(catalog_path: Path) -> list:
    """Validate catalog; return list[IntegrityError]. Empty == clean."""
    catalog_path = Path(catalog_path)
    errors: list[IntegrityError] = []

    try:
        data = json.loads(catalog_path.read_text())
    except Exception as exc:
        return [IntegrityError("error", f"Cannot parse catalog: {exc}")]

    # Schema checks
    if not isinstance(data.get("version"), int):
        errors.append(IntegrityError("error", "version must be an integer"))
    if not isinstance(data.get("generated_at"), str):
        errors.append(IntegrityError("error", "generated_at must be a string"))
    if not isinstance(data.get("docs"), list):
        errors.append(IntegrityError("error", "docs must be a list"))
        return errors

    root = _repo_root(catalog_path)
    seen_exact: dict[str, int] = {}
    seen_lower: dict[str, str] = {}

    for i, entry in enumerate(data["docs"]):
        for field in ("path", "description"):
            if not isinstance(entry.get(field), str):
                errors.append(IntegrityError("error", f"docs[{i}].{field} must be a string"))
        if not isinstance(entry.get("touched_by_phases"), list):
            errors.append(IntegrityError("error", f"docs[{i}].touched_by_phases must be a list"))

        path_str = entry.get("path", "")
        if not path_str:
            continue

        # Existence check (case-sensitive on Linux)
        if not (root / path_str).is_file():
            errors.append(IntegrityError("error", f"Path not found on disk: {path_str}"))

        # Exact duplicate check
        if path_str in seen_exact:
            errors.append(IntegrityError("error", f"Duplicate path: {path_str} (indexes {seen_exact[path_str]} and {i})"))
        else:
            seen_exact[path_str] = i

        # Case-variant collision check
        lower = path_str.lower()
        if lower in seen_lower and seen_lower[lower] != path_str:
            errors.append(IntegrityError(
                "warning",
                f"Case-variant collision: '{path_str}' vs '{seen_lower[lower]}'"
            ))
        else:
            seen_lower[lower] = path_str

    return errors


def rescan(catalog_path: Path) -> None:
    """Drop missing-file entries, bump generated_at. Preserves touched_by_phases."""
    catalog_path = Path(catalog_path)
    data = json.loads(catalog_path.read_text())
    root = _repo_root(catalog_path)

    original_count = len(data["docs"])
    data["docs"] = [
        e for e in data["docs"]
        if (root / e["path"]).is_file()
    ]
    removed = original_count - len(data["docs"])
    data["generated_at"] = str(date.today())

    catalog_path.write_text(json.dumps(data, indent=2) + "\n")
    if removed:
        print(f"Removed {removed} missing-file entries.", file=sys.stderr)
    print(f"generated_at set to {data['generated_at']}.", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Docs-catalog integrity tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", metavar="CATALOG", help="Validate catalog (read-only)")
    group.add_argument("--rescan", metavar="CATALOG", help="Drop missing entries, bump generated_at")
    args = parser.parse_args()

    if args.check:
        errors = check_catalog(Path(args.check))
        if errors:
            for e in errors:
                print(e)
            hard = [e for e in errors if e.severity == "error"]
            sys.exit(1 if hard else 0)
        sys.exit(0)

    if args.rescan:
        rescan(Path(args.rescan))
        errors = check_catalog(Path(args.rescan))
        hard = [e for e in errors if e.severity == "error"]
        if hard:
            for e in hard:
                print(e)
            sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    main()
