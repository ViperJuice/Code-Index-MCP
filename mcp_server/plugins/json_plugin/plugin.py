"""
Comprehensive JSON language plugin using hybrid approach.

This plugin provides advanced JSON parsing capabilities including:
- Schema detection and validation
- JSONPath-style key extraction
- Nested object navigation
- Array index tracking
- JSON5 and JSONC comment support
- Package manager file detection
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass

from ..plugin_template import LanguagePluginBase, SymbolType, ParsedSymbol, PluginConfig
from ...core.logging import get_logger
from .tree_sitter_queries import JSON_QUERIES, SCHEMA_QUERIES, get_query_for_schema


@dataclass
class JSONKey:
    """Represents a JSON key with path information."""
    key: str
    path: str  # JSONPath-style path
    value_type: str
    line: int
    column: int = 0
    parent_type: str = "object"  # object, array, root
    depth: int = 0
    schema_hint: Optional[str] = None


class JSONSchemaDetector:
    """Detects and validates known JSON schemas."""
    
    KNOWN_SCHEMAS = {
        "package.json": {
            "required_keys": ["name", "version"],
            "optional_keys": ["description", "dependencies", "devDependencies", "scripts"],
            "schema_type": "npm_package"
        },
        "composer.json": {
            "required_keys": ["name"],
            "optional_keys": ["description", "require", "require-dev", "autoload"],
            "schema_type": "composer_package"
        },
        "tsconfig.json": {
            "required_keys": [],
            "optional_keys": ["compilerOptions", "include", "exclude", "extends"],
            "schema_type": "typescript_config"
        },
        "jsconfig.json": {
            "required_keys": [],
            "optional_keys": ["compilerOptions", "include", "exclude"],
            "schema_type": "javascript_config"
        },
        ".eslintrc.json": {
            "required_keys": [],
            "optional_keys": ["extends", "rules", "env", "parserOptions"],
            "schema_type": "eslint_config"
        },
        "manifest.json": {
            "required_keys": ["manifest_version"],
            "optional_keys": ["name", "version", "permissions", "content_scripts"],
            "schema_type": "browser_extension_manifest"
        },
        ".vscode/settings.json": {
            "required_keys": [],
            "optional_keys": [],
            "schema_type": "vscode_settings"
        },
        "launch.json": {
            "required_keys": ["version", "configurations"],
            "optional_keys": [],
            "schema_type": "vscode_launch"
        }
    }
    
    @classmethod
    def detect_schema(cls, file_path: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect the schema type of a JSON file."""
        filename = Path(file_path).name
        
        # Direct filename match
        if filename in cls.KNOWN_SCHEMAS:
            return cls.KNOWN_SCHEMAS[filename]
        
        # Path-based detection (e.g., .vscode/settings.json)
        for pattern, schema in cls.KNOWN_SCHEMAS.items():
            if file_path.endswith(pattern):
                return schema
        
        # Content-based detection
        if isinstance(data, dict):
            # NPM package detection
            if "name" in data and "version" in data and isinstance(data.get("dependencies"), dict):
                return cls.KNOWN_SCHEMAS["package.json"]
            
            # Composer package detection
            if "name" in data and isinstance(data.get("require"), dict):
                return cls.KNOWN_SCHEMAS["composer.json"]
            
            # TypeScript config detection
            if "compilerOptions" in data:
                return cls.KNOWN_SCHEMAS["tsconfig.json"]
            
            # ESLint config detection
            if "rules" in data or "extends" in data:
                return cls.KNOWN_SCHEMAS[".eslintrc.json"]
            
            # Browser extension manifest detection
            if "manifest_version" in data:
                return cls.KNOWN_SCHEMAS["manifest.json"]
        
        return None


class JSONPathBuilder:
    """Builds JSONPath-style paths for JSON keys."""
    
    @staticmethod
    def build_path(path_components: List[Union[str, int]]) -> str:
        """Build a JSONPath from components."""
        if not path_components:
            return "$"
        
        path = "$"
        for component in path_components:
            if isinstance(component, int):
                path += f"[{component}]"
            else:
                # Escape special characters in keys
                escaped = component.replace(".", r"\.")
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', escaped):
                    path += f".{escaped}"
                else:
                    path += f"['{escaped}']"
        
        return path
    
    @staticmethod
    def parse_path(jsonpath: str) -> List[Union[str, int]]:
        """Parse a JSONPath into components."""
        if jsonpath == "$":
            return []
        
        components = []
        # Simple parser for basic JSONPath expressions
        path = jsonpath[1:]  # Remove leading $
        
        # Split by dots and brackets
        parts = re.findall(r'\.([^.\[]+)|\[(\d+)\]|\[\'([^\']+)\'\]|\["([^"]+)"\]', path)
        
        for part in parts:
            if part[0]:  # .key
                components.append(part[0])
            elif part[1]:  # [index]
                components.append(int(part[1]))
            elif part[2]:  # ['key']
                components.append(part[2])
            elif part[3]:  # ["key"]
                components.append(part[3])
        
        return components


