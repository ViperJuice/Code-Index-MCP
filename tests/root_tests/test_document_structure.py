#!/usr/bin/env python3
"""Test document structure parsing without API calls."""

import tempfile
from pathlib import Path

from mcp_server.utils.semantic_indexer import SemanticIndexer


def create_test_documents(temp_dir: Path) -> None:
    """Create test documentation files."""

    # Create README.md
    readme_content = """# MCP Server Documentation

This is the main documentation for the MCP Server project.

## Installation

Follow these steps to install:

### Prerequisites

- Python 3.9+
- Docker (optional)

### Basic Installation

```bash
pip install mcp-server
```

## Configuration

The server can be configured using environment variables.

### Environment Variables

- `MCP_PORT`: Server port (default: 8080)
- `MCP_HOST`: Server host (default: localhost)

## API Reference

### Search Endpoint

```
GET /api/search?q=<query>
```

Returns search results.

### Index Endpoint

```
POST /api/index
```

Indexes new content.
"""

    readme_path = temp_dir / "README.md"
    readme_path.write_text(readme_content)

    return readme_path


def test_document_parsing():
    """Test the document parsing functionality without API calls."""

    # Create temporary directory with test documents
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        readme_path = create_test_documents(temp_path)

        # Create indexer instance (but don't initialize voyage client)
        indexer = SemanticIndexer.__new__(SemanticIndexer)

        print("Testing document structure parsing...")
        print("-" * 50)

        # Test markdown section parsing
        content = readme_path.read_text()
        print(f"\nOriginal document content ({len(content)} chars):")
        print(content[:200] + "..." if len(content) > 200 else content)

        print("\nParsing markdown sections:")
        sections = indexer._parse_markdown_sections(content, str(readme_path))

        print(f"\nFound {len(sections)} sections:")
        for i, section in enumerate(sections, 1):
            print(f"\n{i}. Section: '{section.title}'")
            print(f"   - Level: {section.level}")
            print(f"   - Lines: {section.start_line}-{section.end_line}")
            print(f"   - Parent: {section.parent_section or 'None'}")
            print(f"   - Subsections: {section.subsections}")
            print(f"   - Content preview: {section.content[:100].replace(chr(10), ' ')}...")

        # Test document type detection
        print("\n" + "=" * 50)
        print("Testing document type detection:")

        test_files = [
            ("README.md", None),
            ("api.md", None),
            ("tutorial.rst", None),
            ("guide.txt", None),
        ]

        for filename, doc_type in test_files:
            file_name = filename.lower()

            # Simulate document type detection logic
            if doc_type is None:
                if file_name == "readme.md":
                    detected_type = "readme"
                elif file_name.endswith(".md"):
                    detected_type = "markdown"
                elif file_name.endswith(".rst"):
                    detected_type = "markdown"  # Similar handling
                else:
                    detected_type = "text"
            else:
                detected_type = doc_type

            print(f"   - {filename} -> {detected_type}")

        # Test context building
        print("\n" + "=" * 50)
        print("Testing section context building:")

        for section in sections:
            section_context = []
            if section.parent_section:
                section_context.append(section.parent_section)
            section_context.append(section.title)
            context_str = " > ".join(section_context)

            print(f"   - '{section.title}' -> '{context_str}'")

        # Test embedding text preparation (without API call)
        print("\n" + "=" * 50)
        print("Testing embedding text preparation:")

        sample_section = sections[0] if sections else None
        if sample_section:
            # Simulate the embedding text creation logic
            embedding_parts = []

            title = "README"
            section_context = sample_section.title
            metadata = {
                "tags": ["documentation", "readme", "main"],
                "summary": "Main project documentation",
            }

            if title:
                embedding_parts.append(f"Document: {title}")

            if section_context:
                embedding_parts.append(f"Section: {section_context}")

            if metadata:
                if "summary" in metadata:
                    embedding_parts.append(f"Summary: {metadata['summary']}")
                if "tags" in metadata:
                    embedding_parts.append(f"Tags: {', '.join(metadata['tags'])}")

            embedding_parts.append(sample_section.content[:200])
            embedding_text = "\n\n".join(embedding_parts)

            print(f"Sample embedding text for '{sample_section.title}':")
            print("-" * 30)
            print(embedding_text)
            print("-" * 30)
            print(f"Total length: {len(embedding_text)} characters")


if __name__ == "__main__":
    test_document_parsing()
