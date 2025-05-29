# Jedi Documentation

## Overview and Key Features

Jedi is a static analysis library for Python that provides code completion, definition finding, reference tracking, and other IDE-like features. It understands Python code without executing it, making it safe and fast for development tools.

### Key Features
- **Code Completion**: Context-aware completions with type inference
- **Goto Definition**: Find where functions, classes, and variables are defined
- **Find References**: Locate all usages of a symbol
- **Rename Refactoring**: Safely rename symbols across a codebase
- **Type Inference**: Understand variable types without type hints
- **Docstring Support**: Extract and format documentation
- **Signature Help**: Function parameter information
- **Static Analysis**: No code execution required
- **Python 2 & 3**: Supports multiple Python versions

## Installation and Basic Setup

### Installation

```bash
# Basic installation
pip install jedi

# For development with latest features
pip install -e git+https://github.com/davidhalter/jedi.git#egg=jedi
```

### Basic Setup

```python
import jedi

# Create a script analysis
script = jedi.Script(
    source='import json\njson.lo',
    path='example.py'
)

# Get completions
completions = script.complete(2, 7)  # line 2, column 7
for completion in completions:
    print(completion.name, completion.type)

# Get definitions
script = jedi.Script(
    source='import os\nos.path.join',
    path='example.py'
)
definitions = script.goto(2, 11)  # line 2, column 11
for definition in definitions:
    print(definition.module_path, definition.line, definition.column)
```

## MCP Server Use Cases

### 1. Code Intelligence Service

```python
import jedi
from typing import List, Dict, Any, Optional
from pathlib import Path
import ast

class CodeIntelligenceService:
    """Provide code intelligence features using Jedi."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.project = jedi.Project(path=project_root)
    
    def get_completions(self, file_path: str, line: int, column: int,
                       source: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get code completions at a specific position."""
        if source is None:
            with open(file_path, 'r') as f:
                source = f.read()
        
        script = jedi.Script(
            source=source,
            path=file_path,
            project=self.project
        )
        
        completions = []
        for completion in script.complete(line, column):
            completions.append({
                'name': completion.name,
                'type': completion.type,
                'description': completion.description,
                'docstring': completion.docstring(),
                'module': completion.module_name,
                'is_keyword': completion.is_keyword,
                'full_name': completion.full_name,
                'signature': self._get_signature(completion)
            })
        
        return completions
    
    def _get_signature(self, completion) -> Optional[str]:
        """Extract function signature if available."""
        try:
            signatures = completion.get_signatures()
            if signatures:
                return str(signatures[0])
        except:
            pass
        return None
    
    def goto_definition(self, file_path: str, line: int, column: int,
                       source: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find symbol definitions."""
        if source is None:
            with open(file_path, 'r') as f:
                source = f.read()
        
        script = jedi.Script(
            source=source,
            path=file_path,
            project=self.project
        )
        
        definitions = []
        for definition in script.goto(line, column, follow_imports=True):
            definitions.append({
                'name': definition.name,
                'type': definition.type,
                'module_path': str(definition.module_path) if definition.module_path else None,
                'line': definition.line,
                'column': definition.column,
                'description': definition.description,
                'docstring': definition.docstring(),
                'full_name': definition.full_name
            })
        
        return definitions
    
    def find_references(self, file_path: str, line: int, column: int,
                       source: Optional[str] = None,
                       include_definitions: bool = True) -> List[Dict[str, Any]]:
        """Find all references to a symbol."""
        if source is None:
            with open(file_path, 'r') as f:
                source = f.read()
        
        script = jedi.Script(
            source=source,
            path=file_path,
            project=self.project
        )
        
        references = []
        for ref in script.get_references(line, column, include_builtins=False):
            references.append({
                'module_path': str(ref.module_path) if ref.module_path else None,
                'line': ref.line,
                'column': ref.column,
                'name': ref.name,
                'is_definition': ref.is_definition
            })
        
        if not include_definitions:
            references = [r for r in references if not r['is_definition']]
        
        return references
    
    def get_signature_help(self, file_path: str, line: int, column: int,
                          source: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get signature help for function calls."""
        if source is None:
            with open(file_path, 'r') as f:
                source = f.read()
        
        script = jedi.Script(
            source=source,
            path=file_path,
            project=self.project
        )
        
        signatures = script.get_signatures(line, column)
        if not signatures:
            return None
        
        sig = signatures[0]
        return {
            'name': sig.name,
            'params': [
                {
                    'name': param.name,
                    'description': param.description,
                    'type_hint': param.get_type_hint()
                }
                for param in sig.params
            ],
            'index': sig.index,
            'docstring': sig.docstring()
        }
```

