# Haskell Plugin

Comprehensive Haskell language plugin with support for type signatures, type classes, ADTs, and functional programming patterns.

## Features

- **Language**: Haskell
- **File Extensions**: `.hs`, `.lhs`, `.hsc`, `.cabal`
- **Project Files**: `stack.yaml`, `package.yaml`
- **Plugin Type**: IPlugin implementation with enhanced parsing

### Language Support

This plugin provides comprehensive support for Haskell language features:

#### Core Language Features
- **Type Signatures**: Multi-line type signatures with complex types
- **Function Definitions**: Including guards, pattern matching, and where clauses
- **Data Types**: `data`, `newtype`, and `type` declarations (including GADTs)
- **Type Classes**: Class declarations with method signatures
- **Instances**: Instance declarations including type/data family instances
- **Module System**: Module declarations with explicit exports
- **Imports**: Regular, qualified, and hiding imports with aliases
- **Language Pragmas**: `{-# LANGUAGE ... #-}` and other pragma types
- **Operators**: Infix operators with fixity declarations

#### Advanced Features
- **Literate Haskell**: Full support for `.lhs` files (Bird and LaTeX styles)
- **Type Families**: Type and data family declarations and instances
- **GADTs**: Generalized Algebraic Data Type syntax
- **Record Syntax**: Record field extraction
- **Pattern Bindings**: Named patterns with `@`
- **Deriving Clauses**: Automatic instance derivation

#### Project File Support
- **Cabal Files**: Package configuration, dependencies, and module lists
- **Stack Files**: Resolver, packages, and extra dependencies
- **Package.yaml**: Hpack format for generating Cabal files

## Usage

```python
from mcp_server.plugins.haskell_plugin import Plugin
from mcp_server.storage.sqlite_store import SQLiteStore

# Initialize with optional SQLite storage
store = SQLiteStore("index.db")
plugin = Plugin(sqlite_store=store)

# Check if a file is supported
if plugin.supports("MyModule.hs"):
    with open("MyModule.hs", "r") as f:
        content = f.read()
    
    # Index the file
    result = plugin.indexFile("MyModule.hs", content)
    print(f"Found {len(result['symbols'])} symbols")
    
    # Access metadata
    print(f"Language pragmas: {result['metadata']['pragmas']}")
    print(f"Is literate: {result['metadata']['is_literate']}")

# Find symbol definitions
definition = plugin.getDefinition("myFunction")
if definition:
    print(f"Found at {definition['defined_in']}:{definition['line']}")

# Find references
references = plugin.findReferences("MyDataType")
for ref in references:
    print(f"Referenced at {ref.file}:{ref.line}")

# Search for patterns
results = plugin.search("monad")
for result in results:
    print(f"{result['file']}:{result['line']} - {result['snippet']}")
```

## Symbol Types

The plugin recognizes and indexes the following symbol types:

| Symbol Type | Description | Example |
|-------------|-------------|---------|
| `module` | Module declarations | `module Data.List where` |
| `import` | Import statements | `import qualified Data.Map as M` |
| `function` | Function definitions | `map :: (a -> b) -> [a] -> [b]` |
| `data` | Data type declarations | `data Maybe a = Nothing \| Just a` |
| `newtype` | Newtype declarations | `newtype Identity a = Identity a` |
| `type_alias` | Type synonyms | `type String = [Char]` |
| `type_family` | Type families | `type family Elem a` |
| `class` | Type class declarations | `class Eq a where` |
| `instance` | Instance declarations | `instance Eq Bool where` |
| `operator` | Infix operators | `infixl 7 *` |
| `package` | Package names (Cabal) | `name: myproject` |
| `dependency` | Dependencies (Cabal) | `base >= 4.14` |
| `resolver` | Stack resolver | `resolver: lts-18.28` |

## Testing

The plugin includes comprehensive test coverage:

```bash
# Run all tests
pytest mcp_server/plugins/haskell_plugin/test_haskell_plugin.py

# Run specific test
pytest mcp_server/plugins/haskell_plugin/test_haskell_plugin.py::TestHaskellPlugin::test_parse_type_classes
```

## Configuration

The plugin behavior can be customized through initialization parameters:

```python
from mcp_server.plugins.haskell_plugin import Plugin

# Custom configuration
plugin = Plugin(
    sqlite_store=store  # Optional: Enable database storage
)
```

## Implementation Details

### Parser Architecture

The plugin uses a custom `HaskellTreeSitterWrapper` that provides:

1. **Comprehensive Regex Patterns**: Carefully crafted patterns for all Haskell constructs
2. **Multi-line Support**: Handles type signatures and other constructs spanning multiple lines
3. **Context Awareness**: Understands the relationship between type signatures and functions
4. **Literate Haskell**: Extracts code from documentation

### Performance Optimizations

- **Pre-indexing**: Files are pre-indexed on initialization for faster searches
- **Fuzzy Indexing**: Enables fast text-based searches
- **SQLite Integration**: Optional persistent storage for large codebases
- **Incremental Updates**: Only re-indexes changed files

### Error Handling

The plugin gracefully handles:
- Syntax errors in Haskell code
- Malformed project files
- Large files (with configurable limits)
- Missing type signatures

## Examples

### Indexing a Web Application

```haskell
-- The plugin will extract all symbols from Servant-based web apps
type API = "users" :> Get '[JSON] [User]
      :<|> "posts" :> Get '[JSON] [Post]

server :: Server API
server = getUsers :<|> getPosts
```

### Parsing Complex Type Signatures

```haskell
-- Handles higher-rank types and type families
runST :: (forall s. ST s a) -> a

type family F a where
  F Int = Bool
  F Bool = Char
```

### Project File Analysis

The plugin extracts valuable information from project files:
- Package metadata
- Dependencies with version constraints
- Exposed modules
- Build targets (library, executables, tests)

## Contributing

To extend the Haskell plugin:

1. **Add new patterns**: Update regex patterns in `HaskellTreeSitterWrapper`
2. **Support new constructs**: Add pattern matching for new language features
3. **Improve project file parsing**: Extend Cabal/Stack file support
4. **Add test cases**: Ensure new features are well-tested

## License

Part of the MCP Server project. See the main project license for details.