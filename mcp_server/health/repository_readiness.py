"""Shared repository readiness contracts for query and status surfaces."""

from __future__ import annotations

import json
import sqlite3
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from mcp_server.storage.repo_identity import compute_repo_id


class RepositoryReadinessState(str, Enum):
    READY = "ready"
    UNREGISTERED_REPOSITORY = "unregistered_repository"
    MISSING_INDEX = "missing_index"
    INDEX_EMPTY = "index_empty"
    STALE_COMMIT = "stale_commit"
    WRONG_BRANCH = "wrong_branch"
    INDEX_BUILDING = "index_building"
    UNSUPPORTED_WORKTREE = "unsupported_worktree"


class SemanticReadinessState(str, Enum):
    READY = "ready"
    ENRICHMENT_UNAVAILABLE = "enrichment_unavailable"
    SUMMARIES_MISSING = "summaries_missing"
    VECTORS_MISSING = "vectors_missing"
    VECTOR_DIMENSION_MISMATCH = "vector_dimension_mismatch"
    PROFILE_MISMATCH = "profile_mismatch"
    SEMANTIC_STALE = "semantic_stale"


@dataclass(frozen=True)
class RepositoryReadiness:
    state: RepositoryReadinessState
    repository_id: Optional[str] = None
    repository_name: Optional[str] = None
    registered_path: Optional[str] = None
    requested_path: Optional[str] = None
    tracked_branch: Optional[str] = None
    current_branch: Optional[str] = None
    current_commit: Optional[str] = None
    last_indexed_commit: Optional[str] = None
    index_path: Optional[str] = None
    remediation: Optional[str] = None

    @property
    def ready(self) -> bool:
        return self.state == RepositoryReadinessState.READY

    @property
    def code(self) -> Optional[str]:
        return None if self.ready else self.state.value

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "ready": self.ready,
            "code": self.code,
            "repository_id": self.repository_id,
            "repository_name": self.repository_name,
            "registered_path": self.registered_path,
            "requested_path": self.requested_path,
            "tracked_branch": self.tracked_branch,
            "current_branch": self.current_branch,
            "current_commit": self.current_commit,
            "last_indexed_commit": self.last_indexed_commit,
            "index_path": self.index_path,
            "remediation": self.remediation,
        }


@dataclass(frozen=True)
class SemanticReadiness:
    state: SemanticReadinessState
    profile_id: Optional[str] = None
    compatibility_fingerprint: Optional[str] = None
    discovered_fingerprint: Optional[str] = None
    collection_name: Optional[str] = None
    discovered_collection_name: Optional[str] = None
    vector_dimension: Optional[int] = None
    discovered_vector_dimension: Optional[int] = None
    remediation: Optional[str] = None
    evidence: Optional[dict[str, Any]] = None

    @property
    def ready(self) -> bool:
        return self.state == SemanticReadinessState.READY

    @property
    def code(self) -> Optional[str]:
        return None if self.ready else self.state.value

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "ready": self.ready,
            "code": self.code,
            "profile_id": self.profile_id,
            "compatibility_fingerprint": self.compatibility_fingerprint,
            "discovered_fingerprint": self.discovered_fingerprint,
            "collection_name": self.collection_name,
            "discovered_collection_name": self.discovered_collection_name,
            "vector_dimension": self.vector_dimension,
            "discovered_vector_dimension": self.discovered_vector_dimension,
            "remediation": self.remediation,
            "evidence": self.evidence,
        }


