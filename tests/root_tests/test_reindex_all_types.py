#!/usr/bin/env python
"""Debug script to test reindex functionality with all file types."""

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

print(f"Dispatcher has {len(dispatcher._plugins)} plugins\n")

# Find all files of different types
file_patterns = {
    "Python": "**/*.py",
    "JavaScript": "**/*.js",
    "TypeScript": "**/*.ts",
    "C": "**/*.c",
    "C Header": "**/*.h",
    "C++": "**/*.cpp",
    "Dart": "**/*.dart",
    "HTML": "**/*.html",
    "CSS": "**/*.css",
}

# Count files by type that would be indexed
for file_type, pattern in file_patterns.items():
    files = list(Path(".").glob(pattern))[:3]  # Just first 3 of each type
    if files:
        print(f"\n{file_type} files found:")
        for file_path in files:
            print(f"  {file_path}")
            supported = False
            for plugin in dispatcher._plugins:
                if plugin.supports(file_path):
                    lang = getattr(plugin, "lang", "unknown")
                    print(f"    -> Supported by {lang} plugin")
                    supported = True
                    break
            if not supported:
                print(f"    -> NOT SUPPORTED by any plugin!")

# Test the actual reindex logic from gateway.py
print("\n\nSimulating actual reindex logic:")
indexed_count = 0
indexed_by_type = {}

# This simulates the code from gateway.py lines 805-817
for file_path in Path(".").rglob("*"):
    if file_path.is_file() and indexed_count < 20:  # Limit to 20 files for testing
        try:
            # Check if any plugin supports this file
            for plugin in dispatcher._plugins:
                if plugin.supports(file_path):
                    # Would index file here
                    indexed_count += 1

                    # Track by file type
                    suffix = file_path.suffix.lower()
                    indexed_by_type[suffix] = indexed_by_type.get(suffix, 0) + 1
                    break
        except Exception as e:
            print(f"Error checking {file_path}: {e}")

print(f"\nTotal files that would be indexed: {indexed_count}")
print("\nBreakdown by type:")
for ext, count in sorted(indexed_by_type.items()):
    print(f"  {ext}: {count} files")
