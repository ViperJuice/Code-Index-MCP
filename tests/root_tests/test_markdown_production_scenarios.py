#!/usr/bin/env python3
"""
Production scenario tests for Markdown plugin.
Tests real-world markdown patterns and edge cases.
"""

import os
import tempfile

import pytest

from mcp_server.plugins.markdown_plugin import MarkdownPlugin
from mcp_server.storage.sqlite_store import SQLiteStore


class TestMarkdownProductionScenarios:
    """Test Markdown plugin with production scenarios."""

    @pytest.fixture
    def sqlite_store(self):
        """Create a temporary SQLite store for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        store = SQLiteStore(db_path)
        yield store

        # Cleanup
        store.close()
        os.unlink(db_path)

    @pytest.fixture
    def markdown_plugin(self, sqlite_store):
        """Create a concrete Markdown plugin instance for production-shape tests."""
        return MarkdownPlugin(sqlite_store)

    def test_github_flavored_markdown(self, markdown_plugin):
        """Test GitHub Flavored Markdown features."""
        content = """
# Project Title

## Task Lists

- [x] Completed task
- [ ] Incomplete task
- [x] ~~Strikethrough completed~~

## Tables

| Feature | Status | Priority |
|---------|--------|----------|
| Search  | ✅ Done | High     |
| Index   | 🔄 WIP  | Medium   |
| Export  | ❌ Todo | Low      |

## Alerts

> [!NOTE]
> Useful information that users should know.

> [!WARNING]
> Critical content demanding user attention.

## Mermaid Diagrams

```mermaid
graph TD
    A[Start] --> B{Is it?}
    B -->|Yes| C[OK]
    B -->|No| D[End]
```

## Math Expressions

When $a \\ne 0$, there are two solutions to $(ax^2 + bx + c = 0)$:

$$x = \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}$$
"""

        result = markdown_plugin.indexFile("github.md", content)

        symbol_names = [symbol["symbol"] for symbol in result["symbols"]]
        assert "Project Title" in symbol_names
        assert "Task Lists" in symbol_names
        assert "Tables" in symbol_names
        assert "Alerts" in symbol_names
        assert "Mermaid Diagrams" in symbol_names
        assert "Math Expressions" in symbol_names
        assert result["chunks"] != []

    def test_nested_lists_and_blockquotes(self, markdown_plugin):
        """Test complex nested structures."""
        content = """
# Complex Nesting

## Nested Lists

1. First level
   1. Second level
      - Third level bullet
      - Another bullet
        * Fourth level
   2. Back to second
2. Back to first

## Nested Blockquotes

> Level 1 quote
> > Level 2 quote
> > > Level 3 quote
> > 
> > Back to level 2
> 
> Back to level 1

## Mixed Nesting

1. List item with quote:
   > This is a quote inside a list
   > It spans multiple lines
   
2. Another item with code:
   ```python
   def nested():
       return "code in list"
   ```
"""

        result = markdown_plugin.indexFile("nested.md", content)

        symbol_names = [symbol["symbol"] for symbol in result["symbols"]]
        assert "Complex Nesting" in symbol_names
        assert "Nested Lists" in symbol_names
        assert "Nested Blockquotes" in symbol_names
        assert "Mixed Nesting" in symbol_names
        assert result["chunks"] != []

    def test_wiki_style_links_and_footnotes(self, markdown_plugin):
        """Test wiki-style links and footnotes."""
        content = """
# Wiki-Style Document

This is a [[Internal Link]] to another page.

See also [[Another Page|with custom text]].

## Footnotes

Here's a sentence with a footnote[^1].

This one has multiple[^2][^3] footnotes.

