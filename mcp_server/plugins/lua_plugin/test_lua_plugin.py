"""Comprehensive tests for Lua plugin."""

import pytest
from pathlib import Path
from .plugin import Plugin
from ...plugin_template import SymbolType


class TestLuaPlugin:
    """Test cases for Lua plugin."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = Plugin()
        self.test_data_dir = Path(__file__).parent / "test_data"
    
    def test_supports_files(self):
        """Test file support detection."""
        # Test supported extensions
        assert self.plugin.supports("test.lua")
        assert self.plugin.supports("package.rockspec")
        assert self.plugin.supports(".luacheckrc")
        assert self.plugin.supports("/path/to/file.lua")
        
        # Test unsupported extensions
        assert not self.plugin.supports("test.txt")
        assert not self.plugin.supports("test.py")
        assert not self.plugin.supports("test.js")
    
    def test_parse_simple_lua_code(self):
        """Test parsing simple Lua code."""
        content = """
-- Simple Lua functions
function hello()
    print("Hello, World!")
end

local function privateFunc(x)
    return x * 2
end

local myFunc = function(a, b)
    return a + b
end
"""
        
        result = self.plugin.indexFile("test.lua", content)
        assert result["language"] == "lua"
        assert len(result["symbols"]) >= 3
        
        # Check function names
        symbols = result["symbols"]
        names = [s["symbol"] for s in symbols]
        assert "hello" in names
        assert "privateFunc" in names
        assert "myFunc" in names
    
    def test_extract_lua_classes(self):
        """Test extraction of Lua class patterns."""
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

-- Another class pattern
local Animal = setmetatable({}, {
    __call = function(cls, ...)
        return cls.new(...)
    end
})
"""
        
        result = self.plugin.indexFile("test.lua", content)
        symbols = result["symbols"]
        
        # Find class symbols
        classes = [s for s in symbols if s["kind"] == "class"]
        assert len(classes) >= 1
        
        class_names = [c["symbol"] for c in classes]
        assert "Person" in class_names
        
        # Find methods
        methods = [s for s in symbols if s["kind"] == "method"]
        assert any(m["symbol"] == "greet" for m in methods)
    
    def test_extract_modules_and_requires(self):
        """Test extraction of module patterns and require statements."""
        content = """
local json = require("json")
local utils = require("utils.helpers")
local config = require "config"
require("init")

local MyModule = {}

function MyModule.init()
    print("Module initialized")
end

return MyModule
"""
        
        result = self.plugin.indexFile("test.lua", content)
        symbols = result["symbols"]
        
        # Check for module imports
        modules = [s for s in symbols if s["kind"] == "module"]
        imports = [s for s in symbols if s["kind"] == "import"]
        
        assert len(modules) + len(imports) >= 3
        
        symbol_names = [s["symbol"] for s in symbols]
        assert "json" in symbol_names or "init" in symbol_names
    
    def test_extract_coroutines(self):
        """Test extraction of coroutine patterns."""
        content = """
local producer = coroutine.create(function()
    for i = 1, 10 do
        coroutine.yield(i)
    end
end)

local consumer = coroutine.wrap(function(prod)
    while true do
        local value = coroutine.resume(prod)
        if not value then break end
        print(value)
    end
end)
"""
        
        result = self.plugin.indexFile("test.lua", content)
        symbols = result["symbols"]
        
        # Find coroutine symbols
        coroutines = [s for s in symbols if "coroutine" in s.get("modifiers", [])]
        assert len(coroutines) >= 1
        
        names = [s["symbol"] for s in symbols]
        assert "producer" in names or "consumer" in names
    
    def test_extract_love2d_patterns(self):
        """Test extraction of Love2D specific patterns."""
        # Read Love2D test file
        love2d_file = self.test_data_dir / "love2d_game.lua"
        if love2d_file.exists():
            content = love2d_file.read_text()
            result = self.plugin.indexFile("game.lua", content)
            symbols = result["symbols"]
            
            # Check for Love2D callbacks
            love_functions = [s for s in symbols if s["symbol"].startswith("love.")]
            assert len(love_functions) > 0
            
            # Check for specific callbacks
            callback_names = [f["symbol"] for f in love_functions]
            assert any("load" in name for name in callback_names)
            assert any("update" in name for name in callback_names)
            assert any("draw" in name for name in callback_names)
    
    def test_extract_openresty_patterns(self):
        """Test extraction of OpenResty/Nginx Lua patterns."""
        content = """
local function handle_request()
    local args = ngx.req.get_uri_args()
    local headers = ngx.req.get_headers()
    
    ngx.ctx.user_id = args.user_id
    
    local red = ngx.location.capture("/redis", {
        args = {cmd = "get", key = "user:" .. args.user_id}
    })
    
    ngx.say("Hello from OpenResty!")
end
"""
        
        result = self.plugin.indexFile("api.lua", content)
        symbols = result["symbols"]
        
        # Should find the handler function
        functions = [s for s in symbols if s["kind"] == "function"]
        assert any(f["symbol"] == "handle_request" for f in functions)
    
    def test_parse_rockspec_file(self):
        """Test parsing of .rockspec files."""
        rockspec_file = self.test_data_dir / "mylibrary-1.0-1.rockspec"
        if rockspec_file.exists():
            content = rockspec_file.read_text()
            result = self.plugin.indexFile(str(rockspec_file), content)
            symbols = result["symbols"]
            
            # Should extract package name
            assert any(s["symbol"] == "mylibrary" for s in symbols)
            
            # Should extract dependencies
            deps = [s for s in symbols if s.get("metadata", {}).get("dependency")]
            assert len(deps) > 0
    
    def test_extract_constants_and_variables(self):
        """Test extraction of constants and variables."""
        content = """
-- Constants
local MAX_PLAYERS = 4
local DEFAULT_PORT = 8080
local VERSION = "1.0.0"

-- Variables
local count = 0
local items, index = {}, 1
local x, y, z = 0, 0, 0

-- Global constant
GAME_TITLE = "My Awesome Game"
API_ENDPOINT = "https://api.example.com"
"""
        
        result = self.plugin.indexFile("test.lua", content)
        symbols = result["symbols"]
        
        # Check constants
        constants = [s for s in symbols if s["kind"] == "constant"]
        assert len(constants) >= 2  # At least the global ones
        
        # Check variables
        variables = [s for s in symbols if s["kind"] == "variable"]
        assert len(variables) >= 4
    
    def test_extract_table_methods_and_fields(self):
        """Test extraction of table methods and fields."""
        content = """
local Player = {}
Player.MAX_HEALTH = 100
Player.DEFAULT_SPEED = 5

function Player:new(name)
    local obj = {name = name, health = self.MAX_HEALTH}
    setmetatable(obj, self)
    self.__index = self
    return obj
end

function Player:takeDamage(amount)
    self.health = math.max(0, self.health - amount)
end

Player.heal = function(self, amount)
    self.health = math.min(self.MAX_HEALTH, self.health + amount)
end

-- Table fields
local config = {}
config.debug = true
config.version = "1.0"
config.server = {
    host = "localhost",
    port = 8080
}
"""
        
        result = self.plugin.indexFile("test.lua", content)
        symbols = result["symbols"]
        
        # Check methods
        methods = [s for s in symbols if s["kind"] == "method"]
        method_names = [m["symbol"] for m in methods]
        assert "takeDamage" in method_names
        assert "heal" in method_names
        
        # Check fields
        fields = [s for s in symbols if s["kind"] == "field"]
        assert len(fields) >= 2  # config.debug, config.version, etc.
    
    def test_symbol_metadata_and_modifiers(self):
        """Test that symbols have appropriate metadata and modifiers."""
        content = """
-- Module with metatable
local MyClass = {}
MyClass.__index = MyClass

function MyClass:new()
    return setmetatable({}, self)
end

-- Coroutine
local coro = coroutine.create(function()
    while true do
        coroutine.yield()
    end
end)

-- Love2D callback
function love.load()
    print("Game loaded")
end
"""
        
        result = self.plugin.indexFile("test.lua", content)
        symbols = result["symbols"]
        
        # Find class with metatable
        classes = [s for s in symbols if s["kind"] == "class"]
        assert any("metatable" in c.get("modifiers", []) for c in classes)
        
        # Find coroutine
        coros = [s for s in symbols if "coroutine" in s.get("modifiers", [])]
        assert len(coros) >= 1
    
    def test_comprehensive_sample_file(self):
        """Test parsing the comprehensive sample.lua file."""
        sample_file = self.test_data_dir / "sample.lua"
        if sample_file.exists():
            content = sample_file.read_text()
            result = self.plugin.indexFile("sample.lua", content)
            
            assert result["language"] == "lua"
            symbols = result["symbols"]
            assert len(symbols) > 10  # Should extract many symbols
            
            # Verify various symbol types are extracted
            symbol_types = set(s["kind"] for s in symbols)
            expected_types = {"function", "class", "variable", "method", "module"}
            assert len(symbol_types.intersection(expected_types)) >= 4
            
            # Check specific symbols
            symbol_names = [s["symbol"] for s in symbols]
            assert "globalFunction" in symbol_names
            assert "Vector" in symbol_names
            assert "Animal" in symbol_names
            assert "MyModule" in symbol_names
            
            # Check methods are properly identified
            methods = [s for s in symbols if s["kind"] == "method"]
            assert len(methods) >= 4  # magnitude, normalize, makeSound, etc.
    
    def test_line_numbers_and_positions(self):
        """Test that line numbers are correctly extracted."""
        content = """function first()
end

local second = function()
end

-- Some comments
local third = {}
function third:method()
end"""
        
        result = self.plugin.indexFile("test.lua", content)
        symbols = sorted(result["symbols"], key=lambda s: s["line"])
        
        assert symbols[0]["symbol"] == "first"
        assert symbols[0]["line"] == 1
        
        assert symbols[1]["symbol"] == "second"
        assert symbols[1]["line"] == 4
        
        # Table and method should have appropriate line numbers
        remaining = symbols[2:]
        assert any(s["symbol"] == "third" for s in remaining)
        assert any(s["symbol"] == "method" for s in remaining)
    
    def test_get_plugin_info(self):
        """Test plugin information."""
        info = self.plugin.get_plugin_info()
        
        assert info["language"] == "lua"
        assert ".lua" in info["extensions"]
        assert ".rockspec" in info["extensions"]
        assert "features" in info
        assert "functions" in info["features"]
        assert "metatables" in info["features"]
        assert "coroutines" in info["features"]