class ReadinessClassifier:
    """Classify registered and arbitrary repository paths without mutating state."""

    @classmethod
    def classify_registered(
        cls,
        repo_info: Any,
        requested_path: Optional[Path] = None,
        indexing_active: bool = False,
    ) -> RepositoryReadiness:
        registered_path = Path(repo_info.path).resolve(strict=False)
        index_path = (
            Path(repo_info.index_path).resolve(strict=False) if repo_info.index_path else None
        )
        current_branch = getattr(repo_info, "current_branch", None) or _git_branch(registered_path)
        current_commit = getattr(repo_info, "current_commit", None) or _git_commit(registered_path)
        tracked_branch = getattr(repo_info, "tracked_branch", None)
        last_indexed_commit = getattr(repo_info, "last_indexed_commit", None)

        state = RepositoryReadinessState.READY
        remediation = None
        if indexing_active:
            state = RepositoryReadinessState.INDEX_BUILDING
            remediation = "Wait for indexing to finish, then retry the request."
        elif index_path is None or not index_path.exists():
            state = RepositoryReadinessState.MISSING_INDEX
            remediation = "Run reindex or pull the latest artifact for this repository."
        elif cls._index_is_empty(index_path):
            state = RepositoryReadinessState.INDEX_EMPTY
            remediation = "Run reindex to populate the repository index."
        elif tracked_branch and current_branch and tracked_branch != current_branch:
            state = RepositoryReadinessState.WRONG_BRANCH
            remediation = f"Switch to the tracked branch '{tracked_branch}' or register the intended repository path."
        elif current_commit and last_indexed_commit and current_commit != last_indexed_commit:
            state = RepositoryReadinessState.STALE_COMMIT
            remediation = "Run reindex to update the repository index to the current commit."

        return RepositoryReadiness(
            state=state,
            repository_id=getattr(repo_info, "repository_id", None),
            repository_name=getattr(repo_info, "name", None),
            registered_path=str(registered_path),
            requested_path=(
                str(Path(requested_path).resolve(strict=False)) if requested_path else None
            ),
            tracked_branch=tracked_branch,
            current_branch=current_branch,
            current_commit=current_commit,
            last_indexed_commit=last_indexed_commit,
            index_path=str(index_path) if index_path else None,
            remediation=remediation,
        )

    @classmethod
    def classify_path(
        cls,
        registry: Any,
        path: Path,
        indexing_active: bool = False,
    ) -> RepositoryReadiness:
        requested_path = Path(path).expanduser().resolve(strict=False)
        git_root = _find_git_root(requested_path)
        if git_root is None:
            return cls._unregistered(requested_path)

        repo_id = registry.find_by_path(git_root)
        if repo_id:
            repo_info = registry.get(repo_id)
            if repo_info is not None:
                return cls.classify_registered(
                    repo_info,
                    requested_path=requested_path,
                    indexing_active=indexing_active,
                )

        if hasattr(registry, "find_unsupported_worktree"):
            repo_info = registry.find_unsupported_worktree(git_root)
            if repo_info is not None:
                return cls._unsupported_worktree(repo_info, requested_path)

        try:
            repo_id = compute_repo_id(git_root).repo_id
        except Exception:
            return cls._unregistered(requested_path)
        repo_info = registry.get(repo_id)
        if repo_info is None:
            return cls._unregistered(requested_path)
        return cls.classify_registered(
            repo_info,
            requested_path=requested_path,
            indexing_active=indexing_active,
        )

    @classmethod
    def classify_semantic_registered(
        cls,
        repo_info: Any,
        sqlite_store: Any,
    ) -> SemanticReadiness:
        profile = _current_semantic_profile()
        if profile is None:
            return SemanticReadiness(
                state=SemanticReadinessState.ENRICHMENT_UNAVAILABLE,
                remediation="Configure a semantic profile before treating semantic search as ready.",
            )

        metadata = _load_index_metadata(Path(repo_info.path))
        expected_collection = _profile_collection_name(profile)
        evidence = _semantic_evidence(sqlite_store, profile.profile_id, expected_collection)
        metadata_profile = _current_profile_metadata(metadata, profile.profile_id)
        discovered_fingerprint = _metadata_fingerprint(metadata_profile)
        discovered_collection = _metadata_string(metadata_profile, "collection_name")
        discovered_dimension = _metadata_int(metadata_profile, "model_dimension")
        remediation = (
            "Run semantic summary/vector generation for the current profile before semantic queries."
        )

        if evidence is None:
            return SemanticReadiness(
                state=SemanticReadinessState.ENRICHMENT_UNAVAILABLE,
                profile_id=profile.profile_id,
                compatibility_fingerprint=profile.compatibility_fingerprint,
                collection_name=expected_collection,
                vector_dimension=profile.vector_dimension,
                remediation="Semantic evidence tables are unavailable; repair the local index store.",
            )

        if int(evidence["missing_summaries"]) > 0:
            return SemanticReadiness(
                state=SemanticReadinessState.SUMMARIES_MISSING,
                profile_id=profile.profile_id,
                compatibility_fingerprint=profile.compatibility_fingerprint,
                collection_name=expected_collection,
                vector_dimension=profile.vector_dimension,
                remediation=remediation,
                evidence=evidence,
            )

        if int(evidence["missing_vectors"]) > 0 or int(evidence["vector_link_count"]) == 0:
            return SemanticReadiness(
                state=SemanticReadinessState.VECTORS_MISSING,
                profile_id=profile.profile_id,
                compatibility_fingerprint=profile.compatibility_fingerprint,
                collection_name=expected_collection,
                vector_dimension=profile.vector_dimension,
                remediation=remediation,
                evidence=evidence,
            )

        if discovered_dimension is not None and discovered_dimension != profile.vector_dimension:
            return SemanticReadiness(
                state=SemanticReadinessState.VECTOR_DIMENSION_MISMATCH,
                profile_id=profile.profile_id,
                compatibility_fingerprint=profile.compatibility_fingerprint,
                discovered_fingerprint=discovered_fingerprint,
                collection_name=expected_collection,
                discovered_collection_name=discovered_collection,
                vector_dimension=profile.vector_dimension,
                discovered_vector_dimension=discovered_dimension,
                remediation="Rebuild semantic vectors with the current embedding dimension.",
                evidence=evidence,
            )

        if (
            expected_collection
            and discovered_collection
            and expected_collection != discovered_collection
        ) or int(evidence["collection_mismatches"]) > 0:
            return SemanticReadiness(
                state=SemanticReadinessState.PROFILE_MISMATCH,
                profile_id=profile.profile_id,
                compatibility_fingerprint=profile.compatibility_fingerprint,
                discovered_fingerprint=discovered_fingerprint,
                collection_name=expected_collection,
                discovered_collection_name=discovered_collection,
                vector_dimension=profile.vector_dimension,
                discovered_vector_dimension=discovered_dimension,
                remediation="Rebuild semantic vectors so the current profile and collection agree.",
                evidence=evidence,
            )

        if metadata_profile is None or (
            discovered_fingerprint
            and discovered_fingerprint != profile.compatibility_fingerprint
        ):
            return SemanticReadiness(
                state=SemanticReadinessState.SEMANTIC_STALE,
                profile_id=profile.profile_id,
                compatibility_fingerprint=profile.compatibility_fingerprint,
                discovered_fingerprint=discovered_fingerprint,
                collection_name=expected_collection,
                discovered_collection_name=discovered_collection,
                vector_dimension=profile.vector_dimension,
                discovered_vector_dimension=discovered_dimension,
                remediation="Semantic summaries/vectors are stale for the current profile; rebuild them.",
                evidence=evidence,
            )

        return SemanticReadiness(
            state=SemanticReadinessState.READY,
            profile_id=profile.profile_id,
            compatibility_fingerprint=profile.compatibility_fingerprint,
            discovered_fingerprint=discovered_fingerprint,
            collection_name=expected_collection,
            discovered_collection_name=discovered_collection,
            vector_dimension=profile.vector_dimension,
            discovered_vector_dimension=discovered_dimension,
            evidence=evidence,
        )

    @classmethod
    def _unsupported_worktree(cls, repo_info: Any, requested_path: Path) -> RepositoryReadiness:
        return RepositoryReadiness(
            state=RepositoryReadinessState.UNSUPPORTED_WORKTREE,
            repository_id=getattr(repo_info, "repository_id", None),
            repository_name=getattr(repo_info, "name", None),
            registered_path=str(Path(repo_info.path).resolve(strict=False)),
            requested_path=str(requested_path),
            tracked_branch=getattr(repo_info, "tracked_branch", None),
            current_branch=getattr(repo_info, "current_branch", None),
            current_commit=getattr(repo_info, "current_commit", None),
            last_indexed_commit=getattr(repo_info, "last_indexed_commit", None),
            index_path=str(Path(repo_info.index_path).resolve(strict=False)),
            remediation=_worktree_remediation(),
        )

    @staticmethod
    def _unregistered(requested_path: Path) -> RepositoryReadiness:
        return RepositoryReadiness(
            state=RepositoryReadinessState.UNREGISTERED_REPOSITORY,
            requested_path=str(requested_path),
            remediation="Register this repository path before querying it.",
        )

    @staticmethod
    def _index_is_empty(index_path: Path) -> bool:
        if index_path.stat().st_size == 0:
            return True
        try:
            conn = sqlite3.connect(str(index_path))
            try:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='files'"
                )
                if cursor.fetchone() is None:
                    return True
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM files WHERE is_deleted = 0 OR is_deleted IS NULL"
                )
                return int(cursor.fetchone()[0]) == 0
            finally:
                conn.close()
        except sqlite3.OperationalError:
            try:
                conn = sqlite3.connect(str(index_path))
                try:
                    cursor = conn.execute("SELECT COUNT(*) FROM files")
                    return int(cursor.fetchone()[0]) == 0
                finally:
                    conn.close()
            except Exception:
                return False
        except Exception:
            return False


