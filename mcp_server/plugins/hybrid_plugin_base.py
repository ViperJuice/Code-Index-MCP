"""Hybrid plugin base class.

This module provides a specialized base class for plugins that use Tree-sitter
as the primary parser with regex-based fallback. It combines the power of
Tree-sitter parsing with the reliability of regex patterns.
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
from .tree_sitter_plugin_base import TreeSitterPluginBase
from .regex_plugin_base import RegexPluginBase, RegexPattern


class HybridPluginBase(LanguagePluginBase):
    """Base class for hybrid plugins that use Tree-sitter with regex fallback."""
    
    def __init__(self, config: Optional[PluginConfig] = None, **kwargs):
        """Initialize hybrid plugin."""
        # Ensure fallback is enabled
        if config is None:
            config = PluginConfig()
        config.enable_fallback = True
        config.preferred_backend = "tree-sitter"
        
        super().__init__(config, **kwargs)
        
        # Initialize both parsing strategies
        self._tree_sitter_available = self._check_tree_sitter_availability()
        self._regex_patterns = self._compile_regex_patterns()
        
        # Performance tracking
        self._parse_stats = {
            "tree_sitter_success": 0,
            "tree_sitter_fallback": 0,
            "regex_only": 0,
            "total_files": 0
        }
    
    def supports_tree_sitter(self) -> bool:
        """Hybrid plugins support Tree-sitter when available."""
        return True
    
    @abstractmethod
    def get_tree_sitter_node_types(self) -> Dict[SymbolType, List[str]]:
        """Return Tree-sitter node types for symbol extraction."""
        pass
    
    @abstractmethod
    def get_regex_patterns(self) -> List[RegexPattern]:
        """Return regex patterns for fallback symbol extraction."""
        pass
    
    def get_fallback_threshold(self) -> float:
        """Return threshold for deciding when to fallback to regex."""
        return 0.1  # If Tree-sitter extracts less than 10% expected symbols
    
    def _check_tree_sitter_availability(self) -> bool:
        """Check if Tree-sitter is available for this language."""
        try:
            if self._parser and self._parser.get_backend_name() == "tree-sitter":
                return True
        except Exception as e:
            self.logger.warning(f"Tree-sitter not available: {e}")
        
        return False
    
    def _compile_regex_patterns(self) -> List[RegexPattern]:
        """Compile regex patterns for fallback."""
        patterns = self.get_regex_patterns()
        
        for pattern in patterns:
            if pattern.compiled is None:
                import re
                pattern.compiled = re.compile(pattern.pattern, pattern.flags)
        
        return patterns
    
    def _extract_symbols(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Extract symbols using hybrid approach."""
        self._parse_stats["total_files"] += 1
        symbols = []
        
        # Try Tree-sitter first
        if self._tree_sitter_available:
            try:
                symbols = self._extract_symbols_tree_sitter(content, file_path)
                
                # Check if Tree-sitter results are sufficient
                if self._is_tree_sitter_result_sufficient(symbols, content):
                    self._parse_stats["tree_sitter_success"] += 1
                    self.logger.debug(f"Used Tree-sitter for {file_path} ({len(symbols)} symbols)")
                    return self._enhance_tree_sitter_symbols(symbols, content)
                else:
                    self.logger.warning(f"Tree-sitter results insufficient for {file_path}, falling back to regex")
                    self._parse_stats["tree_sitter_fallback"] += 1
                    
            except Exception as e:
                self.logger.warning(f"Tree-sitter parsing failed for {file_path}: {e}")
                self._parse_stats["tree_sitter_fallback"] += 1
        
        # Fallback to regex or combine results
        regex_symbols = self._extract_symbols_regex(content, file_path)
        
        if symbols:  # Tree-sitter had some results
            # Combine and deduplicate
            symbols = self._combine_symbol_results(symbols, regex_symbols)
        else:
            # Use regex results only
            symbols = regex_symbols
            self._parse_stats["regex_only"] += 1
        
        self.logger.debug(f"Used hybrid approach for {file_path} ({len(symbols)} symbols)")
        return symbols
    
    def _extract_symbols_tree_sitter(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Extract symbols using Tree-sitter."""
        if not self._parser:
            raise ParsingError("Tree-sitter parser not initialized")
        
        try:
            root_node = self._parser.parse(content.encode('utf-8'))
            if not root_node:
                raise ParsingError("Failed to parse content")
            
            symbols = []
            node_types = self.get_tree_sitter_node_types()
            
            def traverse(node):
                # Check if this node type maps to a symbol type
                for symbol_type, node_type_list in node_types.items():
                    if node.type in node_type_list:
                        symbol = self._create_symbol_from_tree_sitter_node(
                            node, symbol_type, content
                        )
                        if symbol:
                            symbols.append(symbol)
                
                # Recursively traverse children
                for child in node.children:
                    traverse(child)
            
            traverse(root_node)
            return symbols
            
        except Exception as e:
            self.logger.error(f"Tree-sitter parsing failed: {e}")
            raise ParsingError(f"Tree-sitter parsing failed: {e}") from e
    
    def _extract_symbols_regex(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Extract symbols using regex patterns."""
        symbols = []
        lines = content.splitlines()
        
        for pattern in self._regex_patterns:
            for line_no, line in enumerate(lines, 1):
                matches = pattern.compiled.finditer(line)
                for match in matches:
                    symbol = self._create_symbol_from_regex_match(
                        match, pattern, line_no, line, content
                    )
                    if symbol:
                        symbols.append(symbol)
        
        return symbols
    
    def _create_symbol_from_tree_sitter_node(
        self, 
        node: Any, 
        symbol_type: SymbolType, 
        content: str
    ) -> Optional[ParsedSymbol]:
        """Create symbol from Tree-sitter node."""
        try:
            # Get symbol name
            name = self._extract_name_from_node(node, content)
            if not name:
                return None
            
            # Get position
            start_line = node.start_point[0] + 1
            start_column = node.start_point[1]
            end_line = node.end_point[0] + 1
            end_column = node.end_point[1]
            
            # Get signature
            signature = self._extract_signature_from_node(node, content)
            
            # Get docstring
            docstring = self._extract_docstring_from_node(node, content)
            
            # Get scope
            scope = self._extract_scope_from_node(node, content)
            
            # Get modifiers
            modifiers = self._extract_modifiers_from_node(node, content)
            
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
                    "source": "tree-sitter",
                    "node_type": node.type,
                    "byte_range": (node.start_byte, node.end_byte)
                }
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create symbol from Tree-sitter node: {e}")
            return None
    
    def _create_symbol_from_regex_match(
        self,
        match,
        pattern: RegexPattern,
        line_no: int,
        line: str,
        content: str
    ) -> Optional[ParsedSymbol]:
        """Create symbol from regex match."""
        try:
            # Extract name
            name = match.group(pattern.name_group) if pattern.name_group <= len(match.groups()) else match.group(0)
            name = name.strip()
            
            if not name or not self._is_valid_symbol_name(name):
                return None
            
            # Extract signature
            signature = line.strip()
            if pattern.signature_group and pattern.signature_group <= len(match.groups()):
                signature = match.group(pattern.signature_group).strip()
            
            return ParsedSymbol(
                name=name,
                symbol_type=pattern.symbol_type,
                line=line_no,
                column=match.start(),
                signature=signature,
                metadata={
                    "source": "regex",
                    "pattern": pattern.pattern,
                    "full_match": match.group(0)
                }
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create symbol from regex match: {e}")
            return None
    
    def _is_tree_sitter_result_sufficient(self, symbols: List[ParsedSymbol], content: str) -> bool:
        """Check if Tree-sitter results are sufficient."""
        if not symbols:
            return False
        
        # Simple heuristic: check if we found at least some symbols
        # compared to the number of lines that might contain symbols
        lines_with_definitions = 0
        for line in content.splitlines():
            line = line.strip().lower()
            if any(keyword in line for keyword in ['def ', 'class ', 'function ', 'var ', 'let ']):
                lines_with_definitions += 1
        
        if lines_with_definitions == 0:
            return True  # No definitions expected
        
        # If we found at least the threshold percentage of expected symbols
        threshold = self.get_fallback_threshold()
        return len(symbols) >= (lines_with_definitions * threshold)
    
    def _combine_symbol_results(
        self, 
        tree_sitter_symbols: List[ParsedSymbol], 
        regex_symbols: List[ParsedSymbol]
    ) -> List[ParsedSymbol]:
        """Combine and deduplicate symbols from both sources."""
        # Create a map of Tree-sitter symbols
        ts_symbols = {}
        for symbol in tree_sitter_symbols:
            key = (symbol.name, symbol.symbol_type, symbol.line)
            ts_symbols[key] = symbol
        
        # Add regex symbols that don't conflict
        combined = list(tree_sitter_symbols)
        for symbol in regex_symbols:
            key = (symbol.name, symbol.symbol_type, symbol.line)
            if key not in ts_symbols:
                # Check for nearby conflicts (within 2 lines)
                conflicting = False
                for ts_key, ts_symbol in ts_symbols.items():
                    if (ts_key[0] == key[0] and  # Same name
                        ts_key[1] == key[1] and  # Same type
                        abs(ts_key[2] - key[2]) <= 2):  # Within 2 lines
                        conflicting = True
                        break
                
                if not conflicting:
                    combined.append(symbol)
        
        # Sort by line number
        combined.sort(key=lambda s: s.line)
        return combined
    
    def _enhance_tree_sitter_symbols(self, symbols: List[ParsedSymbol], content: str) -> List[ParsedSymbol]:
        """Enhance Tree-sitter symbols with additional information."""
        # Use regex patterns to add missing information
        lines = content.splitlines()
        
        for symbol in symbols:
            # Try to enhance with regex if information is missing
            if not symbol.docstring:
                symbol.docstring = self._find_docstring_near_line(lines, symbol.line)
            
            if not symbol.modifiers:
                symbol.modifiers = self._find_modifiers_near_line(lines, symbol.line)
        
        return symbols
    
    # Helper methods (similar to regex plugin)
    
    def _extract_name_from_node(self, node: Any, content: str) -> Optional[str]:
        """Extract symbol name from Tree-sitter node."""
        # Look for name field or identifier child
        name_node = None
        
        if hasattr(node, 'child_by_field_name'):
            name_node = node.child_by_field_name("name")
        
        if not name_node:
            for child in node.children:
                if child.type in ("identifier", "name"):
                    name_node = child
                    break
        
        if name_node:
            return content[name_node.start_byte:name_node.end_byte]
        
        return None
    
    def _extract_signature_from_node(self, node: Any, content: str) -> Optional[str]:
        """Extract signature from Tree-sitter node."""
        # Return the first line of the node
        lines = content[node.start_byte:node.end_byte].split('\n')
        return lines[0].strip() if lines else None
    
    def _extract_docstring_from_node(self, node: Any, content: str) -> Optional[str]:
        """Extract docstring from Tree-sitter node."""
        # Look for string literals that could be docstrings
        # This is highly language-specific
        return None
    
    def _extract_scope_from_node(self, node: Any, content: str) -> Optional[str]:
        """Extract scope from Tree-sitter node."""
        parent = node.parent
        scopes = []
        
        while parent:
            if parent.type in ("class_definition", "function_definition", "module", "namespace"):
                scope_name = self._extract_name_from_node(parent, content)
                if scope_name:
                    scopes.append(scope_name)
            parent = parent.parent
        
        return ".".join(reversed(scopes)) if scopes else None
    
    def _extract_modifiers_from_node(self, node: Any, content: str) -> Set[str]:
        """Extract modifiers from Tree-sitter node."""
        modifiers = set()
        
        # Look for modifier siblings
        if node.parent:
            for sibling in node.parent.children:
                if sibling.type in ("public", "private", "protected", "static", "abstract", "final"):
                    modifiers.add(sibling.type)
        
        return modifiers
    
    def _find_docstring_near_line(self, lines: List[str], line_no: int) -> Optional[str]:
        """Find docstring near the given line."""
        import re
        
        for i in range(line_no, min(line_no + 5, len(lines))):
            line = lines[i].strip()
            if '"""' in line or "'''" in line:
                docstring_match = re.search(r'["\']([^"\']*?)["\']', line)
                if docstring_match:
                    return docstring_match.group(1)
        
        return None
    
    def _find_modifiers_near_line(self, lines: List[str], line_no: int) -> Set[str]:
        """Find modifiers near the given line."""
        modifiers = set()
        
        for i in range(max(0, line_no - 2), min(line_no + 1, len(lines))):
            line = lines[i].lower()
            
            if 'public' in line:
                modifiers.add('public')
            if 'private' in line:
                modifiers.add('private')
            if 'protected' in line:
                modifiers.add('protected')
            if 'static' in line:
                modifiers.add('static')
            if 'abstract' in line:
                modifiers.add('abstract')
            if 'final' in line:
                modifiers.add('final')
            if 'async' in line:
                modifiers.add('async')
        
        return modifiers
    
    def _is_valid_symbol_name(self, name: str) -> bool:
        """Check if a name is a valid symbol name."""
        import re
        
        if not name or not name.strip():
            return False
        
        if not re.match(r'^[a-zA-Z_]', name):
            return False
        
        if not re.match(r'^[a-zA-Z0-9_]+$', name):
            return False
        
        return True
    
    def get_hybrid_info(self) -> Dict[str, Any]:
        """Get hybrid plugin information."""
        info = self.get_plugin_info()
        info.update({
            "parsing_strategy": "hybrid",
            "tree_sitter_available": self._tree_sitter_available,
            "regex_patterns": len(self._regex_patterns),
            "parse_stats": self._parse_stats.copy(),
            "fallback_threshold": self.get_fallback_threshold()
        })
        
        return info
    
    def get_parsing_statistics(self) -> Dict[str, Any]:
        """Get detailed parsing statistics."""
        total = self._parse_stats["total_files"]
        if total == 0:
            return {"message": "No files parsed yet"}
        
        return {
            "total_files": total,
            "tree_sitter_success": self._parse_stats["tree_sitter_success"],
            "tree_sitter_success_rate": self._parse_stats["tree_sitter_success"] / total,
            "fallback_used": self._parse_stats["tree_sitter_fallback"] + self._parse_stats["regex_only"],
            "fallback_rate": (self._parse_stats["tree_sitter_fallback"] + self._parse_stats["regex_only"]) / total,
            "regex_only": self._parse_stats["regex_only"],
            "regex_only_rate": self._parse_stats["regex_only"] / total
        }