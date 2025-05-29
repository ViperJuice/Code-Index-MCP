workspace "MCP Server – Level 3 (Actual Implementation)" {
  description "Component diagram showing the ACTUAL implementation of the MCP Server"
  
  properties {
    "structurizr.dslEditor" "false"
    "implementation.status" "prototype"
    "implementation.coverage" "20%"
  }

  model {
    mcp = softwareSystem "MCP Server" {
      
      # ========================================
      # IMPLEMENTED Components
      # ========================================
      
      api = container "API Gateway" {
        gateway = component "Gateway Module" {
          description "Simple FastAPI app with 2 endpoints"
          technology "Python, FastAPI"
          tags "Implemented"
          properties {
            "actual_interface" "FastAPI endpoints only"
            "missing" "Auth, validation, health checks"
          }
        }
      }
      
      dispatcher = container "Dispatcher" {
        dispatcher_core = component "Dispatcher Class" {
          description "Basic plugin routing by file extension"
          technology "Python"
          tags "Implemented"
          properties {
            "actual_interface" "Simple class, no interfaces"
            "missing" "Router, aggregator components"
          }
        }
      }
      
      plugin_system = container "Plugin System" {
        plugin_base = component "IPlugin ABC" {
          description "Abstract base class for plugins"
          technology "Python, ABC"
          tags "Implemented"
          properties {
            "actual_interface" "IPlugin abstract class"
            "missing" "Registry, manager, loader"
          }
        }
      }
      
      python_plugin = container "Python Plugin" {
        python_analyzer = component "Python Plugin" {
          description "Jedi + Tree-sitter based Python analysis"
          technology "Python, Jedi, Tree-sitter"
          tags "Implemented"
          properties {
            "actual_interface" "Implements IPlugin"
            "features" "Pre-indexing, definition lookup"
          }
        }
      }
      
      indexer = container "Indexers" {
        fuzzy_indexer = component "Fuzzy Indexer" {
          description "In-memory substring search"
          technology "Python"
          tags "Implemented"
          properties {
            "actual_interface" "Simple class"
            "limitations" "No persistence, basic search"
          }
        }
        
        semantic_indexer = component "Semantic Indexer" {
          description "Voyage AI embeddings with Qdrant"
          technology "Python, Voyage AI, Qdrant"
          tags "Implemented"
          properties {
            "actual_interface" "Voyage + Qdrant integration"
            "features" "Vector search, embeddings"
          }
        }
      }
      
      utils = container "Utilities" {
        treesitter_wrapper = component "TreeSitter Wrapper" {
          description "Basic tree-sitter Python parser"
          technology "Python, tree-sitter"
          tags "Implemented"
          properties {
            "actual_interface" "Simple wrapper class"
            "limitations" "Python-only currently"
          }
        }
      }
      
      watcher = container "File Watcher" {
        watcher_engine = component "Watcher Class" {
          description "Watchdog-based file monitoring (TODO: indexing)"
          technology "Python, Watchdog"
          tags "Partial"
          properties {
            "actual_interface" "Basic observer pattern"
            "missing" "Actual indexing trigger"
          }
        }
      }
      
      # ========================================
      # STUB/EMPTY Components
      # ========================================
      
      sync = container "Cloud Sync" {
        sync_stub = component "CloudSync Stub" {
          description "Empty placeholder methods"
          technology "Python"
          tags "Stub"
          properties {
            "actual_interface" "Empty methods only"
            "status" "Not implemented"
          }
        }
      }
      
      cpp_plugin = container "C++ Plugin" {
        cpp_stub = component "C++ Plugin Stub" {
          description "Empty implementation"
          technology "Python"
          tags "Stub"
        }
      }
      
      js_plugin = container "JavaScript Plugin" {
        js_stub = component "JS Plugin Stub" {
          description "Empty implementation"
          technology "Python"
          tags "Stub"
        }
      }
      
      c_plugin = container "C Plugin" {
        c_stub = component "C Plugin Stub" {
          description "Empty implementation"
          technology "Python"
          tags "Stub"
        }
      }
      
      dart_plugin = container "Dart Plugin" {
        dart_stub = component "Dart Plugin Stub" {
          description "Empty implementation"
          technology "Python"
          tags "Stub"
        }
      }
      
      html_css_plugin = container "HTML/CSS Plugin" {
        html_css_stub = component "HTML/CSS Plugin Stub" {
          description "Empty implementation"
          technology "Python"
          tags "Stub"
        }
      }
      
      # ========================================
      # NOT IMPLEMENTED Components
      # ========================================
      
      graph_store = container "Graph Store" {
        not_implemented = component "Not Implemented" {
          description "Memgraph integration not built"
          tags "NotImplemented"
        }
      }
      
      cache = container "Cache Layer" {
        not_implemented = component "Not Implemented" {
          description "No caching layer"
          tags "NotImplemented"
        }
      }
      
      monitor = container "Metrics Collector" {
        not_implemented = component "Not Implemented" {
          description "No metrics collection"
          tags "NotImplemented"
        }
      }
      
      config = container "Configuration Service" {
        not_implemented = component "Not Implemented" {
          description "No configuration service"
          tags "NotImplemented"
        }
      }
      
      store = container "Local Index Store" {
        not_implemented = component "Not Implemented" {
          description "No SQLite/FTS5 implementation"
          tags "NotImplemented"
        }
      }
      
      embed = container "Embedding Service" {
        partial = component "Partial Implementation" {
          description "Embeddings in semantic indexer only"
          tags "Partial"
        }
      }
      
      security = container "Security Manager" {
        not_implemented = component "Not Implemented" {
          description "No security implementation"
          tags "NotImplemented"
        }
      }
      
      queue = container "Task Queue" {
        not_implemented = component "Not Implemented" {
          description "No task queue"
          tags "NotImplemented"
        }
      }
      
      plugin_registry = container "Plugin Registry" {
        not_implemented = component "Not Implemented" {
          description "Hardcoded plugin list only"
          tags "NotImplemented"
        }
      }
    }

    # Component relationships (actual)
    gateway -> dispatcher_core "directly calls"
    dispatcher_core -> python_analyzer "calls methods"
    dispatcher_core -> cpp_stub "would call"
    dispatcher_core -> js_stub "would call"
    
    python_analyzer -> fuzzy_indexer "uses for search"
    python_analyzer -> treesitter_wrapper "parses with"
    
    semantic_indexer -> treesitter_wrapper "parses with"
    
    watcher_engine -> dispatcher_core "TODO: trigger indexing"
  }
  
  views { 
    component mcp "ActualImplementation" {
      include *
      autolayout lr
      description "Actual implementation status of MCP Server components"
    }
  }
  
  styles {
    element "Implemented" {
      background #90EE90
    }
    element "Partial" {
      background #FFD700
    }
    element "Stub" {
      background #FFA500
    }
    element "NotImplemented" {
      background #FF6B6B
    }
  }
}