#!/usr/bin/env python3
"""
Demonstration of structured outputs for MCP code retrieval.

This example shows how structured inputs and outputs can improve
agent-MCP interactions with better context, metadata, and workflow support.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path


class SearchIntent(str, Enum):
    """Intent types for code search operations."""
    CODE_REVIEW = "code_review"
    REFACTORING = "refactoring"
    DEBUGGING = "debugging"
    OPTIMIZATION = "optimization"
    TESTING = "testing"
    DOCUMENTATION = "documentation"


class AgentType(str, Enum):
    """Types of agents that may interact with MCP."""
    CODING_ASSISTANT = "coding_assistant"
    REFACTORING_AGENT = "refactoring_agent" 
    TESTING_AGENT = "testing_agent"
    SECURITY_AGENT = "security_agent"
    DOCUMENTATION_AGENT = "documentation_agent"


@dataclass
class SearchContext:
    """Context information for search operations."""
    intent: SearchIntent
    agent_type: AgentType
    workflow_step: str
    desired_output_format: str = "detailed_context"


@dataclass
class RetrievalOptions:
    """Options for how to retrieve and format results."""
    include_related_symbols: bool = True
    include_dependencies: bool = True
    include_usage_examples: bool = False
    context_window_lines: int = 5
    max_results: int = 10
    include_edit_guidance: bool = True


@dataclass
class SymbolInfo:
    """Structured information about a code symbol."""
    name: str
    type: str  # function, class, method, variable, etc.
    signature: Optional[str] = None
    docstring: Optional[str] = None
    line_range: Optional[Dict[str, int]] = None
    scope: Optional[str] = None
    visibility: str = "public"  # public, private, protected


@dataclass 
class ContextInfo:
    """Context information for a code location."""
    file_path: str
    language: str
    full_content: str
    imports: List[str]
    related_symbols: List[Dict[str, Any]]
    file_metrics: Dict[str, Any]


@dataclass
class EditGuidance:
    """Guidance for agents on how to edit the code."""
    edit_type: str  # modification, addition, refactoring, deletion
    complexity_level: str  # simple, moderate, complex
    dependencies: List[str]
    test_requirements: bool
    breaking_change_risk: str  # low, medium, high
    recommended_approach: str


@dataclass
class QualityMetrics:
    """Quality and relevance metrics for search results."""
    relevance_score: float  # 0.0 to 1.0
    confidence_score: float  # 0.0 to 1.0
    complexity_score: int  # 1 to 10
    maintainability_score: float  # 0.0 to 1.0


@dataclass
class WorkflowSuggestion:
    """Suggested next step in a workflow."""
    step_type: str
    tool_name: str
    parameters: Dict[str, Any]
    description: str
    priority: int = 5  # 1-10, 10 being highest


@dataclass
class StructuredSearchResult:
    """Complete structured search result."""
    symbol_info: SymbolInfo
    context_info: ContextInfo
    edit_guidance: EditGuidance
    quality_metrics: QualityMetrics
    
    
@dataclass
class StructuredSearchResponse:
    """Complete response for a structured search."""
    results: List[StructuredSearchResult]
    metadata: Dict[str, Any]
    workflow_suggestions: List[WorkflowSuggestion]
    search_context: SearchContext


class StructuredOutputDemo:
    """Demonstrates structured outputs for MCP code retrieval."""
    
    def __init__(self):
        self.sample_code_files = {
            "auth.py": '''import hashlib
import jwt
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

class UserAuthenticator:
    """Handles user authentication and token management."""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.token_expiry = timedelta(hours=24)
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user with username and password.
        
        Args:
            username: User's username
            password: User's password (plain text)
            
        Returns:
            User data if authentication successful, None otherwise
        """
        # TODO: Add proper password hashing validation
        user = self._get_user(username)
        if user and user.get('password') == password:  # Security issue!
            return self._generate_token(user)
        return None
    
    def _get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Retrieve user from database."""
        # Placeholder implementation
        return {"id": 1, "username": username, "password": "plaintext"}
    
    def _generate_token(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Generate JWT token for authenticated user."""
        payload = {
            'user_id': user['id'],
            'username': user['username'],
            'exp': datetime.utcnow() + self.token_expiry
        }
        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        return {"token": token, "user": user}
''',
            "api_handler.py": '''from flask import Flask, request, jsonify
from auth import UserAuthenticator

app = Flask(__name__)
auth = UserAuthenticator("secret_key")

@app.route('/api/login', methods=['POST'])
def login():
    """Handle user login requests."""
    data = request.get_json()
    
    # TODO: Add input validation
    username = data.get('username')
    password = data.get('password')
    
    result = auth.authenticate_user(username, password)
    
    if result:
        return jsonify({"success": True, "data": result})
    else:
        return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route('/api/protected', methods=['GET'])
