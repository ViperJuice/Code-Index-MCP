"""Regex-based plugin base class.

This module provides a specialized base class for plugins that use regular
expressions for parsing. It includes optimized regex patterns, multi-line
matching, and pattern composition utilities.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Pattern, Set, Tuple, Union
from abc import abstractmethod
from dataclasses import dataclass

from .plugin_template import (
    LanguagePluginBase,
    ParsedSymbol,
    SymbolType,
    PluginConfig
)


@dataclass
class RegexPattern:
    """Enhanced regex pattern with metadata."""
    pattern: str
    flags: int = re.MULTILINE
    symbol_type: SymbolType = SymbolType.UNKNOWN
    name_group: int = 1
    signature_group: Optional[int] = None
    docstring_group: Optional[int] = None
    scope_group: Optional[int] = None
    modifiers_group: Optional[int] = None
    compiled: Optional[Pattern] = None
    
    def __post_init__(self):
        """Compile the pattern after initialization."""
        self.compiled = re.compile(self.pattern, self.flags)


class RegexPluginBase(LanguagePluginBase):
    """Base class for regex-based language plugins."""
    
    def __init__(self, config: Optional[PluginConfig] = None, **kwargs):
        """Initialize regex plugin."""
        # Ensure fallback is enabled for regex plugins
        if config is None:
            config = PluginConfig()
        config.enable_fallback = True
        config.preferred_backend = None  # Don't prefer Tree-sitter
        
        super().__init__(config, **kwargs)
        
        # Regex specific configuration
        self.regex_patterns = self._compile_patterns()
        self.multi_line_patterns = self.get_multi_line_patterns()
        self.context_patterns = self.get_context_patterns()
    
    def supports_tree_sitter(self) -> bool:
        """Regex plugins don't require Tree-sitter."""
        return False
    
    @abstractmethod
    def get_regex_patterns(self) -> List[RegexPattern]:
        """Return list of regex patterns for symbol extraction."""
        pass
    
    def get_multi_line_patterns(self) -> Dict[SymbolType, RegexPattern]:
        """Return patterns for multi-line constructs."""
        return {
            SymbolType.FUNCTION: RegexPattern(
                pattern=r'^(\s*def\s+\w+.*?)(?=^\s*def|\Z)',
                flags=re.MULTILINE | re.DOTALL,
                symbol_type=SymbolType.FUNCTION
            ),
            SymbolType.CLASS: RegexPattern(
                pattern=r'^(\s*class\s+\w+.*?)(?=^\s*class|\s*def|\Z)',
                flags=re.MULTILINE | re.DOTALL,
                symbol_type=SymbolType.CLASS
            )
        }
    
    def get_context_patterns(self) -> Dict[str, RegexPattern]:
        """Return patterns for extracting context information."""
        return {
            "docstring": RegexPattern(
                pattern=r'"""([^"]*?)"""',
                flags=re.MULTILINE | re.DOTALL
            ),
            "comment": RegexPattern(
                pattern=r'#\s*(.*?)$',
                flags=re.MULTILINE
            ),
            "import": RegexPattern(
                pattern=r'^(import\s+\w+|from\s+\w+\s+import.*?)$',
                flags=re.MULTILINE
            )
        }
    
    def _compile_patterns(self) -> List[RegexPattern]:
        """Compile all regex patterns."""
        patterns = self.get_regex_patterns()
        
        # Ensure all patterns are compiled
        for pattern in patterns:
            if pattern.compiled is None:
                pattern.compiled = re.compile(pattern.pattern, pattern.flags)
        
        return patterns
    
    def _extract_symbols_regex(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Extract symbols using regex patterns."""
        symbols = []
        
        # Extract using single-line patterns
        symbols.extend(self._extract_single_line_symbols(content))
        
        # Extract using multi-line patterns
        symbols.extend(self._extract_multi_line_symbols(content))
        
        # Enhance symbols with context
        symbols = self._enhance_symbols_with_context(symbols, content)
        
        # Post-process symbols
        symbols = self._post_process_regex_symbols(symbols, content)
        
        return symbols
    
    def _extract_single_line_symbols(self, content: str) -> List[ParsedSymbol]:
        """Extract symbols using single-line patterns."""
        symbols = []
        lines = content.splitlines()
        
        for pattern in self.regex_patterns:
            for line_no, line in enumerate(lines, 1):
                matches = pattern.compiled.finditer(line)
                for match in matches:
                    symbol = self._create_symbol_from_match(
                        match, pattern, line_no, line, content
                    )
                    if symbol:
                        symbols.append(symbol)
        
        return symbols
    
    def _extract_multi_line_symbols(self, content: str) -> List[ParsedSymbol]:
        """Extract symbols using multi-line patterns."""
        symbols = []
        
        for symbol_type, pattern in self.multi_line_patterns.items():
            matches = pattern.compiled.finditer(content)
            for match in matches:
                symbol = self._create_multi_line_symbol(
                    match, pattern, symbol_type, content
                )
                if symbol:
                    symbols.append(symbol)
        
        return symbols
    
    def _create_symbol_from_match(
        self,
        match: re.Match,
        pattern: RegexPattern,
        line_no: int,
        line: str,
        content: str
    ) -> Optional[ParsedSymbol]:
        """Create a ParsedSymbol from a regex match."""
        try:
            # Extract name
            name = match.group(pattern.name_group) if pattern.name_group <= len(match.groups()) else match.group(0)
            name = name.strip()
            
            if not name or not self._is_valid_symbol_name(name):
                return None
            
            # Extract signature
            signature = None
            if pattern.signature_group and pattern.signature_group <= len(match.groups()):
                signature = match.group(pattern.signature_group).strip()
            else:
                signature = line.strip()
            
            # Extract docstring
            docstring = None
            if pattern.docstring_group and pattern.docstring_group <= len(match.groups()):
                docstring = match.group(pattern.docstring_group)
            
            # Extract scope
            scope = None
            if pattern.scope_group and pattern.scope_group <= len(match.groups()):
                scope = match.group(pattern.scope_group)
            
            # Extract modifiers
            modifiers = set()
            if pattern.modifiers_group and pattern.modifiers_group <= len(match.groups()):
                modifier_text = match.group(pattern.modifiers_group)
                modifiers = self._parse_modifiers(modifier_text)
            
            return ParsedSymbol(
                name=name,
                symbol_type=pattern.symbol_type,
                line=line_no,
                column=match.start(),
                signature=signature,
                docstring=docstring,
                scope=scope,
                modifiers=modifiers,
                metadata={
                    "pattern": pattern.pattern,
                    "full_match": match.group(0)
                }
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create symbol from regex match: {e}")
            return None
    
    def _create_multi_line_symbol(
        self,
        match: re.Match,
        pattern: RegexPattern,
        symbol_type: SymbolType,
        content: str
    ) -> Optional[ParsedSymbol]:
        """Create a symbol from a multi-line regex match."""
        try:
            # Get the matched text
            matched_text = match.group(0)
            
            # Find line numbers
            content_before_match = content[:match.start()]
            start_line = content_before_match.count('\n') + 1
            
            matched_lines = matched_text.count('\n')
            end_line = start_line + matched_lines
            
            # Extract name from the first line
            first_line = matched_text.split('\n')[0]
            name_match = re.search(r'\b(\w+)\b', first_line)
            if not name_match:
                return None
            
            name = name_match.group(1)
            
            # Extract signature (first line)
            signature = first_line.strip()
            
            # Look for docstring in the matched text
            docstring = self._extract_docstring_from_text(matched_text)
            
            return ParsedSymbol(
                name=name,
                symbol_type=symbol_type,
                line=start_line,
                column=0,
                end_line=end_line,
                signature=signature,
                docstring=docstring,
                metadata={
                    "multi_line": True,
                    "full_text": matched_text
                }
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create multi-line symbol: {e}")
            return None
    
    def _enhance_symbols_with_context(self, symbols: List[ParsedSymbol], content: str) -> List[ParsedSymbol]:
        """Enhance symbols with additional context information."""
        lines = content.splitlines()
        
        for symbol in symbols:
            # Add docstring if not already present
            if not symbol.docstring:
                symbol.docstring = self._find_docstring_near_line(lines, symbol.line)
            
            # Add scope information
            if not symbol.scope:
                symbol.scope = self._find_scope_for_line(lines, symbol.line)
            
            # Add modifiers if not already present
            if not symbol.modifiers:
                symbol.modifiers = self._find_modifiers_near_line(lines, symbol.line)
        
        return symbols
    
    def _find_docstring_near_line(self, lines: List[str], line_no: int) -> Optional[str]:
        """Find docstring near the given line."""
        # Look for docstring in the next few lines
        for i in range(line_no, min(line_no + 5, len(lines))):
            line = lines[i].strip()
            if '"""' in line or "'''" in line:
                # Extract docstring
                docstring_match = re.search(r'["\']([^"\']*?)["\']', line)
                if docstring_match:
                    return docstring_match.group(1)
        
        return None
    
    def _find_scope_for_line(self, lines: List[str], line_no: int) -> Optional[str]:
        """Find the scope (class, function) for the given line."""
        scopes = []
        
        # Look backwards to find containing scopes
        for i in range(line_no - 1, -1, -1):
            line = lines[i].strip()
            
            # Simple pattern matching for common scope indicators
            class_match = re.match(r'^class\s+(\w+)', line)
            if class_match:
                scopes.append(class_match.group(1))
                break
            
            func_match = re.match(r'^def\s+(\w+)', line)
            if func_match and not scopes:  # Only add if no class scope found
                scopes.append(func_match.group(1))
        
        return '.'.join(reversed(scopes)) if scopes else None
    
    def _find_modifiers_near_line(self, lines: List[str], line_no: int) -> Set[str]:
        """Find modifiers near the given line."""
        modifiers = set()
        
        # Check the line and previous line for modifiers
        for i in range(max(0, line_no - 2), min(line_no + 1, len(lines))):
            line = lines[i].lower()
            
            # Common modifiers across languages
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
    
    def _extract_docstring_from_text(self, text: str) -> Optional[str]:
        """Extract docstring from a block of text."""
        # Look for common docstring patterns
        for pattern_name, pattern in self.context_patterns.items():
            if pattern_name == "docstring":
                match = pattern.compiled.search(text)
                if match:
                    return match.group(1).strip()
        
        return None
    
    def _is_valid_symbol_name(self, name: str) -> bool:
        """Check if a name is a valid symbol name."""
        # Basic validation - can be overridden by subclasses
        if not name or not name.strip():
            return False
        
        # Should start with letter or underscore
        if not re.match(r'^[a-zA-Z_]', name):
            return False
        
        # Should contain only alphanumeric characters and underscores
        if not re.match(r'^[a-zA-Z0-9_]+$', name):
            return False
        
        return True
    
    def _parse_modifiers(self, modifier_text: str) -> Set[str]:
        """Parse modifiers from text."""
        modifiers = set()
        modifier_words = ['public', 'private', 'protected', 'static', 'abstract', 'final', 'async']
        
        for word in modifier_words:
            if word in modifier_text.lower():
                modifiers.add(word)
        
        return modifiers
    
    def _post_process_regex_symbols(self, symbols: List[ParsedSymbol], content: str) -> List[ParsedSymbol]:
        """Post-process symbols extracted with regex."""
        # Remove duplicates based on name and line
        seen = set()
        unique_symbols = []
        
        for symbol in symbols:
            key = (symbol.name, symbol.symbol_type, symbol.line)
            if key not in seen:
                unique_symbols.append(symbol)
                seen.add(key)
        
        # Sort by line number
        unique_symbols.sort(key=lambda s: s.line)
        
        # Filter out invalid symbols
        valid_symbols = [
            s for s in unique_symbols 
            if self._is_valid_symbol_name(s.name)
        ]
        
        return valid_symbols
    
    def get_regex_info(self) -> Dict[str, Any]:
        """Get regex-specific information."""
        info = self.get_plugin_info()
        info.update({
            "regex_patterns": len(self.regex_patterns),
            "multi_line_patterns": len(self.multi_line_patterns),
            "context_patterns": len(self.context_patterns),
            "pattern_details": [
                {
                    "symbol_type": p.symbol_type.value,
                    "pattern": p.pattern[:50] + "..." if len(p.pattern) > 50 else p.pattern,
                    "flags": p.flags
                }
                for p in self.regex_patterns
            ]
        })
        
        return info


class SimpleRegexPlugin(RegexPluginBase):
    """Simple regex plugin for basic pattern matching."""
    
    def get_regex_patterns(self) -> List[RegexPattern]:
        """Return basic patterns that work for many languages."""
        return [
            RegexPattern(
                pattern=r'^(\s*(?:def|function)\s+(\w+))',
                symbol_type=SymbolType.FUNCTION,
                name_group=2,
                signature_group=1
            ),
            RegexPattern(
                pattern=r'^(\s*(?:class|struct)\s+(\w+))',
                symbol_type=SymbolType.CLASS,
                name_group=2,
                signature_group=1
            ),
            RegexPattern(
                pattern=r'^(\s*(?:var|let|const)\s+(\w+))',
                symbol_type=SymbolType.VARIABLE,
                name_group=2,
                signature_group=1
            )
        ]