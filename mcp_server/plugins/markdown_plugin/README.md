# Comprehensive Markdown Plugin

A comprehensive Markdown plugin with advanced parsing capabilities, supporting GitHub-flavored Markdown, front matter, MDX, and extensive documentation analysis features.

## Features

- **Language**: markdown
- **File Extensions**: .md, .markdown, .mdx, .mkd
- **Plugin Type**: hybrid (Tree-sitter + regex fallback)
- **Tree-sitter Support**: Yes

## Supported Symbol Types & Features

### Core Markdown Elements
- **Headers** (H1-H6): Extracted as class symbols with proper hierarchy
- **Code Blocks**: Language-aware extraction with metadata
- **Tables**: Structure parsing with column detection
- **Links & Images**: Reference and inline link extraction
- **Lists**: Including GitHub-style task lists with completion status

### Advanced Features
- **Front Matter**: YAML, TOML, and JSON front matter extraction
- **Math Formulas**: LaTeX syntax support (inline and display)
- **Wiki Links**: `[[Page Name]]` and `[[Page|Display Text]]` syntax
- **Footnotes**: Reference-style footnotes with content extraction
- **Task Lists**: GitHub-style checkboxes with nested support
- **Reference Definitions**: Link and image reference parsing

### MDX Support
- **JSX Components**: React component detection and analysis
- **Mixed Content**: Seamless handling of Markdown + JSX
- **Component Props**: Extraction of component properties

## Symbol Type Mapping

| Markdown Element | Symbol Type | Example |
|------------------|-------------|---------|
| Headers (# ## ###) | `class` | `# Introduction` |
| Code blocks | `function` | ` ```python ` |
| Reference definitions | `variable` | `[ref]: url` |
| Links | `import` | `[text](url)` |
| Images | `property` | `![alt](src)` |
| Tables | `struct` | `| col1 | col2 |` |
| Task lists | `enum` | `- [x] Done` |
| Math formulas | `constant` | `$x = y$` |
| Wiki links | `namespace` | `[[Page]]` |
| Front matter | `module` | `---\ntitle: foo\n---` |
| JSX components | `interface` | `<Component />` |

## Usage

```python
from mcp_server.plugins.markdown_plugin import Plugin

# Initialize the plugin
plugin = Plugin()

# Check if a file is supported
if plugin.supports("example.md"):
    # Index the file
    with open("example.md", "r") as f:
        content = f.read()
    
    result = plugin.indexFile("example.md", content)
    print(f"Found {len(result['symbols'])} symbols")
    
    # Analyze symbol types
    for symbol in result['symbols']:
        symbol_type = symbol.get('metadata', {}).get('type') or symbol['kind']
        print(f"- {symbol['symbol']} ({symbol_type})")
```

### Example Analysis Results

For a typical documentation file, you might see:
```
Found 25 symbols
- yaml_front_matter (yaml_front_matter)
- Introduction (class)
- Getting Started (class)
- code_block_python_15 (code_block)
- Configuration (class)
- table_line_28 (table)
- task_35 (task_list_item)
- API Reference (wiki_link)
- math_inline_42_156 (math_inline)
```

## Configuration

The plugin can be configured using the `plugin_config.json` file:

```json
{
  "plugin": {
    "name": "markdown",
    "language": "markdown",
    "version": "1.0.0",
    "type": "hybrid"
  },
  "extensions": [".md", ".markdown", ".mdx", ".mkd"],
  "features": {
    "tree_sitter_support": true,
    "caching": true,
    "async_processing": true,
    "semantic_analysis": true
  },
  "performance": {
    "max_file_size": 10485760,
    "cache_ttl": 3600,
    "batch_size": 100
  }
}
```

## Testing

Run comprehensive tests with:
```bash
pytest test_markdown_plugin.py -v
```

Test specific features:
```bash
# Test basic parsing
pytest test_markdown_plugin.py::TestMarkdownPlugin::test_basic_markdown_parsing

# Test front matter
pytest test_markdown_plugin.py::TestMarkdownPlugin::test_front_matter_extraction

# Test MDX support
pytest test_markdown_plugin.py::TestMarkdownPlugin::test_mdx_jsx_extraction
```

## Development

### Architecture

The plugin uses a hybrid approach:
1. **Tree-sitter** (primary): For accurate structural parsing
2. **Regex patterns** (fallback): For robustness and custom features
3. **Enhanced extraction**: Additional Markdown-specific processing

### Extending the Plugin

To add new Markdown features:

1. **Add regex patterns** in `get_regex_patterns()`
2. **Add Tree-sitter nodes** in `get_tree_sitter_node_types()`
3. **Implement custom extraction** in `_extract_markdown_specific_symbols()`
4. **Add test cases** in `test_markdown_plugin.py`

### Performance Optimizations

- **Caching**: Aggressive caching of parsed results
- **Lazy loading**: On-demand pattern compilation
- **Batch processing**: Efficient handling of large documents
- **Fallback strategy**: Graceful degradation when Tree-sitter fails

### Supported Markdown Variants

- ✅ **CommonMark**: Core Markdown specification
- ✅ **GitHub Flavored Markdown**: Tables, task lists, strikethrough
- ✅ **MDX**: React components in Markdown
- ✅ **Front matter**: YAML, TOML, JSON metadata
- ✅ **Math**: LaTeX formula support
- ✅ **Wiki-style**: Double-bracket links

## Use Cases

### Documentation Analysis
- **API Documentation**: Extract function signatures and examples
- **README Files**: Identify structure and key sections
- **Wiki Pages**: Track cross-references and links
- **Technical Blogs**: Analyze code examples and structure

### Content Management
- **Static Site Generators**: Hugo, Jekyll, Gatsby integration
- **Documentation Sites**: GitBook, Docusaurus, VitePress
- **Knowledge Management**: Obsidian, Roam Research, Notion
- **Blog Platforms**: Markdown-based publishing systems

### Development Workflows
- **Code Reviews**: Analyze documentation changes
- **Project Planning**: Extract task lists and progress
- **Knowledge Sharing**: Index team documentation
- **Learning Resources**: Structure educational content

## License

**MCP Server Team** - Version 1.0.0

This plugin demonstrates the power of hybrid parsing approaches for complex document formats, providing comprehensive analysis capabilities for modern Markdown workflows.