def protected_route():
    """Example of a protected route requiring authentication."""
    token = request.headers.get('Authorization')
    
    if not token:
        return jsonify({"error": "No token provided"}), 401
    
    # TODO: Implement token validation
    return jsonify({"message": "Access granted", "data": "protected_data"})
'''
        }
    
    async def demonstrate_traditional_search(self) -> Dict[str, Any]:
        """Show traditional, unstructured search results."""
        print("=== TRADITIONAL SEARCH RESULTS ===")
        
        # Simulate traditional search response
        traditional_result = {
            "results": [
                {
                    "file": "auth.py",
                    "line": 15,
                    "snippet": "def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:",
                    "score": 0.85
                },
                {
                    "file": "api_handler.py", 
                    "line": 8,
                    "snippet": "def login():",
                    "score": 0.72
                }
            ],
            "total_found": 2
        }
        
        print("Query: 'authentication function'")
        print(json.dumps(traditional_result, indent=2))
        print("\nLimitations:")
        print("- No context about what agent should do with results")
        print("- No guidance on complexity or risk")
        print("- No related symbols or dependencies")
        print("- Agent must figure out edit approach independently")
        
        return traditional_result
    
    async def demonstrate_structured_search(self) -> StructuredSearchResponse:
        """Show enhanced structured search results."""
        print("\n=== STRUCTURED SEARCH RESULTS ===")
        
        # Create search context
        search_context = SearchContext(
            intent=SearchIntent.CODE_REVIEW,
            agent_type=AgentType.SECURITY_AGENT,
            workflow_step="security_analysis"
        )
        
        # Create structured results
        auth_result = StructuredSearchResult(
            symbol_info=SymbolInfo(
                name="authenticate_user",
                type="method",
                signature="authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]",
                docstring="Authenticate a user with username and password.",
                line_range={"start": 15, "end": 27},
                scope="UserAuthenticator",
                visibility="public"
            ),
            context_info=ContextInfo(
                file_path="auth.py",
                language="python",
                full_content=self.sample_code_files["auth.py"],
                imports=["hashlib", "jwt", "typing.Optional", "typing.Dict", "typing.Any"],
                related_symbols=[
                    {"name": "_get_user", "type": "method", "line": 29},
                    {"name": "_generate_token", "type": "method", "line": 34}
                ],
                file_metrics={
                    "lines_of_code": 45,
                    "complexity_score": 6,
                    "test_coverage": 0.3
                }
            ),
            edit_guidance=EditGuidance(
                edit_type="modification",
                complexity_level="moderate", 
                dependencies=["password hashing library", "input validation"],
                test_requirements=True,
                breaking_change_risk="low",
                recommended_approach="Add password hashing, input validation, and rate limiting"
            ),
            quality_metrics=QualityMetrics(
                relevance_score=0.95,
                confidence_score=0.88,
                complexity_score=6,
                maintainability_score=0.65
            )
        )
        
        login_result = StructuredSearchResult(
            symbol_info=SymbolInfo(
                name="login",
                type="function",
                signature="login() -> Response",
                docstring="Handle user login requests.",
                line_range={"start": 8, "end": 19},
                scope="global",
                visibility="public"
            ),
            context_info=ContextInfo(
                file_path="api_handler.py",
                language="python", 
                full_content=self.sample_code_files["api_handler.py"],
                imports=["flask.Flask", "flask.request", "flask.jsonify", "auth.UserAuthenticator"],
                related_symbols=[
                    {"name": "protected_route", "type": "function", "line": 21}
                ],
                file_metrics={
                    "lines_of_code": 30,
                    "complexity_score": 4,
                    "test_coverage": 0.1
                }
            ),
            edit_guidance=EditGuidance(
                edit_type="modification",
                complexity_level="simple",
                dependencies=["input validation library", "error handling"],
                test_requirements=True,
                breaking_change_risk="low",
                recommended_approach="Add input validation, improve error handling, add logging"
            ),
            quality_metrics=QualityMetrics(
                relevance_score=0.78,
                confidence_score=0.82,
                complexity_score=4,
                maintainability_score=0.70
            )
        )
        
        # Create workflow suggestions
        workflow_suggestions = [
            WorkflowSuggestion(
                step_type="security_analysis",
                tool_name="analyze_security_vulnerabilities", 
                parameters={
                    "symbols": ["authenticate_user", "login"],
                    "focus": ["password_handling", "input_validation"]
                },
                description="Analyze password handling and input validation security",
                priority=9
            ),
            WorkflowSuggestion(
                step_type="dependency_check",
                tool_name="analyze_dependencies",
                parameters={
                    "files": ["auth.py", "api_handler.py"],
                    "include_security_libs": True
                },
                description="Check for security-related dependencies and suggest improvements",
                priority=7
            ),
            WorkflowSuggestion(
                step_type="generate_tests",
                tool_name="generate_security_tests",
                parameters={
                    "functions": ["authenticate_user", "login"],
                    "test_types": ["security", "edge_cases"]
                },
                description="Generate security-focused test cases",
                priority=6
            )
        ]
        
        # Create complete response
        response = StructuredSearchResponse(
            results=[auth_result, login_result],
            metadata={
                "query": "authentication function",
                "search_time_ms": 45,
                "total_results": 2,
                "result_confidence": 0.87,
                "search_strategy": "semantic_with_security_focus"
            },
            workflow_suggestions=workflow_suggestions,
            search_context=search_context
        )
        
        # Display structured result
        print("Query: 'authentication function'")
        print("Context: Security review by security agent")
        print("\nStructured Results:")
        print(json.dumps(asdict(response), indent=2, default=str))
        
        return response
    
    async def demonstrate_prompt_generation(self, search_response: StructuredSearchResponse) -> Dict[str, Any]:
        """Show structured prompt generation based on search results."""
        print("\n=== STRUCTURED PROMPT GENERATION ===")
        
        # Generate structured prompt based on search results
        prompt_request = {
            "method": "prompts/get",
            "params": {
                "name": "security_code_review",
                "arguments": {
                    "search_results": search_response,
                    "review_focus": {
                        "primary_concerns": ["password_security", "input_validation", "authentication_bypass"],
                        "severity_threshold": "medium",
                        "include_remediation": True
                    },
                    "output_format": {
                        "structure": "markdown",
                        "include_code_blocks": True,
                        "include_diff_suggestions": True,
                        "max_length": 2000
                    },
                    "agent_context": {
                        "agent_type": "security_agent",
                        "expertise_level": "expert",
                        "time_constraint": "normal"
                    }
                }
            }
        }
        
        # Simulate structured prompt response
        prompt_response = {
            "result": {
                "prompt_content": """# Security Code Review: Authentication System

## Overview
Review the following authentication-related code for security vulnerabilities, focusing on password handling and input validation.

## Code Context
You are reviewing functions from a user authentication system that shows several security concerns.

## Review Requirements
1. **Password Security**: Check for proper password hashing and storage
2. **Input Validation**: Verify all user inputs are properly validated  
3. **Authentication Bypass**: Look for ways to bypass authentication

## Code to Review

### Function 1: authenticate_user (auth.py, lines 15-27)
```python
def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
    user = self._get_user(username)
    if user and user.get('password') == password:  # ⚠️ Security Issue
        return self._generate_token(user)
    return None
```

**Context**: Method in UserAuthenticator class, called by API endpoints

### Function 2: login (api_handler.py, lines 8-19)  
```python
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')  # ⚠️ No validation
    password = data.get('password')  # ⚠️ No validation
    result = auth.authenticate_user(username, password)
    # ... rest of function
```

**Context**: Flask API endpoint, directly accepts user input

## Expected Output Format
Provide your findings in this structure:
```json
{
  "critical_issues": [{"issue": "...", "location": "...", "remediation": "..."}],
  "high_priority_fixes": [{"description": "...", "code_suggestion": "..."}],
  "recommended_improvements": ["..."],
  "security_score": "1-10 rating"
}
```

## Related Files to Consider
- Authentication utilities in auth.py
- API endpoints in api_handler.py
- Consider impact on protected_route function""",
                
                "metadata": {
                    "generated_at": "2025-01-01T12:00:00Z",
                    "template_version": "2.1.0",
                    "estimated_tokens": 520,
                    "complexity_level": "intermediate",
                    "review_scope": "security_focused"
                },
                
                "structured_sections": {
                    "instructions": "Review authentication code for security vulnerabilities",
                    "context": "User authentication system with potential security issues",
                    "requirements": [
                        "Check password hashing and storage",
                        "Verify input validation",
                        "Look for authentication bypass vulnerabilities"
                    ],
                    "code_blocks": [
                        {
                            "function": "authenticate_user",
                            "file": "auth.py",
                            "lines": "15-27",
                            "security_concerns": ["plaintext password comparison"]
                        },
                        {
                            "function": "login", 
                            "file": "api_handler.py",
                            "lines": "8-19",
                            "security_concerns": ["no input validation", "no rate limiting"]
                        }
                    ]
                },
                
                "validation_schema": {
                    "type": "object",
                    "properties": {
                        "critical_issues": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "issue": {"type": "string"},
                                    "location": {"type": "string"},
                                    "remediation": {"type": "string"}
                                },
                                "required": ["issue", "location", "remediation"]
                            }
                        },
                        "security_score": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10
                        }
                    },
                    "required": ["critical_issues", "security_score"]
                },
                
                "follow_up_prompts": [
                    {
                        "name": "implement_password_hashing",
                        "condition": "if password security issues found",
                        "parameters": {
                            "focus": "password_security",
                            "include_examples": True
                        },
                        "description": "Generate specific code for implementing secure password hashing"
                    },
                    {
                        "name": "add_input_validation", 
                        "condition": "if validation issues found",
                        "parameters": {
                            "validation_types": ["type_checking", "sanitization", "length_limits"],
                            "framework": "flask"
                        },
                        "description": "Create comprehensive input validation for the API endpoints"
                    }
                ]
            }
        }
        
        print("Structured Prompt Request:")
        print(json.dumps(prompt_request, indent=2, default=str))
        print("\nStructured Prompt Response:")
        print(json.dumps(prompt_response, indent=2, default=str))
        
        return prompt_response
    
    async def demonstrate_workflow_chaining(self):
        """Show how structured outputs enable workflow chaining."""
        print("\n=== WORKFLOW CHAINING DEMONSTRATION ===")
        
        workflow_chain = [
            {
                "step": 1,
                "action": "structured_search",
                "input": {
                    "query": "authentication function",
                    "context": {
                        "intent": "security_review",
                        "agent_type": "security_agent"
                    }
                },
                "output_schema": "StructuredSearchResponse",
                "description": "Find authentication-related code with security context"
            },
            {
                "step": 2,
                "action": "analyze_dependencies",
                "input": {
                    "symbols": "${step1.results[*].symbol_info.name}",
                    "focus": "security_libraries"
                },
                "output_schema": "DependencyAnalysisResponse", 
                "description": "Analyze security-related dependencies"
            },
            {
                "step": 3,
                "action": "generate_security_prompt",
                "input": {
                    "search_results": "${step1.output}",
                    "dependency_analysis": "${step2.output}",
                    "prompt_type": "comprehensive_security_review"
                },
                "output_schema": "StructuredPromptResponse",
                "description": "Generate comprehensive security review prompt"
            },
            {
                "step": 4,
                "action": "execute_security_review",
                "input": {
                    "prompt": "${step3.prompt_content}",
                    "validation_schema": "${step3.validation_schema}"
                },
                "output_schema": "SecurityReviewResult",
                "description": "Execute security review with structured output validation"
            }
        ]
        
        print("Multi-step workflow enabled by structured outputs:")
        for step in workflow_chain:
            print(f"\nStep {step['step']}: {step['action']}")
            print(f"Description: {step['description']}")
            print(f"Input: {json.dumps(step['input'], indent=2)}")
            print(f"Expected Output Schema: {step['output_schema']}")
            
        print("\nBenefits of structured workflow:")
        print("✓ Each step provides typed, validated data to the next")
        print("✓ Workflow can branch based on structured conditions")
        print("✓ Error handling can be context-aware")
        print("✓ Results can be cached and reused with structured keys")
        print("✓ Agent can make intelligent decisions about next steps")

    async def run_demo(self):
        """Run the complete structured outputs demonstration."""
        print("STRUCTURED OUTPUTS FOR MCP CODE RETRIEVAL")
        print("=" * 60)
        
        # 1. Show traditional vs structured search
        await self.demonstrate_traditional_search()
        structured_results = await self.demonstrate_structured_search()
        
        # 2. Show structured prompt generation
        await self.demonstrate_prompt_generation(structured_results)
        
        # 3. Show workflow chaining capabilities
        await self.demonstrate_workflow_chaining()
        
        print("\n" + "=" * 60)
        print("SUMMARY OF IMPROVEMENTS")
        print("=" * 60)
        
        improvements = [
            "Rich contextual metadata for informed agent decisions",
            "Edit guidance reduces agent uncertainty and errors", 
            "Quality metrics enable result ranking and filtering",
            "Workflow suggestions enable intelligent multi-step operations",
            "Structured schemas enable validation and error handling",
            "Agent-specific formatting optimizes for different use cases",
            "Follow-up prompts create seamless workflow transitions"
        ]
        
        for i, improvement in enumerate(improvements, 1):
            print(f"{i}. {improvement}")


async def main():
    """Run the structured outputs demonstration."""
    demo = StructuredOutputDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())