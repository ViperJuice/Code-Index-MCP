"""
Code search tool implementation.

Provides pattern and semantic search across codebase.
"""

import asyncio
import re
import logging
from typing import Dict, Any, List, Optional, Iterator
from pathlib import Path

from ...dispatcher.dispatcher import Dispatcher
from ...plugin_base import SearchResult, SearchOpts
from ..registry import ToolRegistry, ToolMetadata, ToolCapability
from ..schemas import SEARCH_CODE_SCHEMA

logger = logging.getLogger(__name__)


class SearchCodeHandler:
    """Handler for code search operations with MCP integration."""
    
    def __init__(self):
        """Initialize the search code handler."""
        self._cache = {}  # Simple result cache
        self._cache_max_size = 100
    
    async def handle(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle code search requests with structured optimization.
        
        Args:
            params: Validated parameters from the tool request
            context: Execution context including dispatcher and agent info
            
        Returns:
            Search results formatted for MCP clients with optional optimization hints
        """
        from ..template_selector import optimize_request, get_optimization_hint
        
        # Get dispatcher from context
        dispatcher = context.get("dispatcher")
        if not dispatcher:
            raise ValueError("Dispatcher not available in context")
        
        # Get agent information
        agent_info = context.get("agent_info", {})
        
        # Store original request for optimization hints
        original_params = params.copy()
        
        # Optimize request using template selector
        optimized_params = optimize_request(params, agent_info)
        
        # Extract and validate parameters (from optimized request)
        if "target" in optimized_params:
            # Structured request format
            query = optimized_params["target"]["query"]
        else:
            # Legacy format
            query = optimized_params.get("query", "")
        
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        # Extract parameters from optimized request
        if "search_optimization" in optimized_params:
            search_opt = optimized_params["search_optimization"]
            file_pattern = search_opt.get("file_patterns", ["*"])[0] if search_opt.get("file_patterns") else "*"
            semantic_weight = search_opt.get("semantic_weight", 0.7)
            search_type = "semantic" if semantic_weight > 0.6 else "literal"
        else:
            # Legacy parameters
            file_pattern = optimized_params.get("file_pattern", "*")
            search_type = optimized_params.get("search_type", "literal")
        
        if "response_format" in optimized_params:
            resp_format = optimized_params["response_format"]
            max_results = resp_format.get("max_results", 100)
            context_lines = resp_format.get("context_lines", 2)
        else:
            # Legacy parameters
            max_results = optimized_params.get("max_results", 100)
            context_lines = optimized_params.get("context_lines", 2)
        
        case_sensitive = optimized_params.get("case_sensitive", False)
        
        # Validate parameters
        if max_results < 1 or max_results > 1000:
            raise ValueError("max_results must be between 1 and 1000")
        if context_lines < 0 or context_lines > 10:
            raise ValueError("context_lines must be between 0 and 10")
        
        try:
            # Perform search based on type
            if search_type == "regex":
                results = await self._search_regex(
                    dispatcher, query, file_pattern, case_sensitive, max_results
                )
            elif search_type == "semantic":
                results = await self._search_semantic(
                    dispatcher, query, file_pattern, max_results
                )
            elif search_type == "fuzzy":
                results = await self._search_fuzzy(
                    dispatcher, query, file_pattern, max_results
                )
            else:  # literal
                results = await self._search_literal(
                    dispatcher, query, file_pattern, case_sensitive, max_results
                )
            
            # Add context lines to results if requested
            if context_lines > 0:
                results = await self._add_context_lines(results, context_lines)
            
            # Format response
            response = {
                "query": query,
                "search_type": search_type,
                "file_pattern": file_pattern,
                "case_sensitive": case_sensitive,
                "total_results": len(results),
                "max_results": max_results,
                "context_lines": context_lines,
                "results": results[:max_results]
            }
            
            # Add pagination info if results were truncated
            if len(results) > max_results:
                response["truncated"] = True
                response["total_found"] = len(results)
            
            # Add optimization hint for unstructured requests
            optimization_hint = get_optimization_hint(original_params, optimized_params, agent_info)
            if optimization_hint:
                response["optimization_hint"] = optimization_hint
            
            # Add structured request metadata if available
            if "request_type" in optimized_params:
                response["request_metadata"] = {
                    "request_type": optimized_params["request_type"],
                    "optimized": True,
                    "agent_type": optimized_params.get("agent_context", {}).get("agent_type", "unknown")
                }
            
            return response
            
        except Exception as e:
            logger.error(f"Search failed for query {query}: {e}", exc_info=True)
            raise


    async def _search_literal(
        self,
        dispatcher: Dispatcher,
        query: str,
        file_pattern: str,
        case_sensitive: bool,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Perform literal text search."""
        try:
            # Create search options
            search_opts = SearchOpts(semantic=False, limit=max_results)
            
            # Perform search using dispatcher
            search_results = dispatcher.search(query, semantic=False, limit=max_results)
            
            results = []
            for result in search_results:
                # Apply case sensitivity filtering if needed
                if not case_sensitive:
                    if query.lower() not in result.get("snippet", "").lower():
                        continue
                elif query not in result.get("snippet", ""):
                    continue
                
                # Apply file pattern filtering
                if file_pattern != "*" and not self._matches_pattern(result.get("file", ""), file_pattern):
                    continue
                
                formatted_result = {
                    "file_path": result.get("file", ""),
                    "line_number": result.get("line", 0),
                    "content": result.get("snippet", ""),
                    "score": 1.0,  # Literal search has uniform score
                    "match_type": "literal"
                }
                results.append(formatted_result)
                
                if len(results) >= max_results:
                    break
            
            return results
            
        except Exception as e:
            logger.error(f"Literal search failed: {e}")
            return []


    async def _search_regex(
        self,
        dispatcher: Dispatcher,
        pattern: str,
        file_pattern: str,
        case_sensitive: bool,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Perform regex pattern search."""
        try:
            # Compile regex pattern
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
            
            # Use literal search as base, then filter with regex
            literal_results = await self._search_literal(
                dispatcher, ".", file_pattern, True, max_results * 5
            )
            
            results = []
            for result in literal_results:
                content = result.get("content", "")
                match = regex.search(content)
                if match:
                    result["match_type"] = "regex"
                    result["match_start"] = match.start()
                    result["match_end"] = match.end()
                    result["matched_text"] = match.group()
                    results.append(result)
                    
                    if len(results) >= max_results:
                        break
            
            return results
            
        except Exception as e:
            logger.error(f"Regex search failed: {e}")
            return []


    async def _search_semantic(
        self,
        dispatcher: Dispatcher,
        query: str,
        file_pattern: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Perform semantic search using embeddings."""
        try:
            # Use dispatcher semantic search capabilities
            search_results = dispatcher.search(query, semantic=True, limit=max_results)
            
            results = []
            for result in search_results:
                # Apply file pattern filtering
                file_path = result.get("file", "")
                if file_pattern != "*" and not self._matches_pattern(file_path, file_pattern):
                    continue
                
                formatted_result = {
                    "file_path": file_path,
                    "line_number": result.get("line", 0),
                    "content": result.get("snippet", ""),
                    "score": 0.8,  # Semantic search typically has high relevance
                    "match_type": "semantic"
                }
                results.append(formatted_result)
                
                if len(results) >= max_results:
                    break
            
            return results
            
        except Exception as e:
            logger.warning(f"Semantic search failed, falling back to literal: {e}")
            # Fall back to literal search
            return await self._search_literal(dispatcher, query, file_pattern, False, max_results)


    async def _search_fuzzy(
        self,
        dispatcher: Dispatcher,
        query: str,
        file_pattern: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Perform fuzzy search with approximate matching."""
        try:
            # For fuzzy search, use case-insensitive literal search
            # and then apply fuzzy matching algorithms
            literal_results = await self._search_literal(
                dispatcher, query, file_pattern, False, max_results * 2
            )
            
            # Apply fuzzy matching scoring
            fuzzy_results = []
            for result in literal_results:
                content = result.get("content", "")
                fuzzy_score = self._calculate_fuzzy_score(query, content)
                
                if fuzzy_score > 0.3:  # Threshold for fuzzy matching
                    result["score"] = fuzzy_score
                    result["match_type"] = "fuzzy"
                    fuzzy_results.append(result)
            
            # Sort by fuzzy score
            fuzzy_results.sort(key=lambda x: x["score"], reverse=True)
            
            return fuzzy_results[:max_results]
            
        except Exception as e:
            logger.warning(f"Fuzzy search failed, falling back to literal: {e}")
            return await self._search_literal(dispatcher, query, file_pattern, False, max_results)


    def _calculate_fuzzy_score(self, query: str, content: str) -> float:
        """Calculate fuzzy matching score between query and content."""
        # Simple fuzzy scoring based on character overlap and position
        query_lower = query.lower()
        content_lower = content.lower()
        
        if query_lower in content_lower:
            return 1.0
        
        # Calculate character overlap
        query_chars = set(query_lower)
        content_chars = set(content_lower)
        overlap = len(query_chars.intersection(content_chars))
        total_chars = len(query_chars.union(content_chars))
        
        if total_chars == 0:
            return 0.0
        
        return overlap / total_chars


    async def _add_context_lines(
        self,
        results: List[Dict[str, Any]],
        context_lines: int
    ) -> List[Dict[str, Any]]:
        """Add context lines around each search result."""
        enhanced_results = []
        
        for result in results:
            file_path = result.get("file_path", "")
            line_number = result.get("line_number", 0)
            
            try:
                # Read file content to get context
                path_obj = Path(file_path)
                if not path_obj.exists():
                    result["context_before"] = []
                    result["context_after"] = []
                    enhanced_results.append(result)
                    continue
                
                content = path_obj.read_text(encoding="utf-8", errors="ignore")
                lines = content.split("\n")
                
                # Calculate context range
                start_line = max(0, line_number - context_lines - 1)
                end_line = min(len(lines), line_number + context_lines)
                
                # Extract context
                context_before = []
                context_after = []
                
                for i in range(start_line, line_number - 1):
                    if i < len(lines):
                        context_before.append({
                            "line_number": i + 1,
                            "content": lines[i]
                        })
                
                for i in range(line_number, end_line):
                    if i < len(lines):
                        context_after.append({
                            "line_number": i + 1,
                            "content": lines[i]
                        })
                
                # Add context to result
                enhanced_result = result.copy()
                enhanced_result["context_before"] = context_before
                enhanced_result["context_after"] = context_after
                enhanced_results.append(enhanced_result)
                
            except Exception as e:
                logger.debug(f"Could not add context for {file_path}: {e}")
                # Add empty context
                result["context_before"] = []
                result["context_after"] = []
                enhanced_results.append(result)
        
        return enhanced_results


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


async def search_code_handler(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle code search requests.
    
    This is the main entry point for the search_code tool.
    """
    handler = SearchCodeHandler()
    return await handler.handle(params, context)


def register_tool(registry: ToolRegistry) -> None:
    """Register the search_code tool with the registry."""
    metadata = ToolMetadata(
        name="search_code",
        description="Search for code patterns across the codebase with support for literal, regex, semantic, and fuzzy search",
        version="1.1.0",
        capabilities=[ToolCapability.SEARCH],
        tags=["search", "code", "pattern", "regex", "semantic", "fuzzy"],
        author="MCP Team"
    )
    
    registry.register(
        name="search_code",
        handler=search_code_handler,
        schema=SEARCH_CODE_SCHEMA,
        metadata=metadata
    )
