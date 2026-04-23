"""Build per-repository health rows for the get_status surface (IF-0-P10-7)."""

from pathlib import Path
from typing import Optional

from mcp_server.health.repository_readiness import (
    ReadinessClassifier,
    RepositoryReadiness,
    RepositoryReadinessState,
)
from mcp_server.storage.multi_repo_manager import RepositoryInfo


def build_health_row(
    repo_info: RepositoryInfo,
    readiness: Optional[RepositoryReadiness] = None,
) -> dict:
    if readiness is None:
        readiness = ReadinessClassifier.classify_registered(repo_info)

    index_path_exists = bool(repo_info.index_path) and Path(repo_info.index_path).exists()
    git_dir_exists = bool(repo_info.git_common_dir) and Path(repo_info.git_common_dir).exists()
    staleness = None
    if not git_dir_exists:
        staleness = "missing_git_dir"
    elif not index_path_exists:
        staleness = "missing_index"
    elif readiness.state != RepositoryReadinessState.READY:
        staleness = readiness.state.value
    return {
        "repo_id": repo_info.repository_id,
        "tracked_branch": repo_info.tracked_branch,
        "index_path_exists": index_path_exists,
        "git_dir_exists": git_dir_exists,
        "last_indexed_commit": repo_info.last_indexed_commit,
        "staleness_reason": staleness,
        "readiness": readiness.state.value,
        "ready": readiness.ready,
        "readiness_code": readiness.code,
        "remediation": readiness.remediation,
    }