### 2. Code Navigation Engine

```python
import jedi
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path
import networkx as nx

class CodeNavigationEngine:
    """Navigate code relationships using Jedi."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.project = jedi.Project(path=project_root)
        self.dependency_graph = nx.DiGraph()
    
    def analyze_imports(self, file_path: str) -> List[Dict[str, Any]]:
        """Analyze all imports in a file."""
        with open(file_path, 'r') as f:
            source = f.read()
        
        script = jedi.Script(
            source=source,
            path=file_path,
            project=self.project
        )
        
        imports = []
        for name in script.get_names(all_scopes=True, definitions=True):
            if name.type in ['import_name', 'import_from']:
                import_info = {
                    'name': name.name,
                    'full_name': name.full_name,
                    'line': name.line,
                    'column': name.column,
                    'module_name': name.get_definition_start_position(),
                    'is_definition': name.is_definition()
                }
                
                # Try to resolve the import
                try:
                    definitions = name.goto()
                    if definitions:
                        import_info['resolved_path'] = str(definitions[0].module_path)
                except:
                    pass
                
                imports.append(import_info)
        
        return imports
    
    def build_call_graph(self, file_path: str) -> nx.DiGraph:
        """Build a call graph for functions in a file."""
        with open(file_path, 'r') as f:
            source = f.read()
        
        script = jedi.Script(
            source=source,
            path=file_path,
            project=self.project
        )
        
        graph = nx.DiGraph()
        
        # Get all function definitions
        functions = {}
        for name in script.get_names(all_scopes=True, definitions=True):
            if name.type == 'function':
                functions[name.name] = name
                graph.add_node(name.full_name or name.name, 
                             line=name.line,
                             type='function')
        
        # Analyze function bodies for calls
        for func_name, func_def in functions.items():
            # Get the function's scope
            func_scope = self._get_function_scope(source, func_def.line)
            if func_scope:
                # Find all calls within this function
                calls = self._find_function_calls(func_scope, func_def.line)
                for called_func in calls:
                    if called_func in functions:
                        graph.add_edge(
                            func_def.full_name or func_name,
                            functions[called_func].full_name or called_func
                        )
        
        return graph
    
    def _get_function_scope(self, source: str, start_line: int) -> Optional[str]:
        """Extract function body source."""
        lines = source.split('\n')
        if start_line > len(lines):
            return None
        
        # Simple extraction - can be improved with AST
        func_lines = []
        indent_level = None
        
        for i in range(start_line - 1, len(lines)):
            line = lines[i]
            if not line.strip():
                continue
            
            current_indent = len(line) - len(line.lstrip())
            
            if indent_level is None:
                indent_level = current_indent
            elif current_indent <= indent_level and i > start_line - 1:
                break
            
            func_lines.append(line)
        
        return '\n'.join(func_lines)
    
    def _find_function_calls(self, source: str, base_line: int) -> Set[str]:
        """Find function calls in source code."""
        calls = set()
        
        # Parse with AST for accurate call detection
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        calls.add(node.func.id)
                    elif isinstance(node.func, ast.Attribute):
                        calls.add(node.func.attr)
        except:
            pass
        
        return calls
    
    def find_unused_code(self, file_path: str) -> List[Dict[str, Any]]:
        """Find potentially unused functions and classes."""
        with open(file_path, 'r') as f:
            source = f.read()
        
        script = jedi.Script(
            source=source,
            path=file_path,
            project=self.project
        )
        
        unused = []
        
        # Get all definitions
        for name in script.get_names(all_scopes=False, definitions=True):
            if name.type in ['function', 'class'] and not name.name.startswith('_'):
                # Check if it has any references
                refs = script.get_references(name.line, name.column)
                
                # Filter out the definition itself
                usage_refs = [r for r in refs if not r.is_definition]
                
                if not usage_refs:
                    unused.append({
                        'name': name.name,
                        'type': name.type,
                        'line': name.line,
                        'column': name.column,
                        'full_name': name.full_name
                    })
        
        return unused
```

