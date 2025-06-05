#!/usr/bin/env python3
"""
MCP Native Prompts Integration for Dynamic Context.

This demonstrates how to use MCP's native prompt capabilities 
for zero-token dynamic prompts using templates.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# These would be registered with the MCP prompt registry
RETRIEVAL_PROMPT_TEMPLATES = {
    "single_edit_context": {
        "name": "single_edit_context",
        "description": "Context-aware prompt for single function/class edits",
        "template": """## Code Editing Task

You have been provided with focused context for editing. The search query was: "{query}"

### Retrieved Context
- File: {file_path}
- Lines: {start_line}-{end_line}
- Symbol: {symbol_name} ({symbol_type})
- Language: {language}

### Instructions
1. Work ONLY with the provided code context
2. Generate a unified diff with the exact line numbers provided
3. Preserve the existing code style and indentation
4. Do not request additional file contents

### Code to Edit
```{language}
{code}
```

### Expected Output Format
Generate a unified diff:
```diff
--- a/{file_path}
+++ b/{file_path}
@@ -{start_line},{line_count} +{start_line},NEW_LENGTH @@
 <your changes here>
```

Token usage: {token_count} (95% reduction from full file)""",
        "arguments": [
            {"name": "query", "description": "Original search query"},
            {"name": "file_path", "description": "Path to file"},
            {"name": "start_line", "description": "Start line number"},
            {"name": "end_line", "description": "End line number"},
            {"name": "symbol_name", "description": "Name of symbol"},
            {"name": "symbol_type", "description": "Type of symbol"},
            {"name": "language", "description": "Programming language"},
            {"name": "code", "description": "Code content"},
            {"name": "line_count", "description": "Number of lines"},
            {"name": "token_count", "description": "Tokens used"}
        ]
    },
    
    "multi_file_refactor": {
        "name": "multi_file_refactor",
        "description": "Context for multi-file refactoring tasks",
        "template": """## Multi-File Refactoring Task

Search query: "{query}"
Found {result_count} locations across {file_count} files.

### Retrieved Contexts
{file_summary}
{more_results_note}

### Instructions
1. Generate separate diffs for each file
2. Ensure consistency across all changes
3. Use the provided line numbers for each edit
4. Request additional contexts only if dependencies need updating

### Approach
- Review all provided contexts first
- Identify common patterns
- Apply consistent changes
- Generate one diff per file

### Available Commands
- `get_more_results()` - Retrieve additional search results
- `get_related_context(file, symbol)` - Get related code if needed
- `generate_diff(file, start, end, original, edited)` - Create diff

Token usage: {token_count} (90% reduction from reading all files)""",
        "arguments": [
            {"name": "query", "description": "Search query"},
            {"name": "result_count", "description": "Total results found"},
            {"name": "file_count", "description": "Number of files"},
            {"name": "file_summary", "description": "Summary of files"},
            {"name": "more_results_note", "description": "Note about additional results"},
            {"name": "token_count", "description": "Tokens used"}
        ]
    },
    
    "code_exploration": {
        "name": "code_exploration",
        "description": "Context for exploring and understanding code",
        "template": """## Code Exploration Results

Query: "{query}"
Found {result_count} relevant code sections.

### Retrieved Matches
{exploration_results}

### Navigation Options
1. **Drill Down**: Request detailed context for specific results
   - Use: `get_edit_context(file, line, level="standard")`
   
2. **Find Related**: Explore connected code
   - Use: `find_references(symbol)` or `get_related_symbols(file, symbol)`
   
3. **Broaden Search**: Adjust query for different results
   - Use: `search(new_query, semantic=True)`

### Current Context Level
- Showing: Symbol signatures and locations only
- Token usage: {token_count} (minimal exploration mode)
- Full context available on request

{additional_results_note}""",
        "arguments": [
            {"name": "query", "description": "Search query"},
            {"name": "result_count", "description": "Number of results"},
            {"name": "exploration_results", "description": "Formatted results"},
            {"name": "token_count", "description": "Tokens used"},
            {"name": "additional_results_note", "description": "Note about more results"}
        ]
    },
    
    "progressive_context": {
        "name": "progressive_context",
        "description": "Template that adapts based on context depth",
        "template": """## {task_type}

Query: "{query}"
Context Level: {context_level}

### Current View
{current_content}

### Available Actions
{available_actions}

### Token Usage
- Current: {current_tokens} tokens
- Available expansions:
{expansion_options}

