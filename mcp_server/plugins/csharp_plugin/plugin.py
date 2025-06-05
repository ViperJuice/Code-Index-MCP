"""
Comprehensive C# language plugin using hybrid Tree-sitter and regex approach.

This plugin provides advanced C# language support including:
- .NET framework detection (.NET Framework, .NET Core, .NET 5+)
- NuGet package parsing (packages.config, *.csproj)
- Attribute/annotation extraction
- Generic type support
- Async/await pattern recognition
- LINQ expression detection
- ASP.NET, WPF, and console application support
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from ..hybrid_plugin_base import HybridPluginBase
from ..regex_plugin_base import RegexPattern
from ..plugin_template import SymbolType, ParsedSymbol, PluginConfig


@dataclass
class CSharpProjectInfo:
    """Information about a C# project."""
    framework_version: Optional[str] = None
    target_framework: Optional[str] = None
    packages: List[str] = None
    project_type: Optional[str] = None  # "console", "web", "library", "wpf", etc.
    
    def __post_init__(self):
        if self.packages is None:
            self.packages = []


class Plugin(HybridPluginBase):
    """Hybrid plugin for C# with Tree-sitter and regex fallback."""
    
    def __init__(self, config: Optional[PluginConfig] = None, **kwargs):
        """Initialize C# plugin."""
        super().__init__(config, **kwargs)
        
        # C#-specific configuration
        self._project_cache = {}
        self._framework_patterns = self._compile_framework_patterns()
        self._linq_patterns = self._compile_linq_patterns()
        self._attribute_patterns = self._compile_attribute_patterns()
        self._async_patterns = self._compile_async_patterns()
    
    def get_language(self) -> str:
        """Return the language this plugin supports."""
        return "c#"
    
    def get_supported_extensions(self) -> List[str]:
        """Return supported file extensions."""
        return [".cs", ".csx", ".cshtml"]
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        """Return basic symbol patterns for fallback."""
        return {
            SymbolType.FUNCTION: r"(?:public|private|protected|internal)?\s*(?:static|virtual|override|abstract)?\s*(?:async\s+)?(?:\w+(?:<[^>]+>)?\s+)+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
            SymbolType.CLASS: r"(?:public|private|protected|internal)?\s*(?:static|abstract|sealed)?\s*(?:class|interface|struct|enum)\s+([A-Za-z_][A-Za-z0-9_]*)",
            SymbolType.VARIABLE: r"(?:public|private|protected|internal)?\s*(?:static|readonly|const)?\s*(?:\w+(?:<[^>]+>)?\s+)+([A-Za-z_][A-Za-z0-9_]*)\s*[=;]",
            SymbolType.IMPORT: r"using\s+([A-Za-z_][A-Za-z0-9_.]*)",
            SymbolType.PROPERTY: r"(?:public|private|protected|internal)?\s*(?:static|virtual|override|abstract)?\s*(?:\w+(?:<[^>]+>)?\s+)+([A-Za-z_][A-Za-z0-9_]*)\s*\{\s*(?:get|set)",
            SymbolType.ENUM: r"(?:public|private|protected|internal)?\s*enum\s+([A-Za-z_][A-Za-z0-9_]*)",
            SymbolType.INTERFACE: r"(?:public|private|protected|internal)?\s*interface\s+([A-Za-z_][A-Za-z0-9_]*)",
            SymbolType.STRUCT: r"(?:public|private|protected|internal)?\s*struct\s+([A-Za-z_][A-Za-z0-9_]*)",
            SymbolType.NAMESPACE: r"namespace\s+([A-Za-z_][A-Za-z0-9_.]*)",
            SymbolType.FIELD: r"(?:public|private|protected|internal)?\s*(?:static|readonly|const)?\s*(?:\w+(?:<[^>]+>)?\s+)+([A-Za-z_][A-Za-z0-9_]*)\s*;"
        }
    
    def get_tree_sitter_node_types(self) -> Dict[SymbolType, List[str]]:
        """Return Tree-sitter node types for symbol extraction."""
        return {
            SymbolType.FUNCTION: ["method_declaration", "constructor_declaration", "operator_declaration"],
            SymbolType.CLASS: ["class_declaration"],
            SymbolType.INTERFACE: ["interface_declaration"],
            SymbolType.STRUCT: ["struct_declaration"],
            SymbolType.ENUM: ["enum_declaration"],
            SymbolType.PROPERTY: ["property_declaration"],
            SymbolType.FIELD: ["field_declaration"],
            SymbolType.VARIABLE: ["variable_declarator", "local_declaration_statement"],
            SymbolType.NAMESPACE: ["namespace_declaration"],
            SymbolType.IMPORT: ["using_directive"]
        }
    
    def get_regex_patterns(self) -> List[RegexPattern]:
        """Return regex patterns for fallback symbol extraction."""
        return [
            # Method declarations - simplified pattern
            RegexPattern(
                pattern=r"(?:public|private|protected|internal)?\s*(?:static\s+)?(?:async\s+)?(?:\w+(?:<[^>]+>)?\s+)+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
                symbol_type=SymbolType.FUNCTION,
                name_group=1,
                flags=re.MULTILINE
            ),
            
            # Class declarations
            RegexPattern(
                pattern=r"(?:public|private|protected|internal)?\s*(?:class|interface|struct|enum)\s+([A-Za-z_][A-Za-z0-9_]*)",
                symbol_type=SymbolType.CLASS,
                name_group=1,
                flags=re.MULTILINE
            ),
            
            # Property declarations
            RegexPattern(
                pattern=r"(?:public|private|protected|internal)?\s*(?:static\s+)?(?:\w+(?:<[^>]+>)?\s+)+([A-Za-z_][A-Za-z0-9_]*)\s*\{\s*(?:get|set)",
                symbol_type=SymbolType.PROPERTY,
                name_group=1,
                flags=re.MULTILINE
            ),
            
            # Field declarations
            RegexPattern(
                pattern=r"(?:public|private|protected|internal)?\s*(?:static\s+)?(?:readonly\s+)?(?:\w+(?:<[^>]+>)?\s+)+([A-Za-z_][A-Za-z0-9_]*)\s*(?:=.*?)?;",
                symbol_type=SymbolType.FIELD,
                name_group=1,
                flags=re.MULTILINE
            ),
            
            # Namespace declarations
            RegexPattern(
                pattern=r"namespace\s+([A-Za-z_][A-Za-z0-9_.]*)",
                symbol_type=SymbolType.NAMESPACE,
                name_group=1,
                flags=re.MULTILINE
            ),
            
            # Using statements
            RegexPattern(
                pattern=r"using\s+([A-Za-z_][A-Za-z0-9_.]*);",
                symbol_type=SymbolType.IMPORT,
                name_group=1,
                flags=re.MULTILINE
            ),
            
            # Event declarations
            RegexPattern(
                pattern=r"(?:public|private|protected|internal)?\s*(?:static\s+)?event\s+(?:\w+(?:<[^>]+>)?\s+)+([A-Za-z_][A-Za-z0-9_]*)",
                symbol_type=SymbolType.FIELD,  # Events are a special kind of field
                name_group=1,
                flags=re.MULTILINE
            ),
            
            # Delegate declarations
            RegexPattern(
                pattern=r"(?:public|private|protected|internal)?\s*delegate\s+(?:\w+(?:<[^>]+>)?\s+)+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
                symbol_type=SymbolType.CLASS,  # Delegates are a special kind of type
                name_group=1,
                flags=re.MULTILINE
            )
        ]
    
    def get_fallback_threshold(self) -> float:
        """Return threshold for deciding when to fallback to regex."""
        return 0.15  # Fallback if Tree-sitter finds less than 15% expected symbols
    
    def _compile_framework_patterns(self) -> List[re.Pattern]:
        """Compile patterns for .NET framework detection."""
        return [
            re.compile(r"<TargetFramework>([^<]+)</TargetFramework>", re.IGNORECASE),
            re.compile(r"<TargetFrameworkVersion>([^<]+)</TargetFrameworkVersion>", re.IGNORECASE),
            re.compile(r"<UseWPF>true</UseWPF>", re.IGNORECASE),
            re.compile(r"<UseWindowsForms>true</UseWindowsForms>", re.IGNORECASE),
            re.compile(r"<OutputType>([^<]+)</OutputType>", re.IGNORECASE)
        ]
    
    def _compile_linq_patterns(self) -> List[re.Pattern]:
        """Compile patterns for LINQ expression detection."""
        return [
            re.compile(r"\b(?:from|where|select|join|orderby|group)\s+", re.IGNORECASE),
            re.compile(r"\.\s*(?:Where|Select|OrderBy|GroupBy|Join|Take|Skip)\s*\("),
            re.compile(r"=>\s*[^;]+"),  # Lambda expressions
            re.compile(r"\bvar\s+\w+\s*=\s*from\b")
        ]
    
    def _compile_attribute_patterns(self) -> List[re.Pattern]:
        """Compile patterns for attribute detection."""
        return [
            re.compile(r"\[([A-Za-z_][A-Za-z0-9_]*)\]"),  # Simple attributes
            re.compile(r"\[([A-Za-z_][A-Za-z0-9_]*)\([^)]*\)\]"),  # Attributes with parameters
            re.compile(r"\[assembly:\s*([A-Za-z_][A-Za-z0-9_]*)")  # Assembly attributes
        ]
    
    def _compile_async_patterns(self) -> List[re.Pattern]:
        """Compile patterns for async/await detection."""
        return [
            re.compile(r"\basync\s+(?:Task|void|Task<[^>]+>)", re.IGNORECASE),
            re.compile(r"\bawait\s+"),
            re.compile(r"Task\s*\.\s*(?:Run|Start|Factory)")
        ]
    
    def _extract_symbols(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Extract symbols with C#-specific enhancements."""
        # Get base symbols using hybrid approach
        symbols = super()._extract_symbols(content, file_path)
        
        # Enhance symbols with C#-specific information
        symbols = self._enhance_csharp_symbols(symbols, content, file_path)
        
        # Add project-level information
        project_info = self._analyze_project_context(file_path)
        if project_info:
            for symbol in symbols:
                symbol.metadata = symbol.metadata or {}
                symbol.metadata.update({
                    "framework_version": project_info.framework_version,
                    "target_framework": project_info.target_framework,
                    "project_type": project_info.project_type
                })
        
        return symbols
    
    def _enhance_csharp_symbols(self, symbols: List[ParsedSymbol], content: str, file_path: str) -> List[ParsedSymbol]:
        """Enhance symbols with C#-specific information."""
        lines = content.splitlines()
        
        for symbol in symbols:
            # Enhance with attributes
            attributes = self._find_attributes_for_symbol(lines, symbol.line)
            if attributes:
                symbol.metadata = symbol.metadata or {}
                symbol.metadata["attributes"] = attributes
            
            # Enhance with generics information
            generic_info = self._extract_generic_info(symbol.signature or "")
            if generic_info:
                symbol.metadata = symbol.metadata or {}
                symbol.metadata["generics"] = generic_info
            
            # Check for async patterns
            if self._is_async_symbol(symbol, lines):
                symbol.modifiers = symbol.modifiers or set()
                symbol.modifiers.add("async")
            
            # Check for LINQ usage
            if self._contains_linq(symbol, lines, content):
                symbol.metadata = symbol.metadata or {}
                symbol.metadata["uses_linq"] = True
            
            # Extract parameter information for methods
            if symbol.symbol_type == SymbolType.FUNCTION:
                params = self._extract_method_parameters(symbol.signature or "")
                if params:
                    symbol.metadata = symbol.metadata or {}
                    symbol.metadata["parameters"] = params
            
            # Extract inheritance information for classes
            if symbol.symbol_type in (SymbolType.CLASS, SymbolType.INTERFACE, SymbolType.STRUCT):
                inheritance = self._extract_inheritance_info(symbol, lines)
                if inheritance:
                    symbol.metadata = symbol.metadata or {}
                    symbol.metadata["inheritance"] = inheritance
        
        return symbols
    
    def _find_attributes_for_symbol(self, lines: List[str], symbol_line: int) -> List[str]:
        """Find attributes above a symbol."""
        attributes = []
        
        # Look for attributes in the lines above the symbol
        for i in range(max(0, symbol_line - 10), symbol_line):
            if i < len(lines):
                line = lines[i].strip()
                for pattern in self._attribute_patterns:
                    matches = pattern.findall(line)
                    attributes.extend(matches)
        
        return list(set(attributes))  # Remove duplicates
    
    def _extract_generic_info(self, signature: str) -> Optional[Dict[str, any]]:
        """Extract generic type information from signature."""
        generic_pattern = re.compile(r"<([^>]+)>")
        matches = generic_pattern.findall(signature)
        
        if matches:
            generic_params = []
            for match in matches:
                params = [p.strip() for p in match.split(",")]
                generic_params.extend(params)
            
            return {
                "type_parameters": generic_params,
                "is_generic": True
            }
        
        return None
    
    def _is_async_symbol(self, symbol: ParsedSymbol, lines: List[str]) -> bool:
        """Check if symbol is async."""
        if symbol.line <= len(lines):
            # Check current line and a few lines above
            for i in range(max(0, symbol.line - 3), min(symbol.line + 1, len(lines))):
                line = lines[i].lower()
                for pattern in self._async_patterns:
                    if pattern.search(line):
                        return True
        
        return False
    
    def _contains_linq(self, symbol: ParsedSymbol, lines: List[str], content: str) -> bool:
        """Check if symbol contains LINQ expressions."""
        # Check in the symbol's scope
        symbol_content = self._get_symbol_content(symbol, lines)
        
        for pattern in self._linq_patterns:
            if pattern.search(symbol_content):
                return True
        
        return False
    
    def _get_symbol_content(self, symbol: ParsedSymbol, lines: List[str]) -> str:
        """Get the content of a symbol (method body, class content, etc.)."""
        start_line = symbol.line - 1
        end_line = symbol.end_line if symbol.end_line else start_line + 1
        
        if start_line < len(lines) and end_line <= len(lines):
            return "\n".join(lines[start_line:end_line])
        
        return ""
    
    def _extract_method_parameters(self, signature: str) -> List[Dict[str, str]]:
        """Extract method parameters from signature."""
        params = []
        
        # Extract parameter list from signature
        param_match = re.search(r"\(([^)]*)\)", signature)
        if param_match:
            param_text = param_match.group(1).strip()
            if param_text:
                param_parts = param_text.split(",")
                for param in param_parts:
                    param = param.strip()
                    # Simple parsing: last word is name, everything else is type
                    parts = param.split()
                    if len(parts) >= 2:
                        param_type = " ".join(parts[:-1])
                        param_name = parts[-1]
                        params.append({
                            "name": param_name,
                            "type": param_type
                        })
        
        return params
    
    def _extract_inheritance_info(self, symbol: ParsedSymbol, lines: List[str]) -> Optional[Dict[str, any]]:
        """Extract inheritance information for classes/interfaces."""
        if symbol.line <= len(lines):
            line = lines[symbol.line - 1]
            
            # Look for inheritance syntax
            inheritance_match = re.search(r":\s*([^{]+)", line)
            if inheritance_match:
                inheritance_text = inheritance_match.group(1).strip()
                base_types = [t.strip() for t in inheritance_text.split(",")]
                
                return {
                    "base_types": base_types,
                    "has_inheritance": True
                }
        
        return None
    
    def _analyze_project_context(self, file_path: str) -> Optional[CSharpProjectInfo]:
        """Analyze the project context for a C# file."""
        file_path = Path(file_path)
        
        # Check cache first
        project_dir = self._find_project_directory(file_path)
        if project_dir and str(project_dir) in self._project_cache:
            return self._project_cache[str(project_dir)]
        
        if not project_dir:
            return None
        
        project_info = CSharpProjectInfo()
        
        # Look for .csproj files
        csproj_files = list(project_dir.glob("*.csproj"))
        if csproj_files:
            project_info = self._parse_csproj_file(csproj_files[0])
        
        # Look for packages.config
        packages_config = project_dir / "packages.config"
        if packages_config.exists():
            packages = self._parse_packages_config(packages_config)
            project_info.packages.extend(packages)
        
        # Cache the result
        self._project_cache[str(project_dir)] = project_info
        return project_info
    
    def _find_project_directory(self, file_path: Path) -> Optional[Path]:
        """Find the project directory containing the C# file."""
        current = file_path.parent
        
        # Look for project indicators going up the directory tree
        for _ in range(10):  # Limit search depth
            if any(current.glob("*.csproj")) or any(current.glob("*.sln")):
                return current
            
            if current.parent == current:  # Reached root
                break
            current = current.parent
        
        return None
    
    def _parse_csproj_file(self, csproj_path: Path) -> CSharpProjectInfo:
        """Parse a .csproj file for project information."""
        project_info = CSharpProjectInfo()
        
        try:
            tree = ET.parse(csproj_path)
            root = tree.getroot()
            
            # Extract target framework
            target_framework = root.find(".//TargetFramework")
            if target_framework is not None:
                project_info.target_framework = target_framework.text
            
            target_framework_version = root.find(".//TargetFrameworkVersion")
            if target_framework_version is not None:
                project_info.framework_version = target_framework_version.text
            
            # Determine project type
            output_type = root.find(".//OutputType")
            if output_type is not None:
                project_info.project_type = output_type.text.lower()
            
            # Check for specific project types
            if root.find(".//UseWPF") is not None:
                project_info.project_type = "wpf"
            elif root.find(".//UseWindowsForms") is not None:
                project_info.project_type = "winforms"
            elif any(ref.get("Include", "").startswith("Microsoft.AspNetCore") 
                    for ref in root.findall(".//PackageReference")):
                project_info.project_type = "web"
            
            # Extract package references
            for package_ref in root.findall(".//PackageReference"):
                include = package_ref.get("Include")
                if include:
                    version = package_ref.get("Version", "")
                    project_info.packages.append(f"{include}:{version}" if version else include)
            
        except Exception as e:
            self.logger.warning(f"Failed to parse .csproj file {csproj_path}: {e}")
        
        return project_info
    
    def _parse_packages_config(self, packages_path: Path) -> List[str]:
        """Parse packages.config file."""
        packages = []
        
        try:
            tree = ET.parse(packages_path)
            root = tree.getroot()
            
            for package in root.findall(".//package"):
                package_id = package.get("id")
                version = package.get("version")
                if package_id:
                    packages.append(f"{package_id}:{version}" if version else package_id)
                    
        except Exception as e:
            self.logger.warning(f"Failed to parse packages.config {packages_path}: {e}")
        
        return packages
    
    def get_query_patterns(self) -> Dict[str, str]:
        """Return Tree-sitter query patterns for C#."""
        return {
            "classes": """
                (class_declaration
                  name: (identifier) @name) @class
            """,
            "interfaces": """
                (interface_declaration
                  name: (identifier) @name) @interface
            """,
            "structs": """
                (struct_declaration
                  name: (identifier) @name) @struct
            """,
            "enums": """
                (enum_declaration
                  name: (identifier) @name) @enum
            """,
            "methods": """
                (method_declaration
                  name: (identifier) @name) @method
            """,
            "constructors": """
                (constructor_declaration
                  name: (identifier) @name) @constructor
            """,
            "properties": """
                (property_declaration
                  name: (identifier) @name) @property
            """,
            "fields": """
                (field_declaration
                  (variable_declaration
                    (variable_declarator
                      (identifier) @name))) @field
            """,
            "namespaces": """
                (namespace_declaration
                  name: (qualified_name) @name) @namespace
            """,
            "using_directives": """
                (using_directive
                  (qualified_name) @name) @using
            """,
            "attributes": """
                (attribute_list
                  (attribute
                    name: (identifier) @name)) @attribute
            """,
            "generic_types": """
                (type_parameter_list
                  (type_parameter
                    (identifier) @name)) @generic
            """,
            "async_methods": """
                (method_declaration
                  (modifier) @async
                  name: (identifier) @name) @method
                (#eq? @async "async")
            """,
            "linq_queries": """
                (query_expression) @linq
            """
        }
    
    def get_csharp_info(self) -> Dict[str, any]:
        """Get C#-specific plugin information."""
        info = self.get_hybrid_info()
        info.update({
            "language_features": {
                "generics": True,
                "linq": True,
                "async_await": True,
                "attributes": True,
                "nullable_reference_types": True,
                "pattern_matching": True
            },
            "project_types_supported": [
                "console", "library", "web", "wpf", "winforms", "blazor"
            ],
            "framework_support": {
                "net_framework": True,
                "net_core": True,
                "net_5_plus": True
            },
            "cached_projects": len(self._project_cache)
        })
        
        return info
    
    def _extract_docstring_from_node(self, node, content: str) -> Optional[str]:
        """Extract XML documentation comments for C#."""
        # Look for XML doc comments (/// comments) above the node
        lines = content[:node.start_byte].split('\n')
        doc_lines = []
        
        # Work backwards from the node to find doc comments
        for line in reversed(lines[-10:]):  # Look at last 10 lines
            stripped = line.strip()
            if stripped.startswith('///'):
                # Extract content after ///
                doc_content = stripped[3:].strip()
                if doc_content:
                    doc_lines.insert(0, doc_content)
            elif stripped and not stripped.startswith('//'):
                # Non-comment line, stop looking
                break
        
        if doc_lines:
            return ' '.join(doc_lines)
        
        return None
    
    def _extract_modifiers_from_node(self, node, content: str) -> Set[str]:
        """Extract modifiers from Tree-sitter node for C#."""
        modifiers = set()
        
        # Look for modifier siblings or children
        if hasattr(node, 'children'):
            for child in node.children:
                if hasattr(child, 'type') and child.type in {
                    'public', 'private', 'protected', 'internal',
                    'static', 'virtual', 'override', 'abstract',
                    'sealed', 'readonly', 'const', 'async',
                    'partial', 'extern', 'unsafe'
                }:
                    modifiers.add(child.type)
        
        return modifiers