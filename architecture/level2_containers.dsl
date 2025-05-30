workspace "MCP Server – Level 2" {
  description "Container diagram showing the internal architecture of the MCP Server"
  
  properties {
    "structurizr.dslEditor" "false"
    "implementation.status" "prototype"
    "implementation.coverage" "65%"
  }

  model {
    mcp = softwareSystem "MCP Server" {
      # Core containers
      api = container "API Gateway" {
        description "REST API endpoint for MCP tools"
        technology "FastAPI, Python"
        tags "Web API" "PartiallyImplemented"
        properties {
          "implementation.status" "partial"
          "implementation.notes" "Basic endpoints only. No auth, validation, or health checks."
        }
      }
      
      dispatcher = container "Dispatcher" {
        description "Routes requests to appropriate handlers"
        technology "Python"
        tags "Implemented"
        properties {
          "implementation.status" "implemented"
          "implementation.notes" "Basic routing by file extension. No advanced features."
        }
      }
      
      indexer = container "Index Manager" {
        description "Manages code indexing operations"
        technology "Python, Tree-sitter"
        tags "PartiallyImplemented"
        properties {
          "implementation.status" "partial"
          "implementation.notes" "Fuzzy and semantic indexers work. No coordinating engine."
        }
      }
      
      store = container "Local Index Store" {
        description "Persistent storage for code indices"
        technology "SQLite, FTS5"
        tags "Database" "Implemented"
        properties {
          "implementation.status" "implemented"
          "implementation.notes" "Full SQLite implementation with FTS5 and trigram search."
        }
      }
      
      # Cloud integration
      sync = container "Cloud Sync" {
        description "Optional cloud synchronization"
        technology "Python, gRPC"
        tags "Stub"
        properties {
          "implementation.status" "stub"
          "implementation.notes" "Empty methods only."
        }
      }
      
      embed = container "Embedding Service" {
        description "Semantic code understanding"
        technology "Voyage AI, Qdrant"
        tags "PartiallyImplemented"
        properties {
          "implementation.status" "partial"
          "implementation.notes" "Works via semantic indexer. No separate service."
        }
      }
      
      # Graph storage
      graph_store = container "Graph Store" {
        description "Graph database for code relationships and context analysis"
        technology "Memgraph, Cypher"
        tags "Database" "NotImplemented"
        properties {
          "implementation.status" "not_implemented"
        }
      }
      
      # Plugin architecture
      plugin_system = container "Plugin System" {
        description "Manages language-specific plugins"
        technology "Python"
        tags "PartiallyImplemented"
        properties {
          "implementation.status" "partial"
          "implementation.notes" "IPlugin interface implemented. No management features."
        }
      }
      
      plugin_registry = container "Plugin Registry" {
        description "Dynamic plugin discovery and registration"
        technology "Python"
        tags "NotImplemented"
        properties {
          "implementation.status" "not_implemented"
          "implementation.notes" "Hardcoded plugin list only."
        }
      }
      
      # Operational containers
      watcher = container "File Watcher" {
        description "Monitors file system changes"
        technology "Python, Watchdog"
        tags "PartiallyImplemented"
        properties {
          "implementation.status" "partial"
          "implementation.notes" "Watches files but doesn't trigger indexing."
        }
      }
      
      cache = container "Cache Layer" {
        description "Performance optimization cache"
        technology "Redis/In-memory"
        tags "Cache" "NotImplemented"
        properties {
          "implementation.status" "not_implemented"
        }
      }
      
      config = container "Configuration Service" {
        description "Dynamic configuration management"
        technology "Python, YAML"
        tags "NotImplemented"
        properties {
          "implementation.status" "not_implemented"
        }
      }
      
      monitor = container "Metrics Collector" {
        description "Collects performance and usage metrics"
        technology "Prometheus, OpenTelemetry"
        tags "NotImplemented"
        properties {
          "implementation.status" "not_implemented"
        }
      }
      
      security = container "Security Manager" {
        description "Access control and validation"
        technology "Python"
        tags "NotImplemented"
        properties {
          "implementation.status" "not_implemented"
        }
      }
      
      queue = container "Task Queue" {
        description "Async task processing"
        technology "Celery, Redis"
        tags "Queue" "NotImplemented"
        properties {
          "implementation.status" "not_implemented"
        }
      }
      
      # Language Plugin Containers
      python_plugin = container "Python Plugin" {
        description "Python code analysis with Jedi"
        technology "Python, Tree-sitter, Jedi"
        tags "Plugin" "Implemented"
        properties {
          "implementation.status" "implemented"
          "implementation.notes" "Full implementation with Jedi and tree-sitter."
        }
      }
      
      cpp_plugin = container "C++ Plugin" {
        description "C++ code analysis"
        technology "Python, Tree-sitter"
        tags "Plugin" "Stub"
        properties {
          "implementation.status" "stub"
        }
      }
      
      js_plugin = container "JavaScript Plugin" {
        description "JavaScript/TypeScript analysis"
        technology "Python, Tree-sitter"
        tags "Plugin" "Implemented"
        properties {
          "implementation.status" "implemented"
          "implementation.notes" "Full implementation with JS/TS/JSX/TSX support and Tree-sitter."
        }
      }
      
      c_plugin = container "C Plugin" {
        description "C code analysis"
        technology "Python, Tree-sitter"
        tags "Plugin" "Implemented"
        properties {
          "implementation.status" "implemented"
          "implementation.notes" "Full implementation with functions, structs, enums, typedefs, macros."
        }
      }
      
      dart_plugin = container "Dart Plugin" {
        description "Dart/Flutter code analysis"
        technology "Python, Tree-sitter"
        tags "Plugin" "Stub"
        properties {
          "implementation.status" "stub"
        }
      }
      
      html_css_plugin = container "HTML/CSS Plugin" {
        description "Web markup and styles analysis"
        technology "Python, Tree-sitter"
        tags "Plugin" "Stub"
        properties {
          "implementation.status" "stub"
        }
      }
    }

    # Container relationships
    api -> dispatcher "routes requests"
    api -> security "validates"
    api -> monitor "reports metrics"
    
    dispatcher -> plugin_system "delegates to plugins"
    dispatcher -> cache "checks cache"
    dispatcher -> store "queries indices"
    dispatcher -> graph_store "queries relationships"
    dispatcher -> embed "semantic search"
    dispatcher -> queue "queues tasks"
    
    plugin_system -> plugin_registry "discovers plugins"
    plugin_system -> indexer "triggers indexing"
    plugin_system -> python_plugin "manages"
    plugin_system -> cpp_plugin "manages"
    plugin_system -> js_plugin "manages"
    plugin_system -> c_plugin "manages"
    plugin_system -> dart_plugin "manages"
    plugin_system -> html_css_plugin "manages"
    
    indexer -> store "persists indices"
    indexer -> graph_store "stores relationships"
    indexer -> embed "generates embeddings"
    indexer -> cache "updates cache"
    
    watcher -> indexer "triggers reindex"
    watcher -> queue "queues changes"
    
    sync -> store "syncs data"
    sync -> cloud "communicates"
    
    config -> api "configures"
    config -> plugin_system "configures plugins"
    
    queue -> indexer "processes tasks"
    queue -> sync "sync tasks"
    
    security -> store "access control"
    security -> config "reads policies"
  }
  
  views { 
    container mcp "Containers" {
      include *
      autolayout lr
      description "Container diagram showing MCP Server internal architecture"
    }
  }
  
  styles {
    element "Database" {
      shape Cylinder
    }
    element "Cache" {
      shape Component
    }
    element "Queue" {
      shape Pipe
    }
    element "Web API" {
      shape WebBrowser
    }
    element "Implemented" {
      background #90EE90
    }
    element "PartiallyImplemented" {
      background #FFD700
    }
    element "Stub" {
      background #FFA500
    }
    element "NotImplemented" {
      background #FF6B6B
    }
    element "Plugin" {
      shape Component
    }
  }
}
