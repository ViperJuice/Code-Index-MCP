# Lua Plugin

Comprehensive Lua plugin with support for modules, metatables, coroutines, and game development frameworks.

## Features

- **Language**: lua
- **File Extensions**: .lua, .rockspec, .luacheckrc
- **Plugin Type**: hybrid (Tree-sitter with regex fallback)
- **Tree-sitter Support**: Yes (tree-sitter-lua)

## Supported Symbol Types

### Core Lua Constructs
- **Functions**: Global functions, local functions, anonymous functions, method definitions
- **Classes**: Table constructors, metatables, class simulations
- **Variables**: Local variables, global variables, multiple assignments
- **Constants**: Uppercase global constants
- **Modules**: Module definitions, require statements, LuaRocks packages
- **Methods**: Colon syntax methods, dot syntax method assignments
- **Fields**: Table fields and properties
- **Coroutines**: coroutine.create and coroutine.wrap patterns

### Framework Support

#### Love2D
- Detects Love2D game projects automatically
- Extracts Love2D callbacks (love.load, love.update, love.draw, etc.)
- Recognizes Love2D API calls (love.graphics.*, love.physics.*, etc.)

#### OpenResty/Nginx Lua
- Detects OpenResty projects automatically
- Extracts ngx.* API usage
- Recognizes location capture patterns
- Supports Nginx Lua module patterns

#### LuaJIT
- Detects FFI usage
- Supports LuaJIT-specific patterns

## Lua Version Support

The plugin supports multiple Lua versions:
- Lua 5.1
- Lua 5.2
- Lua 5.3
- Lua 5.4 (default)
- LuaJIT

## Usage

```python
from mcp_server.plugins.lua_plugin import Plugin

# Initialize the plugin
plugin = Plugin()

# Check if a file is supported
if plugin.supports("game.lua"):
    # Index the file
    with open("game.lua", "r") as f:
        content = f.read()
    
    result = plugin.indexFile("game.lua", content)
    print(f"Found {len(result['symbols'])} symbols")
    
    # Get plugin info including detected frameworks
    info = plugin.get_plugin_info()
    print(f"Detected frameworks: {info['frameworks']}")
```

## Special File Support

### .rockspec Files
The plugin can parse LuaRocks package specification files:
- Extracts package name
- Lists dependencies
- Parses module definitions

### .luacheckrc Files
Supports Luacheck configuration files for linting settings.

## Symbol Examples

### Functions
```lua
-- Global function
function globalFunc() end

-- Local function
local function localFunc() end

-- Anonymous function
local handler = function() end

-- Method with colon syntax
function MyClass:method() end

-- Method assignment
MyClass.staticMethod = function() end
```

### Classes and Metatables
```lua
-- Class pattern 1
local Vector = {}
Vector.__index = Vector

-- Class pattern 2
local Animal = setmetatable({}, {
    __call = function(cls, ...)
        return cls.new(...)
    end
})
```

### Modules
```lua
-- Module imports
local json = require("json")
local utils = require("utils.helpers")

-- Module definition
local MyModule = {}
return MyModule
```

### Coroutines
```lua
local co = coroutine.create(function()
    coroutine.yield()
end)
```

## Configuration

The plugin can be configured using the `plugin_config.json` file:

```json
{
  "plugin": {
    "name": "lua",
    "language": "lua",
    "version": "1.0.0",
    "type": "hybrid"
  },
  "extensions": [".lua", ".rockspec", ".luacheckrc"],
  "features": {
    "tree_sitter_support": true,
    "caching": true,
    "async_processing": true,
    "semantic_analysis": true
  },
  "performance": {
    "max_file_size": 10485760,
    "cache_ttl": 3600,
    "batch_size": 100
  }
}
```

## Testing

Run tests with:
```bash
pytest test_lua_plugin.py -v
```

The test suite includes:
- Basic Lua syntax parsing
- Class and metatable detection
- Module and require statement extraction
- Coroutine pattern recognition
- Love2D framework support
- OpenResty/Nginx Lua patterns
- .rockspec file parsing
- Line number accuracy
- Symbol metadata and modifiers

## Development

### Adding New Patterns

To add support for new Lua patterns:

1. **Update regex patterns** in `get_regex_patterns()`
2. **Add Tree-sitter node types** in `get_tree_sitter_node_types()`
3. **Implement pattern-specific extraction** in `_extract_lua_specific_constructs()`
4. **Add tests** for the new patterns

### Framework Detection

The plugin automatically detects:
- Love2D projects by looking for main.lua or conf.lua
- OpenResty projects by finding nginx.conf or resty modules
- LuaJIT usage by detecting FFI requires

### Performance Optimization

- Uses hybrid parsing (Tree-sitter primary, regex fallback)
- Implements intelligent caching
- Deduplicates symbols efficiently
- Processes large files incrementally

## Common Use Cases

### Game Development
Perfect for Love2D game projects with automatic detection of:
- Game callbacks and lifecycle methods
- Graphics and physics API usage
- Game state management patterns

### Web Development
Ideal for OpenResty/Nginx Lua development:
- API endpoint handlers
- Middleware functions
- Request/response processing

### Embedded Scripting
Supports embedded Lua scenarios:
- Configuration scripts
- Plugin systems
- Automation scripts

## License

MCP Team - Version 1.0.0