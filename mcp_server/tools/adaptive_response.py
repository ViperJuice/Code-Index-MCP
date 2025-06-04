"""
Adaptive response system for providing optimization guidance to agents.

This module handles response enhancement, optimization hints, and guidance
for agents using unstructured requests or suboptimal patterns.
"""

import logging
from typing import Dict, Any, Optional, List
from .schemas_structured import AgentType, RequestType, ContextDepth, ResponseFormat
from .template_selector import template_selector

logger = logging.getLogger(__name__)


class AdaptiveResponseEnhancer:
    """Enhances responses with optimization guidance and hints."""
    
    def __init__(self):
        self.response_cache = {}  # Cache optimization suggestions
        self.feedback_stats = {}  # Track user feedback on suggestions
    
    def enhance_response(
        self, 
        original_response: Dict[str, Any],
        original_request: Dict[str, Any],
        optimized_request: Dict[str, Any],
        agent_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhance response with optimization guidance.
        
        Args:
            original_response: The original tool response
            original_request: The original request parameters
            optimized_request: The optimized request parameters  
            agent_info: Information about the requesting agent
            
        Returns:
            Enhanced response with optimization hints
        """
        enhanced = original_response.copy()
        
        # Add optimization hint if request was unstructured
        if not self._is_structured_request(original_request):
            hint = self._generate_optimization_hint(
                original_request, optimized_request, agent_info
            )
            if hint:
                enhanced["optimization_hint"] = hint
        
        # Add learning suggestions based on results
        learning_suggestion = self._generate_learning_suggestion(
            original_response, optimized_request, agent_info
        )
        if learning_suggestion:
            enhanced["learning_suggestion"] = learning_suggestion
        
        # Add next steps guidance
        next_steps = self._suggest_next_steps(
            original_response, optimized_request, agent_info
        )
        if next_steps:
            enhanced["suggested_next_steps"] = next_steps
        
        return enhanced
    
    def _is_structured_request(self, request: Dict[str, Any]) -> bool:
        """Check if request uses structured format."""
        return "request_type" in request and "target" in request
    
    def _generate_optimization_hint(
        self,
        original: Dict[str, Any],
        optimized: Dict[str, Any], 
        agent_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate optimization hint for unstructured requests."""
        
        agent_type = template_selector._detect_agent_type(agent_info)
        
        # Calculate potential improvements
        improvements = self._calculate_improvements(original, optimized, agent_type)
        
        if not improvements["significant"]:
            return None  # Don't show hints for minimal improvements
        
        return {
            "message": f"💡 Optimize your {agent_type.value} workflow with structured requests",
            "current_efficiency": improvements["current_score"],
            "potential_efficiency": improvements["optimized_score"],
            "improvements": improvements["benefits"],
            "example_optimization": {
                "instead_of": self._simplify_request(original),
                "try_this": self._simplify_request(optimized),
                "benefits": improvements["specific_benefits"]
            },
            "learn_more": "Use 'get_search_guidance' tool for personalized optimization"
        }
    
    def _calculate_improvements(
        self, 
        original: Dict[str, Any], 
        optimized: Dict[str, Any],
        agent_type: AgentType
    ) -> Dict[str, Any]:
        """Calculate potential improvements from optimization."""
        
        # Score original request (0-100)
        current_score = 30  # Base score for working request
        if "search_type" in original:
            current_score += 10  # +10 for explicit search type
        if "max_results" in original:
            current_score += 5   # +5 for result limiting
        if "file_pattern" in original:
            current_score += 5   # +5 for file filtering
        
        # Score optimized request (0-100)
        optimized_score = 60  # Base score for structured request
        if "search_optimization" in optimized:
            optimized_score += 15  # +15 for search optimization
        if "context_spec" in optimized:
            optimized_score += 15  # +15 for context specification
        if "response_format" in optimized:
            optimized_score += 10  # +10 for response formatting
        
        # Agent-specific bonuses
        if agent_type == AgentType.CLAUDE_CODE and optimized.get("context_spec", {}).get("depth") == "comprehensive":
            optimized_score += 10
        elif agent_type == AgentType.CODEX_CLI and optimized.get("response_format", {}).get("format") == "diff_ready":
            optimized_score += 10
        
        improvement_delta = optimized_score - current_score
        
        benefits = []
        specific_benefits = []
        
        if improvement_delta >= 20:
            benefits.append("🚀 Significantly faster results")
            specific_benefits.append("Search algorithms optimized for your request type")
        
        if "semantic_weight" in optimized.get("search_optimization", {}):
            benefits.append("🎯 More relevant results")
            specific_benefits.append("Balanced semantic vs keyword matching")
        
        if optimized.get("context_spec", {}).get("depth") in ["edit_ready", "comprehensive"]:
            benefits.append("📝 Better context for your workflow")
            specific_benefits.append("Context depth optimized for " + agent_type.value)
        
        if optimized.get("response_format", {}).get("token_budget"):
            benefits.append("⚡ Efficient token usage")
            specific_benefits.append("Token budget management")
        
        return {
            "current_score": current_score,
            "optimized_score": min(optimized_score, 100),
            "improvement_delta": improvement_delta,
            "significant": improvement_delta >= 15,
            "benefits": benefits,
            "specific_benefits": specific_benefits
        }
    
    def _simplify_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify request for display in hints."""
        if "request_type" in request:
            # Structured request - show key parts
            simplified = {
                "request_type": request["request_type"],
                "target": request.get("target", {}),
            }
            if "context_spec" in request:
                simplified["context_spec"] = request["context_spec"]
            return simplified
        else:
            # Legacy request - show as-is
            return {k: v for k, v in request.items() if k in ["query", "search_type", "max_results"]}
    
    def _generate_learning_suggestion(
        self,
        response: Dict[str, Any],
        optimized_request: Dict[str, Any],
        agent_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate learning suggestions based on search results."""
        
        results = response.get("results", [])
        if not results:
            return None
        
        agent_type = template_selector._detect_agent_type(agent_info)
        request_type = optimized_request.get("request_type")
        
        suggestions = []
        
        # Handle empty results with fallback suggestions
        if not results:
            suggestions.append({
                "action": "try_broader_search_terms",
                "reason": "No results found - try broader or different search terms with MCP first",
                "mcp_suggestions": [
                    "Try more general keywords (e.g., 'auth' instead of 'authentication')",
                    "Search for related concepts (e.g., 'login', 'user', 'session')", 
                    "Use pattern search for code structures (e.g., 'class.*User')",
                    "Search in specific file types (e.g., '*.py', '*.js')"
                ],
                "example": "Try: search_code with broader terms before using native tools"
            })
            
            suggestions.append({
                "action": "fallback_to_native_discovery",
                "reason": "If MCP search still finds nothing, use native code discovery methods",
                "native_fallbacks": [
                    "Use 'LS' tool to explore directory structure",
                    "Use 'grep' or 'ripgrep' for text-based search",
                    "Check recently modified files with 'git log --name-only'",
                    "Search external dependencies and vendor directories",
                    "Look in documentation, README files, and comments"
                ],
                "claude_code_specific": [
                    "Try: 'ls src/' to explore source structure",
                    "Try: 'grep -r \"authentication\" .' for text search",
                    "Try: 'find . -name \"*auth*\" -type f' for file names"
                ]
            })
            return {"suggestions": suggestions}
        
        # Suggest follow-up actions based on results
        if request_type == "symbol_search" and len(results) > 0:
            suggestions.append({
                "action": "Deep dive with explain_code",
                "reason": "Found symbols - get comprehensive understanding",
                "example": {
                    "request_type": "explain_code",
                    "target": {"symbol": results[0].get("content", "").split()[0]},
                    "context_spec": {"depth": "comprehensive"}
                }
            })
        
        if request_type == "explain_code" and agent_type in [AgentType.CODEX_CLI, AgentType.CLAUDE_CODE]:
            suggestions.append({
                "action": "Get edit-ready context", 
                "reason": "Ready to modify? Get precise editing context",
                "example": {
                    "request_type": "edit_preparation",
                    "target": optimized_request["target"],
                    "context_spec": {"depth": "edit_ready"}
                }
            })
        
        if len(results) > 20:
            suggestions.append({
                "action": "Refine your search",
                "reason": "Many results found - add filters for precision",
                "example": {
                    **optimized_request,
                    "search_optimization": {
                        **optimized_request.get("search_optimization", {}),
                        "file_patterns": ["*.py"],  # Example filter
                        "semantic_weight": 0.8
                    }
                }
            })
        
        return {"suggestions": suggestions} if suggestions else None
    
    def _suggest_next_steps(
        self,
        response: Dict[str, Any],
        optimized_request: Dict[str, Any], 
        agent_info: Dict[str, Any]
    ) -> Optional[list[Dict[str, Any]]]:
        """Suggest logical next steps based on current results."""
        
        request_type = optimized_request.get("request_type")
        agent_type = template_selector._detect_agent_type(agent_info)
        results = response.get("results", [])
        
        if not results:
            return None
        
        next_steps = []
        
        # Common workflow progressions
        if request_type == "symbol_search":
            next_steps.extend([
                {
                    "step": "goto_definition",
                    "description": "Navigate to symbol definition",
                    "use_case": "Quick exploration of found symbols"
                },
                {
                    "step": "find_references", 
                    "description": "See how symbols are used",
                    "use_case": "Understand usage patterns and dependencies"
                }
            ])
        
        elif request_type == "goto_definition":
            next_steps.extend([
                {
                    "step": "explain_code",
                    "description": "Understand the symbol thoroughly",
                    "use_case": "Before making modifications"
                },
                {
                    "step": "find_references",
                    "description": "Check impact before changes",
                    "use_case": "Safe refactoring and modifications"
                }
            ])
        
        elif request_type == "explain_code":
            if agent_type in [AgentType.CODEX_CLI, AgentType.CLAUDE_CODE]:
                next_steps.append({
                    "step": "edit_preparation",
                    "description": "Get edit-ready context",
                    "use_case": "Ready to make changes"
                })
        
        # Agent-specific suggestions
        if agent_type == AgentType.JULES:
            next_steps.append({
                "step": "assess_impact",
                "description": "Analyze change implications for autonomous work",
                "use_case": "Before implementing features or fixes"
            })
        
        return next_steps if next_steps else None
    
    def record_feedback(self, hint_id: str, feedback: str):
        """Record user feedback on optimization hints."""
        if hint_id not in self.feedback_stats:
            self.feedback_stats[hint_id] = {"helpful": 0, "not_helpful": 0}
        
        if feedback in ["helpful", "used"]:
            self.feedback_stats[hint_id]["helpful"] += 1
        elif feedback in ["not_helpful", "ignored"]:
            self.feedback_stats[hint_id]["not_helpful"] += 1
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get feedback statistics for optimization."""
        return self.feedback_stats.copy()


# Global response enhancer instance
response_enhancer = AdaptiveResponseEnhancer()


def enhance_response(
    response: Dict[str, Any],
    original_request: Dict[str, Any],
    optimized_request: Dict[str, Any],
    agent_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Convenience function to enhance a response with optimization guidance.
    
    Args:
        response: Original tool response
        original_request: Original request parameters
        optimized_request: Optimized request parameters
        agent_info: Agent information
        
    Returns:
        Enhanced response with guidance
    """
    return response_enhancer.enhance_response(
        response, original_request, optimized_request, agent_info
    )