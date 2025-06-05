#!/usr/bin/env python3
"""
Example plugin using the new template system.

This example demonstrates how to create a language plugin using the
comprehensive template system. It shows different approaches for
different types of plugins.
"""

from typing import Dict, List, Optional, Set
from pathlib import Path

from mcp_server.plugins import (
    # Base classes
    LanguagePluginBase,
    TreeSitterPluginBase,
    RegexPluginBase,
    HybridPluginBase,
    
    # Data structures
    SymbolType,
    ParsedSymbol,
    PluginConfig,
    RegexPattern,
    
    # Utilities
    SymbolExtractor,
    FileAnalyzer,
    timing_decorator,
    cached_method
)


# Example 1: Simple Language Plugin using LanguagePluginBase
class SimpleLuaPlugin(LanguagePluginBase):
    """Simple Lua plugin using basic pattern matching."""
    
    def get_language(self) -> str:
        return "lua"
    
    def get_supported_extensions(self) -> List[str]:
        return [".lua"]
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        """Basic regex patterns for Lua."""
        return {
            SymbolType.FUNCTION: r"function\s+([a-zA-Z_][a-zA-Z0-9_.:]*)",
            SymbolType.VARIABLE: r"local\s+([a-zA-Z_][a-zA-Z0-9_]*)",
            SymbolType.MODULE: r"module\s*\(\s*['\"]([^'\"]+)['\"]"
        }
    
    def supports_tree_sitter(self) -> bool:
        """Simple plugin doesn't use Tree-sitter."""
        return False


# Example 2: Tree-sitter-based Plugin
class TypeScriptTreeSitterPlugin(TreeSitterPluginBase):
    """TypeScript plugin using Tree-sitter parsing."""
    
    def get_language(self) -> str:
        return "typescript"
    
    def get_supported_extensions(self) -> List[str]:
        return [".ts", ".tsx"]
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        """Fallback patterns for TypeScript."""
        return {
            SymbolType.FUNCTION: r"function\s+(\w+)|(\w+)\s*=\s*\([^)]*\)\s*=>",
            SymbolType.CLASS: r"class\s+(\w+)",
            SymbolType.INTERFACE: r"interface\s+(\w+)",
            SymbolType.TYPE: r"type\s+(\w+)",
            SymbolType.VARIABLE: r"(?:const|let|var)\s+(\w+)",
            SymbolType.IMPORT: r"import.*?from\s+['\"]([^'\"]+)['\"]"
        }
    
    def get_node_types(self) -> Dict[SymbolType, List[str]]:
        """Tree-sitter node types for TypeScript."""
        return {
            SymbolType.FUNCTION: [
                "function_declaration",
                "function_expression", 
                "arrow_function",
                "method_definition"
            ],
            SymbolType.CLASS: ["class_declaration"],
            SymbolType.INTERFACE: ["interface_declaration"],
            SymbolType.TYPE: ["type_alias_declaration"],
            SymbolType.VARIABLE: [
                "variable_declaration",
                "lexical_declaration"
            ],
            SymbolType.IMPORT: ["import_statement"]
        }
    
    def get_query_patterns(self) -> Dict[str, str]:
        """Advanced Tree-sitter queries for TypeScript."""
        return {
            "functions": """
                (function_declaration
                  name: (identifier) @name) @function
                (method_definition
                  name: (property_name) @name) @method
            """,
            "classes": """
                (class_declaration
                  name: (type_identifier) @name) @class
            """,
            "interfaces": """
                (interface_declaration
                  name: (type_identifier) @name) @interface
            """,
            "exports": """
                (export_statement
                  declaration: (_) @exported)
            """
        }
    
    def _extract_docstring_from_node(self, node, content: str) -> Optional[str]:
        """Extract JSDoc comments for TypeScript."""
        # Look for preceding comment nodes
        prev_sibling = node.prev_sibling
        while prev_sibling and prev_sibling.type in ["comment"]:
            comment_text = content[prev_sibling.start_byte:prev_sibling.end_byte]
            if comment_text.startswith("/**"):
                # Clean up JSDoc comment
                lines = comment_text.split('\n')
                cleaned_lines = []
                for line in lines:
                    line = line.strip()
                    if line.startswith("/**") or line.startswith("*/"):
                        continue
                    if line.startswith("*"):
                        line = line[1:].strip()
                    if line:
                        cleaned_lines.append(line)
                return '\n'.join(cleaned_lines)
            prev_sibling = prev_sibling.prev_sibling
        
        return None
    
    def _extract_modifiers_from_node(self, node, content: str) -> Set[str]:
        """Extract TypeScript modifiers."""
        modifiers = set()
        
        # Look for modifier children
        for child in node.children:
            if child.type in [
                "public", "private", "protected", "static", 
                "abstract", "readonly", "async", "export"
            ]:
                modifiers.add(child.type)
        
        # Check parent for export
        if node.parent and node.parent.type == "export_statement":
            modifiers.add("export")
        
        return modifiers