### 3. Type Analysis Service

```python
import jedi
from typing import Dict, List, Any, Optional, Set
import ast

class TypeAnalysisService:
    """Analyze and infer types using Jedi."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.project = jedi.Project(path=project_root)
    
    def infer_variable_types(self, file_path: str, 
                           source: Optional[str] = None) -> Dict[str, List[str]]:
        """Infer types for all variables in a file."""
        if source is None:
            with open(file_path, 'r') as f:
                source = f.read()
        
        script = jedi.Script(
            source=source,
            path=file_path,
            project=self.project
        )
        
        variable_types = {}
        
        for name in script.get_names(all_scopes=True):
            if name.type == 'name' and name.is_definition():
                # Get inferred type
                inferred = script.infer(name.line, name.column)
                
                types = []
                for inference in inferred:
                    type_name = inference.name
                    if inference.module_name:
                        type_name = f"{inference.module_name}.{type_name}"
                    types.append(type_name)
                
                if types:
                    variable_types[name.name] = types
        
        return variable_types
    
    def get_function_types(self, file_path: str,
                         source: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extract function signatures with type information."""
        if source is None:
            with open(file_path, 'r') as f:
                source = f.read()
        
        script = jedi.Script(
            source=source,
            path=file_path,
            project=self.project
        )
        
        functions = []
        
        for name in script.get_names(all_scopes=True, definitions=True):
            if name.type == 'function':
                func_info = {
                    'name': name.name,
                    'line': name.line,
                    'params': [],
                    'return_type': None
                }
                
                # Get function definition
                definitions = name.goto()
                if definitions:
                    definition = definitions[0]
                    
                    # Get parameter types
                    try:
                        signatures = definition.get_signatures()
                        if signatures:
                            sig = signatures[0]
                            for param in sig.params:
                                param_info = {
                                    'name': param.name,
                                    'type': param.get_type_hint(),
                                    'default': param.get_default_value()
                                }
                                func_info['params'].append(param_info)
                    except:
                        pass
                    
                    # Try to infer return type
                    func_info['return_type'] = self._infer_return_type(
                        source, name.line
                    )
                
                functions.append(func_info)
        
        return functions
    
    def _infer_return_type(self, source: str, func_line: int) -> Optional[str]:
        """Attempt to infer function return type."""
        try:
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if (isinstance(node, ast.FunctionDef) and 
                    hasattr(node, 'lineno') and 
                    node.lineno == func_line):
                    
                    # Check for type annotation
                    if node.returns:
                        return ast.unparse(node.returns)
                    
                    # Simple inference from return statements
                    return_types = set()
                    for child in ast.walk(node):
                        if isinstance(child, ast.Return) and child.value:
                            # Very basic type inference
                            if isinstance(child.value, ast.Constant):
                                return_types.add(type(child.value.value).__name__)
                            elif isinstance(child.value, ast.List):
                                return_types.add('list')
                            elif isinstance(child.value, ast.Dict):
                                return_types.add('dict')
                    
                    if return_types:
                        return ' | '.join(return_types)
        except:
            pass
        
        return None
    
    def check_type_consistency(self, file_path: str) -> List[Dict[str, Any]]:
        """Check for potential type inconsistencies."""
        with open(file_path, 'r') as f:
            source = f.read()
        
        script = jedi.Script(
            source=source,
            path=file_path,
            project=self.project
        )
        
        issues = []
        
        # Track variable type changes
        var_types = {}
        
        for name in script.get_names(all_scopes=True):
            if name.type == 'name':
                # Get current inferred type
                inferred = script.infer(name.line, name.column)
                
                current_types = set()
                for inf in inferred:
                    current_types.add(inf.name)
                
                if name.name in var_types:
                    # Check if type changed
                    if current_types != var_types[name.name]['types']:
                        issues.append({
                            'variable': name.name,
                            'line': name.line,
                            'previous_types': list(var_types[name.name]['types']),
                            'current_types': list(current_types),
                            'previous_line': var_types[name.name]['line']
                        })
                
                var_types[name.name] = {
                    'types': current_types,
                    'line': name.line
                }
        
        return issues
```

### 4. Refactoring Assistant

