workspace "MCP Server – Level 1" {
  model {
    user = person "Developer"
    llm = softwareSystem "Claude"
    mcp = softwareSystem "MCP Server"
    repo = container "Local Code Repo"
    cloud = container "Cloud"

    user -> llm "asks help"
    llm -> mcp "tool.use()"
    mcp -> repo "indexes"
    mcp -> cloud "pulls shards"
  }
  views { systemContext ctx { include * ; autolayout lr } }
}
