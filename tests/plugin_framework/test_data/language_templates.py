"""
Language-specific templates for test data generation.

This module provides templates and patterns for generating test code
in different programming languages.
"""

import random
import string
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class SymbolTestCase:
    """Test case for symbol extraction accuracy testing."""
    name: str
    kind: str
    line: int
    signature: Optional[str] = None
    docstring: Optional[str] = None


class LanguageTemplate(ABC):
    """Abstract base class for language-specific templates."""
    
    @abstractmethod
    def get_file_extension(self) -> str:
        """Get the file extension for this language."""
        pass
    
    @abstractmethod
    def get_simple_template(self) -> str:
        """Get a simple, valid code template."""
        pass
    
    @abstractmethod
    def generate_file_with_symbols(self, count: int, complexity: str) -> str:
        """Generate a file with specified number of symbols."""
        pass


class PythonTemplate(LanguageTemplate):
    """Python-specific code templates."""
    
    def get_file_extension(self) -> str:
        return ".py"
    
    def get_simple_template(self) -> str:
        return '''"""Simple Python module for testing."""

def hello_world():
    """Print hello world."""
    print("Hello, World!")

class SimpleClass:
    """A simple class."""
    
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        """Get the value."""
        return self.value

# Module-level variable
CONSTANT = "test_constant"
'''
    
    def get_minimal_template(self) -> str:
        return "# Minimal Python file\npass\n"
    
    def get_comments_template(self) -> str:
        return '''# This is a comment-only file
"""
Multi-line comment
for testing purposes.
"""

# More comments
# TODO: Add actual code
'''
    
    def get_functions_template(self) -> str:
        return '''def simple_function():
    """A simple function."""
    pass

def function_with_args(x, y=10):
    """Function with arguments."""
    return x + y

async def async_function():
    """An async function."""
    await some_operation()

def function_with_decorator():
    @decorator
    def inner():
        pass
    return inner

def generator_function():
    """A generator function."""
    for i in range(10):
        yield i
'''
    
    def get_methods_template(self) -> str:
        return '''class TestClass:
    """Test class with various methods."""
    
    def __init__(self):
        """Constructor."""
        self.data = []
    
    def instance_method(self):
        """Instance method."""
        return len(self.data)
    
    @classmethod
    def class_method(cls):
        """Class method."""
        return cls()
    
    @staticmethod
    def static_method():
        """Static method."""
        return "static"
    
    @property
    def property_method(self):
        """Property method."""
        return self._value
    
    def __str__(self):
        """String representation."""
        return f"TestClass({len(self.data)})"
'''
    
    def get_classes_template(self) -> str:
        return '''class SimpleClass:
    """A simple class."""
    pass

class ClassWithMethods:
    """Class with methods."""
    
    def method1(self):
        pass
    
    def method2(self):
        pass

class ClassWithInit:
    """Class with constructor."""
    
    def __init__(self, value):
        self.value = value

class AbstractClass(ABC):
    """Abstract class."""
    
    @abstractmethod
    def abstract_method(self):
        pass
'''
    
    def get_inheritance_template(self) -> str:
        return '''class BaseClass:
    """Base class."""
    
    def base_method(self):
        return "base"

class DerivedClass(BaseClass):
    """Derived class."""
    
    def derived_method(self):
        return "derived"
    
    def base_method(self):
        return "overridden"

class MultipleInheritance(BaseClass, Mixin):
    """Class with multiple inheritance."""
    pass

class GenericClass(Generic[T]):
    """Generic class."""
    
    def __init__(self, value: T):
        self.value = value
'''
    
    def get_nested_template(self) -> str:
        return '''class OuterClass:
    """Outer class with nested elements."""
    
    class InnerClass:
        """Inner class."""
        
        def inner_method(self):
            return "inner"
    
    def outer_method(self):
        """Outer method with nested function."""
        
        def nested_function():
            return "nested"
        
        return nested_function()

def outer_function():
    """Function with nested elements."""
    
    def inner_function():
        return "inner"
    
    class LocalClass:
        pass
    
    return inner_function()
'''
    
    def get_complex_functions_template(self) -> str:
        return '''@decorator1
@decorator2(arg="value")
def complex_decorated_function(a: int, b: str = "default", *args, **kwargs) -> Optional[str]:
    """Complex function with decorators and type hints."""
    
    def inner_function(x):
        return x * 2
    
    if a > 0:
        return inner_function(a) + b
    return None

async def async_generator(items: List[Any]) -> AsyncGenerator[str, None]:
    """Async generator function."""
    for item in items:
        processed = await process_item(item)
        yield str(processed)

def function_with_complex_signature(
    mandatory: str,
    optional: int = 42,
    *positional_args: Any,
    keyword_only: bool = False,
    **keyword_args: Dict[str, Any]
) -> Tuple[str, int, bool]:
    """Function with complex signature."""
    return mandatory, optional, keyword_only
'''
    
    def get_nested_classes_template(self) -> str:
        return '''class Level1:
    """Level 1 class."""
    
    class Level2:
        """Level 2 nested class."""
        
        class Level3:
            """Level 3 nested class."""
            
            def deep_method(self):
                return "deep"
        
        def level2_method(self):
            return "level2"
    
    def level1_method(self):
        return "level1"

class ComplexNesting:
    """Class with complex nesting patterns."""
    
    def method_with_local_class(self):
        class LocalClass:
            def local_method(self):
                return "local"
        return LocalClass()
    
    @property
    def property_with_nested(self):
        def getter():
            return self._value
        return getter()
'''
    
    def get_complex_nesting_template(self) -> str:
        return '''def deeply_nested_function():
    """Function with deep nesting."""
    
    def level1():
        def level2():
            def level3():
                def level4():
                    return "deep"
                return level4()
            return level3()
        return level2()
    
    class NestedClass:
        def method_with_nested_function(self):
            def nested():
                class VeryNestedClass:
                    def very_nested_method(self):
                        return "very nested"
                return VeryNestedClass()
            return nested()
    
    return level1(), NestedClass()

class MegaNesting:
    """Class with mega nesting."""
    
    class Inner1:
        class Inner2:
            def method(self):
                def func():
                    class Local:
                        def local_method(self):
                            def inner_func():
                                return "mega nested"
                            return inner_func()
                    return Local()
                return func()
'''
    
    def generate_file_with_symbols(self, count: int, complexity: str) -> str:
        """Generate Python file with specified number of symbols."""
        if complexity == "small":
            return self._generate_small_python_file(count)
        elif complexity == "medium":
            return self._generate_medium_python_file(count)
        elif complexity == "large":
            return self._generate_large_python_file(count)
        else:  # massive
            return self._generate_massive_python_file(count)
    
    def _generate_small_python_file(self, count: int) -> str:
        """Generate small Python file with simple symbols."""
        lines = ['"""Generated Python file for testing."""\n']
        
        for i in range(count):
            if i % 2 == 0:
                lines.append(f'def function_{i}():')
                lines.append(f'    """Function number {i}."""')
                lines.append(f'    return {i}')
                lines.append('')
            else:
                lines.append(f'class Class{i}:')
                lines.append(f'    """Class number {i}."""')
                lines.append(f'    value = {i}')
                lines.append('')
        
        return '\n'.join(lines)
    
    def _generate_medium_python_file(self, count: int) -> str:
        """Generate medium Python file with moderate complexity."""
        lines = ['"""Generated Python file with medium complexity."""\n']
        lines.append('import os')
        lines.append('import sys')
        lines.append('from typing import List, Dict, Optional\n')
        
        functions_count = count // 2
        classes_count = count - functions_count
        
        # Generate functions
        for i in range(functions_count):
            lines.append(f'def process_data_{i}(data: List[int]) -> Optional[int]:')
            lines.append(f'    """Process data function {i}."""')
            lines.append(f'    if not data:')
            lines.append(f'        return None')
            lines.append(f'    return sum(data) + {i}')
            lines.append('')
        
        # Generate classes
        for i in range(classes_count):
            lines.append(f'class DataProcessor{i}:')
            lines.append(f'    """Data processor class {i}."""')
            lines.append('')
            lines.append(f'    def __init__(self):')
            lines.append(f'        self.data = []')
            lines.append(f'        self.count = {i}')
            lines.append('')
            lines.append(f'    def process(self):')
            lines.append(f'        """Process the data."""')
            lines.append(f'        return [x * {i} for x in self.data]')
            lines.append('')
            lines.append(f'    @property')
            lines.append(f'    def size(self):')
            lines.append(f'        """Get size of data."""')
            lines.append(f'        return len(self.data)')
            lines.append('')
        
        return '\n'.join(lines)
    
    def _generate_large_python_file(self, count: int) -> str:
        """Generate large Python file with high complexity."""
        lines = ['"""Generated large Python file for performance testing."""\n']
        
        # Imports
        imports = [
            'import os', 'import sys', 'import json', 'import random',
            'from typing import List, Dict, Any, Optional, Union, Tuple',
            'from pathlib import Path', 'from dataclasses import dataclass',
            'from abc import ABC, abstractmethod'
        ]
        lines.extend(imports)
        lines.append('')
        
        # Generate mix of constructs
        for i in range(count):
            construct_type = i % 4
            
            if construct_type == 0:  # Regular function
                lines.extend(self._generate_complex_function(i))
            elif construct_type == 1:  # Class
                lines.extend(self._generate_complex_class(i))
            elif construct_type == 2:  # Async function
                lines.extend(self._generate_async_function(i))
            else:  # Decorator function
                lines.extend(self._generate_decorated_function(i))
            
            lines.append('')
        
        return '\n'.join(lines)
    
    def _generate_massive_python_file(self, count: int) -> str:
        """Generate massive Python file for stress testing."""
        return self._generate_large_python_file(count)  # Same as large but more symbols
    
    def _generate_complex_function(self, index: int) -> List[str]:
        """Generate a complex function."""
        return [
            f'def complex_function_{index}(data: List[Dict[str, Any]], *args, **kwargs) -> Dict[str, Union[int, str]]:',
            f'    """Complex function {index} with type hints and processing."""',
            f'    result = {{"count": len(data), "index": {index}}}',
            f'    ',
            f'    def inner_processor(item):',
            f'        return item.get("value", 0) * {index}',
            f'    ',
            f'    processed = [inner_processor(item) for item in data]',
            f'    result["processed"] = sum(processed)',
            f'    return result'
        ]
    
    def _generate_complex_class(self, index: int) -> List[str]:
        """Generate a complex class."""
        return [
            f'class ComplexProcessor{index}:',
            f'    """Complex data processor class {index}."""',
            f'    ',
            f'    def __init__(self, config: Dict[str, Any]):',
            f'        self.config = config',
            f'        self.index = {index}',
            f'        self._cache = {{}}',
            f'    ',
            f'    def process_batch(self, items: List[Any]) -> List[Any]:',
            f'        """Process a batch of items."""',
            f'        return [self._process_single(item) for item in items]',
            f'    ',
            f'    def _process_single(self, item: Any) -> Any:',
            f'        """Process a single item."""',
            f'        cache_key = str(hash(str(item)))',
            f'        if cache_key in self._cache:',
            f'            return self._cache[cache_key]',
            f'        ',
            f'        result = item if item else {index}',
            f'        self._cache[cache_key] = result',
            f'        return result',
            f'    ',
            f'    @property',
            f'    def cache_size(self) -> int:',
            f'        """Get cache size."""',
            f'        return len(self._cache)'
        ]
    
    def _generate_async_function(self, index: int) -> List[str]:
        """Generate an async function."""
        return [
            f'async def async_processor_{index}(data: List[str]) -> List[str]:',
            f'    """Async processor function {index}."""',
            f'    results = []',
            f'    ',
            f'    for item in data:',
            f'        processed = await async_process_item(item, {index})',
            f'        results.append(processed)',
            f'    ',
            f'    return results',
            f'',
            f'async def async_process_item(item: str, multiplier: int) -> str:',
            f'    """Process individual item asynchronously."""',
            f'    # Simulate async operation',
            f'    await asyncio.sleep(0.001)',
            f'    return f"{{item}}_{{multiplier}}"'
        ]
    
    def _generate_decorated_function(self, index: int) -> List[str]:
        """Generate a decorated function."""
        return [
            f'@functools.lru_cache(maxsize=128)',
            f'@timing_decorator',
            f'def cached_function_{index}(value: int, power: int = 2) -> int:',
            f'    """Cached function {index} with decorators."""',
            f'    return value ** power + {index}'
        ]
    
    # Accuracy testing templates
    def get_simple_functions_for_accuracy(self) -> str:
        return '''def add_numbers(a, b):
    """Add two numbers."""
    return a + b

def multiply(x, y):
    """Multiply two values."""
    return x * y

def greet(name="World"):
    """Greet someone."""
    return f"Hello, {name}!"
'''
    
    def get_expected_simple_symbols(self) -> List[SymbolTestCase]:
        return [
            SymbolTestCase("add_numbers", "function", 1, "def add_numbers(a, b)", "Add two numbers."),
            SymbolTestCase("multiply", "function", 5, "def multiply(x, y)", "Multiply two values."),
            SymbolTestCase("greet", "function", 9, "def greet(name=\"World\")", "Greet someone.")
        ]
    
    def get_simple_classes_for_accuracy(self) -> str:
        return '''class Calculator:
    """A simple calculator."""
    
    def __init__(self):
        self.result = 0
    
    def add(self, value):
        """Add value to result."""
        self.result += value

class Person:
    """Represents a person."""
    
    def __init__(self, name):
        self.name = name
'''
    
    def get_expected_class_symbols(self) -> List[SymbolTestCase]:
        return [
            SymbolTestCase("Calculator", "class", 1, "class Calculator", "A simple calculator."),
            SymbolTestCase("__init__", "method", 4, "def __init__(self)", None),
            SymbolTestCase("add", "method", 7, "def add(self, value)", "Add value to result."),
            SymbolTestCase("Person", "class", 11, "class Person", "Represents a person."),
            SymbolTestCase("__init__", "method", 14, "def __init__(self, name)", None)
        ]


