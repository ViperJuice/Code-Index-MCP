#!/usr/bin/env python3
"""Dynamic prompt system for context-aware LLM instructions."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class RetrievalType(Enum):
    """Types of retrieval operations."""
    SINGLE_EDIT = "single_edit"
    MULTI_FILE_REFACTOR = "multi_file_refactor"
    CODE_EXPLORATION = "code_exploration"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    BUG_FIX = "bug_fix"
    FEATURE_ADDITION = "feature_addition"
    CODE_REVIEW = "code_review"

@dataclass
class RetrievalContext:
    """Context about the current retrieval."""
    query: str
    retrieval_type: RetrievalType
    results_count: int
    total_tokens: int
    has_more_results: bool
    language: Optional[str] = None
    complexity: str = "simple"  # simple, moderate, complex

class DynamicPromptGenerator:
    """Generate context-specific prompts for LLM based on retrieval type."""
    
    def __init__(self):
        self.base_instructions = {
            "token_awareness": "You have been provided with focused context. Token usage has been optimized.",
            "diff_generation": "Generate unified diffs with exact line numbers provided.",
            "no_file_reading": "Do not request full file contents - work with the provided context."
        }
    
    def generate_prompt(self, retrieval_context: RetrievalContext, 
                       retrieved_data: List[Dict[str, Any]]) -> str:
        """Generate a dynamic prompt based on retrieval context."""
        
        # Select appropriate prompt template
        if retrieval_context.retrieval_type == RetrievalType.SINGLE_EDIT:
            return self._single_edit_prompt(retrieval_context, retrieved_data)
        elif retrieval_context.retrieval_type == RetrievalType.MULTI_FILE_REFACTOR:
            return self._multi_file_prompt(retrieval_context, retrieved_data)
        elif retrieval_context.retrieval_type == RetrievalType.CODE_EXPLORATION:
            return self._exploration_prompt(retrieval_context, retrieved_data)
        elif retrieval_context.retrieval_type == RetrievalType.BUG_FIX:
            return self._bug_fix_prompt(retrieval_context, retrieved_data)
        elif retrieval_context.retrieval_type == RetrievalType.FEATURE_ADDITION:
            return self._feature_addition_prompt(retrieval_context, retrieved_data)
        else:
            return self._generic_prompt(retrieval_context, retrieved_data)
    
    def _single_edit_prompt(self, context: RetrievalContext, data: List[Dict]) -> str:
        """Prompt for single function/class edits."""
        return f"""## Code Editing Task

You have been provided with a focused context for editing. The search query was: "{context.query}"

### Retrieved Context
- File: {data[0]['file']}
- Lines: {data[0]['start_line']}-{data[0]['end_line']}
- Symbol: {data[0]['symbol']} ({data[0]['type']})
- Language: {data[0]['language']}

### Instructions
1. Work ONLY with the provided code context
2. Generate a unified diff with the exact line numbers provided
3. Preserve the existing code style and indentation
4. Do not request additional file contents

### Code to Edit
```{data[0]['language']}
{data[0]['code']}
```

### Expected Output Format
Generate a unified diff:
```diff
--- a/{data[0]['file']}
+++ b/{data[0]['file']}
@@ -{data[0]['start_line']},{data[0]['end_line'] - data[0]['start_line']} +{data[0]['start_line']},NEW_LENGTH @@
 <your changes here>
```

Token usage: {context.total_tokens} (95% reduction from full file)
"""

    def _multi_file_prompt(self, context: RetrievalContext, data: List[Dict]) -> str:
        """Prompt for multi-file refactoring."""
        files_summary = "\n".join([
            f"- {d['file']}: {d['symbol']} (lines {d['start_line']}-{d['end_line']})"
            for d in data[:5]
        ])
        
        return f"""## Multi-File Refactoring Task

Search query: "{context.query}"
Found {context.results_count} locations across {len(set(d['file'] for d in data))} files.

### Retrieved Contexts
{files_summary}
{f"... and {context.results_count - 5} more results available" if context.results_count > 5 else ""}

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

Token usage: {context.total_tokens} (90% reduction from reading all files)
"""

    def _exploration_prompt(self, context: RetrievalContext, data: List[Dict]) -> str:
        """Prompt for code exploration/understanding."""
        return f"""## Code Exploration Results

Query: "{context.query}"
Found {context.results_count} relevant code sections.

### Retrieved Matches
{self._format_exploration_results(data[:10])}

### Navigation Options
1. **Drill Down**: Request detailed context for specific results
   - Use: `get_edit_context(file, line, level="standard")`
   
2. **Find Related**: Explore connected code
   - Use: `find_references(symbol)` or `get_related_symbols(file, symbol)`
   
3. **Broaden Search**: Adjust query for different results
   - Use: `search(new_query, semantic=True)`

### Current Context Level
- Showing: Symbol signatures and locations only
- Token usage: {context.total_tokens} (minimal exploration mode)
- Full context available on request

{f"Note: {context.results_count - len(data)} additional results available" if context.has_more_results else ""}
"""

    def _bug_fix_prompt(self, context: RetrievalContext, data: List[Dict]) -> str:
        """Prompt for bug fixing."""
        return f"""## Bug Fix Task

Bug description: "{context.query}"

### Potentially Affected Code
{self._format_bug_fix_contexts(data)}

### Debugging Approach
1. Analyze the provided error context
2. Check related symbols for side effects
3. Generate minimal fix with tests

### Available Context
- Error location and surrounding code provided
- Related functions that call this code: {self._count_references(data)}
- Test files: {self._find_test_files(data)}

