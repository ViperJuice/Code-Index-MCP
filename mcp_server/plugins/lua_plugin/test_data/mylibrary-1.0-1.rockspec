package = "mylibrary"
version = "1.0-1"

source = {
    url = "git://github.com/username/mylibrary.git",
    tag = "v1.0"
}

description = {
    summary = "A comprehensive Lua library for game development",
    detailed = [[
        MyLibrary provides utilities for game development including
        vector math, collision detection, state management, and more.
        It's designed to work with Love2D but can be used standalone.
    ]],
    homepage = "https://github.com/username/mylibrary",
    license = "MIT",
    maintainer = "Your Name <your.email@example.com>"
}

dependencies = {
    "lua >= 5.1, < 5.5",
    "luafilesystem >= 1.8.0",
    "penlight >= 1.5.4",
    "luasocket >= 3.0",
    "middleclass >= 4.1",
    "json-lua >= 0.1"
}

build = {
    type = "builtin",
    modules = {
        ["mylibrary"] = "src/mylibrary.lua",
        ["mylibrary.vector"] = "src/vector.lua",
        ["mylibrary.collision"] = "src/collision.lua",
        ["mylibrary.state"] = "src/state.lua",
        ["mylibrary.utils"] = "src/utils.lua",
        ["mylibrary.timer"] = "src/timer.lua",
        ["mylibrary.tween"] = "src/tween.lua"
    },
    copy_directories = {
        "docs",
        "examples",
        "tests"
    }
}

test_dependencies = {
    "busted >= 2.0",
    "luacov >= 0.13"
}

test = {
    type = "busted",
    platforms = {
        unix = {
            flags = {
                "--coverage",
                "--output=TAP"
            }
        }
    }
}