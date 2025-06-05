"""
Comprehensive regex patterns library for symbol extraction across programming languages.

This module provides:
- Common regex patterns for symbol extraction
- Language-specific pattern variations
- Performance-optimized compiled patterns
- Pattern composition utilities
- Validation and testing utilities
"""

import re
from typing import Dict, List, Pattern, Optional, Tuple, Union
from dataclasses import dataclass
from functools import lru_cache
from enum import Enum


class PatternType(Enum):
    """Types of patterns that can be extracted."""
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    IMPORT = "import"
    EXPORT = "export"
    INTERFACE = "interface"
    STRUCT = "struct"
    ENUM = "enum"
    TYPEDEF = "typedef"
    NAMESPACE = "namespace"
    MODULE = "module"
    COMMENT = "comment"
    DOCSTRING = "docstring"
    DECORATOR = "decorator"
    ANNOTATION = "annotation"
    GENERIC = "generic"
    PARAMETER = "parameter"
    PROPERTY = "property"


@dataclass
class PatternMatch:
    """Represents a pattern match result."""
    type: PatternType
    name: str
    full_match: str
    line_number: int
    column: int
    groups: Dict[str, str]
    context: Optional[str] = None


class PatternFlags:
    """Common regex flags combinations."""
    DEFAULT = re.MULTILINE
    CASE_INSENSITIVE = re.MULTILINE | re.IGNORECASE
    DOTALL = re.MULTILINE | re.DOTALL
    VERBOSE = re.MULTILINE | re.VERBOSE
    UNICODE = re.MULTILINE | re.UNICODE


class BasePatterns:
    """Base regex patterns that can be reused across languages."""
    
    # Identifier patterns
    IDENTIFIER = r'[a-zA-Z_]\w*'
    QUALIFIED_IDENTIFIER = r'[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*'
    GENERIC_IDENTIFIER = r'[a-zA-Z_]\w*(?:<[^>]+>)?'
    
    # Common constructs
    WHITESPACE = r'\s*'
    OPTIONAL_WHITESPACE = r'\s*'
    REQUIRED_WHITESPACE = r'\s+'
    
    # String patterns
    SINGLE_QUOTED_STRING = r"'(?:[^'\\]|\\.)*'"
    DOUBLE_QUOTED_STRING = r'"(?:[^"\\]|\\.)*"'
    TRIPLE_QUOTED_STRING = r'"""(?:[^"\\]|\\.|"(?!""))*"""'
    BACKTICK_STRING = r'`(?:[^`\\]|\\.)*`'
    
    # Comment patterns
    SINGLE_LINE_COMMENT = r'//[^\n]*'
    MULTI_LINE_COMMENT = r'/\*(?:[^*]|\*(?!/))*\*/'
    HASH_COMMENT = r'#[^\n]*'
    
    # Number patterns
    INTEGER = r'-?\d+'
    FLOAT = r'-?\d+\.\d+'
    HEX = r'0[xX][0-9a-fA-F]+'
    BINARY = r'0[bB][01]+'
    OCTAL = r'0[oO][0-7]+'
    
    # Brackets and delimiters
    PARENS = r'\([^)]*\)'
    BRACKETS = r'\[[^\]]*\]'
    BRACES = r'\{[^}]*\}'
    ANGLES = r'<[^>]*>'
    
    # Parameter patterns
    PARAM_LIST = r'\([^)]*\)'
    TYPED_PARAM = r'(\w+)\s*:\s*([^,)]+)'
    DEFAULT_PARAM = r'(\w+)\s*=\s*([^,)]+)'
    
    # Type patterns
    SIMPLE_TYPE = r'[a-zA-Z_]\w*'
    GENERIC_TYPE = r'[a-zA-Z_]\w*(?:<[^>]+>)?'
    ARRAY_TYPE = r'[a-zA-Z_]\w*(?:\[\])*'
    NULLABLE_TYPE = r'[a-zA-Z_]\w*\?'
    
    # Modifiers
    VISIBILITY_MODIFIERS = r'(?:public|private|protected|internal)'
    STATIC_MODIFIER = r'static'
    FINAL_MODIFIER = r'(?:final|const|readonly)'
    ABSTRACT_MODIFIER = r'abstract'
    ASYNC_MODIFIER = r'(?:async|await)'


