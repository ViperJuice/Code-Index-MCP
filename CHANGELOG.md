# Changelog

All notable changes to Code-Index-MCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure with plugin-based architecture
- FastAPI-based MCP server implementation
- Python plugin with Jedi integration for advanced code analysis
- Tree-sitter wrapper for language parsing
- Semantic indexer with Voyage AI integration
- C4 architecture diagrams using Structurizr DSL
- Comprehensive documentation structure
- Plugin base class for language extensions
- File watcher skeleton for real-time updates
- Cloud sync stub implementation

### Changed
- Enhanced Python plugin with proper AST analysis
- Improved error handling in gateway endpoints
- Updated project documentation and README

### Fixed
- Resolved merge conflicts in treesitter_wrapper.py
- Fixed Python plugin implementation issues

### Security
- Added input validation for file paths
- Implemented basic security checks in API endpoints
- Added secret detection patterns

## [0.1.0] - TBD

### Planned Features
- Complete implementation of C, C++, JavaScript, Dart, and HTML/CSS plugins
- SQLite-based local storage with FTS5
- Full file system watcher implementation
- Performance optimizations and caching
- Authentication and authorization system
- Comprehensive test suite
- Production deployment guide

---

## Version History

### Pre-release Development
- Project inception and architecture design
- Core infrastructure setup
- Initial plugin system implementation