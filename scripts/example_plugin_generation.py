#!/usr/bin/env python3
"""
Example of how to use the plugin generator programmatically.

This demonstrates creating a TypeScript plugin using the generator.
"""

import sys
from pathlib import Path
from generate_language_plugin import PluginGenerator


def create_typescript_plugin():
    """Example: Create a TypeScript plugin."""
    
    # Initialize generator
    base_path = Path(__file__).parent.parent
    generator = PluginGenerator(base_path)
    
    # Define language information
    info = {
        "name": "TypeScript",
        "display_name": "TypeScript",
        "plugin_name": "typescript_plugin",
        "extensions": [".ts", ".tsx"],
        "has_treesitter": True,
        "treesitter_language": "typescript",
        "symbol_types": ["class", "function", "method", "variable", "interface", "type", "enum"],
        "frameworks": ["React", "Angular", "Vue", "Node.js"],
        "features": {
            "multiline_strings": True,
            "decorators": True,
            "type_annotations": True,
            "async_support": True
        },
        "comments": {
            "single": "//",
            "multi_start": "/*",
            "multi_end": "*/"
        }
    }
    
    print("Creating TypeScript plugin...")
    print(f"Plugin will be created at: {generator.plugins_path / info['plugin_name']}")
    
    # Generate the plugin
    generator.generate_plugin(info)
    
    print("\nTypeScript plugin created successfully!")
    print("You can now customize the plugin by editing the generated files.")


if __name__ == "__main__":
    print("This is an example of programmatic plugin generation.")
    print("It would create a TypeScript plugin if run.")
    print("To actually create the plugin, uncomment the next line:")
    print("# create_typescript_plugin()")
    
    # Uncomment to actually generate:
    # create_typescript_plugin()