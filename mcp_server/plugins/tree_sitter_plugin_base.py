"""Tree-sitter-based plugin base class.

This module provides a specialized base class for plugins that use Tree-sitter
for parsing. It includes optimized Tree-sitter integration, AST traversal
utilities, and language-specific query patterns.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from abc import abstractmethod

from .plugin_template import (
    LanguagePluginBase,
    ParsedSymbol,
    SymbolType,
    PluginConfig,
    ParsingError
)
from ..utils.smart_parser import SmartParser


class TreeSitterPluginBase(LanguagePluginBase):
    """Base class for Tree-sitter-based language plugins."""
    
    def __init__(self, config: Optional[PluginConfig] = None, **kwargs):
        """Initialize Tree-sitter plugin."""
        # Ensure Tree-sitter is preferred
        if config is None:
            config = PluginConfig()
        config.preferred_backend = "tree-sitter"
        
        super().__init__(config, **kwargs)
        
        # Tree-sitter specific configuration
        self.node_types = self.get_node_types()
        self.query_patterns = self.get_query_patterns()
    
    def supports_tree_sitter(self) -> bool:
        """Tree-sitter plugins always support Tree-sitter."""
        return True
    
    @abstractmethod
    def get_node_types(self) -> Dict[SymbolType, List[str]]:
        """Return mapping of symbol types to Tree-sitter node types."""
        pass
    
    def get_query_patterns(self) -> Dict[str, str]:
        """Return Tree-sitter query patterns for advanced parsing."""
        # Default query patterns that work for many languages
        return {
            "functions": """
                (function_definition
                  name: (identifier) @name) @function
            """,
            "classes": """
                (class_definition
                  name: (identifier) @name) @class
            """,
            "variables": """
                (variable_declarator
                  name: (identifier) @name) @variable
            """,
            "imports": """
                (import_statement) @import
            """
        }
    
    def _extract_symbols_tree_sitter(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Extract symbols using Tree-sitter parsing."""
        if not self._parser:
            raise ParsingError("Tree-sitter parser not initialized")
        
        try:
            root_node = self._parser.parse(content.encode('utf-8'))
            if not root_node:
                raise ParsingError("Failed to parse content")
            
            symbols = []
            
            # Extract symbols using node type mapping
            symbols.extend(self._extract_by_node_types(root_node, content))
            
            # Extract symbols using query patterns if available
            symbols.extend(self._extract_by_queries(root_node, content))
            
            # Post-process symbols
            symbols = self._post_process_symbols(symbols, content)
            
            return symbols
            
        except Exception as e:
            self.logger.error(f"Tree-sitter parsing failed for {file_path}: {e}")
            raise ParsingError(f"Tree-sitter parsing failed: {e}") from e
    
    def _extract_by_node_types(self, root_node: Any, content: str) -> List[ParsedSymbol]:
        """Extract symbols by traversing nodes of specific types."""
        symbols = []
        
        def traverse(node):
            # Check if this node type maps to a symbol type
            for symbol_type, node_types in self.node_types.items():
                if node.type in node_types:
                    symbol = self._create_symbol_from_node(node, symbol_type, content)
                    if symbol:
                        symbols.append(symbol)
            
            # Recursively traverse children
            for child in node.children:
                traverse(child)
        
        traverse(root_node)
        return symbols
    
    def _extract_by_queries(self, root_node: Any, content: str) -> List[ParsedSymbol]:
        """Extract symbols using Tree-sitter queries."""
        symbols = []
        
        # Note: This is a simplified version. Full implementation would use
        # tree-sitter query language for more sophisticated pattern matching.
        # For now, we use the node type approach above.
        
        return symbols
    
    def _create_symbol_from_node(self, node: Any, symbol_type: SymbolType, content: str) -> Optional[ParsedSymbol]:
        """Create a ParsedSymbol from a Tree-sitter node."""
        try:
            # Get symbol name
            name = self._extract_symbol_name(node, content)
            if not name:
                return None
            
            # Get position information
            start_line = node.start_point[0] + 1
            start_column = node.start_point[1]
            end_line = node.end_point[0] + 1
            end_column = node.end_point[1]
            
            # Get signature
            signature = self._extract_signature(node, content)
            
            # Get docstring
            docstring = self._extract_docstring(node, content)
            
            # Get scope
            scope = self._extract_scope(node, content)
            
            # Get modifiers
            modifiers = self._extract_modifiers(node, content)
            
            return ParsedSymbol(
                name=name,
                symbol_type=symbol_type,
                line=start_line,
                column=start_column,
                end_line=end_line,
                end_column=end_column,
                signature=signature,
                docstring=docstring,
                scope=scope,
                modifiers=modifiers,
                metadata={
                    "node_type": node.type,
                    "byte_range": (node.start_byte, node.end_byte)
                }
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create symbol from node {node.type}: {e}")
            return None
    
    def _extract_symbol_name(self, node: Any, content: str) -> Optional[str]:
        """Extract symbol name from Tree-sitter node."""
        # Look for name field or identifier child
        name_node = None
        
        # Try name field first
        if hasattr(node, 'child_by_field_name'):
            name_node = node.child_by_field_name("name")
        
        # Try finding identifier child
        if not name_node:
            for child in node.children:
                if child.type in ("identifier", "name"):
                    name_node = child
                    break
        
        if name_node:
            return content[name_node.start_byte:name_node.end_byte]
        
        return None
    
    def _extract_signature(self, node: Any, content: str) -> Optional[str]:
        """Extract symbol signature from Tree-sitter node."""
        # Default implementation: return the first line of the node
        lines = content[node.start_byte:node.end_byte].split('\n')
        return lines[0].strip() if lines else None
    
    def _extract_docstring(self, node: Any, content: str) -> Optional[str]:
        """Extract docstring from Tree-sitter node."""
        # Look for string literals that could be docstrings
        # This is language-specific and should be overridden
        return None
    
    def _extract_scope(self, node: Any, content: str) -> Optional[str]:
        """Extract scope information from Tree-sitter node."""
        # Walk up the tree to find containing scopes
        parent = node.parent
        scopes = []
        
        while parent:
            if parent.type in ("class_definition", "function_definition", "module", "namespace"):
                scope_name = self._extract_symbol_name(parent, content)
                if scope_name:
                    scopes.append(scope_name)
            parent = parent.parent
        
        return ".".join(reversed(scopes)) if scopes else None
    
    def _extract_modifiers(self, node: Any, content: str) -> Set[str]:
        """Extract modifiers (public, private, static, etc.) from Tree-sitter node."""
        modifiers = set()
        
        # Look for modifier siblings or parents
        # This is highly language-specific
        if node.parent:
            for sibling in node.parent.children:
                if sibling.type in ("public", "private", "protected", "static", "abstract", "final"):
                    modifiers.add(sibling.type)
        
        return modifiers
    
    def _post_process_symbols(self, symbols: List[ParsedSymbol], content: str) -> List[ParsedSymbol]:
        """Post-process extracted symbols."""
        # Remove duplicates
        seen = set()
        unique_symbols = []
        
        for symbol in symbols:
            key = (symbol.name, symbol.symbol_type, symbol.line)
            if key not in seen:
                unique_symbols.append(symbol)
                seen.add(key)
        
        # Sort by line number
        unique_symbols.sort(key=lambda s: s.line)
        
        return unique_symbols
    
    def get_tree_sitter_info(self) -> Dict[str, Any]:
        """Get Tree-sitter specific information."""
        info = self.get_plugin_info()
        info.update({
            "node_types": self.node_types,
            "query_patterns": list(self.query_patterns.keys()),
            "parser_language": self.lang
        })
        
        if self._parser:
            info["parser_available"] = True
            info["parser_backend"] = self._parser.get_backend_name()
        else:
            info["parser_available"] = False
        
        return info


class AdvancedTreeSitterPlugin(TreeSitterPluginBase):
    """Advanced Tree-sitter plugin with additional features."""
    
    def __init__(self, config: Optional[PluginConfig] = None, **kwargs):
        """Initialize advanced Tree-sitter plugin."""
        super().__init__(config, **kwargs)
        
        # Advanced features
        self.cross_reference_patterns = self.get_cross_reference_patterns()
        self.semantic_patterns = self.get_semantic_patterns()
    
    def get_cross_reference_patterns(self) -> Dict[str, str]:
        """Return patterns for finding cross-references."""
        return {
            "function_calls": r'(\w+)\s*\(',
            "class_instantiation": r'new\s+(\w+)\s*\(',
            "variable_access": r'\b(\w+)\.',
            "import_usage": r'from\s+(\w+)',
        }
    
    def get_semantic_patterns(self) -> Dict[str, str]:
        """Return patterns for semantic analysis."""
        return {
            "type_annotations": r':\s*(\w+)',
            "generics": r'<([^>]+)>',
            "decorators": r'@(\w+)',
            "annotations": r'@(\w+)',
        }
    
    def extract_cross_references(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Extract cross-references from the file."""
        references = []
        
        if not self._parser:
            return references
        
        try:
            root_node = self._parser.parse(content.encode('utf-8'))
            references = self._extract_references_from_tree(root_node, content)
        except Exception as e:
            self.logger.error(f"Failed to extract cross-references: {e}")
        
        return references
    
    def _extract_references_from_tree(self, root_node: Any, content: str) -> List[Dict[str, Any]]:
        """Extract cross-references from Tree-sitter tree."""
        references = []
        
        def traverse(node):
            # Look for call expressions, identifiers, etc.
            if node.type in ("call_expression", "attribute", "identifier"):
                ref = self._analyze_reference_node(node, content)
                if ref:
                    references.append(ref)
            
            for child in node.children:
                traverse(child)
        
        traverse(root_node)
        return references
    
    def _analyze_reference_node(self, node: Any, content: str) -> Optional[Dict[str, Any]]:
        """Analyze a node that might be a cross-reference."""
        try:
            name = content[node.start_byte:node.end_byte]
            return {
                "name": name,
                "type": node.type,
                "line": node.start_point[0] + 1,
                "column": node.start_point[1],
                "context": self._get_node_context(node, content)
            }
        except Exception:
            return None
    
    def _get_node_context(self, node: Any, content: str) -> str:
        """Get context around a node."""
        # Get the line containing the node
        lines = content.split('\n')
        line_no = node.start_point[0]
        if 0 <= line_no < len(lines):
            return lines[line_no].strip()
        return ""