class LanguagePatterns:
    """Language-specific pattern collections."""
    
    @staticmethod
    @lru_cache(maxsize=128)
    def get_python_patterns() -> Dict[PatternType, Pattern]:
        """Get compiled patterns for Python."""
        return {
            PatternType.FUNCTION: re.compile(
                r'^(?P<indent>\s*)def\s+(?P<name>\w+)\s*\((?P<params>[^)]*)\)'
                r'(?:\s*->\s*(?P<return_type>[^:]+))?\s*:',
                re.MULTILINE
            ),
            PatternType.CLASS: re.compile(
                r'^(?P<indent>\s*)class\s+(?P<name>\w+)'
                r'(?:\s*\((?P<bases>[^)]*)\))?\s*:',
                re.MULTILINE
            ),
            PatternType.METHOD: re.compile(
                r'^(?P<indent>\s+)def\s+(?P<name>\w+)\s*\((?P<params>[^)]*)\)'
                r'(?:\s*->\s*(?P<return_type>[^:]+))?\s*:',
                re.MULTILINE
            ),
            PatternType.IMPORT: re.compile(
                r'^(?:from\s+(?P<module>[\w.]+)\s+)?import\s+(?P<names>[\w\s,*]+)'
                r'(?:\s+as\s+(?P<alias>\w+))?',
                re.MULTILINE
            ),
            PatternType.DECORATOR: re.compile(
                r'^(?P<indent>\s*)@(?P<name>[\w.]+)(?:\((?P<args>[^)]*)\))?',
                re.MULTILINE
            ),
            PatternType.VARIABLE: re.compile(
                r'^(?P<indent>\s*)(?P<name>\w+)\s*(?::\s*(?P<type>[^=]+))?\s*=\s*(?P<value>.+)',
                re.MULTILINE
            ),
            PatternType.CONSTANT: re.compile(
                r'^(?P<indent>\s*)(?P<name>[A-Z_]+)\s*=\s*(?P<value>.+)',
                re.MULTILINE
            ),
        }
    
    @staticmethod
    @lru_cache(maxsize=128)
    def get_javascript_patterns() -> Dict[PatternType, Pattern]:
        """Get compiled patterns for JavaScript/TypeScript."""
        return {
            PatternType.FUNCTION: re.compile(
                r'(?:(?P<export>export)\s+)?(?:(?P<async>async)\s+)?'
                r'function\s+(?P<name>\w+)\s*(?P<generics><[^>]+>)?\s*'
                r'\((?P<params>[^)]*)\)(?:\s*:\s*(?P<return_type>[^{]+))?',
                re.MULTILINE
            ),
            PatternType.CLASS: re.compile(
                r'(?:(?P<export>export)\s+)?(?:(?P<abstract>abstract)\s+)?'
                r'class\s+(?P<name>\w+)(?P<generics><[^>]+>)?'
                r'(?:\s+extends\s+(?P<extends>[\w.]+))?'
                r'(?:\s+implements\s+(?P<implements>[\w.,\s]+))?',
                re.MULTILINE
            ),
            PatternType.INTERFACE: re.compile(
                r'(?:(?P<export>export)\s+)?interface\s+(?P<name>\w+)'
                r'(?P<generics><[^>]+>)?(?:\s+extends\s+(?P<extends>[\w.,\s]+))?',
                re.MULTILINE
            ),
            PatternType.VARIABLE: re.compile(
                r'(?:(?P<export>export)\s+)?(?P<kind>const|let|var)\s+'
                r'(?P<name>\w+)(?:\s*:\s*(?P<type>[^=]+))?\s*=\s*(?P<value>.+)',
                re.MULTILINE
            ),
            PatternType.IMPORT: re.compile(
                r'import\s+(?:(?P<default>\w+)|(?:\{(?P<named>[^}]+)\})|(?:\*\s+as\s+(?P<namespace>\w+)))'
                r'\s+from\s+[\'"](?P<module>[^\'"\n]+)[\'"]',
                re.MULTILINE
            ),
            PatternType.EXPORT: re.compile(
                r'export\s+(?:(?P<default>default)\s+)?(?:(?P<declaration>[\w\s]+)|'
                r'(?:\{(?P<named>[^}]+)\}))',
                re.MULTILINE
            ),
        }
    
    @staticmethod
    @lru_cache(maxsize=128)
    def get_csharp_patterns() -> Dict[PatternType, Pattern]:
        """Get compiled patterns for C#."""
        return {
            PatternType.CLASS: re.compile(
                r'(?:(?P<modifiers>(?:public|private|protected|internal|static|abstract|sealed|partial)\s+)*)'
                r'class\s+(?P<name>\w+)(?P<generics><[^>]+>)?'
                r'(?:\s*:\s*(?P<inheritance>[\w.,\s<>]+))?',
                re.MULTILINE
            ),
            PatternType.INTERFACE: re.compile(
                r'(?:(?P<modifiers>(?:public|private|protected|internal)\s+)*)'
                r'interface\s+(?P<name>\w+)(?P<generics><[^>]+>)?'
                r'(?:\s*:\s*(?P<inheritance>[\w.,\s<>]+))?',
                re.MULTILINE
            ),
            PatternType.METHOD: re.compile(
                r'(?:(?P<modifiers>(?:public|private|protected|internal|static|virtual|override|abstract|async)\s+)*)'
                r'(?P<return_type>[\w<>.,\s\[\]?]+)\s+(?P<name>\w+)'
                r'(?P<generics><[^>]+>)?\s*\((?P<params>[^)]*)\)',
                re.MULTILINE
            ),
            PatternType.PROPERTY: re.compile(
                r'(?:(?P<modifiers>(?:public|private|protected|internal|static|virtual|override|abstract)\s+)*)'
                r'(?P<type>[\w<>.,\s\[\]?]+)\s+(?P<name>\w+)\s*\{(?P<accessors>[^}]+)\}',
                re.MULTILINE
            ),
            PatternType.ENUM: re.compile(
                r'(?:(?P<modifiers>(?:public|private|protected|internal)\s+)*)'
                r'enum\s+(?P<name>\w+)(?:\s*:\s*(?P<base>\w+))?',
                re.MULTILINE
            ),
            PatternType.STRUCT: re.compile(
                r'(?:(?P<modifiers>(?:public|private|protected|internal|readonly)\s+)*)'
                r'struct\s+(?P<name>\w+)(?P<generics><[^>]+>)?'
                r'(?:\s*:\s*(?P<interfaces>[\w.,\s<>]+))?',
                re.MULTILINE
            ),
            PatternType.NAMESPACE: re.compile(
                r'namespace\s+(?P<name>[\w.]+)',
                re.MULTILINE
            ),
        }
    
    @staticmethod
    @lru_cache(maxsize=128)
    def get_bash_patterns() -> Dict[PatternType, Pattern]:
        """Get compiled patterns for Bash/Shell scripts."""
        return {
            PatternType.FUNCTION: re.compile(
                r'(?:function\s+)?(?P<name>\w+)\s*\(\s*\)|(?P<name2>\w+)\s*\(\s*\)\s*{',
                re.MULTILINE
            ),
            PatternType.VARIABLE: re.compile(
                r'^(?P<export>export\s+)?(?P<name>\w+)=(?P<value>.+)',
                re.MULTILINE
            ),
            PatternType.CONSTANT: re.compile(
                r'^(?P<readonly>readonly\s+)?(?P<name>[A-Z_]+)=(?P<value>.+)',
                re.MULTILINE
            ),
            PatternType.COMMENT: re.compile(
                r'^#(?P<content>.+)',
                re.MULTILINE
            ),
        }
    
    @staticmethod
    @lru_cache(maxsize=128)
    def get_haskell_patterns() -> Dict[PatternType, Pattern]:
        """Get compiled patterns for Haskell."""
        return {
            PatternType.FUNCTION: re.compile(
                r'^(?P<name>\w+)\s*::\s*(?P<type>.+?)$\n^(?P=name)(?P<params>(?:\s+\w+)*)',
                re.MULTILINE
            ),
            PatternType.MODULE: re.compile(
                r'^module\s+(?P<name>[\w.]+)(?:\s*\((?P<exports>[^)]*)\))?\s+where',
                re.MULTILINE
            ),
            PatternType.IMPORT: re.compile(
                r'^import\s+(?P<qualified>qualified\s+)?(?P<module>[\w.]+)'
                r'(?:\s+as\s+(?P<alias>\w+))?(?:\s+hiding)?(?:\s*\((?P<items>[^)]*)\))?',
                re.MULTILINE
            ),
            PatternType.TYPEDEF: re.compile(
                r'^type\s+(?P<name>\w+)(?:\s+(?P<params>[\w\s]+))?\s*=\s*(?P<definition>.+)',
                re.MULTILINE
            ),
            PatternType.CLASS: re.compile(
                r'^class\s+(?P<constraints>.+?\s+)?(?P<name>\w+)\s+(?P<params>\w+)(?:\s+where)?',
                re.MULTILINE
            ),
        }
    
    @staticmethod
    @lru_cache(maxsize=128)
    def get_rust_patterns() -> Dict[PatternType, Pattern]:
        """Get compiled patterns for Rust."""
        return {
            PatternType.FUNCTION: re.compile(
                r'(?P<visibility>pub(?:\([^)]*\))?\s+)?(?P<async>async\s+)?'
                r'fn\s+(?P<name>\w+)(?P<generics><[^>]+>)?\s*\((?P<params>[^)]*)\)'
                r'(?:\s*->\s*(?P<return_type>[^{]+))?',
                re.MULTILINE
            ),
            PatternType.STRUCT: re.compile(
                r'(?P<visibility>pub(?:\([^)]*\))?\s+)?struct\s+(?P<name>\w+)'
                r'(?P<generics><[^>]+>)?(?:\s*\((?P<tuple_fields>[^)]*)\)|'
                r'\s*\{(?P<fields>[^}]*)\})?',
                re.MULTILINE
            ),
            PatternType.ENUM: re.compile(
                r'(?P<visibility>pub(?:\([^)]*\))?\s+)?enum\s+(?P<name>\w+)'
                r'(?P<generics><[^>]+>)?\s*\{(?P<variants>[^}]*)\}',
                re.MULTILINE
            ),
            PatternType.INTERFACE: re.compile(  # trait in Rust
                r'(?P<visibility>pub(?:\([^)]*\))?\s+)?trait\s+(?P<name>\w+)'
                r'(?P<generics><[^>]+>)?(?:\s*:\s*(?P<bounds>[^{]+))?',
                re.MULTILINE
            ),
            PatternType.MODULE: re.compile(
                r'(?P<visibility>pub(?:\([^)]*\))?\s+)?mod\s+(?P<name>\w+)',
                re.MULTILINE
            ),
        }


