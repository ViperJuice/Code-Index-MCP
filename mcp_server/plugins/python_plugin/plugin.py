from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import jedi

from ...plugin_base import (
    IndexShard,
    IPlugin,
    Reference,
    SearchOpts,
    SearchResult,
    SymbolDef,
)
from ...storage.sqlite_store import SQLiteStore
from ...storage.relationship_tracker import RelationshipTracker, RelationshipType
from ...utils.fuzzy_indexer import FuzzyIndexer
from ...utils.treesitter_wrapper import TreeSitterWrapper


class Plugin(IPlugin):
    lang = "python"

    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        self._ts = TreeSitterWrapper()
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None
        self._relationship_tracker = None

        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            self._repository_id = self._sqlite_store.create_repository(
                str(Path.cwd()), Path.cwd().name, {"language": "python"}
            )
            # Initialize relationship tracker
            self._relationship_tracker = RelationshipTracker(sqlite_store)

        self._preindex()

    # ------------------------------------------------------------------
    def _preindex(self) -> None:
        for path in Path(".").rglob("*.py"):
            try:
                text = path.read_text()
                self._indexer.add_file(str(path), text)
            except Exception:
                continue

    # ------------------------------------------------------------------
    def supports(self, path: str | Path) -> bool:
        """Return True if file extension matches plugin."""
        return Path(path).suffix == ".py"

    # ------------------------------------------------------------------
    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        if isinstance(path, str):
            path = Path(path)
        self._indexer.add_file(str(path), content)
        tree = self._ts._parser.parse(content.encode("utf-8"))
        root = tree.root_node

        # Store file in SQLite if available
        file_id = None
        if self._sqlite_store and self._repository_id:
            import hashlib

            file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            # Handle relative path safely
            try:
                relative_path = str(path.relative_to(Path.cwd()))
            except ValueError:
                # If path is not relative to cwd, use the basename
                relative_path = path.name if isinstance(path, Path) else Path(path).name
            
            file_id = self._sqlite_store.store_file(
                self._repository_id,
                str(path),
                relative_path,
                language="python",
                size=len(content),
                hash=file_hash,
            )

        symbols: list[dict] = []
        symbol_map: dict[str, int] = {}  # Map symbol names to their IDs
        
        # First pass: Extract symbols and store them
        for child in root.named_children:
            if child.type not in {"function_definition", "class_definition"}:
                continue

            name_node = child.child_by_field_name("name")
            if name_node is None:
                continue
            name = content[name_node.start_byte : name_node.end_byte]

            start_line = child.start_point[0] + 1
            end_line = child.end_point[0] + 1

            if child.type == "function_definition":
                kind = "function"
                signature = f"def {name}(...):"
            else:
                kind = "class"
                signature = f"class {name}:"

            # Store symbol in SQLite if available
            symbol_id = None
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id, name, kind, start_line, end_line, signature=signature
                )
                symbol_map[name] = symbol_id
                # Add to fuzzy indexer with metadata
                self._indexer.add_symbol(
                    name,
                    str(path),
                    start_line,
                    {"symbol_id": symbol_id, "file_id": file_id},
                )

            symbols.append(
                {
                    "symbol": name,
                    "kind": kind,
                    "signature": signature,
                    "line": start_line,
                    "span": (start_line, end_line),
                    "node": child,  # Keep node for relationship extraction
                    "symbol_id": symbol_id,
                }
            )

        # Second pass: Extract relationships
        if self._relationship_tracker and file_id:
            relationships = []
            
            for sym in symbols:
                node = sym["node"]
                symbol_id = sym["symbol_id"]
                
                if not symbol_id:
                    continue
                
                # Extract call relationships for functions
                if sym["kind"] == "function":
                    calls = self._extract_function_calls(node, content, symbol_map)
                    for callee_id, metadata in calls:
                        relationships.append({
                            "source_entity_id": symbol_id,
                            "target_entity_id": callee_id,
                            "relationship_type": RelationshipType.CALLS,
                            "confidence_score": metadata.get("confidence", 1.0),
                            "metadata": metadata,
                        })
                
                # Extract inheritance relationships for classes
                elif sym["kind"] == "class":
                    bases = self._extract_class_bases(node, content, symbol_map)
                    for base_id, metadata in bases:
                        relationships.append({
                            "source_entity_id": symbol_id,
                            "target_entity_id": base_id,
                            "relationship_type": RelationshipType.INHERITS,
                            "confidence_score": 1.0,
                            "metadata": metadata,
                        })
            
            # Extract import relationships
            import_rels = self._extract_imports(root, content, file_id)
            relationships.extend(import_rels)
            
            # Store all relationships in batch
            if relationships:
                try:
                    self._relationship_tracker.add_relationships_batch(relationships)
                except Exception as e:
                    # Log but don't fail indexing if relationship extraction fails
                    import logging
                    logging.getLogger(__name__).warning(
                        f"Failed to store relationships for {path}: {e}"
                    )

        # Clean up temporary node references
        for sym in symbols:
            sym.pop("node", None)
            sym.pop("symbol_id", None)

        return {"file": str(path), "symbols": symbols, "language": self.lang}

    # ------------------------------------------------------------------
    def getDefinition(self, symbol: str) -> SymbolDef | None:
        for path in Path(".").rglob("*.py"):
            try:
                source = path.read_text()
                script = jedi.Script(code=source, path=str(path))
                names = script.get_names(all_scopes=True, definitions=True, references=False)
                for name in names:
                    if name.name == symbol and name.type in ("function", "class"):
                        defs = name.goto()
                        if defs:
                            d = defs[0]
                            return {
                                "symbol": d.name,
                                "kind": d.type,
                                "language": self.lang,
                                "signature": d.get_line_code().strip(),
                                "doc": d.docstring(raw=True),
                                "defined_in": str(path),
                                "line": d.line,
                                "span": (d.line, d.line + 3),
                            }
            except Exception:
                continue
        return None

    # ------------------------------------------------------------------
    def findReferences(self, symbol: str) -> list[Reference]:
        refs: list[Reference] = []
        seen: set[tuple[str, int]] = set()
        for path in Path(".").rglob("*.py"):
            try:
                source = path.read_text()
                script = jedi.Script(code=source, path=str(path))
                for r in script.get_references():
                    if r.name == symbol:
                        key = (str(path), r.line)
                        if key not in seen:
                            refs.append(Reference(file=str(path), line=r.line))
                            seen.add(key)
            except Exception:
                continue
        return refs

    # ------------------------------------------------------------------
    def search(self, query: str, opts: SearchOpts | None = None) -> Iterable[SearchResult]:
        limit = 20
        if opts and "limit" in opts:
            limit = opts["limit"]
        if opts and opts.get("semantic"):
            return []
        return self._indexer.search(query, limit=limit)

    # ------------------------------------------------------------------
    def get_indexed_count(self) -> int:
        """Return the number of indexed files."""
        # The fuzzy indexer tracks files internally
        if hasattr(self._indexer, "index"):
            return len(self._indexer.index)
        return 0

    # ------------------------------------------------------------------
    # Relationship extraction methods
    # ------------------------------------------------------------------
    
    def _extract_function_calls(self, func_node, content: str, symbol_map: dict) -> list[tuple[int, dict]]:
        """
        Extract function calls from a function body.
        
        Returns list of (callee_symbol_id, metadata) tuples.
        """
        calls = []
        
        # Find all call expressions in the function body
        body_node = func_node.child_by_field_name("body")
        if not body_node:
            return calls
        
        def visit_calls(node):
            if node.type == "call":
                # Get the function being called
                func_expr = node.child_by_field_name("function")
                if func_expr:
                    # Extract the callee name
                    callee_name = content[func_expr.start_byte : func_expr.end_byte]
                    
                    # Handle method calls (obj.method())
                    if "." in callee_name:
                        callee_name = callee_name.split(".")[-1]
                    
                    # Check if we have this symbol
                    if callee_name in symbol_map:
                        callee_id = symbol_map[callee_name]
                        metadata = {
                            "line": node.start_point[0] + 1,
                            "call_type": "direct",
                            "confidence": 1.0,
                        }
                        calls.append((callee_id, metadata))
            
            # Recurse into children
            for child in node.children:
                visit_calls(child)
        
        visit_calls(body_node)
        return calls
    
    def _extract_class_bases(self, class_node, content: str, symbol_map: dict) -> list[tuple[int, dict]]:
        """
        Extract base classes from a class definition.
        
        Returns list of (base_symbol_id, metadata) tuples.
        """
        bases = []
        
        # Find the argument_list node which contains base classes
        for child in class_node.children:
            if child.type == "argument_list":
                for arg in child.named_children:
                    base_name = content[arg.start_byte : arg.end_byte]
                    
                    # Handle qualified names (module.Class)
                    if "." in base_name:
                        base_name = base_name.split(".")[-1]
                    
                    # Check if we have this symbol
                    if base_name in symbol_map:
                        base_id = symbol_map[base_name]
                        metadata = {
                            "line": class_node.start_point[0] + 1,
                            "inheritance_type": "direct",
                        }
                        bases.append((base_id, metadata))
        
        return bases
    
    def _extract_imports(self, root_node, content: str, file_id: int) -> list[dict]:
        """
        Extract import statements from the module.
        
        Returns list of relationship dicts.
        """
        # Note: Import relationships would link to modules, not symbols within this file
        # For now, we skip this as it requires resolving module paths to file_ids
        # This could be added in a future enhancement
        return []
