"""
MCP capability negotiation.

Handles capability exchange during session initialization.
"""

import logging
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from enum import Enum

from .models import ClientInfo  # Add this import

logger = logging.getLogger(__name__)


class CapabilityType(Enum):
    """Types of capabilities."""
    PROTOCOL = "protocol"
    RESOURCE = "resource"
    TOOL = "tool"
    PROMPT = "prompt"
    TRANSPORT = "transport"
    ENCODING = "encoding"
    EXPERIMENTAL = "experimental"


@dataclass
class Capability:
    """Individual capability definition."""
    name: str
    type: CapabilityType
    version: str
    required: bool = False
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class ClientCapabilities:
    """Client capability information."""
    # Core capabilities
    protocol_version: str = "1.0"
    supported_encodings: List[str] = field(default_factory=lambda: ["json"])
    
    # Feature capabilities
    supports_resources: bool = True
    supports_tools: bool = True
    supports_prompts: bool = True
    supports_subscriptions: bool = True
    supports_streaming: bool = False
    supports_batch_requests: bool = False
    
    # Resource capabilities
    max_resource_size: Optional[int] = None
    supported_resource_types: List[str] = field(default_factory=list)
    
    # Tool capabilities
    max_tool_execution_time: Optional[int] = None
    supports_tool_cancellation: bool = False
    
    # Transport capabilities
    supports_compression: bool = False
    supports_multiplexing: bool = False
    
    # Sampling capabilities
    sampling: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    # Extended capabilities
    experimental_features: Dict[str, Any] = field(default_factory=dict)
    experimental: Optional[Dict[str, Any]] = None
    custom_capabilities: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServerCapabilities:
    """Server capability information."""
    # Core capabilities
    protocol_version: str = "1.0"
    server_name: str = "mcp-server"
    server_version: str = "1.0.0"
    supported_encodings: List[str] = field(default_factory=lambda: ["json"])
    
    # Feature capabilities
    provides_resources: bool = True
    provides_tools: bool = True
    provides_prompts: bool = True
    supports_subscriptions: bool = True
    supports_streaming: bool = False
    supports_batch_requests: bool = False
    
    # Resource capabilities
    available_resource_types: List[str] = field(default_factory=list)
    max_subscriptions_per_session: int = 100
    resource_update_notifications: bool = True
    
    # Tool capabilities
    available_tools: List[str] = field(default_factory=list)
    tool_execution_timeout: int = 30000  # milliseconds
    supports_tool_cancellation: bool = False
    
    # Prompt capabilities
    available_prompts: List[str] = field(default_factory=list)
    supports_prompt_templates: bool = True
    
    # Transport capabilities
    supports_compression: bool = False
    supports_multiplexing: bool = False
    max_message_size: int = 10 * 1024 * 1024  # 10MB
    
    # Rate limiting
    rate_limit_requests_per_minute: Optional[int] = 600
    rate_limit_burst_size: Optional[int] = 100
    
    # Sampling capabilities
    sampling: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    # Extended capabilities
    experimental_features: Dict[str, Any] = field(default_factory=dict)
    experimental: Optional[Dict[str, Any]] = None
    custom_capabilities: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def get_default(cls) -> "ServerCapabilities":
        """Get default server capabilities."""
        import os
        
        # Check if resources should be disabled for Claude Code compatibility
        disable_resources = os.getenv("MCP_DISABLE_RESOURCES", "").lower() in ("true", "1", "yes")
        
        return cls(
            provides_resources=not disable_resources,
            available_resource_types=[] if disable_resources else ["file", "project", "symbol", "search"],
            available_tools=[
                "code-indexer.index_file",
                "code-indexer.lookup_symbol",
                "code-indexer.find_references",
                "code-indexer.search_code"
            ],
            available_prompts=[
                "code_review",
                "refactoring_suggestions",
                "documentation_generation"
            ]
        )