### Instructions
- Focus on the root cause, not symptoms
- Ensure fix doesn't break existing functionality
- Include edge case handling
- Generate diff with precise line numbers

Token usage: {context.total_tokens} (focused on error context only)
"""

    def _feature_addition_prompt(self, context: RetrievalContext, data: List[Dict]) -> str:
        """Prompt for adding new features."""
        return f"""## Feature Addition Task

Feature request: "{context.query}"

### Integration Points
{self._format_integration_points(data)}

### Implementation Guidelines
1. Follow existing patterns in the codebase
2. Add to existing files when possible
3. Maintain consistency with current architecture

### Provided Context
- Similar existing implementations
- Available utilities and helpers
- Current code style examples

### Next Steps
1. Review provided examples
2. Plan implementation approach
3. Request specific integration points if needed
4. Generate additions as diffs

Use `get_edit_context()` for any specific code you need to modify.

Token usage: {context.total_tokens} (showing patterns, not entire codebase)
"""

    def _generic_prompt(self, context: RetrievalContext, data: List[Dict]) -> str:
        """Generic prompt for other retrieval types."""
        return f"""## Code Context Retrieved

Query: "{context.query}"
Results: {context.results_count} matches found

### Retrieved Data
{self._format_generic_results(data[:5])}

### Available Actions
- Get detailed context: `get_edit_context(file, line)`
- Find usages: `find_references(symbol)`
- Search related: `search(refined_query)`

Token usage: {context.total_tokens}
"""

    # Helper methods
    def _format_exploration_results(self, data: List[Dict]) -> str:
        """Format results for exploration."""
        lines = []
        for i, d in enumerate(data, 1):
            lines.append(f"{i}. **{d['symbol']}** ({d['type']}) in `{d['file']}`")
            lines.append(f"   Line {d['line']}: `{d.get('signature', '')[:80]}...`")
        return "\n".join(lines)
    
    def _format_bug_fix_contexts(self, data: List[Dict]) -> str:
        """Format contexts for bug fixing."""
        primary = data[0] if data else None
        if not primary:
            return "No error context found"
        
        return f"""
**Error Location**: {primary['file']}:{primary['line']}
**Function**: {primary['symbol']}
**Type**: {primary['type']}

```{primary.get('language', 'python')}
{primary.get('code', '')}
```

**Related Code**:
{self._list_related_code(data[1:])}
"""

    def _list_related_code(self, data: List[Dict]) -> str:
        """List related code sections."""
        if not data:
            return "None found"
        
        lines = []
        for d in data[:3]:
            lines.append(f"- {d['symbol']} in {d['file']}:{d['line']}")
        return "\n".join(lines)
    
    def _count_references(self, data: List[Dict]) -> int:
        """Count references in the data."""
        return sum(d.get('reference_count', 0) for d in data)
    
    def _find_test_files(self, data: List[Dict]) -> List[str]:
        """Find test files in the data."""
        test_files = []
        for d in data:
            if 'test' in d['file'].lower():
                test_files.append(d['file'])
        return test_files[:3]
    
    def _format_integration_points(self, data: List[Dict]) -> str:
        """Format integration points for feature addition."""
        lines = []
        for d in data[:5]:
            lines.append(f"- **{d['symbol']}** - {d.get('description', 'Similar pattern')}")
            lines.append(f"  Location: {d['file']}:{d['line']}")
        return "\n".join(lines)
    
    def _format_generic_results(self, data: List[Dict]) -> str:
        """Generic result formatting."""
        lines = []
        for d in data:
            lines.append(f"- {d['symbol']} ({d['type']}) at {d['file']}:{d['line']}")
        return "\n".join(lines)


# Example usage
def demonstrate_dynamic_prompts():
    """Show how dynamic prompts adapt to different scenarios."""
    
    generator = DynamicPromptGenerator()
    
    # Example 1: Single edit
    print("="*70)
    print("EXAMPLE 1: Single Function Edit")
    print("="*70)
    
    single_edit_context = RetrievalContext(
        query="add validation to authenticate_user",
        retrieval_type=RetrievalType.SINGLE_EDIT,
        results_count=1,
        total_tokens=150,
        has_more_results=False,
        language="python"
    )
    
    single_edit_data = [{
        "file": "src/auth/user_service.py",
        "symbol": "authenticate_user",
        "type": "function",
        "line": 45,
        "start_line": 45,
        "end_line": 58,
        "language": "python",
        "code": "def authenticate_user(username: str, password: str) -> Optional[User]:\n    # ... function code ..."
    }]
    
    prompt1 = generator.generate_prompt(single_edit_context, single_edit_data)
    print(prompt1)
    
    # Example 2: Multi-file refactoring
    print("\n" + "="*70)
    print("EXAMPLE 2: Multi-File Refactoring")
    print("="*70)
    
    refactor_context = RetrievalContext(
        query="replace deprecated API calls",
        retrieval_type=RetrievalType.MULTI_FILE_REFACTOR,
        results_count=15,
        total_tokens=800,
        has_more_results=True
    )
    
    refactor_data = [
        {"file": "src/api/v1/users.py", "symbol": "get_user", "type": "function", "start_line": 23, "end_line": 35},
        {"file": "src/api/v1/posts.py", "symbol": "create_post", "type": "function", "start_line": 45, "end_line": 67},
        {"file": "src/services/auth.py", "symbol": "validate_token", "type": "function", "start_line": 12, "end_line": 25},
    ]
    
    prompt2 = generator.generate_prompt(refactor_context, refactor_data)
    print(prompt2[:500] + "...")  # Truncated for display

if __name__ == "__main__":
    demonstrate_dynamic_prompts()