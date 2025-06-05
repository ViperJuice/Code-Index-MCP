workspace "Code-Index Native MCP Server" {
  description "Complete multi-level architecture of the native MCP server implementation"
  
  properties {
    "structurizr.dslEditor" "false"
    "implementation.approach" "consolidated_production_server"
    "implementation.status" "completed"
    "primary.server" "stdio_server.py"
    "protocol" "JSON-RPC 2.0"
    "transport" "WebSocket, stdio"
    "refactor.status" "completed"
    "reuse.percentage" "45%"
    "detail.levels" "context, containers, components"
    "phase5.timeline" "Q2-Q3 2025 (6-8 months)"
    "phase5.languages" "Rust, Go, Java/Kotlin, Ruby, PHP"
    "phase5.performance" "Distributed, GPU, Advanced Cache"
  }

  model {
    # ====================
    # LEVEL 1: System Context
    # ====================
    
    # External actors
    user = person "Developer" {
      description "Software developer using Claude or other MCP-enabled AI assistants for code assistance"
    }
    
    llm = softwareSystem "MCP Client (Claude/LLM)" {
      description "AI assistant that connects via Model Context Protocol"
      tags "External" "MCPClient"
      properties {
        "protocol" "JSON-RPC 2.0"
        "transport" "WebSocket or stdio"
      }
    }
    
    # Core MCP Server
    mcp_server = softwareSystem "Code-Index MCP Server" {
      description "Native MCP server providing code indexing, search, and analysis as MCP resources and tools"
      tags "CoreSystem" "MCPNative"
      properties {
        "refactor.status" "native_mcp"
        "protocol" "JSON-RPC 2.0"
        "transport" "WebSocket, stdio"
        "capabilities" "resources, tools, prompts"
        "performance.targets" "Symbol lookup <100ms, Search <500ms, Index 10K files/min"
      }
      
      # ====================
      # LEVEL 2: Containers
      # ====================
      
      # NEW MCP-SPECIFIC CONTAINERS (Must Build)
      
      protocol_handler = container "MCP Protocol Handler" {
        description "JSON-RPC 2.0 protocol implementation for MCP"
        technology "Python, asyncio"
        tags "New" "Required" "Core"
        properties {
          "reuse" "Cannot reuse - REST API incompatible"
          "effort" "3-4 weeks"
          "components" "JSON-RPC parser, method router, error handler"
        }
        
        # Level 3: Protocol Handler Components
        jsonrpc_handler = component "JSON-RPC Handler" {
          description "Parses and validates JSON-RPC 2.0 messages"
          technology "Python"
          tags "New" "Core"
          properties {
            "reuse" "Cannot reuse"
            "implements" "JSON-RPC 2.0 spec"
            "methods" "parse_message, validate_request, format_response"
          }
        }
        
        method_router = component "Method Router" {
          description "Routes MCP methods to appropriate handlers"
          technology "Python"
          tags "New" "Core"
          properties {
            "reuse" "Cannot reuse"
            "routes" "initialize, resources/*, tools/*, prompts/*"
          }
        }
        
        error_handler = component "Error Handler" {
          description "MCP-compliant error responses"
          technology "Python"
          tags "New"
          properties {
            "reuse" "Cannot reuse"
            "errors" "JSON-RPC errors, MCP-specific errors"
          }
        }
        
        capability_negotiator = component "Capability Negotiator" {
          description "Handles MCP capability exchange"
          technology "Python"
          tags "New"
          properties {
            "capabilities" "resources, tools, prompts, subscriptions"
          }
        }
      }
      
      transport_layer = container "Transport Layer" {
        description "WebSocket and stdio transport implementations"
        technology "Python, aiohttp, asyncio"
        tags "New" "Required" "Core"
        properties {
          "reuse" "Cannot reuse - new protocol layer"
          "effort" "2 weeks"
          "transports" "WebSocket server, stdio handler"
        }
        
        # Level 3: Transport Components
        websocket_server = component "WebSocket Server" {
          description "WebSocket endpoint for MCP connections"
          technology "Python, aiohttp"
          tags "New" "Primary"
          properties {
            "reuse" "Cannot reuse"
            "endpoint" "ws://localhost:8000/mcp"
          }
        }
        
        stdio_handler = component "Stdio Handler" {
          description "Standard I/O transport for CLI usage"
          technology "Python, asyncio"
          tags "New"
          properties {
            "reuse" "Cannot reuse"
            "usage" "Subprocess communication"
          }
        }
        
        transport_abstraction = component "Transport Abstraction" {
          description "Common interface for all transports"
          technology "Python"
          tags "New" "Interface"
          properties {
            "interface" "ITransport"
            "methods" "send, receive, close"
          }
        }
      }
      
      session_manager = container "Session Manager" {
        description "MCP session lifecycle and capability negotiation"
        technology "Python"
        tags "New" "Required"
        properties {
          "reuse" "Cannot reuse - MCP requires stateful sessions"
          "effort" "1 week"
          "features" "Session state, capability exchange, client info"
        }
        
        # Level 3: Session Components
        session_store = component "Session Store" {
          description "Stores active MCP sessions"
          technology "Python"
          tags "New"
          properties {
            "storage" "In-memory dict"
            "data" "session_id, client_info, capabilities"
          }
        }
        
        session_lifecycle = component "Session Lifecycle" {
          description "Manages session state transitions"
          technology "Python"
          tags "New"
          properties {
            "states" "initializing, ready, closing, closed"
          }
        }
        
        client_registry = component "Client Registry" {
          description "Tracks connected MCP clients"
          technology "Python"
          tags "New"
          properties {
            "tracks" "Client versions, capabilities, subscriptions"
          }
        }
      }
      
      resource_manager = container "Resource Manager" {
        description "MCP resource abstraction for code elements"
        technology "Python"
        tags "New" "Required" "Adapter"
        properties {
          "reuse" "Partial - wraps existing storage queries"
          "effort" "2 weeks"
          "resources" "code://file/*, code://symbol/*, code://search"
        }
        
        # Level 3: Resource Components
        resource_registry = component "Resource Registry" {
          description "Manages available MCP resources"
          technology "Python"
          tags "New" "Core"
          properties {
            "resources" "file, symbol, search, project"
          }
        }
        
        file_resource_handler = component "File Resource Handler" {
          description "Handles code://file/* resources"
          technology "Python"
          tags "New" "Adapter"
          properties {
            "reuses" "storage.get_file_content()"
            "wraps" "Existing file queries"
          }
        }
        
        symbol_resource_handler = component "Symbol Resource Handler" {
          description "Handles code://symbol/* resources"
          technology "Python"
          tags "New" "Adapter"
          properties {
            "reuses" "dispatcher.lookup()"
            "wraps" "Symbol definitions"
          }
        }
        
        search_resource_handler = component "Search Resource Handler" {
          description "Handles code://search resources"
          technology "Python"
          tags "New" "Adapter"
          properties {
            "reuses" "dispatcher.search()"
            "dynamic" "Query-based resource"
          }
        }
        
        subscription_manager = component "Subscription Manager" {
          description "Manages resource change subscriptions"
          technology "Python"
          tags "New" "Advanced"
          properties {
            "integrates" "file_watcher notifications"
          }
        }
      }
      
      tool_manager = container "Tool Manager" {
        description "MCP tools exposing code operations"
        technology "Python"
        tags "New" "Required" "Adapter"
        properties {
          "reuse" "High - wraps existing dispatcher methods"
          "effort" "2 weeks"
          "tools" "search_code, lookup_symbol, find_references, index_file"
        }
        
        # Level 3: Tool Components
        tool_registry = component "Tool Registry" {
          description "Registry of available MCP tools"
          technology "Python"
          tags "New" "Core"
          properties {
            "tools" "search_code, lookup_symbol, find_references, index_file"
          }
        }
        
        search_tool = component "Search Code Tool" {
          description "MCP tool for code search"
          technology "Python"
          tags "New" "Adapter"
          properties {
            "reuses" "dispatcher.search()"
            "schema" "JSON Schema validation"
          }
        }
        
        symbol_lookup_tool = component "Symbol Lookup Tool" {
          description "MCP tool for symbol definitions"
          technology "Python"
          tags "New" "Adapter"
          properties {
            "reuses" "dispatcher.lookup()"
            "schema" "JSON Schema validation"
          }
        }
        
        reference_finder_tool = component "Reference Finder Tool" {
          description "MCP tool for finding references"
          technology "Python"
          tags "New" "Adapter"
          properties {
            "reuses" "dispatcher.find_references()"
            "schema" "JSON Schema validation"
          }
        }
        
        indexing_tool = component "Indexing Tool" {
          description "MCP tool for automatic file indexing"
          technology "Python"
          tags "New" "Adapter"
          properties {
            "reuses" "dispatcher.index_file()"
            "features" "Progress notifications, auto-download"
          }
        }
        
        tool_validator = component "Tool Validator" {
          description "Validates tool inputs against schemas"
          technology "Python"
          tags "New"
          properties {
            "validation" "JSON Schema"
          }
        }
      }
      
      prompt_manager = container "Prompt Manager" {
        description "MCP prompt templates for code analysis"
        technology "Python"
        tags "New" "Optional"
        properties {
          "reuse" "Cannot reuse - new MCP feature"
          "effort" "1 week"
          "priority" "Phase 3"
        }
      }
      
      # REUSABLE CONTAINERS (From existing codebase)
      
      dispatcher = container "Dispatcher" {
        description "Routes requests to appropriate language plugins"
        technology "Python"
        tags "Reusable" "Modify" "Core"
        properties {
          "reuse" "High - core logic intact"
          "changes" "Remove REST coupling, add async support"
          "effort" "1 week refactoring"
          "current_state" "Working dispatcher with plugin routing"
        }
        
        # Level 3: Dispatcher Components
        dispatcher_core = component "Dispatcher Core" {
          description "Core request routing logic"
          technology "Python"
          tags "Reusable" "Modify"
          properties {
            "current" "REST-coupled implementation"
            "changes" "Remove FastAPI deps, add async"
            "reusable_methods" "lookup(), search(), index_file()"
          }
        }
        
        plugin_router = component "Plugin Router" {
          description "Routes to language plugins by file type"
          technology "Python"
          tags "Reusable" "AsIs"
          properties {
            "current" "Working implementation"
            "reuse" "100% - no changes needed"
          }
        }
        
        result_aggregator = component "Result Aggregator" {
          description "Aggregates results from multiple plugins"
          technology "Python"
          tags "Reusable" "AsIs"
          properties {
            "current" "Working implementation"
            "reuse" "100% - no changes needed"
          }
        }
        
        dispatcher_cache = component "Dispatcher Cache" {
          description "In-memory result cache"
          technology "Python"
          tags "Reusable" "AsIs"
          properties {
            "current" "Content-based caching"
            "reuse" "100% - works as-is"
          }
        }
      }
      
      plugin_system = container "Plugin System" {
        description "Manages language-specific code analyzers"
        technology "Python"
        tags "Reusable" "AsIs"
        properties {
          "reuse" "100% - clean IPlugin interface"
          "effort" "0 weeks"
          "plugins" "Python, JavaScript, C, C++, Dart, HTML/CSS"
        }
        
        # Level 3: Plugin System Components
        plugin_base = component "Plugin Base" {
          description "IPlugin abstract interface"
          technology "Python"
          tags "Reusable" "AsIs" "Interface"
          properties {
            "interface" "IPlugin"
            "methods" "supports(), index_file(), get_definition(), search()"
            "reuse" "100% - clean abstraction"
          }
        }
        
        plugin_manager = component "Plugin Manager" {
          description "Plugin lifecycle management"
          technology "Python"
          tags "Reusable" "MinorChanges"
          properties {
            "current" "Basic plugin list"
            "enhance" "Add dynamic loading"
          }
        }
        
        treesitter_wrapper = component "TreeSitter Wrapper" {
          description "Unified Tree-sitter interface"
          technology "Python, tree-sitter"
          tags "Reusable" "AsIs"
          properties {
            "current" "Working wrapper"
            "reuse" "100% - used by all plugins"
          }
        }
      }
      
      storage = container "Storage Layer" {
        description "SQLite database with FTS5 for fast search"
        technology "SQLite, Python"
        tags "Reusable" "AsIs" "Database"
        properties {
          "reuse" "100% - protocol agnostic"
          "effort" "0 weeks"
          "features" "Symbol storage, FTS5 search, persistence"
        }
        
        # Level 3: Storage Components
        sqlite_store = component "SQLite Store" {
          description "Main persistence layer"
          technology "Python, SQLite"
          tags "Reusable" "AsIs"
          properties {
            "current" "sqlite_store.py implementation"
            "reuse" "100% - protocol agnostic"
            "features" "Symbol storage, file tracking"
          }
        }
        
        fts_engine = component "FTS5 Engine" {
          description "Full-text search engine"
          technology "SQLite FTS5"
          tags "Reusable" "AsIs"
          properties {
            "current" "Integrated in SQLite"
            "reuse" "100% - works perfectly"
          }
        }
        
        query_builder = component "Query Builder" {
          description "SQL query construction"
          technology "Python"
          tags "Reusable" "AsIs"
          properties {
            "current" "Part of sqlite_store"
            "reuse" "100% - well abstracted"
          }
        }
      }
      
      indexer = container "Index Engine" {
        description "Code parsing and indexing engine"
        technology "Python, Tree-sitter"
        tags "Reusable" "MinorChanges"
        properties {
          "reuse" "95% - add progress notifications"
          "effort" "3 days"
          "components" "Fuzzy indexer, Semantic indexer"
        }
        
        # Level 3: Indexer Components
        index_coordinator = component "Index Coordinator" {
          description "Coordinates indexing operations"
          technology "Python"
          tags "Reusable" "MinorChanges"
          properties {
            "changes" "Add progress reporting"
            "effort" "1 day"
          }
        }
        
        fuzzy_indexer = component "Fuzzy Indexer" {
          description "Fuzzy search implementation"
          technology "Python"
          tags "Reusable" "AsIs"
          properties {
            "current" "fuzzy_indexer.py"
            "reuse" "100% - works as-is"
          }
        }
        
        semantic_indexer = component "Semantic Indexer" {
          description "Vector-based semantic search"
          technology "Python, Voyage AI"
          tags "Reusable" "AsIs"
          properties {
            "current" "semantic_indexer.py"
            "reuse" "100% - works as-is"
          }
        }
      }
      
      file_watcher = container "File Watcher" {
        description "Monitors file system for changes"
        technology "Python, Watchdog"
        tags "Reusable" "Modify"
        properties {
          "reuse" "90% - add MCP notifications"
          "effort" "2 days"
          "current" "Watchdog-based monitoring"
        }
        
        # Level 3: File Watcher Components
        watchdog_monitor = component "Watchdog Monitor" {
          description "File system event monitoring"
          technology "Python, Watchdog"
          tags "Reusable" "AsIs"
          properties {
            "current" "watcher.py implementation"
            "reuse" "100% - event generation works"
          }
        }
        
        change_notifier = component "Change Notifier" {
          description "Notifies subscribers of file changes"
          technology "Python"
          tags "Reusable" "Enhance"
          properties {
            "current" "Basic notifications"
            "enhance" "Add MCP resource notifications"
          }
        }
      }
      
      # LANGUAGE PLUGINS (All fully reusable)
      
      python_plugin = container "Python Plugin" {
        description "Python code analysis with Tree-sitter and Jedi"
        technology "Python, Tree-sitter, Jedi"
        tags "Reusable" "AsIs" "Plugin"
        properties {
          "reuse" "100% - implements IPlugin"
          "features" "Type inference, imports, docstrings"
        }
        
        # Level 3: Python Plugin Components
        python_analyzer = component "Python Analyzer" {
          description "Python code analysis engine"
          technology "Python, Tree-sitter, Jedi"
          tags "Reusable" "AsIs" "Plugin"
          properties {
            "current" "Fully implemented"
            "reuse" "100% - implements IPlugin"
          }
        }
      }
      
      js_plugin = container "JavaScript Plugin" {
        description "JavaScript/TypeScript analysis"
        technology "Python, Tree-sitter"
        tags "Reusable" "AsIs" "Plugin"
        properties {
          "reuse" "100% - implements IPlugin"
          "features" "ES6+, JSX, TypeScript"
        }
        
        # Level 3: JS Plugin Components
        js_analyzer = component "JavaScript Analyzer" {
          description "JS/TS code analysis engine"
          technology "Python, Tree-sitter"
          tags "Reusable" "AsIs" "Plugin"
          properties {
            "current" "Fully implemented"
            "reuse" "100% - implements IPlugin"
          }
        }
      }
      
      c_plugin = container "C Plugin" {
        description "C code analysis"
        technology "Python, Tree-sitter"
        tags "Reusable" "AsIs" "Plugin"
        properties {
          "reuse" "100% - implements IPlugin"
          "features" "Functions, structs, macros"
        }
        
        # Level 3: C Plugin Components
        c_analyzer = component "C Analyzer" {
          description "C code analysis engine"
          technology "Python, Tree-sitter"
          tags "Reusable" "AsIs" "Plugin"
          properties {
            "current" "Fully implemented"
            "reuse" "100% - implements IPlugin"
          }
        }
      }
      
      cpp_plugin = container "C++ Plugin" {
        description "C++ code analysis"
        technology "Python, Tree-sitter"
        tags "Reusable" "AsIs" "Plugin"
        properties {
          "reuse" "100% - implements IPlugin"
          "features" "Classes, templates, namespaces"
        }
      }
      
      dart_plugin = container "Dart Plugin" {
        description "Dart/Flutter code analysis"
        technology "Python, Regex"
        tags "Reusable" "AsIs" "Plugin"
        properties {
          "reuse" "100% - implements IPlugin"
          "features" "Classes, functions, Flutter widgets"
        }
      }
      
      html_css_plugin = container "HTML/CSS Plugin" {
        description "Web markup and styles analysis"
        technology "Python, Tree-sitter"
        tags "Reusable" "AsIs" "Plugin"
        properties {
          "reuse" "100% - implements IPlugin"
          "features" "Selectors, properties, HTML structure"
        }
      }
      
      # PHASE 5 LANGUAGE PLUGINS (Planned Q2 2025)
      
      rust_plugin = container "Rust Plugin" {
        description "Rust code analysis with advanced type inference"
        technology "Python, Tree-sitter, rust-analyzer"
        tags "Future" "Plugin" "Phase5"
        properties {
          "status" "Planned Q2 2025"
          "effort" "6 weeks"
          "features" "Traits, lifetimes, unsafe blocks, procedural macros"
          "integration" "Cargo.toml dependency analysis"
        }
      }
      
      go_plugin = container "Go Plugin" {
        description "Go code analysis with modules support"
        technology "Python, Tree-sitter, gopls"
        tags "Future" "Plugin" "Phase5"
        properties {
          "status" "Planned Q2 2025"
          "effort" "4 weeks"
          "features" "Interfaces, goroutines, channels, generics"
          "integration" "go.mod dependency tracking"
        }
      }
      
      jvm_plugin = container "JVM Plugin" {
        description "Java/Kotlin unified language support"
        technology "Python, Tree-sitter, Eclipse JDT"
        tags "Future" "Plugin" "Phase5"
        properties {
          "status" "Planned Q2 2025"
          "effort" "6 weeks"
          "features" "Annotations, generics, coroutines, null safety"
          "integration" "Maven/Gradle project analysis"
        }
      }
      
      ruby_plugin = container "Ruby Plugin" {
        description "Ruby code analysis with metaprogramming support"
        technology "Python, Tree-sitter"
        tags "Future" "Plugin" "Phase5"
        properties {
          "status" "Planned Q2 2025"
          "effort" "4 weeks"
          "features" "Dynamic methods, DSLs, mixins"
          "integration" "Rails framework detection"
        }
      }
      
      php_plugin = container "PHP Plugin" {
        description "PHP code analysis with modern features"
        technology "Python, Tree-sitter"
        tags "Future" "Plugin" "Phase5"
        properties {
          "status" "Planned Q2 2025"
          "effort" "4 weeks"
          "features" "Namespaces, traits, attributes"
          "integration" "Laravel framework detection"
        }
      }
      
      # OPTIONAL REUSABLE CONTAINERS
      
      semantic_indexer_service = container "Semantic Indexer Service" {
        description "AI-powered semantic search with Voyage AI embeddings"
        technology "Python, Voyage AI, Qdrant"
        tags "Reusable" "AsIs" "Optional"
        properties {
          "reuse" "100% - works as-is"
          "integration" "Called by indexer"
          "embedding_model" "voyage-code-3 for code understanding"
          "vector_store" "Qdrant for scalable similarity search"
        }
      }
      
      # PHASE 5 PERFORMANCE CONTAINERS (Planned Q3 2025)
      
      distributed_processor = container "Distributed Processor" {
        description "Multi-node indexing orchestration"
        technology "Python, Redis, Celery"
        tags "Future" "Performance" "Phase5"
        properties {
          "status" "Planned Q3 2025"
          "effort" "6 weeks"
          "features" "Master-worker pattern, work queue, fault tolerance"
          "scalability" "10+ worker nodes, 100K files/min"
        }
      }
      
      advanced_cache = container "Advanced Cache" {
        description "Multi-tier intelligent caching system"
        technology "Python, Redis, LRU"
        tags "Future" "Performance" "Phase5"
        properties {
          "status" "Planned Q3 2025"
          "effort" "4 weeks"
          "features" "L1/L2/L3 cache, predictive warming, smart invalidation"
          "performance" "90% hit rate, <10ms cached response"
        }
      }
      
      gpu_accelerator = container "GPU Accelerator" {
        description "GPU-accelerated processing for embeddings"
        technology "Python, CUDA, Metal"
        tags "Future" "Performance" "Phase5"
        properties {
          "status" "Planned Q3 2025"
          "effort" "4 weeks"
          "features" "CUDA/Metal support, batch processing, CPU fallback"
          "performance" "5-10x speedup for semantic operations"
        }
      }
      
      vector_search_engine = container "Enhanced Vector Search" {
        description "Voyage AI embeddings with Qdrant vector search"
        technology "Python, Voyage AI, Qdrant"
        tags "Future" "Performance" "Phase5"
        properties {
          "status" "Planned Q3 2025"
          "effort" "4 weeks"
          "features" "voyage-code-3 model, batch API, flexible dimensions"
          "performance" "50% faster embeddings, 1M+ symbol support"
        }
      }
    }
    
    # External dependencies (reusable)
    repo = softwareSystem "Local Code Repository" {
      description "The developer's local codebase being indexed and analyzed"
      tags "External" "Reusable"
      properties {
        "integration" "File system access"
        "monitoring" "Watchdog for changes"
      }
    }
    
    # Optional external systems
    embedding_service = softwareSystem "Embedding Service" {
      description "Optional AI embeddings for semantic search (Voyage AI)"
      tags "External" "Optional" "Reusable"
      properties {
        "current.usage" "Semantic indexer"
        "integration" "REST API"
      }
    }
    
    vector_db = softwareSystem "Vector Database" {
      description "Optional vector storage for semantic search (Qdrant)"
      tags "External" "Optional" "Reusable"
      properties {
        "current.usage" "Semantic search"
        "integration" "gRPC/REST"
      }
    }
    
    # Future optional systems
    monitoring = softwareSystem "Monitoring System" {
      description "Metrics and observability (Prometheus/Grafana)"
      tags "External" "Future"
      properties {
        "implementation.status" "not_implemented"
        "priority" "phase_4"
      }
    }
    
    # ====================
    # RELATIONSHIPS
    # ====================
    
    # Level 1: System relationships
    user -> llm "requests code assistance"
    llm -> mcp_server "MCP protocol (JSON-RPC 2.0)" {
      tags "Primary"
      properties {
        "transport" "WebSocket or stdio"
        "methods" "initialize, resources/*, tools/*, prompts/*"
      }
    }
    
    mcp_server -> repo "indexes and monitors" {
      properties {
        "operations" "read files, watch changes"
      }
    }
    
    mcp_server -> embedding_service "generates embeddings" {
      tags "Optional"
      properties {
        "current.implementation" "Via semantic indexer"
      }
    }
    
    mcp_server -> vector_db "stores/queries vectors" {
      tags "Optional"
      properties {
        "current.implementation" "Via semantic indexer"
      }
    }
    
    mcp_server -> monitoring "reports metrics" {
      tags "Future"
    }
    
    # Level 2: Container relationships
    
    # MCP Protocol Flow
    llm -> transport_layer "JSON-RPC 2.0 messages"
    transport_layer -> protocol_handler "delivers messages"
    protocol_handler -> session_manager "manages sessions"
    
    # Method routing
    protocol_handler -> resource_manager "resources/* methods"
    protocol_handler -> tool_manager "tools/* methods"
    protocol_handler -> prompt_manager "prompts/* methods"
    
    # Resource/Tool to existing components
    resource_manager -> storage "queries indexed data"
    resource_manager -> dispatcher "gets symbols/files"
    tool_manager -> dispatcher "executes operations"
    
    # Existing component relationships (unchanged)
    dispatcher -> plugin_system "routes to plugins"
    plugin_system -> python_plugin "manages"
    plugin_system -> js_plugin "manages"
    plugin_system -> c_plugin "manages"
    plugin_system -> cpp_plugin "manages"
    plugin_system -> dart_plugin "manages"
    plugin_system -> html_css_plugin "manages"
    
    # Phase 5 plugin relationships
    plugin_system -> rust_plugin "will manage" {
      tags "Future"
    }
    plugin_system -> go_plugin "will manage" {
      tags "Future"
    }
    plugin_system -> jvm_plugin "will manage" {
      tags "Future"
    }
    plugin_system -> ruby_plugin "will manage" {
      tags "Future"
    }
    plugin_system -> php_plugin "will manage" {
      tags "Future"
    }
    
    # Plugin operations
    python_plugin -> storage "stores symbols"
    js_plugin -> storage "stores symbols"
    c_plugin -> storage "stores symbols"
    cpp_plugin -> storage "stores symbols"
    dart_plugin -> storage "stores symbols"
    html_css_plugin -> storage "stores symbols"
    
    # Phase 5 storage relationships
    rust_plugin -> storage "will store symbols" {
      tags "Future"
    }
    go_plugin -> storage "will store symbols" {
      tags "Future"
    }
    jvm_plugin -> storage "will store symbols" {
      tags "Future"
    }
    ruby_plugin -> storage "will store symbols" {
      tags "Future"
    }
    php_plugin -> storage "will store symbols" {
      tags "Future"
    }
    
    # Indexing flow
    indexer -> storage "persists indices"
    indexer -> semantic_indexer_service "semantic search"
    dispatcher -> indexer "triggers indexing"
    
    # Phase 5 performance relationships
    indexer -> distributed_processor "will distribute work" {
      tags "Future"
    }
    distributed_processor -> storage "will persist results" {
      tags "Future"
    }
    dispatcher -> advanced_cache "will use caching" {
      tags "Future"
    }
    advanced_cache -> storage "will cache queries" {
      tags "Future"
    }
    semantic_indexer_service -> gpu_accelerator "will accelerate" {
      tags "Future"
    }
    indexer -> vector_search_engine "will enhance search" {
      tags "Future"
    }
    vector_search_engine -> gpu_accelerator "will use GPU" {
      tags "Future"
    }
    
    # File monitoring
    file_watcher -> repo "monitors changes"
    file_watcher -> indexer "triggers reindex"
    file_watcher -> resource_manager "notifies changes"
    
    # Level 3: Component relationships
    
    # MCP Protocol flow
    jsonrpc_handler -> method_router "parsed requests"
    method_router -> capability_negotiator "initialize"
    method_router -> resource_registry "resources/*"
    method_router -> tool_registry "tools/*"
    
    # Transport flow
    websocket_server -> transport_abstraction "implements"
    stdio_handler -> transport_abstraction "implements"
    transport_abstraction -> jsonrpc_handler "delivers messages"
    
    # Session management
    jsonrpc_handler -> session_store "session lookup"
    session_lifecycle -> session_store "updates state"
    capability_negotiator -> client_registry "registers capabilities"
    
    # Resource handling
    resource_registry -> file_resource_handler "file resources"
    resource_registry -> symbol_resource_handler "symbol resources"
    resource_registry -> search_resource_handler "search resources"
    
    file_resource_handler -> sqlite_store "queries files"
    symbol_resource_handler -> dispatcher_core "lookup symbols"
    search_resource_handler -> dispatcher_core "search code"
    
    subscription_manager -> change_notifier "subscribes"
    
    # Tool handling
    tool_registry -> search_tool "search_code"
    tool_registry -> symbol_lookup_tool "lookup_symbol"
    tool_registry -> reference_finder_tool "find_references"
    tool_registry -> indexing_tool "index_file"
    
    search_tool -> dispatcher_core "calls search()"
    symbol_lookup_tool -> dispatcher_core "calls lookup()"
    reference_finder_tool -> dispatcher_core "calls find_references()"
    indexing_tool -> index_coordinator "triggers indexing"
    
    tool_validator -> tool_registry "validates inputs"
    
    # Existing component relationships (unchanged)
    dispatcher_core -> plugin_router "routes requests"
    plugin_router -> plugin_manager "gets plugins"
    dispatcher_core -> result_aggregator "combines results"
    dispatcher_core -> dispatcher_cache "caches results"
    
    plugin_manager -> plugin_base "manages plugins"
    python_analyzer -> treesitter_wrapper "parses code"
    js_analyzer -> treesitter_wrapper "parses code"
    c_analyzer -> treesitter_wrapper "parses code"
    
    index_coordinator -> fuzzy_indexer "fuzzy search"
    index_coordinator -> semantic_indexer "semantic search"
    
    python_analyzer -> sqlite_store "stores symbols"
    js_analyzer -> sqlite_store "stores symbols"
    c_analyzer -> sqlite_store "stores symbols"
    
    sqlite_store -> fts_engine "full-text search"
    sqlite_store -> query_builder "builds queries"
    
    watchdog_monitor -> change_notifier "file events"
  }
  
  views { 
    # Level 1: System Context
    systemContext mcp_server "MCPSystemContext" {
      include *
      autoLayout lr
      title "Code-Index Native MCP Server - System Context"
      description "Shows how the MCP server integrates with AI assistants via the Model Context Protocol"
    }
    
    # Level 2: Container View
    container mcp_server "MCPContainers" {
      include *
      autoLayout lr
      title "Native MCP Server Container Architecture"
      description "Shows MCP protocol containers and reusable components from existing codebase"
    }
    
    # Level 3: Component Views
    component protocol_handler "ProtocolComponents" {
      include *
      autoLayout lr
      title "MCP Protocol Handler Components"
      description "New components for JSON-RPC 2.0 protocol handling"
    }
    
    component resource_manager "ResourceComponents" {
      include *
      autoLayout lr
      title "Resource Manager Components"
      description "MCP resource handlers wrapping existing functionality"
    }
    
    component tool_manager "ToolComponents" {
      include *
      autoLayout lr
      title "Tool Manager Components"
      description "MCP tools exposing existing operations"
    }
    
    component dispatcher "DispatcherComponents" {
      include *
      autoLayout lr
      title "Dispatcher Components (Reusable)"
      description "Existing dispatcher components to be modified"
    }
    
    component storage "StorageComponents" {
      include *
      autoLayout lr
      title "Storage Components (100% Reusable)"
      description "Protocol-agnostic storage layer"
    }
    
    # Combined view showing all levels
    systemLandscape "CompleteArchitecture" {
      include *
      autoLayout lr
      title "Complete MCP Server Architecture"
      description "All levels of the Code-Index MCP server architecture"
    }
    
    # Style definitions
    styles {
      # Basic element styles
      element "Person" {
        background #08427b
        color #ffffff
        shape Person
      }
      
      element "Software System" {
        background #1168bd
        color #ffffff
      }
      
      element "Container" {
        background #438dd5
        color #ffffff
      }
      
      element "Component" {
        background #85bbf0
        color #000000
        shape Component
      }
      
      # Tag-based styles
      element "CoreSystem" {
        background #1168bd
        color #ffffff
        shape RoundedBox
      }
      
      element "MCPNative" {
        background #2E86AB
        color #ffffff
      }
      
      element "MCPClient" {
        background #A23B72
        color #ffffff
        shape Person
      }
      
      element "External" {
        background #999999
        color #ffffff
      }
      
      element "Core" {
        background #1168bd
        color #ffffff
      }
      
      element "New" {
        background #E74C3C
        color #ffffff
      }
      
      element "Required" {
        background #E74C3C
        color #ffffff
      }
      
      element "Reusable" {
        background #27AE60
        color #ffffff
      }
      
      element "AsIs" {
        background #27AE60
        color #ffffff
      }
      
      element "Modify" {
        background #F39C12
        color #ffffff
      }
      
      element "MinorChanges" {
        background #F1C40F
        color #000000
      }
      
      element "Enhance" {
        background #E67E22
        color #ffffff
      }
      
      element "Adapter" {
        background #9B59B6
        color #ffffff
      }
      
      element "Interface" {
        background #3498DB
        color #ffffff
      }
      
      element "Plugin" {
        background #2ECC71
        color #ffffff
      }
      
      element "Database" {
        background #438dd5
        color #ffffff
        shape Cylinder
      }
      
      element "Optional" {
        background #95A5A6
        color #ffffff
        stroke #95A5A6
      }
      
      element "Future" {
        background #ECF0F1
        color #7F8C8D
        stroke #BDC3C7
      }
      
      element "Phase5" {
        background #3498DB
        color #ffffff
        stroke #2980B9
        strokeWidth 2
      }
      
      element "Performance" {
        background #E67E22
        color #ffffff
      }
      
      element "Primary" {
        background #E74C3C
        color #ffffff
      }
      
      element "Advanced" {
        stroke #999999
        strokeWidth 2
      }
      
      # Relationship styles
      relationship "Relationship" {
        thickness 2
        color #666666
      }
      
      relationship "Primary" {
        thickness 3
        color #E74C3C
        style solid
      }
      
      relationship "Optional" {
        thickness 2
        color #95A5A6
        style dashed
      }
      
      relationship "Future" {
        thickness 1
        color #BDC3C7
        style dotted
      }
    }
    
    themes default
  }
}