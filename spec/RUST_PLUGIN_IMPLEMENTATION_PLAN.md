# Rust Plugin Implementation Plan
**Phase**: Phase 5 Track 1 - Rust Plugin  
**Spec**: PHASE5_TRACK1_LANGUAGE_PLUGINS.md  
**Status**: Ready for execution

---

## A. Architectural Baseline & Component Catalog

### 1. Files to Add

**Plugin Core:**
- `mcp_server/plugins/rust_plugin/__init__.py` - NEW
- `mcp_server/plugins/rust_plugin/plugin.py` - NEW
- `mcp_server/plugins/rust_plugin/AGENTS.md` - NEW
- `mcp_server/plugins/rust_plugin/README.md` - NEW
- `mcp_server/plugins/rust_plugin/plugin_config.json` - NEW

**Tree-sitter Queries:**
- `mcp_server/plugins/rust_plugin/queries/highlights.scm` - NEW
- `mcp_server/plugins/rust_plugin/queries/symbols.scm` - NEW

**Test Files:**
- `mcp_server/plugins/rust_plugin/test_data/sample.rs` - NEW
- `mcp_server/plugins/rust_plugin/test_data/Cargo.toml` - NEW
- `tests/test_rust_plugin.py` - NEW

### 2. Files to Modify

- `mcp_server/plugins/__init__.py` - MODIFY (add rust_plugin import)
- `plugins.yaml` - MODIFY (register rust plugin)
- `pyproject.toml` - MODIFY (add tree-sitter-rust dependency)

### 3. Classes / Types

**RustPlugin** (`mcp_server/plugins/rust_plugin/plugin.py`)
- Class: NEW
- Base: TreeSitterPluginBase
- Visibility: Public
- Purpose: Parse Rust files and extract symbols

### 4. Key Methods

**RustPlugin.parse_file()**
- Signature: `parse_file(file_path: Path) -> List[Symbol]`
- Returns: List of Symbol objects
- Errors: Raises ParseError on invalid syntax

**RustPlugin.extract_symbols()**  
- Signature: `extract_symbols(tree: Tree, source: bytes) -> List[Symbol]`
- Returns: List of Symbol dictionaries
- Errors: None (graceful degradation)

**RustPlugin.extract_cargo_metadata()**
- Signature: `extract_cargo_metadata(cargo_path: Path) -> Dict[str, Any]`
- Returns: Package metadata dictionary
- Errors: Returns empty dict on failure

### 5. Data Structures

**RustSymbol** (extends base Symbol):
```python
{
    "name": str,
    "kind": str,  # "function", "struct", "enum", "trait", "macro"
    "line_start": int,
    "line_end": int,
    "signature": str,
    "metadata": {
        "visibility": str,  # "pub", "pub(crate)", "private"
        "is_async": bool,
        "is_unsafe": bool,
        "is_const": bool,
        "generics": List[str],
        "lifetimes": List[str],
        "trait_impl": Optional[str]
    }
}
```

---

## B. Code-Level Interface Contracts

### Interface 1: Plugin Registration

**Owner**: Rust Plugin  
**Consumers**: PluginManager

**Contract**:
```python
# File: mcp_server/plugins/rust_plugin/__init__.py
from .plugin import RustPlugin

__all__ = ["RustPlugin"]
```

**Freeze Gate**: IF-RUST-001
- Plugin must expose RustPlugin class
- Must be importable via mcp_server.plugins.rust_plugin

### Interface 2: Symbol Extraction API

**Owner**: Rust Plugin  
**Consumers**: Indexer, MCP Gateway

**Contract**:
```python
def parse_file(file_path: Path) -> List[Symbol]:
    """Parse a Rust file and return symbols.
    
    Args:
        file_path: Path to .rs file
        
    Returns:
        List of Symbol objects with Rust-specific metadata
        
    Raises:
        ParseError: If file cannot be parsed
        FileNotFoundError: If file doesn't exist
    """
```

**Freeze Gate**: IF-RUST-002
- Return type must match Symbol schema
- Must handle all Rust symbol kinds listed in requirements

### Interface 3: Tree-sitter Queries

**Owner**: Rust Plugin  
**Consumers**: Internal (symbol extraction)