class Plugin(LanguagePluginBase):
    """Comprehensive JSON plugin with schema detection and advanced parsing."""
    
    def __init__(self, config: Optional[PluginConfig] = None, **kwargs):
        """Initialize the JSON plugin."""
        # Enhanced symbol patterns for JSON (must be set before super().__init__)
        self.json_patterns = {
            SymbolType.PROPERTY: r'"([^"]+)"\s*:',  # JSON keys
            SymbolType.CONSTANT: r'"([^"]+)"\s*:\s*"([^"]*)"',  # String values
            SymbolType.VARIABLE: r'"([^"]+)"\s*:\s*(\d+(?:\.\d+)?)',  # Numeric values
            SymbolType.FIELD: r'"([^"]+)"\s*:\s*(\{|\[)',  # Object/array fields
        }
        
        super().__init__(config, **kwargs)
        self.logger = get_logger(__name__)
        
        # JSON-specific state
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._key_cache: Dict[str, List[JSONKey]] = {}
    
    def get_language(self) -> str:
        """Return the language this plugin supports."""
        return "json"
    
    def get_supported_extensions(self) -> List[str]:
        """Return supported file extensions."""
        return ['.json', '.jsonc', '.json5', '.jsonl', '.ndjson']
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        """Return regex patterns for JSON symbol extraction."""
        return self.json_patterns
    
    def supports_tree_sitter(self) -> bool:
        """JSON plugin supports Tree-sitter parsing."""
        return True
    
    def _extract_symbols(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Extract symbols from JSON content with schema awareness."""
        symbols = []
        
        try:
            # Try Tree-sitter first if available
            if self._parser and self.supports_tree_sitter():
                try:
                    symbols = self._extract_symbols_tree_sitter(content, file_path)
                    if symbols:
                        self.logger.debug(f"Extracted {len(symbols)} symbols using Tree-sitter")
                        return symbols
                except Exception as e:
                    self.logger.warning(f"Tree-sitter parsing failed: {e}")
                    if not self.config.enable_fallback:
                        raise
            
            # Fallback to JSON parsing approach
            # Handle different JSON variants
            cleaned_content = self._clean_json_content(content, file_path)
            
            # Parse JSON
            try:
                data = json.loads(cleaned_content)
            except json.JSONDecodeError as e:
                self.logger.warning(f"JSON parsing failed for {file_path}: {e}")
                # Fallback to regex-based extraction
                return self._extract_symbols_regex(content, file_path)
            
            # Detect schema
            schema_info = JSONSchemaDetector.detect_schema(file_path, data)
            if schema_info:
                self._schema_cache[file_path] = schema_info
                self.logger.debug(f"Detected schema: {schema_info['schema_type']} for {file_path}")
            
            # Extract keys and structure
            json_keys = self._extract_json_keys(data, file_path, content)
            self._key_cache[file_path] = json_keys
            
            # Convert to ParsedSymbol format
            symbols.extend(self._convert_keys_to_symbols(json_keys, schema_info))
            
            # Add schema-specific symbols
            if schema_info:
                symbols.extend(self._extract_schema_specific_symbols(data, file_path, schema_info))
            
            # Add structural symbols
            symbols.extend(self._extract_structural_symbols(data, file_path, content))
            
        except Exception as e:
            self.logger.error(f"Failed to extract JSON symbols from {file_path}: {e}")
            # Fallback to regex
            return self._extract_symbols_regex(content, file_path)
        
        return symbols
    
    def _extract_symbols_tree_sitter(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Extract symbols using Tree-sitter parsing."""
        symbols = []
        
        # For now, fall back to JSON parsing since Tree-sitter integration 
        # needs more sophisticated query handling. The JSON parsing approach
        # is more reliable and provides better semantic understanding.
        return []
    
    def _extract_pairs_tree_sitter(self, tree, content: str, schema_info: Optional[Dict[str, Any]]) -> List[ParsedSymbol]:
        """Extract key-value pairs using Tree-sitter."""
        symbols = []
        lines = content.splitlines()
        
        # Query for all pairs
        pairs_query = self._parser.query(JSON_QUERIES["pairs"])
        
        if not pairs_query:
            return symbols
        
        try:
            captures = pairs_query.captures(tree.root_node)
            
            for node, capture_name in captures:
                if capture_name == "key.name":
                    # Get the key name
                    key_name = self._get_node_text(node, content).strip('"')
                    
                    # Find the corresponding value
                    pair_node = node.parent.parent  # string -> key -> pair
                    if pair_node and pair_node.type == "pair":
                        value_node = None
                        for child in pair_node.children:
                            if child.type != "string" and child != pair_node.children[0]:  # Not the key
                                value_node = child
                                break
                        
                        if value_node:
                            value_type = self._get_tree_sitter_value_type(value_node)
                            
                            # Get position information
                            start_point = node.start_point
                            line_no = start_point[0] + 1
                            
                            # Build JSONPath
                            json_path = self._build_tree_sitter_path(node)
                            
                            # Determine symbol type
                            symbol_type = self._determine_symbol_type_from_tree_sitter(
                                key_name, value_type, json_path, schema_info
                            )
                            
                            # Create symbol
                            symbol = ParsedSymbol(
                                name=key_name,
                                symbol_type=symbol_type,
                                line=line_no,
                                column=start_point[1],
                                signature=f'"{key_name}": {value_type}',
                                scope=json_path if json_path != "$" else None,
                                metadata={
                                    "json_path": json_path,
                                    "value_type": value_type,
                                    "tree_sitter": True,
                                    "schema_type": schema_info.get("schema_type") if schema_info else None
                                }
                            )
                            
                            symbols.append(symbol)
        
        except Exception as e:
            self.logger.error(f"Failed to extract pairs with Tree-sitter: {e}")
        
        return symbols
    
    def _extract_structures_tree_sitter(self, tree, content: str) -> List[ParsedSymbol]:
        """Extract structural elements (objects, arrays) using Tree-sitter."""
        symbols = []
        
        try:
            # Extract objects
            objects_query = self._parser.query(JSON_QUERIES["objects"])
            if objects_query:
                captures = objects_query.captures(tree.root_node)
                for node, capture_name in captures:
                    if capture_name == "object" and len(node.children) > 2:  # More than just {}
                        start_point = node.start_point
                        line_no = start_point[0] + 1
                        
                        # Count properties
                        pair_count = sum(1 for child in node.children if child.type == "pair")
                        
                        # Build path
                        json_path = self._build_tree_sitter_path(node)
                        
                        symbol = ParsedSymbol(
                            name=f"object_at_{json_path}",
                            symbol_type=SymbolType.NAMESPACE,
                            line=line_no,
                            column=start_point[1],
                            signature=f"object with {pair_count} properties",
                            scope=json_path if json_path != "$" else None,
                            metadata={
                                "structure_type": "object",
                                "property_count": pair_count,
                                "json_path": json_path,
                                "tree_sitter": True
                            }
                        )
                        symbols.append(symbol)
            
            # Extract arrays
            arrays_query = self._parser.query(JSON_QUERIES["arrays"])
            if arrays_query:
                captures = arrays_query.captures(tree.root_node)
                for node, capture_name in captures:
                    if capture_name == "array" and len(node.children) > 2:  # More than just []
                        start_point = node.start_point
                        line_no = start_point[0] + 1
                        
                        # Count elements
                        element_count = sum(1 for child in node.children if child.type != "," and child.type not in ["[", "]"])
                        
                        # Build path
                        json_path = self._build_tree_sitter_path(node)
                        
                        symbol = ParsedSymbol(
                            name=f"array_at_{json_path}",
                            symbol_type=SymbolType.FIELD,
                            line=line_no,
                            column=start_point[1],
                            signature=f"array with {element_count} items",
                            scope=json_path if json_path != "$" else None,
                            metadata={
                                "structure_type": "array",
                                "item_count": element_count,
                                "json_path": json_path,
                                "tree_sitter": True
                            }
                        )
                        symbols.append(symbol)
        
        except Exception as e:
            self.logger.error(f"Failed to extract structures with Tree-sitter: {e}")
        
        return symbols
    
    def _extract_schema_symbols_tree_sitter(self, tree, content: str, schema_info: Dict[str, Any]) -> List[ParsedSymbol]:
        """Extract schema-specific symbols using Tree-sitter."""
        symbols = []
        schema_type = schema_info["schema_type"]
        
        try:
            # Get schema-specific queries
            schema_queries = get_query_for_schema(schema_type)
            
            for query_name, query_pattern in schema_queries.items():
                try:
                    query = self._parser.query(query_pattern)
                    if query:
                        captures = query.captures(tree.root_node)
                        
                        # Process captures based on query type
                        if query_name == "scripts" and schema_type == "npm_package":
                            symbols.extend(self._process_npm_scripts_tree_sitter(captures, content))
                        elif query_name == "dependencies" and schema_type == "npm_package":
                            symbols.extend(self._process_npm_dependencies_tree_sitter(captures, content))
                        elif query_name == "compiler_options" and schema_type == "typescript_config":
                            symbols.extend(self._process_ts_compiler_options_tree_sitter(captures, content))
                        elif query_name == "rules" and schema_type == "eslint_config":
                            symbols.extend(self._process_eslint_rules_tree_sitter(captures, content))
                
                except Exception as e:
                    self.logger.warning(f"Failed to process schema query {query_name}: {e}")
        
        except Exception as e:
            self.logger.error(f"Failed to extract schema symbols with Tree-sitter: {e}")
        
        return symbols
    
    def _process_npm_scripts_tree_sitter(self, captures, content: str) -> List[ParsedSymbol]:
        """Process NPM scripts from Tree-sitter captures."""
        symbols = []
        
        for node, capture_name in captures:
            if capture_name == "script.name":
                script_name = self._get_node_text(node, content).strip('"')
                
                # Find the corresponding command
                script_command = ""
                pair_node = node.parent.parent  # string -> key -> pair
                if pair_node and pair_node.type == "pair":
                    for child in pair_node.children:
                        if child.type == "string" and child != pair_node.children[0]:
                            script_command = self._get_node_text(child, content).strip('"')
                            break
                
                start_point = node.start_point
                symbol = ParsedSymbol(
                    name=script_name,
                    symbol_type=SymbolType.FUNCTION,
                    line=start_point[0] + 1,
                    column=start_point[1],
                    signature=f'npm run {script_name}',
                    docstring=script_command,
                    scope="scripts",
                    metadata={
                        "script_command": script_command,
                        "executable": True,
                        "package_manager": "npm",
                        "tree_sitter": True
                    }
                )
                symbols.append(symbol)
        
        return symbols
    
    def _process_npm_dependencies_tree_sitter(self, captures, content: str) -> List[ParsedSymbol]:
        """Process NPM dependencies from Tree-sitter captures."""
        symbols = []
        
        dependency_type = None
        for node, capture_name in captures:
            if capture_name == "deps.key":
                dependency_type = self._get_node_text(node, content).strip('"')
            elif capture_name == "dep.name" and dependency_type:
                dep_name = self._get_node_text(node, content).strip('"')
                
                # Find version
                dep_version = ""
                pair_node = node.parent.parent
                if pair_node and pair_node.type == "pair":
                    for child in pair_node.children:
                        if child.type == "string" and child != pair_node.children[0]:
                            dep_version = self._get_node_text(child, content).strip('"')
                            break
                
                start_point = node.start_point
                symbol = ParsedSymbol(
                    name=dep_name,
                    symbol_type=SymbolType.IMPORT,
                    line=start_point[0] + 1,
                    column=start_point[1],
                    signature=f'"{dep_name}": "{dep_version}"',
                    scope=dependency_type,
                    metadata={
                        "dependency_type": dependency_type,
                        "version": dep_version,
                        "package_manager": "npm",
                        "tree_sitter": True
                    }
                )
                symbols.append(symbol)
        
        return symbols
    
    def _process_ts_compiler_options_tree_sitter(self, captures, content: str) -> List[ParsedSymbol]:
        """Process TypeScript compiler options from Tree-sitter captures."""
        symbols = []
        
        for node, capture_name in captures:
            if capture_name == "option.name":
                option_name = self._get_node_text(node, content).strip('"')
                
                # Find option value
                option_value = ""
                pair_node = node.parent.parent
                if pair_node and pair_node.type == "pair":
                    for child in pair_node.children:
                        if child != pair_node.children[0]:  # Not the key
                            option_value = self._get_node_text(child, content)
                            break
                
                start_point = node.start_point
                symbol = ParsedSymbol(
                    name=option_name,
                    symbol_type=SymbolType.PROPERTY,
                    line=start_point[0] + 1,
                    column=start_point[1],
                    signature=f"{option_name}: {option_value}",
                    scope="compilerOptions",
                    metadata={
                        "config_type": "typescript_compiler_option",
                        "value": option_value,
                        "tree_sitter": True
                    }
                )
                symbols.append(symbol)
        
        return symbols
    
    def _process_eslint_rules_tree_sitter(self, captures, content: str) -> List[ParsedSymbol]:
        """Process ESLint rules from Tree-sitter captures."""
        symbols = []
        
        for node, capture_name in captures:
            if capture_name == "rule.name":
                rule_name = self._get_node_text(node, content).strip('"')
                
                # Find rule config
                rule_config = ""
                pair_node = node.parent.parent
                if pair_node and pair_node.type == "pair":
                    for child in pair_node.children:
                        if child != pair_node.children[0]:  # Not the key
                            rule_config = self._get_node_text(child, content)
                            break
                
                start_point = node.start_point
                symbol = ParsedSymbol(
                    name=rule_name,
                    symbol_type=SymbolType.PROPERTY,
                    line=start_point[0] + 1,
                    column=start_point[1],
                    signature=f"{rule_name}: {rule_config}",
                    scope="rules",
                    metadata={
                        "config_type": "eslint_rule",
                        "rule_config": rule_config,
                        "tree_sitter": True
                    }
                )
                symbols.append(symbol)
        
        return symbols
    
    def _get_node_text(self, node, content: str) -> str:
        """Get text content of a Tree-sitter node."""
        start_byte = node.start_byte
        end_byte = node.end_byte
        return content[start_byte:end_byte]
    
    def _get_tree_sitter_value_type(self, node) -> str:
        """Get the value type from a Tree-sitter node."""
        if node.type == "string":
            return "string"
        elif node.type == "number":
            return "number"
        elif node.type == "true" or node.type == "false":
            return "boolean"
        elif node.type == "null":
            return "null"
        elif node.type == "object":
            return "object"
        elif node.type == "array":
            return "array"
        else:
            return "unknown"
    
    def _build_tree_sitter_path(self, node) -> str:
        """Build JSONPath from Tree-sitter node position."""
        path_components = []
        current = node
        
        while current and current.parent:
            parent = current.parent
            
            if parent.type == "pair":
                # This is a value in a key-value pair
                key_node = None
                for child in parent.children:
                    if child.type == "string":
                        key_node = child
                        break
                
                if key_node:
                    # Extract key text (remove quotes)
                    key_text = key_node.text.decode('utf-8').strip('"')
                    path_components.insert(0, key_text)
            
            elif parent.type == "array":
                # This is an element in an array - find its index
                index = 0
                for i, child in enumerate(parent.children):
                    if child == current:
                        # Count non-punctuation siblings before this node
                        index = sum(1 for c in parent.children[:i] if c.type not in [",", "[", "]"])
                        break
                path_components.insert(0, index)
            
            current = parent
        
        return JSONPathBuilder.build_path(path_components)
    
    def _determine_symbol_type_from_tree_sitter(self, key_name: str, value_type: str, json_path: str, schema_info: Optional[Dict[str, Any]]) -> SymbolType:
        """Determine symbol type using Tree-sitter context and schema information."""
        # Use the existing logic but with Tree-sitter context
        json_key = JSONKey(
            key=key_name,
            path=json_path,
            value_type=value_type,
            line=1  # Placeholder
        )
        
        return self._determine_symbol_type(json_key, schema_info)
    
    def _clean_json_content(self, content: str, file_path: str) -> str:
        """Clean JSON content to handle variants like JSONC and JSON5."""
        ext = Path(file_path).suffix.lower()
        
        if ext in ['.jsonc', '.json5']:
            # Remove comments for JSONC/JSON5
            # This is a simple implementation - a full JSON5 parser would be better
            lines = content.splitlines()
            cleaned_lines = []
            
            for line in lines:
                # Remove single-line comments
                if '//' in line:
                    comment_pos = line.find('//')
                    # Check if // is inside a string
                    quote_count = line[:comment_pos].count('"') - line[:comment_pos].count(r'\"')
                    if quote_count % 2 == 0:  # Even number of quotes = outside string
                        line = line[:comment_pos]
                
                cleaned_lines.append(line)
            
            content = '\n'.join(cleaned_lines)
            
            # Remove block comments (basic implementation)
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        if ext == '.jsonl' or ext == '.ndjson':
            # Handle JSON Lines format - parse each line separately
            lines = content.strip().split('\n')
            if lines:
                # For now, just parse the first line
                content = lines[0]
        
        return content
    
    def _extract_json_keys(self, data: Any, file_path: str, original_content: str) -> List[JSONKey]:
        """Extract all JSON keys with their paths and metadata."""
        keys = []
        lines = original_content.splitlines()
        
        def extract_recursive(obj: Any, path_components: List[Union[str, int]], depth: int = 0):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    # Find line number for this key
                    line_no = self._find_key_line(key, lines, depth)
                    
                    # Determine value type
                    value_type = self._get_value_type(value)
                    
                    # Build JSONPath
                    current_path = JSONPathBuilder.build_path(path_components)
                    
                    json_key = JSONKey(
                        key=key,
                        path=current_path,
                        value_type=value_type,
                        line=line_no,
                        parent_type="object",
                        depth=depth
                    )
                    
                    keys.append(json_key)
                    
                    # Recurse into nested structures
                    new_path = path_components + [key]
                    extract_recursive(value, new_path, depth + 1)
            
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_path = path_components + [i]
                    extract_recursive(item, new_path, depth + 1)
        
        extract_recursive(data, [], 0)
        return keys
    
    def _find_key_line(self, key: str, lines: List[str], depth: int) -> int:
        """Find the line number where a JSON key is defined."""
        # Simple heuristic: find the line containing the key with appropriate indentation
        escaped_key = re.escape(key)
        pattern = rf'^\s*"{escaped_key}"\s*:'
        
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line):
                return i
        
        # Fallback: estimate based on depth
        return min(depth + 1, len(lines))
    
    def _get_value_type(self, value: Any) -> str:
        """Get the type of a JSON value."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "unknown"
    
    def _convert_keys_to_symbols(self, keys: List[JSONKey], schema_info: Optional[Dict[str, Any]]) -> List[ParsedSymbol]:
        """Convert JSON keys to ParsedSymbol objects."""
        symbols = []
        
        for key in keys:
            # Determine symbol type based on value type and schema
            symbol_type = self._determine_symbol_type(key, schema_info)
            
            # Create signature
            signature = f'"{key.key}": {key.value_type}'
            if key.path != "$":
                signature = f"{key.path}.{key.key}: {key.value_type}"
            
            # Add schema hint to metadata
            metadata = {
                "json_path": key.path,
                "value_type": key.value_type,
                "depth": key.depth,
                "parent_type": key.parent_type
            }
            
            if schema_info:
                metadata["schema_type"] = schema_info["schema_type"]
                if key.key in schema_info.get("required_keys", []):
                    metadata["required"] = True
            
            symbol = ParsedSymbol(
                name=key.key,
                symbol_type=symbol_type,
                line=key.line,
                signature=signature,
                scope=key.path if key.path != "$" else None,
                metadata=metadata
            )
            
            symbols.append(symbol)
        
        return symbols
    
    def _determine_symbol_type(self, key: JSONKey, schema_info: Optional[Dict[str, Any]]) -> SymbolType:
        """Determine the appropriate symbol type for a JSON key."""
        # Schema-specific typing
        if schema_info:
            schema_type = schema_info["schema_type"]
            
            if schema_type == "npm_package":
                if key.key in ["dependencies", "devDependencies", "peerDependencies"]:
                    return SymbolType.MODULE
                elif key.key in ["scripts"]:
                    return SymbolType.FUNCTION
                elif key.key in ["name", "version", "description"]:
                    return SymbolType.PROPERTY
            
            elif schema_type == "typescript_config":
                if key.key == "compilerOptions":
                    return SymbolType.NAMESPACE
                elif key.path.startswith("$.compilerOptions"):
                    return SymbolType.PROPERTY
            
            elif schema_type == "eslint_config":
                if key.key == "rules":
                    return SymbolType.NAMESPACE
                elif key.path.startswith("$.rules"):
                    return SymbolType.PROPERTY
        
        # Generic typing based on value type
        if key.value_type == "object":
            return SymbolType.NAMESPACE
        elif key.value_type == "array":
            return SymbolType.FIELD
        elif key.value_type in ["string", "number", "integer", "boolean"]:
            return SymbolType.PROPERTY
        else:
            return SymbolType.FIELD
    
    def _extract_schema_specific_symbols(self, data: Dict[str, Any], file_path: str, schema_info: Dict[str, Any]) -> List[ParsedSymbol]:
        """Extract symbols specific to detected schemas."""
        symbols = []
        schema_type = schema_info["schema_type"]
        
        if schema_type == "npm_package":
            symbols.extend(self._extract_npm_package_symbols(data, file_path))
        elif schema_type == "composer_package":
            symbols.extend(self._extract_composer_symbols(data, file_path))
        elif schema_type == "typescript_config":
            symbols.extend(self._extract_typescript_config_symbols(data, file_path))
        elif schema_type == "eslint_config":
            symbols.extend(self._extract_eslint_config_symbols(data, file_path))
        
        return symbols
    
    def _extract_npm_package_symbols(self, data: Dict[str, Any], file_path: str) -> List[ParsedSymbol]:
        """Extract NPM package-specific symbols."""
        symbols = []
        
        # Dependencies as imports
        for dep_type in ["dependencies", "devDependencies", "peerDependencies", "optionalDependencies"]:
            if dep_type in data and isinstance(data[dep_type], dict):
                for dep_name, version in data[dep_type].items():
                    symbol = ParsedSymbol(
                        name=dep_name,
                        symbol_type=SymbolType.IMPORT,
                        line=self._find_key_line(dep_name, [], 0),
                        signature=f'"{dep_name}": "{version}"',
                        scope=dep_type,
                        metadata={
                            "dependency_type": dep_type,
                            "version": version,
                            "package_manager": "npm"
                        }
                    )
                    symbols.append(symbol)
        
        # Scripts as functions
        if "scripts" in data and isinstance(data["scripts"], dict):
            for script_name, command in data["scripts"].items():
                symbol = ParsedSymbol(
                    name=script_name,
                    symbol_type=SymbolType.FUNCTION,
                    line=self._find_key_line(script_name, [], 0),
                    signature=f'npm run {script_name}',
                    docstring=command,
                    scope="scripts",
                    metadata={
                        "script_command": command,
                        "executable": True
                    }
                )
                symbols.append(symbol)
        
        return symbols
    
    def _extract_composer_symbols(self, data: Dict[str, Any], file_path: str) -> List[ParsedSymbol]:
        """Extract Composer package-specific symbols."""
        symbols = []
        
        # Dependencies
        for dep_type in ["require", "require-dev"]:
            if dep_type in data and isinstance(data[dep_type], dict):
                for package_name, version in data[dep_type].items():
                    symbol = ParsedSymbol(
                        name=package_name,
                        symbol_type=SymbolType.IMPORT,
                        line=self._find_key_line(package_name, [], 0),
                        signature=f'"{package_name}": "{version}"',
                        scope=dep_type,
                        metadata={
                            "dependency_type": dep_type,
                            "version": version,
                            "package_manager": "composer"
                        }
                    )
                    symbols.append(symbol)
        
        return symbols
    
    def _extract_typescript_config_symbols(self, data: Dict[str, Any], file_path: str) -> List[ParsedSymbol]:
        """Extract TypeScript config-specific symbols."""
        symbols = []
        
        # Compiler options
        if "compilerOptions" in data and isinstance(data["compilerOptions"], dict):
            for option, value in data["compilerOptions"].items():
                symbol = ParsedSymbol(
                    name=option,
                    symbol_type=SymbolType.PROPERTY,
                    line=self._find_key_line(option, [], 0),
                    signature=f"{option}: {json.dumps(value)}",
                    scope="compilerOptions",
                    metadata={
                        "config_type": "typescript_compiler_option",
                        "value": value
                    }
                )
                symbols.append(symbol)
        
        return symbols
    
    def _extract_eslint_config_symbols(self, data: Dict[str, Any], file_path: str) -> List[ParsedSymbol]:
        """Extract ESLint config-specific symbols."""
        symbols = []
        
        # Rules
        if "rules" in data and isinstance(data["rules"], dict):
            for rule_name, rule_config in data["rules"].items():
                symbol = ParsedSymbol(
                    name=rule_name,
                    symbol_type=SymbolType.PROPERTY,
                    line=self._find_key_line(rule_name, [], 0),
                    signature=f"{rule_name}: {json.dumps(rule_config)}",
                    scope="rules",
                    metadata={
                        "config_type": "eslint_rule",
                        "rule_config": rule_config
                    }
                )
                symbols.append(symbol)
        
        return symbols
    
    def _extract_structural_symbols(self, data: Dict[str, Any], file_path: str, content: str) -> List[ParsedSymbol]:
        """Extract structural symbols (objects, arrays) from JSON."""
        symbols = []
        
        def extract_structure(obj: Any, path_components: List[Union[str, int]], depth: int = 0):
            if isinstance(obj, dict) and len(obj) > 1:  # Only meaningful objects
                path = JSONPathBuilder.build_path(path_components)
                
                # Estimate line number
                line_no = depth + 1
                
                symbol = ParsedSymbol(
                    name=f"object_at_{path}",
                    symbol_type=SymbolType.NAMESPACE,
                    line=line_no,
                    signature=f"object with {len(obj)} properties",
                    scope=path if path != "$" else None,
                    metadata={
                        "structure_type": "object",
                        "property_count": len(obj),
                        "json_path": path,
                        "depth": depth
                    }
                )
                symbols.append(symbol)
                
                for key, value in obj.items():
                    new_path = path_components + [key]
                    extract_structure(value, new_path, depth + 1)
            
            elif isinstance(obj, list) and len(obj) > 0:
                path = JSONPathBuilder.build_path(path_components)
                line_no = depth + 1
                
                symbol = ParsedSymbol(
                    name=f"array_at_{path}",
                    symbol_type=SymbolType.FIELD,
                    line=line_no,
                    signature=f"array with {len(obj)} items",
                    scope=path if path != "$" else None,
                    metadata={
                        "structure_type": "array",
                        "item_count": len(obj),
                        "json_path": path,
                        "depth": depth
                    }
                )
                symbols.append(symbol)
                
                # Only process first few items to avoid too many symbols
                for i, item in enumerate(obj[:5]):
                    new_path = path_components + [i]
                    extract_structure(item, new_path, depth + 1)
        
        extract_structure(data, [], 0)
        return symbols
    
    def get_definition(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get definition for a JSON key or schema element."""
        # Try parent implementation first
        result = super().getDefinition(symbol)
        if result:
            return result
        
        # JSON-specific definition lookup
        for file_path, keys in self._key_cache.items():
            for key in keys:
                if key.key == symbol:
                    return {
                        "symbol": symbol,
                        "kind": "property",
                        "language": "json",
                        "signature": f'"{symbol}": {key.value_type}',
                        "doc": f"JSON key at path {key.path}",
                        "defined_in": file_path,
                        "line": key.line,
                        "span": (key.line, key.line)
                    }
        
        return None
    
    def search(self, query: str, opts: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Enhanced search with JSONPath and schema-aware queries."""
        opts = opts or {}
        results = []
        
        # Check if query looks like a JSONPath
        if query.startswith('$'):
            results.extend(self._search_by_jsonpath(query, opts.get("limit", 20)))
        
        # Check if query is a schema type
        if query in ["package.json", "tsconfig.json", "composer.json"]:
            results.extend(self._search_by_schema_type(query, opts.get("limit", 20)))
        
        # Fall back to standard search
        if not results:
            results.extend(super().search(query, opts))
        
        return results
    
    def _search_by_jsonpath(self, jsonpath: str, limit: int) -> List[Dict[str, Any]]:
        """Search for JSON keys matching a JSONPath expression."""
        results = []
        
        for file_path, keys in self._key_cache.items():
            for key in keys:
                if key.path.startswith(jsonpath) or key.path == jsonpath:
                    result = {
                        "file": file_path,
                        "line": key.line,
                        "snippet": f'"{key.key}": {key.value_type} (at {key.path})'
                    }
                    results.append(result)
                    
                    if len(results) >= limit:
                        return results
        
        return results
    
    def _search_by_schema_type(self, schema_name: str, limit: int) -> List[Dict[str, Any]]:
        """Search for files matching a specific schema type."""
        results = []
        
        for file_path, schema_info in self._schema_cache.items():
            if Path(file_path).name == schema_name or schema_info.get("schema_type", "").endswith(schema_name.replace(".json", "")):
                result = {
                    "file": file_path,
                    "line": 1,
                    "snippet": f"{schema_name} schema detected"
                }
                results.append(result)
                
                if len(results) >= limit:
                    break
        
        return results
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Get JSON plugin-specific information."""
        info = super().get_plugin_info()
        info.update({
            "schema_cache_size": len(self._schema_cache),
            "key_cache_size": len(self._key_cache),
            "supported_schemas": list(JSONSchemaDetector.KNOWN_SCHEMAS.keys()),
            "features": [
                "schema_detection",
                "jsonpath_queries", 
                "nested_navigation",
                "package_manager_support",
                "json5_comments"
            ]
        })
        return info