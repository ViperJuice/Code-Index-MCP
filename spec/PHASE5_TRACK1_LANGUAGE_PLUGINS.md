# Phase 5 Track 1: Language Plugins Specification

## Overview

Extend Code-Index-MCP with comprehensive support for 5 additional programming languages through Tree-sitter-based plugins. This track focuses on language plugin development with no external dependencies, enabling immediate parallel execution.

**Timeline**: 8-12 weeks  
**Dependencies**: None (can start immediately)

---

## Phase 1: Rust Plugin

### Requirements

**Must Have:**
- Parse Rust source files using tree-sitter-rust
- Extract symbols:
  - Functions (fn, async fn, unsafe fn, const fn)
  - Structs (struct, tuple structs, unit structs)
  - Enums (enum with variants)
  - Traits (trait definitions and implementations)
  - Modules (mod, use declarations)
  - Macros (macro_rules!)
- Handle Rust-specific features:
  - Generics and lifetime parameters
  - Associated types and constants
  - Impl blocks (inherent and trait implementations)
- Parse Cargo.toml for metadata
- Support for .rs files

**Performance Targets:**
- Parse 1000 lines/second minimum
- <100ms for typical Rust source file
- Handle large projects (tokio, actix) without degradation

**Test Projects:**
- tokio (async runtime)
- actix-web (web framework)
- serde (serialization framework)

### Acceptance Criteria

1. All "Must Have" requirements implemented
2. Test coverage >90%
3. Passes integration tests with test projects
4. Performance targets met
5. Documentation complete (README, AGENTS)
6. Successfully indexes at least 2 real-world projects

---

## Cross-Plugin Requirements

### Plugin Architecture

All plugins must:
- Extend TreeSitterPluginBase
- Implement standard interface:
  - `parse_file(file_path: Path) -> List[Symbol]`
  - `extract_imports(file_path: Path) -> List[Import]`
- Use tree-sitter for parsing
- Handle parse errors gracefully

### Symbol Schema

```python
{
    "name": str,
    "kind": str,
    "line_start": int,
    "line_end": int,
    "signature": str,
    "documentation": str,
    "metadata": {...}
}
```

### Testing Requirements

- Unit tests (90%+ coverage)
- Integration tests with real project files
- Performance benchmarks
- Test data from actual open-source projects