**Contract**:
- `queries/symbols.scm` must define captures for:
  - `@function.definition`
  - `@struct.definition`
  - `@enum.definition`
  - `@trait.definition`
  - `@macro.definition`

**Freeze Gate**: IF-RUST-003
- Query file must be present before implementation
- All symbol kinds must have corresponding captures

---

## C. Swim Lane Decomposition

### Lane 1: Plugin Foundation & Tree-sitter Integration
**Owner**: Developer A  
**Duration**: 3 days  
**Dependencies**: None  
**Blocks**: Lanes 2, 3, 4

**Tasks**:
1. Create plugin directory structure
2. Install tree-sitter-rust parser
3. Create base RustPlugin class extending TreeSitterPluginBase
4. Implement file detection (.rs files)
5. Write basic tree-sitter query file (symbols.scm)
6. Create minimal test file (sample.rs)
7. Verify tree-sitter can parse test file

**Deliverables**:
- `mcp_server/plugins/rust_plugin/plugin.py` (skeleton)
- `mcp_server/plugins/rust_plugin/queries/symbols.scm` (basic)
- `mcp_server/plugins/rust_plugin/test_data/sample.rs`
- Passing smoke test: plugin can load and parse simple Rust file

**Acceptance**:
- Tree-sitter-rust successfully parses test file
- Plugin class instantiates without errors
- Basic query returns at least one symbol

---

### Lane 2: Core Symbol Extraction
**Owner**: Developer B  
**Duration**: 4 days  
**Dependencies**: Lane 1 (IF-RUST-001, IF-RUST-003)  
**Blocks**: Lane 4

**Tasks**:
1. Implement function extraction (fn, async fn, unsafe fn, const fn)
2. Implement struct extraction (struct, tuple struct, unit struct)
3. Implement enum extraction (enum with variants)
4. Implement trait extraction (trait definitions)
5. Implement impl block extraction (inherent and trait impls)
6. Handle visibility modifiers (pub, pub(crate), private)
7. Extract signatures and documentation
8. Write unit tests for each symbol type

**Deliverables**:
- Complete `extract_symbols()` method
- Updated `queries/symbols.scm` with all symbol patterns
- Unit tests for all symbol types (>80% coverage)

**Acceptance**:
- All symbol types extracted correctly
- Visibility and modifiers detected properly
- Unit tests pass with >80% coverage

---

### Lane 3: Rust-Specific Features
**Owner**: Developer C  
**Duration**: 3 days  
**Dependencies**: Lane 1 (IF-RUST-001)  
**Blocks**: Lane 4

**Tasks**:
1. Extract generics and type parameters
2. Extract lifetime parameters
3. Handle macro definitions (macro_rules!)
4. Extract module declarations
5. Parse use statements for imports
6. Implement Cargo.toml parser
7. Write integration tests with real Rust code

**Deliverables**:
- `extract_cargo_metadata()` method
- Generic/lifetime extraction logic
- Macro extraction support
- Integration tests with tokio/serde sample files

**Acceptance**:
- Generics correctly extracted from complex types
- Cargo.toml metadata parsed successfully
- Macros detected and cataloged

---

### Lane 4: Testing & Documentation
**Owner**: Developer D  
**Duration**: 2 days  
**Dependencies**: Lanes 2, 3  
**Blocks**: None

**Tasks**:
1. Create comprehensive test suite
2. Download and test with tokio codebase
3. Download and test with actix-web codebase
4. Benchmark parsing performance
5. Write README.md with usage examples
6. Write AGENTS.md for AI assistance
7. Add plugin to registry (plugins.yaml)
8. Update main __init__.py

**Deliverables**:
- Complete test suite (>90% coverage)
- Performance benchmarks
- README.md and AGENTS.md
- Plugin registered in system

**Acceptance**:
- Test coverage >90%
- Performance meets targets (1000 lines/sec, <100ms)
- Successfully indexes tokio and actix-web
- Documentation complete

---

## D. Execution Plan

### Week 1

**Days 1-3**: Lanes 1, 2, 3 start in parallel
- Lane 1: Foundation complete by EOD Day 3
- Lane 2: 50% complete (functions, structs)
- Lane 3: 50% complete (generics, Cargo.toml)

**Days 4-5**: Lanes 2, 3 continue
- Lane 2: Complete all symbol extraction
- Lane 3: Complete Rust-specific features

