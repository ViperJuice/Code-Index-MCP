import pathlib
import re

ARCH_PATH = pathlib.Path(__file__).parents[2] / "specs" / "active" / "architecture.md"


def _mermaid_bodies(text: str) -> str:
    """Concatenate bodies of all ```mermaid ... ``` blocks."""
    return "\n".join(re.findall(r"```mermaid\s*(.*?)```", text, re.DOTALL))


def test_architecture_c4_nodes():
    text = ARCH_PATH.read_text()
    bodies = _mermaid_bodies(text)
    for node in [
        "RepoContext",
        "StoreRegistry",
        "RepositoryRegistry",
        "MultiRepositoryWatcher",
        "RefPoller",
        "HandshakeGate",
    ]:
        assert node in bodies, f"Mermaid diagrams missing node: {node}"


def test_architecture_sandbox_and_caveat():
    text = ARCH_PATH.read_text()
    assert "path_outside_allowed_roots" in text, "Missing sandbox error code"
    lower = text.lower()
    assert "enhanceddispatcher" in lower, "Missing EnhancedDispatcher in dependability caveat"
    assert "tree-sitter" in lower, "Missing tree-sitter in dependability caveat"
