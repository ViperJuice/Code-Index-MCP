import subprocess
from pathlib import Path

from mcp_server import open_client
from tests.fixtures.multi_repo import boot_test_server, build_temp_repo


def test_direct_client_reindex_and_status_work_for_registered_repo(tmp_path: Path):
    token = "pyclient_reindex_token"
    symbol = "pyclient_reindexed_symbol"
    repo_path, _ = build_temp_repo(
        tmp_path,
        "pyclient_index_repo",
        seed_files={"seed.py": "def seed():\n    return 'seed'\n"},
    )
    new_file = repo_path / "fresh.py"
    new_file.write_text(f"def {symbol}():\n    return '{token}'\n", encoding="utf-8")

    with boot_test_server(tmp_path, [repo_path]):
        with open_client(
            workspace_root=repo_path, registry_path=tmp_path / "registry.json"
        ) as client:
            reindex = client.reindex(repository=repo_path)
            status = client.get_status(repository=repo_path)
            lookup = client.symbol_lookup(symbol, repository=repo_path)

    assert reindex.mutation_performed is True
    assert reindex.indexed_files is not None
    assert status.index_unavailable is None
    assert status.readiness["state"] == "ready"
    assert lookup.found is True
    assert lookup.defined_in is not None and lookup.defined_in.endswith("fresh.py")


def test_direct_client_returns_typed_index_unavailable_for_non_ready_repo(tmp_path: Path):
    repo_path, _ = build_temp_repo(
        tmp_path,
        "pyclient_stale_repo",
        seed_files={"seed.py": "def stale_demo():\n    return 'stale'\n"},
    )
    with boot_test_server(tmp_path, [repo_path]):
        (repo_path / "post_index_change.py").write_text(
            "def changed():\n    return 'changed'\n", encoding="utf-8"
        )
        subprocess.run(["git", "add", "post_index_change.py"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "advance head for stale readiness"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        with open_client(
            workspace_root=repo_path, registry_path=tmp_path / "registry.json"
        ) as client:
            status = client.get_status(repository=repo_path)

    assert status.index_unavailable is not None
    assert status.index_unavailable.safe_fallback == "native_search"
    assert status.readiness["state"] == "stale_commit"