### Week 2

**Days 1-2**: Lane 4 executes
- Testing, documentation, integration

**Day 3**: Final review and merge
- Code review
- Integration testing
- Merge to main branch

---

## E. Interface Freeze Gates

### Gate IF-RUST-001: Plugin Registration
**Frozen**: Before Lane 2, 3 start  
**Verifiable by**: Successfully importing RustPlugin class

### Gate IF-RUST-002: Symbol Schema
**Frozen**: Before Lane 2 starts  
**Verifiable by**: Symbol dictionary matches spec schema

### Gate IF-RUST-003: Tree-sitter Queries
**Frozen**: Before Lane 2 starts  
**Verifiable by**: symbols.scm exists with basic patterns

---

## F. Risk Management

**Risk**: Tree-sitter-rust grammar incomplete for advanced features
- **Mitigation**: Test with real projects early (tokio)
- **Fallback**: Document limitations, iterate in v2

**Risk**: Performance degradation on large files
- **Mitigation**: Profile and optimize hot paths
- **Fallback**: Implement timeout/size limits

**Risk**: Macro expansion complexity
- **Mitigation**: Start with macro_rules! only, defer procedural macros
- **Fallback**: Basic macro cataloging without expansion

---

## G. Success Metrics

### Functional
- ✅ All symbol types extracted correctly
- ✅ Parses tokio codebase without errors
- ✅ Parses actix-web codebase without errors

### Performance
- ✅ >1000 lines/second parsing speed
- ✅ <100ms per typical file
- ✅ <10% memory overhead

### Quality
- ✅ >90% test coverage
- ✅ Zero P0/P1 bugs
- ✅ Documentation complete

---

## H. Next Actions

1. **Create feature branch**: `git checkout -b feature/phase5-rust-plugin`
2. **Execute lanes using slash command**: `/execute-lane RUST_PLUGIN_IMPLEMENTATION_PLAN.md "Lane 1"`
3. **After Lane 1 completes**: Freeze interfaces and start Lanes 2, 3 in parallel
4. **After Lanes 2, 3 complete**: Execute Lane 4
5. **Review and merge**: Create PR to main branch

---

## I. Swim Lane Task Lists

### Lane 1 Tasks (Checkboxes)
- [ ] Create `mcp_server/plugins/rust_plugin/` directory
- [ ] Add `tree-sitter-rust` to pyproject.toml
- [ ] Create `__init__.py` with RustPlugin export
- [ ] Create base `plugin.py` extending TreeSitterPluginBase
- [ ] Create `queries/symbols.scm` with basic patterns
- [ ] Create `test_data/sample.rs` with basic Rust code
- [ ] Write smoke test to verify parsing works
- [ ] **Gate**: Verify IF-RUST-001 (plugin importable)

### Lane 2 Tasks (Checkboxes)
- [ ] Implement function extraction in `extract_symbols()`
- [ ] Implement struct extraction
- [ ] Implement enum extraction
- [ ] Implement trait extraction
- [ ] Implement impl block extraction
- [ ] Add visibility modifier detection
- [ ] Extract function signatures
- [ ] Extract documentation comments
- [ ] Write unit test for functions
- [ ] Write unit test for structs
- [ ] Write unit test for enums
- [ ] Write unit test for traits
- [ ] **Gate**: Verify IF-RUST-002 (symbol schema compliance)

### Lane 3 Tasks (Checkboxes)
- [ ] Add generic parameter extraction
- [ ] Add lifetime parameter extraction
- [ ] Implement macro_rules! extraction
- [ ] Implement module declaration extraction
- [ ] Implement use statement extraction
- [ ] Create `extract_cargo_metadata()` method
- [ ] Parse Cargo.toml dependencies
- [ ] Test with tokio sample files
- [ ] Test with serde sample files

### Lane 4 Tasks (Checkboxes)
- [ ] Download tokio codebase for testing
- [ ] Download actix-web codebase for testing
- [ ] Run comprehensive test suite
- [ ] Benchmark parsing performance
- [ ] Verify >1000 lines/sec throughput
- [ ] Verify <100ms per file
- [ ] Write README.md
- [ ] Write AGENTS.md
- [ ] Add plugin to plugins.yaml
- [ ] Update mcp_server/plugins/__init__.py
- [ ] Create PR to main
