workspace "MCP Native Architecture Roadmap" {
  description "Maps existing Code-Index components to native MCP architecture with reuse/recreation annotations"
  
  properties {
    "structurizr.dslEditor" "false"
    "refactor.approach" "native_mcp"
    "timeline.estimate" "17-23 weeks"
    "reuse.percentage" "40-50%"
  }

  model {
    # Level 1: System Context
    user = person "Developer" {
      description "Software developer using Claude for code assistance"
    }
    
    llm = softwareSystem "Claude" {
      description "AI assistant using MCP protocol"
    }
    
    mcp_server = softwareSystem "MCP Code Index Server" {
      description "Native MCP server providing code indexing as MCP resources and tools"
      tags "MCP_Native" "Refactored"
      properties {
        "refactor.status" "complete_redesign"
        "protocol" "JSON-RPC 2.0"
        "transport" "WebSocket, stdio"
      }
    }
    
    repo = softwareSystem "Local Code Repository" {
      description "Developer's local codebase"
      tags "External" "Reusable"
    }
    
    # Relationships
    user -> llm "requests code assistance"
    llm -> mcp_server "MCP protocol (JSON-RPC)"
    mcp_server -> repo "indexes and monitors"
    
    # Level 2: Containers
    mcp_server = softwareSystem "MCP Code Index Server" {
      
      # Core MCP Protocol Layer (NEW)
      mcp_protocol = container "MCP Protocol Handler" {
        description "JSON-RPC 2.0 protocol implementation"
        technology "Python, asyncio"
        tags "New" "Required"
        properties {
          "reuse.status" "cannot_reuse"
          "reason" "No existing JSON-RPC implementation"
          "effort" "2-3 weeks"
        }
      }
      
      # Transport Layer (NEW)
      transport = container "Transport Layer" {
        description "WebSocket and stdio transport implementations"
        technology "Python, WebSocket, asyncio"
        tags "New" "Required"
        properties {
          "reuse.status" "cannot_reuse"
          "reason" "REST API cannot be adapted"
          "effort" "1-2 weeks"
        }
      }
      
      # Session Manager (NEW)
      session = container "Session Manager" {
        description "MCP session lifecycle and state management"
        technology "Python"
        tags "New" "Required"
        properties {
          "reuse.status" "cannot_reuse"
          "reason" "MCP requires stateful sessions"
          "effort" "1 week"
        }
      }
      
      # Resource Manager (NEW)
      resources = container "Resource Manager" {
        description "MCP resource abstraction for code elements"
        technology "Python"
        tags "New" "Required"
        properties {
          "reuse.status" "partial_reuse"
          "reusable" "Storage queries, file content"
          "new" "Resource URI scheme, subscription"
          "effort" "2 weeks"
        }
      }
      
      # Tool Manager (NEW)
      tools = container "Tool Manager" {
        description "MCP tools for code operations"
        technology "Python"
        tags "New" "Required"
        properties {
          "reuse.status" "adapter_pattern"
          "reusable" "Dispatcher logic, search, lookup"
          "new" "Tool registration, schema validation"
          "effort" "2 weeks"
        }
      }
      
      # Prompt Manager (NEW)
      prompts = container "Prompt Manager" {
        description "MCP prompt templates for code analysis"
        technology "Python"
        tags "New" "Optional"
        properties {
          "reuse.status" "cannot_reuse"
          "reason" "New MCP feature"
          "effort" "1 week"
        }
      }
      
      # Existing Components (REUSABLE with modifications)
      dispatcher = container "Dispatcher Core" {
        description "Request routing and plugin coordination"
        technology "Python"
        tags "Reusable" "Modify"
        properties {
          "reuse.status" "heavy_modification"
          "current" "REST-based routing"
          "target" "Called by Tool Manager"
          "changes" "Remove REST deps, add async"
          "effort" "1 week refactor"
        }
      }
      
      plugin_system = container "Plugin System" {
        description "Language-specific code analyzers"
        technology "Python"
        tags "Reusable" "AsIs"
        properties {
          "reuse.status" "full_reuse"
          "reason" "Clean plugin interface (IPlugin)"
          "changes" "None required"
          "effort" "0 weeks"
        }
      }
      
      indexer = container "Index Engine" {
        description "Code indexing and search"
        technology "Python, Tree-sitter"
        tags "Reusable" "AsIs"
        properties {
          "reuse.status" "full_reuse"
          "components" "Fuzzy indexer, Semantic indexer"
          "changes" "Add progress notifications"
          "effort" "3 days"
        }
      }
      
      storage = container "Storage Layer" {
        description "SQLite with FTS5"
        technology "SQLite, Python"
        tags "Reusable" "AsIs"
        properties {
          "reuse.status" "full_reuse"
          "reason" "Storage is protocol-agnostic"
          "changes" "None"
          "effort" "0 weeks"
        }
      }
      
      watcher = container "File Watcher" {
        description "File system monitoring"
        technology "Python, Watchdog"
        tags "Reusable" "Modify"
        properties {
          "reuse.status" "minor_modification"
          "changes" "Emit MCP notifications"
          "effort" "2 days"
        }
      }
      
      # Language Plugins (FULLY REUSABLE)
      python_plugin = container "Python Plugin" {
        description "Python code analysis"
        technology "Python, Tree-sitter, Jedi"
        tags "Reusable" "AsIs"
        properties {
          "reuse.status" "full_reuse"
          "reason" "Implements IPlugin cleanly"
        }
      }
      
      js_plugin = container "JavaScript Plugin" {
        description "JS/TS code analysis"
        technology "Python, Tree-sitter"
        tags "Reusable" "AsIs"
        properties {
          "reuse.status" "full_reuse"
          "reason" "Implements IPlugin cleanly"
        }
      }
      
      c_plugin = container "C Plugin" {
        description "C code analysis"
        technology "Python, Tree-sitter"
        tags "Reusable" "AsIs"
        properties {
          "reuse.status" "full_reuse"
          "reason" "Implements IPlugin cleanly"
        }
      }
      
      # Components to REMOVE
      api_gateway = container "REST API Gateway" {
        description "FastAPI REST endpoints"
        technology "FastAPI"
        tags "Remove" "NotNeeded"
        properties {
          "reuse.status" "remove"
          "reason" "Replaced by MCP protocol"
          "migration" "Logic moves to Tool Manager"
        }
      }
      
      # Optional Future Components
      graph_store = container "Graph Store" {
        description "Code relationship analysis"
        technology "Memgraph"
        tags "Future" "Optional"
        properties {
          "reuse.status" "not_implemented"
          "priority" "phase_4"
        }
      }
      
      cache = container "Cache Layer" {
        description "Performance cache"
        technology "Redis"
        tags "Future" "Optional"
        properties {
          "reuse.status" "not_implemented"
          "priority" "phase_4"
        }
      }
      
      # Container Relationships
      llm -> transport "JSON-RPC over WebSocket/stdio"
      transport -> mcp_protocol "delivers messages"
      mcp_protocol -> session "manages sessions"
      mcp_protocol -> resources "handles resource methods"
      mcp_protocol -> tools "handles tool methods"
      mcp_protocol -> prompts "handles prompt methods"
      
      resources -> storage "queries indexed data"
      resources -> indexer "gets file content"
      
      tools -> dispatcher "executes operations"
      dispatcher -> plugin_system "delegates to plugins"
      plugin_system -> python_plugin "manages"
      plugin_system -> js_plugin "manages"
      plugin_system -> c_plugin "manages"
      
      indexer -> storage "persists indices"
      watcher -> indexer "triggers reindex"
      watcher -> resources "notifies changes"
      
      python_plugin -> storage "stores symbols"
      js_plugin -> storage "stores symbols"
      c_plugin -> storage "stores symbols"
    }
    
    # Level 3: Components
    mcp_protocol = container "MCP Protocol Handler" {
      
      jsonrpc = component "JSON-RPC Handler" {
        description "JSON-RPC 2.0 message processing"
        technology "Python"
        tags "New" "Core"
        properties {
          "methods" "parse, validate, route, respond"
          "error_handling" "JSON-RPC error codes"
        }
      }
      
      method_router = component "Method Router" {
        description "Routes JSON-RPC methods to handlers"
        technology "Python"
        tags "New" "Core"
        properties {
          "methods" "initialize, resources/*, tools/*, prompts/*"
        }
      }
      
      capability_manager = component "Capability Manager" {
        description "MCP capability negotiation"
        technology "Python"
        tags "New" "Core"
        properties {
          "capabilities" "resources, tools, prompts, sampling"
        }
      }
    }
    
    transport = container "Transport Layer" {
      
      websocket_transport = component "WebSocket Transport" {
        description "WebSocket server for MCP"
        technology "Python, aiohttp"
        tags "New" "Primary"
        properties {
          "endpoint" "/mcp"
          "features" "bidirectional, async"
        }
      }
      
      stdio_transport = component "Stdio Transport" {
        description "Standard I/O for CLI usage"
        technology "Python, asyncio"
        tags "New" "Secondary"
        properties {
          "features" "subprocess communication"
        }
      }
      
      transport_interface = component "Transport Interface" {
        description "Common transport abstraction"
        technology "Python"
        tags "New" "Core"
        properties {
          "interface" "ITransport"
        }
      }
    }
    
    resources = container "Resource Manager" {
      
      resource_registry = component "Resource Registry" {
        description "Manages available resources"
        technology "Python"
        tags "New" "Core"
        properties {
          "resources" "code://file/*, code://symbol/*, code://search"
        }
      }
      
      file_resource = component "File Resource Handler" {
        description "Handles code file resources"
        technology "Python"
        tags "New" "Adapter"
        properties {
          "reuses" "Storage file queries"
          "new" "URI scheme, metadata"
        }
      }
      
      symbol_resource = component "Symbol Resource Handler" {
        description "Handles symbol definition resources"
        technology "Python"
        tags "New" "Adapter"
        properties {
          "reuses" "Dispatcher lookup"
          "new" "Resource format"
        }
      }
      
      subscription_manager = component "Subscription Manager" {
        description "Resource change subscriptions"
        technology "Python"
        tags "New" "Advanced"
        properties {
          "integrates_with" "File Watcher"
        }
      }
    }
    
    tools = container "Tool Manager" {
      
      tool_registry = component "Tool Registry" {
        description "Available MCP tools"
        technology "Python"
        tags "New" "Core"
        properties {
          "tools" "search_code, lookup_symbol, find_references, index_file"
        }
      }
      
      search_tool = component "Search Code Tool" {
        description "Code search tool adapter"
        technology "Python"
        tags "Adapter" "Reuse"
        properties {
          "wraps" "Dispatcher.search()"
          "schema" "JSON Schema validation"
        }
      }
      
      symbol_tool = component "Symbol Lookup Tool" {
        description "Symbol definition tool adapter"
        technology "Python"
        tags "Adapter" "Reuse"
        properties {
          "wraps" "Dispatcher.lookup()"
          "schema" "JSON Schema validation"
        }
      }
      
      index_tool = component "Index File Tool" {
        description "Manual indexing tool"
        technology "Python"
        tags "Adapter" "Reuse"
        properties {
          "wraps" "Indexer.index_file()"
          "features" "Progress notifications"
        }
      }
    }
    
    # Existing components that need modification
    dispatcher = container "Dispatcher Core" {
      
      core_dispatcher = component "Core Dispatcher" {
        description "Plugin routing logic"
        technology "Python"
        tags "Reusable" "Modify"
        properties {
          "current_coupling" "REST request/response"
          "target_coupling" "Direct method calls"
          "effort" "Remove REST deps"
        }
      }
      
      plugin_router = component "Plugin Router" {
        description "Routes to language plugins"
        technology "Python"
        tags "Reusable" "AsIs"
        properties {
          "status" "No changes needed"
        }
      }
      
      result_aggregator = component "Result Aggregator" {
        description "Combines plugin results"
        technology "Python"
        tags "Reusable" "AsIs"
        properties {
          "status" "No changes needed"
        }
      }
    }
    
    # Component Relationships
    jsonrpc -> method_router "routes methods"
    method_router -> capability_manager "checks capabilities"
    
    websocket_transport -> transport_interface "implements"
    stdio_transport -> transport_interface "implements"
    transport_interface -> jsonrpc "delivers messages"
    
    method_router -> resource_registry "resources/* methods"
    method_router -> tool_registry "tools/* methods"
    
    resource_registry -> file_resource "delegates file resources"
    resource_registry -> symbol_resource "delegates symbol resources"
    file_resource -> core_dispatcher "queries files"
    symbol_resource -> core_dispatcher "lookups symbols"
    
    tool_registry -> search_tool "search_code tool"
    tool_registry -> symbol_tool "lookup_symbol tool"
    tool_registry -> index_tool "index_file tool"
    
    search_tool -> core_dispatcher "calls search()"
    symbol_tool -> core_dispatcher "calls lookup()"
    index_tool -> core_dispatcher "calls index_file()"
    
    subscription_manager -> file_resource "notifies changes"
  }
  
  views {
    systemContext mcp_server "MCPSystemContext" {
      include *
      autolayout lr
      description "MCP native architecture system context"
    }
    
    container mcp_server "MCPContainers" {
      include *
      autolayout lr
      description "MCP server container architecture showing reuse/new components"
    }
    
    component mcp_protocol "ProtocolComponents" {
      include *
      autolayout lr
      description "New MCP protocol handler components"
    }
    
    component transport "TransportComponents" {
      include *
      autolayout lr
      description "New transport layer components"
    }
    
    component resources "ResourceComponents" {
      include *
      autolayout lr
      description "New resource manager components with adapters"
    }
    
    component tools "ToolComponents" {
      include *
      autolayout lr
      description "New tool manager components wrapping existing logic"
    }
    
    component dispatcher "DispatcherRefactor" {
      include *
      autolayout lr
      description "Existing dispatcher components to be modified"
    }
    
    styles {
    element "MCP_Native" {
      background #4A90E2
      color #ffffff
    }
    
    element "New" {
      background #E74C3C
      color #ffffff
      shape RoundedBox
    }
    
    element "Required" {
      icon "!"
    }
    
    element "Reusable" {
      background #27AE60
      color #ffffff
    }
    
    element "AsIs" {
      shape Box
      icon "✓"
    }
    
    element "Modify" {
      background #F39C12
      color #ffffff
      shape Hexagon
    }
    
    element "Remove" {
      background #95A5A6
      color #ffffff
      shape Box
      icon "✗"
    }
    
    element "Adapter" {
      background #9B59B6
      color #ffffff
      shape Component
    }
    
    element "Future" {
      background #BDC3C7
      color #000000
      style dashed
    }
    
    element "Core" {
      icon "★"
    }
    
    element "External" {
      background #34495E
      color #ffffff
    }
    
    element "NotNeeded" {
      style dashed
    }
    
    element "Optional" {
      style dotted
    }
    
    relationship "Relationship" {
      thickness 2
      colour #333333
    }
    }
  }
}

