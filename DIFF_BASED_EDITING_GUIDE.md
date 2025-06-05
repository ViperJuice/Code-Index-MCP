# Diff-Based Editing with Code Index MCP

## Overview

Yes, agents can generate diffs without reading entire files! The Code Index MCP provides sufficient context for agents to create precise, applicable diffs that can be directly applied to codebases.

## How It Works

### 1. Context Retrieval
The agent receives targeted context from the Code Index:
```json
{
  "file": "src/auth/user_service.py",
  "location": {
    "start_line": 45,
    "end_line": 52
  },
  "original_code": "def authenticate_user(username: str, password: str) -> Optional[User]:\n    # Complete function code...",
  "language": "python",
  "indentation": "    ",
  "imports": ["from typing import Optional", "from app.models import User"]
}
```

### 2. Agent Generates Diff
The agent creates a standard unified diff:
```diff
--- a/src/auth/user_service.py
+++ b/src/auth/user_service.py
@@ -45,8 +45,19 @@ def authenticate_user(username: str, password: str) -> Optional[User]:
+    # Validate inputs
+    if not username or not username.strip():
+        logger.warning("Authentication attempted with empty username")
+        return None
+    
     # Get user from database
     user = get_user_by_username(username)
     
     if user and check_password(password, user.password_hash):
+        logger.info(f"User {username} authenticated successfully")
         return user
     
+    logger.warning(f"Authentication failed for user: {username}")
     return None
```

### 3. Direct Application
The diff can be applied without reading the full file:
- Using `patch` command: `patch < changes.diff`
- Programmatically: Read only affected lines, replace, write back
- Through git: `git apply changes.diff`

## Key Components for Diff Generation

### Essential Context Elements

1. **Exact Line Numbers**
   - `start_line`: Where the symbol begins
   - `end_line`: Where it ends
   - Critical for accurate diff generation

2. **Complete Original Code**
   - The full function/class being edited
   - Preserves formatting and style
   - Enables accurate line-by-line comparison

3. **Language and Formatting**
   - Programming language for syntax
   - Indentation style (spaces/tabs)
   - Line ending preferences

4. **Surrounding Context** (Optional but helpful)
   - Few lines before/after
   - Helps with context in diff
   - Not required for generation

## API Design for Diff-Based Editing

### Request Format
```python
{
    "action": "edit_code",
    "search_query": "authenticate user function",
    "edit_instructions": "Add input validation",
    "options": {
        "output_format": "unified_diff",
        "include_context": 3,  # Lines of context in diff
        "preserve_style": true
    }
}
```

### Response Format
```python
{
    "status": "success",
    "edits": [
        {
            "file": "src/auth/user_service.py",
            "diff": {
                "format": "unified",
                "content": "--- a/src/auth/user_service.py\n+++ b/...",
                "stats": {
                    "insertions": 11,
                    "deletions": 0,
                    "files_changed": 1
                }
            },
            "summary": "Added input validation to authenticate_user function"
        }
    ]
}
```

## Implementation Example

```python
class DiffBasedEditor:
    """Generate and apply diffs without full file access."""
    
    def edit_function(self, search_query: str, instructions: str):
        # 1. Search for target code
        results = self.code_index.search(search_query)
        
        # 2. Get focused context
        context = self.code_index.get_edit_context(
            file=results[0].file,
            line=results[0].line,
            include_full_symbol=True
        )
        
        # 3. Generate edited version
        edited_code = self.agent.edit_code(
            original=context.code,
            instructions=instructions,
            constraints=context.constraints
        )
        
        # 4. Create diff
        diff = self.create_unified_diff(
            file_path=context.file,
            start_line=context.start_line,
            original=context.code,
            edited=edited_code
        )
        
        return diff
    
    def apply_diff(self, diff: str):
        """Apply diff using standard tools."""
        # Option 1: Save and use patch
        with open("changes.diff", "w") as f:
            f.write(diff)
        subprocess.run(["patch", "-p1"], input=diff, text=True)
        
        # Option 2: Parse and apply programmatically
        # This allows validation before application
```

## Advantages of Diff-Based Approach

### 1. **Efficiency**
- No need to load entire files into memory
- Minimal data transfer between services
- Fast application of changes

### 2. **Safety**
- Changes are reviewable before application
- Clear visualization of modifications
- Easy rollback if needed

### 3. **Compatibility**
- Standard diff format works with existing tools
- Git-compatible for version control
- IDE support for diff viewing

### 4. **Scalability**
- Can edit multiple files in parallel
- Handles large files efficiently
- Reduces API token usage

### 5. **Auditability**
- Clear record of what changed
- Line-by-line attribution
- Integration with code review tools

## Best Practices

### 1. Validate Context Boundaries
```python
def validate_edit_context(context):
    """Ensure we have complete symbol boundaries."""
    # Check that we have the entire function/class
    if context.language == "python":
        # Ensure we have all decorators
        # Check indentation is consistent
        # Verify we have the complete block
    elif context.language == "javascript":
        # Ensure balanced braces
        # Check for complete function
```

### 2. Preserve Code Style
```python
def preserve_formatting(original, edited):
    """Maintain original formatting preferences."""
    # Detect indentation style
    indent = detect_indentation(original)
    
    # Apply to edited code
    edited = apply_indentation(edited, indent)
    
    # Preserve line endings
    line_ending = detect_line_ending(original)
    edited = normalize_line_endings(edited, line_ending)
    
    return edited
```

### 3. Handle Edge Cases
```python
def handle_diff_conflicts(diff_patches):
    """Handle overlapping edits."""
    # Sort by file and line number
    # Detect overlaps
    # Merge or sequence as appropriate
    # Generate combined diff
```

## Complete Workflow Example

```python
# 1. User request
"Add error handling to all API endpoints"

# 2. Search for API endpoints
results = code_index.search("API endpoint route handler function")

# 3. For each result, generate targeted edit
diffs = []
for result in results[:5]:  # Top 5 matches
    context = code_index.get_edit_context(result)
    
    # Agent generates diff without seeing full file
    diff = agent.create_diff(
        context=context,
        instructions="Add try-catch with proper error responses"
    )
    
    diffs.append(diff)

# 4. Review diffs
for diff in diffs:
    print(f"Changes to {diff.file}:")
    print(diff.unified_diff)
    
# 5. Apply approved diffs
for diff in approved_diffs:
    apply_diff_to_file(diff)

# 6. Run tests on changed files
affected_files = [d.file for d in diffs]
run_tests(affected_files)
```

## Conclusion

The Code Index MCP enables efficient diff-based editing by providing:
- Precise location information (file + line numbers)
- Complete symbol context (full function/class code)
- Language-aware boundaries
- Formatting preservation

This allows agents to generate applicable diffs without ever reading entire files, making the system scalable, efficient, and token-optimal for large codebases.