# Code-Index-MCP API Reference

## Overview

Code-Index-MCP provides a FastAPI-based REST API for code indexing and searching across multiple programming languages. The API uses a plugin-based architecture to support language-specific features.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API does not require authentication. This may change in future versions.

## Endpoints

### GET /symbol

Look up a symbol definition across all indexed files.

#### Request

**Parameters:**
- `symbol` (string, required): The symbol name to look up

**Example:**
```bash
curl "http://localhost:8000/symbol?symbol=MyClass"
```

#### Response

**Success Response (200 OK):**
```json
{
  "symbol": "MyClass",
  "kind": "class",
  "language": "python",
  "signature": "class MyClass(BaseClass):",
  "doc": "A sample class for demonstration",
  "defined_in": "/path/to/file.py",
  "line": 42,
  "span": [42, 58]
}
```

**Symbol Not Found (200 OK):**
```json
null
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| symbol | string | The symbol name |
| kind | string | Symbol type (e.g., "class", "function", "variable") |
| language | string | Programming language |
| signature | string | Symbol signature/declaration |
| doc | string \| null | Documentation/docstring if available |
| defined_in | string | File path where symbol is defined |
| line | integer | Line number of definition |
| span | [integer, integer] | Start and end line numbers |

### GET /search

Search for code across all indexed files.

#### Request

**Parameters:**
- `q` (string, required): Search query
- `semantic` (boolean, optional, default: false): Enable semantic search
- `limit` (integer, optional, default: 20): Maximum number of results

**Example:**
```bash
curl "http://localhost:8000/search?q=calculate&semantic=true&limit=10"
```

#### Response

**Success Response (200 OK):**
```json
[
  {
    "file": "/path/to/calculator.py",
    "line": 15,
    "snippet": "def calculate_total(items):\n    \"\"\"Calculate the total price of items\"\"\"\n    return sum(item.price for item in items)"
  },
  {
    "file": "/path/to/utils.js",
    "line": 23,
    "snippet": "function calculateDiscount(price, percentage) {\n  return price * (1 - percentage / 100);\n}"
  }
]
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| file | string | File path containing the match |
| line | integer | Line number of the match |
| snippet | string | Code snippet around the match |

## Error Responses

### 503 Service Unavailable

Returned when the dispatcher is not ready (e.g., during startup).

```json
{
  "detail": "Dispatcher not ready"
}
```

### 422 Unprocessable Entity

Returned when request parameters are invalid.

```json
{
  "detail": [
    {
      "loc": ["query", "q"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Data Types

### SymbolDef

Symbol definition returned by the `/symbol` endpoint.

```typescript
interface SymbolDef {
  symbol: string;      // Symbol name
  kind: string;        // Symbol type (class, function, etc.)
  language: string;    // Programming language
  signature: string;   // Symbol signature
  doc: string | null;  // Documentation/docstring
  defined_in: string;  // File path
  line: number;        // Line number
  span: [number, number]; // Line range
}
```

### SearchResult

Search result returned by the `/search` endpoint.

```typescript
interface SearchResult {
  file: string;    // File path
  line: number;    // Line number
  snippet: string; // Code snippet
}
```

## Language Support

The API supports multiple programming languages through plugins:

- **Python** (`.py`)
- **JavaScript** (`.js`, `.jsx`)
- **TypeScript** (`.ts`, `.tsx`)
- **Dart** (`.dart`)
- **C** (`.c`, `.h`)
- **C++** (`.cpp`, `.cc`, `.cxx`, `.hpp`)
- **HTML/CSS** (`.html`, `.css`)

## Usage Examples

### Search for a function

```bash
# Basic search
curl "http://localhost:8000/search?q=getUserById"

# Semantic search with limit
curl "http://localhost:8000/search?q=authentication&semantic=true&limit=5"
```

### Look up a class definition

```bash
curl "http://localhost:8000/symbol?symbol=UserController"
```

### Python Example

```python
import requests

# Search for code
response = requests.get(
    "http://localhost:8000/search",
    params={"q": "database connection", "semantic": True, "limit": 10}
)
results = response.json()

for result in results:
    print(f"{result['file']}:{result['line']}")
    print(result['snippet'])
    print("-" * 80)

# Look up a symbol
response = requests.get(
    "http://localhost:8000/symbol",
    params={"symbol": "DatabaseManager"}
)
symbol_def = response.json()

if symbol_def:
    print(f"Found {symbol_def['kind']} '{symbol_def['symbol']}' in {symbol_def['defined_in']}")
```

### JavaScript Example

```javascript
// Search for code
fetch('http://localhost:8000/search?q=async%20function&limit=5')
  .then(response => response.json())
  .then(results => {
    results.forEach(result => {
      console.log(`${result.file}:${result.line}`);
      console.log(result.snippet);
    });
  });

// Look up a symbol
fetch('http://localhost:8000/symbol?symbol=ApiClient')
  .then(response => response.json())
  .then(symbolDef => {
    if (symbolDef) {
      console.log(`Found ${symbolDef.kind} '${symbolDef.symbol}'`);
      console.log(`Location: ${symbolDef.defined_in}:${symbolDef.line}`);
    }
  });
```

## Rate Limiting

Currently, there are no rate limits imposed by the API. This may change in future versions.

## Versioning

The API currently does not use versioning. Future versions may introduce versioning through URL paths (e.g., `/v1/symbol`) or headers.

## Future Enhancements

Planned features for future API versions:

1. **Authentication & Authorization**
   - API key authentication
   - Role-based access control

2. **Additional Endpoints**
   - `POST /index` - Trigger indexing for specific files/directories
   - `GET /status` - Server health and indexing status
   - `GET /languages` - List supported languages and plugins
   - `GET /references` - Find all references to a symbol

3. **Enhanced Search**
   - Regular expression search
   - Scope filtering (file patterns, directories)
   - Sort options (relevance, file path, date)

4. **WebSocket Support**
   - Real-time indexing updates
   - Live search results

5. **Batch Operations**
   - Bulk symbol lookups
   - Multiple search queries in one request