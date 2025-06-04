"""
MCP prompt handlers.

Handles MCP prompt-related requests.
"""

import asyncio
from typing import Dict, List, Optional, Any
import logging

from .registry import prompt_registry, PromptTemplate, PromptArgument
from ..protocol.errors import McpError, ErrorCode

logger = logging.getLogger(__name__)


class PromptHandler:
    """Handler for MCP prompt operations."""
    
    def __init__(self):
        self.registry = prompt_registry
    
    async def list_prompts(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle prompts/list request."""
        try:
            # Extract filters from params
            category = None
            tag = None
            if params:
                category = params.get("category")
                tag = params.get("tag")
            
            # Get prompt names
            prompt_names = self.registry.list_prompts(category=category, tag=tag)
            
            # Get detailed info for each prompt
            prompts = []
            for name in prompt_names:
                info = self.registry.get_prompt_info(name)
                if info:
                    prompts.append(info)
            
            return {
                "prompts": prompts
            }
            
        except Exception as e:
            logger.error(f"Error listing prompts: {e}")
            raise McpError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to list prompts: {str(e)}"
            )
    
    async def get_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request."""
        try:
            name = params.get("name")
            if not name:
                raise McpError(
                    code=ErrorCode.INVALID_PARAMS,
                    message="Missing required parameter: name"
                )
            
            arguments = params.get("arguments", {})
            
            # Generate the prompt
            generated_prompt = await self.registry.generate_prompt(name, arguments)
            if generated_prompt is None:
                raise McpError(
                    code=ErrorCode.INVALID_PARAMS,
                    message=f"Failed to generate prompt: {name}"
                )
            
            # Get prompt metadata
            info = self.registry.get_prompt_info(name)
            if not info:
                raise McpError(
                    code=ErrorCode.INVALID_PARAMS,
                    message=f"Prompt not found: {name}"
                )
            
            return {
                "description": info["description"],
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": generated_prompt
                        }
                    }
                ]
            }
            
        except McpError:
            raise
        except Exception as e:
            logger.error(f"Error getting prompt: {e}")
            raise McpError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to get prompt: {str(e)}"
            )
    
    async def search_prompts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle custom prompts/search request."""
        try:
            query = params.get("query")
            if not query:
                raise McpError(
                    code=ErrorCode.INVALID_PARAMS,
                    message="Missing required parameter: query"
                )
            
            # Search prompts
            prompt_names = self.registry.search_prompts(query)
            
            # Get detailed info for matches
            prompts = []
            for name in prompt_names:
                info = self.registry.get_prompt_info(name)
                if info:
                    prompts.append(info)
            
            return {
                "prompts": prompts,
                "total": len(prompts)
            }
            
        except McpError:
            raise
        except Exception as e:
            logger.error(f"Error searching prompts: {e}")
            raise McpError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to search prompts: {str(e)}"
            )
    
    async def get_categories(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle custom prompts/categories request."""
        try:
            categories = self.registry.get_categories()
            return {
                "categories": categories
            }
            
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            raise McpError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to get categories: {str(e)}"
            )
    
    async def get_tags(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle custom prompts/tags request."""
        try:
            tags = self.registry.get_tags()
            return {
                "tags": tags
            }
            
        except Exception as e:
            logger.error(f"Error getting tags: {e}")
            raise McpError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to get tags: {str(e)}"
            )
    
    async def create_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle custom prompts/create request."""
        try:
            name = params.get("name")
            description = params.get("description")
            prompt_text = params.get("prompt")
            
            if not all([name, description, prompt_text]):
                raise McpError(
                    code=ErrorCode.INVALID_PARAMS,
                    message="Missing required parameters: name, description, prompt"
                )
            
            # Parse arguments if provided
            args = []
            if "arguments" in params:
                for arg_data in params["arguments"]:
                    args.append(PromptArgument(
                        name=arg_data["name"],
                        description=arg_data["description"],
                        required=arg_data.get("required", True),
                        type=arg_data.get("type", "string"),
                        default=arg_data.get("default")
                    ))
            
            # Create prompt template
            template = PromptTemplate(
                name=name,
                description=description,
                prompt=prompt_text,
                arguments=args,
                category=params.get("category", "custom"),
                tags=params.get("tags", []),
                version=params.get("version", "1.0.0")
            )
            
            # Register the prompt
            self.registry.register_prompt(template)
            
            return {
                "success": True,
                "name": name,
                "message": f"Prompt '{name}' created successfully"
            }
            
        except McpError:
            raise
        except Exception as e:
            logger.error(f"Error creating prompt: {e}")
            raise McpError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to create prompt: {str(e)}"
            )
    
    async def delete_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle custom prompts/delete request."""
        try:
            name = params.get("name")
            if not name:
                raise McpError(
                    code=ErrorCode.INVALID_PARAMS,
                    message="Missing required parameter: name"
                )
            
            # Delete the prompt
            success = self.registry.unregister_prompt(name)
            if not success:
                raise McpError(
                    code=ErrorCode.INVALID_PARAMS,
                    message=f"Prompt not found: {name}"
                )
            
            return {
                "success": True,
                "name": name,
                "message": f"Prompt '{name}' deleted successfully"
            }
            
        except McpError:
            raise
        except Exception as e:
            logger.error(f"Error deleting prompt: {e}")
            raise McpError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to delete prompt: {str(e)}"
            )


# Global handler instance
prompt_handler = PromptHandler()