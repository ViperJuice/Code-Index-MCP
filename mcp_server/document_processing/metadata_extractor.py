"""
Metadata extractor for document processing.

This module provides functionality to extract metadata from various document types,
including title detection, author information, timestamps, keywords, and summaries.
"""

import re

import yaml

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import toml as tomllib
    except ImportError:
        tomllib = None
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extracts metadata from documents using various strategies."""

    def __init__(self):
        """Initialize the metadata extractor."""
        # Common title patterns
        self.title_patterns = [
            r"^#\s+(.+)$",  # Markdown h1
            r"^(.+)\n={3,}$",  # Underlined title
            r"^Title:\s*(.+)$",  # Explicit title field
            r"^<h1[^>]*>(.+?)</h1>",  # HTML h1
            r'^{{\s*title:\s*"(.+?)"\s*}}',  # Common template syntax
        ]

        # Author patterns
        self.author_patterns = [
            r"(?:Author|By|Written by):\s*(.+?)(?:\n|$)",
            r"@author\s+(.+?)(?:\n|$)",  # Javadoc style
            r'__author__\s*=\s*["\'](.+?)["\']',  # Python style
        ]

        # Date patterns
        self.date_patterns = [
            r"(?:Date|Published|Updated):\s*(\d{4}-\d{2}-\d{2})",
            r"(?:Date|Published|Updated):\s*(\d{1,2}/\d{1,2}/\d{4})",
            r"@date\s+(.+?)(?:\n|$)",
        ]

        # Language detection patterns (basic)
        self.language_indicators = {
            "python": [
                r"def\s+\w+\s*\(",
                r"import\s+\w+",
                r"class\s+\w+",
                r"if\s+__name__",
            ],
            "javascript": [
                r"function\s+\w+\s*\(",
                r"const\s+\w+\s*=",
                r"let\s+\w+\s*=",
                r"=>",
            ],
            "java": [
                r"public\s+class",
                r"private\s+\w+",
                r"package\s+\w+",
                r"import\s+java\.",
            ],
            "markdown": [r"^#{1,6}\s+", r"^\*\s+", r"^\d+\.\s+", r"\[.+\]\(.+\)"],
            "html": [r"<html", r"<body", r"<div", r"<head>"],
        }

    def extract_metadata(self, content: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract metadata from document content.

        Args:
            content: The document content
            file_path: Optional file path for additional metadata

        Returns:
            Dictionary containing extracted metadata
        """
        metadata = {}

        # Extract frontmatter if present
        frontmatter = self.extract_frontmatter(content)
        if frontmatter:
            metadata.update(frontmatter)
            # Remove frontmatter from content for further processing
            content = self.remove_frontmatter(content)

        # Extract title
        if "title" not in metadata:
            title = self.detect_title(content, file_path)
            if title:
                metadata["title"] = title

        # Extract author
        if "author" not in metadata:
            author = self.extract_author(content)
            if author:
                metadata["author"] = author

        # Extract date
        if "date" not in metadata:
            date = self.extract_date(content)
            if date:
                metadata["date"] = date

        # Detect language
        if "language" not in metadata:
            language = self.detect_language(content)
            if language:
                metadata["language"] = language

        # Extract keywords
        if "keywords" not in metadata:
            keywords = self.extract_keywords(content)
            if keywords:
                metadata["keywords"] = keywords

        # Generate summary
        if "summary" not in metadata and "description" not in metadata:
            summary = self.generate_summary(content)
            if summary:
                metadata["summary"] = summary

        # Add file metadata if available
        if file_path:
            file_metadata = self.extract_file_metadata(file_path)
            metadata.update(file_metadata)

        return metadata

    def extract_frontmatter(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract YAML or TOML frontmatter from content.

        Args:
            content: The document content

        Returns:
            Parsed frontmatter as dictionary or None
        """
        # YAML frontmatter pattern
        yaml_pattern = r"^---\s*\n(.*?)\n---\s*\n"
        yaml_match = re.match(yaml_pattern, content, re.DOTALL)

        if yaml_match:
            try:
                return yaml.safe_load(yaml_match.group(1))
            except yaml.YAMLError:
                logger.warning("Failed to parse YAML frontmatter")

        # TOML frontmatter pattern
        if tomllib:
            toml_pattern = r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n"
            toml_match = re.match(toml_pattern, content, re.DOTALL)

            if toml_match:
                try:
                    if hasattr(tomllib, "loads"):
                        return tomllib.loads(toml_match.group(1))
                    else:
                        # Python 3.11+ tomllib only has load() for file objects
                        import io

                        return tomllib.load(io.StringIO(toml_match.group(1)))
                except Exception:
                    logger.warning("Failed to parse TOML frontmatter")

        return None

    def remove_frontmatter(self, content: str) -> str:
        """Remove frontmatter from content."""
        # Remove YAML frontmatter
        content = re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, flags=re.DOTALL)
        # Remove TOML frontmatter
        content = re.sub(r"^\+\+\+\s*\n.*?\n\+\+\+\s*\n", "", content, flags=re.DOTALL)
        return content

    def detect_title(self, content: str, file_path: Optional[str] = None) -> Optional[str]:
        """
        Detect document title using various heuristics.

        Args:
            content: The document content
            file_path: Optional file path as fallback

        Returns:
            Detected title or None
        """
        # Try each title pattern
        for pattern in self.title_patterns:
            match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # Clean up common markdown/HTML artifacts
                title = re.sub(r"[#*`]", "", title)
                title = re.sub(r"<[^>]+>", "", title)
                return title

        # Special handling for HTML title tag
        html_title_match = re.search(r"<title>(.+?)</title>", content, re.IGNORECASE | re.DOTALL)
        if html_title_match:
            return html_title_match.group(1).strip()

        # Look for Python/code docstring title
        docstring_match = re.search(r'(?:"""|\'\'\')(.*?)(?:"""|\'\'\')', content, re.DOTALL)
        if docstring_match and file_path and file_path.endswith((".py", ".js", ".java")):
            docstring_content = docstring_match.group(1).strip()
            # First line of docstring is often the title
            first_line = docstring_content.split("\n")[0].strip()
            if first_line and not first_line.lower().startswith(("author:", "date:", "copyright:")):
                return first_line

        # Fallback: use first non-empty line
        lines = content.strip().split("\n")
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            line = line.strip()
            # Skip common non-title patterns
            if (
                line
                and not line.startswith(
                    ("#", "-", "*", "```", "/*", "//", "<!--", "<!DOCTYPE", "<?xml")
                )
                and not line.lower().startswith(
                    ("author:", "date:", "by:", "written by:", "copyright:")
                )
                and line not in ('"""', "'''", "*/")
                and len(line) > 3
                and len(line) < 100
            ):

                # For Python docstrings, skip lines that look like metadata
                if file_path and file_path.endswith(".py"):
                    # Skip if inside a docstring and looks like metadata
                    if i > 0 and i < len(lines) - 1:
                        prev_line = lines[i - 1].strip()
                        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                        # Check if we're inside a docstring
                        if (
                            prev_line in ('"""', "'''")
                            or next_line in ('"""', "'''")
                            or (i >= 2 and lines[i - 2].strip() in ('"""', "'''"))
                        ):
                            # This might be inside a docstring, check if it's metadata
                            if ":" in line:
                                continue

                return line

        # Last resort: use filename
        if file_path:
            filename = Path(file_path).stem
            # Convert snake_case or kebab-case to title case
            title = filename.replace("_", " ").replace("-", " ")
            return title.title()

        return None

    def extract_author(self, content: str) -> Optional[str]:
        """Extract author information from content."""
        for pattern in self.author_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def extract_date(self, content: str) -> Optional[str]:
        """Extract date information from content."""
        for pattern in self.date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def detect_language(self, content: str) -> Optional[str]:
        """
        Detect the primary language/format of the document.

        Args:
            content: The document content

        Returns:
            Detected language or None
        """
        scores = {}

        for language, patterns in self.language_indicators.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, content, re.MULTILINE))
                score += matches
            if score > 0:
                scores[language] = score

        if scores:
            # Return language with highest score
            return max(scores, key=scores.get)

        return None

    def extract_keywords(self, content: str, max_keywords: int = 10) -> List[str]:
        """
        Extract keywords using TF-IDF algorithm.

        Args:
            content: The document content
            max_keywords: Maximum number of keywords to extract

        Returns:
            List of extracted keywords
        """
        # Simple tokenization (can be improved with proper NLP)
        words = re.findall(r"\b[a-zA-Z]{3,}\b", content.lower())

        # Remove common stop words (basic list)
        stop_words = {
            "the",
            "is",
            "at",
            "which",
            "on",
            "and",
            "a",
            "an",
            "as",
            "are",
            "been",
            "by",
            "for",
            "from",
            "has",
            "he",
            "in",
            "is",
            "it",
            "its",
            "of",
            "on",
            "that",
            "the",
            "to",
            "was",
            "will",
            "with",
            "be",
            "have",
            "this",
            "can",
            "but",
            "not",
            "you",
            "all",
            "they",
            "their",
            "what",
            "when",
            "where",
            "who",
            "why",
            "how",
            "these",
            "those",
            "some",
            "many",
            "much",
            "very",
            "such",
            "only",
            "other",
            "into",
            "after",
            "before",
            "then",
            "also",
            "just",
            "more",
            "most",
            "than",
        }

        words = [w for w in words if w not in stop_words]

        if not words:
            return []

        # Calculate term frequency
        word_count = Counter(words)
        total_words = len(words)

        # Calculate TF-IDF (simplified - without IDF from corpus)
        tf_scores = {}
        for word, count in word_count.items():
            tf = count / total_words
            # Boost longer words (they tend to be more specific)
            length_boost = 1 + (len(word) - 3) * 0.1
            tf_scores[word] = tf * length_boost

        # Get top keywords
        sorted_keywords = sorted(tf_scores.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, score in sorted_keywords[:max_keywords]]

        return keywords

    def generate_summary(self, content: str, max_length: int = 200) -> Optional[str]:
        """
        Generate a summary from the document content.

        Args:
            content: The document content
            max_length: Maximum length of the summary

        Returns:
            Generated summary or None
        """
        # Remove frontmatter and code blocks for summary
        clean_content = self.remove_frontmatter(content)
        clean_content = re.sub(r"```.*?```", "", clean_content, flags=re.DOTALL)
        clean_content = re.sub(r"`[^`]+`", "", clean_content)

        # Remove HTML tags
        clean_content = re.sub(r"<[^>]+>", "", clean_content)

        # Remove language-specific comment blocks
        clean_content = re.sub(r"/\*.*?\*/", "", clean_content, flags=re.DOTALL)
        clean_content = re.sub(r'""".*?"""', "", clean_content, flags=re.DOTALL)
        clean_content = re.sub(r"'''.*?'''", "", clean_content, flags=re.DOTALL)

        # Split into paragraphs
        paragraphs = re.split(r"\n\s*\n", clean_content)

        # Find first substantial paragraph
        for para in paragraphs:
            para = para.strip()
            # Skip headers, lists, imports, etc.
            if (
                para
                and not para.startswith("#")
                and not para.startswith("*")
                and not para.startswith("-")
                and not para.startswith("1.")
                and not para.startswith("import ")
                and not para.startswith("from ")
                and not para.startswith("class ")
                and not para.startswith("def ")
                and not para.startswith("//")
                and not para.startswith("/*")
                and len(para) > 50
            ):

                # Truncate if needed
                if len(para) > max_length:
                    # Try to cut at sentence boundary
                    sentences = re.split(r"[.!?]\s+", para)
                    summary = ""
                    for sentence in sentences:
                        if len(summary) + len(sentence) < max_length:
                            summary += sentence + ". "
                        else:
                            break
                    return summary.strip() or para[:max_length] + "..."
                return para

        # Fallback: use beginning of clean content
        if clean_content:
            # Skip any leading whitespace or short lines
            lines = clean_content.strip().split("\n")
            for line in lines:
                line = line.strip()
                if len(line) > 20:
                    return line[:max_length] + "..." if len(line) > max_length else line

        return None

    def extract_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from file system.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with file metadata
        """
        metadata = {}

        try:
            path = Path(file_path)
            if path.exists():
                stat = path.stat()

                metadata["file_name"] = path.name
                metadata["file_path"] = str(path.absolute())
                metadata["file_size"] = stat.st_size
                metadata["created_at"] = datetime.fromtimestamp(stat.st_ctime).isoformat()
                metadata["modified_at"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                metadata["file_extension"] = path.suffix.lower()

        except Exception as e:
            logger.warning(f"Failed to extract file metadata: {e}")

        return metadata

    def extract_code_metadata(self, content: str, language: str) -> Dict[str, Any]:
        """
        Extract metadata specific to code files.

        Args:
            content: The code content
            language: The programming language

        Returns:
            Dictionary with code-specific metadata
        """
        metadata = {}

        # Extract imports/dependencies
        if language == "python":
            imports = re.findall(r"^(?:from\s+(\S+)\s+)?import\s+(.+)$", content, re.MULTILINE)
            dependencies = []
            for from_module, import_names in imports:
                if from_module:
                    dependencies.append(from_module.split(".")[0])
                else:
                    for name in import_names.split(","):
                        dependencies.append(name.strip().split(".")[0])
            metadata["dependencies"] = list(set(dependencies))

            # Extract classes and functions
            classes = re.findall(r"^class\s+(\w+)", content, re.MULTILINE)
            functions = re.findall(r"^def\s+(\w+)", content, re.MULTILINE)
            metadata["classes"] = classes
            metadata["functions"] = functions

        elif language == "javascript":
            # Extract imports
            imports = re.findall(r'(?:import|require)\s*\(?[\'"]([^\'"]+)[\'"]\)?', content)
            metadata["dependencies"] = list(set(imports))

            # Extract functions and classes
            functions = re.findall(
                r"(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)\s*)?=>)",
                content,
            )
            functions = [f for group in functions for f in group if f]
            metadata["functions"] = list(set(functions))

            classes = re.findall(r"class\s+(\w+)", content)
            metadata["classes"] = classes

        return metadata
