"""
C# plugin for C# language support with .NET framework compatibility.

Comprehensive C# plugin supporting:
- Classes, interfaces, structs, enums
- Methods, properties, fields, events
- Generics and attributes
- Async/await patterns
- LINQ expressions
- NuGet package detection
"""

from .plugin import Plugin

__version__ = "1.0.0"
__author__ = "Code-Index-MCP"
__description__ = "Comprehensive C# plugin with .NET framework support"

__all__ = ["Plugin"]