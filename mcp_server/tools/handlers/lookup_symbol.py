"""
Symbol lookup tool implementation.

Finds symbol definitions across the codebase with support for fuzzy matching
and multiple symbol types.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
import difflib
import re

from ...dispatcher.dispatcher import Dispatcher
from ...plugin_base import SymbolDef
from ..registry import ToolRegistry, ToolMetadata, ToolCapability
from ..schemas import LOOKUP_SYMBOL_SCHEMA

logger = logging.getLogger(__name__)


class LookupSymbolHandler:
    """Handler for symbol lookup operations with MCP integration."""
    
    def __init__(self):
        """Initialize the symbol lookup handler."""
        self._cache = {}  # Symbol lookup cache
        self._cache_max_size = 200
        
    async def handle(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle symbol lookup requests.
        
        Args:
            params: Validated parameters from the tool request
            context: Execution context including dispatcher
            
        Returns:
            Symbol lookup results formatted for MCP clients
        """
        # Get dispatcher from context
        dispatcher = context.get("dispatcher")
        if not dispatcher:
            raise ValueError("Dispatcher not available in context")
        
        # Extract and validate parameters
        symbol = params["symbol"]
        if not symbol or not symbol.strip():
            raise ValueError("Symbol name cannot be empty")
        
        symbol_type = params.get("symbol_type", "any")
        file_pattern = params.get("file_pattern", "*")
        exact_match = params.get("exact_match", True)
        
        # Normalize symbol name
        symbol = symbol.strip()
        
        try:
            # Cache key for lookup results
            cache_key = self._make_cache_key(symbol, symbol_type, file_pattern, exact_match)
            
            # Check cache first
            if cache_key in self._cache:
                logger.debug(f"Cache hit for symbol lookup: {symbol}")
                return self._cache[cache_key]
            
            # Perform symbol lookup
            if exact_match:
                results = await self._lookup_exact(dispatcher, symbol, symbol_type, file_pattern)
            else:
                results = await self._lookup_fuzzy(dispatcher, symbol, symbol_type, file_pattern)
            
            # Format response
            response = {
                "symbol": symbol,
                "symbol_type": symbol_type,
                "file_pattern": file_pattern,
                "exact_match": exact_match,
                "total_matches": len(results),
                "matches": results
            }
            
            # Add to cache
            self._add_to_cache(cache_key, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Symbol lookup failed for '{symbol}': {e}", exc_info=True)
            raise

    async def _lookup_exact(
        self,
        dispatcher: Dispatcher,
        symbol: str,
        symbol_type: str,
        file_pattern: str
    ) -> List[Dict[str, Any]]:
        """Perform exact symbol lookup."""
        try:
            # Use dispatcher to get symbol definition
            symbol_def = dispatcher.lookup(symbol)
            
            if not symbol_def:
                return []
            
            # Filter by symbol type if specified
            if symbol_type != "any" and symbol_def.get("kind", "").lower() != symbol_type.lower():
                return []
            
            # Filter by file pattern if specified
            file_path = symbol_def.get("defined_in", "")
            if file_pattern != "*" and not self._matches_pattern(file_path, file_pattern):
                return []
            
            # Format the result
            formatted_result = self._format_symbol_def(symbol_def)
            return [formatted_result]
            
        except Exception as e:
            logger.error(f"Exact lookup failed for '{symbol}': {e}")
            return []

    async def _lookup_fuzzy(
        self,
        dispatcher: Dispatcher,
        symbol: str,
        symbol_type: str,
        file_pattern: str
    ) -> List[Dict[str, Any]]:
        """Perform fuzzy symbol lookup using search capabilities."""
        try:
            # Use search to find potential symbol matches
            search_results = list(dispatcher.search(symbol, semantic=False, limit=100))
            
            # Extract potential symbols from search results
            potential_symbols = self._extract_symbols_from_search(search_results, symbol)
            
            # Look up each potential symbol
            matched_symbols = []
            seen_symbols = set()
            
            for potential_symbol in potential_symbols:
                if potential_symbol in seen_symbols:
                    continue
                seen_symbols.add(potential_symbol)
                
                symbol_def = dispatcher.lookup(potential_symbol)
                if symbol_def:
                    # Apply filters
                    if symbol_type != "any" and symbol_def.get("kind", "").lower() != symbol_type.lower():
                        continue
                    
                    file_path = symbol_def.get("defined_in", "")
                    if file_pattern != "*" and not self._matches_pattern(file_path, file_pattern):
                        continue
                    
                    # Calculate fuzzy match score
                    fuzzy_score = self._calculate_fuzzy_score(symbol, potential_symbol)
                    if fuzzy_score > 0.3:  # Minimum threshold for fuzzy matching
                        formatted_result = self._format_symbol_def(symbol_def)
                        formatted_result["fuzzy_score"] = fuzzy_score
                        formatted_result["matched_symbol"] = potential_symbol
                        matched_symbols.append(formatted_result)
            
            # Sort by fuzzy score (highest first)
            matched_symbols.sort(key=lambda x: x.get("fuzzy_score", 0), reverse=True)
            
            # Limit results to top 20 for fuzzy matching
            return matched_symbols[:20]
            
        except Exception as e:
            logger.error(f"Fuzzy lookup failed for '{symbol}': {e}")
            return []

    def _extract_symbols_from_search(self, search_results: List[Dict], target_symbol: str) -> List[str]:
        """Extract potential symbol names from search results."""
        symbols = set()
        target_lower = target_symbol.lower()
        
        # Common symbol patterns for different languages
        symbol_patterns = [
            r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',  # Function calls/definitions
            r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)',    # Python functions
            r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # Python/Java classes
            r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)', # JavaScript functions
            r'var\s+([a-zA-Z_][a-zA-Z0-9_]*)',    # Variable declarations
            r'let\s+([a-zA-Z_][a-zA-Z0-9_]*)',    # ES6 let declarations
            r'const\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # ES6 const declarations
            r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*:',    # Object properties/type annotations
            r'typedef\s+.*?\s+([a-zA-Z_][a-zA-Z0-9_]*)', # C typedefs
            r'#define\s+([a-zA-Z_][a-zA-Z0-9_]*)', # C macros
        ]
        
        for result in search_results:
            snippet = result.get("snippet", "")
            
            # Extract symbols using patterns
            for pattern in symbol_patterns:
                matches = re.finditer(pattern, snippet, re.IGNORECASE)
                for match in matches:
                    symbol_name = match.group(1)
                    
                    # Only include symbols that are somewhat similar to target
                    if (target_lower in symbol_name.lower() or 
                        symbol_name.lower() in target_lower or
                        self._calculate_fuzzy_score(target_symbol, symbol_name) > 0.4):
                        symbols.add(symbol_name)
            
            # Also try to extract words that look like symbols
            words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', snippet)
            for word in words:
                if (len(word) > 1 and 
                    (target_lower in word.lower() or 
                     word.lower() in target_lower or
                     self._calculate_fuzzy_score(target_symbol, word) > 0.5)):
                    symbols.add(word)
        
        # Use difflib to find close matches
        close_matches = difflib.get_close_matches(
            target_symbol, list(symbols), n=50, cutoff=0.3
        )
        
        # Combine and deduplicate
        all_symbols = list(symbols) + close_matches
        return list(set(all_symbols))

    def _format_symbol_def(self, symbol_def: SymbolDef) -> Dict[str, Any]:
        """Format a SymbolDef for the response."""
        return {
            "symbol": symbol_def.get("symbol", ""),
            "kind": symbol_def.get("kind", "unknown"),
            "language": symbol_def.get("language", "unknown"),
            "signature": symbol_def.get("signature", ""),
            "documentation": symbol_def.get("doc"),
            "file_path": symbol_def.get("defined_in", ""),
            "line_number": symbol_def.get("line", 0),
            "span": symbol_def.get("span", [0, 0]),
            "context": self._get_symbol_context(symbol_def)
        }

    def _get_symbol_context(self, symbol_def: SymbolDef) -> Dict[str, Any]:
        """Get additional context information for a symbol."""
        context = {
            "accessibility": self._determine_accessibility(symbol_def),
            "scope": self._determine_scope(symbol_def),
            "is_builtin": self._is_builtin_symbol(symbol_def),
            "is_exported": self._is_exported_symbol(symbol_def)
        }
        
        # Add language-specific context
        language = symbol_def.get("language", "").lower()
        if language == "python":
            context.update(self._get_python_context(symbol_def))
        elif language in ["javascript", "typescript"]:
            context.update(self._get_js_context(symbol_def))
        elif language in ["c", "cpp"]:
            context.update(self._get_c_context(symbol_def))
        
        return context

    def _determine_accessibility(self, symbol_def: SymbolDef) -> str:
        """Determine symbol accessibility (public, private, protected)."""
        symbol_name = symbol_def.get("symbol", "")
        language = symbol_def.get("language", "").lower()
        
        if language == "python":
            if symbol_name.startswith("__") and symbol_name.endswith("__"):
                return "magic"
            elif symbol_name.startswith("_"):
                return "private" if symbol_name.startswith("__") else "protected"
            else:
                return "public"
        elif language in ["javascript", "typescript"]:
            # JS/TS doesn't have built-in access modifiers, but conventions exist
            if symbol_name.startswith("_"):
                return "private"
            else:
                return "public"
        elif language in ["c", "cpp"]:
            # In C/C++, we'd need more context to determine this
            return "unknown"
        
        return "public"  # Default assumption

    def _determine_scope(self, symbol_def: SymbolDef) -> str:
        """Determine symbol scope (global, local, class, etc.)."""
        kind = symbol_def.get("kind", "").lower()
        
        if kind in ["class", "interface"]:
            return "global"
        elif kind in ["method", "property"]:
            return "class"
        elif kind in ["function"]:
            return "global"
        elif kind in ["variable"]:
            return "unknown"  # Would need more context
        
        return "unknown"

    def _is_builtin_symbol(self, symbol_def: SymbolDef) -> bool:
        """Check if symbol is a built-in/standard library symbol."""
        file_path = symbol_def.get("defined_in", "")
        language = symbol_def.get("language", "").lower()
        
        # Common patterns for built-in symbols
        builtin_patterns = {
            "python": ["/usr/lib/python", "site-packages", "/Library/Frameworks/Python"],
            "javascript": ["node_modules", "/usr/lib/node"],
            "c": ["/usr/include", "/usr/local/include"],
            "cpp": ["/usr/include", "/usr/local/include"]
        }
        
        if language in builtin_patterns:
            for pattern in builtin_patterns[language]:
                if pattern in file_path:
                    return True
        
        return False

    def _is_exported_symbol(self, symbol_def: SymbolDef) -> bool:
        """Check if symbol is exported/public."""
        # This would require analyzing the file context
        # For now, assume non-private symbols are exported
        accessibility = self._determine_accessibility(symbol_def)
        return accessibility in ["public", "protected"]

    def _get_python_context(self, symbol_def: SymbolDef) -> Dict[str, Any]:
        """Get Python-specific context."""
        return {
            "is_async": "async" in symbol_def.get("signature", ""),
            "is_property": "@property" in symbol_def.get("signature", ""),
            "is_classmethod": "@classmethod" in symbol_def.get("signature", ""),
            "is_staticmethod": "@staticmethod" in symbol_def.get("signature", "")
        }

    def _get_js_context(self, symbol_def: SymbolDef) -> Dict[str, Any]:
        """Get JavaScript/TypeScript-specific context."""
        signature = symbol_def.get("signature", "")
        return {
            "is_async": "async" in signature,
            "is_generator": "function*" in signature,
            "is_arrow_function": "=>" in signature,
            "is_const": signature.startswith("const"),
            "is_let": signature.startswith("let"),
            "is_var": signature.startswith("var")
        }

    def _get_c_context(self, symbol_def: SymbolDef) -> Dict[str, Any]:
        """Get C/C++-specific context."""
        signature = symbol_def.get("signature", "")
        return {
            "is_static": "static" in signature,
            "is_inline": "inline" in signature,
            "is_extern": "extern" in signature,
            "is_const": "const" in signature,
            "is_volatile": "volatile" in signature
        }

    def _calculate_fuzzy_score(self, target: str, candidate: str) -> float:
        """Calculate fuzzy matching score between target and candidate symbols."""
        if target == candidate:
            return 1.0
        
        target_lower = target.lower()
        candidate_lower = candidate.lower()
        
        if target_lower == candidate_lower:
            return 0.95
        
        # Exact substring match
        if target_lower in candidate_lower or candidate_lower in target_lower:
            return 0.8
        
        # Use difflib for sequence matching
        sequence_ratio = difflib.SequenceMatcher(None, target_lower, candidate_lower).ratio()
        
        # Bonus for common prefixes/suffixes
        prefix_bonus = 0
        suffix_bonus = 0
        
        # Check for common prefixes
        for i in range(1, min(len(target_lower), len(candidate_lower)) + 1):
            if target_lower[:i] == candidate_lower[:i]:
                prefix_bonus = i / max(len(target_lower), len(candidate_lower))
            else:
                break
        
        # Check for common suffixes
        for i in range(1, min(len(target_lower), len(candidate_lower)) + 1):
            if target_lower[-i:] == candidate_lower[-i:]:
                suffix_bonus = i / max(len(target_lower), len(candidate_lower))
            else:
                break
        
        # Combine scores
        final_score = sequence_ratio + (prefix_bonus * 0.2) + (suffix_bonus * 0.1)
        return min(1.0, final_score)

    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file path matches the given glob pattern."""
        if pattern == "*":
            return True
        
        try:
            from pathlib import Path
            path_obj = Path(file_path)
            return path_obj.match(pattern)
        except:
            # Fallback to simple string matching
            if pattern.startswith("*."):
                extension = pattern[2:]
                return file_path.endswith(f".{extension}")
            return pattern in file_path

    def _make_cache_key(self, symbol: str, symbol_type: str, file_pattern: str, exact_match: bool) -> str:
        """Create a cache key for lookup parameters."""
        return f"{symbol}:{symbol_type}:{file_pattern}:{exact_match}"

    def _add_to_cache(self, key: str, response: Dict[str, Any]) -> None:
        """Add response to cache with size management."""
        if len(self._cache) >= self._cache_max_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[key] = response


async def lookup_symbol_handler(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle symbol lookup requests.
    
    This is the main entry point for the lookup_symbol tool.
    """
    handler = LookupSymbolHandler()
    return await handler.handle(params, context)


def register_tool(registry: ToolRegistry) -> None:
    """Register the lookup_symbol tool with the registry."""
    metadata = ToolMetadata(
        name="lookup_symbol",
        description="Look up symbol definitions in the codebase with support for exact and fuzzy matching across multiple languages",
        version="1.0.0",
        capabilities=[ToolCapability.LOOKUP, ToolCapability.SEARCH],
        tags=["symbol", "lookup", "definition", "fuzzy", "search", "code", "navigation"],
        author="MCP Team"
    )
    
    registry.register(
        name="lookup_symbol",
        handler=lookup_symbol_handler,
        schema=LOOKUP_SYMBOL_SCHEMA,
        metadata=metadata
    )