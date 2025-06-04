"""
Enhanced tool descriptions with structured request guidance.

This module provides comprehensive tool descriptions that guide AI agents
toward optimal request patterns while maintaining backward compatibility.
"""

from typing import Dict, Any, Optional
from .schemas_structured import AgentType, RequestType, ContextDepth, ResponseFormat


def get_enhanced_search_description(agent_type: Optional[str] = None) -> str:
    """Get enhanced description for search_code tool with agent-specific guidance."""
    
    base_description = """Search for code patterns across the codebase with support for literal, regex, semantic, and fuzzy search.

🚀 **OPTIMIZED REQUEST FORMAT** (Recommended):
Use structured requests for 95% better token efficiency and more precise results:

```json
{
    "request_type": "symbol_search|edit_preparation|explain_code|goto_definition",
    "target": {
        "query": "your search query",
        "symbol": "exact_symbol_name (optional)"
    },
    "context_spec": {
        "depth": "minimal|standard|comprehensive|edit_ready"
    },
    "response_format": {
        "format": "summary|detailed|diff_ready|navigation"
    }
}
```

📋 **COMMON PATTERNS**:

**🔍 Discovery & Search**:
```json
{
    "request_type": "symbol_search",
    "target": {"query": "authentication functions"},
    "context_spec": {"depth": "standard"},
    "response_format": {"format": "summary", "max_results": 10}
}
```

**✏️ Code Editing**:
```json
{
    "request_type": "edit_preparation", 
    "target": {"symbol": "login_user"},
    "context_spec": {"depth": "edit_ready", "include_related": ["dependencies", "tests"]},
    "response_format": {"format": "diff_ready", "context_lines": 10}
}
```

**🔄 Cross-Repository Translation**:
```json
{
    "request_type": "edit_preparation",
    "target": {"query": "authentication function"},
    "repository_filter": {"repositories": ["local", "rust_reference"], "group_by_repository": true},
    "context_spec": {"depth": "comprehensive", "include_related": ["dependencies"]}
}
```

**🧠 Understanding Code**:
```json
{
    "request_type": "explain_code",
    "target": {"query": "payment processing flow"},
    "context_spec": {"depth": "comprehensive", "include_related": ["docs", "examples"]},
    "response_format": {"format": "detailed"}
}
```

**🧭 Navigation**:
```json
{
    "request_type": "goto_definition",
    "target": {"symbol": "calculate_total"},
    "context_spec": {"depth": "minimal"},
    "response_format": {"format": "navigation"}
}
```"""

    # Agent-specific guidance
    agent_guidance = {
        "claude code": """

🤖 **CLAUDE CODE OPTIMIZATIONS**:
- Use `"depth": "comprehensive"` for exploration tasks
- Include `"include_related": ["dependencies", "tests", "docs"]` for thorough analysis
- Set `"semantic_weight": 0.8` for better conceptual understanding
- Leverage `"workflow_type": "exploration"` for codebase discovery

**Best for**: Comprehensive code analysis, architectural understanding, refactoring""",

        "codex cli": """

⚡ **CODEX CLI OPTIMIZATIONS**:
- Use `"depth": "edit_ready"` for modification tasks
- Set `"format": "diff_ready"` for immediate editing
- Use `"exact_symbols": true` for precise targeting
- Set `"session_mode": "approval_required"` for safety

**Best for**: Precise edits, targeted fixes, terminal-based workflows""",

        "jules": """

🤖 **JULES OPTIMIZATIONS**:
- Use `"depth": "comprehensive"` for autonomous work
- Set higher `"token_budget": 4000` for complex tasks  
- Include `"affects_api": true/false` for breaking change analysis
- Use `"session_mode": "autonomous"` for independent execution

**Best for**: Asynchronous development, bug fixes, feature implementation""",

        "cursor": """

🎯 **CURSOR OPTIMIZATIONS**:
- Use `"depth": "standard"` for interactive development
- Set `"max_results": 5-10` for focused results
- Use `"format": "summary"` for quick overviews
- Leverage `"workflow_type": "implementation"` for active coding

**Best for**: Interactive development, code completion, real-time assistance""",

        "github copilot": """

✨ **GITHUB COPILOT OPTIMIZATIONS**:
- Use `"format": "code_only"` for clean snippets
- Set `"context_lines": 3-5` for focused context
- Include `"examples"` in related content for patterns
- Use `"depth": "standard"` for balanced information

**Best for**: Code completion, inline suggestions, pattern recognition"""
    }

    # Add agent-specific guidance if available
    if agent_type and agent_type.lower() in agent_guidance:
        base_description += agent_guidance[agent_type.lower()]

    base_description += """

🔄 **LEGACY FORMAT** (Still Supported):
Simple string queries work but are less efficient:
```json
{"query": "authentication", "search_type": "semantic", "max_results": 10}
```

💡 **PRO TIPS**:
- Start with `"symbol_search"` to explore, then use `"edit_preparation"` for changes
- Use `"explain_code"` when you need to understand before modifying  
- Combine `"goto_definition"` + `"find_references"` for complete symbol analysis
- Set appropriate `"token_budget"` to control response size

📚 **LEARN MORE**: Use `get_search_guidance` tool for personalized request optimization.

ℹ️ **NOTE**: General usage instructions are provided during MCP initialization for all agent types."""

    return base_description