# Example 3: Regex-based Plugin
class KotlinRegexPlugin(RegexPluginBase):
    """Kotlin plugin using comprehensive regex patterns."""
    
    def get_language(self) -> str:
        return "kotlin"
    
    def get_supported_extensions(self) -> List[str]:
        return [".kt", ".kts"]
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        """Basic patterns for fallback."""
        return {
            SymbolType.FUNCTION: r"fun\s+(\w+)",
            SymbolType.CLASS: r"class\s+(\w+)",
            SymbolType.VARIABLE: r"(?:val|var)\s+(\w+)"
        }
    
    def get_regex_patterns(self) -> List[RegexPattern]:
        """Detailed regex patterns for Kotlin."""
        return [
            # Functions
            RegexPattern(
                pattern=r"(?:public|private|protected|internal)?\s*(?:suspend\s+)?fun\s+(\w+)\s*\(",
                symbol_type=SymbolType.FUNCTION,
                name_group=1,
                signature_group=0,
                flags=re.MULTILINE
            ),
            
            # Classes
            RegexPattern(
                pattern=r"(?:public|private|protected|internal)?\s*(?:abstract|open|final)?\s*class\s+(\w+)",
                symbol_type=SymbolType.CLASS,
                name_group=1,
                signature_group=0,
                flags=re.MULTILINE
            ),
            
            # Interfaces
            RegexPattern(
                pattern=r"(?:public|private|protected|internal)?\s*interface\s+(\w+)",
                symbol_type=SymbolType.INTERFACE,
                name_group=1,
                signature_group=0,
                flags=re.MULTILINE
            ),
            
            # Data classes
            RegexPattern(
                pattern=r"(?:public|private|protected|internal)?\s*data\s+class\s+(\w+)",
                symbol_type=SymbolType.CLASS,
                name_group=1,
                signature_group=0,
                flags=re.MULTILINE
            ),
            
            # Properties
            RegexPattern(
                pattern=r"(?:public|private|protected|internal)?\s*(?:val|var)\s+(\w+)\s*:",
                symbol_type=SymbolType.PROPERTY,
                name_group=1,
                signature_group=0,
                flags=re.MULTILINE
            ),
            
            # Object declarations
            RegexPattern(
                pattern=r"(?:public|private|protected|internal)?\s*object\s+(\w+)",
                symbol_type=SymbolType.CLASS,  # Treat objects as classes
                name_group=1,
                signature_group=0,
                flags=re.MULTILINE
            )
        ]
    
    def get_multi_line_patterns(self) -> Dict[SymbolType, RegexPattern]:
        """Multi-line patterns for Kotlin."""
        patterns = super().get_multi_line_patterns()
        
        # Add Kotlin-specific multi-line patterns
        patterns[SymbolType.CLASS] = RegexPattern(
            pattern=r'((?:public|private|protected|internal)?\s*(?:abstract|open|final)?\s*class\s+\w+.*?)(?=\n(?:public|private|protected|internal)?\s*(?:class|fun|val|var|object)|$)',
            flags=re.MULTILINE | re.DOTALL,
            symbol_type=SymbolType.CLASS
        )
        
        return patterns
    
    def get_context_patterns(self) -> Dict[str, RegexPattern]:
        """Kotlin-specific context patterns."""
        patterns = super().get_context_patterns()
        
        # KDoc comments
        patterns["kdoc"] = RegexPattern(
            pattern=r'/\*\*(.*?)\*/',
            flags=re.MULTILINE | re.DOTALL
        )
        
        # Annotations
        patterns["annotation"] = RegexPattern(
            pattern=r'@(\w+)(?:\([^)]*\))?',
            flags=re.MULTILINE
        )
        
        # Imports
        patterns["import"] = RegexPattern(
            pattern=r'import\s+([\w.]+)(?:\s+as\s+(\w+))?',
            flags=re.MULTILINE
        )
        
        return patterns


