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
          properties {
            "interfaces" "IRequestHandler, IHealthCheck"
            "level4" "architecture/level4/api_gateway.puml"
          }
        }
        
        auth = component "Auth Middleware" {
          description "Authentication and authorization"
          technology "Python, JWT"
          properties {
            "interfaces" "IAuthenticator, IAuthorizer"
            "level4" "architecture/level4/api_gateway.puml"
          }
        }
        
        validator = component "Request Validator" {
          description "Input validation and sanitization"
          technology "Python, Pydantic"
          properties {
            "interfaces" "IRequestValidator, ISanitizer"
            "level4" "architecture/level4/api_gateway.puml"
          }
        }
      }
      
      dispatcher = container "Dispatcher" {
        core = component "Dispatcher Core" {
          description "Request routing logic"
          technology "Python"
          properties {
            "interfaces" "IDispatcher, IRequestRouter"
            "level4" "architecture/level4/dispatcher.puml"
          }
        }
        
        router = component "Plugin Router" {
          description "Routes to appropriate plugin by file type"
          technology "Python"
          properties {
            "interfaces" "IPluginRouter, IFileTypeMatcher"
            "level4" "architecture/level4/dispatcher.puml"
          }
        }
        
        aggregator = component "Result Aggregator" {
          description "Combines results from multiple plugins"
          technology "Python"
          properties {
            "interfaces" "IResultAggregator, IResultMerger"
            "level4" "architecture/level4/dispatcher.puml"
          }
        }
      }
      
      plugin_system = container "Plugin System" {
        base = component "Plugin Base" {
          description "Abstract interface for all plugins"
          technology "Python, ABC"
          properties {
            "interfaces" "IPlugin, ILanguageAnalyzer"
            "level4" "architecture/level4/plugin_system.puml"
          }
        }
        
        registry = component "Plugin Registry" {
          description "Dynamic plugin discovery and registration"
          technology "Python"
          properties {
            "interfaces" "IPluginRegistry, IPluginDiscovery"
            "level4" "architecture/level4/plugin_system.puml"
          }
        }
        
        manager = component "Plugin Manager" {
          description "Plugin lifecycle management"
          technology "Python"
          properties {
            "interfaces" "IPluginManager, ILifecycleManager"
            "level4" "architecture/level4/plugin_system.puml"
          }
        }
        
        loader = component "Plugin Loader" {
          description "Dynamic plugin loading"
          technology "Python, importlib"
          properties {
            "interfaces" "IPluginLoader, IModuleImporter"
            "level4" "architecture/level4/plugin_system.puml"
          }
        }
        
        treesitter_wrapper = component "TreeSitter Wrapper" {
          description "Unified tree-sitter interface"
          technology "Python, tree-sitter"
          properties {
            "interfaces" "ITreeSitterWrapper, IParserAdapter"
            "level4" "architecture/level4/shared_utilities.puml"
          }
        }
      }
      
      indexer = container "Index Manager" {
        index_engine = component "Index Engine" {
          description "Core indexing logic"
          technology "Python"
          properties {
            "interfaces" "IIndexEngine, IIndexCoordinator"
            "level4" "architecture/level4/indexer.puml"
          }
        }
        
        parser = component "Parser Coordinator" {
          description "Coordinates parsing across plugins"
          technology "Python"
          properties {
            "interfaces" "IParserCoordinator, IParseOrchestrator"
            "level4" "architecture/level4/indexer.puml"
          }
        }
        
        optimizer = component "Query Optimizer" {
          description "Optimizes search queries"
          technology "Python"
          properties {
            "interfaces" "IQueryOptimizer, ISearchPlanner"
            "level4" "architecture/level4/indexer.puml"
          }
        }
        
        fuzzy_indexer = component "Fuzzy Indexer" {
          description "Fuzzy search implementation"
          technology "Python"
          properties {
            "interfaces" "IFuzzyIndexer, ITrigramSearcher"
            "level4" "architecture/level4/indexer.puml"
          }
        }
        
        semantic_indexer = component "Semantic Indexer" {
          description "Semantic search with embeddings"
          technology "Python, Voyage AI"
          properties {
            "interfaces" "ISemanticIndexer, IEmbeddingGenerator"
            "level4" "architecture/level4/indexer.puml"
          }
        }
      }
      
      # Missing containers from Level 2
      graph_store = container "Graph Store" {
        graph_builder = component "Graph Builder" {
          description "Builds graph from parsed code"
          technology "Python"
          properties {
            "interfaces" "IGraphBuilder, INodeFactory"
            "level4" "architecture/level4/graph_store.puml"
          }
        }
        
        graph_analyzer = component "Graph Analyzer" {
          description "Code relationship analysis engine"
          technology "Python, GQLAlchemy"
          properties {
            "interfaces" "IGraphAnalyzer, IRelationshipAnalyzer"
            "level4" "architecture/level4/graph_store.puml"
          }
        }
        
        context_analyzer = component "Context Analyzer" {
          description "Code context extraction and analysis"
          technology "Python, Cypher"
          properties {
            "interfaces" "IContextAnalyzer, IContextExtractor"
            "level4" "architecture/level4/graph_store.puml"
          }
        }
      }
      
      watcher = container "File Watcher" {
        watcher_engine = component "Watcher Engine" {
          description "File system monitoring"
          technology "Python, Watchdog"
          properties {
            "interfaces" "IFileWatcher, IChangeNotifier"
            "level4" "architecture/level4/file_watcher.puml"
          }
        }
      }
      
      cache = container "Cache Layer" {
        cache_manager = component "Cache Manager" {
          description "Cache coordination"
          technology "Python, Redis"
          properties {
            "interfaces" "ICacheManager, ICacheCoordinator"
            "level4" "architecture/level4/cache.puml"
          }
        }
      }
      
      monitor = container "Metrics Collector" {
        metrics = component "Metrics Engine" {
          description "Performance metrics collection"
          technology "Python, Prometheus"
          properties {
            "interfaces" "IMetricsCollector, IMetricsExporter"
            "level4" "architecture/level4/monitoring.puml"
          }
        }
      }
      
      config = container "Configuration Service" {
        config_loader = component "Config Loader" {
          description "Configuration management"
          technology "Python, YAML"
          properties {
            "interfaces" "IConfigLoader, IConfigProvider"
            "level4" "architecture/level4/configuration.puml"
          }
        }
      }
      
      # Storage containers
      store = container "Local Index Store" {
        storage_engine = component "Storage Engine" {
          description "SQLite persistence layer"
          technology "Python, SQLite, FTS5"
          properties {
            "interfaces" "IStorageEngine, IQueryEngine"
            "level4" "architecture/level4/storage.puml"
          }
        }
        
        fts_engine = component "FTS Engine" {
          description "Full-text search engine"
          technology "SQLite FTS5"
          properties {
            "interfaces" "IFTSEngine, ITextSearcher"
            "level4" "architecture/level4/storage.puml"
          }
        }
      }
      
      # Cloud integration containers
      sync = container "Cloud Sync" {
        sync_engine = component "Sync Engine" {
          description "Cloud synchronization engine"
          technology "Python, gRPC"
          properties {
            "interfaces" "ISyncEngine, ICloudConnector"
            "level4" "architecture/level4/cloud_sync.puml"
          }
        }
        
        conflict_resolver = component "Conflict Resolver" {
          description "Sync conflict resolution"
          technology "Python"
          properties {
            "interfaces" "IConflictResolver, IMergeStrategy"
            "level4" "architecture/level4/cloud_sync.puml"
          }
        }
      }
      
      embed = container "Embedding Service" {
        embedding_generator = component "Embedding Generator" {
          description "Code embedding generation"
          technology "Python, Voyage AI"
          properties {
            "interfaces" "IEmbeddingGenerator, IVectorizer"
            "level4" "architecture/level4/embeddings.puml"
          }
        }
        
        vector_store = component "Vector Store" {
          description "Vector database interface"
          technology "Python, Qdrant"
          properties {
            "interfaces" "IVectorStore, ISimilaritySearcher"
            "level4" "architecture/level4/embeddings.puml"
          }
        }
      }
      
      # Operational containers
      security = container "Security Manager" {
        access_controller = component "Access Controller" {
          description "Access control and validation"
          technology "Python"
          properties {
            "interfaces" "IAccessController, IPermissionChecker"
            "level4" "architecture/level4/security.puml"
          }
        }
        
        policy_engine = component "Policy Engine" {
          description "Security policy enforcement"
          technology "Python"
          properties {
            "interfaces" "IPolicyEngine, IRuleEvaluator"
            "level4" "architecture/level4/security.puml"
          }
        }
      }
      
      queue = container "Task Queue" {
        queue_manager = component "Queue Manager" {
          description "Async task management"
          technology "Python, Celery"
          properties {
            "interfaces" "IQueueManager, ITaskScheduler"
            "level4" "architecture/level4/task_queue.puml"
          }
        }
        
        worker_pool = component "Worker Pool" {
          description "Task worker management"
          technology "Python, Celery"
          properties {
            "interfaces" "IWorkerPool, ITaskExecutor"
            "level4" "architecture/level4/task_queue.puml"
          }
        }
      }
      
      plugin_registry = container "Plugin Registry" {
        registry_store = component "Registry Store" {
          description "Plugin metadata storage"
          technology "Python"
          properties {
            "interfaces" "IRegistryStore, IPluginMetadata"
            "level4" "architecture/level4/plugin_registry.puml"
          }
        }
      }
      
      # Language Plugin containers - define as separate containers since Structurizr doesn't support nested components
      python_plugin = container "Python Plugin" {
        python_analyzer = component "Python Analyzer" {
          description "Python code analysis with Jedi"
          technology "Python, Tree-sitter, Jedi"
          tags "Plugin"
          properties {
            "interfaces" "IPythonPlugin, IPythonAnalyzer"
            "level4" "architecture/level4/python_plugin.puml"
          }
        }
      }
      
      cpp_plugin = container "C++ Plugin" {
        cpp_analyzer = component "C++ Analyzer" {
          description "C++ code analysis with template support"
          technology "Python, Tree-sitter, Clang"
          tags "Plugin"
          properties {
            "interfaces" "ICppPlugin, ITemplateAnalyzer"
            "level4" "architecture/level4/cpp_plugin.puml"
          }
        }
      }
      
      js_plugin = container "JavaScript Plugin" {
        js_analyzer = component "JavaScript Analyzer" {
          description "JS/TS code analysis"
          technology "Python, Tree-sitter, TypeScript"
          tags "Plugin"
          properties {
            "interfaces" "IJavaScriptPlugin, ITypeScriptAnalyzer"
            "level4" "architecture/level4/js_plugin.puml"
          }
        }
      }
      
      c_plugin = container "C Plugin" {
        c_analyzer = component "C Analyzer" {
          description "C code analysis"
          technology "Python, Tree-sitter"
          tags "Plugin"
          properties {
            "interfaces" "ICPlugin, IPreprocessorHandler"
            "level4" "architecture/level4/c_plugin.puml"
          }
        }
      }
      
      dart_plugin = container "Dart Plugin" {
        dart_analyzer = component "Dart Analyzer" {
          description "Dart/Flutter code analysis"
          technology "Python, Tree-sitter"
          tags "Plugin"
          properties {
            "interfaces" "IDartPlugin, IFlutterAnalyzer"
            "level4" "architecture/level4/dart_plugin.puml"
          }
        }
      }
      
      html_css_plugin = container "HTML/CSS Plugin" {
        html_css_analyzer = component "HTML/CSS Analyzer" {
          description "Web markup and styles analysis"
          technology "Python, Tree-sitter"
          tags "Plugin"
          properties {
            "interfaces" "IHtmlCssPlugin, ISelectorAnalyzer"
            "level4" "architecture/level4/html_css_plugin.puml"
          }
        }
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
    manager -> python_analyzer "manages"
    manager -> cpp_analyzer "manages"
    manager -> js_analyzer "manages"
    manager -> c_analyzer "manages"
    manager -> dart_analyzer "manages"
    manager -> html_css_analyzer "manages"
    
    python_analyzer -> treesitter_wrapper "parses"
    cpp_analyzer -> treesitter_wrapper "parses"
    js_analyzer -> treesitter_wrapper "parses"
    c_analyzer -> treesitter_wrapper "parses"
    dart_analyzer -> treesitter_wrapper "parses"
    html_css_analyzer -> treesitter_wrapper "parses"
    
    index_engine -> parser "coordinates parsing"
    index_engine -> fuzzy_indexer "indexes"
    index_engine -> semantic_indexer "embeddings"
    index_engine -> graph_builder "builds graph"
    
    graph_builder -> graph_analyzer "analyzes"
    graph_analyzer -> context_analyzer "extracts context"
    
    parser -> manager "requests plugins"
    parser -> graph_builder "sends AST data"
    
    core -> context_analyzer "queries context"
    optimizer -> cache_manager "caches"
    
    watcher_engine -> index_engine "triggers reindex"
    metrics -> gateway "monitors"
    config_loader -> manager "configures"
    
    # Storage relationships
    index_engine -> storage_engine "persists indices"
    storage_engine -> fts_engine "delegates search"
    core -> storage_engine "queries"
    
    # Cloud sync relationships
    sync_engine -> storage_engine "syncs data"
    sync_engine -> conflict_resolver "resolves conflicts"
    
    # Embedding relationships
    semantic_indexer -> embedding_generator "generates embeddings"
    embedding_generator -> vector_store "stores vectors"
    core -> vector_store "semantic search"
    
    # Security relationships
    gateway -> access_controller "checks access"
    access_controller -> policy_engine "evaluates policies"
    policy_engine -> config_loader "reads policies"
    
    # Task queue relationships
    watcher_engine -> queue_manager "queues changes"
    queue_manager -> worker_pool "executes tasks"
    worker_pool -> index_engine "processes tasks"
    worker_pool -> sync_engine "sync tasks"
    
    # Plugin registry relationships
    registry -> registry_store "persists metadata"
    loader -> registry_store "reads metadata"
  }
  
  views { 
    component plugin_system "PluginComponents" {
      include base registry manager loader treesitter_wrapper
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
    
    component graph_store "GraphComponents" {
      include graph_builder graph_analyzer context_analyzer
      autolayout lr
      description "Graph store component architecture"
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