def negotiate_capabilities(
    client_caps: ClientCapabilities,
    server_caps: ServerCapabilities
) -> Dict[str, Any]:
    """
    Negotiate capabilities between client and server.
    
    Returns a dictionary of negotiated capabilities that both
    client and server support.
    """
    negotiated = {
        "protocol_version": min(client_caps.protocol_version, server_caps.protocol_version),
        "encodings": list(
            set(client_caps.supported_encodings) & 
            set(server_caps.supported_encodings)
        ),
        "features": {}
    }
    
    # Negotiate feature support
    features = negotiated["features"]
    
    # Resources
    if client_caps.supports_resources and server_caps.provides_resources:
        features["resources"] = {
            "enabled": True,
            "types": list(
                set(client_caps.supported_resource_types or server_caps.available_resource_types) &
                set(server_caps.available_resource_types)
            ) if client_caps.supported_resource_types else server_caps.available_resource_types,
            "max_size": client_caps.max_resource_size,
            "subscriptions": client_caps.supports_subscriptions and server_caps.supports_subscriptions,
            "max_subscriptions": server_caps.max_subscriptions_per_session,
            "update_notifications": server_caps.resource_update_notifications
        }
    
    # Tools
    if client_caps.supports_tools and server_caps.provides_tools:
        features["tools"] = {
            "enabled": True,
            "available": server_caps.available_tools,
            "execution_timeout": min(
                client_caps.max_tool_execution_time or server_caps.tool_execution_timeout,
                server_caps.tool_execution_timeout
            ),
            "cancellation": (
                client_caps.supports_tool_cancellation and 
                server_caps.supports_tool_cancellation
            )
        }
    
    # Prompts
    if client_caps.supports_prompts and server_caps.provides_prompts:
        features["prompts"] = {
            "enabled": True,
            "available": server_caps.available_prompts,
            "templates": server_caps.supports_prompt_templates
        }
    
    # Streaming
    if client_caps.supports_streaming and server_caps.supports_streaming:
        features["streaming"] = {"enabled": True}
    
    # Batch requests
    if client_caps.supports_batch_requests and server_caps.supports_batch_requests:
        features["batch_requests"] = {"enabled": True}
    
    # Sampling
    if client_caps.sampling and getattr(server_caps, "sampling", None):
        features["sampling"] = {
            "enabled": True,
            "createMessage": (
                client_caps.sampling.get("createMessage", False) and
                server_caps.sampling.get("createMessage", False)
            )
        }
    
    # Transport features
    transport = {
        "compression": (
            client_caps.supports_compression and 
            server_caps.supports_compression
        ),
        "multiplexing": (
            client_caps.supports_multiplexing and 
            server_caps.supports_multiplexing
        ),
        "max_message_size": server_caps.max_message_size
    }
    negotiated["transport"] = transport
    
    # Rate limiting
    if server_caps.rate_limit_requests_per_minute:
        negotiated["rate_limits"] = {
            "requests_per_minute": server_caps.rate_limit_requests_per_minute,
            "burst_size": server_caps.rate_limit_burst_size
        }
    
    # Experimental features
    experimental = {}
    
    # Handle experimental_features field
    for feature, config in client_caps.experimental_features.items():
        if feature in server_caps.experimental_features:
            experimental[feature] = {
                "client": config,
                "server": server_caps.experimental_features[feature]
            }
    
    # Handle experimental field if present
    if client_caps.experimental and server_caps.experimental:
        # Merge experimental dictionaries
        for key, value in client_caps.experimental.items():
            if key in server_caps.experimental:
                experimental[key] = {
                    "client": value,
                    "server": server_caps.experimental[key]
                }
    
    if experimental:
        negotiated["experimental"] = experimental
    
    logger.info(f"Negotiated capabilities: {negotiated}")
    return negotiated


def validate_capability_requirements(
    required_capabilities: List[Capability],
    negotiated_capabilities: Dict[str, Any]
) -> tuple[bool, List[str]]:
    """
    Validate that all required capabilities are satisfied.
    
    Returns:
        Tuple of (is_valid, missing_capabilities)
    """
    missing = []
    
    for cap in required_capabilities:
        if not cap.required:
            continue
        
        # Check based on capability type
        if cap.type == CapabilityType.RESOURCE:
            if not negotiated_capabilities.get("features", {}).get("resources", {}).get("enabled"):
                missing.append(f"resource support")
            elif cap.name not in negotiated_capabilities["features"]["resources"].get("types", []):
                missing.append(f"resource type: {cap.name}")
        
        elif cap.type == CapabilityType.TOOL:
            if not negotiated_capabilities.get("features", {}).get("tools", {}).get("enabled"):
                missing.append(f"tool support")
            elif cap.name not in negotiated_capabilities["features"]["tools"].get("available", []):
                missing.append(f"tool: {cap.name}")
        
        elif cap.type == CapabilityType.ENCODING:
            if cap.name not in negotiated_capabilities.get("encodings", []):
                missing.append(f"encoding: {cap.name}")
        
        elif cap.type == CapabilityType.EXPERIMENTAL:
            if cap.name not in negotiated_capabilities.get("experimental", {}):
                missing.append(f"experimental feature: {cap.name}")
    
    return len(missing) == 0, missing


def filter_methods_by_capabilities(
    available_methods: List[str],
    negotiated_capabilities: Dict[str, Any]
) -> List[str]:
    """
    Filter available methods based on negotiated capabilities.
    
    Returns list of methods that can be used with current capabilities.
    """
    allowed_methods = [
        # Core methods always available
        "initialize",
        "shutdown",
        "ping"
    ]
    
    # Add methods based on features
    features = negotiated_capabilities.get("features", {})
    
    if features.get("resources", {}).get("enabled"):
        allowed_methods.extend([
            "resources/list",
            "resources/read"
        ])
        if features["resources"].get("subscriptions"):
            allowed_methods.extend([
                "resources/subscribe",
                "resources/unsubscribe"
            ])
    
    if features.get("tools", {}).get("enabled"):
        allowed_methods.extend([
            "tools/list",
            "tools/call"
        ])
        if features["tools"].get("cancellation"):
            allowed_methods.append("tools/cancel")
    
    if features.get("prompts", {}).get("enabled"):
        allowed_methods.extend([
            "prompts/list",
            "prompts/get"
        ])
    
    if features.get("batch_requests", {}).get("enabled"):
        allowed_methods.append("batch")
    
    # Filter to only include methods that are actually available
    return [m for m in allowed_methods if m in available_methods]
