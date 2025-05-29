workspace "MCP Server – Level 2" {
  description "Container diagram showing the internal architecture of the MCP Server"
  
  properties {
    "structurizr.dslEditor" "false"
  }

  model {
    mcp = softwareSystem "MCP Server" {
      # Core containers
      api = container "API Gateway" {
        description "REST API endpoint for MCP tools"
        technology "FastAPI, Python"
        tags "Web API"
      }
      
      dispatcher = container "Dispatcher" {
        description "Routes requests to appropriate handlers"
        technology "Python"
      }
      
      indexer = container "Index Manager" {
        description "Manages code indexing operations"
        technology "Python, Tree-sitter"
      }
      
      store = container "Local Index Store" {
        description "Persistent storage for code indices"
        technology "SQLite, FTS5"
        tags "Database"
      }
      
      # Cloud integration
      sync = container "Cloud Sync" {
        description "Optional cloud synchronization"
        technology "Python, gRPC"
      }
      
      embed = container "Embedding Service" {
        description "Semantic code understanding"
        technology "Voyage AI, Qdrant"
      }
      
      # Graph storage
      graph_store = container "Graph Store" {
        description "Graph database for code relationships and context analysis"
        technology "Memgraph, Cypher"
        tags "Database"
      }
      
      # Plugin architecture
      plugin_system = container "Plugin System" {
        description "Manages language-specific plugins"
        technology "Python"
      }
      
      plugin_registry = container "Plugin Registry" {
        description "Dynamic plugin discovery and registration"
        technology "Python"
      }
      
      # Operational containers
      watcher = container "File Watcher" {
        description "Monitors file system changes"
        technology "Python, Watchdog"
      }
      
      cache = container "Cache Layer" {
        description "Performance optimization cache"
        technology "Redis/In-memory"
        tags "Cache"
      }
      
      config = container "Configuration Service" {
        description "Dynamic configuration management"
        technology "Python, YAML"
      }
      
      monitor = container "Metrics Collector" {
        description "Collects performance and usage metrics"
        technology "Prometheus, OpenTelemetry"
      }
      
      security = container "Security Manager" {
        description "Access control and validation"
        technology "Python"
      }
      
      queue = container "Task Queue" {
        description "Async task processing"
        technology "Celery, Redis"
        tags "Queue"
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
  }
}
