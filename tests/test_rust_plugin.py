"""Test suite for Rust plugin."""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

from mcp_server.plugins.rust_plugin.plugin import Plugin
from mcp_server.storage.sqlite_store import SQLiteStore


class TestRustPlugin:
    """Test cases for Rust plugin functionality."""

    @pytest.fixture
    def rust_plugin(self):
        """Create a Rust plugin instance for testing."""
        return Plugin()

    @pytest.fixture
    def rust_plugin_with_sqlite(self, tmp_path):
        """Create a Rust plugin with SQLite storage."""
        db_path = tmp_path / "test.db"
        sqlite_store = SQLiteStore(str(db_path))
        return Plugin(sqlite_store=sqlite_store)

    @pytest.fixture
    def sample_rust_code(self):
        """Sample Rust code for testing."""
        return '''
/// A simple calculator struct
pub struct Calculator {
    value: f64,
}

impl Calculator {
    /// Create a new calculator
    pub fn new() -> Self {
        Calculator { value: 0.0 }
    }
    
    /// Add a value to the calculator
    pub fn add(&mut self, x: f64) -> &mut Self {
        self.value += x;
        self
    }
}

/// A trait for mathematical operations
pub trait MathOps {
    fn multiply(&self, x: f64) -> f64;
}

impl MathOps for Calculator {
    fn multiply(&self, x: f64) -> f64 {
        self.value * x
    }
}

/// An enum for different calculation modes
#[derive(Debug, Clone)]
pub enum CalcMode {
    Basic,
    Scientific,
    Programmer,
}

/// A constant for PI
pub const PI: f64 = 3.14159265359;

/// A static variable for the default mode
pub static DEFAULT_MODE: CalcMode = CalcMode::Basic;

/// Type alias for calculation result
pub type CalcResult = Result<f64, String>;

/// A simple module
pub mod utils {
    use super::*;
    
    /// Helper function
    pub fn format_result(value: f64) -> String {
        format!("{:.2}", value)
    }
}

use std::collections::HashMap;
use crate::utils::*;
'''

    @pytest.fixture
    def complex_rust_code(self):
        """More complex Rust code for testing."""
        return '''
//! Advanced data structures module
//! 
//! This module provides various data structures for efficient computation.

use std::collections::{HashMap, HashSet};
use std::sync::{Arc, Mutex};
use std::thread;

/// Generic container with lifetime parameters
pub struct Container<'a, T> 
where 
    T: Clone + Send + Sync,
{
    data: &'a [T],
    metadata: HashMap<String, String>,
}

impl<'a, T> Container<'a, T> 
where 
    T: Clone + Send + Sync,
{
    /// Create a new container
    pub fn new(data: &'a [T]) -> Self {
        Self {
            data,
            metadata: HashMap::new(),
        }
    }
    
    /// Get the length of the container
    pub fn len(&self) -> usize {
        self.data.len()
    }
    
    /// Check if the container is empty
    pub fn is_empty(&self) -> bool {
        self.data.is_empty()
    }
}

/// Async trait for processing
#[async_trait::async_trait]
pub trait AsyncProcessor {
    type Output;
    type Error;
    
    /// Process data asynchronously
    async fn process(&self, input: &[u8]) -> Result<Self::Output, Self::Error>;
    
    /// Validate input before processing
    fn validate(&self, input: &[u8]) -> bool {
        !input.is_empty()
    }
}

/// Error types for the module
#[derive(Debug, thiserror::Error)]
pub enum ProcessingError {
    #[error("Invalid input: {0}")]
    InvalidInput(String),
    #[error("Processing failed")]
    ProcessingFailed,
    #[error("Timeout occurred")]
    Timeout,
}

/// Configuration struct with builder pattern
#[derive(Debug, Clone)]
pub struct Config {
    pub timeout: u64,
    pub max_retries: u32,
    pub buffer_size: usize,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            timeout: 5000,
            max_retries: 3,
            buffer_size: 1024,
        }
    }
}

impl Config {
    /// Builder method for timeout
    pub fn with_timeout(mut self, timeout: u64) -> Self {
        self.timeout = timeout;
        self
    }
    
    /// Builder method for retries
    pub fn with_retries(mut self, retries: u32) -> Self {
        self.max_retries = retries;
        self
    }
}

/// Macro for creating configurations
macro_rules! config {
    ($timeout:expr, $retries:expr) => {
        Config {
            timeout: $timeout,
            max_retries: $retries,
            buffer_size: 1024,
        }
    };
}

/// Tests module
#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_container_creation() {
        let data = vec![1, 2, 3];
        let container = Container::new(&data);
        assert_eq!(container.len(), 3);
    }
}
'''

    def test_supports_rust_files(self, rust_plugin):
        """Test that plugin supports .rs files."""
        assert rust_plugin.supports("main.rs")
        assert rust_plugin.supports("lib.rs")
        assert rust_plugin.supports("src/main.rs")
        assert not rust_plugin.supports("main.py")
        assert not rust_plugin.supports("main.js")

    def test_plugin_initialization(self, rust_plugin):
        """Test plugin initialization."""
        assert rust_plugin.lang == "rust"
        # Parser may be None if tree-sitter version is incompatible
        # The plugin should still function with regex fallback

    def test_index_simple_rust_file(self, rust_plugin, sample_rust_code, tmp_path):
        """Test indexing a simple Rust file."""
        # Create a temporary Rust file
        rust_file = tmp_path / "calculator.rs"
        rust_file.write_text(sample_rust_code)
        
        # Index the file
        start_time = time.time()
        shard = rust_plugin.indexFile(str(rust_file), sample_rust_code)
        elapsed = time.time() - start_time
        
        # Check that indexing is fast (< 100ms target)
        assert elapsed < 0.1, f"Indexing took {elapsed*1000:.1f}ms, should be < 100ms"
        
        # Verify the shard structure
        assert shard["file"] == str(rust_file)
        assert shard["language"] == "rust"
        assert len(shard["symbols"]) > 0
        
        # Check for expected symbols
        symbol_names = [s["symbol"] for s in shard["symbols"]]
        assert "Calculator" in symbol_names
        assert "MathOps" in symbol_names
        assert "CalcMode" in symbol_names
        assert "PI" in symbol_names

    def test_extract_functions(self, rust_plugin, sample_rust_code, tmp_path):
        """Test extraction of function symbols."""
        rust_file = tmp_path / "calculator.rs"
        rust_file.write_text(sample_rust_code)
        
        shard = rust_plugin.indexFile(str(rust_file), sample_rust_code)
        
        # Find function symbols
        functions = [s for s in shard["symbols"] if s["kind"] == "function"]
        function_names = [f["symbol"] for f in functions]
        
        assert "new" in function_names
        assert "add" in function_names
        assert "multiply" in function_names
        assert "format_result" in function_names
        
        # Check function signature
        new_func = next(f for f in functions if f["symbol"] == "new")
        assert "fn new" in new_func["signature"]

    def test_extract_structs(self, rust_plugin, sample_rust_code, tmp_path):
        """Test extraction of struct symbols."""
        rust_file = tmp_path / "calculator.rs"
        rust_file.write_text(sample_rust_code)
        
        shard = rust_plugin.indexFile(str(rust_file), sample_rust_code)
        
        # Find struct symbols
        structs = [s for s in shard["symbols"] if s["kind"] == "struct"]
        struct_names = [s["symbol"] for s in structs]
        
        assert "Calculator" in struct_names
        
        # Check struct details
        calc_struct = next(s for s in structs if s["symbol"] == "Calculator")
        assert calc_struct["signature"] == "struct Calculator"
        assert calc_struct["visibility"] == "pub"

    def test_extract_traits(self, rust_plugin, sample_rust_code, tmp_path):
        """Test extraction of trait symbols."""
        rust_file = tmp_path / "calculator.rs"
        rust_file.write_text(sample_rust_code)
        
        shard = rust_plugin.indexFile(str(rust_file), sample_rust_code)
        
        # Find trait symbols
        traits = [s for s in shard["symbols"] if s["kind"] == "trait"]
        trait_names = [t["symbol"] for t in traits]
        
        assert "MathOps" in trait_names
        
        # Check trait details
        math_ops = next(t for t in traits if t["symbol"] == "MathOps")
        assert math_ops["signature"] == "trait MathOps"

    def test_extract_enums(self, rust_plugin, sample_rust_code, tmp_path):
        """Test extraction of enum symbols."""
        rust_file = tmp_path / "calculator.rs"
        rust_file.write_text(sample_rust_code)
        
        shard = rust_plugin.indexFile(str(rust_file), sample_rust_code)
        
        # Find enum symbols
        enums = [s for s in shard["symbols"] if s["kind"] == "enum"]
        enum_names = [e["symbol"] for e in enums]
        
        assert "CalcMode" in enum_names

    def test_extract_constants(self, rust_plugin, sample_rust_code, tmp_path):
        """Test extraction of constant symbols."""
        rust_file = tmp_path / "calculator.rs"
        rust_file.write_text(sample_rust_code)
        
        shard = rust_plugin.indexFile(str(rust_file), sample_rust_code)
        
        # Find constant symbols
        constants = [s for s in shard["symbols"] if s["kind"] in ["constant", "static"]]
        const_names = [c["symbol"] for c in constants]
        
        assert "PI" in const_names
        assert "DEFAULT_MODE" in const_names

    def test_extract_modules(self, rust_plugin, sample_rust_code, tmp_path):
        """Test extraction of module symbols."""
        rust_file = tmp_path / "calculator.rs"
        rust_file.write_text(sample_rust_code)
        
        shard = rust_plugin.indexFile(str(rust_file), sample_rust_code)
        
        # Find module symbols
        modules = [s for s in shard["symbols"] if s["kind"] == "module"]
        module_names = [m["symbol"] for m in modules]
        
        assert "utils" in module_names

    def test_extract_use_statements(self, rust_plugin, sample_rust_code, tmp_path):
        """Test extraction of use statements."""
        rust_file = tmp_path / "calculator.rs"
        rust_file.write_text(sample_rust_code)
        
        shard = rust_plugin.indexFile(str(rust_file), sample_rust_code)
        
        # Find import symbols
        imports = [s for s in shard["symbols"] if s["kind"] == "import"]
        
        assert len(imports) > 0
        
        # Check for specific imports
        import_symbols = [i["symbol"] for i in imports]
        assert any("HashMap" in imp for imp in import_symbols)

    def test_complex_rust_parsing(self, rust_plugin, complex_rust_code, tmp_path):
        """Test parsing of complex Rust code."""
        rust_file = tmp_path / "advanced.rs"
        rust_file.write_text(complex_rust_code)
        
        start_time = time.time()
        shard = rust_plugin.indexFile(str(rust_file), complex_rust_code)
        elapsed = time.time() - start_time
        
        # Should still be fast
        assert elapsed < 0.1, f"Complex parsing took {elapsed*1000:.1f}ms"
        
        # Check for complex symbols
        symbol_names = [s["symbol"] for s in shard["symbols"]]
        assert "Container" in symbol_names
        assert "AsyncProcessor" in symbol_names
        assert "ProcessingError" in symbol_names
        assert "Config" in symbol_names

    def test_get_definition(self, rust_plugin, sample_rust_code, tmp_path):
        """Test getting symbol definitions."""
        rust_file = tmp_path / "calculator.rs"
        rust_file.write_text(sample_rust_code)
        
        # Index the file first
        rust_plugin.indexFile(str(rust_file), sample_rust_code)
        
        # Get definition for Calculator
        definition = rust_plugin.getDefinition("Calculator")
        
        assert definition is not None
        assert definition["symbol"] == "Calculator"
        assert definition["kind"] == "struct"
        assert definition["language"] == "rust"
        assert "struct Calculator" in definition["signature"]

    def test_find_references(self, rust_plugin, sample_rust_code, tmp_path):
        """Test finding symbol references."""
        rust_file = tmp_path / "calculator.rs"
        rust_file.write_text(sample_rust_code)
        
        # Index the file first
        rust_plugin.indexFile(str(rust_file), sample_rust_code)
        
        # Find references to Calculator
        references = list(rust_plugin.findReferences("Calculator"))
        
        assert len(references) > 0
        
        # Check reference structure
        for ref in references:
            assert hasattr(ref, 'file')
            assert hasattr(ref, 'line')
            assert ref.file == str(rust_file)

    def test_search_functionality(self, rust_plugin, sample_rust_code, tmp_path):
        """Test search functionality."""
        rust_file = tmp_path / "calculator.rs"
        rust_file.write_text(sample_rust_code)
        
        # Index the file first
        rust_plugin.indexFile(str(rust_file), sample_rust_code)
        
        # Search for "Calculator"
        results = list(rust_plugin.search("Calculator"))
        
        assert len(results) > 0
        
        # Check result structure
        for result in results:
            assert "file" in result
            assert "line" in result
            assert "snippet" in result

    def test_performance_target(self, rust_plugin, tmp_path):
        """Test that parsing meets performance targets."""
        # Create a moderately sized Rust file
        large_rust_code = '''
pub struct TestStruct {
    field1: i32,
    field2: String,
}

impl TestStruct {
    pub fn new(field1: i32, field2: String) -> Self {
        Self { field1, field2 }
    }
}
''' * 50  # Repeat to create larger file
        
        rust_file = tmp_path / "large.rs"
        rust_file.write_text(large_rust_code)
        
        # Measure parsing time
        start_time = time.time()
        shard = rust_plugin.indexFile(str(rust_file), large_rust_code)
        elapsed = time.time() - start_time
        
        # Should be under 100ms target
        assert elapsed < 0.1, f"Large file parsing took {elapsed*1000:.1f}ms, should be < 100ms"
        
        # Should have found symbols
        assert len(shard["symbols"]) > 0

    def test_error_handling(self, rust_plugin, tmp_path):
        """Test error handling with invalid Rust code."""
        invalid_rust = "pub struct Incomplete {"
        
        rust_file = tmp_path / "invalid.rs"
        rust_file.write_text(invalid_rust)
        
        # Should not crash on invalid code
        shard = rust_plugin.indexFile(str(rust_file), invalid_rust)
        
        # Should return a shard even if parsing partially fails
        assert shard["file"] == str(rust_file)
        assert shard["language"] == "rust"

    def test_docstring_extraction(self, rust_plugin, tmp_path):
        """Test extraction of documentation comments."""
        rust_code_with_docs = '''
/// This is a documented struct
/// with multiple lines of documentation
pub struct DocumentedStruct {
    value: i32,
}

impl DocumentedStruct {
    /// Creates a new instance
    /// 
    /// # Arguments
    /// * `value` - The initial value
    pub fn new(value: i32) -> Self {
        Self { value }
    }
}
'''
        
        rust_file = tmp_path / "documented.rs"
        rust_file.write_text(rust_code_with_docs)
        
        shard = rust_plugin.indexFile(str(rust_file), rust_code_with_docs)
        
        # Find the documented struct
        documented_struct = next(
            (s for s in shard["symbols"] if s["symbol"] == "DocumentedStruct"), 
            None
        )
        
        assert documented_struct is not None
        assert documented_struct.get("docstring") is not None
        assert "documented struct" in documented_struct["docstring"]

    def test_sqlite_integration(self, rust_plugin_with_sqlite, sample_rust_code, tmp_path):
        """Test SQLite storage integration."""
        rust_file = tmp_path / "calculator.rs"
        rust_file.write_text(sample_rust_code)
        
        # Index with SQLite storage
        shard = rust_plugin_with_sqlite.indexFile(str(rust_file), sample_rust_code)
        
        # Should work the same as without SQLite
        assert len(shard["symbols"]) > 0
        
        # Verify SQLite store was used
        assert rust_plugin_with_sqlite._sqlite_store is not None
        assert rust_plugin_with_sqlite._repository_id is not None

    def test_visibility_extraction(self, rust_plugin, tmp_path):
        """Test extraction of visibility modifiers."""
        visibility_code = '''
pub struct PublicStruct;
struct PrivateStruct;
pub(crate) struct CrateStruct;

impl PublicStruct {
    pub fn public_method(&self) {}
    fn private_method(&self) {}
    pub(crate) fn crate_method(&self) {}
}
'''
        
        rust_file = tmp_path / "visibility.rs"
        rust_file.write_text(visibility_code)
        
        shard = rust_plugin.indexFile(str(rust_file), visibility_code)
        
        # Find structs and check visibility
        structs = [s for s in shard["symbols"] if s["kind"] == "struct"]
        
        public_struct = next(s for s in structs if s["symbol"] == "PublicStruct")
        assert public_struct["visibility"] == "pub"
        
        private_struct = next(s for s in structs if s["symbol"] == "PrivateStruct")
        assert private_struct["visibility"] == "private"

    @pytest.mark.performance
    def test_indexing_multiple_files(self, rust_plugin, tmp_path):
        """Test indexing multiple Rust files."""
        # Create multiple Rust files
        for i in range(10):
            rust_file = tmp_path / f"module_{i}.rs"
            rust_content = f'''
pub struct Module{i}Struct {{
    value: i32,
}}

impl Module{i}Struct {{
    pub fn new() -> Self {{
        Self {{ value: {i} }}
    }}
    
    pub fn process(&self) -> i32 {{
        self.value * 2
    }}
}}

pub fn module_{i}_function() -> i32 {{
    {i}
}}
'''
            rust_file.write_text(rust_content)
        
        # Measure total indexing time
        start_time = time.time()
        
        for i in range(10):
            rust_file = tmp_path / f"module_{i}.rs"
            content = rust_file.read_text()
            rust_plugin.indexFile(str(rust_file), content)
        
        elapsed = time.time() - start_time
        
        # Should index 10 files in reasonable time
        assert elapsed < 1.0, f"Indexing 10 files took {elapsed:.3f}s, should be < 1s"

    def test_get_indexed_count(self, rust_plugin, sample_rust_code, tmp_path):
        """Test getting the count of indexed files."""
        initial_count = rust_plugin.get_indexed_count()
        
        rust_file = tmp_path / "calculator.rs"
        rust_file.write_text(sample_rust_code)
        
        # Index a file
        rust_plugin.indexFile(str(rust_file), sample_rust_code)
        
        # Count should increase
        new_count = rust_plugin.get_indexed_count()
        assert new_count > initial_count