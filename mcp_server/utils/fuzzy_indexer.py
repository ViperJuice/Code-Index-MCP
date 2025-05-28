class FuzzyIndexer:
    """Simple in-memory index for fuzzy searching source files."""

    def __init__(self) -> None:
        self.index: dict[str, list[tuple[int, str]]] = {}

    # ------------------------------------------------------------------
    def add_file(self, path: str, content: str) -> None:
        """Add a file's contents to the index."""
        lines = [
            (i + 1, line.rstrip())
            for i, line in enumerate(content.splitlines())
        ]
        self.index[path] = lines

    # ------------------------------------------------------------------
    def search(self, query: str, limit: int = 20) -> list[dict]:
        """Return list of matches with basic substring matching."""
        results: list[dict] = []
        seen: set[tuple[str, int]] = set()
        q = query.lower()

        for file, lines in self.index.items():
            for line_no, text in lines:
                if q in text.lower():
                    key = (file, line_no)
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append(
                        {"file": file, "line": line_no, "snippet": text.strip()}
                    )
                    if len(results) >= limit:
                        return results
        return results
