"""Tests for mcp_server.storage.repo_identity — SL-1."""
import subprocess
from pathlib import Path

import pytest


def git(*args, cwd=None):
    subprocess.run(["git"] + list(args), cwd=cwd, check=True, capture_output=True)


def make_bare_and_clone(tmp_path):
    """Return (bare_dir, clone_dir) with at least one commit."""
    bare = tmp_path / "bare.git"
    bare.mkdir()
    git("init", "--bare", str(bare))

    clone = tmp_path / "clone"
    git("clone", str(bare), str(clone))

    # Configure identity so commit works
    git("config", "user.email", "test@test.com", cwd=clone)
    git("config", "user.name", "Test", cwd=clone)

    (clone / "README.md").write_text("hello")
    git("add", "README.md", cwd=clone)
    git("commit", "-m", "init", cwd=clone)
    git("push", "origin", "HEAD:main", cwd=clone)
    git("symbolic-ref", "HEAD", "refs/heads/main", cwd=bare)

    return bare, clone


# ---------------------------------------------------------------------------
# SL-1.1 tests — all should FAIL before the module exists
# ---------------------------------------------------------------------------


class TestComputeRepoId:
    def test_worktree_equivalence(self, tmp_path):
        """bare + main clone + two worktrees → same repo_id."""
        from mcp_server.storage.repo_identity import compute_repo_id

        bare, clone = make_bare_and_clone(tmp_path)

        # Create two extra worktrees from the clone
        wt1 = tmp_path / "wt1"
        wt2 = tmp_path / "wt2"
        git("worktree", "add", str(wt1), "-b", "wt-branch-1", cwd=clone)
        git("worktree", "add", str(wt2), "-b", "wt-branch-2", cwd=clone)

        id_bare = compute_repo_id(bare).repo_id
        id_clone = compute_repo_id(clone).repo_id
        id_wt1 = compute_repo_id(wt1).repo_id
        id_wt2 = compute_repo_id(wt2).repo_id

        assert id_bare == id_clone == id_wt1 == id_wt2, (
            f"IDs diverge: bare={id_bare}, clone={id_clone}, wt1={id_wt1}, wt2={id_wt2}"
        )

    def test_tier1_source_label(self, tmp_path):
        """Normal git repo uses git_common_dir source."""
        from mcp_server.storage.repo_identity import compute_repo_id

        _, clone = make_bare_and_clone(tmp_path)
        identity = compute_repo_id(clone)
        assert identity.source == "git_common_dir"
        assert identity.git_common_dir is not None

    def test_tier2_remote_url_fallback(self, tmp_path):
        """When git-common-dir is broken, falls back to remote URL (tier-2)."""
        from mcp_server.storage.repo_identity import compute_repo_id

        bare, clone = make_bare_and_clone(tmp_path)

        # Make a directory that looks like a repo but has a garbage .git file
        broken = tmp_path / "broken"
        broken.mkdir()
        # Set up a git config with a remote origin url but break the .git pointer
        git("init", cwd=broken)
        git("config", "user.email", "test@test.com", cwd=broken)
        git("config", "user.name", "Test", cwd=broken)
        git("remote", "add", "origin", str(bare), cwd=broken)

        # Overwrite the .git dir with a file containing garbage to break tier-1
        import shutil
        shutil.rmtree(str(broken / ".git"))
        (broken / ".git").write_text("garbage - not a valid git dir")

        identity = compute_repo_id(broken)
        assert identity.source == "remote_url", f"Expected remote_url but got {identity.source}"

    def test_tier3_abs_path_fallback(self, tmp_path):
        """Non-git directory falls back to abs-path (tier-3)."""
        from mcp_server.storage.repo_identity import compute_repo_id

        non_git = tmp_path / "not_a_repo"
        non_git.mkdir()

        identity = compute_repo_id(non_git)
        assert identity.source == "abs_path"
        assert identity.git_common_dir is None

    def test_repo_id_format(self, tmp_path):
        """repo_id is a 16-char lowercase hex string."""
        from mcp_server.storage.repo_identity import compute_repo_id

        non_git = tmp_path / "plain"
        non_git.mkdir()
        identity = compute_repo_id(non_git)
        assert len(identity.repo_id) == 16
        assert identity.repo_id == identity.repo_id.lower()
        assert all(c in "0123456789abcdef" for c in identity.repo_id)

    def test_idempotency(self, tmp_path):
        """Three calls return the same result."""
        from mcp_server.storage.repo_identity import compute_repo_id

        _, clone = make_bare_and_clone(tmp_path)
        ids = [compute_repo_id(clone).repo_id for _ in range(3)]
        assert ids[0] == ids[1] == ids[2]