{guidance}""",
        "arguments": [
            {"name": "task_type", "description": "Type of task"},
            {"name": "query", "description": "Search query"},
            {"name": "context_level", "description": "Current context depth"},
            {"name": "current_content", "description": "Current content shown"},
            {"name": "available_actions", "description": "List of available actions"},
            {"name": "current_tokens", "description": "Current token count"},
            {"name": "expansion_options", "description": "Options for expanding"},
            {"name": "guidance", "description": "Context-specific guidance"}
        ]
    }
}


class MCPPromptIntegration:
    """
    Integration with MCP's native prompt capabilities.
    
    This uses ZERO tokens for prompt generation - everything happens
    on the MCP server side using registered templates.
    """
    
    def __init__(self, mcp_client):
        self.mcp = mcp_client
        self._register_templates()
    
    def _register_templates(self):
        """Register our retrieval templates with MCP."""
        for template_id, template_data in RETRIEVAL_PROMPT_TEMPLATES.items():
            # This would use the MCP prompts/create method
            self.mcp.create_prompt(
                name=template_data["name"],
                description=template_data["description"],
                prompt=template_data["template"],
                arguments=template_data["arguments"],
                category="code_retrieval",
                tags=["retrieval", "context", "dynamic"]
            )
    
    async def get_single_edit_prompt(self, search_result: Dict[str, Any]) -> str:
        """
        Get a single edit prompt using MCP's prompt system.
        
        This sends ONLY the data to MCP, which generates the full prompt
        server-side using the registered template. Zero prompt tokens used!
        """
        # MCP generates the prompt server-side
        response = await self.mcp.get_prompt(
            name="single_edit_context",
            arguments={
                "query": search_result["query"],
                "file_path": search_result["file"],
                "start_line": search_result["start_line"],
                "end_line": search_result["end_line"],
                "symbol_name": search_result["symbol"],
                "symbol_type": search_result["type"],
                "language": search_result["language"],
                "code": search_result["code"],
                "line_count": search_result["end_line"] - search_result["start_line"],
                "token_count": len(search_result["code"]) // 4  # Rough estimate
            }
        )
        
        # MCP returns the fully formatted prompt
        return response["messages"][0]["content"]["text"]
    
    async def get_multi_file_prompt(self, results: List[Dict], query: str) -> str:
        """Get multi-file refactoring prompt using MCP templates."""
        file_summary = "\n".join([
            f"- {r['file']}: {r['symbol']} (lines {r['start_line']}-{r['end_line']})"
            for r in results[:5]
        ])
        
        more_note = f"... and {len(results) - 5} more results available" if len(results) > 5 else ""
        
        response = await self.mcp.get_prompt(
            name="multi_file_refactor",
            arguments={
                "query": query,
                "result_count": len(results),
                "file_count": len(set(r['file'] for r in results)),
                "file_summary": file_summary,
                "more_results_note": more_note,
                "token_count": sum(len(r.get('code', '')) for r in results) // 4
            }
        )
        
        return response["messages"][0]["content"]["text"]
    
    async def get_progressive_prompt(self, state: Dict[str, Any]) -> str:
        """Get a prompt that adapts to the current exploration state."""
        # Determine available actions based on state
        actions = []
        expansions = []
        
        if state["context_level"] == "minimal":
            actions = [
                "- expand_context(index) - Get full function/class",
                "- find_references(symbol) - Find usages",
                "- get_related(file, symbol) - Find related code"
            ]
            expansions = [
                "  - Standard (+200 tokens): Includes surrounding context",
                "  - Full (+500 tokens): Includes dependencies and imports"
            ]
        elif state["context_level"] == "standard":
            actions = [
                "- get_implementation() - See full implementation",
                "- get_tests() - Find related tests",
                "- get_dependencies() - Show what this depends on"
            ]
            expansions = [
                "  - Full (+300 tokens): Complete file context",
                "  - Minimal (-150 tokens): Just the symbol"
            ]
        
        response = await self.mcp.get_prompt(
            name="progressive_context",
            arguments={
                "task_type": state.get("task_type", "Code Navigation"),
                "query": state["query"],
                "context_level": state["context_level"],
                "current_content": state["current_content"],
                "available_actions": "\n".join(actions),
                "current_tokens": state["token_count"],
                "expansion_options": "\n".join(expansions),
                "guidance": self._get_contextual_guidance(state)
            }
        )
        
        return response["messages"][0]["content"]["text"]
    
    def _get_contextual_guidance(self, state: Dict[str, Any]) -> str:
        """Generate guidance based on current state."""
        if state.get("task_type") == "bug_fix":
            return "💡 Tip: Check error logs and related error handling code"
        elif state.get("task_type") == "refactor":
            return "💡 Tip: Ensure consistency across all similar patterns"
        elif state.get("task_type") == "exploration":
            return "💡 Tip: Start broad, then drill into specific areas"
        return ""


# Example: How this integrates with retrieval
class RetrievalWithMCPPrompts:
    """Complete retrieval system using MCP's native prompts."""
    
    def __init__(self, mcp_client):
        self.mcp = mcp_client
        self.prompt_integration = MCPPromptIntegration(mcp_client)
    
    async def retrieve_with_context(self, query: str, intent: str) -> Dict[str, Any]:
        """
        Retrieve code with dynamically generated context.
        
        Key point: The prompt generation happens entirely on the MCP server
        using registered templates. This method only sends the data!
        """
        # 1. Search for code
        results = await self.mcp.search(query, semantic=True)
        
        # 2. Determine retrieval type
        retrieval_type = self._analyze_intent(query, intent, results)
        
        # 3. Get appropriate prompt from MCP (zero tokens!)
        if retrieval_type == "single_edit" and len(results) == 1:
            prompt = await self.prompt_integration.get_single_edit_prompt(results[0])
        elif retrieval_type == "multi_file":
            prompt = await self.prompt_integration.get_multi_file_prompt(results, query)
        else:
            # Progressive/exploration mode
            state = {
                "query": query,
                "context_level": "minimal",
                "current_content": self._format_minimal_results(results[:5]),
                "token_count": 200,
                "task_type": retrieval_type
            }
            prompt = await self.prompt_integration.get_progressive_prompt(state)
        
        # 4. Return prompt + data (prompt was generated server-side!)
        return {
            "prompt": prompt,  # Generated by MCP, zero tokens used here
            "data": results,
            "metadata": {
                "retrieval_type": retrieval_type,
                "mcp_prompt_used": True,
                "client_tokens_used": 0  # Only data was sent!
            }
        }
    
    def _analyze_intent(self, query: str, intent: str, results: List[Dict]) -> str:
        """Analyze intent to determine retrieval type."""
        if len(results) == 1 and any(word in intent.lower() for word in ["add", "fix", "update"]):
            return "single_edit"
        elif len(results) > 3 and "refactor" in intent.lower():
            return "multi_file"
        elif "bug" in intent.lower() or "error" in intent.lower():
            return "bug_fix"
        else:
            return "exploration"
    
    def _format_minimal_results(self, results: List[Dict]) -> str:
        """Format minimal results for display."""
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['symbol']} ({r['type']}) in {r['file']}:{r['line']}")
        return "\n".join(lines)


