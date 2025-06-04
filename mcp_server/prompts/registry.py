"""
Prompt registry for MCP.

Manages available prompt templates and handles prompt generation.
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PromptArgument:
    """Definition of a prompt argument."""
    name: str
    description: str
    required: bool = True
    type: str = "string"
    default: Optional[Any] = None


@dataclass
class PromptTemplate:
    """A prompt template with metadata."""
    name: str
    description: str
    prompt: Union[str, Callable[..., str]]
    arguments: List[PromptArgument] = field(default_factory=list)
    version: str = "1.0.0"
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class PromptRegistry:
    """Registry for managing MCP prompt templates."""
    
    def __init__(self):
        self._prompts: Dict[str, PromptTemplate] = {}
        self._categories: Dict[str, List[str]] = {}
        self._tags: Dict[str, List[str]] = {}
        self._template_cache: Dict[str, str] = {}
        self._load_built_in_prompts()
    
    def register_prompt(self, template: PromptTemplate) -> None:
        """Register a prompt template."""
        self._prompts[template.name] = template
        
        # Update category index
        if template.category not in self._categories:
            self._categories[template.category] = []
        if template.name not in self._categories[template.category]:
            self._categories[template.category].append(template.name)
        
        # Update tags index
        for tag in template.tags:
            if tag not in self._tags:
                self._tags[tag] = []
            if template.name not in self._tags[tag]:
                self._tags[tag].append(template.name)
        
        logger.info(f"Registered prompt template: {template.name}")
    
    def unregister_prompt(self, name: str) -> bool:
        """Unregister a prompt template."""
        if name not in self._prompts:
            return False
        
        template = self._prompts.pop(name)
        
        # Remove from category index
        if template.category in self._categories:
            if name in self._categories[template.category]:
                self._categories[template.category].remove(name)
            if not self._categories[template.category]:
                del self._categories[template.category]
        
        # Remove from tags index
        for tag in template.tags:
            if tag in self._tags and name in self._tags[tag]:
                self._tags[tag].remove(name)
                if not self._tags[tag]:
                    del self._tags[tag]
        
        # Clear cache entry
        if name in self._template_cache:
            del self._template_cache[name]
        
        logger.info(f"Unregistered prompt template: {name}")
        return True
    
    def get_prompt(self, name: str) -> Optional[PromptTemplate]:
        """Get a prompt template by name."""
        return self._prompts.get(name)
    
    def list_prompts(self, category: Optional[str] = None, tag: Optional[str] = None) -> List[str]:
        """List available prompts, optionally filtered by category or tag."""
        if category:
            return self._categories.get(category, [])
        elif tag:
            return self._tags.get(tag, [])
        else:
            return list(self._prompts.keys())
    
    def get_categories(self) -> List[str]:
        """Get all available categories."""
        return list(self._categories.keys())
    
    def get_tags(self) -> List[str]:
        """Get all available tags."""
        return list(self._tags.keys())
    
    async def generate_prompt(self, name: str, arguments: Dict[str, Any]) -> Optional[str]:
        """Generate a prompt from a template with given arguments."""
        template = self.get_prompt(name)
        if not template:
            logger.error(f"Prompt template not found: {name}")
            return None
        
        try:
            # Validate required arguments
            missing_args = []
            for arg in template.arguments:
                if arg.required and arg.name not in arguments:
                    if arg.default is not None:
                        arguments[arg.name] = arg.default
                    else:
                        missing_args.append(arg.name)
            
            if missing_args:
                logger.error(f"Missing required arguments for prompt {name}: {missing_args}")
                return None
            
            # Generate prompt
            if callable(template.prompt):
                # Dynamic prompt generation
                result = template.prompt(**arguments)
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            else:
                # Static template with parameter substitution
                return template.prompt.format(**arguments)
                
        except Exception as e:
            logger.error(f"Error generating prompt {name}: {e}")
            return None
    
    def get_prompt_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a prompt template."""
        template = self.get_prompt(name)
        if not template:
            return None
        
        return {
            "name": template.name,
            "description": template.description,
            "arguments": [
                {
                    "name": arg.name,
                    "description": arg.description,
                    "required": arg.required,
                    "type": arg.type,
                    "default": arg.default
                }
                for arg in template.arguments
            ],
            "version": template.version,
            "category": template.category,
            "tags": template.tags,
            "created_at": template.created_at.isoformat(),
            "updated_at": template.updated_at.isoformat()
        }
    
    def search_prompts(self, query: str) -> List[str]:
        """Search prompts by name, description, or tags."""
        query_lower = query.lower()
        matches = []
        
        for name, template in self._prompts.items():
            if (query_lower in name.lower() or 
                query_lower in template.description.lower() or
                any(query_lower in tag.lower() for tag in template.tags)):
                matches.append(name)
        
        return matches
    
    def _load_built_in_prompts(self) -> None:
        """Load built-in prompt templates."""
        # Code review prompts
        self.register_prompt(PromptTemplate(
            name="code_review",
            description="Generate a comprehensive code review for given code",
            prompt="""Please review the following code and provide feedback:

Code File: {file_path}
Language: {language}

```{language}
{code}
```

Please analyze:
1. Code quality and style
2. Potential bugs or issues
3. Performance considerations
4. Security concerns
5. Maintainability
6. Documentation quality

Provide specific suggestions for improvement.""",
            arguments=[
                PromptArgument("file_path", "Path to the code file"),
                PromptArgument("language", "Programming language"),
                PromptArgument("code", "Code content to review")
            ],
            category="code_analysis",
            tags=["review", "quality", "analysis"]
        ))
        
        # Refactoring prompts
        self.register_prompt(PromptTemplate(
            name="refactor_suggestions",
            description="Suggest refactoring opportunities for code",
            prompt="""Analyze the following code for refactoring opportunities:

File: {file_path}
Language: {language}

```{language}
{code}
```

Focus on: {focus_areas}

Please identify:
1. Code smells and anti-patterns
2. Opportunities for simplification
3. Design pattern applications
4. Performance optimizations
5. Reusability improvements

Provide specific refactoring suggestions with examples.""",
            arguments=[
                PromptArgument("file_path", "Path to the code file"),
                PromptArgument("language", "Programming language"),
                PromptArgument("code", "Code content to analyze"),
                PromptArgument("focus_areas", "Specific areas to focus on", 
                             required=False, default="general improvements")
            ],
            category="refactoring",
            tags=["refactor", "optimization", "patterns"]
        ))
        
        # Documentation prompts
        self.register_prompt(PromptTemplate(
            name="generate_documentation",
            description="Generate documentation for code functions or classes",
            prompt="""Generate comprehensive documentation for the following code:

File: {file_path}
Language: {language}
Documentation Style: {doc_style}

```{language}
{code}
```

Please generate:
1. Function/class descriptions
2. Parameter documentation
3. Return value descriptions
4. Usage examples
5. Error handling notes

Format the documentation according to {doc_style} standards.""",
            arguments=[
                PromptArgument("file_path", "Path to the code file"),
                PromptArgument("language", "Programming language"),
                PromptArgument("code", "Code content to document"),
                PromptArgument("doc_style", "Documentation style", 
                             required=False, default="standard")
            ],
            category="documentation",
            tags=["docs", "comments", "examples"]
        ))
        
        # Bug analysis prompts
        self.register_prompt(PromptTemplate(
            name="bug_analysis",
            description="Analyze code for potential bugs and issues",
            prompt="""Analyze the following code for potential bugs and issues:

File: {file_path}
Language: {language}
Context: {context}

```{language}
{code}
```

Please examine:
1. Logic errors
2. Edge cases
3. Error handling gaps
4. Resource management
5. Concurrency issues
6. Security vulnerabilities

Provide detailed analysis with severity levels and fix suggestions.""",
            arguments=[
                PromptArgument("file_path", "Path to the code file"),
                PromptArgument("language", "Programming language"),
                PromptArgument("code", "Code content to analyze"),
                PromptArgument("context", "Additional context about the code", 
                             required=False, default="")
            ],
            category="debugging",
            tags=["bugs", "analysis", "security"]
        ))
        
        # Test generation prompts
        self.register_prompt(PromptTemplate(
            name="generate_tests",
            description="Generate unit tests for given code",
            prompt="""Generate comprehensive unit tests for the following code:

File: {file_path}
Language: {language}
Test Framework: {test_framework}

```{language}
{code}
```

Please generate tests that cover:
1. Normal execution paths
2. Edge cases
3. Error conditions
4. Boundary values
5. Mock scenarios (if applicable)

Use {test_framework} framework and follow best practices.""",
            arguments=[
                PromptArgument("file_path", "Path to the code file"),
                PromptArgument("language", "Programming language"),
                PromptArgument("code", "Code content to test"),
                PromptArgument("test_framework", "Testing framework to use", 
                             required=False, default="default")
            ],
            category="testing",
            tags=["tests", "unit", "coverage"]
        ))
        
        # Performance analysis prompts
        self.register_prompt(PromptTemplate(
            name="performance_analysis",
            description="Analyze code performance and suggest optimizations",
            prompt="""Analyze the performance characteristics of the following code:

File: {file_path}
Language: {language}
Performance Focus: {focus}

```{language}
{code}
```

Please analyze:
1. Time complexity
2. Space complexity
3. Resource usage patterns
4. Bottlenecks
5. Optimization opportunities
6. Scalability considerations

Provide specific optimization recommendations with estimated impact.""",
            arguments=[
                PromptArgument("file_path", "Path to the code file"),
                PromptArgument("language", "Programming language"),
                PromptArgument("code", "Code content to analyze"),
                PromptArgument("focus", "Performance focus area", 
                             required=False, default="general performance")
            ],
            category="performance",
            tags=["performance", "optimization", "complexity"]
        ))


# Global registry instance
prompt_registry = PromptRegistry()
