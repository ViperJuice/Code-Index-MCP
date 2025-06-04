"""
Search guidance handler for providing personalized optimization advice.

This module implements the get_search_guidance tool that helps agents
structure optimal requests based on their specific tasks and capabilities.
"""

import logging
from typing import Dict, Any
from .enhanced_descriptions import format_instruction_prompt
from .template_selector import template_selector
from .schemas_structured import AgentType, RequestType

logger = logging.getLogger(__name__)


class SearchGuidanceHandler:
    """Handler for providing personalized search guidance to agents."""
    
    def __init__(self):
        self.guidance_cache = {}  # Cache common guidance patterns
    
    async def handle(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle search guidance requests.
        
        Args:
            params: Request parameters including task description
            context: Execution context including agent info
            
        Returns:
            Personalized guidance with optimized request structure
        """
        try:
            # Extract task description
            task = params.get("task", "")
            if not task.strip():
                return {
                    "error": "Please provide a task description",
                    "example": "I need to add rate limiting to the login function"
                }
            
            # Get agent information from context
            agent_info = context.get("agent_info", {})
            agent_type = template_selector._detect_agent_type(agent_info)
            
            # Generate personalized guidance
            guidance = self._generate_guidance(task, agent_type, agent_info)
            
            return guidance
            
        except Exception as e:
            logger.error(f"Search guidance failed: {e}")
            return {
                "error": "Failed to generate guidance",
                "fallback": "Use structured requests with request_type, target, and context_spec"
            }
    
    def _generate_guidance(
        self, 
        task: str, 
        agent_type: AgentType, 
        agent_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive guidance for the given task and agent."""
        
        # Infer request type from task
        request_type = self._infer_request_type_from_task(task)
        
        # Create optimal request structure
        optimal_request = self._create_optimal_request(task, agent_type, request_type)
        
        # Generate instruction prompt
        instruction = format_instruction_prompt(task, agent_type.value)
        
        # Calculate estimated benefits
        benefits = self._calculate_benefits(agent_type, request_type)
        
        return {
            "task_analysis": {
                "task": task,
                "inferred_intent": request_type.value,
                "agent_type": agent_type.value,
                "confidence": self._calculate_confidence(task, request_type)
            },
            "optimal_request": optimal_request,
            "instruction_prompt": instruction,
            "benefits": benefits,
            "alternatives": self._suggest_alternatives(task, request_type),
            "examples": self._get_related_examples(agent_type, request_type)
        }
    
    def _infer_request_type_from_task(self, task: str) -> RequestType:
        """Infer the most likely request type from task description."""
        task_lower = task.lower()
        
        # More sophisticated intent detection
        edit_keywords = ["edit", "change", "modify", "fix", "add", "update", "implement", "create"]
        understand_keywords = ["explain", "understand", "how", "what", "why", "analyze", "meaning"]
        search_keywords = ["find", "search", "locate", "where", "show", "list"]
        navigate_keywords = ["go to", "jump", "navigate", "definition", "source"]
        reference_keywords = ["references", "usage", "used", "calls", "depends", "who uses"]
        
        # Score each category
        scores = {
            RequestType.EDIT_PREPARATION: sum(1 for kw in edit_keywords if kw in task_lower),
            RequestType.EXPLAIN_CODE: sum(1 for kw in understand_keywords if kw in task_lower),
            RequestType.SYMBOL_SEARCH: sum(1 for kw in search_keywords if kw in task_lower),
            RequestType.GOTO_DEFINITION: sum(1 for kw in navigate_keywords if kw in task_lower),
            RequestType.FIND_REFERENCES: sum(1 for kw in reference_keywords if kw in task_lower)
        }
        
        # Return highest scoring request type, default to search
        if max(scores.values()) == 0:
            return RequestType.SYMBOL_SEARCH
        
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def _create_optimal_request(
        self, 
        task: str, 
        agent_type: AgentType, 
        request_type: RequestType
    ) -> Dict[str, Any]:
        """Create optimal request structure for the task."""
        
        # Extract potential symbol/query from task
        query = self._extract_query_from_task(task)
        
        # Base request structure
        request = {
            "request_type": request_type.value,
            "target": {"query": query},
            "agent_context": {"agent_type": agent_type.value}
        }
        
        # Apply agent and request type templates
        optimized = template_selector._apply_structured_templates(request, agent_type, request_type)
        
        return optimized
    
    def _extract_query_from_task(self, task: str) -> str:
        """Extract the most relevant search query from task description."""
        # Simple extraction - could be enhanced with NLP
        task_lower = task.lower()
        
        # Look for quoted strings
        import re
        quoted = re.findall(r'"([^"]*)"', task)
        if quoted:
            return quoted[0]
        
        # Look for function/class names (camelCase or snake_case)
        identifiers = re.findall(r'\b[a-z_][a-z0-9_]*[a-z0-9]\b', task_lower)
        if identifiers:
            return max(identifiers, key=len)  # Return longest identifier
        
        # Look for key nouns
        nouns = re.findall(r'\b(?:function|class|method|component|module|service|handler|manager|processor)\b', task_lower)
        if nouns:
            return nouns[0]
        
        # Fallback: use key words from task
        words = task.split()
        meaningful_words = [w for w in words if len(w) > 3 and w.lower() not in 
                          ['need', 'want', 'help', 'please', 'could', 'would', 'should']]
        
        if meaningful_words:
            return ' '.join(meaningful_words[:3])  # Take first 3 meaningful words
        
        return task[:50]  # Fallback to first 50 chars
    
    def _calculate_confidence(self, task: str, request_type: RequestType) -> float:
        """Calculate confidence in the inferred request type."""
        task_lower = task.lower()
        
        # Strong indicators for each type
        strong_indicators = {
            RequestType.EDIT_PREPARATION: ["edit", "modify", "fix", "change", "add to"],
            RequestType.EXPLAIN_CODE: ["explain", "understand", "how does", "what is"],
            RequestType.SYMBOL_SEARCH: ["find", "search", "locate", "show me"],
            RequestType.GOTO_DEFINITION: ["go to", "jump to", "definition of"],
            RequestType.FIND_REFERENCES: ["references", "usage", "who uses", "where used"]
        }
        
        indicators = strong_indicators.get(request_type, [])
        matches = sum(1 for indicator in indicators if indicator in task_lower)
        
        # Convert to confidence score
        if matches >= 2:
            return 0.95
        elif matches == 1:
            return 0.8
        else:
            return 0.6
    
    def _calculate_benefits(self, agent_type: AgentType, request_type: RequestType) -> Dict[str, Any]:
        """Calculate estimated benefits of using structured requests."""
        
        base_benefits = {
            "token_efficiency": "70-95% reduction vs unstructured",
            "result_precision": "Higher relevance and accuracy",
            "response_speed": "Optimized search algorithms",
            "context_control": "Customizable depth and scope"
        }
        
        # Agent-specific benefits
        agent_benefits = {
            AgentType.CLAUDE_CODE: {
                "workflow_integration": "Optimized for comprehensive analysis",
                "context_awareness": "Deep dependency and test integration",
                "token_budget": "Intelligent context expansion"
            },
            AgentType.CODEX_CLI: {
                "edit_optimization": "Diff-ready format for immediate editing",
                "precision_mode": "Exact symbol targeting",
                "approval_workflow": "Safe modification guidance"
            },
            AgentType.JULES: {
                "autonomous_support": "Rich context for independent decisions",
                "scalability": "Higher token budgets for complex tasks",
                "api_awareness": "Breaking change analysis"
            }
        }
        
        return {
            **base_benefits,
            **agent_benefits.get(agent_type, {})
        }
    
    def _suggest_alternatives(self, task: str, primary_type: RequestType) -> list[Dict[str, Any]]:
        """Suggest alternative request types for the task."""
        
        alternatives = []
        
        # Common alternative patterns
        if primary_type == RequestType.SYMBOL_SEARCH:
            alternatives.extend([
                {
                    "request_type": "explain_code",
                    "use_case": "If you need to understand the code before using it",
                    "benefit": "Comprehensive context with examples and documentation"
                },
                {
                    "request_type": "edit_preparation", 
                    "use_case": "If you plan to modify the found code",
                    "benefit": "Edit-ready context with dependencies and risks"
                }
            ])
        
        elif primary_type == RequestType.EDIT_PREPARATION:
            alternatives.extend([
                {
                    "request_type": "find_references",
                    "use_case": "Check impact before making changes",
                    "benefit": "See all code that depends on your target"
                },
                {
                    "request_type": "explain_code",
                    "use_case": "Understand the code thoroughly first",
                    "benefit": "Avoid breaking existing functionality"
                }
            ])
        
        elif primary_type == RequestType.EXPLAIN_CODE:
            alternatives.extend([
                {
                    "request_type": "find_references",
                    "use_case": "See how the code is used in practice",
                    "benefit": "Real usage examples and patterns"
                },
                {
                    "request_type": "goto_definition",
                    "use_case": "Quick navigation to specific symbols",
                    "benefit": "Minimal context for fast exploration"
                }
            ])
        
        return alternatives
    
    def _get_related_examples(
        self, 
        agent_type: AgentType, 
        request_type: RequestType
    ) -> list[Dict[str, Any]]:
        """Get related examples for the agent and request type."""
        
        examples = []
        
        # Agent-specific examples
        if agent_type == AgentType.CLAUDE_CODE and request_type == RequestType.EXPLAIN_CODE:
            examples.append({
                "scenario": "Understanding a complex algorithm",
                "request": {
                    "request_type": "explain_code",
                    "target": {"query": "authentication flow"},
                    "context_spec": {
                        "depth": "comprehensive",
                        "include_related": ["dependencies", "tests", "docs", "examples"]
                    },
                    "response_format": {"format": "detailed", "token_budget": 3000}
                },
                "outcome": "Complete understanding with security considerations and usage patterns"
            })
        
        elif agent_type == AgentType.CODEX_CLI and request_type == RequestType.EDIT_PREPARATION:
            examples.append({
                "scenario": "Adding a new parameter to a function",
                "request": {
                    "request_type": "edit_preparation",
                    "target": {"symbol": "process_payment"},
                    "context_spec": {
                        "depth": "edit_ready",
                        "include_related": ["dependencies", "tests"]
                    },
                    "response_format": {"format": "diff_ready", "context_lines": 10}
                },
                "outcome": "Precise editing context with test update guidance"
            })
        
        return examples


async def search_guidance_handler(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Main entry point for search guidance tool."""
    handler = SearchGuidanceHandler()
    return await handler.handle(params, context)


# Schema for search guidance tool
SEARCH_GUIDANCE_SCHEMA = {
    "type": "object",
    "description": "Get personalized guidance for structuring optimal code search requests",
    "properties": {
        "task": {
            "type": "string",
            "description": "Description of what you're trying to accomplish"
        },
        "current_query": {
            "type": "string",
            "description": "Your current search query (optional)",
            "default": ""
        },
        "preferences": {
            "type": "object",
            "description": "Optional preferences for guidance",
            "properties": {
                "detail_level": {
                    "enum": ["brief", "standard", "comprehensive"],
                    "default": "standard",
                    "description": "How detailed the guidance should be"
                },
                "include_examples": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include practical examples"
                }
            }
        }
    },
    "required": ["task"]
}