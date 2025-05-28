from abc import ABC, abstractmethod
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