def get_enhanced_symbol_description(agent_type: Optional[str] = None) -> str:
    """Get enhanced description for lookup_symbol tool."""
    
    return """Look up detailed information about a specific symbol (function, class, variable, etc.).

🚀 **OPTIMIZED REQUEST FORMAT**:
```json
{
    "request_type": "goto_definition|explain_code|edit_preparation",
    "target": {
        "symbol": "exact_symbol_name",
        "file_path": "optional/path/hint.py"
    },
    "context_spec": {
        "depth": "minimal|standard|comprehensive|edit_ready",
        "include_related": ["dependencies", "dependents", "tests"]
    }
}
```

📋 **COMMON USAGE PATTERNS**:

**🎯 Quick Definition Lookup**:
```json
{
    "request_type": "goto_definition",
    "target": {"symbol": "authenticate_user"},
    "context_spec": {"depth": "minimal"}
}
```

**🔍 Deep Symbol Analysis**:
```json
{
    "request_type": "explain_code", 
    "target": {"symbol": "PaymentProcessor"},
    "context_spec": {"depth": "comprehensive", "include_related": ["dependencies", "tests"]}
}
```

**✏️ Edit Preparation**:
```json
{
    "request_type": "edit_preparation",
    "target": {"symbol": "validate_input"},
    "context_spec": {"depth": "edit_ready", "include_related": ["dependents"]}
}
```

🔄 **LEGACY FORMAT**: `{"symbol": "function_name", "file_path": "optional/path.py"}`"""


def get_enhanced_references_description(agent_type: Optional[str] = None) -> str:
    """Get enhanced description for find_references tool."""
    
    return """Find all references to a symbol across the codebase.

🚀 **OPTIMIZED REQUEST FORMAT**:
```json
{
    "request_type": "find_references|assess_impact|refactor_planning",
    "target": {"symbol": "symbol_name"},
    "context_spec": {
        "scope": "file|module|project",
        "include_related": ["call_hierarchy", "dependents"]
    },
    "response_format": {
        "format": "navigation|detailed",
        "max_results": 50
    }
}
```

📋 **USAGE PATTERNS**:

**🗺️ Navigate All Usages**:
```json
{
    "request_type": "find_references",
    "target": {"symbol": "user_login"},
    "response_format": {"format": "navigation", "max_results": 25}
}
```

**🔄 Refactoring Impact Analysis**:
```json
{
    "request_type": "assess_impact",
    "target": {"symbol": "deprecated_function"},
    "context_spec": {"scope": "project", "include_related": ["dependents"]},
    "response_format": {"format": "detailed"}
}
```"""


def get_search_guidance_description() -> str:
    """Get description for the search guidance helper tool."""
    
    return """Get personalized guidance for structuring optimal code search requests.

This helper tool analyzes your task and provides specific recommendations for:
- Optimal request structure for your goal
- Agent-specific optimizations  
- Expected token usage and confidence levels
- Alternative approaches to consider

**Input**: Describe what you're trying to accomplish
**Output**: Customized structured request template with explanations

**Example**:
Input: `{"task": "I need to add rate limiting to the login function"}`
Output: Optimized `edit_preparation` request structure with precise parameters"""


