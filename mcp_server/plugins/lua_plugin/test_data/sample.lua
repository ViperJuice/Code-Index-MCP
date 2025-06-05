-- Sample Lua code demonstrating various language features

-- Module definition
local MyModule = {}

-- Constants
local MAX_ITEMS = 100
local DEFAULT_NAME = "Unnamed"

-- Local variables
local counter = 0
local items = {}

-- Global function
function globalFunction(param1, param2)
    print("Global function called with:", param1, param2)
    return param1 + param2
end

-- Local function
local function privateHelper(value)
    return value * 2
end

-- Function assignment
local processData = function(data)
    for i, item in ipairs(data) do
        print(i, item)
    end
end

-- Class-like table with metatable
local Vector = {}
Vector.__index = Vector

-- Constructor
function Vector.new(x, y)
    local self = setmetatable({}, Vector)
    self.x = x or 0
    self.y = y or 0
    return self
end

-- Method using colon syntax
function Vector:magnitude()
    return math.sqrt(self.x^2 + self.y^2)
end

-- Method assignment
Vector.normalize = function(self)
    local mag = self:magnitude()
    if mag > 0 then
        self.x = self.x / mag
        self.y = self.y / mag
    end
end

-- Another class using different pattern
local Animal = {
    species = "unknown",
    sound = "..."
}

function Animal:new(species, sound)
    local obj = {}
    setmetatable(obj, self)
    self.__index = self
    obj.species = species or self.species
    obj.sound = sound or self.sound
    return obj
end

function Animal:makeSound()
    print(self.species .. " says: " .. self.sound)
end

-- Module pattern
function MyModule.publicFunction(arg)
    return privateHelper(arg)
end

function MyModule:methodStyleFunction()
    print("Method style function in module")
end

-- Coroutine example
local myCoroutine = coroutine.create(function()
    for i = 1, 10 do
        print("Coroutine iteration:", i)
        coroutine.yield(i)
    end
end)

-- Table with fields
local config = {
    debug = true,
    version = "1.0.0"
}
config.timeout = 30
config.retries = 3

-- Require statements
local json = require("json")
local utils = require("utils.helpers")
require("init")  -- Without assignment

-- Anonymous function in table
local handlers = {
    onClick = function(event)
        print("Clicked at:", event.x, event.y)
    end,
    onHover = function(event)
        print("Hovering over:", event.target)
    end
}

-- Return module
return MyModule