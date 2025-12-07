#!/usr/bin/env python
"""Test reindex functionality with test files of different types."""

from pathlib import Path

from mcp_server.dispatcher import EnhancedDispatcher as Dispatcher
from mcp_server.plugin_system import PluginManager

# Initialize plugin manager
plugin_manager = PluginManager()
config_path = Path("plugins.yaml")
load_result = plugin_manager.load_plugins_safe(config_path if config_path.exists() else None)

if not load_result.success:
    print(f"Plugin loading failed: {load_result.error}")
    exit(1)

# Get active plugins
active_plugins = plugin_manager.get_active_plugins()
plugin_instances = list(active_plugins.values())

# Create dispatcher
dispatcher = Dispatcher(plugin_instances)

print(f"Dispatcher has {len(dispatcher._plugins)} plugins")
print("\nActive plugins:")
for plugin in dispatcher._plugins:
    lang = getattr(plugin, "lang", "unknown")
    print(f"  - {lang}")

# Test files in test_files directory
test_dir = Path("test_files")
print(f"\n\nTesting files in {test_dir}:")

for file_path in test_dir.glob("*"):
    if file_path.is_file():
        print(f"\n{file_path.name}:")
        supported = False
        for plugin in dispatcher._plugins:
            if plugin.supports(file_path):
                lang = getattr(plugin, "lang", "unknown")
                print(f"  ✓ Supported by {lang} plugin")
                supported = True
                break
        if not supported:
            print(f"  ✗ NOT SUPPORTED by any plugin")

# Simulate reindex on test_files directory
print("\n\nSimulating reindex on test_files directory:")
indexed_count = 0
indexed_by_type = {}

for file_path in test_dir.rglob("*"):
    if file_path.is_file():
        try:
            # Check if any plugin supports this file
            for plugin in dispatcher._plugins:
                if plugin.supports(file_path):
                    # Would index file here
                    indexed_count += 1

                    # Track by file type
                    suffix = file_path.suffix.lower()
                    indexed_by_type[suffix] = indexed_by_type.get(suffix, 0) + 1

                    lang = getattr(plugin, "lang", "unknown")
                    print(f"  Would index {file_path.name} with {lang} plugin")
                    break
        except Exception as e:
            print(f"  Error checking {file_path}: {e}")

print(f"\nTotal files that would be indexed: {indexed_count}")
print("\nBreakdown by type:")
for ext, count in sorted(indexed_by_type.items()):
    print(f"  {ext}: {count} files")
