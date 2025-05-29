workspace "MCP Server – Level 3" {
  description "Component diagram showing the detailed internal components of the MCP Server"
  
  properties {
    "structurizr.dslEditor" "false"
  }

  model {
    mcp = softwareSystem "MCP Server" {
      api = container "API Gateway" {
        gateway = component "Gateway Controller" {
          description "FastAPI controllers and endpoints"
          technology "Python, FastAPI"
          tags "Controller"
        }
        
        auth = component "Auth Middleware" {
          description "Authentication and authorization"
          technology "Python, JWT"
        }
        
        validator = component "Request Validator" {
          description "Input validation and sanitization"
          technology "Python, Pydantic"
        }
      }
      
      dispatcher = container "Dispatcher" {
        core = component "Dispatcher Core" {
          description "Request routing logic"
          technology "Python"
        }
        
        router = component "Plugin Router" {
          description "Routes to appropriate plugin by file type"
          technology "Python"
        }
        
        aggregator = component "Result Aggregator" {
          description "Combines results from multiple plugins"
          technology "Python"
        }
      }
      
      plugin_system = container "Plugin System" {
        base = component "Plugin Base" {
          description "Abstract interface for all plugins"
          technology "Python, ABC"
        }
        
        registry = component "Plugin Registry" {
          description "Dynamic plugin discovery and registration"
          technology "Python"
        }
        
        manager = component "Plugin Manager" {
          description "Plugin lifecycle management"
          technology "Python"
        }
        
        loader = component "Plugin Loader" {
          description "Dynamic plugin loading"
          technology "Python, importlib"
        }
      }
      
      indexer = container "Index Manager" {
        index_engine = component "Index Engine" {
          description "Core indexing logic"
          technology "Python"
        }
        
        parser = component "Parser Coordinator" {
          description "Coordinates parsing across plugins"
          technology "Python"
        }
        
        optimizer = component "Query Optimizer" {
          description "Optimizes search queries"
          technology "Python"
        }
      }
      
      # Language plugins
      python_plugin = component "Python Plugin" {
        description "Python code analysis"
        technology "Python, Tree-sitter, Jedi"
        tags "Plugin"
      }
      
      cpp_plugin = component "C++ Plugin" {
        description "C++ code analysis with template support"
        technology "Python, Tree-sitter, Clang"
        tags "Plugin"
      }
      
      js_plugin = component "JavaScript Plugin" {
        description "JS/TS code analysis"
        technology "Python, Tree-sitter, TypeScript"
        tags "Plugin"
      }
      
      c_plugin = component "C Plugin" {
        description "C code analysis"
        technology "Python, Tree-sitter"
        tags "Plugin"
      }
      
      dart_plugin = component "Dart Plugin" {
        description "Dart/Flutter code analysis"
        technology "Python, Tree-sitter"
        tags "Plugin"
      }
      
      html_css_plugin = component "HTML/CSS Plugin" {
        description "Web markup and styles analysis"
        technology "Python, Tree-sitter"
        tags "Plugin"
      }
      
      # Utilities
      treesitter_wrapper = component "TreeSitter Wrapper" {
        description "Unified tree-sitter interface"
        technology "Python, tree-sitter"
      }
      
      fuzzy_indexer = component "Fuzzy Indexer" {
        description "Fuzzy search implementation"
        technology "Python"
      }
      
      semantic_indexer = component "Semantic Indexer" {
        description "Semantic search with embeddings"
        technology "Python, Voyage AI"
      }
      
      # Operational components
      watcher_engine = component "Watcher Engine" {
        description "File system monitoring"
        technology "Python, Watchdog"
      }
      
      cache_manager = component "Cache Manager" {
        description "Cache coordination"
        technology "Python, Redis"
      }
      
      metrics = component "Metrics Engine" {
        description "Performance metrics collection"
        technology "Python, Prometheus"
      }
      
      config_loader = component "Config Loader" {
        description "Configuration management"
        technology "Python, YAML"
      }
    }

    # Component relationships
    gateway -> auth "authenticates"
    gateway -> validator "validates"
    gateway -> core "delegates"
    
    core -> router "routes"
    router -> registry "finds plugins"
    core -> aggregator "aggregates results"
    
    registry -> loader "loads plugins"
    manager -> base "manages"
    manager -> python_plugin "manages"
    manager -> cpp_plugin "manages"
    manager -> js_plugin "manages"
    manager -> c_plugin "manages"
    manager -> dart_plugin "manages"
    manager -> html_css_plugin "manages"
    
    python_plugin -> treesitter_wrapper "parses"
    cpp_plugin -> treesitter_wrapper "parses"
    js_plugin -> treesitter_wrapper "parses"
    c_plugin -> treesitter_wrapper "parses"
    dart_plugin -> treesitter_wrapper "parses"
    html_css_plugin -> treesitter_wrapper "parses"
    
    index_engine -> parser "coordinates parsing"
    index_engine -> fuzzy_indexer "indexes"
    index_engine -> semantic_indexer "embeddings"
    
    parser -> manager "requests plugins"
    optimizer -> cache_manager "caches"
    
    watcher_engine -> index_engine "triggers reindex"
    metrics -> gateway "monitors"
    config_loader -> manager "configures"
  }
  
  views { 
    component plugin_system "PluginComponents" {
      include base registry manager loader python_plugin cpp_plugin js_plugin
      autolayout lr
      description "Plugin system component architecture"
    }
    
    component api "APIComponents" {
      include gateway auth validator core router aggregator
      autolayout lr
      description "API Gateway component architecture"
    }
    
    component indexer "IndexerComponents" {
      include index_engine parser optimizer fuzzy_indexer semantic_indexer
      autolayout lr
      description "Indexer component architecture"
    }
  }
  
  styles {
    element "Controller" {
      shape Component
    }
    element "Plugin" {
      shape Component
    }
  }
}
