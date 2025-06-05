#!/usr/bin/env python3
"""Demonstrate how agents can generate diffs without reading entire files."""

import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import difflib

@dataclass
class EditContext:
    """Context provided to the agent."""
    file_path: str
    start_line: int
    end_line: int
    original_code: str
    language: str
    indentation: str  # Important for maintaining formatting
    
@dataclass
class DiffPatch:
    """A diff that can be applied without reading the full file."""
    file_path: str
    start_line: int
    end_line: int
    original_lines: List[str]
    new_lines: List[str]
    unified_diff: str

class DiffGenerator:
    """Generate diffs from edit contexts."""
    
    def create_targeted_diff(self, context: EditContext, edited_code: str) -> DiffPatch:
        """Create a diff that can be applied to a specific line range."""
        
        # Split into lines
        original_lines = context.original_code.splitlines(keepends=True)
        new_lines = edited_code.splitlines(keepends=True)
        
        # Ensure proper line endings
        if original_lines and not original_lines[-1].endswith('\n'):
            original_lines[-1] += '\n'
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines[-1] += '\n'
        
        # Generate unified diff
        diff = difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"a/{context.file_path}",
            tofile=f"b/{context.file_path}",
            lineterm='',
            n=3  # Context lines
        )
        
        # Adjust line numbers for the file position
        adjusted_diff = self._adjust_line_numbers(
            list(diff), 
            context.start_line
        )
        
        return DiffPatch(
            file_path=context.file_path,
            start_line=context.start_line,
            end_line=context.end_line,
            original_lines=original_lines,
            new_lines=new_lines,
            unified_diff='\n'.join(adjusted_diff)
        )
    
    def _adjust_line_numbers(self, diff_lines: List[str], start_line: int) -> List[str]:
        """Adjust diff line numbers to match file position."""
        adjusted = []
        
        for line in diff_lines:
            if line.startswith('@@'):
                # Parse the line range: @@ -1,7 +1,9 @@
                parts = line.split()
                if len(parts) >= 3:
                    # Adjust the line numbers
                    old_range = parts[1]  # e.g., "-1,7"
                    new_range = parts[2]  # e.g., "+1,9"
                    
                    old_start, old_count = self._parse_range(old_range)
                    new_start, new_count = self._parse_range(new_range)
                    
                    # Adjust to actual file position
                    old_start_adj = old_start + start_line - 1
                    new_start_adj = new_start + start_line - 1
                    
                    adjusted_line = f"@@ -{old_start_adj},{old_count} +{new_start_adj},{new_count} @@"
                    if len(parts) > 3:
                        adjusted_line += " " + " ".join(parts[3:])
                    adjusted.append(adjusted_line)
                else:
                    adjusted.append(line)
            else:
                adjusted.append(line)
        
        return adjusted
    
    def _parse_range(self, range_str: str) -> Tuple[int, int]:
        """Parse range like '-1,7' into (1, 7)."""
        range_str = range_str.lstrip('+-')
        if ',' in range_str:
            start, count = range_str.split(',')
            return int(start), int(count)
        else:
            return int(range_str), 1

def demonstrate_diff_generation():
    """Show how agents can generate diffs without full file access."""
    
    print("="*70)
    print("DIFF GENERATION WITHOUT FULL FILE ACCESS")
    print("="*70)
    
    # Example 1: Python function edit
    context1 = EditContext(
        file_path="src/auth/user_service.py",
        start_line=45,
        end_line=52,
        original_code="""def authenticate_user(username: str, password: str) -> Optional[User]:
    # Get user from database
    user = get_user_by_username(username)
    
    if user and check_password(password, user.password_hash):
        return user
    
    return None""",
        language="python",
        indentation="    "
    )
    
    # Agent's edited version (with validation added)
    edited_code1 = """def authenticate_user(username: str, password: str) -> Optional[User]:
    # Validate inputs
    if not username or not username.strip():
        logger.warning("Authentication attempted with empty username")
        return None
    
    if not password or len(password) < 8:
        logger.warning(f"Authentication attempted with invalid password for user: {username}")
        return None
    
    # Get user from database
    user = get_user_by_username(username)
    
    if user and check_password(password, user.password_hash):
        logger.info(f"User {username} authenticated successfully")
        return user
    
    logger.warning(f"Authentication failed for user: {username}")
    return None"""
    
    generator = DiffGenerator()
    diff1 = generator.create_targeted_diff(context1, edited_code1)
    
    print("\n1. Python Function Edit")
    print("-" * 70)
    print(f"File: {diff1.file_path}")
    print(f"Lines: {diff1.start_line}-{diff1.end_line} → {diff1.start_line}-{diff1.start_line + len(diff1.new_lines) - 1}")
    print("\nUnified Diff:")
    print(diff1.unified_diff)
    
    # Example 2: JavaScript function edit
    context2 = EditContext(
        file_path="src/api/routes/users.js",
        start_line=23,
        end_line=28,
        original_code="""async function createUser(req, res) {
  const userData = req.body;
  
  const user = await User.create(userData);
  
  res.json({ success: true, user });
}""",
        language="javascript",
        indentation="  "
    )
    
    edited_code2 = """async function createUser(req, res) {
  try {
    const userData = req.body;
    
    // Validate required fields
    if (!userData.email || !userData.username) {
      return res.status(400).json({ 
        error: 'Email and username are required' 
      });
    }
    
    const user = await User.create(userData);
    
    res.status(201).json({ success: true, user });
  } catch (error) {
    console.error('Error creating user:', error);
    res.status(500).json({ 
      error: 'Failed to create user' 
    });
  }
}"""
    
    diff2 = generator.create_targeted_diff(context2, edited_code2)
    
    print("\n\n2. JavaScript Function Edit")
    print("-" * 70)
    print(f"File: {diff2.file_path}")
    print(f"Lines: {diff2.start_line}-{diff2.end_line} → {diff2.start_line}-{diff2.start_line + len(diff2.new_lines) - 1}")
    print("\nUnified Diff:")
    print(diff2.unified_diff)

