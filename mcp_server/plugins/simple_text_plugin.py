"""Simple text plugin for indexing configuration and other text files."""

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from ..plugin_base import IndexShard, IPlugin, Reference, SearchResult, SymbolDef

logger = logging.getLogger(__name__)


class SimpleTextPlugin(IPlugin):
    """Simple plugin for indexing text files including configs and secrets."""

    def __init__(self, sqlite_store=None):
        """Initialize simple text plugin."""
        self.lang = "plaintext"
        self._sqlite_store = sqlite_store
        self._repository_id = 1  # Default repository ID

        # Extensions we support
        self.extensions = {
            ".txt",
            ".text",
            ".log",
            ".env",
            ".key",
            ".pem",
            ".crt",
            ".cer",
            ".pfx",
            ".p12",
            ".pub",
            ".pri",
            ".license",
            ".version",
            ".gitignore",
            ".dockerignore",
            ".npmignore",
            ".conf",
            ".cfg",
            ".ini",
            ".properties",
            ".sh",
            ".bash",
            ".zsh",
        }

        # Filenames without extensions
        self.exact_filenames = {
            "Dockerfile",
            "Makefile",
            "Procfile",
            "Gemfile",
            "Rakefile",
            "LICENSE",
            "README",
            "CHANGELOG",
            "TODO",
            "AUTHORS",
            ".env",
            ".env.local",
            ".env.production",
            ".env.development",
        }

    def supports(self, path: Path) -> bool:
        """Check if this plugin supports the given file."""
        # Check extensions
        if path.suffix.lower() in self.extensions:
            return True

        # Check exact filenames
        if path.name in self.exact_filenames:
            return True

        # Check patterns
        name_lower = path.name.lower()
        patterns = ["dockerfile", "makefile", ".env", "readme", "license"]
        if any(pattern in name_lower for pattern in patterns):
            return True

        return False

    def indexFile(self, path: Path, content: str) -> IndexShard:
        """Index a text file."""
        logger.info(f"Indexing text file: {path}")

        # Create basic shard as a dict (expected by dispatcher)
        shard = {
            "file": str(path),
            "language": "plaintext",
            "doc": f"Plain text file: {path.name}",
            "symbols": [],
            "content": content,
        }

        # For .env files, extract variables as symbols
        if ".env" in path.name:
            lines = content.splitlines()
            for i, line in enumerate(lines):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key = line.split("=", 1)[0].strip()
                    if key:
                        symbol = {
                            "name": key,
                            "kind": "variable",
                            "signature": line,
                            "doc": f"Environment variable in {path.name}",
                            "defined_in": str(path),
                            "line": i + 1,
                            "span": (i + 1, i + 1),
                        }
                        shard["symbols"].append(symbol)

        # Store in SQLite if available
        if self._sqlite_store:
            try:
                file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                file_id = self._sqlite_store.store_file(
                    self._repository_id,
                    str(path),
                    str(path.relative_to(Path.cwd()) if path.is_absolute() else path),
                    language="plaintext",
                    size=len(content),
                    hash=file_hash,
                )

                # Store symbols
                for symbol in shard["symbols"]:
                    self._sqlite_store.store_symbol(
                        file_id,
                        symbol["name"],
                        symbol["kind"],
                        line_start=symbol["line"],
                        line_end=symbol["line"],
                        column_start=0,
                        column_end=None,
                        signature=symbol.get("signature", ""),
                        documentation=symbol.get("doc", ""),
                    )

            except Exception as e:
                logger.error(f"Failed to store {path} in SQLite: {e}")

        return shard

    def getDefinition(self, symbol: str) -> Optional[SymbolDef]:
        """Get definition of a symbol."""
        if not self._sqlite_store:
            return None

        try:
            result = self._sqlite_store.get_definition(symbol, "plaintext")
            if result:
                return SymbolDef(
                    name=result["symbol"],
                    kind=result.get("kind", "variable"),
                    signature=result.get("signature", symbol),
                    doc=result.get("doc", ""),
                    defined_in=result["defined_in"],
                    line=result.get("line", 1),
                    span=(result.get("line", 1), result.get("line", 1)),
                )
        except Exception as e:
            logger.error(f"Error getting definition for {symbol}: {e}")

        return None

    def search(self, query: str, opts: Dict[str, Any] = None) -> Iterable[SearchResult]:
        """Search for text in files."""
        if not self._sqlite_store:
            return []

        opts = opts or {}
        limit = opts.get("limit", 20)

        try:
            results = self._sqlite_store.search(query, "plaintext", limit)
            for result in results:
                yield SearchResult(
                    file=result["file"],
                    line=result["line"],
                    snippet=result["snippet"],
                    score=result.get("score", 0.5),
                    kind=result.get("kind", "text"),
                )
        except Exception as e:
            logger.error(f"Error searching for {query}: {e}")
            return []

    def findReferences(self, symbol: str) -> Iterable[Reference]:
        """Find references to a symbol."""
        # For text files, we can search for the symbol as text
        if not self._sqlite_store:
            return []

        try:
            results = self._sqlite_store.search(symbol, "plaintext", 50)
            for result in results:
                yield Reference(
                    file=result["file"],
                    line=result["line"],
                    span=(result["line"], result["line"]),
                    kind="text",
                )
        except Exception as e:
            logger.error(f"Error finding references for {symbol}: {e}")
            return []