class TestResolveTrackedBranch:
    def test_origin_head_precedence(self, tmp_path):
        """When origin/HEAD is set to a non-default branch, that branch is returned."""
        from mcp_server.storage.repo_identity import resolve_tracked_branch

        bare, clone = make_bare_and_clone(tmp_path)

        # Create and push a custom branch on the bare repo, then set origin/HEAD there
        feature = tmp_path / "feature_clone"
        git("clone", str(bare), str(feature))
        git("config", "user.email", "test@test.com", cwd=feature)
        git("config", "user.name", "Test", cwd=feature)
        git("checkout", "-b", "release/v1", cwd=feature)
        (feature / "file.txt").write_text("x")
        git("add", "file.txt", cwd=feature)
        git("commit", "-m", "release", cwd=feature)
        git("push", "origin", "release/v1", cwd=feature)
        # Set origin/HEAD on the bare repo to release/v1
        git("symbolic-ref", "HEAD", "refs/heads/release/v1", cwd=bare)

        # Refresh remote tracking in clone
        git("remote", "set-head", "origin", "-a", cwd=clone)

        git_common_dir = _get_common_dir(clone)
        branch = resolve_tracked_branch(git_common_dir)
        assert branch == "release/v1", f"Expected release/v1, got {branch}"

    def test_main_fallback_when_no_origin_head(self, tmp_path):
        """Without origin/HEAD, returns 'main' if present."""
        from mcp_server.storage.repo_identity import resolve_tracked_branch

        bare, clone = make_bare_and_clone(tmp_path)

        # Remove origin/HEAD
        git("remote", "set-head", "origin", "--delete", cwd=clone)

        git_common_dir = _get_common_dir(clone)
        branch = resolve_tracked_branch(git_common_dir)
        assert branch == "main", f"Expected main, got {branch}"

    def test_current_head_branch_fallback(self, tmp_path):
        """Without origin/HEAD, main, or master, returns current HEAD branch."""
        from mcp_server.storage.repo_identity import resolve_tracked_branch

        # Create a local-only repo with only a feature branch
        repo = tmp_path / "lone_repo"
        repo.mkdir()
        git("init", cwd=repo)
        git("config", "user.email", "test@test.com", cwd=repo)
        git("config", "user.name", "Test", cwd=repo)
        git("checkout", "-b", "feature/foo", cwd=repo)
        (repo / "f.txt").write_text("x")
        git("add", "f.txt", cwd=repo)
        git("commit", "-m", "feat", cwd=repo)

        git_common_dir = _get_common_dir(repo)
        branch = resolve_tracked_branch(git_common_dir)
        assert branch == "feature/foo", f"Expected feature/foo, got {branch}"

    def test_none_git_common_dir(self, tmp_path):
        """resolve_tracked_branch with None returns a string (empty or sentinel)."""
        from mcp_server.storage.repo_identity import resolve_tracked_branch

        result = resolve_tracked_branch(None)
        assert isinstance(result, str)


def _get_common_dir(path: Path) -> Path:
    """Helper: return git common dir for a path."""
    result = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=path,
        capture_output=True,
        text=True,
        check=True,
    )
    raw = result.stdout.strip()
    return (path / raw).resolve()
