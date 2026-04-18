from pathlib import Path


class SchemaMismatchError(Exception):
    def __init__(self, expected: str, found: str, index_path: Path):
        self.expected = expected
        self.found = found
        self.index_path = index_path
        super().__init__(str(self))

    def __str__(self) -> str:
        return (
            f"Index schema mismatch at {self.index_path}: "
            f"expected version {self.expected}, found {self.found}. "
            f"Rebuild with: mcp-server stdio --rebuild-on-schema-mismatch "
            f"(or serve --rebuild-on-schema-mismatch). "
            f"See BREAKING-CHANGES.md for migration notes."
        )
