"""Go regex parser based on existing patterns with Unicode support.

This parser extracts symbols from Go source code using regular expressions
adapted from the existing Go plugin with proper Unicode identifier support.
"""

import re
from typing import Dict, List, Any, Optional, Pattern
from pathlib import Path

from ..regex_parser import RegexParser, Symbol, ParseResult


class GoRegexParser(RegexParser):
    """Regex-based parser for Go source code."""
    
    def get_language(self) -> str:
        return 'go'
    
    def _setup_patterns(self):
        """Set up Go-specific regex patterns."""
        super()._setup_patterns()
        
        # Go keywords that aren't symbol definitions
        self.keywords = {
            'break', 'case', 'chan', 'continue', 'default', 'defer', 'else',
            'fallthrough', 'for', 'go', 'goto', 'if', 'import', 'map',
            'range', 'return', 'select', 'switch'
        }
        
        # Go built-in types
        self.builtin_types = {
            'bool', 'byte', 'complex64', 'complex128', 'error', 'float32',
            'float64', 'int', 'int8', 'int16', 'int32', 'int64', 'rune',
            'string', 'uint', 'uint8', 'uint16', 'uint32', 'uint64', 'uintptr',
            'any', 'comparable'
        }
        
        # Package declaration
        self.package_pattern = re.compile(
            rf'^{self.optional_whitespace}package\s+({self.identifier})',
            re.MULTILINE
        )
        
        # Import patterns
        self.import_single_pattern = re.compile(
            rf'^{self.optional_whitespace}import\s+"([^"]+)"',
            re.MULTILINE
        )
        
        self.import_block_pattern = re.compile(
            rf'^{self.optional_whitespace}import\s*\(',
            re.MULTILINE
        )
        
        # Function patterns (with generics support)
        self.function_pattern = re.compile(
            rf'^{self.optional_whitespace}func\s+'
            rf'(?:\((?P<receiver>[^)]+)\)\s+)?'  # Optional receiver
            rf'(?P<name>{self.identifier})'       # Function name
            rf'(?:\[(?P<generics>[^\]]+)\])?'     # Optional generics
            rf'\s*\((?P<params>[^)]*)\)'          # Parameters
            rf'(?:\s*\((?P<returns>[^)]+)\)|'     # Multiple returns
            rf'\s*(?P<return_type>[^{{]+))?'      # Single return
            rf'(?:\s*\{{|\s*$)',                  # Opening brace or end of line
            re.MULTILINE
        )
        
        # Type patterns
        self.struct_pattern = re.compile(
            rf'^{self.optional_whitespace}type\s+({self.identifier})'
            rf'(?:\[[^\]]+\])?\s+struct\s*\{{',
            re.MULTILINE
        )
        
        self.interface_pattern = re.compile(
            rf'^{self.optional_whitespace}type\s+({self.identifier})'
            rf'(?:\[[^\]]+\])?\s+interface\s*\{{',
            re.MULTILINE
        )
        
        self.type_alias_pattern = re.compile(
            rf'^{self.optional_whitespace}type\s+({self.identifier})'
            rf'(?:\[[^\]]+\])?\s+(?!struct|interface)([^{{]+?)(?:\s*$|\s*//)',
            re.MULTILINE
        )
        
        # Constant and variable patterns
        self.const_pattern = re.compile(
            rf'^{self.optional_whitespace}const\s+'
            rf'(?:\(\s*)?({self.identifier})(?:\s+[^=\n]+)?(?:\s*=|$)',
            re.MULTILINE
        )
        
        self.var_pattern = re.compile(
            rf'^{self.optional_whitespace}var\s+'
            rf'(?:\(\s*)?({self.identifier})(?:\s+[^=\n]+)?(?:\s*=|$)',
            re.MULTILINE
        )
        
        # Method pattern (functions with receivers)
        self.method_pattern = re.compile(
            rf'^\s*func\s*\(\s*(?P<recv_name>{self.identifier})\s+'
            rf'(?P<recv_type>\*?{self.identifier}(?:\[[^\]]+\])?)\s*\)\s+'
            rf'(?P<method_name>{self.identifier})',
            re.MULTILINE
        )
        
        # Struct field pattern
        self.struct_field_pattern = re.compile(
            rf'^\s*({self.identifier}(?:\s*,\s*{self.identifier})*)'
            rf'\s+([^`\n]+?)(?:\s*`[^`]*`)?$',
            re.MULTILINE
        )
        
        # Interface method pattern
        self.interface_method_pattern = re.compile(
            rf'^\s*({self.identifier})\s*\([^)]*\)(?:\s*\([^)]+\)|[^{{]+)?$',
            re.MULTILINE
        )
        
        # Comment patterns
        self.line_comment_pattern = re.compile(r'^\s*//(.*)$', re.MULTILINE)
        self.block_comment_pattern = re.compile(r'/\*([^*]|\*(?!/))*\*/', re.DOTALL)
        
        # go.mod patterns
        self.module_pattern = re.compile(r'^module\s+(.+)$', re.MULTILINE)
        self.require_pattern = re.compile(r'^\s*([^\s]+)\s+(.+)$', re.MULTILINE)
    
    def parse(self, content: str, path: Optional[Path] = None) -> ParseResult:
        """Parse Go source code and extract symbols."""
        # Check if it's a go.mod file
        if path and path.name == 'go.mod':
            return self._parse_go_mod(content, path)
        
        symbols: List[Symbol] = []
        imports: List[Dict[str, Any]] = []
        
        # Extract package name
        package_name = None
        package_match = self.package_pattern.search(content)
        if package_match:
            package_name = package_match.group(1)
        
        # Extract imports
        imports = self._extract_imports(content)
        
        # Extract functions and methods
        symbols.extend(self._extract_functions(content))
        
        # Extract types
        symbols.extend(self._extract_types(content))
        
        # Extract constants and variables
        symbols.extend(self._extract_constants(content))
        symbols.extend(self._extract_variables(content))
        
        # Extract exports (Go exports based on capitalization)
        exports = []
        for symbol in symbols:
            if symbol.name and symbol.name[0].isupper():
                exports.append({
                    'name': symbol.name,
                    'kind': symbol.kind,
                    'line': symbol.line
                })
        
        return ParseResult(
            symbols=symbols,
            imports=imports,
            exports=exports,
            package=package_name,
            language='go'
        )
    
    def _parse_go_mod(self, content: str, path: Path) -> ParseResult:
        """Parse go.mod file for module and dependency information."""
        symbols: List[Symbol] = []
        
        # Extract module declaration
        module_match = self.module_pattern.search(content)
        if module_match:
            module_name = module_match.group(1)
            line_num = self._find_line_number(content, module_match.start())
            
            symbols.append(Symbol(
                name=module_name,
                kind='module',
                line=line_num,
                signature=f"module {module_name}"
            ))
        
        # Extract dependencies
        in_require_block = False
        lines = content.splitlines()
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            if stripped.startswith('require'):
                if stripped.endswith('('):
                    in_require_block = True
                    continue
                else:
                    # Single line require
                    parts = stripped.split()
                    if len(parts) >= 3:
                        dep_name = parts[1]
                        dep_version = parts[2]
                        symbols.append(Symbol(
                            name=dep_name,
                            kind='dependency',
                            line=i,
                            signature=f"require {dep_name} {dep_version}"
                        ))
            elif in_require_block:
                if stripped == ')':
                    in_require_block = False
                    continue
                elif stripped and not stripped.startswith('//'):
                    # Parse dependency in require block
                    require_match = self.require_pattern.match(stripped)
                    if require_match:
                        dep_name = require_match.group(1)
                        dep_version = require_match.group(2)
                        symbols.append(Symbol(
                            name=dep_name,
                            kind='dependency',
                            line=i,
                            signature=f"require {dep_name} {dep_version}"
                        ))
        
        return ParseResult(
            symbols=symbols,
            language='go-mod'
        )
    
    def _extract_imports(self, content: str) -> List[Dict[str, Any]]:
        """Extract import statements."""
        imports = []
        
        # Single imports
        for match in self.import_single_pattern.finditer(content):
            import_path = match.group(1)
            line_num = self._find_line_number(content, match.start())
            
            imports.append({
                'path': import_path,
                'line': line_num,
                'alias': self._extract_import_alias(import_path)
            })
        
        # Block imports
        for match in self.import_block_pattern.finditer(content):
            block_start = match.end()
            block_end = content.find(')', block_start)
            if block_end > 0:
                import_block = content[block_start:block_end]
                base_line = self._find_line_number(content, block_start)
                
                for line in import_block.splitlines():
                    line = line.strip()
                    if line and not line.startswith('//'):
                        # Handle aliased imports
                        if ' ' in line:
                            parts = line.split(None, 1)
                            if len(parts) == 2:
                                alias = parts[0].strip()
                                path = parts[1].strip('"')
                                imports.append({
                                    'path': path,
                                    'alias': alias,
                                    'line': base_line
                                })
                        else:
                            # Regular import
                            path = line.strip('"')
                            imports.append({
                                'path': path,
                                'alias': self._extract_import_alias(path),
                                'line': base_line
                            })
                    base_line += 1
        
        return imports
    
    def _extract_import_alias(self, import_path: str) -> str:
        """Extract the default alias from an import path."""
        # Get the last component of the path
        parts = import_path.split('/')
        return parts[-1]
    
    def _extract_functions(self, content: str) -> List[Symbol]:
        """Extract function and method declarations."""
        symbols = []
        
        for match in self.function_pattern.finditer(content):
            func_name = match.group('name')
            receiver = match.group('receiver')
            generics = match.group('generics')
            params = match.group('params')
            returns = match.group('returns')
            return_type = match.group('return_type')
            
            line_num = self._find_line_number(content, match.start())
            
            # Build signature
            signature_parts = ['func']
            
            # Add receiver if present (making it a method)
            if receiver:
                signature_parts.append(f"({receiver})")
                kind = 'method'
                # Extract receiver type for scope
                recv_match = re.match(rf'\s*{self.identifier}\s+(\*?{self.identifier})', receiver)
                scope = recv_match.group(1) if recv_match else None
            else:
                kind = 'function'
                scope = None
            
            signature_parts.append(func_name)
            
            # Add generics if present
            if generics:
                signature_parts.append(f"[{generics}]")
            
            # Add parameters
            signature_parts.append(f"({params})")
            
            # Add return type
            if returns:
                signature_parts.append(f"({returns})")
            elif return_type:
                signature_parts.append(return_type.strip())
            
            signature = ' '.join(signature_parts)
            signature = self._clean_signature(signature)
            
            # Extract documentation
            doc = self._extract_go_doc(content, match.start())
            
            # Check if exported
            modifiers = []
            if func_name[0].isupper():
                modifiers.append('exported')
            
            symbols.append(Symbol(
                name=func_name,
                kind=kind,
                line=line_num,
                signature=signature,
                doc=doc,
                scope=scope,
                modifiers=modifiers
            ))
        
        return symbols
    
    def _extract_types(self, content: str) -> List[Symbol]:
        """Extract type declarations."""
        symbols = []
        
        # Extract structs
        for match in self.struct_pattern.finditer(content):
            type_name = match.group(1)
            line_num = self._find_line_number(content, match.start())
            
            # Extract full struct definition for signature
            sig_start = match.start()
            sig_end = content.find('{', sig_start)
            signature = content[sig_start:sig_end + 1].strip()
            
            # Extract documentation
            doc = self._extract_go_doc(content, match.start())
            
            # Check if exported
            modifiers = []
            if type_name[0].isupper():
                modifiers.append('exported')
            
            symbols.append(Symbol(
                name=type_name,
                kind='struct',
                line=line_num,
                signature=f"type {type_name} struct",
                doc=doc,
                modifiers=modifiers
            ))
            
            # Extract struct fields
            struct_end, struct_body = self._extract_block_content(content, sig_end)
            if struct_body:
                fields = self._extract_struct_fields(struct_body, type_name, line_num)
                symbols.extend(fields)
        
        # Extract interfaces
        for match in self.interface_pattern.finditer(content):
            type_name = match.group(1)
            line_num = self._find_line_number(content, match.start())
            
            # Extract documentation
            doc = self._extract_go_doc(content, match.start())
            
            # Check if exported
            modifiers = []
            if type_name[0].isupper():
                modifiers.append('exported')
            
            symbols.append(Symbol(
                name=type_name,
                kind='interface',
                line=line_num,
                signature=f"type {type_name} interface",
                doc=doc,
                modifiers=modifiers
            ))
            
            # Extract interface methods
            sig_end = content.find('{', match.start())
            interface_end, interface_body = self._extract_block_content(content, sig_end)
            if interface_body:
                methods = self._extract_interface_methods(interface_body, type_name, line_num)
                symbols.extend(methods)
        
        # Extract type aliases
        for match in self.type_alias_pattern.finditer(content):
            type_name = match.group(1)
            type_def = match.group(2).strip()
            line_num = self._find_line_number(content, match.start())
            
            # Extract documentation
            doc = self._extract_go_doc(content, match.start())
            
            # Check if exported
            modifiers = []
            if type_name[0].isupper():
                modifiers.append('exported')
            
            symbols.append(Symbol(
                name=type_name,
                kind='type',
                line=line_num,
                signature=f"type {type_name} {type_def}",
                doc=doc,
                modifiers=modifiers
            ))
        
        return symbols
    
    def _extract_struct_fields(self, struct_body: str, struct_name: str, 
                              struct_start_line: int) -> List[Symbol]:
        """Extract fields from a struct body."""
        symbols = []
        
        lines = struct_body.splitlines()
        for i, line in enumerate(lines[1:-1], 1):  # Skip opening and closing braces
            stripped = line.strip()
            if not stripped or stripped.startswith('//'):
                continue
            
            field_match = self.struct_field_pattern.match(line)
            if field_match:
                field_names = field_match.group(1)
                field_type = field_match.group(2).strip()
                
                # Handle multiple fields with same type
                for field_name in field_names.split(','):
                    field_name = field_name.strip()
                    
                    modifiers = []
                    if field_name[0].isupper():
                        modifiers.append('exported')
                    
                    # Check for embedded struct
                    if field_name == field_type:
                        modifiers.append('embedded')
                    
                    symbols.append(Symbol(
                        name=f"{struct_name}.{field_name}",
                        kind='field',
                        line=struct_start_line + i,
                        signature=f"{field_name} {field_type}",
                        scope=struct_name,
                        modifiers=modifiers
                    ))
        
        return symbols
    
    def _extract_interface_methods(self, interface_body: str, interface_name: str,
                                  interface_start_line: int) -> List[Symbol]:
        """Extract method signatures from an interface body."""
        symbols = []
        
        lines = interface_body.splitlines()
        for i, line in enumerate(lines[1:-1], 1):  # Skip opening and closing braces
            stripped = line.strip()
            if not stripped or stripped.startswith('//'):
                continue
            
            method_match = self.interface_method_pattern.match(line)
            if method_match:
                method_name = method_match.group(1)
                
                modifiers = []
                if method_name[0].isupper():
                    modifiers.append('exported')
                
                symbols.append(Symbol(
                    name=f"{interface_name}.{method_name}",
                    kind='interface_method',
                    line=interface_start_line + i,
                    signature=stripped,
                    scope=interface_name,
                    modifiers=modifiers
                ))
        
        return symbols
    
    def _extract_constants(self, content: str) -> List[Symbol]:
        """Extract constant declarations."""
        symbols = []
        
        for match in self.const_pattern.finditer(content):
            const_name = match.group(1)
            line_num = self._find_line_number(content, match.start())
            
            # Extract full declaration
            line_start = content.rfind('\n', 0, match.start()) + 1
            line_end = content.find('\n', match.end())
            if line_end == -1:
                line_end = len(content)
            
            signature = content[line_start:line_end].strip()
            signature = self._clean_signature(signature)
            
            # Extract documentation
            doc = self._extract_go_doc(content, match.start())
            
            # Check if exported
            modifiers = []
            if const_name[0].isupper():
                modifiers.append('exported')
            
            symbols.append(Symbol(
                name=const_name,
                kind='constant',
                line=line_num,
                signature=signature,
                doc=doc,
                modifiers=modifiers
            ))
        
        return symbols
    
    def _extract_variables(self, content: str) -> List[Symbol]:
        """Extract variable declarations."""
        symbols = []
        
        for match in self.var_pattern.finditer(content):
            var_name = match.group(1)
            line_num = self._find_line_number(content, match.start())
            
            # Extract full declaration
            line_start = content.rfind('\n', 0, match.start()) + 1
            line_end = content.find('\n', match.end())
            if line_end == -1:
                line_end = len(content)
            
            signature = content[line_start:line_end].strip()
            signature = self._clean_signature(signature)
            
            # Extract documentation
            doc = self._extract_go_doc(content, match.start())
            
            # Check if exported
            modifiers = []
            if var_name[0].isupper():
                modifiers.append('exported')
            
            symbols.append(Symbol(
                name=var_name,
                kind='variable',
                line=line_num,
                signature=signature,
                doc=doc,
                modifiers=modifiers
            ))
        
        return symbols
    
    def _extract_go_doc(self, content: str, position: int) -> Optional[str]:
        """Extract Go documentation comment before a symbol."""
        # Find the start of the line containing the position
        line_start = content.rfind('\n', 0, position) + 1
        
        # Look backwards for documentation comments
        doc_lines = []
        pos = line_start - 1
        
        while pos > 0:
            line_start = content.rfind('\n', 0, pos) + 1
            line_end = pos
            line = content[line_start:line_end].strip()
            
            if line.startswith('//'):
                # Single line comment
                comment_text = line[2:].strip()
                doc_lines.insert(0, comment_text)
                pos = line_start - 1
            elif line.endswith('*/'):
                # End of block comment, find start
                block_start = content.rfind('/*', 0, pos)
                if block_start >= 0:
                    block_content = content[block_start + 2:pos - 2].strip()
                    # Clean block comment
                    for block_line in block_content.splitlines():
                        block_line = block_line.strip()
                        if block_line.startswith('*'):
                            block_line = block_line[1:].strip()
                        if block_line:
                            doc_lines.insert(0, block_line)
                break
            elif not line:
                # Empty line, might continue
                pos = line_start - 1
            else:
                # Non-comment line, stop
                break
        
        return '\n'.join(doc_lines) if doc_lines else None