def _worktree_remediation() -> str:
    return "Use the registered path or unregister it before registering another worktree."


def _find_git_root(start: Path) -> Optional[Path]:
    current = start.expanduser().resolve(strict=False)
    if current.is_file():
        current = current.parent
    top_level = _run_git(["rev-parse", "--show-toplevel"], current)
    if top_level:
        return Path(top_level).resolve(strict=False)
    is_bare = _run_git(["rev-parse", "--is-bare-repository"], current)
    if is_bare == "true":
        return current
    while True:
        if (current / ".git").exists():
            return current
        if current.parent == current:
            return None
        current = current.parent


def _git_branch(path: Path) -> Optional[str]:
    return _run_git(["rev-parse", "--abbrev-ref", "HEAD"], path)


def _git_commit(path: Path) -> Optional[str]:
    return _run_git(["rev-parse", "HEAD"], path)


def _run_git(args: list[str], cwd: Path) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        value = result.stdout.strip()
        return value if value and value != "HEAD" else None
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def _current_semantic_profile() -> Any:
    try:
        from mcp_server.config.settings import get_settings
        from mcp_server.artifacts.semantic_profiles import SemanticProfileRegistry

        settings = get_settings()
        if not settings.semantic_search_enabled:
            return None

        registry = SemanticProfileRegistry.from_raw(
            settings.get_semantic_profiles_config(),
            settings.get_semantic_default_profile(),
            tool_version=settings.app_version,
        )
        return registry.get()
    except Exception:
        return None