class PatternComposer:
    """Utilities for composing complex patterns from simpler ones."""
    
    @staticmethod
    def optional(pattern: str) -> str:
        """Make a pattern optional."""
        return f'(?:{pattern})?'
    
    @staticmethod
    def group(pattern: str, name: Optional[str] = None) -> str:
        """Create a capturing or non-capturing group."""
        if name:
            return f'(?P<{name}>{pattern})'
        return f'(?:{pattern})'
    
    @staticmethod
    def alternation(*patterns: str) -> str:
        """Create an alternation of patterns."""
        return f'(?:{"|".join(patterns)})'
    
    @staticmethod
    def repeat(pattern: str, min_count: int = 0, max_count: Optional[int] = None) -> str:
        """Repeat a pattern."""
        if max_count is None:
            if min_count == 0:
                return f'(?:{pattern})*'
            elif min_count == 1:
                return f'(?:{pattern})+'
            else:
                return f'(?:{pattern}){{{min_count},}}'
        else:
            return f'(?:{pattern}){{{min_count},{max_count}}}'
    
    @staticmethod
    def lookahead(pattern: str, positive: bool = True) -> str:
        """Create a lookahead assertion."""
        return f'(?={pattern})' if positive else f'(?!{pattern})'
    
    @staticmethod
    def lookbehind(pattern: str, positive: bool = True) -> str:
        """Create a lookbehind assertion."""
        return f'(?<={pattern})' if positive else f'(?<!{pattern})'
    
    @staticmethod
    def word_boundary(pattern: str) -> str:
        """Wrap pattern with word boundaries."""
        return f'\\b{pattern}\\b'
    
    @staticmethod
    def line_anchored(pattern: str, start: bool = True, end: bool = True) -> str:
        """Anchor pattern to line start/end."""
        result = pattern
        if start:
            result = f'^{result}'
        if end:
            result = f'{result}$'
        return result


