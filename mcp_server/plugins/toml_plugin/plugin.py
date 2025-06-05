"""
TOML language plugin using Tree-sitter with advanced features.

This plugin provides comprehensive TOML parsing with support for:
- Cargo.toml (Rust projects)
- pyproject.toml (Python projects)
- Configuration files
- Nested tables and arrays
- Inline tables
- Multi-line strings
"""

from typing import Dict, List, Optional, Set, Any
import re
from pathlib import Path
from ..tree_sitter_plugin_base import TreeSitterPluginBase
from ..plugin_template import SymbolType, ParsedSymbol, PluginConfig


class Plugin(TreeSitterPluginBase):
    """Tree-sitter based plugin for TOML with enhanced features."""
    
    def __init__(self, config: Optional[PluginConfig] = None, **kwargs):
        """Initialize TOML plugin with enhanced configuration."""
        # Set config to prefer regex fallback since tree-sitter-toml might not be available
        if config is None:
            config = PluginConfig()
        config.enable_fallback = True
        
        super().__init__(config, **kwargs)
        
        # TOML-specific configuration
        self.cargo_patterns = self._get_cargo_patterns()
        self.pyproject_patterns = self._get_pyproject_patterns()
        self.config_patterns = self._get_config_patterns()
    
    def get_language(self) -> str:
        """Return the language this plugin supports."""
        return "toml"
    
    def get_supported_extensions(self) -> List[str]:
        """Return supported file extensions."""
        return [".toml", ".lock"]
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        """Return regex patterns as fallback."""
        return {
            # Top-level sections
            SymbolType.MODULE: r'^\[([\w.-]+)\]',
            # Nested sections/tables
            SymbolType.CLASS: r'^\[\[([\w.-]+)\]\]',
            # Key-value pairs
            SymbolType.VARIABLE: r'^(\w[\w.-]*)\s*=',
            # Inline tables
            SymbolType.FIELD: r'(\w[\w.-]*)\s*=\s*\{',
        }
    
    def get_node_types(self) -> Dict[SymbolType, List[str]]:
        """Return Tree-sitter node types for symbol extraction."""
        return {
            SymbolType.MODULE: ["table", "table_array_element"],
            SymbolType.VARIABLE: ["pair"],
            SymbolType.FIELD: ["inline_table"],
            SymbolType.PROPERTY: ["dotted_key"],
        }
    
    def get_query_patterns(self) -> Dict[str, str]:
        """Return Tree-sitter query patterns."""
        return {
            "tables": """
                (table
                  (bracket_left)
                  (dotted_key) @table_name
                  (bracket_right)) @table
            """,
            "table_arrays": """
                (table_array_element
                  (double_bracket_left)
                  (dotted_key) @array_name
                  (double_bracket_right)) @table_array
            """,
            "pairs": """
                (pair
                  key: (_) @key
                  value: (_) @value) @pair
            """,
            "inline_tables": """
                (inline_table) @inline_table
            """,
            "arrays": """
                (array) @array
            """,
        }
    
    def supports(self, path: str | Path) -> bool:
        """Check if this plugin supports the given file."""
        path = Path(path) if isinstance(path, str) else path
        
        # Check standard extensions
        if super().supports(path):
            return True
        
        # Special case for common TOML files without extensions
        filename = path.name.lower()
        return filename in ["cargo.toml", "pyproject.toml", "poetry.lock", "config.toml"]
    
    def _extract_symbols(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Extract symbols with fallback to regex if Tree-sitter fails."""
        symbols = []
        
        # Try Tree-sitter first if available
        if self._parser and self.supports_tree_sitter():
            try:
                symbols = self._extract_symbols_tree_sitter(content, file_path)
                if symbols:  # Only use Tree-sitter results if we got symbols
                    self.logger.debug(f"Extracted {len(symbols)} symbols using Tree-sitter")
                    return self._enhance_toml_symbols(symbols, content, file_path)
            except Exception as e:
                self.logger.warning(f"Tree-sitter parsing failed, falling back to regex: {e}")
        
        # Fallback to regex-based extraction
        symbols = self._extract_symbols_regex(content, file_path)
        self.logger.debug(f"Extracted {len(symbols)} symbols using regex")
        
        return self._enhance_toml_symbols(symbols, content, file_path)
    
    def _enhance_toml_symbols(self, symbols: List[ParsedSymbol], content: str, file_path: str) -> List[ParsedSymbol]:
        """Enhance symbols with TOML-specific information."""
        # Enhance with TOML-specific parsing
        file_path_obj = Path(file_path)
        if file_path_obj.name.lower() == "cargo.toml":
            symbols.extend(self._extract_cargo_symbols(content, symbols))
        elif file_path_obj.name.lower() == "pyproject.toml":
            symbols.extend(self._extract_pyproject_symbols(content, symbols))
        
        # Extract key paths for nested structures
        symbols = self._enhance_with_key_paths(symbols, content)
        
        return symbols
    
    def _extract_symbols_regex(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Extract symbols using regex patterns."""
        symbols = []
        lines = content.splitlines()
        
        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                continue
            
            # Check for table headers [section]
            table_match = re.match(r'^\[([\w.-]+)\]$', stripped)
            if table_match:
                table_name = table_match.group(1)
                symbol = ParsedSymbol(
                    name=table_name,
                    symbol_type=SymbolType.MODULE,
                    line=line_no,
                    signature=stripped,
                    metadata={"is_table": True}
                )
                symbols.append(symbol)
                continue
            
            # Check for table arrays [[array]]
            array_match = re.match(r'^\[\[([\w.-]+)\]\]$', stripped)
            if array_match:
                array_name = array_match.group(1)
                symbol = ParsedSymbol(
                    name=array_name,
                    symbol_type=SymbolType.CLASS,
                    line=line_no,
                    signature=stripped,
                    modifiers={"array"},
                    metadata={"is_table_array": True}
                )
                symbols.append(symbol)
                continue
            
            # Check for key-value pairs
            kv_match = re.match(r'^([\w.-]+)\s*=\s*(.+)$', stripped)
            if kv_match:
                key = kv_match.group(1)
                value = kv_match.group(2).strip()
                
                # Determine symbol type based on value
                if value.startswith('{'):
                    symbol_type = SymbolType.FIELD
                else:
                    symbol_type = SymbolType.VARIABLE
                
                symbol = ParsedSymbol(
                    name=key,
                    symbol_type=symbol_type,
                    line=line_no,
                    signature=stripped,
                    metadata={"raw_value": value}
                )
                symbols.append(symbol)
        
        return symbols
    
    def _extract_cargo_symbols(self, content: str, existing_symbols: List[ParsedSymbol]) -> List[ParsedSymbol]:
        """Extract Cargo.toml specific symbols."""
        additional_symbols = []
        lines = content.splitlines()
        
        # Track current section
        current_section = None
        
        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Update section tracking
            if re.match(r'^\[([^\]]+)\]', stripped):
                match = re.match(r'^\[([^\]]+)\]', stripped)
                if match:
                    current_section = match.group(1)
            
            # Package metadata
            if current_section == "package" and "=" in stripped:
                match = re.match(r'^(name|version|authors|edition)\s*=\s*"([^"]*)"', stripped)
                if match:
                    key, value = match.groups()
                    symbol = ParsedSymbol(
                        name=f"package.{key}",
                        symbol_type=SymbolType.PROPERTY,
                        line=line_no,
                        signature=stripped,
                        metadata={
                            "cargo_field": key,
                            "value": value,
                            "section": "package"
                        }
                    )
                    additional_symbols.append(symbol)
            
            # Dependencies
            elif current_section and "dependencies" in current_section and "=" in stripped:
                # Parse dependency specifications
                dep_match = re.match(r'^(\w[\w-]*)\s*=', stripped)
                if dep_match:
                    dep_name = dep_match.group(1)
                    symbol = ParsedSymbol(
                        name=f"{current_section}.{dep_name}",
                        symbol_type=SymbolType.IMPORT,
                        line=line_no,
                        signature=stripped,
                        metadata={
                            "dependency": dep_name,
                            "section": current_section,
                            "is_dependency": True
                        }
                    )
                    additional_symbols.append(symbol)
            
            # Features
            elif current_section == "features" and "=" in stripped:
                feature_match = re.match(r'^(\w[\w-]*)\s*=\s*\[([^\]]*)\]', stripped)
                if feature_match:
                    feature_name = feature_match.group(1)
                    feature_deps = feature_match.group(2)
                    symbol = ParsedSymbol(
                        name=f"features.{feature_name}",
                        symbol_type=SymbolType.PROPERTY,
                        line=line_no,
                        signature=stripped,
                        metadata={
                            "feature": feature_name,
                            "dependencies": [dep.strip().strip('"') for dep in feature_deps.split(",") if dep.strip()],
                            "section": "features"
                        }
                    )
                    additional_symbols.append(symbol)
        
        return additional_symbols
    
    def _extract_pyproject_symbols(self, content: str, existing_symbols: List[ParsedSymbol]) -> List[ParsedSymbol]:
        """Extract pyproject.toml specific symbols."""
        additional_symbols = []
        lines = content.splitlines()
        
        current_section = None
        
        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Update section tracking
            if re.match(r'^\[([^\]]+)\]', stripped):
                match = re.match(r'^\[([^\]]+)\]', stripped)
                if match:
                    current_section = match.group(1)
            
            # Extract Python-specific metadata
            if current_section == "project" and "=" in stripped:
                meta_match = re.match(r'^(name|version|description|readme|requires-python)\s*=', stripped)
                if meta_match:
                    key = meta_match.group(1)
                    symbol = ParsedSymbol(
                        name=f"project.{key}",
                        symbol_type=SymbolType.PROPERTY,
                        line=line_no,
                        signature=stripped,
                        metadata={
                            "project_field": key,
                            "section": "project"
                        }
                    )
                    additional_symbols.append(symbol)
            
            # Tool configurations
            elif current_section and current_section.startswith("tool.") and "=" in stripped:
                tool_name = current_section.split('.')[1] if '.' in current_section else current_section
                key_match = re.match(r'^(\w[\w-]*)\s*=', stripped)
                if key_match:
                    key = key_match.group(1)
                    symbol = ParsedSymbol(
                        name=f"{current_section}.{key}",
                        symbol_type=SymbolType.PROPERTY,
                        line=line_no,
                        signature=stripped,
                        metadata={
                            "tool": tool_name,
                            "is_tool_config": True
                        }
                    )
                    additional_symbols.append(symbol)
        
        return additional_symbols
    
    def _enhance_with_key_paths(self, symbols: List[ParsedSymbol], content: str) -> List[ParsedSymbol]:
        """Enhance symbols with full key paths for nested structures."""
        enhanced_symbols = []
        current_path = []
        lines = content.splitlines()
        
        for symbol in symbols:
            # Update current path based on section headers
            if symbol.symbol_type == SymbolType.MODULE:
                # Extract path from brackets
                if symbol.line <= len(lines):
                    match = re.match(r'^\[([\w.-]+)\]', lines[symbol.line - 1].strip())
                    if match:
                        current_path = match.group(1).split('.')
                        symbol.metadata["path"] = current_path
                        symbol.metadata["depth"] = len(current_path)
            
            # Add path information to variables
            elif symbol.symbol_type in (SymbolType.VARIABLE, SymbolType.PROPERTY, SymbolType.FIELD):
                if current_path and not '.' in symbol.name:
                    full_path = '.'.join(current_path + [symbol.name])
                    symbol.metadata["full_path"] = full_path
                    symbol.metadata["parent_path"] = '.'.join(current_path)
            
            enhanced_symbols.append(symbol)
        
        return enhanced_symbols
    
    def _extract_docstring_from_node(self, node, content: str) -> Optional[str]:
        """Extract comments as documentation for TOML."""
        # In TOML, comments are documentation
        try:
            # Look for comments above the node
            lines = content.splitlines()
            node_line = node.start_point[0]
            
            comments = []
            # Check lines above for comments
            for i in range(max(0, node_line - 3), node_line):
                line = lines[i].strip()
                if line.startswith('#'):
                    comments.append(line[1:].strip())
            
            return '\n'.join(comments) if comments else None
        except Exception:
            return None
    
    def _extract_modifiers_from_node(self, node, content: str) -> Set[str]:
        """Extract modifiers for TOML nodes."""
        modifiers = set()
        
        # Check node type for specific modifiers
        if node.type == "table_array_element":
            modifiers.add("array")
        elif node.type == "inline_table":
            modifiers.add("inline")
        
        # Check if it's a multi-line string
        if node.type == "string" and '"""' in content[node.start_byte:node.end_byte]:
            modifiers.add("multiline")
        
        return modifiers
    
    def _get_cargo_patterns(self) -> Dict[str, re.Pattern]:
        """Get regex patterns specific to Cargo.toml."""
        return {
            "package_name": re.compile(r'name\s*=\s*"([^"]+)"'),
            "version": re.compile(r'version\s*=\s*"([^"]+)"'),
            "dependency": re.compile(r'^(\w[\w-]*)\s*=\s*(.+)$'),
            "feature": re.compile(r'^(\w[\w-]*)\s*=\s*\[([^\]]*)\]'),
            "workspace": re.compile(r'^\[workspace\]'),
            "workspace_member": re.compile(r'members\s*=\s*\[([^\]]+)\]'),
        }
    
    def _get_pyproject_patterns(self) -> Dict[str, re.Pattern]:
        """Get regex patterns specific to pyproject.toml."""
        return {
            "project_name": re.compile(r'name\s*=\s*"([^"]+)"'),
            "version": re.compile(r'version\s*=\s*"([^"]+)"'),
            "python_version": re.compile(r'requires-python\s*=\s*"([^"]+)"'),
            "dependency": re.compile(r'^(\w[\w-]*)\s*=\s*(.+)$'),
            "tool_section": re.compile(r'^\[tool\.(\w+)\]'),
            "poetry_dep": re.compile(r'^(\w[\w-]*)\s*=\s*["{]([^"}]+)["}]'),
        }
    
    def _get_config_patterns(self) -> Dict[str, re.Pattern]:
        """Get regex patterns for general configuration files."""
        return {
            "section": re.compile(r'^\[([^\]]+)\]'),
            "key_value": re.compile(r'^(\w+)\s*=\s*(.+)$'),
            "dotted_key": re.compile(r'^([\w.]+)\s*=\s*(.+)$'),
            "array": re.compile(r'^\w+\s*=\s*\[([^\]]*)\]'),
            "inline_table": re.compile(r'^\w+\s*=\s*\{([^}]*)\}'),
        }
    
    def search(self, query: str, opts: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """Enhanced search for TOML files with semantic understanding."""
        results = super().search(query, opts)
        
        # Enhance results with TOML-specific information
        enhanced_results = []
        for result in results:
            enhanced = result.copy()
            
            # Add context about the TOML structure
            if "file" in result:
                file_path = Path(result["file"])
                if file_path.name.lower() == "cargo.toml":
                    enhanced["context"] = "Rust project configuration"
                elif file_path.name.lower() == "pyproject.toml":
                    enhanced["context"] = "Python project configuration"
                else:
                    enhanced["context"] = "Configuration file"
            
            enhanced_results.append(enhanced)
        
        return enhanced_results
    
    def getDefinition(self, symbol: str) -> Dict[str, Any] | None:
        """Get definition with TOML-specific enhancements."""
        definition = super().getDefinition(symbol)
        
        if definition:
            # Enhance with TOML-specific information
            if "." in symbol:
                parts = symbol.split(".")
                definition["section"] = parts[0]
                definition["key"] = parts[-1]
                definition["is_nested"] = len(parts) > 2
            
            # Add value type information if available
            if "signature" in definition:
                sig = definition["signature"]
                if "= true" in sig or "= false" in sig:
                    definition["value_type"] = "boolean"
                elif re.search(r'=\s*\d+', sig):
                    definition["value_type"] = "integer"
                elif re.search(r'=\s*\d+\.\d+', sig):
                    definition["value_type"] = "float"
                elif re.search(r'=\s*"[^"]*"', sig):
                    definition["value_type"] = "string"
                elif re.search(r'=\s*\[', sig):
                    definition["value_type"] = "array"
                elif re.search(r'=\s*\{', sig):
                    definition["value_type"] = "inline_table"
        
        return definition