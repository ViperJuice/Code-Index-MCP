"""
Section extractor for hierarchical document structure extraction.
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SectionExtractor:
    """Extract hierarchical sections from Markdown documents."""

    def __init__(self):
        """Initialize the section extractor."""
        self.heading_levels = ["h1", "h2", "h3", "h4", "h5", "h6"]

    def extract(self, ast: Dict[str, Any], content: str) -> List[Dict[str, Any]]:
        """Extract sections from the AST."""
        sections = []
        current_section_stack = []
        content_lines = content.split("\n")

        for node in ast.get("children", []):
            if node.get("type") == "heading":
                # Process heading
                level = node.get("depth", 1)
                title = self._extract_text(node)
                start_line = node.get("position", {}).get("start", {}).get("line", 1) - 1

                # Create section object
                section = {
                    "id": self._generate_section_id(title),
                    "title": title,
                    "level": level,
                    "start_line": start_line,
                    "content": "",
                    "subsections": [],
                    "metadata": {
                        "word_count": 0,
                        "code_blocks": 0,
                        "links": 0,
                        "images": 0,
                    },
                }

                # Update section hierarchy
                while current_section_stack and current_section_stack[-1]["level"] >= level:
                    # Close previous sections at same or higher level
                    closed_section = current_section_stack.pop()
                    self._finalize_section(closed_section, content_lines)

                    if current_section_stack:
                        current_section_stack[-1]["subsections"].append(closed_section)
                    else:
                        sections.append(closed_section)

                # Add new section to stack
                current_section_stack.append(section)

            elif current_section_stack:
                # Add content to current section
                self._add_content_to_section(current_section_stack[-1], node)

        # Close remaining sections
        while current_section_stack:
            closed_section = current_section_stack.pop()
            self._finalize_section(closed_section, content_lines)

            if current_section_stack:
                current_section_stack[-1]["subsections"].append(closed_section)
            else:
                sections.append(closed_section)

        return sections

    def extract_flat(self, ast: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract a flat list of sections without hierarchy."""
        sections = []

        for node in ast.get("children", []):
            if node.get("type") == "heading":
                level = node.get("depth", 1)
                title = self._extract_text(node)

                section = {
                    "id": self._generate_section_id(title),
                    "title": title,
                    "level": level,
                    "type": f"h{level}",
                    "position": node.get("position", {}),
                }
                sections.append(section)

        return sections

    def get_all_sections_flat(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get all sections in a flat list, including nested ones."""
        flat_sections = []

        def flatten(section_list):
            for section in section_list:
                flat_sections.append(section)
                if section.get("subsections"):
                    flatten(section["subsections"])

        flatten(sections)
        return flat_sections

    def find_section_by_heading(
        self, sections: List[Dict[str, Any]], heading: str
    ) -> Optional[Dict[str, Any]]:
        """Find a section by its heading text."""
        heading_lower = heading.lower()

        def search_sections(
            section_list: List[Dict[str, Any]],
        ) -> Optional[Dict[str, Any]]:
            for section in section_list:
                if section["title"].lower() == heading_lower:
                    return section

                # Search subsections
                found = search_sections(section.get("subsections", []))
                if found:
                    return found

            return None

        return search_sections(sections)

    def get_section_path(self, sections: List[Dict[str, Any]], target_id: str) -> List[str]:
        """Get the path to a section (list of parent section titles)."""
        _ = []

        def find_path(
            section_list: List[Dict[str, Any]], current_path: List[str]
        ) -> Optional[List[str]]:
            for section in section_list:
                new_path = current_path + [section["title"]]

                if section["id"] == target_id:
                    return new_path

                # Search subsections
                found = find_path(section.get("subsections", []), new_path)
                if found:
                    return found

            return None

        result = find_path(sections, [])
        return result or []

    def get_table_of_contents(
        self, sections: List[Dict[str, Any]], max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """Generate a table of contents from sections."""
        toc = []

        def process_sections(section_list: List[Dict[str, Any]], depth: int = 1):
            for section in section_list:
                if depth <= max_depth:
                    toc_entry = {
                        "id": section["id"],
                        "title": section["title"],
                        "level": section["level"],
                        "depth": depth,
                    }
                    toc.append(toc_entry)

                    # Process subsections
                    if section.get("subsections"):
                        process_sections(section["subsections"], depth + 1)

        process_sections(sections)
        return toc

    def get_section_content(self, section: Dict[str, Any], include_subsections: bool = True) -> str:
        """Get the full content of a section."""
        content_parts = [section.get("content", "")]

        if include_subsections:
            for subsection in section.get("subsections", []):
                subsection_content = self.get_section_content(subsection, True)
                if subsection_content:
                    content_parts.append(subsection_content)

        return "\n\n".join(filter(None, content_parts))

    def _extract_text(self, node: Dict[str, Any]) -> str:
        """Extract text content from an AST node."""
        if node.get("type") == "text":
            return node.get("value", "")

        text_parts = []
        for child in node.get("children", []):
            text_parts.append(self._extract_text(child))

        return " ".join(text_parts).strip()

    def _generate_section_id(self, title: str) -> str:
        """Generate a URL-friendly section ID from title."""
        # Convert to lowercase
        id_str = title.lower()

        # Replace spaces and special characters with hyphens
        id_str = re.sub(r"[^\w\s-]", "", id_str)
        id_str = re.sub(r"[-\s]+", "-", id_str)

        # Remove leading/trailing hyphens
        id_str = id_str.strip("-")

        return id_str

    def _add_content_to_section(self, section: Dict[str, Any], node: Dict[str, Any]):
        """Add content metadata to a section."""
        node_type = node.get("type", "")

        if node_type == "code":
            section["metadata"]["code_blocks"] += 1
        elif node_type == "paragraph":
            # Count words
            text = self._extract_text(node)
            section["metadata"]["word_count"] += len(text.split())

            # Count links and images
            self._count_inline_elements(node, section["metadata"])
        elif node_type == "list":
            # Count words in list items
            for item in node.get("children", []):
                text = self._extract_text(item)
                section["metadata"]["word_count"] += len(text.split())
                self._count_inline_elements(item, section["metadata"])

    def _count_inline_elements(self, node: Dict[str, Any], metadata: Dict[str, Any]):
        """Count inline elements in a node."""
        if node.get("type") == "link":
            metadata["links"] += 1
        elif node.get("type") == "image":
            metadata["images"] += 1

        for child in node.get("children", []):
            self._count_inline_elements(child, metadata)

    def _finalize_section(self, section: Dict[str, Any], content_lines: List[str]):
        """Finalize a section by extracting its content."""
        start_line = section["start_line"]

        # Find the end line (start of next section at same or higher level)
        end_line = len(content_lines)

        # Extract content lines (excluding the heading itself)
        if start_line + 1 < end_line:
            section_lines = content_lines[start_line + 1 : end_line]

            # Remove empty lines at start and end
            while section_lines and not section_lines[0].strip():
                section_lines.pop(0)
            while section_lines and not section_lines[-1].strip():
                section_lines.pop()

            section["content"] = "\n".join(section_lines)

    def merge_sections(
        self, sections1: List[Dict[str, Any]], sections2: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge two lists of sections, avoiding duplicates."""
        merged = sections1.copy()
        existing_ids = {s["id"] for s in sections1}

        for section in sections2:
            if section["id"] not in existing_ids:
                merged.append(section)

        return merged
