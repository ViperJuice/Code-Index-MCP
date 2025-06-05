#!/usr/bin/env python3
"""
Setup script for MCP migration directory structure.
Creates new MCP directories alongside existing code for gradual migration.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Color codes for terminal output
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

def create_directory(path: Path, description: str):
    """Create a directory and report status."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        print(f"{GREEN}✓{RESET} Created: {path} - {description}")
        return True
    except Exception as e:
        print(f"{RED}✗{RESET} Failed to create {path}: {e}")
        return False

def create_file(path: Path, content: str, description: str):
    """Create a file with content and report status."""
    try:
        # Create parent directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Only create if file doesn't exist (don't overwrite)
        if path.exists():
            print(f"{YELLOW}⚠{RESET} Skipped: {path} - already exists")
            return True
            
        path.write_text(content)
        print(f"{GREEN}✓{RESET} Created: {path} - {description}")
        return True
    except Exception as e:
        print(f"{RED}✗{RESET} Failed to create {path}: {e}")
        return False

def create_init_file(path: Path, module_doc: str):
    """Create __init__.py with module documentation."""
    content = f'"""\n{module_doc}\n"""\n'
    return create_file(path / "__init__.py", content, "__init__.py")

def setup_mcp_structure():
    """Create the complete MCP migration directory structure."""
    
    print(f"\n{BLUE}Setting up MCP migration directory structure...{RESET}\n")
    
    # Base path
    base_path = Path("mcp_server")
    
    # Track success
    total = 0
    successful = 0
    
    # 1. Protocol Layer
    protocol_path = base_path / "protocol"
    total += 1
    if create_directory(protocol_path, "MCP Protocol Layer"):
        successful += 1
        
    # Protocol files
    protocol_files = {
        "__init__.py": "MCP Protocol implementation for JSON-RPC 2.0",
        "jsonrpc.py": """\"\"\"
JSON-RPC 2.0 protocol handler for MCP.

This module implements the core JSON-RPC 2.0 protocol handling
for the Model Context Protocol.
\"\"\"

# TODO: Implement JSONRPCRequest, JSONRPCResponse, JSONRPCError classes
# TODO: Implement request parsing and response formatting
# TODO: Add error handling for protocol violations
""",
        "methods.py": """\"\"\"
MCP method routing and handling.

Maps MCP method names to handler functions and manages
method registration and dispatch.
\"\"\"

# TODO: Implement method registry
# TODO: Add handlers for initialize, resources/*, tools/*, prompts/*
# TODO: Implement method validation
""",
        "errors.py": """\"\"\"
MCP error definitions and handling.

Defines standard MCP error codes and error response formatting.
\"\"\"

# TODO: Define MCP error codes (following JSON-RPC standards)
# TODO: Implement error response formatting
# TODO: Add error logging
""",
        "validators.py": """\"\"\"
Request validation for MCP protocol.

Validates incoming requests against MCP schema definitions.
\"\"\"

# TODO: Implement request schema validation
# TODO: Add parameter validation for each method type
# TODO: Implement capability checking
"""
    }
    
    for filename, content in protocol_files.items():
        total += 1
        if create_file(protocol_path / filename, content, f"Protocol {filename}"):
            successful += 1
    
    # 2. Transport Layer
    transport_path = base_path / "transport"
    total += 1
    if create_directory(transport_path, "Transport Implementations"):
        successful += 1
        
    transport_files = {
        "__init__.py": "Transport layer implementations for MCP",
        "base.py": """\"\"\"
Abstract base transport interface.

Defines the common interface that all transport implementations must follow.
\"\"\"

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

class Transport(ABC):
    \"\"\"Abstract base class for MCP transports.\"\"\"
    
    @abstractmethod
    async def send(self, message: str) -> None:
        \"\"\"Send a message over the transport.\"\"\"
        pass
        
    @abstractmethod
    async def receive(self) -> AsyncIterator[str]:
        \"\"\"Receive messages from the transport.\"\"\"
        pass
        
    @abstractmethod
    async def close(self) -> None:
        \"\"\"Close the transport connection.\"\"\"
        pass

# TODO: Add connection state management
# TODO: Add error handling methods
# TODO: Add transport metadata
""",
        "websocket.py": """\"\"\"
WebSocket transport implementation for MCP.

Provides WebSocket-based communication for MCP clients.
\"\"\"

# TODO: Implement WebSocket server using aiohttp
# TODO: Add connection handling and lifecycle management
# TODO: Implement message framing and buffering
# TODO: Add reconnection support
""",
        "stdio.py": """\"\"\"
Standard I/O transport implementation for MCP.

Provides stdin/stdout communication for subprocess-based MCP usage.
\"\"\"

# TODO: Implement async stdio reading/writing
# TODO: Add line-based message framing
# TODO: Handle process lifecycle
# TODO: Add buffering for large messages
""",
        "connection.py": """\"\"\"
Connection management for MCP transports.

Handles connection lifecycle, authentication, and session binding.
\"\"\"

# TODO: Implement connection pool
# TODO: Add connection authentication
# TODO: Implement session binding
# TODO: Add connection metrics
"""
    }
    
    for filename, content in transport_files.items():
        total += 1
        if create_file(transport_path / filename, content, f"Transport {filename}"):
            successful += 1
    
    # 3. Session Management
    session_path = base_path / "session"
    total += 1
    if create_directory(session_path, "Session Management"):
        successful += 1
        
    session_files = {
        "__init__.py": "MCP session management",
        "manager.py": """\"\"\"
MCP session lifecycle management.

Manages session creation, state transitions, and cleanup.
\"\"\"

# TODO: Implement session state machine
# TODO: Add session storage and retrieval
# TODO: Implement session timeout handling
# TODO: Add session event notifications
""",
        "store.py": """\"\"\"
Session storage implementation.

Stores active session data and provides retrieval methods.
\"\"\"

# TODO: Implement in-memory session store
# TODO: Add session persistence (optional)
# TODO: Implement session querying
# TODO: Add session cleanup
""",
        "capabilities.py": """\"\"\"
MCP capability negotiation.

Handles capability exchange during session initialization.
\"\"\"

# TODO: Define server capabilities
# TODO: Implement capability negotiation protocol
# TODO: Add capability validation
# TODO: Implement capability-based method filtering
"""
    }
    
    for filename, content in session_files.items():
        total += 1
        if create_file(session_path / filename, content, f"Session {filename}"):
            successful += 1
    
    # 4. Resources
    resources_path = base_path / "resources"
    total += 1
    if create_directory(resources_path, "MCP Resources"):
        successful += 1
        
    total += 1
    if create_init_file(resources_path, "MCP resource implementations"):
        successful += 1
        
    # Resource files
    resource_files = {
        "registry.py": """\"\"\"
Resource registry for MCP.

Manages available resources and their metadata.
\"\"\"

# TODO: Implement resource registration
# TODO: Add resource discovery
# TODO: Implement resource metadata management
# TODO: Add resource access control
""",
        "subscriptions.py": """\"\"\"
Resource subscription management.

Handles resource change notifications and subscriptions.
\"\"\"

# TODO: Implement subscription registry
# TODO: Add change detection integration
# TODO: Implement notification batching
# TODO: Add subscription filtering
"""
    }
    
    for filename, content in resource_files.items():
        total += 1
        if create_file(resources_path / filename, content, f"Resource {filename}"):
            successful += 1
    
    # Resource handlers subdirectory
    handlers_path = resources_path / "handlers"
    total += 1
    if create_directory(handlers_path, "Resource handlers"):
        successful += 1
        
    handler_files = {
        "__init__.py": "Resource handler implementations",
        "file.py": """\"\"\"
File resource handler for code://file/* URIs.

Provides access to indexed source files.
\"\"\"

# TODO: Implement file resource URI parsing
# TODO: Add file content retrieval from storage
# TODO: Implement file metadata (language, size, etc.)
# TODO: Add syntax highlighting metadata
""",
        "symbol.py": """\"\"\"
Symbol resource handler for code://symbol/* URIs.

Provides access to code symbols (functions, classes, etc.).
\"\"\"

# TODO: Implement symbol URI parsing
# TODO: Add symbol lookup from storage
# TODO: Implement symbol metadata (type, signature, docs)
# TODO: Add symbol relationship data
""",
        "search.py": """\"\"\"
Search resource handler for code://search URIs.

Provides dynamic search results as resources.
\"\"\"

# TODO: Implement search query parsing
# TODO: Add search execution via dispatcher
# TODO: Implement result formatting
# TODO: Add search result ranking
""",
        "project.py": """\"\"\"
Project resource handler for code://project URIs.

Provides project-level information and statistics.
\"\"\"

# TODO: Implement project statistics gathering
# TODO: Add project structure information
# TODO: Implement project configuration data
# TODO: Add project dependency information
"""
    }
    
    for filename, content in handler_files.items():
        total += 1
        if create_file(handlers_path / filename, content, f"Handler {filename}"):
            successful += 1
    
    # 5. Tools
    tools_path = base_path / "tools"
    total += 1
    if create_directory(tools_path, "MCP Tools"):
        successful += 1
        
    total += 1
    if create_init_file(tools_path, "MCP tool implementations"):
        successful += 1
        
    # Tool files
    tool_files = {
        "registry.py": """\"\"\"
Tool registry for MCP.

Manages available tools and their schemas.
\"\"\"

# TODO: Implement tool registration
# TODO: Add tool discovery
# TODO: Implement tool schema management
# TODO: Add tool access control
""",
        "validators.py": """\"\"\"
Tool input validation.

Validates tool inputs against JSON schemas.
\"\"\"

# TODO: Implement JSON schema validation
# TODO: Add custom validation rules
# TODO: Implement error reporting
# TODO: Add validation caching
""",
        "schemas.py": """\"\"\"
Tool schema definitions.

Defines JSON schemas for all MCP tools.
\"\"\"

# TODO: Define schema for search_code tool
# TODO: Define schema for lookup_symbol tool
# TODO: Define schema for find_references tool
# TODO: Define schema for index_file tool
"""
    }
    
    for filename, content in tool_files.items():
        total += 1
        if create_file(tools_path / filename, content, f"Tool {filename}"):
            successful += 1
    
    # Tool handlers subdirectory
    tool_handlers_path = tools_path / "handlers"
    total += 1
    if create_directory(tool_handlers_path, "Tool handlers"):
        successful += 1
        
    tool_handler_files = {
        "__init__.py": "Tool handler implementations",
        "search_code.py": """\"\"\"
Code search tool implementation.

Provides pattern and semantic search across codebase.
\"\"\"

# TODO: Implement search parameter parsing
# TODO: Add dispatcher integration for search
# TODO: Implement result formatting
# TODO: Add search options (regex, semantic, fuzzy)
""",
        "lookup_symbol.py": """\"\"\"
Symbol lookup tool implementation.

Finds symbol definitions across the codebase.
\"\"\"

# TODO: Implement symbol lookup parameters
# TODO: Add dispatcher integration
# TODO: Implement fuzzy matching support
# TODO: Add multi-symbol batch lookup
""",
        "find_references.py": """\"\"\"
Reference finder tool implementation.

Locates all references to a given symbol.
\"\"\"

# TODO: Implement reference search parameters
# TODO: Add dispatcher integration
# TODO: Implement scope filtering
# TODO: Add reference categorization
""",
        "index_file.py": """\"\"\"
File indexing tool implementation.

Manually triggers indexing for specific files.
\"\"\"

# TODO: Implement indexing parameters
# TODO: Add dispatcher integration
# TODO: Implement progress notifications
# TODO: Add batch indexing support
"""
    }
    
    for filename, content in tool_handler_files.items():
        total += 1
        if create_file(tool_handlers_path / filename, content, f"Tool handler {filename}"):
            successful += 1
    
    # 6. Prompts (Phase 3 - create structure now)
    prompts_path = base_path / "prompts"
    total += 1
    if create_directory(prompts_path, "MCP Prompts (Phase 3)"):
        successful += 1
        
    total += 1
    if create_init_file(prompts_path, "MCP prompt templates (Phase 3)"):
        successful += 1
        
    prompt_files = {
        "registry.py": """\"\"\"
Prompt registry for MCP.

Manages available prompt templates.
\"\"\"

# TODO: Phase 3 - Implement prompt registration
# TODO: Phase 3 - Add prompt discovery
# TODO: Phase 3 - Implement prompt metadata
"""
    }
    
    for filename, content in prompt_files.items():
        total += 1
        if create_file(prompts_path / filename, content, f"Prompt {filename}"):
            successful += 1
    
    # Prompt templates subdirectory
    templates_path = prompts_path / "templates"
    total += 1
    if create_directory(templates_path, "Prompt templates"):
        successful += 1
        
    template_files = {
        "__init__.py": "Prompt template implementations",
        "code_review.py": """\"\"\"
Code review prompt templates.

Provides prompts for code review scenarios.
\"\"\"

# TODO: Phase 3 - Implement code review prompts
""",
        "refactoring.py": """\"\"\"
Refactoring prompt templates.

Provides prompts for code refactoring scenarios.
\"\"\"

# TODO: Phase 3 - Implement refactoring prompts
"""
    }
    
    for filename, content in template_files.items():
        total += 1
        if create_file(templates_path / filename, content, f"Template {filename}"):
            successful += 1
    
    # 7. Interfaces - Add MCP interfaces
    interfaces_path = base_path / "interfaces"
    mcp_interfaces_content = """\"\"\"
MCP-specific interface definitions.

Defines interfaces for MCP protocol components.
\"\"\"

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncIterator
from dataclasses import dataclass

@dataclass
class MCPRequest:
    \"\"\"Base MCP request structure.\"\"\"
    method: str
    params: Optional[Dict[str, Any]] = None
    
@dataclass
class MCPResponse:
    \"\"\"Base MCP response structure.\"\"\"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

class IMCPHandler(ABC):
    \"\"\"Interface for MCP method handlers.\"\"\"
    
    @abstractmethod
    async def handle(self, request: MCPRequest) -> MCPResponse:
        \"\"\"Handle an MCP request and return a response.\"\"\"
        pass

class IMCPResource(ABC):
    \"\"\"Interface for MCP resources.\"\"\"
    
    @abstractmethod
    def get_uri(self) -> str:
        \"\"\"Get the resource URI.\"\"\"
        pass
        
    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        \"\"\"Get resource metadata.\"\"\"
        pass

class IMCPTool(ABC):
    \"\"\"Interface for MCP tools.\"\"\"
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        \"\"\"Get the tool's JSON schema.\"\"\"
        pass
        
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Any:
        \"\"\"Execute the tool with given parameters.\"\"\"
        pass

# TODO: Add more specific interfaces as needed
# TODO: Add interface documentation
# TODO: Add type hints for all methods
"""
    
    total += 1
    if create_file(interfaces_path / "mcp_interfaces.py", mcp_interfaces_content, "MCP interfaces"):
        successful += 1
    
    # 8. Security - Add MCP security
    security_path = base_path / "security"
    mcp_security_content = """\"\"\"
MCP-specific security implementation.

Handles security for MCP protocol connections.
\"\"\"

# TODO: Implement MCP connection authentication
# TODO: Add capability-based access control
# TODO: Implement rate limiting for MCP methods
# TODO: Add audit logging for MCP operations

class MCPSecurityManager:
    \"\"\"Manages security for MCP connections.\"\"\"
    
    def __init__(self):
        \"\"\"Initialize the security manager.\"\"\"
        # TODO: Initialize security components
        pass
        
    async def authenticate_connection(self, connection_info: dict) -> bool:
        \"\"\"Authenticate an MCP connection.\"\"\"
        # TODO: Implement authentication logic
        return True  # Temporary - accept all connections
        
    def check_capability(self, session_id: str, capability: str) -> bool:
        \"\"\"Check if a session has a specific capability.\"\"\"
        # TODO: Implement capability checking
        return True  # Temporary - allow all capabilities

# TODO: Add more security features as needed
"""
    
    total += 1
    if create_file(security_path / "mcp_security.py", mcp_security_content, "MCP security"):
        successful += 1
    
    # Summary
    print(f"\n{BLUE}={'='*60}{RESET}")
    print(f"{BLUE}Summary:{RESET}")
    print(f"  Total items: {total}")
    print(f"  Successful: {GREEN}{successful}{RESET}")
    print(f"  Failed: {RED}{total - successful}{RESET}")
    
    if successful == total:
        print(f"\n{GREEN}✓ MCP migration structure created successfully!{RESET}")
    else:
        print(f"\n{YELLOW}⚠ Some items failed. Check the errors above.{RESET}")
    
    print(f"\n{BLUE}Next steps:{RESET}")
    print(f"  1. Review the generated structure in mcp_server/")
    print(f"  2. Start implementing Phase 1 components (protocol, transport, session)")
    print(f"  3. Update MCP_MIGRATION_STATUS.md as you progress")
    print(f"  4. Run tests alongside existing code")
    print(f"{BLUE}={'='*60}{RESET}\n")

if __name__ == "__main__":
    setup_mcp_structure()