class JavaScriptTemplate(LanguageTemplate):
    """JavaScript-specific code templates."""
    
    def get_file_extension(self) -> str:
        return ".js"
    
    def get_simple_template(self) -> str:
        return '''// Simple JavaScript module for testing

function helloWorld() {
    console.log("Hello, World!");
}

class SimpleClass {
    constructor() {
        this.value = 42;
    }
    
    getValue() {
        return this.value;
    }
}

// Module-level constant
const CONSTANT = "test_constant";

module.exports = { helloWorld, SimpleClass, CONSTANT };
'''
    
    def get_minimal_template(self) -> str:
        return "// Minimal JavaScript file\n"
    
    def generate_file_with_symbols(self, count: int, complexity: str) -> str:
        """Generate JavaScript file with specified number of symbols."""
        lines = ['// Generated JavaScript file for testing\n']
        
        for i in range(count):
            if i % 2 == 0:
                lines.append(f'function func{i}() {{')
                lines.append(f'    return {i};')
                lines.append(f'}}')
                lines.append('')
            else:
                lines.append(f'class Class{i} {{')
                lines.append(f'    constructor() {{')
                lines.append(f'        this.value = {i};')
                lines.append(f'    }}')
                lines.append(f'}}')
                lines.append('')
        
        return '\n'.join(lines)