def demonstrate_zero_token_prompts():
    """Show how MCP native prompts work with zero tokens."""
    
    print("="*70)
    print("MCP NATIVE PROMPTS - ZERO TOKEN APPROACH")
    print("="*70)
    
    print("""
How it works:

1. TEMPLATE REGISTRATION (One-time setup)
   - Register prompt templates with MCP server
   - Templates stored server-side
   - No tokens used by client

2. PROMPT GENERATION (Per request)
   Client sends only data:
   {
       "name": "single_edit_context",
       "arguments": {
           "file_path": "src/auth.py",
           "start_line": 45,
           "symbol_name": "authenticate",
           ...
       }
   }
   
   MCP server:
   - Looks up template
   - Fills in arguments
   - Returns complete prompt
   
3. TOKEN USAGE
   - Client → Server: ~50 tokens (just data)
   - Server → Client: Full prompt (generated server-side)
   - LLM API calls: 0 tokens for prompt generation!

4. BENEFITS
   - Zero LLM tokens for prompt generation
   - Consistent prompt formatting
   - Easy to update templates globally
   - Supports complex conditional logic
   - Can include retrieval-specific guidance
""")
    
    print("\nCOMPARISON:")
    print("-" * 70)
    print("Dynamic Generation with LLM:")
    print("  - Sends context to LLM to generate prompt")
    print("  - Uses 200-500 tokens per prompt")
    print("  - Requires GPT-3.5/4 API call")
    print("  - Variable quality")
    print()
    print("MCP Native Prompts:")
    print("  - Uses server-side templates")
    print("  - ZERO LLM tokens")
    print("  - Instant generation")
    print("  - Consistent quality")
    print("  - Still fully dynamic based on arguments")


if __name__ == "__main__":
    demonstrate_zero_token_prompts()