def demonstrate_patch_application():
    """Show how to apply a diff without reading the full file."""
    
    print("\n\n" + "="*70)
    print("APPLYING DIFFS WITHOUT FULL FILE ACCESS")
    print("="*70)
    
    print("""
The generated diffs can be applied in several ways:

1. DIRECT LINE REPLACEMENT
   - Read only the affected lines
   - Replace with new content
   - Write back only those lines

2. USING PATCH COMMAND
   - Save diff to file
   - Apply with: patch < changes.diff
   - Handles context automatically

3. PROGRAMMATIC APPLICATION
   """)
    
    # Show programmatic application
    code = '''
def apply_targeted_edit(file_path: str, diff_patch: DiffPatch):
    """Apply a diff to specific lines without reading entire file."""
    
    # Read the file in chunks
    with open(file_path, 'r') as f:
        lines = []
        current_line = 1
        
        # Read lines before the edit
        while current_line < diff_patch.start_line:
            lines.append(f.readline())
            current_line += 1
        
        # Skip the lines being replaced
        for _ in range(diff_patch.end_line - diff_patch.start_line + 1):
            f.readline()
            
        # Add the new lines
        lines.extend(diff_patch.new_lines)
        
        # Read the rest of the file
        lines.extend(f.readlines())
    
    # Write back
    with open(file_path, 'w') as f:
        f.writelines(lines)
'''
    
    print(code)

def demonstrate_api_format():
    """Show the API format for diff generation."""
    
    print("\n" + "="*70)
    print("API FORMAT FOR AGENT DIFF GENERATION")
    print("="*70)
    
    # Example API request
    api_request = {
        "action": "generate_edit",
        "context": {
            "file": "src/auth/user_service.py",
            "target": {
                "start_line": 45,
                "end_line": 52,
                "code": "def authenticate_user(username: str, password: str) -> Optional[User]:\n    # original code..."
            },
            "language": "python",
            "indentation": "    "
        },
        "instructions": "Add input validation for username and password",
        "constraints": [
            "Return None for invalid inputs",
            "Add appropriate logging",
            "Maintain function signature"
        ]
    }
    
    # Example API response
    api_response = {
        "status": "success",
        "diff": {
            "type": "unified",
            "file": "src/auth/user_service.py",
            "changes": {
                "lines_removed": 8,
                "lines_added": 19,
                "start_line": 45,
                "end_line": 63
            },
            "patch": "--- a/src/auth/user_service.py\n+++ b/src/auth/user_service.py\n@@ -45,8 +45,19 @@\n def authenticate_user(username: str, password: str) -> Optional[User]:\n+    # Validate inputs\n+    if not username or not username.strip():\n+        logger.warning(\"Authentication attempted with empty username\")\n+        return None\n..."
        },
        "summary": "Added input validation with 2 validation checks and 3 log statements"
    }
    
    print("\n3. API Request Format:")
    print("-" * 70)
    print(json.dumps(api_request, indent=2))
    
    print("\n4. API Response Format:")
    print("-" * 70)
    print(json.dumps(api_response, indent=2))

def demonstrate_benefits():
    """Show the benefits of diff-based editing."""
    
    print("\n\n" + "="*70)
    print("BENEFITS OF DIFF-BASED EDITING")
    print("="*70)
    
    print("""
1. EFFICIENCY
   - No need to read entire files
   - Minimal data transfer
   - Fast application of changes

2. SAFETY
   - Changes are isolated to specific lines
   - Easy to review before applying
   - Can validate line number matches

3. VERSION CONTROL FRIENDLY
   - Standard diff format
   - Compatible with git
   - Clear change history

4. TOKEN OPTIMIZATION
   - Agent only sees relevant code
   - No wasted tokens on unchanged code
   - Can handle large files efficiently

5. CONCURRENT EDITING
   - Multiple edits to different parts
   - No conflicts if sections don't overlap
   - Parallel processing possible
""")

def main():
    """Run all demonstrations."""
    demonstrate_diff_generation()
    demonstrate_patch_application()
    demonstrate_api_format()
    demonstrate_benefits()
    
    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print("""
With proper context from the Code Index MCP, agents can:

1. Generate precise diffs for specific functions/classes
2. Include exact line numbers for targeted application
3. Maintain code formatting and style
4. Apply changes without full file access
5. Provide clear, reviewable change sets

This enables efficient, accurate code editing at scale.
""")

if __name__ == "__main__":
    main()