class PatternValidator:
    """Utilities for validating and testing regex patterns."""
    
    @staticmethod
    def is_valid_pattern(pattern: str) -> Tuple[bool, Optional[str]]:
        """Check if a pattern is valid regex."""
        try:
            re.compile(pattern)
            return True, None
        except re.error as e:
            return False, str(e)
    
    @staticmethod
    def test_pattern(pattern: Union[str, Pattern], 
                    test_cases: List[Tuple[str, bool]], 
                    flags: int = 0) -> Tuple[bool, List[str]]:
        """Test a pattern against a list of test cases."""
        if isinstance(pattern, str):
            try:
                compiled = re.compile(pattern, flags)
            except re.error as e:
                return False, [f"Pattern compilation error: {e}"]
        else:
            compiled = pattern
        
        failures = []
        for test_string, should_match in test_cases:
            match = compiled.search(test_string)
            if bool(match) != should_match:
                failures.append(
                    f"Test failed: '{test_string}' - "
                    f"Expected {'match' if should_match else 'no match'}, "
                    f"got {'match' if match else 'no match'}"
                )
        
        return len(failures) == 0, failures
    
    @staticmethod
    def benchmark_pattern(pattern: Union[str, Pattern], 
                         test_string: str, 
                         iterations: int = 1000) -> float:
        """Benchmark pattern performance."""
        import timeit
        
        if isinstance(pattern, str):
            compiled = re.compile(pattern)
        else:
            compiled = pattern
        
        def test():
            list(compiled.finditer(test_string))
        
        return timeit.timeit(test, number=iterations) / iterations


