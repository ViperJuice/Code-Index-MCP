"""Intelligent paragraph detection for plain text documents."""

import re
from dataclasses import dataclass
from typing import List


@dataclass
class Paragraph:
    """Represents a paragraph with metadata."""

    text: str
    start_line: int
    end_line: int
    indent_level: int
    is_list_item: bool
    is_code_block: bool


class ParagraphDetector:
    """Detects and analyzes paragraph structure in plain text."""

    def __init__(self):
        # Patterns for different text structures
        self.list_patterns = [
            re.compile(r"^\s*[-*+]\s+"),  # Bullet points
            re.compile(r"^\s*\d+[.)]\s+"),  # Numbered lists
            re.compile(r"^\s*[a-zA-Z][.)]\s+"),  # Alphabetic lists
            re.compile(r"^\s*\([a-zA-Z0-9]+\)\s+"),  # Parenthetical lists
        ]

        self.code_indicators = [
            re.compile(r"^\s*```"),  # Markdown code blocks
            re.compile(r"^\s*~~~"),  # Alternative code blocks
            re.compile(r"^\s{4,}"),  # Indented code blocks
        ]

        self.heading_patterns = [
            re.compile(r"^#+\s+"),  # Markdown headings
            re.compile(r"^[A-Z][A-Z\s]+$"),  # ALL CAPS HEADINGS
            re.compile(r"^={3,}\s*$"),  # Underline with =
            re.compile(r"^-{3,}\s*$"),  # Underline with -
        ]

    def detect_paragraphs(self, text: str) -> List[Paragraph]:
        """Detect paragraphs with intelligent boundary detection."""
        lines = text.split("\n")
        paragraphs = []
        current_para_lines = []
        current_indent = 0
        in_code_block = False
        code_fence = None
        start_line = 0

        for i, line in enumerate(lines):
            # Check for code block boundaries
            if not in_code_block:
                for pattern in self.code_indicators[:2]:  # Check fence patterns
                    if pattern.match(line):
                        # Save current paragraph if any
                        if current_para_lines:
                            para_text = "\n".join(current_para_lines)
                            paragraphs.append(
                                Paragraph(
                                    text=para_text,
                                    start_line=start_line,
                                    end_line=i - 1,
                                    indent_level=current_indent,
                                    is_list_item=self._is_list_item(current_para_lines[0]),
                                    is_code_block=False,
                                )
                            )
                            current_para_lines = []

                        in_code_block = True
                        code_fence = line.strip()
                        start_line = i
                        current_para_lines = [line]
                        break
            else:
                # Check for matching code fence
                if line.strip() == code_fence:
                    current_para_lines.append(line)
                    para_text = "\n".join(current_para_lines)
                    paragraphs.append(
                        Paragraph(
                            text=para_text,
                            start_line=start_line,
                            end_line=i,
                            indent_level=0,
                            is_list_item=False,
                            is_code_block=True,
                        )
                    )
                    current_para_lines = []
                    in_code_block = False
                    code_fence = None
                    continue
                else:
                    current_para_lines.append(line)
                    continue

            # Skip if we're in a code block
            if in_code_block:
                current_para_lines.append(line)
                continue

            # Check for empty lines (paragraph boundaries)
            if not line.strip():
                if current_para_lines:
                    para_text = "\n".join(current_para_lines)
                    paragraphs.append(
                        Paragraph(
                            text=para_text,
                            start_line=start_line,
                            end_line=i - 1,
                            indent_level=current_indent,
                            is_list_item=self._is_list_item(current_para_lines[0]),
                            is_code_block=self._is_indented_code(current_para_lines),
                        )
                    )
                    current_para_lines = []
                continue

            # Check for headings (which are their own paragraphs)
            if self._is_heading(line, i, lines):
                if current_para_lines:
                    para_text = "\n".join(current_para_lines)
                    paragraphs.append(
                        Paragraph(
                            text=para_text,
                            start_line=start_line,
                            end_line=i - 1,
                            indent_level=current_indent,
                            is_list_item=self._is_list_item(current_para_lines[0]),
                            is_code_block=self._is_indented_code(current_para_lines),
                        )
                    )
                    current_para_lines = []

                # Add heading as its own paragraph
                paragraphs.append(
                    Paragraph(
                        text=line,
                        start_line=i,
                        end_line=i,
                        indent_level=0,
                        is_list_item=False,
                        is_code_block=False,
                    )
                )
                continue

            # Start new paragraph or continue current one
            line_indent = self._get_indent_level(line)

            if not current_para_lines:
                # Start new paragraph
                start_line = i
                current_indent = line_indent
                current_para_lines = [line]
            else:
                # Check if this should be a new paragraph
                if self._should_start_new_paragraph(
                    current_para_lines, line, current_indent, line_indent
                ):
                    # Save current paragraph
                    para_text = "\n".join(current_para_lines)
                    paragraphs.append(
                        Paragraph(
                            text=para_text,
                            start_line=start_line,
                            end_line=i - 1,
                            indent_level=current_indent,
                            is_list_item=self._is_list_item(current_para_lines[0]),
                            is_code_block=self._is_indented_code(current_para_lines),
                        )
                    )

                    # Start new paragraph
                    current_para_lines = [line]
                    start_line = i
                    current_indent = line_indent
                else:
                    # Continue current paragraph
                    current_para_lines.append(line)

        # Don't forget the last paragraph
        if current_para_lines:
            para_text = "\n".join(current_para_lines)
            paragraphs.append(
                Paragraph(
                    text=para_text,
                    start_line=start_line,
                    end_line=len(lines) - 1,
                    indent_level=current_indent,
                    is_list_item=self._is_list_item(current_para_lines[0]),
                    is_code_block=self._is_indented_code(current_para_lines) or in_code_block,
                )
            )

        return paragraphs

    def _get_indent_level(self, line: str) -> int:
        """Calculate indentation level of a line."""
        return len(line) - len(line.lstrip())

    def _is_list_item(self, line: str) -> bool:
        """Check if line starts a list item."""
        for pattern in self.list_patterns:
            if pattern.match(line):
                return True
        return False

    def _is_heading(self, line: str, line_num: int, all_lines: List[str]) -> bool:
        """Check if line is a heading."""
        # Check markdown-style headings
        if self.heading_patterns[0].match(line):
            return True

        # Check ALL CAPS headings
        stripped = line.strip()
        if stripped and stripped.isupper() and len(stripped.split()) <= 10:
            return True

        # Check underlined headings
        if line_num + 1 < len(all_lines):
            next_line = all_lines[line_num + 1]
            if self.heading_patterns[2].match(next_line) or self.heading_patterns[3].match(
                next_line
            ):
                return True

        return False

    def _is_indented_code(self, lines: List[str]) -> bool:
        """Check if lines form an indented code block."""
        if not lines:
            return False

        # All lines must be indented by at least 4 spaces
        for line in lines:
            if line.strip() and not self.code_indicators[2].match(line):
                return False

        return True

    def _should_start_new_paragraph(
        self,
        current_lines: List[str],
        new_line: str,
        current_indent: int,
        new_indent: int,
    ) -> bool:
        """Determine if new line should start a new paragraph."""
        # Different indent level usually means new paragraph
        if abs(new_indent - current_indent) > 2:
            return True

        # List item always starts new paragraph
        if self._is_list_item(new_line):
            return True

        # Check if current is list and new is not
        if (
            current_lines
            and self._is_list_item(current_lines[0])
            and not self._is_list_item(new_line)
        ):
            return True

        return False

    def merge_related_paragraphs(
        self, paragraphs: List[Paragraph], max_distance: int = 1
    ) -> List[Paragraph]:
        """Merge closely related paragraphs based on content similarity."""
        if len(paragraphs) <= 1:
            return paragraphs

        merged = []
        i = 0

        while i < len(paragraphs):
            current = paragraphs[i]

            # Don't merge code blocks or headings
            if current.is_code_block or self._is_heading(current.text, 0, [current.text]):
                merged.append(current)
                i += 1
                continue

            # Look ahead for mergeable paragraphs
            j = i + 1
            merge_candidates = [current]

            while j < len(paragraphs) and j - i <= max_distance:
                next_para = paragraphs[j]

                # Check if we should merge
                if (
                    not next_para.is_code_block
                    and not self._is_heading(next_para.text, 0, [next_para.text])
                    and abs(current.indent_level - next_para.indent_level) <= 2
                    and current.is_list_item == next_para.is_list_item
                ):

                    merge_candidates.append(next_para)
                    j += 1
                else:
                    break

            # Merge if we have candidates
            if len(merge_candidates) > 1:
                merged_text = "\n\n".join(p.text for p in merge_candidates)
                merged_para = Paragraph(
                    text=merged_text,
                    start_line=merge_candidates[0].start_line,
                    end_line=merge_candidates[-1].end_line,
                    indent_level=merge_candidates[0].indent_level,
                    is_list_item=merge_candidates[0].is_list_item,
                    is_code_block=False,
                )
                merged.append(merged_para)
                i = j
            else:
                merged.append(current)
                i += 1

        return merged