# Example 4: Hybrid Plugin
class SwiftHybridPlugin(HybridPluginBase):
    """Swift plugin using Tree-sitter with regex fallback."""
    
    def get_language(self) -> str:
        return "swift"
    
    def get_supported_extensions(self) -> List[str]:
        return [".swift"]
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        """Fallback patterns for Swift."""
        return {
            SymbolType.FUNCTION: r"func\s+(\w+)",
            SymbolType.CLASS: r"class\s+(\w+)",
            SymbolType.STRUCT: r"struct\s+(\w+)",
            SymbolType.ENUM: r"enum\s+(\w+)",
            SymbolType.VARIABLE: r"(?:var|let)\s+(\w+)",
            SymbolType.IMPORT: r"import\s+(\w+)"
        }
    
    def get_tree_sitter_node_types(self) -> Dict[SymbolType, List[str]]:
        """Tree-sitter node types for Swift."""
        return {
            SymbolType.FUNCTION: [
                "function_declaration",
                "method_declaration",
                "init_declaration"
            ],
            SymbolType.CLASS: ["class_declaration"],
            SymbolType.STRUCT: ["struct_declaration"],
            SymbolType.ENUM: ["enum_declaration"],
            SymbolType.VARIABLE: [
                "property_declaration",
                "variable_declaration"
            ],
            SymbolType.IMPORT: ["import_declaration"]
        }
    
    def get_regex_patterns(self) -> List[RegexPattern]:
        """Detailed regex patterns for Swift fallback."""
        return [
            RegexPattern(
                pattern=r"(?:public|private|internal|fileprivate)?\s*(?:static\s+)?(?:override\s+)?func\s+(\w+)",
                symbol_type=SymbolType.FUNCTION,
                name_group=1,
                flags=re.MULTILINE
            ),
            RegexPattern(
                pattern=r"(?:public|private|internal|fileprivate)?\s*(?:final\s+)?class\s+(\w+)",
                symbol_type=SymbolType.CLASS,
                name_group=1,
                flags=re.MULTILINE
            ),
            RegexPattern(
                pattern=r"(?:public|private|internal|fileprivate)?\s*struct\s+(\w+)",
                symbol_type=SymbolType.STRUCT,
                name_group=1,
                flags=re.MULTILINE
            )
        ]
    
    def get_fallback_threshold(self) -> float:
        """Swift has good Tree-sitter support, so higher threshold."""
        return 0.8  # Only fallback if Tree-sitter finds less than 80% expected symbols
    
    @timing_decorator
    def _extract_symbols_tree_sitter(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Enhanced Tree-sitter extraction for Swift."""
        symbols = super()._extract_symbols_tree_sitter(content, file_path)
        
        # Add Swift-specific enhancements
        for symbol in symbols:
            # Detect computed properties
            if symbol.symbol_type == SymbolType.VARIABLE and "get" in (symbol.signature or ""):
                symbol.symbol_type = SymbolType.PROPERTY
                symbol.modifiers.add("computed")
            
            # Detect protocol conformances
            if symbol.symbol_type == SymbolType.CLASS and ":" in (symbol.signature or ""):
                symbol.metadata["protocols"] = self._extract_protocols(symbol.signature)
        
        return symbols
    
    def _extract_protocols(self, signature: str) -> List[str]:
        """Extract protocol conformances from class signature."""
        if ":" not in signature:
            return []
        
        # Simple extraction - could be enhanced
        parts = signature.split(":", 1)
        if len(parts) > 1:
            protocols = [p.strip() for p in parts[1].split(",")]
            return [p for p in protocols if p and not p.startswith("where")]
        
        return []


# Example 5: Advanced Plugin with Custom Features
class AdvancedPythonPlugin(HybridPluginBase):
    """Advanced Python plugin with additional features."""
    
    def __init__(self, config: Optional[PluginConfig] = None, **kwargs):
        """Initialize with custom configuration."""
        if config is None:
            config = PluginConfig(
                enable_caching=True,
                cache_ttl=7200,  # 2 hours
                async_processing=True,
                enable_semantic_analysis=True
            )
        
        super().__init__(config, **kwargs)
        self._import_graph = {}
        self._class_hierarchy = {}
    
    def get_language(self) -> str:
        return "python"
    
    def get_supported_extensions(self) -> List[str]:
        return [".py", ".pyi", ".pyx"]
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        return {
            SymbolType.FUNCTION: r"def\s+(\w+)",
            SymbolType.CLASS: r"class\s+(\w+)",
            SymbolType.VARIABLE: r"(\w+)\s*=",
            SymbolType.IMPORT: r"(?:import\s+(\w+)|from\s+(\w+)\s+import)"
        }
    
    def get_tree_sitter_node_types(self) -> Dict[SymbolType, List[str]]:
        return {
            SymbolType.FUNCTION: ["function_definition", "async_function_definition"],
            SymbolType.CLASS: ["class_definition"],
            SymbolType.VARIABLE: ["assignment", "augmented_assignment"],
            SymbolType.IMPORT: ["import_statement", "import_from_statement"]
        }
    
    def get_regex_patterns(self) -> List[RegexPattern]:
        return [
            RegexPattern(
                pattern=r"(?:async\s+)?def\s+(\w+)\s*\([^)]*\):",
                symbol_type=SymbolType.FUNCTION,
                name_group=1,
                flags=re.MULTILINE
            ),
            RegexPattern(
                pattern=r"class\s+(\w+)(?:\([^)]*\))?:",
                symbol_type=SymbolType.CLASS,
                name_group=1,
                flags=re.MULTILINE
            )
        ]
    
    @cached_method(ttl=3600)
    def analyze_imports(self, content: str, file_path: str) -> Dict[str, List[str]]:
        """Analyze import dependencies."""
        imports = SymbolExtractor.extract_imports(content, "python")
        
        # Build import graph
        self._import_graph[file_path] = imports
        
        return {
            "direct_imports": imports,
            "standard_library": [imp for imp in imports if self._is_stdlib(imp)],
            "third_party": [imp for imp in imports if not self._is_stdlib(imp)]
        }
    
    def _is_stdlib(self, module_name: str) -> bool:
        """Check if module is part of standard library."""
        stdlib_modules = {
            "os", "sys", "re", "json", "datetime", "collections",
            "itertools", "functools", "pathlib", "typing"
        }
        return module_name.split('.')[0] in stdlib_modules
    
    def extract_class_hierarchy(self, content: str) -> Dict[str, List[str]]:
        """Extract class inheritance hierarchy."""
        import re
        
        hierarchy = {}
        class_pattern = r"class\s+(\w+)(?:\(([^)]+)\))?"
        
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            parents = []
            
            if match.group(2):
                parents = [p.strip() for p in match.group(2).split(',')]
            
            hierarchy[class_name] = parents
        
        return hierarchy
    
    def get_plugin_metrics(self) -> Dict[str, Any]:
        """Get advanced plugin metrics."""
        base_metrics = self.get_statistics()
        
        return {
            **base_metrics,
            "import_graph_size": len(self._import_graph),
            "class_hierarchy_depth": self._calculate_hierarchy_depth(),
            "average_symbols_per_file": base_metrics.get("total_symbols", 0) / max(base_metrics.get("indexed_files", 1), 1)
        }
    
    def _calculate_hierarchy_depth(self) -> int:
        """Calculate maximum inheritance depth."""
        if not self._class_hierarchy:
            return 0
        
        def get_depth(class_name, visited=None):
            if visited is None:
                visited = set()
            
            if class_name in visited:
                return 0  # Circular inheritance
            
            visited.add(class_name)
            parents = self._class_hierarchy.get(class_name, [])
            
            if not parents:
                return 1
            
            return 1 + max(get_depth(parent, visited.copy()) for parent in parents)
        
        return max(get_depth(cls) for cls in self._class_hierarchy.keys())


# Example usage and testing
def demo_plugins():
    """Demonstrate the different plugin types."""
    
    # Sample code for testing
    test_codes = {
        "lua": '''
function hello_world()
    print("Hello, World!")
end

local my_var = 42
module("mymodule", package.seeall)
''',
        
        "typescript": '''
interface User {
    name: string;
    age: number;
}

class UserService {
    private users: User[] = [];
    
    /**
     * Add a new user to the service
     */
    addUser(user: User): void {
        this.users.push(user);
    }
    
    getUsers = (): User[] => {
        return this.users;
    }
}
''',
        
        "kotlin": '''
data class User(val name: String, val age: Int)

class UserService {
    private val users = mutableListOf<User>()
    
    fun addUser(user: User) {
        users.add(user)
    }
    
    fun getUsers(): List<User> = users
}
''',
        
        "swift": '''
struct User {
    let name: String
    let age: Int
}

class UserService {
    private var users: [User] = []
    
    func addUser(_ user: User) {
        users.append(user)
    }
    
    func getUsers() -> [User] {
        return users
    }
}
''',
        
        "python": '''
from typing import List
import json

class User:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

class UserService:
    def __init__(self):
        self.users: List[User] = []
    
    def add_user(self, user: User) -> None:
        """Add a new user to the service."""
        self.users.append(user)
    
    def get_users(self) -> List[User]:
        return self.users
'''
    }
    
    # Test each plugin
    plugins = [
        ("Lua (Simple)", SimpleLuaPlugin(), "lua"),
        ("TypeScript (Tree-sitter)", TypeScriptTreeSitterPlugin(), "typescript"),
        ("Kotlin (Regex)", KotlinRegexPlugin(), "kotlin"),
        ("Swift (Hybrid)", SwiftHybridPlugin(), "swift"),
        ("Python (Advanced)", AdvancedPythonPlugin(), "python")
    ]
    
    for plugin_name, plugin, lang in plugins:
        print(f"\n=== Testing {plugin_name} ===")
        
        # Get plugin info
        info = plugin.get_plugin_info()
        print(f"Language: {info['language']}")
        print(f"Extensions: {info['extensions']}")
        print(f"Initialized: {info['initialized']}")
        
        # Test file support
        test_file = f"example.{lang}"
        print(f"Supports {test_file}: {plugin.supports(test_file)}")
        
        # Test symbol extraction
        if lang in test_codes:
            try:
                result = plugin.indexFile(test_file, test_codes[lang])
                symbols = result.get("symbols", [])
                print(f"Extracted {len(symbols)} symbols:")
                
                for symbol in symbols[:5]:  # Show first 5 symbols
                    print(f"  - {symbol.get('kind', 'unknown')}: {symbol.get('symbol', 'unnamed')} (line {symbol.get('line', 0)})")
                
                if len(symbols) > 5:
                    print(f"  ... and {len(symbols) - 5} more")
                
            except Exception as e:
                print(f"Error during indexing: {e}")
        
        # Test statistics if available
        try:
            stats = plugin.get_statistics()
            print(f"Statistics: {stats}")
        except Exception as e:
            print(f"Error getting statistics: {e}")


if __name__ == "__main__":
    import re  # Need this for regex patterns
    demo_plugins()