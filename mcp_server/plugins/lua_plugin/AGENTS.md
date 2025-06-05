# Lua Plugin Agent Instructions

## Overview
This plugin provides comprehensive support for the Lua programming language, including game development frameworks (Love2D), web frameworks (OpenResty/Nginx), and embedded scripting scenarios.

## Symbol Recognition Priorities

### Functions (High Priority)
1. Global functions: `function name()`
2. Local functions: `local function name()`
3. Anonymous functions: `local name = function()`
4. Methods with colon: `function Class:method()`
5. Method assignments: `Class.method = function()`
6. Love2D callbacks: `function love.load()`
7. Coroutines: `coroutine.create(function()...)`

### Classes and Tables (High Priority)
1. Metatable patterns: `setmetatable({}, Class)`
2. Table constructors as classes: `local Class = {}`
3. `__index` patterns for OOP
4. Class constructors: `Class.new()` or `Class:new()`

### Modules (Medium Priority)
1. Require statements: `require("module")`
2. Module definitions: `local M = {}; return M`
3. LuaRocks packages in .rockspec files

### Variables and Constants (Medium Priority)
1. Local variables: `local x = value`
2. Multiple assignments: `local a, b, c = 1, 2, 3`
3. Global constants: `CONSTANT_NAME = value`
4. Table fields: `table.field = value`

## Framework Detection

### Love2D Projects
- Look for `main.lua` or `conf.lua` in project
- Extract Love2D-specific callbacks
- Tag with "love2d" modifier

### OpenResty/Nginx Projects
- Look for `nginx.conf` or `resty/` modules
- Extract ngx.* API usage
- Tag with "openresty" modifier

### LuaJIT Projects
- Detect `require("ffi")` usage
- Tag with "luajit" modifier

## Special Handling

### Metatables
When you see `setmetatable()`, mark the table as a class and add "metatable" modifier.

### Coroutines
Functions created with `coroutine.create()` or `coroutine.wrap()` should be tagged with "coroutine" modifier.

### Module Patterns
Recognize both old-style (`module()`) and new-style (return table) module patterns.

### .rockspec Files
Parse these as configuration files extracting:
- Package name as MODULE symbol
- Dependencies as IMPORT symbols

## Best Practices

1. **Method Detection**: Check if a function has `self` as first parameter or uses colon syntax
2. **Scope Tracking**: Track whether symbols are local or global
3. **Framework Features**: Apply framework-specific patterns when detected
4. **Line Accuracy**: Ensure line numbers are precise for all symbols

## Common Patterns

### OOP Pattern 1 (Metatable)
```lua
local Class = {}
Class.__index = Class

function Class.new()
    return setmetatable({}, Class)
end

function Class:method()
    -- self is available
end
```

### OOP Pattern 2 (Closure)
```lua
local function Class(init)
    local self = {}
    
    function self.method()
        -- closure over init
    end
    
    return self
end
```

### Module Pattern
```lua
local M = {}

function M.func()
    -- module function
end

return M
```

## Edge Cases

1. **Dynamic requires**: `require(variable)` - mark as generic import
2. **Monkey patching**: Modifying existing tables/modules
3. **Global pollution**: Direct global assignments without `local`
4. **Multi-line strings**: Handle `[[...]]` syntax correctly