```python
import jedi
from typing import List, Dict, Tuple, Optional
import difflib

class RefactoringAssistant:
    """Assist with code refactoring using Jedi."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.project = jedi.Project(path=project_root)
    
    def rename_symbol(self, file_path: str, line: int, column: int,
                     new_name: str) -> List[Dict[str, Any]]:
        """Rename a symbol across the codebase."""
        with open(file_path, 'r') as f:
            source = f.read()
        
        script = jedi.Script(
            source=source,
            path=file_path,
            project=self.project
        )
        
        # Get all references
        references = script.get_references(line, column, include_builtins=False)
        
        changes = []
        files_content = {}
        
        for ref in references:
            file_path = str(ref.module_path) if ref.module_path else file_path
            
            # Load file content if not already loaded
            if file_path not in files_content:
                with open(file_path, 'r') as f:
                    files_content[file_path] = f.read().splitlines()
            
            # Calculate change
            line_content = files_content[file_path][ref.line - 1]
            old_name = ref.name
            
            # Simple replacement (can be improved)
            new_line = line_content[:ref.column] + new_name + \
                      line_content[ref.column + len(old_name):]
            
            changes.append({
                'file': file_path,
                'line': ref.line,
                'column': ref.column,
                'old_text': line_content,
                'new_text': new_line,
                'old_name': old_name,
                'new_name': new_name
            })
        
        return changes
    
    def extract_function(self, file_path: str, start_line: int, 
                        end_line: int, function_name: str) -> Dict[str, Any]:
        """Extract code block into a new function."""
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # Extract the selected code
        selected_code = lines[start_line-1:end_line]
        
        # Analyze variables used in the selection
        script = jedi.Script(
            source=''.join(selected_code),
            path=file_path,
            project=self.project
        )
        
        # Find variables that need to be parameters
        used_vars = set()
        defined_vars = set()
        
        for name in script.get_names(all_scopes=True):
            if name.type == 'name':
                if name.is_definition():
                    defined_vars.add(name.name)
                else:
                    used_vars.add(name.name)
        
        # Parameters are variables used but not defined
        parameters = used_vars - defined_vars
        
        # Find variables that need to be returned
        # (defined in selection and used after)
        full_script = jedi.Script(
            source=''.join(lines),
            path=file_path,
            project=self.project
        )
        
        returns = []
        for var in defined_vars:
            # Check if used after the selection
            for name in full_script.get_names(all_scopes=True):
                if (name.name == var and 
                    name.line > end_line and 
                    not name.is_definition()):
                    returns.append(var)
                    break
        
        # Generate function
        indent = self._detect_indent(selected_code[0])
        func_def = f"{indent}def {function_name}({', '.join(parameters)}):\n"
        
        # Add function body with additional indent
        body_indent = '    '
        for line in selected_code:
            func_def += body_indent + line
        
        # Add return statement if needed
        if returns:
            func_def += f"\n{indent}{body_indent}return {', '.join(returns)}\n"
        
        # Generate function call
        call = f"{indent}{function_name}({', '.join(parameters)})"
        if returns:
            call = f"{', '.join(returns)} = {call}"
        
        return {
            'function_definition': func_def,
            'function_call': call,
            'parameters': list(parameters),
            'returns': returns,
            'start_line': start_line,
            'end_line': end_line
        }
    
    def _detect_indent(self, line: str) -> str:
        """Detect indentation of a line."""
        return line[:len(line) - len(line.lstrip())]
    
    def find_duplicate_code(self, file_path: str, 
                          min_lines: int = 5) -> List[Dict[str, Any]]:
        """Find duplicate code blocks."""
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # Simple duplicate detection
        duplicates = []
        
        for i in range(len(lines) - min_lines):
            block1 = lines[i:i+min_lines]
            
            for j in range(i + min_lines, len(lines) - min_lines):
                block2 = lines[j:j+min_lines]
                
                # Calculate similarity
                similarity = difflib.SequenceMatcher(
                    None, 
                    ''.join(block1), 
                    ''.join(block2)
                ).ratio()
                
                if similarity > 0.9:  # 90% similar
                    duplicates.append({
                        'block1_start': i + 1,
                        'block1_end': i + min_lines,
                        'block2_start': j + 1,
                        'block2_end': j + min_lines,
                        'similarity': similarity,
                        'lines': min_lines
                    })
        
        return duplicates
```

## Code Examples

### Basic Completion

