"""
Markdown plugin implementation for comprehensive Markdown document processing.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp_server.document_processing import (
    BaseDocumentPlugin,
    DocumentChunk,
)
from mcp_server.document_processing import DocumentMetadata as BaseDocumentMetadata
from mcp_server.document_processing import (
    DocumentStructure,
    Section,
)
from mcp_server.plugin_base import IndexShard

from .chunk_strategies import MarkdownChunkStrategy
from .document_parser import MarkdownParser
from .frontmatter_parser import FrontmatterParser
from .section_extractor import SectionExtractor

logger = logging.getLogger(__name__)


class MarkdownPlugin(BaseDocumentPlugin):
    """Plugin for indexing and searching Markdown documents."""

    def __init__(self, sqlite_store=None, enable_semantic=True):
        """Initialize the Markdown plugin."""
        # Language configuration for Markdown
        language_config = {
            "name": "markdown",
            "code": "markdown",
            "extensions": [".md", ".markdown", ".mdown", ".mkd", ".mdx"],
            "language": "markdown",
            "description": "Markdown document processor with semantic search",
        }

        super().__init__(language_config, sqlite_store, enable_semantic)

        self.parser = MarkdownParser()
        self.section_extractor = SectionExtractor()
        self.frontmatter_parser = FrontmatterParser()
        self.chunk_strategy = MarkdownChunkStrategy()

    def _get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        return [".md", ".markdown", ".mdown", ".mkd", ".mdx"]

    def chunk_document(self, content: str, file_path: Path) -> List[DocumentChunk]:
        """Override to use Markdown-specific chunking."""
        # Parse frontmatter
        frontmatter, content_without_frontmatter = self.frontmatter_parser.parse(content)

        # Parse Markdown AST
        ast = self.parser.parse(content_without_frontmatter)

        # Extract sections
        sections_data = self.section_extractor.extract(ast, content_without_frontmatter)

        # Create chunks using our strategy
        chunks = self.chunk_strategy.create_chunks(
            content_without_frontmatter, ast, sections_data, str(file_path)
        )

        # Optimize for search
        chunks = self.chunk_strategy.optimize_chunks_for_search(chunks)

        # Cache the chunks
        self._chunk_cache[str(file_path)] = chunks

        return chunks

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Override to handle Markdown-specific indexing."""
        path = Path(path)

        # Extract metadata
        metadata = self.extract_metadata(content, path)

        # Extract structure
        structure = self.extract_structure(content, path)
        self._structure_cache[str(path)] = structure

        # Chunk document
        chunks = self.chunk_document(content, path)

        # Extract symbols from AST
        _, content_without_frontmatter = self.frontmatter_parser.parse(content)
        ast = self.parser.parse(content_without_frontmatter)
        symbols = self._extract_symbols(ast, str(path))

        # Add document as a symbol
        doc_symbol = {
            "symbol": metadata.title or path.stem,
            "kind": "document",
            "signature": f"Document: {metadata.title or path.name}",
            "line": 1,
            "span": [1, len(content.splitlines())],
            "metadata": metadata.__dict__,
        }
        symbols.insert(0, doc_symbol)

        # Add sections as symbols
        for section in structure.sections:
            section_symbol = {
                "symbol": section.heading,
                "kind": "section",
                "signature": section.heading,
                "line": section.start_line,
                "span": [section.start_line, section.end_line],
                "metadata": {
                    "level": section.level,
                    "parent": section.parent.heading if section.parent else None,
                },
            }
            symbols.append(section_symbol)

        # Index with semantic indexer if enabled
        if (
            hasattr(self, "_enable_semantic")
            and self._enable_semantic
            and hasattr(self, "semantic_indexer")
        ):
            self._index_chunks_semantically(str(path), chunks, metadata)

        return {"file": str(path), "symbols": symbols, "language": self.lang}

    def extract_structure(self, content: str, file_path: Path) -> DocumentStructure:
        """Extract document structure (headings, sections, etc)."""
        # Parse frontmatter
        frontmatter, content_without_frontmatter = self.frontmatter_parser.parse(content)

        # Parse Markdown AST
        ast = self.parser.parse(content_without_frontmatter)

        # Extract sections hierarchically
        sections_data = self.section_extractor.extract(ast, content_without_frontmatter)

        # Convert to Section objects (flatten the hierarchy)
        flat_sections_data = self.section_extractor.get_all_sections_flat(sections_data)
        sections = []
        for section_data in flat_sections_data:
            section = Section(
                id=section_data["id"],
                heading=section_data["title"],
                level=section_data["level"],
                content=section_data["content"],
                start_line=section_data["start_line"],
                end_line=section_data.get("end_line", section_data["start_line"]),
            )
            sections.append(section)

        # Extract headings and metadata
        _ = self._extract_structure(ast)

        # Build document structure
        structure = DocumentStructure(
            title=frontmatter.get("title", self._extract_title(ast)),
            sections=sections,
            metadata=frontmatter,
            outline=sections[0] if sections else None,  # Use first section as root
        )

        return structure

    def extract_metadata(self, content: str, file_path: Path) -> BaseDocumentMetadata:
        """Extract document metadata."""
        # Parse frontmatter
        frontmatter, _ = self.frontmatter_parser.parse(content)

        # Parse AST to get title if not in frontmatter
        if not frontmatter.get("title"):
            ast = self.parser.parse(content)
            frontmatter["title"] = self._extract_title(ast)

        # Create metadata object
        # Handle both 'author' and 'authors' fields
        author = frontmatter.get("author")
        if not author and "authors" in frontmatter:
            authors = frontmatter["authors"]
            author = authors[0] if authors else None

        metadata = BaseDocumentMetadata(
            title=frontmatter.get("title", file_path.stem),
            author=author,
            created_date=frontmatter.get("date"),
            modified_date=frontmatter.get("updated"),
            document_type="markdown",
            language=frontmatter.get("language", "en"),
            tags=frontmatter.get("tags", []),
            custom=frontmatter,
        )

        return metadata

    def parse_content(self, content: str, file_path: Path) -> str:
        """Parse raw content to plain text."""
        # Remove frontmatter
        _, content_without_frontmatter = self.frontmatter_parser.parse(content)

        # Parse AST
        ast = self.parser.parse(content_without_frontmatter)

        # Convert to plain text
        plain_text = self._ast_to_plain_text(ast)

        return plain_text

    def _ast_to_plain_text(self, ast: Dict[str, Any]) -> str:
        """Convert AST to plain text."""
        text_parts = []

        def traverse(node: Dict[str, Any]):
            node_type = node.get("type", "")

            if node_type == "text":
                text_parts.append(node.get("value", ""))
            elif node_type == "inlineCode":
                text_parts.append(node.get("value", ""))
            elif node_type == "code":
                text_parts.append(node.get("value", ""))
            elif node_type == "thematicBreak":
                text_parts.append("\n---\n")

            # Traverse children
            for child in node.get("children", []):
                traverse(child)

            # Add spacing after blocks
            if node_type in [
                "paragraph",
                "heading",
                "list",
                "blockquote",
                "code",
                "table",
            ]:
                text_parts.append("\n\n")

        traverse(ast)

        # Join and clean up
        text = "".join(text_parts)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _build_outline(self, sections: List[Section]) -> List[Dict[str, Any]]:
        """Build hierarchical outline from sections."""
        outline = []

        for section in sections:
            outline_entry = {
                "id": section.id,
                "title": section.heading,
                "level": section.level,
                "children": [],
            }
            outline.append(outline_entry)

        return outline

    def _extract_structure(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """Extract document structure from AST."""
        structure = {
            "headings": [],
            "lists": [],
            "code_blocks": [],
            "tables": [],
            "links": [],
            "images": [],
        }

        def traverse(node: Dict[str, Any], depth: int = 0):
            node_type = node.get("type", "")

            if node_type == "heading":
                structure["headings"].append(
                    {
                        "level": node.get("depth", 1),
                        "text": self._extract_text(node),
                        "depth": depth,
                    }
                )
            elif node_type == "list":
                structure["lists"].append(
                    {
                        "ordered": node.get("ordered", False),
                        "items": len(node.get("children", [])),
                        "depth": depth,
                    }
                )
            elif node_type == "code":
                structure["code_blocks"].append(
                    {
                        "lang": node.get("lang", ""),
                        "value": node.get("value", ""),
                        "depth": depth,
                    }
                )
            elif node_type == "table":
                structure["tables"].append({"rows": len(node.get("children", [])), "depth": depth})
            elif node_type == "link":
                structure["links"].append(
                    {
                        "url": node.get("url", ""),
                        "text": self._extract_text(node),
                        "depth": depth,
                    }
                )
            elif node_type == "image":
                structure["images"].append(
                    {
                        "url": node.get("url", ""),
                        "alt": node.get("alt", ""),
                        "depth": depth,
                    }
                )

            # Traverse children
            for child in node.get("children", []):
                traverse(child, depth + 1)

        traverse(ast)
        return structure

    def _extract_symbols(self, ast: Dict[str, Any], file_path: str) -> List[Dict[str, Any]]:
        """Extract symbols from Markdown AST."""
        symbols = []

        def traverse(node: Dict[str, Any], parent_heading: Optional[str] = None):
            node_type = node.get("type", "")

            if node_type == "heading":
                heading_text = self._extract_text(node)
                level = node.get("depth", 1)

                # Create symbol for heading
                symbol = {
                    "symbol": heading_text,
                    "kind": "heading",
                    "line": node.get("position", {}).get("start", {}).get("line", 0),
                    "span": [
                        node.get("position", {}).get("start", {}).get("line", 0),
                        node.get("position", {}).get("end", {}).get("line", 0),
                    ],
                    "metadata": {"level": level, "parent": parent_heading},
                }
                symbols.append(symbol)

                # Update parent heading for children
                if level <= 2:  # Only track h1 and h2 as parents
                    parent_heading = heading_text

            elif node_type == "code":
                lang = node.get("lang", "")
                if lang:
                    # Extract function/class definitions from code blocks
                    code_symbols = self._extract_code_symbols(
                        node.get("value", ""),
                        lang,
                        file_path,
                        node.get("position", {}).get("start", {}).get("line", 0),
                    )
                    symbols.extend(code_symbols)

            # Traverse children
            for child in node.get("children", []):
                traverse(child, parent_heading)

        traverse(ast)
        return symbols

    def _extract_code_symbols(
        self, code: str, lang: str, file_path: str, base_line: int
    ) -> List[Dict[str, Any]]:
        """Extract symbols from code blocks."""
        symbols = []

        # Simple regex patterns for common languages
        patterns = {
            "python": [
                (r"^class\s+(\w+)", "class"),
                (r"^def\s+(\w+)", "function"),
            ],
            "javascript": [
                (r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)", "function"),
                (r"^class\s+(\w+)", "class"),
                (r"^const\s+(\w+)\s*=\s*(?:async\s+)?\(", "function"),
            ],
            "typescript": [
                (r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)", "function"),
                (r"^(?:export\s+)?class\s+(\w+)", "class"),
                (r"^(?:export\s+)?interface\s+(\w+)", "interface"),
                (r"^(?:export\s+)?type\s+(\w+)", "type"),
            ],
            "java": [
                (r"^(?:public\s+)?class\s+(\w+)", "class"),
                (
                    r"^(?:public\s+|private\s+|protected\s+)?(?:static\s+)?\w+\s+(\w+)\s*\(",
                    "method",
                ),
            ],
            "go": [
                (r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)", "function"),
                (r"^type\s+(\w+)\s+struct", "struct"),
                (r"^type\s+(\w+)\s+interface", "interface"),
            ],
        }

        if lang in patterns:
            lines = code.split("\n")
            for i, line in enumerate(lines):
                for pattern, kind in patterns[lang]:
                    match = re.match(pattern, line.strip())
                    if match:
                        symbol = {
                            "symbol": match.group(1),
                            "kind": kind,
                            "line": base_line + i,
                            "span": [base_line + i, base_line + i],
                            "metadata": {"language": lang, "in_code_block": True},
                        }
                        symbols.append(symbol)

        return symbols

    def _extract_text(self, node: Dict[str, Any]) -> str:
        """Extract text content from an AST node."""
        if node.get("type") == "text":
            return node.get("value", "")

        text_parts = []
        for child in node.get("children", []):
            text_parts.append(self._extract_text(child))

        return " ".join(text_parts).strip()

    def _extract_title(self, ast: Dict[str, Any]) -> str:
        """Extract the document title (first H1 heading)."""

        def find_first_h1(node: Dict[str, Any]) -> Optional[str]:
            if node.get("type") == "heading" and node.get("depth") == 1:
                return self._extract_text(node)

            for child in node.get("children", []):
                title = find_first_h1(child)
                if title:
                    return title

            return None

        return find_first_h1(ast) or "Untitled"

    def _extract_description(self, content: str) -> str:
        """Extract a description from the document content."""
        # Get first paragraph that's not a heading
        lines = content.split("\n")
        description_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                if description_lines:
                    break
                continue

            # Skip headings and special elements
            if line.startswith("#") or line.startswith("```") or line.startswith("|"):
                continue

            description_lines.append(line)
            if len(" ".join(description_lines)) > 150:
                break

        description = " ".join(description_lines)
        if len(description) > 200:
            description = description[:197] + "..."

        return description

    def _calculate_reading_time(self, content: str) -> int:
        """Calculate estimated reading time in minutes."""
        words = len(content.split())
        # Average reading speed: 200-250 words per minute
        return max(1, round(words / 225))

    def _extract_search_context(self, query: str) -> Dict[str, Any]:
        """Extract search context from query."""
        context = {"headings": [], "code_languages": [], "tags": []}

        # Extract heading references (e.g., "in section X")
        heading_match = re.search(r'in\s+section\s+"([^"]+)"', query, re.IGNORECASE)
        if heading_match:
            context["headings"].append(heading_match.group(1))

        # Extract code language references
        lang_patterns = [
            r"\b(python|javascript|typescript|java|go|rust|c\+\+|c#|swift)\b",
            r"```(\w+)",
        ]
        for pattern in lang_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            context["code_languages"].extend(matches)

        # Extract tag references
        tag_match = re.findall(r"#(\w+)", query)
        context["tags"].extend(tag_match)

        return context

    def _build_search_filters(
        self, context: Dict[str, Any], kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build search filters based on context."""
        filters = {}

        if context["headings"]:
            filters["headings"] = context["headings"]

        if context["code_languages"]:
            filters["languages"] = context["code_languages"]

        if context["tags"]:
            filters["tags"] = context["tags"]

        # Add any additional filters from kwargs
        filters.update(kwargs.get("filters", {}))

        return filters
