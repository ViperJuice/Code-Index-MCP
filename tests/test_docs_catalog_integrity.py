"""Integrity tests for .claude/docs-catalog.json (IF-0-P19-3)."""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / ".claude" / "docs-catalog.json"
TOOL_PATH = REPO_ROOT / ".claude" / "skills" / "_shared" / "scaffold_docs_catalog.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("scaffold_docs_catalog", TOOL_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_tool_importable():
    mod = _load_tool()
    assert hasattr(mod, "check_catalog"), "check_catalog function missing"
    assert hasattr(mod, "IntegrityError"), "IntegrityError class missing"


def test_catalog_schema():
    import json

    data = json.loads(CATALOG_PATH.read_text())
    assert isinstance(data.get("version"), int), "version must be int"
    assert isinstance(data.get("generated_at"), str), "generated_at must be str"
    assert isinstance(data.get("docs"), list), "docs must be list"
    for entry in data["docs"]:
        assert isinstance(entry.get("path"), str), f"path must be str in {entry}"
        assert isinstance(entry.get("description"), str), f"description must be str in {entry}"
        assert isinstance(
            entry.get("touched_by_phases"), list
        ), f"touched_by_phases must be list in {entry}"


def test_no_errors_on_valid_catalog():
    mod = _load_tool()
    errors = mod.check_catalog(CATALOG_PATH)
    hard_errors = [e for e in errors if e.severity == "error"]
    assert hard_errors == [], f"Unexpected hard errors: {hard_errors}"


def test_all_paths_exist_on_disk():
    import json

    data = json.loads(CATALOG_PATH.read_text())
    root = CATALOG_PATH.resolve().parent.parent
    for entry in data["docs"]:
        p = root / entry["path"]
        assert p.is_file(), f"Catalog entry path missing on disk: {entry['path']}"


def test_no_exact_duplicate_paths():
    import json

    data = json.loads(CATALOG_PATH.read_text())
    paths = [e["path"] for e in data["docs"]]
    seen = set()
    for p in paths:
        assert p not in seen, f"Duplicate path in catalog: {p}"
        seen.add(p)


def test_case_variant_warning():
    """check_catalog emits a warning (not error) for case-variant collisions."""
    import copy
    import json

    mod = _load_tool()
    data = json.loads(CATALOG_PATH.read_text())
    # inject a case-variant duplicate
    first = data["docs"][0]
    variant = copy.deepcopy(first)
    variant["path"] = first["path"].upper()
    data_with_variant = copy.deepcopy(data)
    data_with_variant["docs"].append(variant)

    import os
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data_with_variant, f, indent=2)
        tmp = Path(f.name)
    try:
        errors = mod.check_catalog(tmp)
        warnings = [e for e in errors if e.severity == "warning"]
        hard_errors = [e for e in errors if e.severity == "error"]
        assert len(warnings) >= 1, f"Expected at least 1 case-variant warning, got: {errors}"
        # Case-variant collisions must NOT be hard errors
        assert not any(
            "case" in e.message.lower() for e in hard_errors
        ), "Case-variant collision should be a warning, not an error"
    finally:
        os.unlink(tmp)


def test_missing_file_is_hard_error():
    import json
    import os
    import tempfile

    mod = _load_tool()
    data = json.loads(CATALOG_PATH.read_text())
    data_bad = dict(data)
    data_bad["docs"] = list(data["docs"]) + [
        {
            "path": "nonexistent/does_not_exist.md",
            "description": "ghost",
            "touched_by_phases": [],
        }
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data_bad, f, indent=2)
        tmp = Path(f.name)
    try:
        errors = mod.check_catalog(tmp)
        hard_errors = [e for e in errors if e.severity == "error"]
        assert len(hard_errors) >= 1, "Expected hard error for missing file"
    finally:
        os.unlink(tmp)
