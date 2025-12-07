"""
Markdown document parser for AST extraction and processing.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MarkdownParser:
    """Parser for Markdown documents that creates an AST representation."""

    def __init__(self):
        """Initialize the Markdown parser."""
        self.block_parsers = {
            "heading": self._parse_heading,
            "code_block": self._parse_code_block,
            "list": self._parse_list,
            "blockquote": self._parse_blockquote,
            "table": self._parse_table,
            "horizontal_rule": self._parse_horizontal_rule,
            "paragraph": self._parse_paragraph,
        }

    def parse(self, content: str) -> Dict[str, Any]:
        """Parse Markdown content and return an AST."""
        lines = content.split("\n")
        ast = {
            "type": "root",
            "children": [],
            "position": {"start": {"line": 1}, "end": {"line": len(lines)}},
        }

        i = 0
        while i < len(lines):
            # Skip empty lines
            if not lines[i].strip():
                i += 1
                continue

            # Try to parse as different block types
            parsed = False
            for block_type, parser in self.block_parsers.items():
                result = parser(lines, i)
                if result:
                    node, next_i = result
                    ast["children"].append(node)
                    i = next_i
                    parsed = True
                    break

            if not parsed:
                # Default to paragraph
                node, next_i = self._parse_paragraph(lines, i)
                if node:
                    ast["children"].append(node)
                    i = next_i
                else:
                    i += 1

        return ast

    def _parse_heading(self, lines: List[str], start: int) -> Optional[Tuple[Dict[str, Any], int]]:
        """Parse a heading block."""
        line = lines[start]

        # ATX-style headings
        match = re.match(r"^(#{1,6})\s+(.+?)(?:\s*#*)?$", line)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()

            node = {
                "type": "heading",
                "depth": level,
                "children": [{"type": "text", "value": text}],
                "position": {"start": {"line": start + 1}, "end": {"line": start + 1}},
            }
            return node, start + 1

        # Setext-style headings
        if start + 1 < len(lines):
            next_line = lines[start + 1]
            if re.match(r"^=+\s*$", next_line):
                node = {
                    "type": "heading",
                    "depth": 1,
                    "children": [{"type": "text", "value": line.strip()}],
                    "position": {
                        "start": {"line": start + 1},
                        "end": {"line": start + 2},
                    },
                }
                return node, start + 2
            elif re.match(r"^-+\s*$", next_line):
                node = {
                    "type": "heading",
                    "depth": 2,
                    "children": [{"type": "text", "value": line.strip()}],
                    "position": {
                        "start": {"line": start + 1},
                        "end": {"line": start + 2},
                    },
                }
                return node, start + 2

        return None

    def _parse_code_block(
        self, lines: List[str], start: int
    ) -> Optional[Tuple[Dict[str, Any], int]]:
        """Parse a code block."""
        line = lines[start]

        # Fenced code blocks
        fence_match = re.match(r"^```(\w*)", line)
        if fence_match:
            lang = fence_match.group(1) or ""
            code_lines = []
            i = start + 1

            while i < len(lines):
                if lines[i].strip() == "```":
                    node = {
                        "type": "code",
                        "lang": lang,
                        "value": "\n".join(code_lines),
                        "position": {
                            "start": {"line": start + 1},
                            "end": {"line": i + 1},
                        },
                    }
                    return node, i + 1
                code_lines.append(lines[i])
                i += 1

        # Indented code blocks
        if line.startswith("    ") or line.startswith("\t"):
            code_lines = []
            i = start

            while i < len(lines) and (
                lines[i].startswith("    ") or lines[i].startswith("\t") or not lines[i].strip()
            ):
                if lines[i].strip():
                    code_lines.append(lines[i][4:] if lines[i].startswith("    ") else lines[i][1:])
                else:
                    code_lines.append("")
                i += 1

            # Remove trailing empty lines
            while code_lines and not code_lines[-1]:
                code_lines.pop()

            if code_lines:
                node = {
                    "type": "code",
                    "lang": "",
                    "value": "\n".join(code_lines),
                    "position": {"start": {"line": start + 1}, "end": {"line": i}},
                }
                return node, i

        return None

    def _parse_list(self, lines: List[str], start: int) -> Optional[Tuple[Dict[str, Any], int]]:
        """Parse a list block."""
        line = lines[start]

        # Check for ordered or unordered list
        ordered_match = re.match(r"^(\d+)\.\s+(.+)", line)
        unordered_match = re.match(r"^([*+-])\s+(.+)", line)

        if ordered_match or unordered_match:
            ordered = bool(ordered_match)
            _ = ordered_match.group(1) if ordered else unordered_match.group(1)

            list_node = {
                "type": "list",
                "ordered": ordered,
                "children": [],
                "position": {"start": {"line": start + 1}},
            }

            i = start
            _ = 0

            while i < len(lines):
                line = lines[i]

                # Check for list item
                if ordered:
                    item_match = re.match(r"^(\d+)\.\s+(.+)", line)
                else:
                    item_match = re.match(r"^([*+-])\s+(.+)", line)

                if item_match:
                    # New list item
                    item_text = item_match.group(2)
                    item_node = {
                        "type": "listItem",
                        "children": [{"type": "text", "value": item_text}],
                        "position": {"start": {"line": i + 1}},
                    }

                    # Check for nested content
                    nested_lines = []
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j]
                        if not next_line.strip():
                            # Empty line might be part of the item
                            nested_lines.append("")
                            j += 1
                        elif next_line.startswith("  ") or next_line.startswith("\t"):
                            # Nested content
                            nested_lines.append(
                                next_line[2:] if next_line.startswith("  ") else next_line[1:]
                            )
                            j += 1
                        else:
                            # Check if it's another list item
                            if (ordered and re.match(r"^\d+\.\s+", next_line)) or (
                                not ordered and re.match(r"^[*+-]\s+", next_line)
                            ):
                                break
                            else:
                                # Not part of this list
                                break

                    if nested_lines:
                        # Parse nested content
                        nested_content = "\n".join(nested_lines).strip()
                        if nested_content:
                            nested_ast = self.parse(nested_content)
                            item_node["children"].extend(nested_ast["children"])

                    item_node["position"]["end"] = {"line": j}
                    list_node["children"].append(item_node)
                    i = j
                else:
                    # End of list
                    break

            list_node["position"]["end"] = {"line": i}
            return list_node, i

        return None

    def _parse_blockquote(
        self, lines: List[str], start: int
    ) -> Optional[Tuple[Dict[str, Any], int]]:
        """Parse a blockquote."""
        line = lines[start]

        if line.startswith(">"):
            quote_lines = []
            i = start

            while i < len(lines) and (
                lines[i].startswith(">") or (quote_lines and not lines[i].strip())
            ):
                if lines[i].startswith(">"):
                    # Remove the > and optional space
                    content = lines[i][1:]
                    if content.startswith(" "):
                        content = content[1:]
                    quote_lines.append(content)
                else:
                    quote_lines.append("")
                i += 1

            # Parse the blockquote content
            quote_content = "\n".join(quote_lines).strip()
            quote_ast = self.parse(quote_content)

            node = {
                "type": "blockquote",
                "children": quote_ast["children"],
                "position": {"start": {"line": start + 1}, "end": {"line": i}},
            }
            return node, i

        return None

    def _parse_table(self, lines: List[str], start: int) -> Optional[Tuple[Dict[str, Any], int]]:
        """Parse a table."""
        if start + 1 < len(lines):
            # Check for table delimiter
            delimiter_match = re.match(
                r"^\|?[\s:]*-+[\s:]*(\|[\s:]*-+[\s:]*)*\|?$", lines[start + 1]
            )
            if delimiter_match and "|" in lines[start]:
                table_node = {
                    "type": "table",
                    "children": [],
                    "position": {"start": {"line": start + 1}},
                }

                # Parse header row
                header_cells = self._parse_table_row(lines[start])
                if header_cells:
                    header_row = {
                        "type": "tableRow",
                        "children": [
                            {
                                "type": "tableCell",
                                "children": [{"type": "text", "value": cell}],
                            }
                            for cell in header_cells
                        ],
                    }
                    table_node["children"].append(header_row)

                # Skip delimiter row
                i = start + 2

                # Parse body rows
                while i < len(lines) and "|" in lines[i]:
                    cells = self._parse_table_row(lines[i])
                    if cells:
                        row = {
                            "type": "tableRow",
                            "children": [
                                {
                                    "type": "tableCell",
                                    "children": [{"type": "text", "value": cell}],
                                }
                                for cell in cells
                            ],
                        }
                        table_node["children"].append(row)
                    i += 1

                table_node["position"]["end"] = {"line": i}
                return table_node, i

        return None

    def _parse_table_row(self, line: str) -> List[str]:
        """Parse a table row into cells."""
        # Remove leading/trailing pipes if present
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]

        # Split by pipe and clean cells
        cells = [cell.strip() for cell in line.split("|")]
        return cells

    def _parse_horizontal_rule(
        self, lines: List[str], start: int
    ) -> Optional[Tuple[Dict[str, Any], int]]:
        """Parse a horizontal rule."""
        line = lines[start].strip()

        # Check for horizontal rule patterns
        if re.match(r"^([-*_])\s*\1\s*\1(\s*\1)*\s*$", line):
            node = {
                "type": "thematicBreak",
                "position": {"start": {"line": start + 1}, "end": {"line": start + 1}},
            }
            return node, start + 1

        return None

    def _parse_paragraph(
        self, lines: List[str], start: int
    ) -> Optional[Tuple[Dict[str, Any], int]]:
        """Parse a paragraph."""
        paragraph_lines = []
        i = start

        while i < len(lines) and lines[i].strip():
            line = lines[i]

            # Check if this line starts a different block type
            if any(
                [
                    re.match(r"^#{1,6}\s+", line),  # Heading
                    re.match(r"^```", line),  # Code block
                    re.match(r"^(\d+\.|-|\*|\+)\s+", line),  # List
                    line.startswith(">"),  # Blockquote
                    re.match(r"^([-*_])\s*\1\s*\1(\s*\1)*\s*$", line.strip()),  # HR
                ]
            ):
                break

            paragraph_lines.append(line)
            i += 1

        if paragraph_lines:
            # Parse inline elements
            text = " ".join(paragraph_lines)
            children = self._parse_inline(text)

            node = {
                "type": "paragraph",
                "children": children,
                "position": {"start": {"line": start + 1}, "end": {"line": i}},
            }
            return node, i

        return None

    def _parse_inline(self, text: str) -> List[Dict[str, Any]]:
        """Parse inline elements in text."""
        children = []

        # Simple inline parsing - can be enhanced with full inline parser
        # For now, just extract links and basic formatting

        # Links pattern: [text](url)
        link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

        # Code pattern: `code`
        code_pattern = re.compile(r"`([^`]+)`")

        # Bold pattern: **text** or __text__
        bold_pattern = re.compile(r"(\*\*|__)([^*_]+)\1")

        # Italic pattern: *text* or _text_
        italic_pattern = re.compile(r"(\*|_)([^*_]+)\1")

        # Image pattern: ![alt](url)
        image_pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

        # Process text and extract inline elements
        last_end = 0

        # Find all matches
        matches = []

        for match in image_pattern.finditer(text):
            matches.append(("image", match))
        for match in link_pattern.finditer(text):
            matches.append(("link", match))
        for match in code_pattern.finditer(text):
            matches.append(("code", match))
        for match in bold_pattern.finditer(text):
            matches.append(("bold", match))
        for match in italic_pattern.finditer(text):
            matches.append(("italic", match))

        # Sort matches by position
        matches.sort(key=lambda x: x[1].start())

        # Process matches
        for match_type, match in matches:
            # Add text before this match
            if match.start() > last_end:
                children.append({"type": "text", "value": text[last_end : match.start()]})

            # Add the matched element
            if match_type == "image":
                children.append({"type": "image", "url": match.group(2), "alt": match.group(1)})
            elif match_type == "link":
                children.append(
                    {
                        "type": "link",
                        "url": match.group(2),
                        "children": [{"type": "text", "value": match.group(1)}],
                    }
                )
            elif match_type == "code":
                children.append({"type": "inlineCode", "value": match.group(1)})
            elif match_type == "bold":
                children.append(
                    {
                        "type": "strong",
                        "children": [{"type": "text", "value": match.group(2)}],
                    }
                )
            elif match_type == "italic":
                children.append(
                    {
                        "type": "emphasis",
                        "children": [{"type": "text", "value": match.group(2)}],
                    }
                )

            last_end = match.end()

        # Add remaining text
        if last_end < len(text):
            children.append({"type": "text", "value": text[last_end:]})

        # If no inline elements found, return plain text
        if not children:
            children = [{"type": "text", "value": text}]

        return children
