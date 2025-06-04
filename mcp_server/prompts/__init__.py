"""
MCP Prompts System.

Manages prompt templates and generation for MCP.
"""

from .registry import (
    PromptArgument,
    PromptTemplate, 
    PromptRegistry,
    prompt_registry
)
from .handlers import PromptHandler, prompt_handler

def get_prompt_registry() -> PromptRegistry:
    """Get the global prompt registry instance."""
    return prompt_registry

__all__ = [
    "PromptArgument",
    "PromptTemplate",
    "PromptRegistry", 
    "prompt_registry",
    "get_prompt_registry",
    "PromptHandler",
    "prompt_handler"
]
