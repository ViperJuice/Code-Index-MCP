workspace "MCP Server – Level 1" {
  description "System context diagram showing the MCP Server's interactions with external systems and users"
  
  properties {
    "structurizr.dslEditor" "false"
    "implementation.status" "prototype"
    "implementation.coverage" "65%"
    "performance.symbolLookup" "<100ms"
    "performance.semanticSearch" "<500ms"
    "performance.indexing" "10K files/minute"
    "scalability.maxFiles" "1M+ files"
    "availability.target" "99.9%"
    "security.model" "Zero-trust, local-first"
  }

  model {
    user = person "Developer" {
      description "Software developer using Claude for code assistance"
    }
    
    llm = softwareSystem "Claude" {
      description "AI assistant with MCP tool capabilities"
    }
    
    mcp = softwareSystem "MCP Server" {
      description "Local-first code indexing system with deep language understanding and graph-based context analysis"
      tags "Core System" "PartiallyImplemented"
      properties {
        "implementation.status" "partial"
        "implementation.notes" "Basic indexing and search working. Missing graph analysis, cloud sync, monitoring."
      }
    }
    
    plugins = softwareSystem "Language Plugins" {
      description "Language-specific analyzers (Python, JS, C++, etc.)"
      tags "PartiallyImplemented"
      properties {
        "implementation.status" "partial"
        "implementation.notes" "Python plugin fully implemented. Others are stubs."
      }
    }
    
    repo = softwareSystem "Local Code Repo" {
      description "The developer's local codebase"
    }
    
    cloud = softwareSystem "Cloud Services" {
      description "Optional cloud services for sync and embeddings"
      tags "NotImplemented"
      properties {
        "implementation.status" "not_implemented"
        "implementation.notes" "Cloud sync is stub only. Embeddings work locally via Voyage AI."
      }
    }
    
    monitoring = softwareSystem "Monitoring" {
      description "Observability and metrics collection"
      tags "NotImplemented"
      properties {
        "implementation.status" "not_implemented"
      }
    }
    
    ide = softwareSystem "IDE/Editor" {
      description "Development environment integration"
      tags "NotImplemented"
      properties {
        "implementation.status" "not_implemented"
        "implementation.notes" "No IDE integration yet."
      }
    }

    # Relationships
    user -> llm "asks for code help"
    user -> ide "develops code"
    llm -> mcp "uses MCP tools"
    mcp -> plugins "delegates language analysis"
    mcp -> repo "indexes and monitors"
    mcp -> cloud "syncs shards (optional)"
    mcp -> monitoring "reports metrics"
    plugins -> repo "analyzes code structure"
    ide -> mcp "queries symbols/search"
  }
  
  views { 
    systemContext mcp "SystemContext" {
      include *
      autolayout lr
      description "System context showing MCP Server interactions"
    }
    
    styles {
    element "Core System" {
      background #1168bd
      color #ffffff
    }
    element "PartiallyImplemented" {
      background #FFD700
    }
    element "NotImplemented" {
      background #FF6B6B
    }
    }
  }
}
