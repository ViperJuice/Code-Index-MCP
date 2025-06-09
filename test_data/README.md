# Test Data for Document Processing Plugins

This directory contains comprehensive test data files for testing the document processing capabilities of the MCP server plugins.

## Directory Structure

```
test_data/
├── markdown/           # Markdown-specific test files
├── plaintext/         # Plain text test files
├── mixed/            # Mixed content (real-world examples)
└── README.md         # This file
```

## Markdown Files (`/markdown`)

### simple.md (568 bytes)
- Basic markdown with headers and paragraphs
- Simple formatting (bold, italic, inline code)
- Hierarchical structure with subsections
- Tests basic markdown parsing capabilities

### complex.md (5.6KB)
- Comprehensive markdown features showcase
- Includes: frontmatter, tables, code blocks, lists, links, images
- Advanced features: footnotes, math expressions, HTML elements
- Tests full markdown specification support

### huge.md (134KB, 2846 lines)
- Large file for performance testing
- 50 sections with varied content
- Includes code blocks, tables, lists, and blockquotes
- Tests scalability and memory efficiency

### api_docs.md (8.8KB)
- API documentation format
- REST endpoints with request/response examples
- Code snippets in multiple languages
- Tests technical documentation parsing

### tutorial.md (12KB)
- Tutorial/guide format with step-by-step instructions
- Mixed content: prose, code, commands
- Table of contents and navigation
- Tests educational content processing

## Plaintext Files (`/plaintext`)

### simple.txt (1.7KB)
- Basic text with clear paragraph structure
- Natural language content about code indexing
- Tests paragraph detection and basic chunking

### technical.txt (4.1KB)
- Technical specification document
- Structured with numbered sections
- Includes code-like content and technical terms
- Tests handling of technical documentation

### natural.txt (4.6KB)
- Natural language narrative content
- Essay-style writing about software development
- Tests NLP features and topic extraction

### structured.txt (6.4KB)
- Highly structured document with clear sections
- Uses consistent formatting patterns
- Contains lists, subsections, and hierarchy
- Tests structure detection algorithms

### huge.txt (117KB, 2184 lines)
- Large plaintext file for performance testing
- 20 major sections with varied content
- Includes glossary and appendices
- Tests scalability for large documents

## Mixed Content Files (`/mixed`)

### project_readme.md (5.6KB)
- Realistic GitHub project README
- Includes badges, installation instructions, examples
- Mixed markdown features
- Tests real-world markdown processing

### changelog.txt (5.1KB)
- Version changelog in Keep a Changelog format
- Structured with versions and categories
- Date stamps and version numbers
- Tests parsing of semi-structured text

### installation.md (8.8KB)
- Comprehensive installation guide
- Platform-specific instructions
- Code blocks and commands
- Tests technical guide processing

## Usage

These files can be used to test various aspects of document processing:

1. **Parsing accuracy**: Ensure correct extraction of structure
2. **Performance**: Test with huge.md and huge.txt files
3. **Feature coverage**: Use complex.md for comprehensive testing
4. **Real-world scenarios**: Use files in /mixed directory
5. **Edge cases**: Test with various formatting styles

## Test Scenarios

### Basic Functionality
```python
# Test simple parsing
doc = parse_document("test_data/markdown/simple.md")
assert len(doc.sections) > 0
```

### Performance Testing
```python
# Test large file handling
start = time.time()
doc = parse_document("test_data/markdown/huge.md")
elapsed = time.time() - start
assert elapsed < 5.0  # Should parse in under 5 seconds
```

### Feature Testing
```python
# Test markdown features
doc = parse_document("test_data/markdown/complex.md")
assert doc.has_frontmatter
assert len(doc.code_blocks) > 0
assert len(doc.tables) > 0
```

## Adding New Test Files

When adding new test files:

1. Choose appropriate directory based on format
2. Use descriptive names indicating the test purpose
3. Include varied content to test different features
4. Document the file's purpose in this README
5. Consider file size for performance testing

## Notes

- All files use UTF-8 encoding
- Line endings are Unix-style (LF)
- No binary content included
- Files represent realistic use cases
- Content is safe for public repositories