```python
import jedi

# Simple completion
source = """
import os
os.pa
"""

script = jedi.Script(source, path='example.py')
completions = script.complete(3, 5)

for c in completions:
    print(f"{c.name}: {c.type} - {c.description}")
```

### Advanced Analysis

```python
# Analyze a complex file
source = """
class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, x: int, y: int) -> int:
        return x + y
    
    def multiply(self, x: int, y: int) -> int:
        return x * y

calc = Calculator()
result = calc.add(5, 3)
"""

script = jedi.Script(source)

# Get all names
for name in script.get_names():
    print(f"{name.name} ({name.type}) at line {name.line}")

# Infer type of 'result'
inferred = script.infer(12, 0)  # line 12, column 0
for inf in inferred:
    print(f"result is: {inf.name}")
```

### Working with Projects

```python
# Create a project for better analysis
project = jedi.Project(
    path='/path/to/project',
    added_sys_path=['/path/to/venv/lib/python3.9/site-packages']
)

# Use project in analysis
script = jedi.Script(
    source=source,
    path='/path/to/project/module.py',
    project=project
)
```

## Best Practices

### 1. Performance Optimization

```python
import functools
import time

class CachedJediAnalyzer:
    """Jedi analyzer with caching for performance."""
    
    def __init__(self, cache_size: int = 128):
        self.cache_size = cache_size
        self._script_cache = {}
    
    @functools.lru_cache(maxsize=256)
    def _get_completions_cached(self, source_hash: int, line: int, 
                               column: int) -> List[str]:
        """Cached completion results."""
        script = self._get_script(source_hash)
        return [c.name for c in script.complete(line, column)]
    
    def _get_script(self, source_hash: int) -> jedi.Script:
        """Get cached script object."""
        if source_hash not in self._script_cache:
            # Script will be created with the actual source
            # This is a placeholder
            pass
        return self._script_cache[source_hash]
    
    def get_completions(self, source: str, line: int, column: int) -> List[str]:
        """Get completions with caching."""
        source_hash = hash(source)
        
        # Store script in cache
        if source_hash not in self._script_cache:
            if len(self._script_cache) >= self.cache_size:
                # Remove oldest entry
                oldest = next(iter(self._script_cache))
                del self._script_cache[oldest]
            
            self._script_cache[source_hash] = jedi.Script(source)
        
        return self._get_completions_cached(source_hash, line, column)
```

### 2. Error Handling

```python
def safe_jedi_operation(func):
    """Decorator for safe Jedi operations."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except jedi.InvalidInput as e:
            print(f"Invalid input: {e}")
            return []
        except Exception as e:
            print(f"Jedi error: {e}")
            return []
    return wrapper

@safe_jedi_operation
def get_definitions(source: str, line: int, column: int):
    script = jedi.Script(source)
    return script.goto(line, column)
```

### 3. Incremental Analysis

```python
class IncrementalAnalyzer:
    """Incremental code analysis with Jedi."""
    
    def __init__(self):
        self.last_source = ""
        self.last_script = None
        self.last_analysis_time = 0
    
    def analyze(self, source: str, force: bool = False) -> jedi.Script:
        """Analyze source code incrementally."""
        current_time = time.time()
        
        # Check if we need to reanalyze
        if (not force and 
            source == self.last_source and 
            current_time - self.last_analysis_time < 1.0):
            return self.last_script
        
        # Create new script
        self.last_script = jedi.Script(source)
        self.last_source = source
        self.last_analysis_time = current_time
        
        return self.last_script
```

### 4. Integration Patterns

```python
class JediLanguageServer:
    """Language server protocol implementation with Jedi."""
    
    def __init__(self, workspace_root: str):
        self.project = jedi.Project(path=workspace_root)
        self.open_documents = {}
    
    def did_open(self, uri: str, source: str):
        """Handle document open."""
        self.open_documents[uri] = {
            'source': source,
            'script': jedi.Script(source, path=uri, project=self.project)
        }
    
    def did_change(self, uri: str, source: str):
        """Handle document change."""
        if uri in self.open_documents:
            self.open_documents[uri]['source'] = source
            self.open_documents[uri]['script'] = jedi.Script(
                source, path=uri, project=self.project
            )
    
    def completion(self, uri: str, line: int, character: int):
        """Provide completions."""
        if uri not in self.open_documents:
            return []
        
        script = self.open_documents[uri]['script']
        completions = script.complete(line + 1, character)
        
        return [
            {
                'label': c.name,
                'kind': self._get_completion_kind(c.type),
                'detail': c.description,
                'documentation': c.docstring()
            }
            for c in completions
        ]
    
    def _get_completion_kind(self, jedi_type: str) -> int:
        """Map Jedi types to LSP completion kinds."""
        mapping = {
            'module': 9,
            'class': 7,
            'function': 3,
            'param': 6,
            'variable': 6,
            'keyword': 14,
        }
        return mapping.get(jedi_type, 1)
```