class MultilinePatternMatcher:
    """Support for multi-line and context-aware pattern matching."""
    
    def __init__(self):
        self.context_window = 3  # Lines before and after match
    
    def find_with_context(self, pattern: Pattern, text: str) -> List[PatternMatch]:
        """Find all matches with surrounding context."""
        lines = text.split('\n')
        matches = []
        
        for match in pattern.finditer(text):
            line_start = text.count('\n', 0, match.start())
            line_end = text.count('\n', 0, match.end())
            
            # Get context lines
            context_start = max(0, line_start - self.context_window)
            context_end = min(len(lines), line_end + self.context_window + 1)
            context = '\n'.join(lines[context_start:context_end])
            
            # Extract match details
            groups = match.groupdict()
            name = groups.get('name', '')
            
            matches.append(PatternMatch(
                type=PatternType.GENERIC,  # Should be set by caller
                name=name,
                full_match=match.group(0),
                line_number=line_start + 1,
                column=match.start() - text.rfind('\n', 0, match.start()),
                groups=groups,
                context=context
            ))
        
        return matches
    
    def find_nested_patterns(self, 
                           outer_pattern: Pattern,
                           inner_pattern: Pattern,
                           text: str) -> List[Tuple[PatternMatch, List[PatternMatch]]]:
        """Find patterns nested within other patterns."""
        results = []
        
        for outer_match in outer_pattern.finditer(text):
            outer_text = outer_match.group(0)
            inner_matches = []
            
            for inner_match in inner_pattern.finditer(outer_text):
                # Adjust positions relative to original text
                adjusted_start = outer_match.start() + inner_match.start()
                line_number = text.count('\n', 0, adjusted_start) + 1
                
                inner_matches.append(PatternMatch(
                    type=PatternType.GENERIC,
                    name=inner_match.group('name') if 'name' in inner_match.groupdict() else '',
                    full_match=inner_match.group(0),
                    line_number=line_number,
                    column=adjusted_start - text.rfind('\n', 0, adjusted_start),
                    groups=inner_match.groupdict()
                ))
            
            outer_pattern_match = PatternMatch(
                type=PatternType.GENERIC,
                name=outer_match.group('name') if 'name' in outer_match.groupdict() else '',
                full_match=outer_match.group(0),
                line_number=text.count('\n', 0, outer_match.start()) + 1,
                column=outer_match.start() - text.rfind('\n', 0, outer_match.start()),
                groups=outer_match.groupdict()
            )
            
            results.append((outer_pattern_match, inner_matches))
        
        return results


