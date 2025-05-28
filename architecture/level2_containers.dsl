workspace "MCP Server – Level 2" {
  model {
    mcp = softwareSystem "MCP Server"
    api = container mcp "API Gateway" "FastAPI"
    dispatcher = container mcp "Dispatcher"
    indexer = container mcp "Indexer"
    store = container mcp "Local Index Store"
    sync = container mcp "Cloud Sync"
    embed = container mcp "Embedding"

    api -> dispatcher
    dispatcher -> store
    dispatcher -> sync
    dispatcher -> embed
    indexer -> store
    sync -> store
  }
  views { container containers { include * ; autolayout lr } }
}
