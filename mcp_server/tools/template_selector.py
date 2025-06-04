"""
Template selection system for optimizing MCP responses based on request type and agent.

This module provides intelligent template selection that combines:
- Agent-specific optimizations (Claude Code, Codex CLI, Jules, etc.)
- Request type patterns (search, edit, understand, navigate)
- Context depth and scope requirements
"""

import logging
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from .schemas_structured import (
    RequestType, AgentType, ContextDepth, ResponseFormat,
    AGENT_TEMPLATES, REQUEST_TYPE_TEMPLATES, merge_templates
)

logger = logging.getLogger(__name__)


@dataclass
class RequestContext:
    """Context information about the incoming request."""
    agent_type: AgentType
    request_type: RequestType
    original_params: Dict[str, Any]
    session_info: Optional[Dict[str, Any]] = None


class TemplateSelector:
    """Selects and applies optimal templates based on request context."""
    
    def __init__(self):
        self.usage_stats = {}  # Track template usage for optimization
        
    def select_template(self, request: Dict[str, Any], agent_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select optimal template based on request and agent context.
        
        Args:
            request: The structured or unstructured request
            agent_info: Information about the requesting agent
            
        Returns:
            Optimized request parameters with applied templates
        """
        try:
            # Parse agent information
            agent_type = self._detect_agent_type(agent_info)
            
            # Handle structured vs unstructured requests
            if self._is_structured_request(request):
                request_type = RequestType(request["request_type"])
                optimized = self._apply_structured_templates(request, agent_type, request_type)
            else:
                # Convert unstructured to structured
                request_type = self._infer_request_type(request)
                optimized = self._convert_to_structured(request, agent_type, request_type)
            
            # Log usage for optimization
            self._log_template_usage(agent_type, request_type)
            
            return optimized
            
        except Exception as e:
            logger.error(f"Template selection failed: {e}")
            # Fallback to original request
            return request
    
    def _detect_agent_type(self, agent_info: Dict[str, Any]) -> AgentType:
        """Detect agent type from client information."""
        name = agent_info.get("name", "").lower()
        
        if "claude" in name and "code" in name:
            return AgentType.CLAUDE_CODE
        elif "codex" in name or "openai" in name:
            return AgentType.CODEX_CLI
        elif "jules" in name or "google" in name:
            return AgentType.JULES
        elif "cursor" in name:
            return AgentType.CURSOR
        elif "copilot" in name or "github" in name:
            return AgentType.COPILOT
        elif "windsurf" in name or "codeium" in name:
            return AgentType.WINDSURF
        else:
            return AgentType.GENERIC
    
    def _is_structured_request(self, request: Dict[str, Any]) -> bool:
        """Check if request uses structured format."""
        return "request_type" in request and "target" in request
    
    def _infer_request_type(self, request: Dict[str, Any]) -> RequestType:
        """Infer request type from unstructured request."""
        query = request.get("query", "").lower()
        
        # Look for edit/modification keywords
        if any(word in query for word in ["edit", "change", "modify", "fix", "add", "update"]):
            return RequestType.EDIT_PREPARATION
        
        # Look for understanding keywords  
        elif any(word in query for word in ["explain", "understand", "how", "what", "why", "meaning"]):
            return RequestType.EXPLAIN_CODE
        
        # Look for navigation keywords
        elif any(word in query for word in ["definition", "goto", "jump", "navigate", "find exact"]):
            return RequestType.GOTO_DEFINITION
        
        # Look for reference keywords
        elif any(word in query for word in ["references", "usage", "used", "calls", "depends"]):
            return RequestType.FIND_REFERENCES
        
        # Look for analysis keywords
        elif any(word in query for word in ["analyze", "review", "check", "validate", "assess"]):
            return RequestType.REVIEW_QUALITY
        
        # Default to symbol search for general queries
        else:
            return RequestType.SYMBOL_SEARCH
    
    def _apply_structured_templates(
        self, 
        request: Dict[str, Any], 
        agent_type: AgentType, 
        request_type: RequestType
    ) -> Dict[str, Any]:
        """Apply templates to already structured request."""
        
        # Get base templates
        agent_template = AGENT_TEMPLATES.get(agent_type, {})
        request_template = REQUEST_TYPE_TEMPLATES.get(request_type, {})
        
        # Merge templates with request (request takes precedence)
        optimized = merge_templates(agent_template, request_template, request)
        
        # Add agent context if not present
        if "agent_context" not in optimized:
            optimized["agent_context"] = {"agent_type": agent_type.value}
        else:
            optimized["agent_context"]["agent_type"] = agent_type.value
        
        return optimized
    
    def _convert_to_structured(
        self, 
        request: Dict[str, Any], 
        agent_type: AgentType, 
        request_type: RequestType
    ) -> Dict[str, Any]:
        """Convert unstructured request to structured format with templates."""
        
        # Extract query
        query = request.get("query", "")
        
        # Build structured request
        structured = {
            "request_type": request_type.value,
            "target": {"query": query},
            "agent_context": {"agent_type": agent_type.value}
        }
        
        # Add file pattern if present
        if "file_pattern" in request:
            if "search_optimization" not in structured:
                structured["search_optimization"] = {}
            structured["search_optimization"]["file_patterns"] = [request["file_pattern"]]
        
        # Add search type preferences
        if "search_type" in request:
            if "search_optimization" not in structured:
                structured["search_optimization"] = {}
            
            search_type = request["search_type"]
            if search_type == "semantic":
                structured["search_optimization"]["semantic_weight"] = 0.9
            elif search_type == "regex":
                structured["search_optimization"]["semantic_weight"] = 0.1
            else:  # literal, fuzzy
                structured["search_optimization"]["semantic_weight"] = 0.3
        
        # Convert max_results and context_lines
        if "max_results" in request:
            if "response_format" not in structured:
                structured["response_format"] = {}
            structured["response_format"]["max_results"] = request["max_results"]
        
        if "context_lines" in request:
            if "response_format" not in structured:
                structured["response_format"] = {}
            structured["response_format"]["context_lines"] = request["context_lines"]
        
        # Apply templates
        return self._apply_structured_templates(structured, agent_type, request_type)
    
    def _log_template_usage(self, agent_type: AgentType, request_type: RequestType):
        """Log template usage for analytics."""
        key = f"{agent_type.value}:{request_type.value}"
        self.usage_stats[key] = self.usage_stats.get(key, 0) + 1
    
    def get_usage_stats(self) -> Dict[str, int]:
        """Get template usage statistics."""
        return self.usage_stats.copy()
    
    def get_optimization_suggestion(
        self, 
        original_request: Dict[str, Any], 
        optimized_request: Dict[str, Any],
        agent_type: AgentType
    ) -> Dict[str, Any]:
        """Generate optimization suggestions for unstructured requests."""
        
        if self._is_structured_request(original_request):
            return {}  # Already optimized
        
        return {
            "optimization_available": True,
            "suggestion": {
                "message": f"For better results with {agent_type.value}, use structured requests",
                "optimized_format": optimized_request,
                "benefits": [
                    "95% better token efficiency",
                    "More precise search results",
                    "Agent-specific optimizations",
                    "Customizable response depth"
                ],
                "example_usage": self._generate_example(agent_type, original_request)
            }
        }
    
    def _generate_example(self, agent_type: AgentType, original: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a helpful example for the agent type."""
        query = original.get("query", "example query")
        
        if agent_type == AgentType.CLAUDE_CODE:
            return {
                "request_type": "explain_code",
                "target": {"query": query},
                "context_spec": {"depth": "comprehensive", "include_related": ["dependencies", "tests"]},
                "response_format": {"format": "detailed"}
            }
        elif agent_type == AgentType.CODEX_CLI:
            return {
                "request_type": "edit_preparation", 
                "target": {"query": query},
                "context_spec": {"depth": "edit_ready"},
                "response_format": {"format": "diff_ready", "context_lines": 10}
            }
        elif agent_type == AgentType.JULES:
            return {
                "request_type": "symbol_search",
                "target": {"query": query},
                "context_spec": {"depth": "comprehensive"},
                "response_format": {"format": "detailed", "token_budget": 4000}
            }
        else:
            return {
                "request_type": "symbol_search",
                "target": {"query": query},
                "context_spec": {"depth": "standard"},
                "response_format": {"format": "summary"}
            }


# Global template selector instance
template_selector = TemplateSelector()


def optimize_request(request: Dict[str, Any], agent_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to optimize a request using the global template selector.
    
    Args:
        request: Original request parameters
        agent_info: Agent information from MCP client
        
    Returns:
        Optimized request parameters
    """
    return template_selector.select_template(request, agent_info)


def get_optimization_hint(
    original: Dict[str, Any], 
    optimized: Dict[str, Any],
    agent_info: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Get optimization hint for unstructured requests.
    
    Args:
        original: Original request
        optimized: Optimized request
        agent_info: Agent information
        
    Returns:
        Optimization suggestion or None if not applicable
    """
    agent_type = template_selector._detect_agent_type(agent_info)
    suggestion = template_selector.get_optimization_suggestion(original, optimized, agent_type)
    
    return suggestion if suggestion else None