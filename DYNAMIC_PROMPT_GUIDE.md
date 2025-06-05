# Dynamic Prompt System for Code Retrieval

## Why Dynamic Prompts Are Better

### Static CLAUDE.md Limitations
- Same instructions for all scenarios
- Can't adapt to retrieval type
- May provide irrelevant guidance
- Wastes tokens on unnecessary instructions

### Dynamic Prompt Advantages
- **Context-aware instructions** - Different guidance for edits vs exploration
- **Token optimization** - Only include relevant instructions
- **Task-specific guidance** - Bug fixes get debugging tips, refactoring gets consistency reminders
- **Progressive disclosure** - Show available commands based on current state

## Implementation Architecture

```python
class CodeRetrievalMCP:
    def retrieve_with_context(self, query: str, intent: str):
        # 1. Analyze the query to determine retrieval type
        retrieval_type = self.analyze_intent(query, intent)
        
        # 2. Perform the search/retrieval
        results = self.search(query, type=retrieval_type)
        
        # 3. Generate context-specific prompt
        prompt = self.generate_dynamic_prompt(
            retrieval_type=retrieval_type,
            results=results,
            query=query
        )
        
        # 4. Return both data and instructions
        return {
            "prompt": prompt,
            "data": results,
            "metadata": {
                "tokens_used": len(prompt) + len(results),
                "retrieval_type": retrieval_type,
                "available_actions": self.get_available_actions(retrieval_type)
            }
        }
```

## Retrieval Type Examples

### 1. Single Edit
```python
# User: "Add error handling to the login function"
response = {
    "prompt": """
    You have a single function to edit. 
    - Generate a diff using lines 45-58
    - Add try-catch blocks
    - Preserve function signature
    - Don't request more context
    """,
    "data": {
        "file": "auth.py",
        "lines": [45, 58],
        "code": "def login(username, password):..."
    }
}
```

### 2. Multi-File Refactoring
```python
# User: "Update all database calls to use new connection pool"
response = {
    "prompt": """
    Multiple files need consistent updates.
    - 15 locations found across 8 files
    - Generate separate diffs per file
    - Ensure all use pool.get_connection()
    - Request batches of 5 at a time
    """,
    "data": [
        {"file": "user_service.py", "line": 23},
        {"file": "post_service.py", "line": 45},
        # ... first batch of 5
    ]
}
```

### 3. Code Exploration
```python
# User: "How is authentication implemented?"
response = {
    "prompt": """
    Exploration mode - showing high-level overview.
    - 8 authentication-related components found
    - Use drill_down(index) for details
    - Use find_flow() to trace auth flow
    - Current view: signatures only (50 tokens)
    """,
    "data": [
        {"symbol": "authenticate", "type": "function", "file": "auth.py"},
        {"symbol": "JWTValidator", "type": "class", "file": "jwt.py"},
        # ... overview data
    ]
}
```

### 4. Bug Investigation
```python
# User: "Users report login fails after 5 minutes"
response = {
    "prompt": """
    Bug investigation mode.
    - Found timeout-related code
    - Check TOKEN_EXPIRY constant
    - Review session refresh logic
    - Use trace_references() to find all timeout checks
    
    Hypothesis: Token expiry mismatch between frontend/backend
    """,
    "data": {
        "primary_suspect": {"file": "jwt.py", "line": 15, "code": "TOKEN_EXPIRY = 300"},
        "related": [...]
    }
}
```

## Dynamic Instructions Based on State

### Initial Search
```python
prompt = """
Found 23 results for your query.
Showing top 5 with minimal context (200 tokens).

Available actions:
- get_more_results(5) - See next batch
- expand_context(0) - Get full context for result 0
- refine_search("more specific query") - Narrow results
"""
```

### After Expanding Context
```python
prompt = """
Expanded context for authenticate_user function.
Now showing: full function + imports + related (500 tokens).

Available actions:
- find_usages() - See where this is called
- get_tests() - Find related tests
- generate_diff() - Start editing
- minimize_context() - Return to summary view
"""
```

### During Multi-File Edit
```python
prompt = """
Editing file 3 of 8.
Previous edits: 2 files, 45 lines changed.

Consistency check:
- All previous edits used 'pool.get_conn()'
- Current file uses 'db.connect()'
- Maintain consistent naming

Next: Auto-load file 4 after this diff
"""
```

## Benefits Over Static Instructions

| Aspect | Static CLAUDE.md | Dynamic Prompts |
|--------|-----------------|-----------------|
| Token Usage | Same for all tasks | Optimized per task |
| Relevance | Generic instructions | Task-specific guidance |
| Learning | Fixed knowledge | Learns from patterns |
| Flexibility | One-size-fits-all | Adapts to complexity |
| User Experience | May confuse with irrelevant options | Shows only relevant actions |

## Implementation Tips

### 1. Retrieval Type Detection
```python
def detect_retrieval_type(query: str, context: dict) -> RetrievalType:
    patterns = {
        RetrievalType.SINGLE_EDIT: ["add", "fix", "update", "change"],
        RetrievalType.MULTI_FILE: ["all", "refactor", "replace everywhere"],
        RetrievalType.EXPLORATION: ["how", "where", "what", "explore"],
        RetrievalType.BUG_FIX: ["error", "bug", "fails", "broken"],
    }
    # Smart detection logic
```

### 2. Progressive Prompt Enhancement
```python
class PromptState:
    def __init__(self):
        self.shown_tips = set()
        self.user_expertise = "unknown"
        self.task_complexity = "simple"
    
    def enhance_prompt(self, base_prompt: str) -> str:
        # Add tips user hasn't seen
        # Adjust based on expertise
        # Include complexity warnings
```

### 3. Token-Aware Prompt Generation
```python
def generate_prompt(data, max_tokens=500):
    essential = generate_essential_instructions(data)
    
    remaining_tokens = max_tokens - len(essential)
    
    # Add optional elements if space allows
    if remaining_tokens > 100:
        essential += generate_helpful_tips(data)
    
    if remaining_tokens > 200:
        essential += generate_examples(data)
    
    return essential
```

## Conclusion

Dynamic prompts transform the code retrieval experience by:
1. **Providing exactly what's needed** for each specific task
2. **Saving tokens** by excluding irrelevant instructions
3. **Improving accuracy** with context-specific guidance
4. **Enabling progressive workflows** that adapt as users explore

This approach makes the MCP integration more intelligent, efficient, and user-friendly than static instructions could ever be.