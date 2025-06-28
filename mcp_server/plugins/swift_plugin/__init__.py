"""Swift language plugin for code indexing and analysis.

This plugin provides comprehensive Swift language support including:
- Module system and framework imports
- Protocol conformance checking
- Property wrappers and result builders
- Objective-C interoperability
- Swift Package Manager integration
"""

from .plugin import Plugin

__all__ = ["Plugin"]
