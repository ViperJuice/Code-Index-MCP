#!/usr/bin/env python3
"""Demonstrate what context information is returned for coding agents."""

import json
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class SearchResult:
    """What the search returns."""
    file_path: str
    symbol_name: str
    symbol_type: str
    line_number: int
    score: float
    signature: str
    language: str

@dataclass 
class EditContext:
    """Enhanced context for coding agents."""
    # Location info
    file_path: str
    start_line: int
    end_line: int
    
    # Symbol info
    symbol_name: str
    symbol_type: str
    signature: str
    
    # Context
    code_snippet: str
    surrounding_context: str
    
    # Related info
    imports: List[str]
    related_symbols: List[Dict[str, Any]]
    
    # Edit guidance
    edit_instructions: str
    constraints: List[str]

def demonstrate_search_results():
    """Show what information is returned from searches."""
    
    print("="*70)
    print("SEARCH RESULT INFORMATION")
    print("="*70)
    
    # Example search results
    search_results = [
        SearchResult(
            file_path="/project/src/auth/user_service.py",
            symbol_name="authenticate_user",
            symbol_type="function",
            line_number=45,
            score=0.92,
            signature="def authenticate_user(username: str, password: str) -> Optional[User]:",
            language="python"
        ),
        SearchResult(
            file_path="/project/src/api/routes/users.js",
            symbol_name="createUser",
            symbol_type="function", 
            line_number=23,
            score=0.87,
            signature="async function createUser(req, res)",
            language="javascript"
        ),
        SearchResult(
            file_path="/project/src/main/java/com/app/service/UserValidator.java",
            symbol_name="validateEmail",
            symbol_type="method",
            line_number=67,
            score=0.85,
            signature="public boolean validateEmail(String email)",
            language="java"
        )
    ]
    
    print("\n1. Basic Search Results:")
    print("-" * 70)
    for i, result in enumerate(search_results, 1):
        print(f"\nResult {i}:")
        print(f"  File: {result.file_path}")
        print(f"  Symbol: {result.symbol_name} ({result.symbol_type})")
        print(f"  Line: {result.line_number}")
        print(f"  Score: {result.score:.2f}")
        print(f"  Signature: {result.signature}")

def demonstrate_enhanced_context():
    """Show enhanced context for agents."""
    
    print("\n\n" + "="*70)
    print("ENHANCED CONTEXT FOR AGENTS")
    print("="*70)
    
    # Example of enhanced context
    context = EditContext(
        # Precise location
        file_path="/project/src/auth/user_service.py",
        start_line=45,
        end_line=58,
        
        # Symbol details
        symbol_name="authenticate_user",
        symbol_type="function",
        signature="def authenticate_user(username: str, password: str) -> Optional[User]:",
        
        # Actual code
        code_snippet="""def authenticate_user(username: str, password: str) -> Optional[User]:
    \"\"\"Authenticate a user with username and password.\"\"\"
    # TODO: Add validation
    user = get_user_by_username(username)
    
    if user and check_password(password, user.password_hash):
        # Update last login
        user.last_login = datetime.now()
        db.session.commit()
        return user
    
    return None""",
        
        # Surrounding context (what comes before/after)
        surrounding_context="""# Previous function
def get_user_by_username(username: str) -> Optional[User]:
    return User.query.filter_by(username=username).first()

[TARGET FUNCTION HERE]

# Next function  
def generate_auth_token(user: User) -> str:
    payload = {
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }""",
        
        # Dependencies
        imports=[
            "from typing import Optional",
            "from datetime import datetime, timedelta",
            "from app.models import User, db",
            "from app.utils.security import check_password"
        ],
        
        # Related code in the same file
        related_symbols=[
            {"name": "get_user_by_username", "type": "function", "line": 32},
            {"name": "generate_auth_token", "type": "function", "line": 61},
            {"name": "check_password", "type": "import", "line": 5},
            {"name": "test_authenticate_user", "type": "test", "line": 145}
        ],
        
        # Instructions for the agent
        edit_instructions="Add input validation for username and password parameters. Ensure username is not empty and password meets security requirements.",
        
        # Constraints/guidelines
        constraints=[
            "Maintain the existing function signature",
            "Return None for invalid inputs (don't raise exceptions)",
            "Add appropriate logging for security events",
            "Follow the existing code style"
        ]
    )
    
    print("\n2. Enhanced Context Structure:")
    print("-" * 70)
    
    # Show as dictionary for clarity
    context_dict = asdict(context)
    print(json.dumps(context_dict, indent=2, default=str))

def demonstrate_agent_workflow():
    """Show how an agent would use this information."""
    
    print("\n\n" + "="*70)
    print("AGENT WORKFLOW EXAMPLE")
    print("="*70)
    
    print("""
3. How a Coding Agent Uses This Information:

STEP 1: Query Processing
------------------------
User: "Add validation to the user authentication function"
↓
Semantic Search: "user authentication validation function"
↓
Returns: Top 3 relevant functions with scores

STEP 2: Context Retrieval
-------------------------
For each result:
- Load the file
- Find exact function boundaries
- Extract surrounding context
- Identify dependencies
- Find related code

STEP 3: Edit Planning
---------------------
Agent receives:
- Exact file path and line numbers
- Complete function code
- Import statements needed
- Related functions that might be affected
- Specific edit instructions

STEP 4: Code Generation
-----------------------
Agent can now:
- Make targeted edits to the specific function
- Ensure imports are present
- Maintain consistency with related code
- Follow the existing patterns

STEP 5: Validation
------------------
- Check that edits are within the specified line range
- Verify no breaking changes to signature
- Ensure related tests still pass
""")

def demonstrate_api_format():
    """Show the actual API response format."""
    
    print("\n" + "="*70)
    print("API RESPONSE FORMAT")
    print("="*70)
    
    api_response = {
        "query": "add validation to authenticate user",
        "results": [
            {
                "file": "/project/src/auth/user_service.py",
                "symbol": "authenticate_user",
                "type": "function",
                "line": 45,
                "score": 0.92,
                "language": "python",
                "context": {
                    "start_line": 45,
                    "end_line": 58,
                    "code": "def authenticate_user(username: str, password: str) -> Optional[User]:\n    # ... function body ...",
                    "imports": ["from typing import Optional", "from app.models import User"],
                    "related": [
                        {"symbol": "get_user_by_username", "line": 32},
                        {"symbol": "test_authenticate_user", "line": 145}
                    ]
                },
                "edit_suggestion": {
                    "instruction": "Add input validation",
                    "constraints": ["Maintain signature", "Return None for invalid input"]
                }
            }
        ]
    }
    
    print("\n4. Actual API Response:")
    print("-" * 70)
    print(json.dumps(api_response, indent=2))

def main():
    """Run all demonstrations."""
    demonstrate_search_results()
    demonstrate_enhanced_context()
    demonstrate_agent_workflow()
    demonstrate_api_format()
    
    print("\n" + "="*70)
    print("KEY BENEFITS FOR AGENTS")
    print("="*70)
    print("""
1. PRECISE LOCATION
   - Exact file path
   - Start and end line numbers
   - No guessing where to edit

2. COMPLETE CONTEXT
   - Full function/class code
   - Surrounding code
   - Import statements
   - Related symbols

3. LANGUAGE AWARENESS
   - Language-specific parsing
   - Proper symbol boundaries
   - Syntax-aware context

4. EDIT GUIDANCE
   - Clear instructions
   - Constraints to follow
   - Related code to check

5. MINIMAL TOKEN USAGE
   - Only relevant code returned
   - No need to parse entire files
   - Focused on the edit target
""")

if __name__ == "__main__":
    main()