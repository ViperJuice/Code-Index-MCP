# Code Index MCP Server

[![Build Status](https://img.shields.io/github/workflow/status/codeindex/mcp-server/CI)](https://github.com/codeindex/mcp-server/actions)
[![Coverage](https://img.shields.io/codecov/c/github/codeindex/mcp-server)](https://codecov.io/gh/codeindex/mcp-server)
[![License](https://img.shields.io/github/license/codeindex/mcp-server)](LICENSE)
[![Python Version](https://img.shields.io/pypi/pyversions/code-index-mcp)](https://pypi.org/project/code-index-mcp/)

A high-performance code indexing and search server that provides instant code navigation across multiple programming languages.

## Features

- 🚀 **Fast Search**: Sub-millisecond search across millions of lines of code
- 🔍 **Smart Indexing**: Language-aware parsing for accurate results
- 🌐 **Multi-Language**: Support for Python, JavaScript, Go, Java, C++, and more
- 🔄 **Real-time Updates**: Automatic index updates on file changes
- 🧩 **Extensible**: Plugin architecture for adding new languages
- 📊 **Analytics**: Code metrics and quality analysis
- 🤖 **AI-Powered**: Semantic search using embeddings

## Quick Start

### Installation

```bash
pip install code-index-mcp
```

### Basic Usage

```bash
# Start the server
mcp-server start

# Index a repository
mcp-cli index /path/to/your/project

# Search for code
mcp-cli search "class UserManager"
```

## Documentation

- [Getting Started Guide](docs/getting-started.md)
- [API Reference](docs/api-reference.md)
- [Plugin Development](docs/plugin-development.md)
- [Configuration Options](docs/configuration.md)

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   CLI/API   │────▶│ Dispatcher  │────▶│   Plugins   │
└─────────────┘     └─────────────┘     └─────────────┘
                            │                    │
                            ▼                    ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   Indexer   │     │   Storage   │
                    └─────────────┘     └─────────────┘
```

## Supported Languages

| Language | File Extensions | Features |
|----------|----------------|----------|
| Python | `.py`, `.pyi` | Classes, functions, imports, decorators |
| JavaScript | `.js`, `.jsx`, `.mjs` | Functions, classes, exports, JSX |
| TypeScript | `.ts`, `.tsx` | Types, interfaces, generics |
| Go | `.go` | Functions, types, interfaces, packages |
| Java | `.java` | Classes, methods, packages, annotations |
| C/C++ | `.c`, `.cpp`, `.h` | Functions, classes, macros, includes |
| Rust | `.rs` | Functions, structs, traits, modules |
| Ruby | `.rb` | Classes, modules, methods |

## Configuration

Create a `~/.mcp/config.yaml` file:

```yaml
server:
  port: 8000
  workers: 4

indexing:
  ignore_patterns:
    - "*.pyc"
    - "node_modules"
    - ".git"
  max_file_size: 5MB

plugins:
  python:
    enabled: true
    analyze_imports: true
  javascript:
    enabled: true
    parse_jsx: true
```

## Development

### Prerequisites

- Python 3.8+
- Git
- Redis (optional, for caching)

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/codeindex/mcp-server.git
cd mcp-server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Run tests
pytest
```

### Running Tests

```bash
# Unit tests
pytest tests/unit

# Integration tests
pytest tests/integration

# With coverage
pytest --cov=mcp_server --cov-report=html
```

## Performance

Benchmarks on a typical developer machine (Intel i7, 16GB RAM, SSD):

| Operation | Small Project (1K files) | Medium Project (10K files) | Large Project (100K files) |
|-----------|-------------------------|---------------------------|---------------------------|
| Initial Index | < 5 seconds | < 30 seconds | < 5 minutes |
| Incremental Update | < 100ms | < 500ms | < 2 seconds |
| Symbol Search | < 10ms | < 20ms | < 50ms |
| Full-text Search | < 50ms | < 100ms | < 500ms |

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

We use:
- `black` for code formatting
- `flake8` for linting
- `mypy` for type checking

Run `make lint` to check your code before submitting.

## Community

- **Discord**: [Join our server](https://discord.gg/codeindex)
- **Twitter**: [@codeindex](https://twitter.com/codeindex)
- **Blog**: [blog.codeindex.dev](https://blog.codeindex.dev)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Tree-sitter for language parsing
- All our contributors and users
- Open source projects that inspired us

## Roadmap

- [ ] Cloud-hosted version
- [ ] IDE plugins (VS Code, IntelliJ)
- [ ] Advanced refactoring support
- [ ] Multi-repository search
- [ ] Code similarity detection
- [ ] Security vulnerability scanning

---

Made with ❤️ by the Code Index team