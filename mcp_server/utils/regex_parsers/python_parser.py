"""Python regex parser based on Pygments patterns.

This parser extracts symbols from Python source code using regular expressions
based on the Pygments Python lexer patterns.
"""

import re
from typing import Dict, List, Any, Optional, Pattern
from pathlib import Path

from ..regex_parser import RegexParser, Symbol, ParseResult


class PythonRegexParser(RegexParser):
    """Regex-based parser for Python source code."""
    
    def get_language(self) -> str:
        return 'python'
    
    def _setup_patterns(self):
        """Set up Python-specific regex patterns."""
        super()._setup_patterns()
        
        # Python keywords that aren't symbol definitions
        self.keywords = {
            'and', 'as', 'assert', 'break', 'continue', 'del', 'elif', 'else',
            'except', 'finally', 'for', 'from', 'global', 'if', 'import', 'in',
            'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
            'try', 'while', 'with', 'yield', 'async', 'await'
        }
        
        # Decorators pattern
        self.decorator_pattern = re.compile(
            rf'^{self.optional_whitespace}@{self.identifier}(?:\.{self.identifier})*(?:\([^)]*\))?{self.optional_whitespace}$',
            re.MULTILINE
        )
        
        # Class definition pattern
        self.class_pattern = re.compile(
            rf'^{self.optional_whitespace}class\s+({self.identifier})'
            rf'(?:\s*\([^)]*\))?{self.optional_whitespace}:',
            re.MULTILINE
        )
        
        # Function/method definition pattern (including async)
        self.function_pattern = re.compile(
            rf'^{self.optional_whitespace}(?:async\s+)?def\s+({self.identifier})'
            rf'{self.optional_whitespace}\([^)]*\)(?:\s*->\s*[^:]+)?{self.optional_whitespace}:',
            re.MULTILINE
        )
        
        # Variable assignment patterns
        # Simple assignment: name = value
        self.simple_assignment_pattern = re.compile(
            rf'^{self.optional_whitespace}({self.identifier}){self.optional_whitespace}=(?!=)',
            re.MULTILINE
        )
        
        # Type annotated assignment: name: Type = value
        self.typed_assignment_pattern = re.compile(
            rf'^{self.optional_whitespace}({self.identifier}){self.optional_whitespace}:'
            rf'{self.optional_whitespace}[^=]+={self.optional_whitespace}',
            re.MULTILINE
        )
        
        # Multiple assignment: a, b, c = values
        self.multiple_assignment_pattern = re.compile(
            rf'^{self.optional_whitespace}({self.identifier}(?:{self.optional_whitespace},{self.optional_whitespace}{self.identifier})+)'
            rf'{self.optional_whitespace}=(?!=)',
            re.MULTILINE
        )
        
        # Global/nonlocal declarations
        self.global_pattern = re.compile(
            rf'^{self.optional_whitespace}global\s+({self.identifier}(?:{self.optional_whitespace},{self.optional_whitespace}{self.identifier})*)',
            re.MULTILINE
        )
        
        self.nonlocal_pattern = re.compile(
            rf'^{self.optional_whitespace}nonlocal\s+({self.identifier}(?:{self.optional_whitespace},{self.optional_whitespace}{self.identifier})*)',
            re.MULTILINE
        )
        
        # Import patterns
        self.import_pattern = re.compile(
            rf'^{self.optional_whitespace}import\s+([^\s]+(?:\s*,\s*[^\s]+)*)',
            re.MULTILINE
        )
        
        self.from_import_pattern = re.compile(
            rf'^{self.optional_whitespace}from\s+([^\s]+)\s+import\s+([^#\n]+)',
            re.MULTILINE
        )
        
        # Docstring patterns
        self.docstring_single = re.compile(
            rf'^{self.optional_whitespace}{self.triple_single_quoted}',
            re.MULTILINE
        )
        
        self.docstring_double = re.compile(
            rf'^{self.optional_whitespace}{self.triple_double_quoted}',
            re.MULTILINE
        )
        
        # Property decorators
        self.property_getter_pattern = re.compile(
            rf'^{self.optional_whitespace}@property{self.optional_whitespace}$',
            re.MULTILINE
        )
        
        self.property_setter_pattern = re.compile(
            rf'^{self.optional_whitespace}@({self.identifier})\.setter{self.optional_whitespace}$',
            re.MULTILINE
        )
        
        # __all__ export pattern
        self.all_pattern = re.compile(
            rf'^{self.optional_whitespace}__all__{self.optional_whitespace}={self.optional_whitespace}\[([^\]]+)\]',
            re.MULTILINE
        )
    
    def parse(self, content: str, path: Optional[Path] = None) -> ParseResult:
        """Parse Python source code and extract symbols."""
        symbols: List[Symbol] = []
        imports: List[Dict[str, Any]] = []
        exports: List[Dict[str, Any]] = []
        
        # Track current scope
        scope_stack: List[str] = []
        indent_stack: List[int] = [0]
        
        # Extract module-level docstring
        module_doc = self._extract_module_docstring(content)
        
        # Process line by line for scope tracking
        lines = content.splitlines(keepends=True)
        current_decorators: List[str] = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                i += 1
                continue
            
            # Track indentation for scope
            indent = len(line) - len(line.lstrip())
            
            # Update scope based on indentation
            while indent_stack and indent < indent_stack[-1]:
                indent_stack.pop()
                if scope_stack:
                    scope_stack.pop()
            
            # Check for decorators
            if stripped.startswith('@'):
                current_decorators.append(stripped)
                i += 1
                continue
            
            # Check for class definition
            class_match = self.class_pattern.match(line)
            if class_match:
                class_name = class_match.group(1)
                
                # Find the full class signature
                signature_lines = [line.rstrip()]
                j = i + 1
                while j < len(lines) and not lines[j].strip().endswith(':'):
                    signature_lines.append(lines[j].rstrip())
                    j += 1
                
                signature = ' '.join(signature_lines)
                signature = self._clean_signature(signature)
                
                # Extract base classes
                bases_match = re.search(rf'{class_name}\s*\(([^)]+)\)', signature)
                modifiers = []
                if bases_match:
                    bases = bases_match.group(1)
                    # Check for common metaclasses or base classes
                    if 'ABCMeta' in bases or 'ABC' in bases:
                        modifiers.append('abstract')
                
                # Check decorators for dataclass, etc.
                for dec in current_decorators:
                    if 'dataclass' in dec:
                        modifiers.append('dataclass')
                    elif 'final' in dec:
                        modifiers.append('final')
                
                symbol = Symbol(
                    name=class_name,
                    kind='class',
                    line=i + 1,
                    signature=signature,
                    scope='.'.join(scope_stack) if scope_stack else None,
                    modifiers=modifiers
                )
                
                # Look for class docstring
                if j + 1 < len(lines):
                    doc = self._extract_docstring_at_line(lines, j + 1)
                    if doc:
                        symbol.doc = doc
                
                symbols.append(symbol)
                
                # Update scope
                scope_stack.append(class_name)
                indent_stack.append(indent + 4)  # Assume 4-space indent
                
                current_decorators = []
                i = j + 1
                continue
            
            # Check for function/method definition
            func_match = self.function_pattern.match(line)
            if func_match:
                func_name = func_match.group(1)
                
                # Find the full function signature
                signature_lines = [line.rstrip()]
                j = i + 1
                while j < len(lines) and not lines[j].strip().endswith(':'):
                    signature_lines.append(lines[j].rstrip())
                    j += 1
                
                signature = ' '.join(signature_lines)
                signature = self._clean_signature(signature)
                
                # Determine function type and modifiers
                kind = 'method' if scope_stack else 'function'
                modifiers = []
                
                if 'async' in signature:
                    modifiers.append('async')
                
                # Check decorators
                is_property = False
                is_setter = False
                for dec in current_decorators:
                    if '@property' in dec:
                        is_property = True
                        kind = 'property'
                    elif '.setter' in dec:
                        is_setter = True
                        kind = 'setter'
                    elif '@staticmethod' in dec:
                        modifiers.append('static')
                    elif '@classmethod' in dec:
                        modifiers.append('classmethod')
                    elif '@abstractmethod' in dec:
                        modifiers.append('abstract')
                
                # Check for special methods
                if func_name.startswith('__') and func_name.endswith('__'):
                    if func_name == '__init__':
                        kind = 'constructor'
                    else:
                        kind = 'magic_method'
                
                symbol = Symbol(
                    name=func_name,
                    kind=kind,
                    line=i + 1,
                    signature=signature,
                    scope='.'.join(scope_stack) if scope_stack else None,
                    modifiers=modifiers
                )
                
                # Look for function docstring
                if j + 1 < len(lines):
                    doc = self._extract_docstring_at_line(lines, j + 1)
                    if doc:
                        symbol.doc = doc
                
                symbols.append(symbol)
                
                # Update scope for nested functions
                if indent > (indent_stack[-1] if indent_stack else 0):
                    scope_stack.append(func_name)
                    indent_stack.append(indent + 4)
                
                current_decorators = []
                i = j + 1
                continue
            
            # Check for variable assignments (only at module or class level)
            if len(scope_stack) <= 1:  # Module level or class level
                # Type annotated assignment
                typed_match = self.typed_assignment_pattern.match(line)
                if typed_match:
                    var_name = typed_match.group(1)
                    if var_name not in self.keywords:
                        # Extract type annotation
                        type_match = re.search(rf'{var_name}\s*:\s*([^=]+)=', line)
                        type_hint = type_match.group(1).strip() if type_match else None
                        
                        kind = 'class_variable' if scope_stack else 'variable'
                        signature = f"{var_name}: {type_hint}" if type_hint else var_name
                        
                        symbols.append(Symbol(
                            name=var_name,
                            kind=kind,
                            line=i + 1,
                            signature=signature,
                            scope='.'.join(scope_stack) if scope_stack else None
                        ))
                
                # Simple assignment
                elif not typed_match:
                    simple_match = self.simple_assignment_pattern.match(line)
                    if simple_match:
                        var_name = simple_match.group(1)
                        # Filter out common non-symbol assignments
                        if (var_name not in self.keywords and 
                            var_name.isupper() or  # Constants
                            var_name.startswith('_') or  # Private vars
                            (scope_stack and not var_name.startswith('self.'))):  # Class vars
                            
                            kind = 'constant' if var_name.isupper() else ('class_variable' if scope_stack else 'variable')
                            
                            symbols.append(Symbol(
                                name=var_name,
                                kind=kind,
                                line=i + 1,
                                signature=var_name,
                                scope='.'.join(scope_stack) if scope_stack else None
                            ))
            
            # Check for imports
            import_match = self.import_pattern.match(line)
            if import_match:
                modules = import_match.group(1).split(',')
                for module in modules:
                    module = module.strip()
                    imports.append({
                        'module': module,
                        'line': i + 1,
                        'type': 'import'
                    })
            
            from_match = self.from_import_pattern.match(line)
            if from_match:
                module = from_match.group(1).strip()
                items = from_match.group(2).strip()
                
                # Handle different import styles
                if items == '*':
                    imports.append({
                        'module': module,
                        'items': '*',
                        'line': i + 1,
                        'type': 'from_import'
                    })
                else:
                    # Parse imported items
                    import_items = []
                    for item in items.split(','):
                        item = item.strip()
                        if ' as ' in item:
                            name, alias = item.split(' as ')
                            import_items.append({'name': name.strip(), 'alias': alias.strip()})
                        else:
                            import_items.append({'name': item})
                    
                    imports.append({
                        'module': module,
                        'items': import_items,
                        'line': i + 1,
                        'type': 'from_import'
                    })
            
            # Check for __all__ exports
            all_match = self.all_pattern.match(line)
            if all_match:
                export_list = all_match.group(1)
                for item in re.findall(r'["\']([^"\']+)["\']', export_list):
                    exports.append({
                        'name': item,
                        'kind': 'explicit',
                        'line': i + 1
                    })
            
            current_decorators = []
            i += 1
        
        # If no explicit exports, consider all module-level symbols as exports
        if not exports:
            for symbol in symbols:
                if not symbol.scope and not symbol.name.startswith('_'):
                    exports.append({
                        'name': symbol.name,
                        'kind': symbol.kind,
                        'line': symbol.line
                    })
        
        return ParseResult(
            symbols=symbols,
            imports=imports,
            exports=exports,
            language='python',
            module_type='module'
        )
    
    def _extract_module_docstring(self, content: str) -> Optional[str]:
        """Extract module-level docstring."""
        # Skip shebang and encoding declarations
        lines = content.splitlines()
        start_line = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if stripped.startswith('"""') or stripped.startswith("'''"):
                return self._extract_docstring_at_line(lines, i)
            else:
                # Hit non-comment, non-docstring line
                break
        
        return None
    
    def _extract_docstring_at_line(self, lines: List[str], line_idx: int) -> Optional[str]:
        """Extract docstring starting at given line index."""
        if line_idx >= len(lines):
            return None
        
        line = lines[line_idx].strip()
        
        # Check for triple quotes
        if line.startswith('"""') or line.startswith("'''"):
            quote = '"""' if line.startswith('"""') else "'''"
            
            # Single line docstring
            if line.count(quote) >= 2:
                return line[3:-3].strip()
            
            # Multi-line docstring
            doc_lines = []
            first_line = line[3:].strip()
            if first_line:
                doc_lines.append(first_line)
            
            for i in range(line_idx + 1, len(lines)):
                line = lines[i].rstrip()
                if quote in line:
                    # Found closing quotes
                    last_line = line[:line.index(quote)].strip()
                    if last_line:
                        doc_lines.append(last_line)
                    break
                else:
                    # Dedent and clean docstring lines
                    stripped = line.strip()
                    if stripped:
                        doc_lines.append(stripped)
            
            return '\n'.join(doc_lines) if doc_lines else None
        
        return None