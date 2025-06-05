"""PHP language plugin for code indexing and analysis.

This plugin provides comprehensive PHP code parsing including:
- Classes and interfaces
- Functions and methods
- Namespaces and use statements
- Traits and abstract classes
- Laravel framework detection (routes, models, controllers)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple
import hashlib

from ...plugin_base import (
    IPlugin,
    IndexShard,
    SymbolDef,
    Reference,
    SearchResult,
    SearchOpts,
)

from ...utils.treesitter_wrapper import TreeSitterWrapper
from ...utils.fuzzy_indexer import FuzzyIndexer
from ...storage.sqlite_store import SQLiteStore


class PHPPlugin(IPlugin):
    """PHP language plugin with comprehensive parsing and Laravel support."""
    
    lang = "php"
    
    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        self._ts = TreeSitterWrapper()
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None
        
        # Laravel patterns for framework detection
        self._laravel_patterns = {
            'model': re.compile(r'class\s+(\w+)\s+extends\s+(?:Model|Authenticatable)'),
            'controller': re.compile(r'class\s+(\w+Controller)\s+extends\s+(?:Controller|BaseController)'),
            'middleware': re.compile(r'class\s+(\w+)\s+implements?\s+.*Middleware'),
            'migration': re.compile(r'class\s+(\w+)\s+extends\s+Migration'),
            'seeder': re.compile(r'class\s+(\w+)\s+extends\s+Seeder'),
            'route': re.compile(r'Route::(get|post|put|patch|delete)\s*\(\s*[\'"]([^\'"]+)[\'"]'),
        }
        
        # PHP-specific patterns
        self._php_patterns = {
            'namespace': re.compile(r'namespace\s+([\w\\]+)'),
            'use': re.compile(r'use\s+([\w\\]+)(?:\s+as\s+(\w+))?'),
            'trait': re.compile(r'trait\s+(\w+)'),
            'interface': re.compile(r'interface\s+(\w+)'),
            'abstract_class': re.compile(r'abstract\s+class\s+(\w+)'),
            'const': re.compile(r'const\s+(\w+)\s*='),
            'property': re.compile(r'(?:public|private|protected)\s+(?:static\s+)?(?:\w+\s+)?(?:\?\w+\s+)?(?:array\s+)?\$(\w+)'),
        }
        
        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            self._repository_id = self._sqlite_store.create_repository(
                str(Path.cwd()), 
                Path.cwd().name,
                {"language": "php"}
            )
        
        self._preindex()

    def _preindex(self) -> None:
        """Pre-index all PHP files in the current directory."""
        for path in Path(".").rglob("*.php"):
            try:
                text = path.read_text(encoding='utf-8')
                self._indexer.add_file(str(path), text)
            except Exception:
                continue

    def supports(self, path: str | Path) -> bool:
        """Return True if file extension matches PHP files."""
        if isinstance(path, str):
            path = Path(path)
        return path.suffix == '.php'

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Index a PHP file and extract symbols."""
        if isinstance(path, str):
            path = Path(path)
        
        self._indexer.add_file(str(path), content)
        
        # Store file in SQLite if available
        file_id = None
        if self._sqlite_store and self._repository_id:
            file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            try:
                # Try to get relative path, fallback to filename only
                if path.is_absolute():
                    try:
                        relative_path = str(path.relative_to(Path.cwd()))
                    except ValueError:
                        relative_path = path.name
                else:
                    relative_path = str(path)
                        
                file_id = self._sqlite_store.store_file(
                    self._repository_id,
                    str(path),
                    relative_path,
                    language="php",
                    size=len(content),
                    hash=file_hash
                )
            except Exception:
                # Skip SQLite storage if path handling fails
                pass

        symbols = []
        
        # Use regex-based parsing (Tree-sitter PHP support would need separate configuration)
        symbols = self._extract_symbols_regex(content)
        
        # Store symbols in SQLite and fuzzy indexer
        for symbol in symbols:
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    symbol["symbol"],
                    symbol["kind"],
                    symbol["line"],
                    symbol.get("span", (symbol["line"], symbol["line"]))[1],
                    signature=symbol.get("signature", "")
                )
                # Add to fuzzy indexer with metadata
                self._indexer.add_symbol(
                    symbol["symbol"], 
                    str(path), 
                    symbol["line"],
                    {"symbol_id": symbol_id, "file_id": file_id}
                )

        return {"file": str(path), "symbols": symbols, "language": self.lang}

    def _extract_symbols_treesitter(self, content: str, root_node) -> List[Dict]:
        """Extract symbols using Tree-sitter parsing."""
        symbols = []
        current_namespace = ""
        
        for child in root_node.named_children:
            if child.type == "namespace_definition":
                current_namespace = self._extract_namespace(content, child)
            symbol_info = self._parse_node(content, child, current_namespace)
            if symbol_info:
                symbols.extend(symbol_info)
                
        return symbols

    def _extract_namespace(self, content: str, node) -> str:
        """Extract namespace from a namespace definition node."""
        name_node = node.child_by_field_name("name")
        if name_node:
            return content[name_node.start_byte:name_node.end_byte]
        return ""

    def _parse_node(self, content: str, node, namespace: str = "") -> List[Dict]:
        """Parse a Tree-sitter node and extract symbol information."""
        symbols = []
        
        if node.type == "class_declaration":
            symbols.extend(self._parse_class(content, node, namespace))
        elif node.type == "interface_declaration":
            symbols.extend(self._parse_interface(content, node, namespace))
        elif node.type == "trait_declaration":
            symbols.extend(self._parse_trait(content, node, namespace))
        elif node.type == "function_definition":
            symbols.extend(self._parse_function(content, node, namespace))
        elif node.type == "method_declaration":
            symbols.extend(self._parse_method(content, node))
        elif node.type == "const_declaration":
            symbols.extend(self._parse_constant(content, node))
        elif node.type == "property_declaration":
            symbols.extend(self._parse_property(content, node))
            
        # Recursively parse child nodes
        for child in node.named_children:
            symbols.extend(self._parse_node(content, child, namespace))
            
        return symbols

    def _parse_class(self, content: str, node, namespace: str = "") -> List[Dict]:
        """Parse PHP class declaration."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return []
            
        name = content[name_node.start_byte:name_node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        # Check for Laravel patterns
        extends_node = node.child_by_field_name("base_clause")
        extends = ""
        if extends_node:
            extends = content[extends_node.start_byte:extends_node.end_byte]
            
        kind = "class"
        if "Model" in extends or "Authenticatable" in extends:
            kind = "model"
        elif "Controller" in extends:
            kind = "controller"
        elif "Middleware" in extends:
            kind = "middleware"
        elif "Migration" in extends:
            kind = "migration"
        elif "Seeder" in extends:
            kind = "seeder"
            
        # Check for abstract class
        if self._is_abstract_class(content, node):
            kind = "abstract_class"
            
        full_name = f"{namespace}\\{name}" if namespace else name
        signature = f"class {name}"
        if extends:
            signature += f" {extends}"
            
        return [{
            "symbol": name,
            "kind": kind,
            "signature": signature,
            "line": start_line,
            "span": (start_line, end_line),
            "namespace": namespace,
            "full_name": full_name,
        }]

    def _parse_interface(self, content: str, node, namespace: str = "") -> List[Dict]:
        """Parse PHP interface declaration."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return []
            
        name = content[name_node.start_byte:name_node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        full_name = f"{namespace}\\{name}" if namespace else name
        
        return [{
            "symbol": name,
            "kind": "interface",
            "signature": f"interface {name}",
            "line": start_line,
            "span": (start_line, end_line),
            "namespace": namespace,
            "full_name": full_name,
        }]

    def _parse_trait(self, content: str, node, namespace: str = "") -> List[Dict]:
        """Parse PHP trait declaration."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return []
            
        name = content[name_node.start_byte:name_node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        full_name = f"{namespace}\\{name}" if namespace else name
        
        return [{
            "symbol": name,
            "kind": "trait",
            "signature": f"trait {name}",
            "line": start_line,
            "span": (start_line, end_line),
            "namespace": namespace,
            "full_name": full_name,
        }]

    def _parse_function(self, content: str, node, namespace: str = "") -> List[Dict]:
        """Parse PHP function definition."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return []
            
        name = content[name_node.start_byte:name_node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        # Extract parameters
        params_node = node.child_by_field_name("parameters")
        params = ""
        if params_node:
            params = content[params_node.start_byte:params_node.end_byte]
            
        signature = f"function {name}{params}"
        
        return [{
            "symbol": name,
            "kind": "function",
            "signature": signature,
            "line": start_line,
            "span": (start_line, end_line),
            "namespace": namespace,
        }]

    def _parse_method(self, content: str, node) -> List[Dict]:
        """Parse PHP method declaration."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return []
            
        name = content[name_node.start_byte:name_node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        # Extract visibility and static modifier
        visibility = self._get_method_visibility(content, node)
        is_static = self._is_static_method(content, node)
        is_abstract = self._is_abstract_method(content, node)
        
        # Extract parameters
        params_node = node.child_by_field_name("parameters")
        params = ""
        if params_node:
            params = content[params_node.start_byte:params_node.end_byte]
            
        kind = "method"
        if is_static:
            kind = "static_method"
        if visibility in ["private", "protected"]:
            kind = f"{visibility}_method"
        if is_abstract:
            kind = "abstract_method"
            
        modifiers = []
        if visibility != "public":
            modifiers.append(visibility)
        if is_static:
            modifiers.append("static")
        if is_abstract:
            modifiers.append("abstract")
            
        signature = f"{' '.join(modifiers)} function {name}{params}" if modifiers else f"function {name}{params}"
        
        return [{
            "symbol": name,
            "kind": kind,
            "signature": signature,
            "line": start_line,
            "span": (start_line, end_line),
        }]

    def _parse_constant(self, content: str, node) -> List[Dict]:
        """Parse PHP constant declaration."""
        # For const declarations, we need to find the name
        const_elements = node.children_by_field_name("const_element")
        symbols = []
        
        for element in const_elements:
            name_node = element.child_by_field_name("name")
            if name_node:
                name = content[name_node.start_byte:name_node.end_byte]
                start_line = element.start_point[0] + 1
                
                symbols.append({
                    "symbol": name,
                    "kind": "constant",
                    "signature": f"const {name}",
                    "line": start_line,
                    "span": (start_line, start_line),
                })
                
        return symbols

    def _parse_property(self, content: str, node) -> List[Dict]:
        """Parse PHP property declaration."""
        symbols = []
        
        # Find property elements
        for child in node.named_children:
            if child.type == "property_element":
                name_node = child.child_by_field_name("name")
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte].lstrip('$')
                    start_line = child.start_point[0] + 1
                    
                    visibility = self._get_property_visibility(content, node)
                    is_static = self._is_static_property(content, node)
                    
                    kind = "property"
                    if is_static:
                        kind = "static_property"
                    if visibility in ["private", "protected"]:
                        kind = f"{visibility}_property"
                        
                    modifiers = []
                    if visibility != "public":
                        modifiers.append(visibility)
                    if is_static:
                        modifiers.append("static")
                        
                    signature = f"{' '.join(modifiers)} ${name}" if modifiers else f"${name}"
                    
                    symbols.append({
                        "symbol": name,
                        "kind": kind,
                        "signature": signature,
                        "line": start_line,
                        "span": (start_line, start_line),
                    })
                    
        return symbols

    def _is_abstract_class(self, content: str, node) -> bool:
        """Check if a class is abstract."""
        # Look for abstract modifier before class keyword
        line_start = node.start_point[0]
        lines = content.split('\n')
        if line_start < len(lines):
            line = lines[line_start]
            return 'abstract' in line and 'class' in line
        return False

    def _get_method_visibility(self, content: str, node) -> str:
        """Get method visibility (public, private, protected)."""
        # Look for visibility modifiers in the method declaration
        method_line = content.split('\n')[node.start_point[0]]
        if 'private' in method_line:
            return 'private'
        elif 'protected' in method_line:
            return 'protected'
        return 'public'

    def _get_property_visibility(self, content: str, node) -> str:
        """Get property visibility (public, private, protected)."""
        # Look for visibility modifiers in the property declaration
        prop_line = content.split('\n')[node.start_point[0]]
        if 'private' in prop_line:
            return 'private'
        elif 'protected' in prop_line:
            return 'protected'
        return 'public'

    def _is_static_method(self, content: str, node) -> bool:
        """Check if a method is static."""
        method_line = content.split('\n')[node.start_point[0]]
        return 'static' in method_line

    def _is_static_property(self, content: str, node) -> bool:
        """Check if a property is static."""
        prop_line = content.split('\n')[node.start_point[0]]
        return 'static' in prop_line

    def _is_abstract_method(self, content: str, node) -> bool:
        """Check if a method is abstract."""
        method_line = content.split('\n')[node.start_point[0]]
        return 'abstract' in method_line

    def _extract_symbols_regex(self, content: str) -> List[Dict]:
        """Fallback regex-based symbol extraction."""
        symbols = []
        lines = content.split('\n')
        current_namespace = ""
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Namespace declarations
            namespace_match = self._php_patterns['namespace'].search(line)
            if namespace_match:
                current_namespace = namespace_match.group(1)
                continue
            
            # Class declarations
            class_match = re.match(r'(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?', line)
            if class_match:
                name = class_match.group(1)
                extends = class_match.group(2) or ""
                
                kind = "class"
                if "abstract" in line:
                    kind = "abstract_class"
                elif "Model" in extends or "Authenticatable" in extends:
                    kind = "model"
                elif "Controller" in extends:
                    kind = "controller"
                
                full_name = f"{current_namespace}\\{name}" if current_namespace else name
                signature = line
                
                symbols.append({
                    "symbol": name,
                    "kind": kind,
                    "signature": signature,
                    "line": i,
                    "span": (i, i),
                    "namespace": current_namespace,
                    "full_name": full_name,
                })
            
            # Interface declarations
            interface_match = self._php_patterns['interface'].search(line)
            if interface_match:
                name = interface_match.group(1)
                full_name = f"{current_namespace}\\{name}" if current_namespace else name
                symbols.append({
                    "symbol": name,
                    "kind": "interface",
                    "signature": line,
                    "line": i,
                    "span": (i, i),
                    "namespace": current_namespace,
                    "full_name": full_name,
                })
            
            # Trait declarations
            trait_match = self._php_patterns['trait'].search(line)
            if trait_match:
                name = trait_match.group(1)
                full_name = f"{current_namespace}\\{name}" if current_namespace else name
                symbols.append({
                    "symbol": name,
                    "kind": "trait",
                    "signature": line,
                    "line": i,
                    "span": (i, i),
                    "namespace": current_namespace,
                    "full_name": full_name,
                })
            
            # Function declarations - skip if already handled as method
            func_match = re.match(r'function\s+(\w+)\s*\(', line)
            if func_match and not re.match(r'(?:public|private|protected|static)', line):
                # Check if we're inside a class/interface/trait by tracking braces
                inside_class = False
                brace_level = 0
                class_brace_level = -1
                
                # Count braces from start of file to current position
                for j in range(i):
                    check_line = lines[j].strip()
                    # Track when we enter a class/interface/trait
                    if any(keyword in check_line for keyword in ['class ', 'interface ', 'trait ']):
                        # Check if opening brace is on same line or next line
                        if '{' in check_line:
                            class_brace_level = brace_level + 1
                        elif j < len(lines) - 1 and '{' in lines[j+1].strip():
                            class_brace_level = brace_level + 1
                    
                    # Update brace level
                    brace_level += check_line.count('{') - check_line.count('}')
                    
                    # If we closed the class, reset class_brace_level
                    if class_brace_level != -1 and brace_level < class_brace_level:
                        class_brace_level = -1
                
                # We're inside a class if class_brace_level is set and we haven't closed it
                inside_class = (class_brace_level != -1 and brace_level >= class_brace_level)
                
                if not inside_class:  # Global function
                    name = func_match.group(1)
                    symbols.append({
                        "symbol": name,
                        "kind": "function",
                        "signature": line,
                        "line": i,
                        "span": (i, i),
                        "namespace": current_namespace,
                    })
            
            # Method declarations - only process if not already handled as function
            method_match = re.match(r'(?:(public|private|protected)\s+)?(?:(static)\s+)?function\s+(\w+)\s*\(', line)
            if method_match:
                visibility = method_match.group(1)
                is_static = method_match.group(2) is not None
                name = method_match.group(3)
                
                # Check if this is a method with explicit visibility/static or inside a class
                if visibility or is_static:
                    # Explicit visibility or static - definitely a method
                    visibility = visibility or 'public'
                    kind = "method"
                    if is_static:
                        kind = "static_method"
                    if visibility in ["private", "protected"]:
                        kind = f"{visibility}_method"
                        
                    symbols.append({
                        "symbol": name,
                        "kind": kind,
                        "signature": line,
                        "line": i,
                        "span": (i, i),
                    })
                elif not re.match(r'(?:public|private|protected|static)', line):
                    # No explicit visibility - check if inside class
                    inside_class = False
                    brace_level = 0
                    class_brace_level = -1
                    
                    # Count braces from start of file to current position
                    for j in range(i):
                        check_line = lines[j].strip()
                        # Track when we enter a class/interface/trait
                        if any(keyword in check_line for keyword in ['class ', 'interface ', 'trait ']):
                            # Check if opening brace is on same line or next line
                            if '{' in check_line:
                                class_brace_level = brace_level + 1
                            elif j < len(lines) - 1 and '{' in lines[j+1].strip():
                                class_brace_level = brace_level + 1
                        
                        # Update brace level
                        brace_level += check_line.count('{') - check_line.count('}')
                        
                        # If we closed the class, reset class_brace_level
                        if class_brace_level != -1 and brace_level < class_brace_level:
                            class_brace_level = -1
                    
                    # We're inside a class if class_brace_level is set and we haven't closed it
                    inside_class = (class_brace_level != -1 and brace_level >= class_brace_level)
                    
                    if inside_class:
                        # Method without explicit visibility
                        symbols.append({
                            "symbol": name,
                            "kind": "method",
                            "signature": line,
                            "line": i,
                            "span": (i, i),
                        })
            
            # Constants
            const_match = self._php_patterns['const'].search(line)
            if const_match:
                name = const_match.group(1)
                symbols.append({
                    "symbol": name,
                    "kind": "constant",
                    "signature": line,
                    "line": i,
                    "span": (i, i),
                })
            
            # Properties
            prop_match = self._php_patterns['property'].search(line)
            if prop_match:
                name = prop_match.group(1)
                visibility = "public"
                if "private" in line:
                    visibility = "private"
                elif "protected" in line:
                    visibility = "protected"
                    
                kind = "property"
                if "static" in line:
                    kind = "static_property"
                if visibility in ["private", "protected"]:
                    kind = f"{visibility}_property"
                    
                symbols.append({
                    "symbol": name,
                    "kind": kind,
                    "signature": line,
                    "line": i,
                    "span": (i, i),
                })
                    
        return symbols

    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Find the definition of a PHP symbol."""
        for path in Path(".").rglob("*.php"):
            try:
                content = path.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    # Check for class, interface, trait, function, or method definitions
                    patterns = [
                        rf'\b(?:class|interface|trait|function)\s+{re.escape(symbol)}\b',
                        rf'\bfunction\s+{re.escape(symbol)}\s*\(',
                        rf'\bconst\s+{re.escape(symbol)}\s*=',
                        rf'\$\s*{re.escape(symbol)}\s*=',
                    ]
                    
                    if any(re.search(pattern, line) for pattern in patterns):
                        # Extract signature and documentation
                        signature = line.strip()
                        doc = self._extract_documentation(lines, i - 1)
                        
                        # Determine kind
                        kind = "unknown"
                        if line.strip().startswith('class'):
                            kind = "class"
                        elif line.strip().startswith('interface'):
                            kind = "interface"
                        elif line.strip().startswith('trait'):
                            kind = "trait"
                        elif 'function' in line:
                            kind = "function" if 'class' not in '\n'.join(lines[:i]) else "method"
                        elif 'const' in line:
                            kind = "constant"
                        elif '$' in line:
                            kind = "property"
                        
                        return {
                            "symbol": symbol,
                            "kind": kind,
                            "language": self.lang,
                            "signature": signature,
                            "doc": doc,
                            "defined_in": str(path),
                            "line": i,
                            "span": (i, i + 3),
                        }
            except Exception:
                continue
                
        return None

    def _extract_documentation(self, lines: List[str], start_line: int) -> str | None:
        """Extract PHPDoc comments above a symbol."""
        doc_lines = []
        in_doc_block = False
        
        # First, check if start_line is inside a doc block
        if start_line < len(lines):
            current_line = lines[start_line].strip()
            if current_line.startswith('*') and not current_line.startswith('*/'):
                # We're inside a doc block, find the start
                for i in range(start_line, -1, -1):
                    if i >= len(lines):
                        continue
                    line = lines[i].strip()
                    if line.startswith('/**'):
                        # Found the start, now extract from here
                        for j in range(i, start_line + 1):
                            if j >= len(lines):
                                continue
                            line = lines[j].strip()
                            if line.startswith('/**'):
                                doc_lines.append(line[3:].strip())
                            elif line.startswith('*') and not line.startswith('*/'):
                                doc_lines.append(line[1:].strip())
                            elif line.startswith('*/'):
                                doc_lines.append(line[:-2].strip())
                                break
                        return '\n'.join(doc_lines) if doc_lines else None
        
        # Look backwards for PHPDoc comments
        for i in range(start_line, -1, -1):
            if i >= len(lines):
                continue
            line = lines[i].strip()
            
            if line.endswith('*/'):
                in_doc_block = True
                if line.startswith('/**'):
                    # Single line doc block
                    doc_lines.insert(0, line[3:-2].strip())
                    break
                else:
                    doc_lines.insert(0, line[:-2].strip())
            elif line.startswith('/**'):
                if in_doc_block:
                    doc_lines.insert(0, line[3:].strip())
                    break
            elif in_doc_block and line.startswith('*'):
                doc_lines.insert(0, line[1:].strip())
            elif line.startswith('//'):
                if not in_doc_block:
                    doc_lines.insert(0, line[2:].strip())
            elif line == '':
                continue
            else:
                break
                
        return '\n'.join(doc_lines) if doc_lines else None

    def findReferences(self, symbol: str) -> List[Reference]:
        """Find references to a PHP symbol."""
        refs = []
        seen = set()
        
        for path in Path(".").rglob("*.php"):
            try:
                content = path.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    # Look for symbol usage (class instantiation, method calls, etc.)
                    if (re.search(rf'\b{re.escape(symbol)}\b', line) or
                        re.search(rf'\${re.escape(symbol)}\b', line)):
                        key = (str(path), i)
                        if key not in seen:
                            refs.append(Reference(file=str(path), line=i))
                            seen.add(key)
            except Exception:
                continue
                
        return refs

    def search(self, query: str, opts: SearchOpts | None = None) -> List[SearchResult]:
        """Search for symbols in PHP code."""
        limit = 20
        if opts and "limit" in opts:
            limit = opts["limit"]
        if opts and opts.get("semantic"):
            return []
            
        return self._indexer.search(query, limit=limit)

    def get_indexed_count(self) -> int:
        """Return the number of indexed files."""
        if hasattr(self._indexer, '_file_contents'):
            return len(self._indexer._file_contents)
        return 0


# Alias for backwards compatibility
Plugin = PHPPlugin