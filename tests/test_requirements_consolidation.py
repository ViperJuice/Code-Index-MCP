"""SL-2 tests: verify requirements consolidation into pyproject.toml.

These tests confirm that:
- No stale requirements-*.txt files remain
- pyproject.toml has the correct requires-python value
- AGENTS.md does not contain a stale Python 3.8 version claim
- uv.lock exists (pyproject.toml is the sole dependency source of truth)
"""

try:
    import tomllib
except ImportError:  # Python <3.11
    import tomli as tomllib
from pathlib import Path

REPO = Path(__file__).parent.parent
ACTIVE_WORKFLOW_GLOBS = (".github/workflows/*.yml", ".github/workflows/*.yaml")
ACTIVE_DOCKERFILE_GLOBS = ("docker/dockerfiles/Dockerfile*",)
STALE_DEPENDENCY_PATTERNS = (
    "requirements.txt",
    "requirements-production.txt",
    "requirements-semantic.txt",
    "requirements-core.txt",
    "requirements*.txt",
    "pip install -r",
    "hashFiles('**/requirements*.txt')",
)


def test_no_requirements_txt_files():
    stale = list(REPO.glob("requirements*.txt"))
    assert stale == [], f"Stale requirements files: {stale}"


def test_pyproject_parseable_toml():
    with open(REPO / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    assert "project" in data, "pyproject.toml missing [project] section"


def test_pyproject_requires_python():
    with open(REPO / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    assert data["project"]["requires-python"] == ">=3.12"


def test_agents_md_no_stale_python_claim():
    text = (REPO / "AGENTS.md").read_text()
    # The stale claim is the exact string "# Python Version: 3.8+"
    assert "# Python Version: 3.8+" not in text, (
        "AGENTS.md still contains stale '# Python Version: 3.8+' claim"
    )


def test_uv_lock_exists():
    assert (REPO / "uv.lock").exists(), "uv.lock does not exist"


def test_active_workflows_do_not_reference_requirements_files():
    stale = {}
    for pattern in ACTIVE_WORKFLOW_GLOBS:
        for path in REPO.glob(pattern):
            text = path.read_text()
            hits = [needle for needle in STALE_DEPENDENCY_PATTERNS if needle in text]
            if hits:
                stale[str(path.relative_to(REPO))] = hits

    assert stale == {}, f"Active workflows reference removed requirements files: {stale}"


def test_dockerfiles_do_not_reference_requirements_files():
    stale = {}
    for pattern in ACTIVE_DOCKERFILE_GLOBS:
        for path in REPO.glob(pattern):
            text = path.read_text()
            hits = [needle for needle in STALE_DEPENDENCY_PATTERNS if needle in text]
            if hits:
                stale[str(path.relative_to(REPO))] = hits

    assert stale == {}, f"Dockerfiles reference removed requirements files: {stale}"


def test_tomllib_import_guard_present():
    import inspect, sys
    src = inspect.getsource(sys.modules[__name__])
    assert "try:\n    import tomllib\nexcept ImportError:" in src
    assert "import tomli as tomllib" in src


def test_pyproject_declares_tomli_for_py310():
    import re
    with open(REPO / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    dev_deps = data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
    normalized = [re.sub(r'\s+', ' ', entry).strip() for entry in dev_deps]
    assert 'tomli>=2.0.1; python_version<"3.11"' in normalized, (
        f"tomli conditional dep not found in dev deps: {normalized}"
    )