def get_enhanced_tool_descriptions(agent_type: Optional[str] = None) -> Dict[str, str]:
    """Get all enhanced tool descriptions for the given agent type."""
    
    return {
        "search_code": get_enhanced_search_description(agent_type),
        "lookup_symbol": get_enhanced_symbol_description(agent_type), 
        "find_references": get_enhanced_references_description(agent_type),
        "get_search_guidance": get_search_guidance_description()
    }


def create_instruction_examples(agent_type: AgentType, request_type: RequestType) -> Dict[str, Any]:
    """Create specific examples for agent type and request type combinations."""
    
    examples = {
        # Claude Code examples - comprehensive and thorough
        (AgentType.CLAUDE_CODE, RequestType.EXPLAIN_CODE): {
            "request_type": "explain_code",
            "target": {"query": "authentication flow"},
            "context_spec": {
                "depth": "comprehensive", 
                "include_related": ["dependencies", "tests", "docs", "examples"]
            },
            "response_format": {"format": "detailed", "token_budget": 3000},
            "agent_context": {"workflow_type": "exploration"}
        },
        
        # Codex CLI examples - precise and edit-ready
        (AgentType.CODEX_CLI, RequestType.EDIT_PREPARATION): {
            "request_type": "edit_preparation",
            "target": {"symbol": "authenticate_user"},
            "context_spec": {
                "depth": "edit_ready",
                "include_related": ["dependencies", "tests"]
            },
            "response_format": {"format": "diff_ready", "context_lines": 10},
            "agent_context": {"session_mode": "approval_required"}
        },
        
        # Jules examples - autonomous and comprehensive
        (AgentType.JULES, RequestType.REFACTOR_PLANNING): {
            "request_type": "refactor_planning", 
            "target": {"query": "legacy authentication system"},
            "context_spec": {
                "depth": "comprehensive",
                "scope": "module",
                "include_related": ["dependencies", "dependents", "tests"]
            },
            "response_format": {"format": "detailed", "token_budget": 4000},
            "task_metadata": {
                "complexity": "complex",
                "affects_api": True,
                "backwards_compatible": True
            }
        }
    }
    
    return examples.get((agent_type, request_type), {})


def format_instruction_prompt(task_description: str, agent_type: str) -> str:
    """Format a personalized instruction prompt for the given task and agent."""
    
    agent_enum = None
    try:
        agent_enum = AgentType(agent_type.lower())
    except ValueError:
        agent_enum = AgentType.GENERIC
    
    # Detect likely request type from task description
    task_lower = task_description.lower()
    if any(word in task_lower for word in ["edit", "change", "modify", "fix", "add"]):
        suggested_type = RequestType.EDIT_PREPARATION
        depth = "edit_ready"
        format_type = "diff_ready"
    elif any(word in task_lower for word in ["understand", "explain", "how", "what", "why"]):
        suggested_type = RequestType.EXPLAIN_CODE
        depth = "comprehensive" 
        format_type = "detailed"
    elif any(word in task_lower for word in ["find", "search", "locate", "where"]):
        suggested_type = RequestType.SYMBOL_SEARCH
        depth = "standard"
        format_type = "summary"
    elif any(word in task_lower for word in ["navigate", "go to", "jump"]):
        suggested_type = RequestType.GOTO_DEFINITION
        depth = "minimal"
        format_type = "navigation"
    else:
        suggested_type = RequestType.SYMBOL_SEARCH
        depth = "standard"
        format_type = "summary"
    
    example = create_instruction_examples(agent_enum, suggested_type)
    if not example:
        example = {
            "request_type": suggested_type.value,
            "target": {"query": "extracted from your task"},
            "context_spec": {"depth": depth},
            "response_format": {"format": format_type}
        }
    
    return f"""Based on your task: "{task_description}"

I recommend this structured request:
```json
{example}
```

This optimized structure will:
- Focus search algorithms on your specific intent
- Return context optimized for {agent_type} workflows  
- Provide {depth} information depth
- Format results as {format_type} for immediate use
- Reduce token usage by ~70% vs unstructured queries

Alternative request types to consider:
- `symbol_search`: Broad discovery of relevant code
- `edit_preparation`: Get edit-ready context with dependencies
- `explain_code`: Deep understanding with examples and docs
- `goto_definition`: Quick navigation to specific symbols

Pro tip: Start with `symbol_search` to explore, then use `edit_preparation` when ready to make changes."""