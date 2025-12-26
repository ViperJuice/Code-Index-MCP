#!/usr/bin/env python3
"""
Runnable checklist for vector storage/retrieval and artifact lifecycle validation.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server.core.path_resolver import PathResolver
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.semantic_indexer import SemanticIndexer


@dataclass
class StepResult:
    name: str
    status: str
    duration_s: float
    details: Dict[str, Any]


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@contextlib.contextmanager
def _chdir(path: Path) -> Iterable[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


@contextlib.contextmanager
def _temp_env(overrides: Dict[str, str]) -> Iterable[None]:
    original = {key: os.environ.get(key) for key in overrides}
    os.environ.update(overrides)
    try:
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _run_cmd(cmd: List[str], cwd: Optional[Path] = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _git_clean() -> bool:
    return _run_cmd(["git", "status", "--porcelain"]) == ""


def _get_remote_repo(remote_name: str) -> Optional[str]:
    try:
        url = _run_cmd(["git", "remote", "get-url", remote_name])
    except Exception:
        return None
    if "github.com" not in url:
        return None
    if url.startswith("git@"):
        return url.split(":", 1)[1].replace(".git", "").strip()
    if "github.com/" in url:
        return url.split("github.com/", 1)[1].replace(".git", "").strip()
    return None


def _select_sample_files(repo_root: Path) -> List[Path]:
    candidates = [
        repo_root / "mcp_server" / "dispatcher" / "dispatcher_enhanced.py",
        repo_root / "mcp_server" / "storage" / "sqlite_store.py",
        repo_root / "mcp_server" / "utils" / "semantic_indexer.py",
    ]
    return [path for path in candidates if path.exists()]


def _index_sqlite(repo_root: Path, files: List[Path]) -> Tuple[SQLiteStore, Path]:
    temp_dir = Path(tempfile.mkdtemp(prefix="checklist_sqlite_"))
    db_path = temp_dir / "checklist_index.db"
    store = SQLiteStore(str(db_path))
    repo_id = store.create_repository(str(repo_root), repo_root.name, {"type": "checklist"})

    for file_path in files:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        file_id = store.store_file(
            repo_id,
            path=str(file_path),
            relative_path=str(file_path.relative_to(repo_root)),
            language="python",
            size=len(content),
            hash=file_hash,
        )
        store.update_file_content_fts(file_id, content)

    return store, db_path


def _fts_check(store: SQLiteStore, queries: List[str]) -> Dict[str, Any]:
    results = {}
    for query in queries:
        matches = store.search_bm25(query, table="fts_code", limit=5)
        results[query] = {
            "count": len(matches),
            "top_file": matches[0].get("filepath") if matches else None,
        }
        if not matches:
            raise RuntimeError(f"FTS query returned no results: {query}")
    return results


def _semantic_check(
    repo_root: Path,
    files: List[Path],
    qdrant_path: str,
    queries: List[str],
    use_server: bool,
) -> Dict[str, Any]:
    temp_dir = Path(tempfile.mkdtemp(prefix="checklist_semantic_"))
    path_resolver = PathResolver(repository_root=repo_root)
    if qdrant_path == "file":
        qdrant_path = str(temp_dir / "vector_index.qdrant")
    results: Dict[str, Any] = {"qdrant_path": qdrant_path, "queries": {}}

    with _chdir(temp_dir):
        with _temp_env({"QDRANT_USE_SERVER": "true" if use_server else "false"}):
            indexer = SemanticIndexer(
                qdrant_path=qdrant_path,
                collection="checklist",
                path_resolver=path_resolver,
            )
            for file_path in files:
                indexer.index_file(file_path)

            for query in queries:
                matches = indexer.search(query, limit=5)
                results["queries"][query] = {
                    "count": len(matches),
                    "top_symbol": matches[0].get("symbol") if matches else None,
                    "top_file": matches[0].get("relative_path", matches[0].get("file"))
                    if matches
                    else None,
                }
                if not matches:
                    raise RuntimeError(f"Semantic query returned no results: {query}")

    shutil.rmtree(temp_dir, ignore_errors=True)
    return results


def _symbol_lookup_check(repo_root: Path) -> Dict[str, Any]:
    import jedi

    target = repo_root / "mcp_server" / "dispatcher" / "dispatcher_enhanced.py"
    if not target.exists():
        raise RuntimeError("dispatcher_enhanced.py not found")
    content = target.read_text(encoding="utf-8", errors="ignore")
    script = jedi.Script(code=content, path=str(target))
    names = script.get_names(all_scopes=True, definitions=True, references=False)
    found = [name.name for name in names if name.name == "EnhancedDispatcher"]
    if not found:
        raise RuntimeError("Symbol lookup failed for EnhancedDispatcher")
    return {"symbol": "EnhancedDispatcher", "file": str(target)}


def _server_available(url: str) -> bool:
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(url=url, timeout=5)
        client.get_collections()
        return True
    except Exception:
        return False


def _get_workflow_id(repo: str, workflow_path: str) -> int:
    output = _run_cmd(["gh", "api", f"repos/{repo}/actions/workflows/{workflow_path}"])
    data = json.loads(output)
    workflow_id = data.get("id")
    if not workflow_id:
        raise RuntimeError(f"Could not resolve workflow ID for {workflow_path}")
    return int(workflow_id)


def _wait_for_run(
    repo: str, sha: str, workflow_path: str, timeout_s: int = 1800
) -> Dict[str, Any]:
    start = time.time()
    workflow_id = _get_workflow_id(repo, workflow_path)
    while time.time() - start < timeout_s:
        output = _run_cmd(
            [
                "gh",
                "api",
                f"repos/{repo}/actions/workflows/{workflow_id}/runs?branch=main&per_page=20",
            ]
        )
        data = json.loads(output)
        for run in data.get("workflow_runs", []):
            if run.get("head_sha") == sha:
                return run
        time.sleep(10)
    raise RuntimeError(f"Timed out waiting for workflow run for {sha}")


def _wait_for_completion(repo: str, run_id: int, timeout_s: int = 1800) -> Dict[str, Any]:
    start = time.time()
    while time.time() - start < timeout_s:
        output = _run_cmd(["gh", "api", f"repos/{repo}/actions/runs/{run_id}"])
        data = json.loads(output)
        if data.get("status") == "completed":
            return data
        time.sleep(10)
    raise RuntimeError(f"Timed out waiting for run {run_id} to complete")


def _download_artifact(repo: str, run_id: int, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    _run_cmd(
        [
            "gh",
            "run",
            "download",
            str(run_id),
            "-R",
            repo,
            "-n",
            "code-index-bundle",
            "-D",
            str(dest),
        ]
    )
    archive = dest / "index-archive.tar.gz"
    if not archive.exists():
        raise RuntimeError("Artifact archive not found after download")
    return archive


def _extract_artifact(archive: Path, dest: Path) -> Path:
    extract_dir = dest / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(path=extract_dir)
    return extract_dir


def _ensure_git_identity(cwd: Path) -> None:
    name = _run_cmd(["git", "config", "user.name"], cwd=cwd)
    email = _run_cmd(["git", "config", "user.email"], cwd=cwd)
    if not name:
        _run_cmd(["git", "config", "user.name", "Checklist Bot"], cwd=cwd)
    if not email:
        _run_cmd(["git", "config", "user.email", "checklist@example.com"], cwd=cwd)


def _gh_authenticated() -> bool:
    try:
        _run_cmd(["gh", "auth", "status", "-h", "github.com"])
        return True
    except Exception:
        return False


def _validate_artifact(extract_dir: Path, expected_commit: str) -> Dict[str, Any]:
    db_path = extract_dir / "code_index.db"
    metadata_path = extract_dir / ".index_metadata.json"
    qdrant_path = extract_dir / "vector_index.qdrant"

    if not db_path.exists():
        raise RuntimeError("Artifact missing code_index.db")
    if not metadata_path.exists():
        raise RuntimeError("Artifact missing .index_metadata.json")
    if not qdrant_path.exists():
        raise RuntimeError("Artifact missing vector_index.qdrant directory")

    metadata = json.loads(metadata_path.read_text())
    commit_in_meta = metadata.get("commit") or metadata.get("git_commit")
    if commit_in_meta and commit_in_meta != expected_commit:
        raise RuntimeError(
            f"Artifact commit mismatch: expected {expected_commit}, got {commit_in_meta}"
        )

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM fts_code")
        row_count = cursor.fetchone()[0]
        if row_count == 0:
            raise RuntimeError("Artifact FTS index is empty")
        cursor = conn.execute("SELECT COUNT(*) FROM fts_code WHERE fts_code MATCH 'dispatcher'")
        query_count = cursor.fetchone()[0]
    finally:
        conn.close()

    qdrant_status = "unknown"
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(path=str(qdrant_path))
        collections = client.get_collections()
        qdrant_status = f"collections={len(collections.collections)}"
    except Exception as exc:
        qdrant_status = f"error: {exc}"

    return {
        "fts_rows": row_count,
        "fts_query_matches": query_count,
        "qdrant_status": qdrant_status,
    }


def _artifact_versions_check(
    repo: str, versions: int, keep: bool, workflow_path: str
) -> Dict[str, Any]:
    if versions < 1:
        return {"versions": 0}

    if not _git_clean():
        raise RuntimeError("Git working tree is dirty; aborting artifact version test")

    temp_dir = Path(tempfile.mkdtemp(prefix="checklist_worktree_"))
    branch_name = f"checklist-artifacts-{int(time.time())}"
    worktree_path = temp_dir / "worktree"

    _run_cmd(["git", "worktree", "add", "-b", branch_name, str(worktree_path), "HEAD"])

    results: Dict[str, Any] = {"versions": []}
    try:
        for index in range(versions):
            _ensure_git_identity(worktree_path)
            marker_file = worktree_path / "README.md"
            marker_line = f"Checklist artifact version {index + 1} at {int(time.time())}\n"
            with marker_file.open("a", encoding="utf-8") as handle:
                handle.write(marker_line)

            _run_cmd(["git", "add", "README.md"], cwd=worktree_path)
            _run_cmd(
                ["git", "commit", "-m", f"Checklist artifact version {index + 1}"],
                cwd=worktree_path,
            )
            sha = _run_cmd(["git", "rev-parse", "HEAD"], cwd=worktree_path)
            _run_cmd(["git", "push", "test-origin", "HEAD:main"], cwd=worktree_path)

            run = _wait_for_run(repo, sha, workflow_path)
            run_id = run["id"]
            completed = _wait_for_completion(repo, run_id)
            if completed.get("conclusion") != "success":
                raise RuntimeError(f"Workflow failed for {sha}: {completed.get('conclusion')}")

            dest = Path(tempfile.mkdtemp(prefix="checklist_artifact_"))
            archive = _download_artifact(repo, run_id, dest)
            extracted = _extract_artifact(archive, dest)
            validation = _validate_artifact(extracted, sha)

            results["versions"].append(
                {
                    "sha": sha,
                    "run_id": run_id,
                    "validation": validation,
                }
            )

            if not keep:
                shutil.rmtree(dest, ignore_errors=True)
    finally:
        _run_cmd(["git", "worktree", "remove", str(worktree_path), "--force"])
        _run_cmd(["git", "branch", "-D", branch_name])
        shutil.rmtree(temp_dir, ignore_errors=True)

    return results


def _run_step(name: str, func, skip_reason: Optional[str] = None) -> StepResult:
    start = time.time()
    if skip_reason:
        return StepResult(name=name, status="SKIP", duration_s=0.0, details={"reason": skip_reason})
    try:
        details = func()
        return StepResult(
            name=name,
            status="PASS",
            duration_s=time.time() - start,
            details=details if isinstance(details, dict) else {"result": details},
        )
    except Exception as exc:
        return StepResult(
            name=name,
            status="FAIL",
            duration_s=time.time() - start,
            details={"error": str(exc)},
        )


def main() -> int:
    _load_env_file(PROJECT_ROOT / ".env")

    repo_root = PROJECT_ROOT
    sample_files = _select_sample_files(repo_root)
    if not sample_files:
        print("No sample files found for checklist")
        return 1

    api_key = os.environ.get("VOYAGE_AI_API_KEY") or os.environ.get("VOYAGE_API_KEY")
    qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    server_ok = _server_available(qdrant_url)

    artifact_versions = int(os.environ.get("CHECKLIST_ARTIFACT_VERSIONS", "2"))
    artifact_keep = os.environ.get("CHECKLIST_KEEP_ARTIFACTS", "false").lower() == "true"
    artifact_repo = os.environ.get("CHECKLIST_ARTIFACT_REPO") or _get_remote_repo(
        "test-origin"
    )
    workflow_path = os.environ.get(
        "CHECKLIST_WORKFLOW_PATH", ".github/workflows/test-lifecycle.yml"
    )
    skip_github = os.environ.get("CHECKLIST_SKIP_GITHUB", "false").lower() == "true"

    results: List[StepResult] = []

    store, db_path = _index_sqlite(repo_root, sample_files)

    results.append(
        _run_step(
            "fts_retrieval",
            lambda: _fts_check(store, ["EnhancedDispatcher", "SQLiteStore", "SemanticIndexer"]),
        )
    )

    results.append(_run_step("symbol_lookup", lambda: _symbol_lookup_check(repo_root)))

    if api_key:
        results.append(
            _run_step(
                "semantic_in_memory",
                lambda: _semantic_check(
                    repo_root,
                    sample_files,
                    ":memory:",
                    ["dispatcher routing logic", "sqlite storage layer"],
                    use_server=False,
                ),
            )
        )
        results.append(
            _run_step(
                "semantic_file_based",
                lambda: _semantic_check(
                    repo_root,
                    sample_files,
                    "file",
                    ["dispatcher routing logic", "sqlite storage layer"],
                    use_server=False,
                ),
            )
        )
        results.append(
            _run_step(
                "semantic_server",
                lambda: _semantic_check(
                    repo_root,
                    sample_files,
                    "unused",
                    ["dispatcher routing logic", "sqlite storage layer"],
                    use_server=True,
                ),
                skip_reason=None if server_ok else f"Qdrant server unavailable at {qdrant_url}",
            )
        )
    else:
        results.append(
            _run_step(
                "semantic_in_memory",
                lambda: {},
                skip_reason="VOYAGE_AI_API_KEY not set",
            )
        )
        results.append(
            _run_step(
                "semantic_file_based",
                lambda: {},
                skip_reason="VOYAGE_AI_API_KEY not set",
            )
        )
        results.append(
            _run_step(
                "semantic_server",
                lambda: {},
                skip_reason="VOYAGE_AI_API_KEY not set",
            )
        )

    if skip_github:
        results.append(
            _run_step(
                "artifact_lifecycle",
                lambda: {},
                skip_reason="CHECKLIST_SKIP_GITHUB=true",
            )
        )
    elif not artifact_repo:
        results.append(
            _run_step(
                "artifact_lifecycle",
                lambda: {},
                skip_reason="test-origin remote not configured",
            )
        )
    else:
        results.append(
            _run_step(
                "artifact_lifecycle",
                lambda: _artifact_versions_check(
                    artifact_repo, artifact_versions, artifact_keep, workflow_path
                ),
                skip_reason=(
                    None
                    if shutil.which("gh") and _gh_authenticated()
                    else "gh CLI not available or not authenticated"
                ),
            )
        )

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repo_root": str(repo_root),
        "artifact_repo": artifact_repo,
        "workflow_path": workflow_path,
        "results": [asdict(result) for result in results],
    }

    report_dir = repo_root / "reports" / "testing"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"checklist_{int(time.time())}.json"
    report_path.write_text(json.dumps(summary, indent=2))

    print("\nCHECKLIST RESULTS")
    print("=" * 60)
    for result in results:
        print(f"{result.status:<5} {result.name} ({result.duration_s:.2f}s)")
        if result.status != "PASS":
            detail = result.details.get("reason") or result.details.get("error")
            if detail:
                print(f"  -> {detail}")
    print(f"\nReport written to: {report_path}")

    failed = [result for result in results if result.status == "FAIL"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
