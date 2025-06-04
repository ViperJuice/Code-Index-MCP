"""
Enhanced structured request schemas for different agent request types.

This module defines comprehensive schemas for all types of code retrieval requests
that AI agents might make, optimized for vector search, keyword matching, and
precise response formatting.
"""

from typing import Dict, Any, List, Optional
from enum import Enum


class RequestType(Enum):
    """Core request type categories."""
    # Discovery - "What exists?"
    SYMBOL_SEARCH = "symbol_search"
    PATTERN_SEARCH = "pattern_search" 
    DEPENDENCY_DISCOVERY = "dependency_discovery"
    FILE_EXPLORATION = "file_exploration"
    
    # Navigation - "Where is it?"
    GOTO_DEFINITION = "goto_definition"
    FIND_REFERENCES = "find_references"
    CALL_HIERARCHY = "call_hierarchy"
    INHERITANCE_TREE = "inheritance_tree"
    
    # Understanding - "How does it work?"
    EXPLAIN_CODE = "explain_code"
    ANALYZE_FLOW = "analyze_flow"
    ASSESS_IMPACT = "assess_impact"
    REVIEW_QUALITY = "review_quality"
    
    # Modification - "Help me change it"
    EDIT_PREPARATION = "edit_preparation"
    REFACTOR_PLANNING = "refactor_planning"
    TEMPLATE_GENERATION = "template_generation"
    CONFLICT_RESOLUTION = "conflict_resolution"


class ContextDepth(Enum):
    """How much context to include in responses."""
    MINIMAL = "minimal"          # Just the essential info
    STANDARD = "standard"        # Balanced context 
    COMPREHENSIVE = "comprehensive"  # Full context
    EDIT_READY = "edit_ready"    # Optimized for editing


class ResponseFormat(Enum):
    """How to structure the response."""
    SUMMARY = "summary"          # High-level overview
    DETAILED = "detailed"        # Full information
    CODE_ONLY = "code_only"      # Just code snippets
    NAVIGATION = "navigation"    # Location-focused
    DIFF_READY = "diff_ready"    # Ready for editing


class AgentType(Enum):
    """Supported AI coding agents."""
    CLAUDE_CODE = "claude_code"
    CODEX_CLI = "codex_cli"
    JULES = "jules"
    CURSOR = "cursor"
    COPILOT = "copilot"
    WINDSURF = "windsurf"
    GENERIC = "generic"


