# Save this as scaffold_code.py and run it inside your Codespace
import os

BASE = "mcp_server"

plugin_base = f"""{BASE}/plugin_base.py"""
dispatcher = f"""{BASE}/dispatcher.py"""
gateway = f"""{BASE}/gateway.py"""
watcher = f"""{BASE}/watcher.py"""
sync = f"""{BASE}/sync.py"""
treesitter = f"""{BASE}/utils/treesitter_wrapper.py"""

plugins = ["python", "dart", "js", "c", "cpp", "html_css"]

os.makedirs(f"{BASE}/utils", exist_ok=True)

with open(plugin_base, "w") as f:
    f.write('''from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypedDict, Iterable
from pathlib import Path

class IndexShard(TypedDict):
    file: str
    symbols: list[dict]
    language: str

@dataclass(frozen=True)
class Reference:
    file: str
    line: int

class SymbolDef(TypedDict):
    symbol: str
    kind: str
    language: str
    signature: str
    doc: str | None
    defined_in: str
    line: int
    span: tuple[int, int]

class SearchResult(TypedDict):
    file: str
    line: int
    snippet: str

class SearchOpts(TypedDict, total=False):
    semantic: bool
    limit: int

class IPlugin(ABC):
    lang: str

    @abstractmethod
    def supports(self, path: str | Path) -> bool: ...
    
    @abstractmethod
    def indexFile(self, path: str | Path, content: str) -> IndexShard: ...
    
    @abstractmethod
    def getDefinition(self, symbol: str) -> SymbolDef | None: ...
    
    @abstractmethod
    def findReferences(self, symbol: str) -> Iterable[Reference]: ...
    
    @abstractmethod
    def search(self, query: str, opts: SearchOpts | None = None) -> Iterable[SearchResult]: ...
''')

with open(dispatcher, "w") as f:
    f.write('''from pathlib import Path
from typing import Iterable
from .plugin_base import IPlugin, SymbolDef, SearchResult

class Dispatcher:
    def __init__(self, plugins: list[IPlugin]):
        self._plugins = plugins
        self._by_lang = {p.lang: p for p in plugins}

    def _match_plugin(self, path: Path) -> IPlugin:
        for p in self._plugins:
            if p.supports(path):
                return p
        raise RuntimeError(f"No plugin for {path}")

    def lookup(self, symbol: str) -> SymbolDef | None:
        for p in self._plugins:
            res = p.getDefinition(symbol)
            if res:
                return res
        return None

    def search(self, query: str, semantic=False, limit=20) -> Iterable[SearchResult]:
        opts = {"semantic": semantic, "limit": limit}
        for p in self._plugins:
            yield from p.search(query, opts)
''')

with open(gateway, "w") as f:
    f.write('''from fastapi import FastAPI, HTTPException
from .dispatcher import Dispatcher
from .plugin_base import SymbolDef, SearchResult

app = FastAPI(title="MCP Server")
dispatcher: Dispatcher | None = None

@app.get("/symbol", response_model=SymbolDef | None)
def symbol(symbol: str):
    if dispatcher is None:
        raise HTTPException(503, "Dispatcher not ready")
    return dispatcher.lookup(symbol)

@app.get("/search", response_model=list[SearchResult])
def search(q: str, semantic: bool = False, limit: int = 20):
    if dispatcher is None:
        raise HTTPException(503, "Dispatcher not ready")
    return list(dispatcher.search(q, semantic=semantic, limit=limit))
''')

with open(watcher, "w") as f:
    f.write('''from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .dispatcher import Dispatcher

class _Handler(FileSystemEventHandler):
    def __init__(self, dispatcher: Dispatcher):
        self.dispatcher = dispatcher

    def on_modified(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        # TODO: dispatcher._match_plugin(path).indexFile(path.read_text())

class FileWatcher:
    def __init__(self, root: Path, dispatcher: Dispatcher):
        self._observer = Observer()
        self._observer.schedule(_Handler(dispatcher), str(root), recursive=True)

    def start(self): self._observer.start()
    def stop(self): self._observer.stop()
''')

with open(sync, "w") as f:
    f.write('''class CloudSync:
    def push_shard(self, shard_id: str): ...
    def pull_shard(self, shard_id: str): ...
''')

with open(treesitter, "w") as f:
    f.write('''"""Thin wrapper for Tree-sitter (stub)."""
class TreeSitterWrapper:
    def parse_file(self, path):
        ...
''')

# Plugins
for lang in plugins:
    dir_path = f"{BASE}/plugins/{lang}_plugin"
    os.makedirs(dir_path, exist_ok=True)
    with open(f"{dir_path}/plugin.py", "w") as f:
        f.write(f'''from pathlib import Path
from ...plugin_base import IPlugin, IndexShard, SymbolDef, Reference, SearchResult, SearchOpts

class Plugin(IPlugin):
    lang = "{lang}"

    def supports(self, path: str | Path) -> bool:
        """Return True if file extension matches plugin."""
        ...

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Parse the file and return an index shard."""
        ...

    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Return the definition of a symbol, if known."""
        ...

    def findReferences(self, symbol: str) -> list[Reference]:
        """List all references to a symbol."""
        ...

    def search(self, query: str, opts: SearchOpts | None = None) -> list[SearchResult]:
        """Search for code snippets matching a query."""
        ...
''')

print("✅ Code scaffold complete. You can now commit your work.")