class JavaTemplate(LanguageTemplate):
    """Java-specific code templates."""
    
    def get_file_extension(self) -> str:
        return ".java"
    
    def get_simple_template(self) -> str:
        return '''// Simple Java class for testing
public class SimpleClass {
    private int value = 42;
    
    public void helloWorld() {
        System.out.println("Hello, World!");
    }
    
    public int getValue() {
        return value;
    }
    
    public static void main(String[] args) {
        SimpleClass obj = new SimpleClass();
        obj.helloWorld();
    }
}
'''
    
    def get_minimal_template(self) -> str:
        return "// Minimal Java file\npublic class Minimal {}\n"
    
    def generate_file_with_symbols(self, count: int, complexity: str) -> str:
        """Generate Java file with specified number of symbols."""
        lines = ['// Generated Java file for testing']
        lines.append('public class GeneratedClass {')
        lines.append('')
        
        for i in range(count):
            if i % 2 == 0:
                lines.append(f'    public void method{i}() {{')
                lines.append(f'        System.out.println("Method {i}");')
                lines.append(f'    }}')
                lines.append('')
            else:
                lines.append(f'    private int field{i} = {i};')
                lines.append('')
        
        lines.append('}')
        return '\n'.join(lines)


class LanguageTemplates:
    """Main class for managing language-specific templates."""
    
    def __init__(self, language: str):
        self.language = language.lower()
        self._template = self._get_template_class()
    
    def _get_template_class(self) -> LanguageTemplate:
        """Get the appropriate template class for the language."""
        if self.language == "python":
            return PythonTemplate()
        elif self.language == "javascript" or self.language == "js":
            return JavaScriptTemplate()
        elif self.language == "java":
            return JavaTemplate()
        else:
            # Default to Python-like template for unknown languages
            return PythonTemplate()
    
    def get_file_extension(self) -> str:
        return self._template.get_file_extension()
    
    def get_simple_template(self) -> str:
        return self._template.get_simple_template()
    
    def get_minimal_template(self) -> str:
        return self._template.get_minimal_template()
    
    def generate_file_with_symbols(self, count: int, complexity: str) -> str:
        return self._template.generate_file_with_symbols(count, complexity)
    
    # Forward all template methods to the language-specific template
    def __getattr__(self, name):
        if hasattr(self._template, name):
            return getattr(self._template, name)
        else:
            # Provide default implementations for missing methods
            if name.endswith('_template'):
                return lambda: f"// Template not implemented for {self.language}\n"
            elif name.startswith('get_expected_'):
                return lambda: []
            elif name in ['get_syntax_error_template_1', 'get_syntax_error_template_2', 
                         'get_incomplete_template', 'get_unicode_template', 'get_emoji_template',
                         'get_multilingual_template', 'get_generics_template', 'get_annotations_template',
                         'get_metaprogramming_template', 'get_async_template', 'get_edge_symbols_template',
                         'get_special_chars_template', 'get_long_lines_template', 'get_api_client_template',
                         'get_data_model_template', 'get_utility_functions_template', 'get_test_file_template',
                         'get_framework_controller_template', 'get_framework_model_template', 
                         'get_framework_service_template', 'get_definition_template', 'get_reference_template',
                         'get_search_template', 'get_definition_target_symbols', 'get_reference_target_symbols']:
                return lambda: f"# Default {name} for {self.language}\n# Not implemented yet\n"
            else:
                raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")