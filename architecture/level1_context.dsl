workspace "MCP Server – Level 1" {
  model {
    user = person "Developer" {
      description "Software developer using Claude for code assistance"
    }
    
    llm = softwareSystem "Claude" {
      description "AI assistant with MCP tool capabilities"
    }
    
    mcp = softwareSystem "MCP Server" {
      description "Local-first code indexing system with deep language understanding"
      tags "Core System"
    }
    
    plugins = softwareSystem "Language Plugins" {
      description "Language-specific analyzers (Python, JS, C++, etc.)"
    }
    
    repo = container "Local Code Repo" {
      description "The developer's local codebase"
    }
    
    cloud = container "Cloud" {
      description "Optional cloud services for sync and embeddings"
    }
    
    monitoring = softwareSystem "Monitoring" {
      description "Observability and metrics collection"
    }
    
    ide = softwareSystem "IDE/Editor" {
      description "Development environment integration"
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
    
    # Define performance requirements
    properties {
      "performance.symbolLookup" "<100ms"
      "performance.semanticSearch" "<500ms"
      "performance.indexing" "10K files/minute"
      "scalability.maxFiles" "1M+ files"
      "availability.target" "99.9%"
      "security.model" "Zero-trust, local-first"
    }
  }
}
