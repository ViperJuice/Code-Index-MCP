#!/usr/bin/env python
"""Debug script to test the reindex functionality."""

from pathlib import Path
from mcp_server.plugin_system import PluginManager
from mcp_server.dispatcher import EnhancedDispatcher as Dispatcher

# Initialize plugin manager
print("Initializing plugin manager...")
plugin_manager = PluginManager()

# Load plugins
config_path = Path('plugins.yaml')
load_result = plugin_manager.load_plugins_safe(config_path if config_path.exists() else None)

if not load_result.success:
    print(f"Plugin loading failed: {load_result.error}")
    exit(1)

print(f"Plugin loading succeeded: {load_result.metadata}")

# Get active plugins
active_plugins = plugin_manager.get_active_plugins()
plugin_instances = list(active_plugins.values())

print(f"\nLoaded {len(plugin_instances)} active plugins:")
for name, plugin in active_plugins.items():
    print(f"  - {name}")

# Create dispatcher
print("\nCreating dispatcher...")
dispatcher = Dispatcher(plugin_instances)

print(f"\nDispatcher has {len(dispatcher._plugins)} plugins")

# Test file support
test_files = [
    Path("test_python_plugin.py"),
    Path("test_c_plugin_simple.py"), 
    Path("mcp_server/plugins/js_plugin/plugin.py"),
    Path("mcp_server/plugins/c_plugin/plugin.py")
]

print("\nTesting plugin support for existing files:")
for file_path in test_files:
    if file_path.exists():
        print(f"\n{file_path}:")
        for i, plugin in enumerate(dispatcher._plugins):
            supports = plugin.supports(file_path)
            lang = getattr(plugin, 'lang', f'plugin_{i}')
            print(f"  - Plugin {i} ({lang}): {supports}")
    else:
        print(f"\n{file_path}: File not found")

# Simulate reindex logic
print("\n\nSimulating reindex for .py files in current directory:")
indexed_count = 0
py_files = list(Path(".").glob("*.py"))[:5]  # Just first 5 files

for file_path in py_files:
    print(f"\nChecking {file_path}:")
    for i, plugin in enumerate(dispatcher._plugins):
        lang = getattr(plugin, 'lang', f'plugin_{i}')
        supports = plugin.supports(file_path)
        print(f"  - Plugin {i} ({lang}): {supports}")
        if supports:
            print(f"    -> Would index with {lang} plugin")
            indexed_count += 1
            break

print(f"\n\nTotal files that would be indexed: {indexed_count}")