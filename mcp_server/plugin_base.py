from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable

from typing_extensions import TypedDict


class IndexShard(TypedDict):
    file: str
    symbols: list[dict]
    language: str


class Reference:
    """A reference to a symbol occurrence in a file."""

    __slots__ = ("file", "start_line", "end_line")

    def __init__(
        self,
        file: str,
        start_line: int = 0,
        end_line: int = 0,
        *,
        line: int | None = None,
    ) -> None:
        object.__setattr__(self, "file", file)
        if line is not None:
            object.__setattr__(self, "start_line", line)
            object.__setattr__(self, "end_line", line)
        else:
            object.__setattr__(self, "start_line", start_line)
            object.__setattr__(self, "end_line", end_line)

    def __setattr__(self, name, value):
        raise AttributeError("Reference is immutable")

    def __eq__(self, other):
        if not isinstance(other, Reference):
            return NotImplemented
        return (
            self.file == other.file
            and self.start_line == other.start_line
            and self.end_line == other.end_line
        )

    def __hash__(self):
        return hash((self.file, self.start_line, self.end_line))

    def __repr__(self):
        return (
            f"Reference(file={self.file!r}, start_line={self.start_line}, end_line={self.end_line})"
        )


class SymbolDef(TypedDict):
    symbol: str
    kind: str
    language: str
    signature: str
    doc: str | None
    defined_in: str
    start_line: int
    end_line: int
    span: tuple[int, int]


class SearchResult(TypedDict):
    file: str
    start_line: int
    end_line: int
    snippet: str


class SearchOpts(TypedDict, total=False):
    semantic: bool
    limit: int


class IPlugin(ABC):
    lang: str

    @property
    def language(self) -> str:
        """Return the language identifier."""
        return self.lang

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