class PatternFactory:
    """Factory for creating commonly used patterns."""
    
    @staticmethod
    def create_function_pattern(language: str) -> Optional[Pattern]:
        """Create a function pattern for the specified language."""
        language = language.lower()
        
        patterns = {
            'python': LanguagePatterns.get_python_patterns()[PatternType.FUNCTION],
            'javascript': LanguagePatterns.get_javascript_patterns()[PatternType.FUNCTION],
            'typescript': LanguagePatterns.get_javascript_patterns()[PatternType.FUNCTION],
            'csharp': LanguagePatterns.get_csharp_patterns()[PatternType.METHOD],
            'c#': LanguagePatterns.get_csharp_patterns()[PatternType.METHOD],
            'bash': LanguagePatterns.get_bash_patterns()[PatternType.FUNCTION],
            'sh': LanguagePatterns.get_bash_patterns()[PatternType.FUNCTION],
            'haskell': LanguagePatterns.get_haskell_patterns()[PatternType.FUNCTION],
            'rust': LanguagePatterns.get_rust_patterns()[PatternType.FUNCTION],
        }
        
        return patterns.get(language)
    
    @staticmethod
    def create_class_pattern(language: str) -> Optional[Pattern]:
        """Create a class pattern for the specified language."""
        language = language.lower()
        
        patterns = {
            'python': LanguagePatterns.get_python_patterns()[PatternType.CLASS],
            'javascript': LanguagePatterns.get_javascript_patterns()[PatternType.CLASS],
            'typescript': LanguagePatterns.get_javascript_patterns()[PatternType.CLASS],
            'csharp': LanguagePatterns.get_csharp_patterns()[PatternType.CLASS],
            'c#': LanguagePatterns.get_csharp_patterns()[PatternType.CLASS],
            'haskell': LanguagePatterns.get_haskell_patterns()[PatternType.CLASS],
            'rust': LanguagePatterns.get_rust_patterns()[PatternType.STRUCT],
        }
        
        return patterns.get(language)
    
    @staticmethod
    def create_import_pattern(language: str) -> Optional[Pattern]:
        """Create an import pattern for the specified language."""
        language = language.lower()
        
        patterns = {
            'python': LanguagePatterns.get_python_patterns()[PatternType.IMPORT],
            'javascript': LanguagePatterns.get_javascript_patterns()[PatternType.IMPORT],
            'typescript': LanguagePatterns.get_javascript_patterns()[PatternType.IMPORT],
            'haskell': LanguagePatterns.get_haskell_patterns()[PatternType.IMPORT],
        }
        
        return patterns.get(language)


# Example usage and testing
if __name__ == "__main__":
    # Test Python function pattern
    python_code = '''
def simple_function():
    pass

async def async_function(param1, param2: str) -> int:
    return 42

class MyClass:
    def method(self, x: int) -> None:
        pass
'''
    
    patterns = LanguagePatterns.get_python_patterns()
    matcher = MultilinePatternMatcher()
    
    print("Python Functions:")
    for match in matcher.find_with_context(patterns[PatternType.FUNCTION], python_code):
        print(f"  - {match.name} at line {match.line_number}")
    
    print("\nPython Classes:")
    for match in matcher.find_with_context(patterns[PatternType.CLASS], python_code):
        print(f"  - {match.name} at line {match.line_number}")
    
    # Test pattern composition
    composer = PatternComposer()
    
    # Create a pattern for matching async functions in any language
    async_func_pattern = composer.line_anchored(
        composer.group(
            composer.optional(r'export\s+') + 
            'async\\s+function\\s+' + 
            composer.group(BasePatterns.IDENTIFIER, 'name')
        ),
        start=True,
        end=False
    )
    
    # Validate the pattern
    validator = PatternValidator()
    is_valid, error = validator.is_valid_pattern(async_func_pattern)
    print(f"\nAsync function pattern valid: {is_valid}")
    
    # Test C# patterns
    csharp_code = '''
public class UserService : IUserService
{
    private readonly IUserRepository _repository;
    
    public async Task<User> GetUserAsync(int id)
    {
        return await _repository.FindByIdAsync(id);
    }
    
    public string Name { get; set; }
}

public interface IUserService
{
    Task<User> GetUserAsync(int id);
}
'''
    
    csharp_patterns = LanguagePatterns.get_csharp_patterns()
    
    print("\nC# Classes:")
    for match in matcher.find_with_context(csharp_patterns[PatternType.CLASS], csharp_code):
        print(f"  - {match.name} at line {match.line_number}")
        if match.groups.get('inheritance'):
            print(f"    Inherits: {match.groups['inheritance']}")