#!/usr/bin/env python3
"""
Production scenario tests for Markdown plugin.
Tests real-world markdown patterns and edge cases.
"""

import pytest
import tempfile
import os
from pathlib import Path

from mcp_server.plugins.plugin_factory import PluginFactory
from mcp_server.storage.sqlite_store import SQLiteStore


class TestMarkdownProductionScenarios:
    """Test Markdown plugin with production scenarios."""
    
    @pytest.fixture
    def sqlite_store(self):
        """Create a temporary SQLite store for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        store = SQLiteStore(db_path)
        yield store
        
        # Cleanup
        store.close()
        os.unlink(db_path)
    
    @pytest.fixture
    def markdown_plugin(self, sqlite_store):
        """Create Markdown plugin instance."""
        return PluginFactory.create_plugin('markdown', sqlite_store)
    
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
        
        result = markdown_plugin.extract_symbols(content, "github.md")
        
        # Check task list parsing
        assert any("Completed task" in s.name for s in result.symbols)
        
        # Check table detection
        tables = [s for s in result.symbols if s.symbol_type == "table"]
        assert len(tables) >= 1
        
        # Check special blocks
        assert any("NOTE" in str(s.metadata) or "WARNING" in str(s.metadata) 
                  for s in result.symbols)
    
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
        
        result = markdown_plugin.extract_symbols(content, "nested.md")
        
        # Verify structure is preserved
        assert len(result.symbols) > 5
        
        # Check nested content extraction
        assert any("Fourth level" in s.name for s in result.symbols)
        assert any("Level 3 quote" in s.name for s in result.symbols)
    
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
        
        result = markdown_plugin.extract_symbols(content, "wiki.md")
        
        # Check internal link extraction
        assert any("Internal Link" in str(s.metadata) for s in result.symbols)
        
        # Check footnote handling
        assert any("footnote" in s.name.lower() for s in result.symbols)
    
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
        
        result = markdown_plugin.extract_symbols(content, "multilingual.md")
        
        # Check Unicode handling
        assert any("中文部分" in s.name for s in result.symbols)
        assert any("日本語セクション" in s.name for s in result.symbols)
        
        # Verify code blocks with non-ASCII comments
        code_blocks = [s for s in result.symbols if s.symbol_type == "code_block"]
        assert len(code_blocks) >= 2
    
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
        
        result = markdown_plugin.extract_symbols(content, "research.md")
        
        # Check section numbering
        assert any("1. Introduction" in s.name for s in result.symbols)
        assert any("2.1 Experimental Setup" in s.name for s in result.symbols)
        
        # Check citation patterns
        assert any("@smith2022" in str(s.metadata) or "@jones2023" in str(s.metadata)
                  for s in result.symbols)
        
        # Check math expressions
        assert any("equation" in s.symbol_type or "math" in s.symbol_type 
                  for s in result.symbols)
    
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
        
        result = markdown_plugin.extract_symbols(content, "config.md")
        
        # Check different config format extraction
        config_blocks = [s for s in result.symbols if s.symbol_type == "code_block"]
        
        # Verify language detection for configs
        languages = [s.metadata.get('language', '') for s in config_blocks]
        assert 'bash' in languages
        assert 'yaml' in languages
        assert 'nginx' in languages
    
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
        
        result = markdown_plugin.extract_symbols(content, "tutorial.md")
        
        # Check step extraction
        steps = [s for s in result.symbols if "Step" in s.name]
        assert len(steps) >= 4
        
        # Check collapsible sections
        assert any("<details>" in str(s.metadata) for s in result.symbols)
        
        # Check tip/warning boxes
        assert any("Tip:" in s.name or "💡" in s.name for s in result.symbols)
    
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
        
        result = markdown_plugin.extract_symbols(content, "CHANGELOG.md")
        
        # Check version extraction
        versions = [s for s in result.symbols if "[1." in s.name or "[Unreleased]" in s.name]
        assert len(versions) >= 3
        
        # Check change type sections
        change_types = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
        for change_type in change_types:
            assert any(change_type in s.name for s in result.symbols)
    
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
"""
        }
        
        # Process all documents
        for filepath, content in docs.items():
            result = markdown_plugin.extract_symbols(content, filepath)
            
            for symbol in result.symbols:
                sqlite_store.add_symbol(
                    file_path=filepath,
                    symbol_name=symbol.name,
                    symbol_type=symbol.symbol_type,
                    line_number=symbol.line,
                    metadata=symbol.metadata
                )
        
        # Verify cross-references work
        results = sqlite_store.search_symbols("Search API", limit=10)
        assert len(results) > 0
        
        # Check hierarchical structure
        api_docs = [r for r in results if "api/" in r[0]]
        assert len(api_docs) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])