"""Build per-repository health rows for the get_status surface (IF-0-P10-7)."""

from pathlib import Path

from mcp_server.storage.multi_repo_manager import RepositoryInfo


def build_health_row(repo_info: RepositoryInfo) -> dict:
    index_path_exists = bool(repo_info.index_path) and Path(repo_info.index_path).exists()
    git_dir_exists = bool(repo_info.git_common_dir) and Path(repo_info.git_common_dir).exists()
    staleness = None
    if not git_dir_exists:
        staleness = "missing_git_dir"
    elif not index_path_exists:
        staleness = "missing_index"
    return {
        "repo_id": repo_info.repository_id,
        "tracked_branch": repo_info.tracked_branch,
        "index_path_exists": index_path_exists,
        "git_dir_exists": git_dir_exists,
        "last_indexed_commit": repo_info.last_indexed_commit,
        "staleness_reason": staleness,
    }
