"""JavaScript/TypeScript regex parser based on Pygments patterns.

This parser extracts symbols from JavaScript and TypeScript source code using
regular expressions based on the Pygments JavaScript lexer patterns.
"""

import re
from typing import Dict, List, Any, Optional, Pattern, Tuple
from pathlib import Path

from ..regex_parser import RegexParser, Symbol, ParseResult


class JavaScriptRegexParser(RegexParser):
    """Regex-based parser for JavaScript and TypeScript source code."""
    
    def get_language(self) -> str:
        return 'javascript'
    
    def _setup_patterns(self):
        """Set up JavaScript-specific regex patterns."""
        super()._setup_patterns()
        
        # JavaScript keywords that aren't symbol definitions
        self.keywords = {
            'abstract', 'await', 'boolean', 'break', 'byte', 'case', 'catch',
            'char', 'continue', 'debugger', 'default', 'delete', 'do', 'double',
            'else', 'enum', 'extends', 'final', 'finally', 'float', 'for',
            'goto', 'if', 'implements', 'import', 'in', 'instanceof', 'int',
            'long', 'native', 'new', 'null', 'package', 'private', 'protected',
            'public', 'return', 'short', 'static', 'super', 'switch', 'synchronized',
            'this', 'throw', 'throws', 'transient', 'try', 'typeof', 'void',
            'volatile', 'while', 'with', 'yield', 'true', 'false', 'undefined',
            'of', 'as', 'from'
        }
        
        # Reserved words that might appear as property names
        self.reserved_words = {
            'constructor', 'prototype', 'arguments', 'caller', 'callee'
        }
        
        # Function patterns (including async, generator, arrow functions)
        self.function_declaration_pattern = re.compile(
            rf'^{self.optional_whitespace}(?:export\s+)?(?:default\s+)?'
            rf'(?:async\s+)?function\s*(\*?)\s*({self.identifier})?'
            rf'{self.optional_whitespace}\([^)]*\)(?:\s*:\s*[^{{]+)?{self.optional_whitespace}\{{',
            re.MULTILINE
        )
        
        # Method patterns (inside classes/objects)
        self.method_pattern = re.compile(
            rf'^{self.optional_whitespace}(?:static\s+)?(?:async\s+)?'
            rf'(?:get\s+|set\s+)?({self.identifier}|\[[^\]]+\])'
            rf'{self.optional_whitespace}\([^)]*\)(?:\s*:\s*[^{{]+)?{self.optional_whitespace}\{{',
            re.MULTILINE
        )
        
        # Arrow function pattern
        self.arrow_function_pattern = re.compile(
            rf'(?:const|let|var)\s+({self.identifier}){self.optional_whitespace}'
            rf'(?::\s*[^=]+)?={self.optional_whitespace}'
            rf'(?:async\s+)?(?:\([^)]*\)|{self.identifier}){self.optional_whitespace}=>'
        )
        
        # Class patterns
        self.class_pattern = re.compile(
            rf'^{self.optional_whitespace}(?:export\s+)?(?:default\s+)?'
            rf'(?:abstract\s+)?class\s+({self.identifier})'
            rf'(?:\s+extends\s+[^{{]+)?(?:\s+implements\s+[^{{]+)?{self.optional_whitespace}\{{',
            re.MULTILINE
        )
        
        # Interface pattern (TypeScript)
        self.interface_pattern = re.compile(
            rf'^{self.optional_whitespace}(?:export\s+)?(?:default\s+)?'
            rf'interface\s+({self.identifier})'
            rf'(?:\s+extends\s+[^{{]+)?{self.optional_whitespace}\{{',
            re.MULTILINE
        )
        
        # Type alias pattern (TypeScript)
        self.type_alias_pattern = re.compile(
            rf'^{self.optional_whitespace}(?:export\s+)?type\s+({self.identifier})'
            rf'{self.optional_whitespace}=',
            re.MULTILINE
        )
        
        # Enum pattern (TypeScript)
        self.enum_pattern = re.compile(
            rf'^{self.optional_whitespace}(?:export\s+)?(?:const\s+)?enum\s+({self.identifier})'
            rf'{self.optional_whitespace}\{{',
            re.MULTILINE
        )
        
        # Variable declaration patterns
        self.var_declaration_pattern = re.compile(
            rf'^{self.optional_whitespace}(?:export\s+)?'
            rf'(const|let|var)\s+({self.identifier}|\{{[^}}]+\}}|\[[^\]]+\])'
            rf'(?:\s*:\s*[^=;]+)?(?:\s*=|;)',
            re.MULTILINE
        )
        
        # Object property method pattern
        self.object_method_pattern = re.compile(
            rf'({self.identifier}){self.optional_whitespace}:'
            rf'{self.optional_whitespace}(?:async\s+)?(?:function\s*)?'
            rf'\([^)]*\)(?:\s*:\s*[^{{]+)?{self.optional_whitespace}(?:\{{|=>)'
        )
        
        # Import patterns
        self.import_pattern = re.compile(
            rf'^{self.optional_whitespace}import\s+'
            rf'(?:({self.identifier})|(?:\*\s+as\s+({self.identifier}))|'
            rf'(?:\{{([^}}]+)\}}))?'
            rf'(?:\s*,\s*(?:({self.identifier})|\{{([^}}]+)\}}))?'
            rf'\s+from\s+["\']([^"\']+)["\']',
            re.MULTILINE
        )
        
        self.require_pattern = re.compile(
            rf'(?:const|let|var)\s+(?:({self.identifier})|\{{([^}}]+)\}})'
            rf'{self.optional_whitespace}={self.optional_whitespace}'
            rf'require\s*\(\s*["\']([^"\']+)["\']\s*\)'
        )
        
        # Export patterns
        self.export_pattern = re.compile(
            rf'^{self.optional_whitespace}export\s+'
            rf'(?:default\s+|(?:\{{([^}}]+)\}}\s+from\s+["\']([^"\']+)["\'])|'
            rf'(?:(const|let|var|function|class|interface|type|enum)\s+))',
            re.MULTILINE
        )
        
        self.module_exports_pattern = re.compile(
            rf'module\.exports{self.optional_whitespace}='
        )
        
        self.exports_property_pattern = re.compile(
            rf'exports\.({self.identifier}){self.optional_whitespace}='
        )
        
        # JSDoc pattern
        self.jsdoc_pattern = re.compile(
            r'/\*\*(?:[^*]|\*(?!/))*\*/',
            re.DOTALL
        )
        
        # Decorator pattern (TypeScript/ES decorators)
        self.decorator_pattern = re.compile(
            rf'^{self.optional_whitespace}@({self.identifier})(?:\([^)]*\))?',
            re.MULTILINE
        )
    
    def parse(self, content: str, path: Optional[Path] = None) -> ParseResult:
        """Parse JavaScript/TypeScript source code and extract symbols."""
        symbols: List[Symbol] = []
        imports: List[Dict[str, Any]] = []
        exports: List[Dict[str, Any]] = []
        
        # Detect module type
        module_type = self._detect_module_type(content)
        
        # Detect if TypeScript
        is_typescript = False
        if path:
            is_typescript = path.suffix in {'.ts', '.tsx'}
        
        # Extract symbols
        symbols.extend(self._extract_functions(content))
        symbols.extend(self._extract_classes(content))
        symbols.extend(self._extract_variables(content))
        
        if is_typescript:
            symbols.extend(self._extract_interfaces(content))
            symbols.extend(self._extract_type_aliases(content))
            symbols.extend(self._extract_enums(content))
        
        # Extract imports
        imports = self._extract_imports(content, module_type)
        
        # Extract exports
        exports = self._extract_exports(content, module_type, symbols)
        
        return ParseResult(
            symbols=symbols,
            imports=imports,
            exports=exports,
            language='typescript' if is_typescript else 'javascript',
            module_type=module_type
        )
    
    def _detect_module_type(self, content: str) -> str:
        """Detect module type (esm, commonjs, or unknown)."""
        # Check for ES modules
        if (re.search(r'^\s*import\s+', content, re.MULTILINE) or
            re.search(r'^\s*export\s+', content, re.MULTILINE)):
            return 'esm'
        
        # Check for CommonJS
        if ('require(' in content or 'module.exports' in content or 
            'exports.' in content):
            return 'commonjs'
        
        return 'unknown'
    
    def _extract_functions(self, content: str) -> List[Symbol]:
        """Extract function declarations."""
        symbols = []
        
        # Function declarations
        for match in self.function_declaration_pattern.finditer(content):
            is_generator = match.group(1) == '*'
            func_name = match.group(2)
            
            if not func_name:  # Anonymous function
                continue
            
            line_num = self._find_line_number(content, match.start())
            
            # Extract full signature
            sig_end = content.find('{', match.start())
            signature = content[match.start():sig_end].strip()
            signature = self._clean_signature(signature)
            
            # Check for async
            is_async = 'async' in signature
            
            # Extract JSDoc
            doc = self._extract_jsdoc_before(content, match.start())
            
            modifiers = []
            if is_async:
                modifiers.append('async')
            if is_generator:
                modifiers.append('generator')
            
            # Check if exported
            if 'export' in signature:
                modifiers.append('export')
            if 'default' in signature:
                modifiers.append('default')
            
            symbols.append(Symbol(
                name=func_name,
                kind='generator' if is_generator else 'function',
                line=line_num,
                signature=signature,
                doc=doc,
                modifiers=modifiers
            ))
        
        # Arrow functions assigned to variables
        for match in self.arrow_function_pattern.finditer(content):
            var_name = match.group(1)
            line_num = self._find_line_number(content, match.start())
            
            # Extract full signature
            signature = match.group(0).strip()
            signature = self._clean_signature(signature)
            
            # Check for async
            is_async = 'async' in signature
            
            # Extract JSDoc
            doc = self._extract_jsdoc_before(content, match.start())
            
            modifiers = ['arrow']
            if is_async:
                modifiers.append('async')
            
            symbols.append(Symbol(
                name=var_name,
                kind='function',
                line=line_num,
                signature=signature,
                doc=doc,
                modifiers=modifiers
            ))
        
        return symbols
    
    def _extract_classes(self, content: str) -> List[Symbol]:
        """Extract class declarations."""
        symbols = []
        
        for match in self.class_pattern.finditer(content):
            class_name = match.group(1)
            line_num = self._find_line_number(content, match.start())
            
            # Extract full signature
            sig_end = content.find('{', match.start())
            signature = content[match.start():sig_end].strip()
            signature = self._clean_signature(signature)
            
            # Extract JSDoc
            doc = self._extract_jsdoc_before(content, match.start())
            
            modifiers = []
            if 'abstract' in signature:
                modifiers.append('abstract')
            if 'export' in signature:
                modifiers.append('export')
            if 'default' in signature:
                modifiers.append('default')
            
            # Extract extends/implements
            extends_match = re.search(rf'extends\s+({self.identifier})', signature)
            if extends_match:
                modifiers.append(f"extends:{extends_match.group(1)}")
            
            implements_match = re.search(r'implements\s+([^{]+)', signature)
            if implements_match:
                modifiers.append(f"implements:{implements_match.group(1).strip()}")
            
            symbols.append(Symbol(
                name=class_name,
                kind='class',
                line=line_num,
                signature=signature,
                doc=doc,
                modifiers=modifiers
            ))
            
            # Extract class members
            class_body_start = sig_end
            class_body_end, _ = self._extract_block_content(content, class_body_start)
            class_content = content[class_body_start:class_body_end]
            
            # Extract methods and properties
            members = self._extract_class_members(class_content, class_name, line_num)
            symbols.extend(members)
        
        return symbols
    
    def _extract_class_members(self, class_content: str, class_name: str, 
                              class_start_line: int) -> List[Symbol]:
        """Extract members from a class body."""
        symbols = []
        
        # Method pattern for class methods
        method_pattern = re.compile(
            rf'^\s*(?:(static)\s+)?(?:(async)\s+)?'
            rf'(?:(get|set)\s+)?({self.identifier}|\[[^\]]+\])'
            rf'\s*\([^)]*\)(?:\s*:\s*[^{{]+)?\s*\{{',
            re.MULTILINE
        )
        
        # Property pattern for class properties
        property_pattern = re.compile(
            rf'^\s*(?:(static)\s+)?(?:(readonly)\s+)?'
            rf'({self.identifier})(?:\s*:\s*[^=;]+)?(?:\s*=|;)',
            re.MULTILINE
        )
        
        # Constructor pattern
        constructor_pattern = re.compile(
            rf'^\s*constructor\s*\([^)]*\)(?:\s*:\s*[^{{]+)?\s*\{{',
            re.MULTILINE
        )
        
        # Extract constructor
        for match in constructor_pattern.finditer(class_content):
            line_offset = class_content[:match.start()].count('\n')
            line_num = class_start_line + line_offset + 1
            
            symbols.append(Symbol(
                name='constructor',
                kind='constructor',
                line=line_num,
                signature='constructor',
                scope=class_name
            ))
        
        # Extract methods
        for match in method_pattern.finditer(class_content):
            is_static = match.group(1) is not None
            is_async = match.group(2) is not None
            accessor = match.group(3)  # get/set
            method_name = match.group(4)
            
            # Handle computed property names
            if method_name.startswith('['):
                method_name = method_name[1:-1]
            
            line_offset = class_content[:match.start()].count('\n')
            line_num = class_start_line + line_offset + 1
            
            # Build signature
            sig_start = match.start()
            sig_end = class_content.find('{', sig_start)
            signature = class_content[sig_start:sig_end].strip()
            
            modifiers = []
            if is_static:
                modifiers.append('static')
            if is_async:
                modifiers.append('async')
            
            kind = 'method'
            if accessor == 'get':
                kind = 'getter'
            elif accessor == 'set':
                kind = 'setter'
            
            symbols.append(Symbol(
                name=f"{class_name}.{method_name}",
                kind=kind,
                line=line_num,
                signature=signature,
                scope=class_name,
                modifiers=modifiers
            ))
        
        # Extract properties
        for match in property_pattern.finditer(class_content):
            is_static = match.group(1) is not None
            is_readonly = match.group(2) is not None
            prop_name = match.group(3)
            
            line_offset = class_content[:match.start()].count('\n')
            line_num = class_start_line + line_offset + 1
            
            modifiers = []
            if is_static:
                modifiers.append('static')
            if is_readonly:
                modifiers.append('readonly')
            
            symbols.append(Symbol(
                name=f"{class_name}.{prop_name}",
                kind='property',
                line=line_num,
                signature=prop_name,
                scope=class_name,
                modifiers=modifiers
            ))
        
        return symbols
    
    def _extract_variables(self, content: str) -> List[Symbol]:
        """Extract variable declarations."""
        symbols = []
        
        for match in self.var_declaration_pattern.finditer(content):
            decl_type = match.group(1)  # const/let/var
            var_pattern = match.group(2)
            
            # Skip destructuring for now
            if var_pattern.startswith('{') or var_pattern.startswith('['):
                continue
            
            line_num = self._find_line_number(content, match.start())
            
            # Extract full declaration
            sig_end = match.end()
            # Find end of statement
            for char in ';{':
                pos = content.find(char, match.start())
                if pos > 0 and pos < sig_end:
                    sig_end = pos
            
            signature = content[match.start():sig_end].strip()
            signature = self._clean_signature(signature)
            
            # Check if it's a function assignment
            if '=> ' in signature or 'function' in signature:
                continue  # Already handled by function extraction
            
            modifiers = [decl_type]
            if 'export' in signature:
                modifiers.append('export')
            
            # Determine kind
            kind = 'constant' if decl_type == 'const' else 'variable'
            
            symbols.append(Symbol(
                name=var_pattern,
                kind=kind,
                line=line_num,
                signature=signature,
                modifiers=modifiers
            ))
        
        return symbols
    
    def _extract_interfaces(self, content: str) -> List[Symbol]:
        """Extract TypeScript interfaces."""
        symbols = []
        
        for match in self.interface_pattern.finditer(content):
            interface_name = match.group(1)
            line_num = self._find_line_number(content, match.start())
            
            # Extract full signature
            sig_end = content.find('{', match.start())
            signature = content[match.start():sig_end].strip()
            signature = self._clean_signature(signature)
            
            # Extract JSDoc
            doc = self._extract_jsdoc_before(content, match.start())
            
            modifiers = []
            if 'export' in signature:
                modifiers.append('export')
            
            symbols.append(Symbol(
                name=interface_name,
                kind='interface',
                line=line_num,
                signature=signature,
                doc=doc,
                modifiers=modifiers
            ))
        
        return symbols
    
    def _extract_type_aliases(self, content: str) -> List[Symbol]:
        """Extract TypeScript type aliases."""
        symbols = []
        
        for match in self.type_alias_pattern.finditer(content):
            type_name = match.group(1)
            line_num = self._find_line_number(content, match.start())
            
            # Extract full type definition
            sig_start = match.start()
            sig_end = content.find('\n', sig_start)
            signature = content[sig_start:sig_end].strip()
            signature = self._clean_signature(signature)
            
            # Extract JSDoc
            doc = self._extract_jsdoc_before(content, match.start())
            
            modifiers = []
            if 'export' in signature:
                modifiers.append('export')
            
            symbols.append(Symbol(
                name=type_name,
                kind='type',
                line=line_num,
                signature=signature,
                doc=doc,
                modifiers=modifiers
            ))
        
        return symbols
    
    def _extract_enums(self, content: str) -> List[Symbol]:
        """Extract TypeScript enums."""
        symbols = []
        
        for match in self.enum_pattern.finditer(content):
            enum_name = match.group(1)
            line_num = self._find_line_number(content, match.start())
            
            # Extract full signature
            sig_end = content.find('{', match.start())
            signature = content[match.start():sig_end].strip()
            signature = self._clean_signature(signature)
            
            # Extract JSDoc
            doc = self._extract_jsdoc_before(content, match.start())
            
            modifiers = []
            if 'export' in signature:
                modifiers.append('export')
            if 'const' in signature:
                modifiers.append('const')
            
            symbols.append(Symbol(
                name=enum_name,
                kind='enum',
                line=line_num,
                signature=signature,
                doc=doc,
                modifiers=modifiers
            ))
        
        return symbols
    
    def _extract_imports(self, content: str, module_type: str) -> List[Dict[str, Any]]:
        """Extract import statements."""
        imports = []
        
        if module_type == 'esm' or module_type == 'unknown':
            # ES6 imports
            for match in self.import_pattern.finditer(content):
                line_num = self._find_line_number(content, match.start())
                module_path = match.group(6)
                
                import_info = {
                    'module': module_path,
                    'line': line_num,
                    'type': 'esm'
                }
                
                # Default import
                if match.group(1):
                    import_info['default'] = match.group(1)
                
                # Namespace import (* as name)
                if match.group(2):
                    import_info['namespace'] = match.group(2)
                
                # Named imports
                named_imports = []
                for group_idx in [3, 5]:  # Two possible positions for named imports
                    if match.group(group_idx):
                        import_list = match.group(group_idx)
                        for item in import_list.split(','):
                            item = item.strip()
                            if ' as ' in item:
                                name, alias = item.split(' as ')
                                named_imports.append({
                                    'name': name.strip(),
                                    'alias': alias.strip()
                                })
                            else:
                                named_imports.append({'name': item})
                
                if named_imports:
                    import_info['names'] = named_imports
                
                imports.append(import_info)
        
        if module_type == 'commonjs' or module_type == 'unknown':
            # CommonJS requires
            for match in self.require_pattern.finditer(content):
                line_num = self._find_line_number(content, match.start())
                module_path = match.group(3)
                
                import_info = {
                    'module': module_path,
                    'line': line_num,
                    'type': 'commonjs'
                }
                
                # Variable name
                if match.group(1):
                    import_info['name'] = match.group(1)
                
                # Destructured imports
                if match.group(2):
                    names = []
                    for item in match.group(2).split(','):
                        item = item.strip()
                        if ':' in item:  # Renamed destructuring
                            name, alias = item.split(':')
                            names.append({
                                'name': name.strip(),
                                'alias': alias.strip()
                            })
                        else:
                            names.append({'name': item})
                    import_info['names'] = names
                
                imports.append(import_info)
        
        return imports
    
    def _extract_exports(self, content: str, module_type: str, 
                        symbols: List[Symbol]) -> List[Dict[str, Any]]:
        """Extract export statements."""
        exports = []
        
        if module_type == 'esm' or module_type == 'unknown':
            # ES6 exports
            for match in self.export_pattern.finditer(content):
                line_num = self._find_line_number(content, match.start())
                
                # Re-export from another module
                if match.group(2):
                    export_names = match.group(1)
                    from_module = match.group(2)
                    
                    for name in export_names.split(','):
                        name = name.strip()
                        exports.append({
                            'name': name,
                            'kind': 're-export',
                            'from': from_module,
                            'line': line_num
                        })
                
                # Default export
                elif 'default' in match.group(0):
                    exports.append({
                        'name': 'default',
                        'kind': 'default',
                        'line': line_num
                    })
            
            # Named exports from symbols
            for symbol in symbols:
                if 'export' in symbol.modifiers:
                    export_info = {
                        'name': symbol.name,
                        'kind': symbol.kind,
                        'line': symbol.line
                    }
                    if 'default' in symbol.modifiers:
                        export_info['default'] = True
                    exports.append(export_info)
        
        if module_type == 'commonjs' or module_type == 'unknown':
            # module.exports
            for match in self.module_exports_pattern.finditer(content):
                line_num = self._find_line_number(content, match.start())
                exports.append({
                    'name': 'default',
                    'kind': 'commonjs',
                    'line': line_num
                })
            
            # exports.property
            for match in self.exports_property_pattern.finditer(content):
                prop_name = match.group(1)
                line_num = self._find_line_number(content, match.start())
                exports.append({
                    'name': prop_name,
                    'kind': 'commonjs',
                    'line': line_num
                })
        
        return exports
    
    def _extract_jsdoc_before(self, content: str, position: int) -> Optional[str]:
        """Extract JSDoc comment before a position."""
        # Find the last JSDoc before this position
        jsdoc_matches = list(self.jsdoc_pattern.finditer(content[:position]))
        if not jsdoc_matches:
            return None
        
        # Get the last JSDoc
        last_jsdoc = jsdoc_matches[-1]
        jsdoc_end = last_jsdoc.end()
        
        # Check if there's only whitespace between JSDoc and position
        between = content[jsdoc_end:position].strip()
        if between and not all(c in '@' for c in between):  # Allow decorators
            return None
        
        # Extract and clean JSDoc content
        jsdoc_text = last_jsdoc.group(0)
        # Remove /** and */
        jsdoc_text = jsdoc_text[3:-2]
        
        # Clean each line
        lines = []
        for line in jsdoc_text.splitlines():
            line = line.strip()
            if line.startswith('*'):
                line = line[1:].strip()
            if line:
                lines.append(line)
        
        return '\n'.join(lines) if lines else None