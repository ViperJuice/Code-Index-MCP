"""Java language plugin for code indexing and analysis.

This plugin provides comprehensive Java language support including:
- Import resolution for package imports
- Type analysis with generics support
- Maven/Gradle build system integration
- Cross-file reference tracking
- Class inheritance and interface implementation tracking
"""

from .plugin import Plugin

__all__ = ["Plugin"]
