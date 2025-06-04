"""
Reference finder tool implementation.

Locates all references to a given symbol with advanced filtering and categorization.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from pathlib import Path
import re
import difflib

from ...dispatcher.dispatcher import Dispatcher
from ...plugin_base import Reference, SymbolDef
from ..registry import ToolRegistry, ToolMetadata, ToolCapability
from ..schemas import FIND_REFERENCES_SCHEMA

logger = logging.getLogger(__name__)


class FindReferencesHandler:
    """Handler for finding symbol references with MCP integration."""
    
    def __init__(self):
        """Initialize the find references handler."""
        self._cache = {}  # Reference cache
        self._cache_max_size = 150
        
    async def handle(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle find references requests.
        
        Args:
            params: Validated parameters from the tool request
            context: Execution context including dispatcher
            
        Returns:
            Reference results formatted for MCP clients
        """
        # Get dispatcher from context
        dispatcher = context.get("dispatcher")
        if not dispatcher:
            raise ValueError("Dispatcher not available in context")
        
        # Extract and validate parameters
        symbol = params["symbol"]
        if not symbol or not symbol.strip():
            raise ValueError("Symbol name cannot be empty")
        
        file_path = params.get("file_path")
        line_number = params.get("line_number")
        include_definitions = params.get("include_definitions", False)
        file_pattern = params.get("file_pattern", "*")
        
        # Normalize symbol name
        symbol = symbol.strip()
        
        try:
            # Cache key for reference results
            cache_key = self._make_cache_key(
                symbol, file_path, line_number, include_definitions, file_pattern
            )
            
            # Check cache first
            if cache_key in self._cache:
                logger.debug(f"Cache hit for reference search: {symbol}")
                return self._cache[cache_key]
            
            # Find references using dispatcher
            references = await self._find_references(
                dispatcher, symbol, file_path, line_number, file_pattern
            )
            
            # Find symbol definition if needed
            definition = None
            if include_definitions:
                definition = await self._find_symbol_definition(dispatcher, symbol)
            
            # Categorize references
            categorized_references = await self._categorize_references(
                references, symbol, definition
            )
            
            # Add context to references
            references_with_context = await self._add_context_to_references(
                categorized_references
            )
            
            # Format response
            response = {
                "symbol": symbol,
                "file_path": file_path,
                "line_number": line_number,
                "include_definitions": include_definitions,
                "file_pattern": file_pattern,
                "total_references": len(references_with_context),
                "references": references_with_context
            }
            
            # Include definition if found and requested
            if include_definitions and definition:
                response["definition"] = self._format_symbol_definition(definition)
            
            # Add to cache
            self._add_to_cache(cache_key, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Reference search failed for {symbol}: {e}", exc_info=True)
            raise

    async def _find_references(
        self,
        dispatcher: Dispatcher,
        symbol: str,
        file_path: Optional[str],
        line_number: Optional[int],
        file_pattern: str
    ) -> List[Reference]:
        """Find all references to a symbol using the dispatcher."""
        try:
            # Use dispatcher to find references
            references = dispatcher.find_references(symbol)
            
            # Filter by file pattern if specified
            if file_pattern != "*":
                filtered_references = []
                for ref in references:
                    if self._matches_pattern(ref.file, file_pattern):
                        filtered_references.append(ref)
                references = filtered_references
            
            # Filter by specific file if provided
            if file_path:
                filtered_references = []
                for ref in references:
                    if ref.file == file_path:
                        filtered_references.append(ref)
                references = filtered_references
            
            # Filter by line number if provided (for more specific context)
            if line_number:
                # Keep references close to the specified line number
                filtered_references = []
                for ref in references:
                    if ref.file == file_path and abs(ref.line - line_number) <= 50:
                        filtered_references.append(ref)
                if filtered_references:  # Only use filtered if we found matches
                    references = filtered_references
            
            return list(references)
            
        except Exception as e:
            logger.error(f"Error finding references for {symbol}: {e}")
            return []

    async def _find_symbol_definition(
        self,
        dispatcher: Dispatcher,
        symbol: str
    ) -> Optional[SymbolDef]:
        """Find the definition of a symbol."""
        try:
            return dispatcher.lookup(symbol)
        except Exception as e:
            logger.error(f"Error finding definition for {symbol}: {e}")
            return None

    async def _categorize_references(
        self,
        references: List[Reference],
        symbol: str,
        definition: Optional[SymbolDef]
    ) -> List[Dict[str, Any]]:
        """Categorize references by type (usage, definition, import, etc.)."""
        categorized = []
        
        for ref in references:
            try:
                # Read the file to analyze the reference context
                file_path = Path(ref.file)
                if not file_path.exists():
                    # File does not exist, treat as generic usage
                    categorized.append({
                        "reference": ref,
                        "type": "usage",
                        "confidence": 0.5,
                        "context_snippet": ""
                    })
                    continue
                
                try:
                    content = file_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    content = file_path.read_text(encoding="latin-1", errors="ignore")
                
                lines = content.split("\n")
                
                # Get the line content (1-based line numbers)
                if 1 <= ref.line <= len(lines):
                    line_content = lines[ref.line - 1]
                else:
                    line_content = ""
                
                # Determine reference type based on context
                ref_type, confidence = self._determine_reference_type(
                    line_content, symbol, ref, definition
                )
                
                categorized.append({
                    "reference": ref,
                    "type": ref_type,
                    "confidence": confidence,
                    "context_snippet": line_content.strip()
                })
                
            except Exception as e:
                logger.debug(f"Error categorizing reference {ref.file}:{ref.line}: {e}")
                # Fallback to generic usage
                categorized.append({
                    "reference": ref,
                    "type": "usage",
                    "confidence": 0.3,
                    "context_snippet": ""
                })
        
        return categorized

    def _determine_reference_type(
        self,
        line_content: str,
        symbol: str,
        reference: Reference,
        definition: Optional[SymbolDef]
    ) -> Tuple[str, float]:
        """Determine the type of reference based on context analysis."""
        line_lower = line_content.lower().strip()
        symbol_lower = symbol.lower()
        
        # High confidence patterns
        
        # Definition patterns
        if definition and reference.file == definition.get("defined_in") and reference.line == definition.get("line"):
            return "definition", 1.0
        
        # Import patterns - create them without using f-strings
        escaped_symbol = re.escape(symbol)
        import_patterns = [
            r"^\s*import\s+.*" + escaped_symbol,
            r"^\s*from\s+.*\s+import\s+.*" + escaped_symbol,
            r"^\s*#include\s*[<\"].*" + escaped_symbol,
            r"^\s*require\s*\(\s*['\"].*" + escaped_symbol,
            r"^\s*const\s+.*=\s*require\s*\(",
            r"^\s*import\s+.*from\s+['\"].*" + escaped_symbol
        ]
        
        for pattern in import_patterns:
            if re.search(pattern, line_content, re.IGNORECASE):
                return "import", 0.9
        
        # Declaration patterns
        declaration_patterns = [
            r"^\s*def\s+" + escaped_symbol + r"\s*\(",
            r"^\s*class\s+" + escaped_symbol + r"\s*[\(:]",
            r"^\s*function\s+" + escaped_symbol + r"\s*\(",
            r"^\s*var\s+" + escaped_symbol + r"\s*[=;]",
            r"^\s*let\s+" + escaped_symbol + r"\s*[=;]",
            r"^\s*const\s+" + escaped_symbol + r"\s*[=;]",
            r"^\s*" + escaped_symbol + r"\s*:\s*function",
            r"^\s*[a-zA-Z_][a-zA-Z0-9_]*\s+" + escaped_symbol + r"\s*[\(;=]",
            r"^\s*typedef\s+.*\s+" + escaped_symbol + r"\s*;"
        ]
        
        for pattern in declaration_patterns:
            if re.search(pattern, line_content, re.IGNORECASE):
                return "declaration", 0.85
        
        # Assignment patterns
        assignment_patterns = [
            r"\b" + escaped_symbol + r"\s*[=]",
            r"\b" + escaped_symbol + r"\s*\+=",
            r"\b" + escaped_symbol + r"\s*-=",
            r"\b" + escaped_symbol + r"\s*\*=",
            r"\b" + escaped_symbol + r"\s*/="
        ]
        
        for pattern in assignment_patterns:
            if re.search(pattern, line_content, re.IGNORECASE):
                return "assignment", 0.8
        
        # Function call patterns
        call_patterns = [
            r"\b" + escaped_symbol + r"\s*\(",
            r"\." + escaped_symbol + r"\s*\(",
            r"->" + escaped_symbol + r"\s*\("
        ]
        
        for pattern in call_patterns:
            if re.search(pattern, line_content, re.IGNORECASE):
                return "call", 0.75
        
        # Property access patterns
        property_patterns = [
            r"\." + escaped_symbol + r"\b",
            r"->" + escaped_symbol + r"\b",
            r"\[" + escaped_symbol + r"\]",
            r"\[['\"]" + escaped_symbol + r"['\"]\]"
        ]
        
        for pattern in property_patterns:
            if re.search(pattern, line_content, re.IGNORECASE):
                return "property_access", 0.7
        
        # Type annotation patterns
        type_patterns = [
            r":\s*" + escaped_symbol + r"\b",
            r"<" + escaped_symbol + r">",
            r"extends\s+" + escaped_symbol + r"\b",
            r"implements\s+" + escaped_symbol + r"\b"
        ]
        
        for pattern in type_patterns:
            if re.search(pattern, line_content, re.IGNORECASE):
                return "type_annotation", 0.65
        
        # Comment patterns (documentation references)
        if line_content.strip().startswith(("#", "//", "/*", "*")):
            if symbol_lower in line_lower:
                return "documentation", 0.4
        
        # String literal patterns (less confidence as could be coincidental)
        string_patterns = [
            r"['\"]" + escaped_symbol + r"['\"]",
            r"['\"].*" + escaped_symbol + r".*['\"]"
        ]
        
        for pattern in string_patterns:
            if re.search(pattern, line_content, re.IGNORECASE):
                return "string_literal", 0.3
        
        # Default to usage if symbol is found
        if symbol_lower in line_lower:
            return "usage", 0.6
        
        # If we cannot determine the type but we have a reference, it is likely usage
        return "usage", 0.5

    async def _add_context_to_references(
        self,
        categorized_references: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Add surrounding context lines to each reference."""
        enhanced_references = []
        
        # Group references by file for efficiency
        references_by_file = {}
        for cat_ref in categorized_references:
            file_path = cat_ref["reference"].file
            if file_path not in references_by_file:
                references_by_file[file_path] = []
            references_by_file[file_path].append(cat_ref)
        
        # Process each file
        for file_path, refs in references_by_file.items():
            try:
                path_obj = Path(file_path)
                if not path_obj.exists():
                    # Add references without context
                    for cat_ref in refs:
                        enhanced_ref = self._format_reference(cat_ref, [], [])
                        enhanced_references.append(enhanced_ref)
                    continue
                
                try:
                    content = path_obj.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    content = path_obj.read_text(encoding="latin-1", errors="ignore")
                
                lines = content.split("\n")
                
                # Add context for each reference in this file
                for cat_ref in refs:
                    line_number = cat_ref["reference"].line
                    context_before, context_after = self._extract_context_lines(
                        lines, line_number, context_lines=3
                    )
                    
                    enhanced_ref = self._format_reference(
                        cat_ref, context_before, context_after
                    )
                    enhanced_references.append(enhanced_ref)
                    
            except Exception as e:
                logger.debug(f"Error adding context for file {file_path}: {e}")
                # Add references without context
                for cat_ref in refs:
                    enhanced_ref = self._format_reference(cat_ref, [], [])
                    enhanced_references.append(enhanced_ref)
        
        # Sort references by file and line number
        enhanced_references.sort(key=lambda x: (x["file_path"], x["line_number"]))
        
        return enhanced_references

    def _extract_context_lines(
        self,
        lines: List[str],
        line_number: int,
        context_lines: int = 3
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Extract context lines before and after the reference line."""
        context_before = []
        context_after = []
        
        # Lines before (1-based line numbers)
        start_line = max(1, line_number - context_lines)
        for i in range(start_line, line_number):
            if 1 <= i <= len(lines):
                context_before.append({
                    "line_number": i,
                    "content": lines[i - 1]  # Convert to 0-based for array access
                })
        
        # Lines after
        end_line = min(len(lines), line_number + context_lines)
        for i in range(line_number + 1, end_line + 1):
            if 1 <= i <= len(lines):
                context_after.append({
                    "line_number": i,
                    "content": lines[i - 1]  # Convert to 0-based for array access
                })
        
        return context_before, context_after

    def _format_reference(
        self,
        categorized_ref: Dict[str, Any],
        context_before: List[Dict[str, Any]],
        context_after: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format a reference with its context for the response."""
        ref = categorized_ref["reference"]
        
        return {
            "file_path": ref.file,
            "line_number": ref.line,
            "type": categorized_ref["type"],
            "confidence": categorized_ref["confidence"],
            "content": categorized_ref["context_snippet"],
            "context_before": context_before,
            "context_after": context_after,
            "metadata": self._get_reference_metadata(categorized_ref)
        }

    def _get_reference_metadata(self, categorized_ref: Dict[str, Any]) -> Dict[str, Any]:
        """Get additional metadata for a reference."""
        ref = categorized_ref["reference"]
        ref_type = categorized_ref["type"]
        
        # Basic metadata
        metadata = {
            "reference_type": ref_type,
            "is_definition": ref_type == "definition",
            "is_import": ref_type == "import",
            "is_declaration": ref_type == "declaration",
            "is_usage": ref_type in ["usage", "call", "property_access"],
            "language": self._detect_language_from_file(ref.file)
        }
        
        # Add type-specific metadata
        if ref_type == "call":
            metadata["is_function_call"] = True
        elif ref_type == "property_access":
            metadata["is_member_access"] = True
        elif ref_type == "assignment":
            metadata["is_assignment"] = True
        elif ref_type == "type_annotation":
            metadata["is_type_reference"] = True
        elif ref_type == "documentation":
            metadata["is_documented"] = True
        
        return metadata

    def _detect_language_from_file(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        path_obj = Path(file_path)
        extension = path_obj.suffix.lower()
        
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".c": "c",
            ".h": "c",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".hpp": "cpp",
            ".hxx": "cpp",
            ".java": "java",
            ".cs": "csharp",
            ".go": "go",
            ".rs": "rust",
            ".php": "php",
            ".rb": "ruby",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".clj": "clojure",
            ".hs": "haskell",
            ".ml": "ocaml",
            ".fs": "fsharp",
            ".dart": "dart",
            ".lua": "lua",
            ".pl": "perl",
            ".r": "r",
            ".m": "objective-c",
            ".mm": "objective-cpp"
        }
        
        return language_map.get(extension, "unknown")

    def _format_symbol_definition(self, definition: SymbolDef) -> Dict[str, Any]:
        """Format a symbol definition for the response."""
        return {
            "symbol": definition.get("symbol", ""),
            "kind": definition.get("kind", "unknown"),
            "language": definition.get("language", "unknown"),
            "signature": definition.get("signature", ""),
            "documentation": definition.get("doc"),
            "file_path": definition.get("defined_in", ""),
            "line_number": definition.get("line", 0),
            "span": definition.get("span", [0, 0])
        }

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

    def _make_cache_key(
        self,
        symbol: str,
        file_path: Optional[str],
        line_number: Optional[int],
        include_definitions: bool,
        file_pattern: str
    ) -> str:
        """Create a cache key for reference search parameters."""
        return f"{symbol}:{file_path}:{line_number}:{include_definitions}:{file_pattern}"

    def _add_to_cache(self, key: str, response: Dict[str, Any]) -> None:
        """Add response to cache with size management."""
        if len(self._cache) >= self._cache_max_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[key] = response


async def find_references_handler(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle find references requests.
    
    This is the main entry point for the find_references tool.
    """
    handler = FindReferencesHandler()
    return await handler.handle(params, context)


def register_tool(registry: ToolRegistry) -> None:
    """Register the find_references tool with the registry."""
    metadata = ToolMetadata(
        name="find_references",
        description="Find all references to a symbol in the codebase with advanced categorization and context",
        version="1.0.0",
        capabilities=[ToolCapability.SEARCH, ToolCapability.LOOKUP],
        tags=["reference", "symbol", "usage", "navigation", "code", "analysis"],
        author="MCP Team"
    )
    
    registry.register(
        name="find_references",
        handler=find_references_handler,
        schema=FIND_REFERENCES_SCHEMA,
        metadata=metadata
    )