[^1]: This is the first footnote.
[^2]: Second footnote.
[^3]: Third footnote with [a link](http://example.com).

## References

As shown in [Smith2022](@cite) and later confirmed by [Jones2023](@cite).
"""

        result = markdown_plugin.indexFile("wiki.md", content)

        symbol_names = [symbol["symbol"] for symbol in result["symbols"]]
        assert "Wiki-Style Document" in symbol_names
        assert "Footnotes" in symbol_names
        assert "References" in symbol_names
        assert result["chunks"] != []

    def test_multilingual_content(self, markdown_plugin):
        """Test markdown with multiple languages and scripts."""
        content = """
# 多语言文档 (Multilingual Document)

## English Section

This is content in English.

## 中文部分

这是中文内容。包含中文标点符号：，。！？

## 日本語セクション

これは日本語のコンテンツです。

## Code Examples in Different Contexts

```python
# Python comment in English
def greet(name):
    return f"Hello, {name}!"
```

```javascript
// 中文注释
function 打招呼(名字) {
    console.log(`你好，${名字}！`);
}
```

## Mixed Language Lists

- English item
- 中文项目
- 日本語アイテム
- Emoji item 🎉
"""

        result = markdown_plugin.indexFile("multilingual.md", content)

        symbol_names = [symbol["symbol"] for symbol in result["symbols"]]
        assert "多语言文档 (Multilingual Document)" in symbol_names
        assert "中文部分" in symbol_names
        assert "日本語セクション" in symbol_names
        assert "Code Examples in Different Contexts" in symbol_names
        assert result["chunks"] != []

    def test_scientific_documentation(self, markdown_plugin):
        """Test scientific/academic markdown patterns."""
        content = """
# Research Paper Title

## Abstract

This paper presents... [1-3]. Previous work [4,5] has shown...

## 1. Introduction

As described by @smith2022 and @jones2023...

## 2. Methodology

### 2.1 Experimental Setup

$$\\begin{align}
E &= mc^2 \\\\
F &= ma \\\\
\\end{align}$$

### 2.2 Data Collection

| Sample | Temperature (°C) | Pressure (kPa) | Result |
|--------|------------------|----------------|--------|
| A-001  | 25.0 ± 0.1      | 101.3 ± 0.5   | Pass   |
| A-002  | 30.0 ± 0.1      | 105.2 ± 0.5   | Pass   |

## 3. Results

See Figure 1 and Table 2. Statistical significance (p < 0.05).

## References

1. Smith, J. et al. "Title of Paper". *Journal Name*. 2022.
2. Jones, A. "Another Paper". *Conf. Proc.* 2023.

## Appendix A: Supplementary Data

Additional figures and tables...
"""

        result = markdown_plugin.indexFile("research.md", content)

        symbol_names = [symbol["symbol"] for symbol in result["symbols"]]
        assert "Research Paper Title" in symbol_names
        assert "1. Introduction" in symbol_names
        assert "2.1 Experimental Setup" in symbol_names
        assert "2.2 Data Collection" in symbol_names
        assert "Appendix A: Supplementary Data" in symbol_names
        assert result["chunks"] != []

    def test_configuration_documentation(self, markdown_plugin):
        """Test configuration and setup documentation patterns."""
        content = """
# Configuration Guide

## Environment Variables

```bash
# Required
export API_KEY="your-api-key"
export DATABASE_URL="postgresql://user:pass@localhost/db"

# Optional
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
export PORT="${PORT:-8000}"
```

## Configuration File

```yaml
# config.yml
server:
  host: 0.0.0.0
  port: 8000
  workers: 4

database:
  url: ${DATABASE_URL}
  pool_size: 10
  timeout: 30

features:
  - name: search
    enabled: true
    config:
      max_results: 100
  - name: analytics
    enabled: false
```

## Docker Compose

```docker-compose
version: '3.8'

services:
  app:
    image: myapp:latest
    environment:
      - API_KEY=${API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      - db
      
  db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - db_data:/var/lib/postgresql/data

volumes:
  db_data:
```

## Nginx Configuration

```nginx
server {
    listen 80;
    server_name api.example.com;
    
    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
    }
}
```
"""

        result = markdown_plugin.indexFile("config.md", content)

        symbol_names = [symbol["symbol"] for symbol in result["symbols"]]
        assert "Configuration Guide" in symbol_names
        assert "Environment Variables" in symbol_names
        assert "Configuration File" in symbol_names
        assert "Docker Compose" in symbol_names
        assert "Nginx Configuration" in symbol_names
        assert result["chunks"] != []

    def test_tutorial_documentation(self, markdown_plugin):
        """Test tutorial and how-to documentation."""
        content = """
# Getting Started Tutorial

## Prerequisites

Before you begin, ensure you have:
- Python 3.8 or higher installed
- Git for version control
- A text editor (VS Code recommended)

## Step 1: Installation

First, clone the repository:

```bash
git clone https://github.com/example/project.git
cd project
```

## Step 2: Setup Virtual Environment

<details>
<summary>Click to expand setup instructions</summary>

### On macOS/Linux:
```bash
python -m venv venv
source venv/bin/activate
```

### On Windows:
```cmd
python -m venv venv
venv\\Scripts\\activate
```

</details>

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

> **💡 Tip:** Use `pip install -e .` for development mode.

## Step 4: Run Your First Example

Create a file named `hello.py`:

```python
from project import Client

# Initialize client
client = Client(api_key="your-key")

# Make your first request
response = client.hello("World")
print(response)
```

Run it:

```bash
python hello.py
```

Expected output:
```
Hello, World!
Connection successful.
```

## Troubleshooting

<details>
<summary>❌ Error: "Module not found"</summary>

Make sure you've activated your virtual environment:
```bash
source venv/bin/activate  # On macOS/Linux
```

</details>

<details>
<summary>❌ Error: "Invalid API key"</summary>

1. Check your API key is correct
2. Ensure no extra spaces
3. Try regenerating the key

</details>

## Next Steps

- 📖 Read the [API Documentation](api.md)
- 🔧 Check out [Advanced Configuration](config.md)
- 🚀 See [Example Projects](examples.md)

## Video Tutorials

- [Installation Walkthrough](https://youtube.com/watch?v=xxx) (5 min)
- [First Project](https://youtube.com/watch?v=yyy) (10 min)
"""

        result = markdown_plugin.indexFile("tutorial.md", content)

        symbol_names = [symbol["symbol"] for symbol in result["symbols"]]
        assert "Getting Started Tutorial" in symbol_names
        assert "Step 1: Installation" in symbol_names
        assert "Step 2: Setup Virtual Environment" in symbol_names
        assert "Step 3: Install Dependencies" in symbol_names
        assert "Step 4: Run Your First Example" in symbol_names
        assert "Troubleshooting" in symbol_names
        assert "Next Steps" in symbol_names
        assert result["chunks"] != []

    def test_changelog_format(self, markdown_plugin):
        """Test changelog and release notes format."""
        content = """
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New feature X for enhanced performance

### Changed
- Updated dependency Y to version 2.0

## [1.2.0] - 2025-06-09

### Added
- Markdown plugin with full CommonMark support
- PlainText plugin with NLP features
- Performance benchmarking suite

### Changed
- Improved memory usage by 30%
- Updated API response format

### Deprecated
- Old search endpoint `/api/search` (use `/api/v2/search`)

### Removed
- Legacy Python 2.7 support

### Fixed
- Memory leak in file watcher ([#123](https://github.com/ex/pro/issues/123))
- Unicode handling in search queries

### Security
- Updated dependencies to patch CVE-2025-1234

## [1.1.0] - 2025-05-01

### Added
- Initial semantic search support
- Docker deployment configuration

[Unreleased]: https://github.com/ex/pro/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/ex/pro/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/ex/pro/releases/tag/v1.1.0
"""

        result = markdown_plugin.indexFile("CHANGELOG.md", content)
        symbol_names = [symbol["symbol"] for symbol in result["symbols"]]

        # Check version extraction
        versions = [name for name in symbol_names if "[1." in name or "[Unreleased]" in name]
        assert len(versions) >= 3

        # Check change type sections
        change_types = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
        for change_type in change_types:
            assert any(change_type in name for name in symbol_names)

    def test_changelog_bounded_index_preserves_document_and_heading_symbols(self, markdown_plugin):
        """CHANGELOG.md should stay lexically discoverable on the bounded path."""
        content = """
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- New semantic staging diagnostics

## [1.2.0] - 2026-04-28

### Fixed
- Repair changelog lexical timeout handling
"""

        result = markdown_plugin.indexFile("CHANGELOG.md", content)

        assert result["metadata"]["lightweight_index"] is True
        assert result["metadata"]["lightweight_reason"] == "changelog_path"
        assert result["chunks"] == []
        symbol_names = [symbol["symbol"] for symbol in result["symbols"]]
        assert "Changelog" in symbol_names
        assert "[Unreleased]" in symbol_names
        assert "[1.2.0] - 2026-04-28" in symbol_names
        assert "Added" in symbol_names
        assert "Fixed" in symbol_names

    def test_roadmap_bounded_index_preserves_document_and_heading_symbols(self, markdown_plugin):
        """ROADMAP.md should stay lexically discoverable on the bounded path."""
        content = """
# Semantic Hardening Roadmap

## Current Phase

### SEMROADMAP
- Repair roadmap lexical timeout handling

## Next Phase

### SEMEVIDENCE
- Refresh semantic dogfood evidence after the rerun
"""

        result = markdown_plugin.indexFile("ROADMAP.md", content)

        assert result["metadata"]["lightweight_index"] is True
        assert result["metadata"]["lightweight_reason"] == "roadmap_path"
        assert result["chunks"] == []
        symbol_names = [symbol["symbol"] for symbol in result["symbols"]]
        assert "Semantic Hardening Roadmap" in symbol_names
        assert "Current Phase" in symbol_names
        assert "SEMROADMAP" in symbol_names
        assert "Next Phase" in symbol_names
        assert "SEMEVIDENCE" in symbol_names

    def test_final_analysis_bounded_index_preserves_document_and_heading_symbols(
        self, markdown_plugin
    ):
        """Final analysis reports should stay lexically discoverable on the bounded path."""
        content = """
# Final Comprehensive MCP Analysis

## Executive Summary

### Timeout Evidence
- Preserve lexical watchdog coverage for analysis reports

## Recommendations

### Next Step
- Carry forward the next exact downstream blocker
"""

        result = markdown_plugin.indexFile("FINAL_COMPREHENSIVE_MCP_ANALYSIS.md", content)

        assert result["metadata"]["lightweight_index"] is True
        assert result["metadata"]["lightweight_reason"] == "analysis_report_path"
        assert result["chunks"] == []
        symbol_names = [symbol["symbol"] for symbol in result["symbols"]]
        assert "Final Comprehensive MCP Analysis" in symbol_names
        assert "Executive Summary" in symbol_names
        assert "Timeout Evidence" in symbol_names
        assert "Recommendations" in symbol_names
        assert "Next Step" in symbol_names

    def test_agents_bounded_index_preserves_document_and_heading_symbols(
        self, markdown_plugin
    ):
        """AGENTS.md should stay lexically discoverable on the bounded path."""
        content = """
# MCP Server Agent Configuration

## Current State

### MCP Search Strategy
- Prefer readiness-aware indexed search

## Development Priorities

### Immediate
- Repair AGENTS lexical timeout handling
"""

        result = markdown_plugin.indexFile("AGENTS.md", content)

        assert result["metadata"]["lightweight_index"] is True
        assert result["metadata"]["lightweight_reason"] == "agent_instructions_path"
        assert result["chunks"] == []
        symbol_names = [symbol["symbol"] for symbol in result["symbols"]]
        assert "MCP Server Agent Configuration" in symbol_names
        assert "Current State" in symbol_names
        assert "MCP Search Strategy" in symbol_names
        assert "Development Priorities" in symbol_names
        assert "Immediate" in symbol_names

    def test_readme_bounded_index_preserves_document_and_heading_symbols(
        self, markdown_plugin
    ):
        """README.md should stay lexically discoverable on the bounded path."""
        content = """
# Code-Index-MCP

## Overview

### Search Strategy
- Preserve README heading discoverability

## Installation

### Local setup
- Use uv sync --locked
"""

        result = markdown_plugin.indexFile("README.md", content)

        assert result["metadata"]["lightweight_index"] is True
        assert result["metadata"]["lightweight_reason"] == "readme_path"
        assert result["chunks"] == []
        symbol_names = [symbol["symbol"] for symbol in result["symbols"]]
        assert "Code-Index-MCP" in symbol_names
        assert "Overview" in symbol_names
        assert "Search Strategy" in symbol_names
        assert "Installation" in symbol_names
        assert "Local setup" in symbol_names

    def test_jedi_ai_doc_uses_exact_bounded_markdown_path(self, markdown_plugin):
        """ai_docs/jedi.md should use the exact bounded Markdown recovery path."""
        content = """
# Jedi Documentation

## Overview and Key Features

### Code Completion
- Preserve document and heading discoverability

## MCP Server Use Cases

### Code Intelligence Service
- Keep this file on a narrow bounded path only
"""

        result = markdown_plugin.indexFile("ai_docs/jedi.md", content)

        assert result["metadata"]["lightweight_index"] is True
        assert result["metadata"]["lightweight_reason"] == "ai_docs_jedi_path"
        assert result["chunks"] == []
        symbol_names = [symbol["symbol"] for symbol in result["symbols"]]
        assert "Jedi Documentation" in symbol_names
        assert "Overview and Key Features" in symbol_names
        assert "Code Completion" in symbol_names
        assert "MCP Server Use Cases" in symbol_names
        assert "Code Intelligence Service" in symbol_names

    def test_other_ai_docs_markdown_stays_on_heavy_path(self, markdown_plugin):
        """The Jedi recovery must not broaden to unrelated ai_docs Markdown files."""
        content = """
# Semantic Preflight Notes

## Recovery

### Operator guidance
- Preserve the heavy Markdown path for unrelated ai_docs docs
"""

        result = markdown_plugin.indexFile("ai_docs/semantic_preflight_notes.md", content)

        assert result["metadata"].get("lightweight_index") is not True
        assert result["chunks"] != []

    def test_claude_command_markdown_uses_exact_bounded_paths(self, markdown_plugin):
        """The exact Claude command docs should stay lightweight but lexically visible."""
        execute_content = """
# Execute Lane

## Workflow

### Lane execution
- Keep lexical file and heading discoverability intact
"""
        plan_content = """
# Plan Phase

## Planning Rules

### Dependency freeze
- Preserve heading discoverability on the exact command pair
"""

        execute_result = markdown_plugin.indexFile(
            ".claude/commands/execute-lane.md", execute_content
        )
        plan_result = markdown_plugin.indexFile(".claude/commands/plan-phase.md", plan_content)

        assert execute_result["metadata"]["lightweight_index"] is True
        assert execute_result["metadata"]["lightweight_reason"] == "claude_execute_lane_path"
        assert execute_result["chunks"] == []
        execute_symbols = [symbol["symbol"] for symbol in execute_result["symbols"]]
        assert "Execute Lane" in execute_symbols
        assert "Workflow" in execute_symbols
        assert "Lane execution" in execute_symbols

        assert plan_result["metadata"]["lightweight_index"] is True
        assert plan_result["metadata"]["lightweight_reason"] == "claude_plan_phase_path"
        assert plan_result["chunks"] == []
        plan_symbols = [symbol["symbol"] for symbol in plan_result["symbols"]]
        assert "Plan Phase" in plan_symbols
        assert "Planning Rules" in plan_symbols
        assert "Dependency freeze" in plan_symbols

    def test_other_claude_command_markdown_stays_on_heavy_path(self, markdown_plugin):
        """The exact Claude command recovery must not broaden to unrelated command docs."""
        content = """
# Review Phase

## Review Rules

### Guardrails
- Keep unrelated command docs on the heavy Markdown path
"""

        result = markdown_plugin.indexFile(".claude/commands/review-phase.md", content)

        assert result["metadata"].get("lightweight_index") is not True
        assert result["chunks"] != []

    def test_large_documentation_site(self, markdown_plugin, sqlite_store):
        """Test handling of large documentation site structure."""
        # Simulate multiple interconnected docs
        docs = {
            "index.md": """
# Documentation Home

Welcome to the docs! Start with:
- [Getting Started](getting-started.md)
- [API Reference](api/index.md)
- [Examples](examples/index.md)
""",
            "getting-started.md": """
# Getting Started

See [Installation](install.md) and [Configuration](config.md).
""",
            "api/index.md": """
# API Reference

## Endpoints
- [Search API](search.md)
- [Index API](index.md)
""",
            "api/search.md": """
# Search API

## GET /search
See [authentication](../auth.md) for API key setup.
""",
            "examples/index.md": """
# Examples

- [Python Example](python.md)
- [JavaScript Example](javascript.md)
""",
        }

        discovered_symbols = []

        # Process all documents
        for filepath, content in docs.items():
            result = markdown_plugin.indexFile(filepath, content)

            for symbol in result["symbols"]:
                discovered_symbols.append((filepath, symbol["symbol"]))

        search_api_hits = [item for item in discovered_symbols if item[1] == "Search API"]
        assert len(search_api_hits) > 0
        assert any("api/" in filepath for filepath, _ in search_api_hits)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
