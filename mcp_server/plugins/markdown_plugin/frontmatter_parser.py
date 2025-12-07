"""
Frontmatter parser for YAML and TOML metadata extraction.
"""

import re

import yaml

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomlkit as tomllib
    except ImportError:
        import toml as tomllib

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FrontmatterParser:
    """Parser for YAML and TOML frontmatter in Markdown documents."""

    def __init__(self):
        """Initialize the frontmatter parser."""
        self.yaml_delimiter = "---"
        self.toml_delimiter = "+++"

    def parse(self, content: str) -> Tuple[Dict[str, Any], str]:
        """
        Parse frontmatter from content and return metadata and content without frontmatter.

        Args:
            content: The full document content

        Returns:
            Tuple of (metadata dict, content without frontmatter)
        """
        # Check for YAML frontmatter
        if content.startswith(self.yaml_delimiter):
            return self._parse_yaml_frontmatter(content)

        # Check for TOML frontmatter
        if content.startswith(self.toml_delimiter):
            return self._parse_toml_frontmatter(content)

        # No frontmatter found
        return {}, content

    def _parse_yaml_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """Parse YAML frontmatter."""
        lines = content.split("\n")

        # Find the closing delimiter
        end_index = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == self.yaml_delimiter:
                end_index = i
                break

        if end_index == -1:
            # No closing delimiter found
            return {}, content

        # Extract YAML content
        yaml_content = "\n".join(lines[1:end_index])

        try:
            # Parse YAML
            metadata = yaml.safe_load(yaml_content)

            # Ensure metadata is a dict
            if not isinstance(metadata, dict):
                metadata = {}

            # Process metadata
            metadata = self._process_metadata(metadata)

            # Return metadata and content without frontmatter
            remaining_content = "\n".join(lines[end_index + 1 :])
            return metadata, remaining_content.lstrip("\n")

        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML frontmatter: {e}")
            # Still remove the frontmatter from content
            remaining_content = "\n".join(lines[end_index + 1 :])
            return {}, remaining_content.lstrip("\n")

    def _parse_toml_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """Parse TOML frontmatter."""
        lines = content.split("\n")

        # Find the closing delimiter
        end_index = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == self.toml_delimiter:
                end_index = i
                break

        if end_index == -1:
            # No closing delimiter found
            return {}, content

        # Extract TOML content
        toml_content = "\n".join(lines[1:end_index])

        try:
            # Parse TOML
            if hasattr(tomllib, "loads"):
                metadata = tomllib.loads(toml_content)
            else:
                # For tomlkit
                metadata = dict(tomllib.parse(toml_content))

            # Process metadata
            metadata = self._process_metadata(metadata)

            # Return metadata and content without frontmatter
            remaining_content = "\n".join(lines[end_index + 1 :])
            return metadata, remaining_content.lstrip("\n")

        except Exception as e:
            logger.warning(f"Failed to parse TOML frontmatter: {e}")
            return {}, content

    def _process_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process and normalize metadata."""
        processed = {}

        for key, value in metadata.items():
            # Normalize common keys
            normalized_key = self._normalize_key(key)

            # Process values
            if normalized_key == "tags":
                processed[normalized_key] = self._process_tags(value)
            elif normalized_key == "date":
                processed[normalized_key] = self._process_date(value)
            elif normalized_key == "authors":
                processed[normalized_key] = self._process_authors(value)
            elif normalized_key == "categories":
                processed[normalized_key] = self._process_categories(value)
            else:
                processed[normalized_key] = value

        return processed

    def _normalize_key(self, key: str) -> str:
        """Normalize metadata keys."""
        # Common variations to normalize
        key_mappings = {
            "tag": "tags",
            "category": "categories",
            "author": "authors",
            "created": "date",
            "published": "date",
            "modified": "updated",
            "summary": "description",
            "excerpt": "description",
            "slug": "id",
        }

        lower_key = key.lower()
        return key_mappings.get(lower_key, lower_key)

    def _process_tags(self, value: Any) -> List[str]:
        """Process tags value."""
        if isinstance(value, list):
            return [str(tag).strip() for tag in value if tag]
        elif isinstance(value, str):
            # Handle comma-separated or space-separated tags
            if "," in value:
                return [tag.strip() for tag in value.split(",") if tag.strip()]
            else:
                return value.split()
        else:
            return []

    def _process_categories(self, value: Any) -> List[str]:
        """Process categories value."""
        # Similar to tags processing
        return self._process_tags(value)

    def _process_date(self, value: Any) -> Optional[str]:
        """Process date value."""
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        elif isinstance(value, str):
            # Try to parse common date formats
            date_formats = [
                "%Y-%m-%d",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ",
                "%d/%m/%Y",
                "%m/%d/%Y",
            ]

            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(value, fmt)
                    return parsed_date.isoformat()
                except ValueError:
                    continue

            # Return as-is if parsing fails
            return value
        else:
            return None

    def _process_authors(self, value: Any) -> List[str]:
        """Process authors value."""
        if isinstance(value, list):
            authors = []
            for author in value:
                if isinstance(author, dict):
                    # Handle author objects
                    name = author.get("name", author.get("display_name", ""))
                    if name:
                        authors.append(name)
                else:
                    authors.append(str(author))
            return authors
        elif isinstance(value, str):
            # Handle comma-separated authors
            if "," in value:
                return [author.strip() for author in value.split(",") if author.strip()]
            else:
                return [value]
        else:
            return []

    def extract_inline_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from inline markers in content."""
        metadata = {}

        # Extract hashtags
        hashtags = re.findall(r"#(\w+)", content)
        if hashtags:
            metadata["hashtags"] = list(set(hashtags))

        # Extract mentions
        mentions = re.findall(r"@(\w+)", content)
        if mentions:
            metadata["mentions"] = list(set(mentions))

        # Extract metadata markers like [meta:key:value]
        meta_markers = re.findall(r"\[meta:(\w+):([^\]]+)\]", content)
        for key, value in meta_markers:
            metadata[key] = value

        return metadata

    def validate_frontmatter(self, metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate frontmatter against common schema."""
        errors = []

        # Check required fields
        required_fields = []  # Can be customized
        for field in required_fields:
            if field not in metadata:
                errors.append(f"Missing required field: {field}")

        # Validate field types
        type_validations = {
            "title": str,
            "description": str,
            "tags": list,
            "categories": list,
            "authors": list,
            "draft": bool,
            "weight": (int, float),
        }

        for field, expected_type in type_validations.items():
            if field in metadata:
                value = metadata[field]
                if isinstance(expected_type, tuple):
                    if not isinstance(value, expected_type):
                        errors.append(
                            f"Field '{field}' should be one of {expected_type}, got {type(value)}"
                        )
                else:
                    if not isinstance(value, expected_type):
                        errors.append(
                            f"Field '{field}' should be {expected_type}, got {type(value)}"
                        )

        return len(errors) == 0, errors

    def serialize_frontmatter(self, metadata: Dict[str, Any], format: str = "yaml") -> str:
        """Serialize metadata back to frontmatter format."""
        if not metadata:
            return ""

        if format == "yaml":
            try:
                yaml_content = yaml.dump(metadata, default_flow_style=False, allow_unicode=True)
                return f"{self.yaml_delimiter}\n{yaml_content}{self.yaml_delimiter}\n"
            except Exception as e:
                logger.error(f"Failed to serialize YAML frontmatter: {e}")
                return ""

        elif format == "toml":
            try:
                if hasattr(tomllib, "dumps"):
                    toml_content = tomllib.dumps(metadata)
                else:
                    # For tomlkit
                    import tomlkit

                    toml_content = tomlkit.dumps(metadata)
                return f"{self.toml_delimiter}\n{toml_content}{self.toml_delimiter}\n"
            except Exception as e:
                logger.error(f"Failed to serialize TOML frontmatter: {e}")
                return ""

        else:
            raise ValueError(f"Unsupported format: {format}")

    def merge_metadata(self, *metadata_dicts: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple metadata dictionaries."""
        merged = {}

        for metadata in metadata_dicts:
            for key, value in metadata.items():
                if key in merged:
                    # Handle merging lists
                    if isinstance(merged[key], list) and isinstance(value, list):
                        # Merge lists without duplicates
                        merged[key] = list(set(merged[key] + value))
                    else:
                        # Later values override earlier ones
                        merged[key] = value
                else:
                    merged[key] = value

        return merged
