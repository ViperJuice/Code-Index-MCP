workspace "MCP Server – Level 3" {
  model {
    mcp = softwareSystem "MCP Server"
    api = container mcp "API Gateway"
    dispatcher = container mcp "Dispatcher"

    component gateway "Gateway Controller" "mcp_server.gateway"
    component core "Dispatcher Core" "mcp_server.dispatcher"
    component base "Plugin Base" "mcp_server.plugin_base"

    api -> gateway
    dispatcher -> core
    core -> base
  }
  views { component components { include * ; autolayout lr } }
}
