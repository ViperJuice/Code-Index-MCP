"""Test Lua plugin functionality."""

import pytest
from pathlib import Path
from mcp_server.plugins.lua_plugin import Plugin


class TestLuaPlugin:
    """Test cases for Lua plugin."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = Plugin()
    
    def test_plugin_info(self):
        """Test plugin information."""
        info = self.plugin.get_plugin_info()
        assert info["language"] == "lua"
        assert ".lua" in info["extensions"]
        assert ".rockspec" in info["extensions"]
        assert "functions" in info["features"]
    
    def test_supports_files(self):
        """Test file support detection."""
        assert self.plugin.supports("test.lua")
        assert self.plugin.supports("package.rockspec")
        assert self.plugin.supports(".luacheckrc")
        assert not self.plugin.supports("test.py")
        assert not self.plugin.supports("test.js")
    
    def test_parse_simple_functions(self):
        """Test parsing simple Lua functions."""
        content = """
-- Global function
function hello()
    print("Hello, World!")
end

-- Local function
local function privateFunc(x)
    return x * 2
end

-- Anonymous function
local myFunc = function(a, b)
    return a + b
end
"""
        
        result = self.plugin.indexFile("test.lua", content)
        assert result["language"] == "lua"
        symbols = result["symbols"]
        
        # Check function names
        names = [s["symbol"] for s in symbols]
        assert "hello" in names
        assert "privateFunc" in names
        assert "myFunc" in names
        
        # Check all are functions
        for sym in symbols:
            assert sym["kind"] == "function"
    
    def test_parse_classes_and_methods(self):
        """Test parsing Lua class patterns."""
        content = """
-- Class with metatable
local Person = {}
Person.__index = Person

function Person.new(name)
    local self = setmetatable({}, Person)
    self.name = name
    return self
end

function Person:greet()
    print("Hello, I'm " .. self.name)
end

-- Method assignment
Person.staticMethod = function()
    return "static"
end
"""
        
        result = self.plugin.indexFile("test.lua", content)
        symbols = result["symbols"]
        
        # Find class
        classes = [s for s in symbols if s["kind"] == "class"]
        assert len(classes) >= 1
        assert any(c["symbol"] == "Person" for c in classes)
        
        # Find methods
        methods = [s for s in symbols if s["kind"] == "method"]
        method_names = [m["symbol"] for m in methods]
        assert "greet" in method_names
        assert "staticMethod" in method_names
        
        # Check that class has metatable modifier
        person_class = next((c for c in classes if c["symbol"] == "Person"), None)
        assert person_class is not None
        assert "metatable" in person_class.get("modifiers", [])
    
    def test_parse_modules_and_requires(self):
        """Test extraction of module patterns."""
        content = """
local json = require("json")
local utils = require("utils.helpers")
require("init")

local MyModule = {}

function MyModule.init()
    print("Module initialized")
end

return MyModule
"""
        
        result = self.plugin.indexFile("test.lua", content)
        symbols = result["symbols"]
        
        # Check modules
        modules = [s for s in symbols if s["kind"] == "module"]
        module_names = [m["symbol"] for m in modules]
        assert "json" in module_names
        assert "utils" in module_names
        
        # Check MyModule is detected as a class/table
        classes = [s for s in symbols if s["kind"] == "class"]
        assert any(c["symbol"] == "MyModule" for c in classes)
    
    def test_parse_coroutines(self):
        """Test extraction of coroutine patterns."""
        content = """
local producer = coroutine.create(function()
    for i = 1, 10 do
        coroutine.yield(i)
    end
end)

local consumer = coroutine.wrap(function()
    while true do
        local value = coroutine.yield()
        if not value then break end
    end
end)
"""
        
        result = self.plugin.indexFile("test.lua", content)
        symbols = result["symbols"]
        
        # Find coroutines (they should be functions with coroutine modifier)
        functions = [s for s in symbols if s["kind"] == "function"]
        coroutines = [f for f in functions if "coroutine" in f.get("modifiers", [])]
        
        assert len(coroutines) >= 1
        names = [c["symbol"] for c in coroutines]
        assert "producer" in names or "consumer" in names
    
    def test_parse_love2d_callbacks(self):
        """Test extraction of Love2D patterns."""
        content = """
function love.load()
    player = {x = 100, y = 100}
end

function love.update(dt)
    player.x = player.x + 100 * dt
end

function love.draw()
    love.graphics.circle("fill", player.x, player.y, 20)
end

function love.keypressed(key)
    if key == "escape" then
        love.event.quit()
    end
end
"""
        
        result = self.plugin.indexFile("test.lua", content)
        symbols = result["symbols"]
        
        # Check Love2D functions
        love_funcs = [s for s in symbols if s["symbol"].startswith("love.")]
        assert len(love_funcs) >= 4
        
        func_names = [f["symbol"] for f in love_funcs]
        assert "love.load" in func_names
        assert "love.update" in func_names
        assert "love.draw" in func_names
        assert "love.keypressed" in func_names
        
        # Check they have love2d modifier
        for func in love_funcs:
            assert "love2d" in func.get("modifiers", [])
    
    def test_parse_constants_and_fields(self):
        """Test extraction of constants and table fields."""
        content = """
-- Constants
GAME_TITLE = "My Game"
MAX_PLAYERS = 4

-- Local variable
local config = {}
config.debug = true
config.version = "1.0.0"

-- Table field assignments
Player.MAX_HEALTH = 100
Player.DEFAULT_SPEED = 5
"""
        
        result = self.plugin.indexFile("test.lua", content)
        symbols = result["symbols"]
        
        # Check constants
        constants = [s for s in symbols if s["kind"] == "constant"]
        const_names = [c["symbol"] for c in constants]
        assert "GAME_TITLE" in const_names
        assert "MAX_PLAYERS" in const_names
        
        # Check fields
        fields = [s for s in symbols if s["kind"] == "field"]
        field_names = [f["symbol"] for f in fields]
        assert "debug" in field_names
        assert "version" in field_names
    
    def test_parse_rockspec_file(self):
        """Test parsing .rockspec files."""
        content = '''package = "mylibrary"
version = "1.0-1"

dependencies = {
    "lua >= 5.1",
    "luafilesystem >= 1.8.0",
    "penlight >= 1.5.4"
}

build = {
    type = "builtin",
    modules = {
        ["mylibrary"] = "src/mylibrary.lua"
    }
}'''
        
        result = self.plugin.indexFile("mylibrary-1.0-1.rockspec", content)
        assert result["language"] == "rockspec"
        symbols = result["symbols"]
        
        # Check package name
        modules = [s for s in symbols if s["kind"] == "module"]
        assert any(m["symbol"] == "mylibrary" for m in modules)
        
        # Check dependencies
        imports = [s for s in symbols if s["kind"] == "import"]
        import_names = [i["symbol"] for i in imports]
        assert "lua >= 5.1" in import_names
        assert "luafilesystem >= 1.8.0" in import_names