## Performance Tips

### 1. Batch Operations

```python
def batch_analyze_files(file_paths: List[str], project: jedi.Project):
    """Analyze multiple files efficiently."""
    results = {}
    
    for file_path in file_paths:
        with open(file_path, 'r') as f:
            source = f.read()
        
        # Create script once per file
        script = jedi.Script(source, path=file_path, project=project)
        
        # Perform multiple analyses
        results[file_path] = {
            'imports': extract_imports(script),
            'functions': extract_functions(script),
            'classes': extract_classes(script),
            'global_vars': extract_globals(script)
        }
    
    return results

def extract_imports(script: jedi.Script) -> List[Dict[str, Any]]:
    imports = []
    for name in script.get_names(all_scopes=True, definitions=True):
        if name.type in ['import_name', 'import_from']:
            imports.append({
                'name': name.name,
                'line': name.line,
                'full_name': name.full_name
            })
    return imports
```

### 2. Lazy Loading

```python
class LazyJediProject:
    """Lazy-loading Jedi project."""
    
    def __init__(self, root_path: str):
        self.root_path = root_path
        self._project = None
        self._scripts = {}
    
    @property
    def project(self):
        if self._project is None:
            self._project = jedi.Project(path=self.root_path)
        return self._project
    
    def get_script(self, file_path: str, source: Optional[str] = None):
        """Get or create script with lazy loading."""
        if file_path not in self._scripts:
            if source is None:
                with open(file_path, 'r') as f:
                    source = f.read()
            
            self._scripts[file_path] = jedi.Script(
                source,
                path=file_path,
                project=self.project
            )
        
        return self._scripts[file_path]
```

### 3. Parallel Processing

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing

def analyze_file(args):
    """Analyze a single file (for multiprocessing)."""
    file_path, project_path = args
    
    # Create new project in subprocess
    project = jedi.Project(path=project_path)
    
    with open(file_path, 'r') as f:
        source = f.read()
    
    script = jedi.Script(source, path=file_path, project=project)
    
    # Perform analysis
    return {
        'path': file_path,
        'functions': len([n for n in script.get_names() if n.type == 'function']),
        'classes': len([n for n in script.get_names() if n.type == 'class']),
        'lines': len(source.splitlines())
    }

def parallel_analysis(file_paths: List[str], project_path: str):
    """Analyze files in parallel."""
    # Use processes for CPU-bound analysis
    with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        args = [(fp, project_path) for fp in file_paths]
        results = list(executor.map(analyze_file, args))
    
    return results
```

### 4. Memory Management

```python
import gc
import weakref

class ManagedJediCache:
    """Memory-managed Jedi script cache."""
    
    def __init__(self, max_memory_mb: int = 100):
        self.max_memory = max_memory_mb * 1024 * 1024
        self.cache = weakref.WeakValueDictionary()
        self.strong_refs = []
        self.memory_used = 0
    
    def get_script(self, file_path: str, source: str) -> jedi.Script:
        """Get script with memory management."""
        cache_key = f"{file_path}:{hash(source)}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Create new script
        script = jedi.Script(source, path=file_path)
        
        # Estimate memory usage
        script_size = len(source) * 2  # Rough estimate
        
        # Check memory limit
        if self.memory_used + script_size > self.max_memory:
            self._cleanup()
        
        # Add to cache
        self.cache[cache_key] = script
        self.strong_refs.append(script)
        self.memory_used += script_size
        
        return script
    
    def _cleanup(self):
        """Clean up old scripts."""
        # Remove oldest strong references
        to_remove = len(self.strong_refs) // 2
        self.strong_refs = self.strong_refs[to_remove:]
        
        # Force garbage collection
        gc.collect()
        
        # Recalculate memory usage
        self.memory_used = sum(len(s._code) * 2 for s in self.strong_refs)
```