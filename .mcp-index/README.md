# MCP Index Directory

This directory contains the code index for this repository, managed by the MCP Index Kit.

## Contents

- `code_index.db` - SQLite database containing code symbols and search index
- `.index_metadata.json` - Metadata about the index (version, creation time, etc.)

## Usage

The index is automatically managed by GitHub Actions. To use it locally:

1. Install the MCP extension for your IDE
2. The extension will automatically detect and use this index
3. Enjoy fast code navigation and search!

## Disabling

To disable MCP indexing:
1. Set `MCP_INDEX_ENABLED=false` in your repository settings
2. Or delete the `.github/workflows/mcp-index.yml` file
3. Or set `"enabled": false` in `.mcp-index.json`

## More Information

Visit https://github.com/yourusername/Code-Index-MCP for more details.