# Core structured request schema
STRUCTURED_REQUEST_SCHEMA = {
    "type": "object",
    "properties": {
        # Core search parameters
        "request_type": {
            "enum": [rt.value for rt in RequestType],
            "description": "Specific type of context needed"
        },
        "target": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query"
                },
                "symbol": {
                    "type": "string", 
                    "description": "Exact symbol name (optional)"
                },
                "file_path": {
                    "type": "string",
                    "description": "Specific file path (optional)"
                },
                "line_range": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Start and end line numbers [start, end]"
                }
            },
            "required": ["query"]
        },
        
        # Search strategy optimization
        "search_optimization": {
            "type": "object",
            "properties": {
                "semantic_weight": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0.7,
                    "description": "Preference for semantic vs keyword search (0=keyword, 1=semantic)"
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific keywords to emphasize"
                },
                "exact_symbols": {
                    "type": "array", 
                    "items": {"type": "string"},
                    "description": "Exact symbol names to match"
                },
                "file_patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File glob patterns to include/exclude"
                },
                "language_filter": {
                    "type": "string",
                    "description": "Programming language to focus on"
                },
                "recency_preference": {
                    "enum": ["recent", "stable", "any"],
                    "default": "any",
                    "description": "Preference for recently modified code"
                }
            }
        },
        
        # Context scope and depth
        "context_spec": {
            "type": "object",
            "properties": {
                "depth": {
                    "enum": [cd.value for cd in ContextDepth],
                    "default": "standard",
                    "description": "How much context to include"
                },
                "scope": {
                    "enum": ["symbol", "function", "class", "file", "module", "project"],
                    "default": "function",
                    "description": "Boundaries of context retrieval"
                },
                "include_related": {
                    "type": "array",
                    "items": {
                        "enum": ["dependencies", "dependents", "tests", "docs", "examples", "similar_code"]
                    },
                    "description": "Related information to include"
                }
            }
        },
        
        # Response formatting preferences  
        "response_format": {
            "type": "object",
            "properties": {
                "format": {
                    "enum": [rf.value for rf in ResponseFormat],
                    "default": "detailed",
                    "description": "How to structure the response"
                },
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 10,
                    "description": "Maximum number of results to return"
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 20,
                    "default": 5,
                    "description": "Lines of context around matches"
                },
                "include_line_numbers": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include line numbers in code snippets"
                },
                "include_metadata": {
                    "type": "boolean", 
                    "default": True,
                    "description": "Include file metadata and statistics"
                },
                "token_budget": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 10000,
                    "default": 2000,
                    "description": "Approximate token budget for response"
                }
            }
        },
        
        # Repository filtering
        "repository_filter": {
            "type": "object",
            "properties": {
                "repositories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific repository names or IDs to search"
                },
                "repository_types": {
                    "type": "array", 
                    "items": {"enum": ["local", "reference", "temporary", "external"]},
                    "description": "Repository types to include"
                },
                "exclude_temporary": {
                    "type": "boolean",
                    "default": False,
                    "description": "Exclude temporary repositories"
                },
                "cross_repository": {
                    "type": "boolean",
                    "default": True,
                    "description": "Allow searching across multiple repositories"
                },
                "group_by_repository": {
                    "type": "boolean",
                    "default": False,
                    "description": "Group results by repository"
                }
            }
        },
        
        # Agent context
        "agent_context": {
            "type": "object",
            "properties": {
                "agent_type": {
                    "enum": [at.value for at in AgentType],
                    "default": "generic",
                    "description": "Type of AI agent making the request"
                },
                "session_mode": {
                    "enum": ["interactive", "autonomous", "approval_required", "one_shot"],
                    "default": "interactive",
                    "description": "How the agent operates"
                },
                "workflow_type": {
                    "enum": ["exploration", "implementation", "debugging", "refactoring", "review"],
                    "default": "exploration", 
                    "description": "Current workflow context"
                },
                "supports_structured": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether agent supports structured outputs"
                }
            }
        },
        
        # Task metadata
        "task_metadata": {
            "type": "object",
            "properties": {
                "user_intent": {
                    "type": "string",
                    "description": "What the user is trying to accomplish"
                },
                "current_task": {
                    "type": "string",
                    "description": "Specific task being performed"
                },
                "priority": {
                    "enum": ["low", "medium", "high", "critical"],
                    "default": "medium",
                    "description": "Task priority level"
                },
                "complexity": {
                    "enum": ["simple", "moderate", "complex", "expert"],
                    "default": "moderate",
                    "description": "Expected task complexity"
                },
                "risk_level": {
                    "enum": ["safe", "moderate", "high"],
                    "default": "safe",
                    "description": "Risk level of proposed changes"
                },
                "affects_tests": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether changes might affect tests"
                },
                "affects_api": {
                    "type": "boolean", 
                    "default": False,
                    "description": "Whether changes might affect public API"
                },
                "backwards_compatible": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether changes should be backwards compatible"
                }
            }
        }
    },
    "required": ["request_type", "target"]
}

# Legacy request schema for backward compatibility
LEGACY_REQUEST_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search query (legacy format)"
        },
        "file_pattern": {
            "type": "string", 
            "default": "*",
            "description": "File pattern to search within"
        },
        "search_type": {
            "enum": ["literal", "regex", "semantic", "fuzzy"],
            "default": "literal",
            "description": "Type of search to perform"
        },
        "case_sensitive": {
            "type": "boolean",
            "default": False,
            "description": "Whether search should be case sensitive"
        },
        "max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": 1000,
            "default": 100,
            "description": "Maximum number of results"
        },
        "context_lines": {
            "type": "integer",
            "minimum": 0,
            "maximum": 10,
            "default": 2,
            "description": "Lines of context around matches"
        }
    },
    "required": ["query"]
}