def _load_index_metadata(repo_root: Path) -> dict[str, Any]:
    metadata_path = repo_root / ".index_metadata.json"
    if not metadata_path.exists():
        return {}
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _semantic_evidence(
    sqlite_store: Any,
    profile_id: str,
    expected_collection: Optional[str],
) -> Optional[dict[str, Any]]:
    getter = getattr(sqlite_store, "get_semantic_readiness_evidence", None)
    if not callable(getter):
        return None
    try:
        result = getter(profile_id, collection=expected_collection)
        return result if isinstance(result, dict) else None
    except Exception:
        return None


def _current_profile_metadata(metadata: dict[str, Any], profile_id: str) -> Optional[dict[str, Any]]:
    try:
        from mcp_server.artifacts.semantic_profiles import get_primary_semantic_profile_metadata
    except Exception:
        return None

    discovered_profile_id, payload = get_primary_semantic_profile_metadata(metadata)
    if payload is None:
        return None
    if discovered_profile_id == profile_id:
        return payload

    semantic_profiles = metadata.get("semantic_profiles")
    if isinstance(semantic_profiles, dict):
        candidate = semantic_profiles.get(profile_id)
        if isinstance(candidate, dict):
            return candidate
    return None


def _profile_collection_name(profile: Any) -> Optional[str]:
    metadata = getattr(profile, "build_metadata", None) or {}
    value = metadata.get("collection_name")
    return str(value).strip() if isinstance(value, str) and value.strip() else None


def _metadata_string(metadata: Optional[dict[str, Any]], key: str) -> Optional[str]:
    if not metadata:
        return None
    value = metadata.get(key)
    return str(value).strip() if isinstance(value, str) and value.strip() else None


def _metadata_int(metadata: Optional[dict[str, Any]], key: str) -> Optional[int]:
    if not metadata:
        return None
    value = metadata.get(key)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _metadata_fingerprint(metadata: Optional[dict[str, Any]]) -> Optional[str]:
    if not metadata:
        return None
    raw = metadata.get("compatibility_fingerprint") or metadata.get("compatibility_hash")
    return str(raw).strip() if isinstance(raw, str) and raw.strip() else None