## Implementation Phases Summary

### Phase 1: MCP Foundation (4-6 weeks)
**New Components Required:**
- MCP Protocol Handler (JSON-RPC 2.0)
- Transport Layer (WebSocket + stdio)
- Session Manager
- Basic Resource/Tool/Prompt managers

**Cannot Reuse:**
- REST API Gateway (completely different protocol)
- HTTP request/response patterns

### Phase 2: Core Integration (6-8 weeks)
**Components to Adapt:**
- Dispatcher (remove REST coupling) - 1 week
- File Watcher (add MCP notifications) - 2 days
- Create Resource handlers wrapping storage
- Create Tool handlers wrapping dispatcher

**Fully Reusable:**
- Storage Layer (SQLite)
- All Language Plugins (Python, JS, C)
- Indexer components (Fuzzy, Semantic)
- Plugin System base

### Phase 3: Migration (4-5 weeks)
**Migration Tasks:**
- REST endpoint logic → MCP Tools
- File paths → Resource URIs
- Sync responses → Async notifications
- Add progress reporting

### Phase 4: Advanced Features (3-4 weeks)
**Optional Enhancements:**
- Graph Store (not implemented yet)
- Cache Layer (not implemented yet)
- Advanced subscriptions
- Sampling support

## Reusability Analysis

### Can Fully Reuse (40%):
- All language plugins (IPlugin interface)
- Storage layer (SQLite + FTS5)
- Core indexing algorithms
- Tree-sitter wrappers
- Plugin interfaces

### Need Modification (20%):
- Dispatcher (remove REST deps)
- File Watcher (add notifications)
- Result formats (adapt to MCP)

### Must Recreate (40%):
- Protocol layer (JSON-RPC)
- Transport layer (WebSocket/stdio)
- Session management
- Resource/Tool abstractions
- MCP method handlers

### Can Remove:
- FastAPI REST API
- HTTP authentication
- REST request validation