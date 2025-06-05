# Pygments Regex Patterns for Syntax Highlighting

This document contains regex patterns extracted from the Pygments library (https://github.com/pygments/pygments) that can be adapted for our regex fallback parser.

## Python Patterns

### Function Definitions
```regex
(def)((?:\s|\\\s)+)
```
- Matches 'def' keyword followed by whitespace (including line continuations)
- Pattern continues to parse function name in a separate state

### Class Definitions
```regex
(class)((?:\s|\\\s)+)
```
- Matches 'class' keyword followed by whitespace
- Pattern continues to parse class name in a separate state

### Import Statements
```regex
(from)((?:\s|\\\s)+)
(import)((?:\s|\\\s)+)
```
- Handles both 'from ... import' and direct 'import' statements
- Includes line continuation support

### Decorators
```regex
@[a-zA-Z_]\w*
```
- Matches @ symbol followed by a valid Python identifier

### Identifiers
```regex
[a-zA-Z_]\w*
```
- Standard Python identifier pattern

## JavaScript Patterns

### Function Definitions

#### Arrow Functions
```regex
(?:\([^()]*\))?\s*[=-]>
```
- Matches optional parameters in parentheses followed by arrow (=>)

#### Named Functions
```regex
([a-zA-Z_?.$][\w?.$]*)(?=\(\) \{)
```
- Matches function names before function body

### Class Definitions
```regex
\b(class)\b
```
- Simple class keyword detection

### Method/Constructor Keywords
```regex
(constructor|from|as)\b
```

### Variable Declarations
```regex
(var|let|const)\b
```

### Import/Export Statements
```regex
\b(import|export)\b
(from|as)\b
```

### Access Modifiers
```regex
(abstract|implements|private|protected|public|readonly)\b
```

### Template Literal Interpolation
```regex
#\{
```
- Matches template literal interpolation start

## CSS Patterns

### Selectors

#### Class Selector
```regex
(\.)([\w-]+)
```
- Matches dot followed by class name

#### ID Selector
```regex
(\#)([\w-]+)
```
- Matches hash followed by ID name

#### Element Selector
```regex
[\w-]+
```
- Matches HTML element names

#### Pseudo-classes/elements
```regex
(\:{1,2})([\w-]+)
```
- Matches single colon (pseudo-class) or double colon (pseudo-element)

### Properties

#### Standard Properties
```regex
[-a-zA-Z]+(\s*)(:)
```
- Matches CSS property names followed by colon

#### Custom Properties
```regex
([-]+[a-zA-Z_][\w-]*)(\s*)(:)
```
- Matches CSS custom properties (variables)

### Values

#### Hex Colors
```regex
\#[a-zA-Z0-9]{1,6}
```

#### Numbers
```regex
[+\-]?[0-9]*[.][0-9]+  # Float
[+\-]?[0-9]+           # Integer
```

### @Rules
```regex
(@)([\w-]+)
```
- Matches @ followed by rule name (media, import, keyframes, etc.)

## Java Patterns

### Class/Interface Definitions
```regex
(class|interface)(\s+)
```

### Method Definitions
```regex
((?:[^\W\d]|\$)[\w$]*\s+)+?  # return type(s)
((?:[^\W\d]|\$)[\w$]*)       # method name
(\s*)(\()                    # opening parenthesis
```
- Complex pattern capturing return type, method name, and signature start

### Import Statements
```regex
(import(?:\s+static)?)(\s+)
```
- Handles both regular and static imports

### Package Declaration
```regex
(package)(\s+)
```

### Annotations
```regex
@[^\W\d][\w.]*
```
- Matches annotations with dot notation support

### Access Modifiers
```regex
(public|private|protected|static|strictfp)
```

### Primitive Types
```regex
(boolean|byte|char|double|float|int|long|short|void)
```

### Variable Declarations
```regex
(var|val)(\s+)
```

## General Patterns

### Whitespace with Line Continuation
```regex
(?:\s|\\\s)+
```
- Matches whitespace including escaped newlines

### Identifier Patterns
- Python: `[a-zA-Z_]\w*`
- JavaScript: `[$_a-zA-Z][$\w]*`
- Java: `(?:[^\W\d]|\$)[\w$]*`

### Number Patterns
- Binary: `0[bB][01]+`
- Octal: `0[oO][0-7]+`
- Hex: `0[xX][0-9a-fA-F]+`
- Decimal: `[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?`

## Usage Notes

1. These patterns are extracted from Pygments' battle-tested lexers
2. Many patterns use capturing groups for tokenization
3. Some patterns rely on state machines for complete parsing
4. Whitespace handling often includes line continuation support
5. Consider language-specific identifier rules when adapting patterns

## Adaptation Strategy

When adapting these patterns for our regex fallback parser:

1. **Simplify state-dependent patterns**: Some Pygments patterns rely on lexer states. These need to be converted to standalone patterns.

2. **Combine related patterns**: For efficiency, related patterns can be combined using alternation.

3. **Add anchoring**: Add appropriate anchors (^, $, \b) for more precise matching.

4. **Handle multi-line**: Consider using MULTILINE and DOTALL flags where appropriate.

5. **Performance optimization**: Test pattern performance and optimize for common cases.