# Combined schema supporting both formats
ENHANCED_SEARCH_SCHEMA = {
    "oneOf": [
        {
            "title": "Structured Request (Recommended)",
            "description": "Structured request format for optimal results",
            **STRUCTURED_REQUEST_SCHEMA
        },
        {
            "title": "Legacy Request (Supported)",
            "description": "Legacy format for backward compatibility", 
            **LEGACY_REQUEST_SCHEMA
        }
    ]
}

# Agent-specific template defaults
AGENT_TEMPLATES = {
    AgentType.CLAUDE_CODE: {
        "context_spec": {"depth": "comprehensive", "include_related": ["dependencies", "tests", "docs"]},
        "search_optimization": {"semantic_weight": 0.8, "recency_preference": "stable"},
        "response_format": {"format": "detailed", "include_metadata": True}
    },
    AgentType.CODEX_CLI: {
        "context_spec": {"depth": "edit_ready", "include_related": ["dependencies"]},
        "search_optimization": {"semantic_weight": 0.3, "recency_preference": "any"},
        "response_format": {"format": "diff_ready", "include_line_numbers": True}
    },
    AgentType.JULES: {
        "context_spec": {"depth": "comprehensive", "include_related": ["dependencies", "tests"]},
        "search_optimization": {"semantic_weight": 0.6, "recency_preference": "recent"},
        "response_format": {"format": "detailed", "token_budget": 4000}
    },
    AgentType.CURSOR: {
        "context_spec": {"depth": "standard", "include_related": ["dependencies"]},
        "search_optimization": {"semantic_weight": 0.7, "recency_preference": "any"},
        "response_format": {"format": "summary", "max_results": 5}
    },
    AgentType.COPILOT: {
        "context_spec": {"depth": "standard", "include_related": ["examples"]},
        "search_optimization": {"semantic_weight": 0.6, "recency_preference": "any"},
        "response_format": {"format": "code_only", "context_lines": 3}
    }
}

# Request type specific optimizations
REQUEST_TYPE_TEMPLATES = {
    RequestType.SYMBOL_SEARCH: {
        "search_optimization": {"semantic_weight": 0.8, "keywords": ["function", "class", "method"]},
        "response_format": {"format": "summary", "max_results": 20}
    },
    RequestType.EDIT_PREPARATION: {
        "context_spec": {"depth": "edit_ready", "include_related": ["dependencies", "tests"]},
        "search_optimization": {"semantic_weight": 0.3, "exact_symbols": True},
        "response_format": {"format": "diff_ready", "context_lines": 10}
    },
    RequestType.EXPLAIN_CODE: {
        "context_spec": {"depth": "comprehensive", "include_related": ["dependencies", "docs", "examples"]},
        "search_optimization": {"semantic_weight": 0.9},
        "response_format": {"format": "detailed", "token_budget": 3000}
    },
    RequestType.GOTO_DEFINITION: {
        "context_spec": {"depth": "minimal", "scope": "symbol"},
        "search_optimization": {"semantic_weight": 0.1, "exact_symbols": True},
        "response_format": {"format": "navigation", "max_results": 1}
    },
    RequestType.FIND_REFERENCES: {
        "context_spec": {"depth": "standard", "scope": "project"},
        "search_optimization": {"semantic_weight": 0.2, "exact_symbols": True},
        "response_format": {"format": "navigation", "max_results": 50}
    }
}


def get_agent_template(agent_type: AgentType) -> Dict[str, Any]:
    """Get default template for specific agent type."""
    return AGENT_TEMPLATES.get(agent_type, AGENT_TEMPLATES[AgentType.GENERIC])


def get_request_type_template(request_type: RequestType) -> Dict[str, Any]:
    """Get optimization template for specific request type."""
    return REQUEST_TYPE_TEMPLATES.get(request_type, {})


def merge_templates(*templates: Dict[str, Any]) -> Dict[str, Any]:
    """Merge multiple template dictionaries with deep merging."""
    result = {}
    for template in templates:
        for key, value in template.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = {**result[key], **value}
            else:
                result[key] = value
    return result