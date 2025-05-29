# SQLite FTS5 Comprehensive Guide for Code Indexing

## Table of Contents
1. [Introduction to FTS5](#introduction)
2. [FTS5 Basics and Setup](#fts5-basics-and-setup)
3. [Python sqlite3 Integration](#python-integration)
4. [Creating and Querying FTS Tables](#creating-and-querying)
5. [Indexing Strategies for Code](#indexing-strategies)
6. [Performance Optimization](#performance-optimization)
7. [MCP Server Implementation Patterns](#mcp-server-implementation)

## Introduction to FTS5 {#introduction}

SQLite FTS5 (Full-Text Search 5) is a virtual table module that provides full-text search functionality to database applications. It's particularly useful for implementing search capabilities in applications that need to search through large amounts of text data, including source code.

### Key Features
- Fast full-text search using inverted indexes
- Built-in ranking algorithm (BM25)
- Support for phrase searches, prefix searches, and boolean operators
- Customizable tokenizers for different languages and use cases
- Auxiliary functions for highlighting and snippet extraction

### Requirements
- SQLite version 3.9.0 or later (FTS5 is included in the amalgamation)
- Python with sqlite3 module (included in standard library)

## FTS5 Basics and Setup {#fts5-basics-and-setup}

### Creating an FTS5 Virtual Table

FTS5 tables are created using the `CREATE VIRTUAL TABLE` statement:

```sql
CREATE VIRTUAL TABLE documents USING fts5(
    title,
    content,
    tags
);
```

**Important Notes:**
- Column types, constraints, or PRIMARY KEY declarations are not allowed
- All columns are treated as TEXT
- An implicit `rowid` column is automatically created

### Configuration Options

FTS5 provides several configuration options to optimize performance:

```sql
-- With tokenizer configuration
CREATE VIRTUAL TABLE code_index USING fts5(
    filename,
    content,
    language,
    tokenize = 'porter unicode61'
);

-- With prefix indexing for faster prefix searches
CREATE VIRTUAL TABLE code_index USING fts5(
    content,
    prefix = '2 3'
);

-- With detail reduction for smaller index size
CREATE VIRTUAL TABLE code_index USING fts5(
    content,
    detail = 'column'
);
```

## Python sqlite3 Integration {#python-integration}

### Basic Setup

```python
import sqlite3

# Connect to database
conn = sqlite3.connect('code_index.db')
cursor = conn.cursor()

# Enable FTS5 (usually enabled by default)
cursor.execute("PRAGMA compile_options;")
options = cursor.fetchall()
fts5_enabled = any('ENABLE_FTS5' in str(option) for option in options)

if not fts5_enabled:
    print("Warning: FTS5 may not be available in this SQLite build")
```

### Complete Working Example

```python
import sqlite3
import os

class CodeIndexer:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        """Create FTS5 virtual table for code indexing"""
        self.cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS code_files
            USING fts5(
                filepath,
                filename,
                content,
                language,
                tokenize = 'porter unicode61'
            )
        """)
        self.conn.commit()
    
    def index_file(self, filepath, language):
        """Index a single code file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        filename = os.path.basename(filepath)
        
        self.cursor.execute("""
            INSERT INTO code_files (filepath, filename, content, language)
            VALUES (?, ?, ?, ?)
        """, (filepath, filename, content, language))
        self.conn.commit()
    
    def search(self, query, limit=10):
        """Search indexed code files"""
        results = self.cursor.execute("""
            SELECT filepath, filename, snippet(code_files, 2, '<mark>', '</mark>', '...', 32)
            FROM code_files
            WHERE code_files MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit)).fetchall()
        
        return results
    
    def search_by_language(self, query, language):
        """Search within specific programming language"""
        results = self.cursor.execute("""
            SELECT filepath, filename, highlight(code_files, 2, '<mark>', '</mark>')
            FROM code_files
            WHERE code_files MATCH ? AND language = ?
            ORDER BY rank
        """, (query, language)).fetchall()
        
        return results
    
    def close(self):
        self.conn.close()

# Usage example
indexer = CodeIndexer('my_code_index.db')

# Index some files
indexer.index_file('/path/to/main.py', 'python')
indexer.index_file('/path/to/utils.js', 'javascript')

# Search for code
results = indexer.search('function')
for filepath, filename, snippet in results:
    print(f"{filename}: {snippet}")

indexer.close()
```

## Creating and Querying FTS Tables {#creating-and-querying}

### Basic Queries

```python
# Simple search
cursor.execute("""
    SELECT * FROM code_files 
    WHERE code_files MATCH 'python'
""")

# Alternative syntax
cursor.execute("""
    SELECT * FROM code_files('python')
""")

# Using = operator
cursor.execute("""
    SELECT * FROM code_files 
    WHERE code_files = 'python'
""")
```

### Advanced Query Syntax

#### Boolean Operators

```python
# AND operator - both terms must be present
cursor.execute("""
    SELECT * FROM code_files 
    WHERE code_files MATCH 'class AND method'
""")

# OR operator - either term can be present
cursor.execute("""
    SELECT * FROM code_files 
    WHERE code_files MATCH 'async OR await'
""")

# NOT operator - exclude documents with term
cursor.execute("""
    SELECT * FROM code_files 
    WHERE code_files MATCH 'function NOT lambda'
""")
```

#### Phrase Searches

```python
# Exact phrase match
cursor.execute("""
    SELECT * FROM code_files 
    WHERE code_files MATCH '"import numpy"'
""")

# NEAR operator - terms within N tokens
cursor.execute("""
    SELECT * FROM code_files 
    WHERE code_files MATCH 'NEAR(class method, 10)'
""")
```

#### Column-Specific Searches

```python
# Search only in filename column
cursor.execute("""
    SELECT * FROM code_files 
    WHERE code_files MATCH 'filename:test'
""")

# Search in content column
cursor.execute("""
    SELECT * FROM code_files 
    WHERE code_files MATCH 'content:TODO'
""")
```

#### Prefix Searches

```python
# Find all words starting with 'func'
cursor.execute("""
    SELECT * FROM code_files 
    WHERE code_files MATCH 'func*'
""")
```

### Using Auxiliary Functions

#### BM25 Ranking

```python
# Get relevance scores
cursor.execute("""
    SELECT filepath, bm25(code_files) as score
    FROM code_files
    WHERE code_files MATCH ?
    ORDER BY score
""", (query,))

# Custom column weights
cursor.execute("""
    SELECT filepath, bm25(code_files, 1.0, 2.0, 0.5, 0.5) as score
    FROM code_files
    WHERE code_files MATCH ?
    ORDER BY score
""", (query,))
```

#### Highlighting

```python
# Highlight matching terms
cursor.execute("""
    SELECT 
        filepath,
        highlight(code_files, 2, '<b>', '</b>') as highlighted_content
    FROM code_files
    WHERE code_files MATCH ?
""", (query,))
```

#### Snippets

```python
# Extract relevant snippets
cursor.execute("""
    SELECT 
        filepath,
        snippet(code_files, 2, '<mark>', '</mark>', '...', 32) as extract
    FROM code_files
    WHERE code_files MATCH ?
""", (query,))
```

## Indexing Strategies for Code {#indexing-strategies}

### 1. Language-Specific Tokenization

For code indexing, consider creating custom tokenizers or configuring existing ones appropriately:

```python
# Create separate tables for different languages with appropriate tokenizers
cursor.execute("""
    CREATE VIRTUAL TABLE python_code USING fts5(
        filepath,
        content,
        tokenize = 'porter unicode61'
    )
""")

cursor.execute("""
    CREATE VIRTUAL TABLE c_code USING fts5(
        filepath,
        content,
        tokenize = 'unicode61'  -- No stemming for C code
    )
""")
```

### 2. Structured Code Indexing

Index different parts of code separately:

```python
cursor.execute("""
    CREATE VIRTUAL TABLE code_structure USING fts5(
        filepath,
        functions,
        classes,
        imports,
        comments,
        docstrings
    )
""")

# When indexing, parse code and extract components
def index_python_file(filepath):
    import ast
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    functions = []
    classes = []
    imports = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
    
    cursor.execute("""
        INSERT INTO code_structure 
        (filepath, functions, classes, imports)
        VALUES (?, ?, ?, ?)
    """, (
        filepath,
        ' '.join(functions),
        ' '.join(classes),
        ' '.join(imports)
    ))
```

### 3. Incremental Indexing

Implement efficient update strategies:

```python
class IncrementalIndexer:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        # Main FTS table
        self.cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS code_index
            USING fts5(filepath, content, mtime)
        """)
        
        # Metadata table for tracking
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_metadata (
                filepath TEXT PRIMARY KEY,
                mtime REAL,
                size INTEGER,
                hash TEXT
            )
        """)
    
    def needs_update(self, filepath):
        """Check if file needs re-indexing"""
        stat = os.stat(filepath)
        mtime = stat.st_mtime
        
        self.cursor.execute("""
            SELECT mtime FROM file_metadata
            WHERE filepath = ?
        """, (filepath,))
        
        result = self.cursor.fetchone()
        return result is None or result[0] < mtime
    
    def update_index(self, filepath):
        """Update index for a single file"""
        if not self.needs_update(filepath):
            return False
        
        # Remove old entry
        self.cursor.execute("""
            DELETE FROM code_index WHERE filepath = ?
        """, (filepath,))
        
        # Add new entry
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        stat = os.stat(filepath)
        
        self.cursor.execute("""
            INSERT INTO code_index (filepath, content, mtime)
            VALUES (?, ?, ?)
        """, (filepath, content, stat.st_mtime))
        
        # Update metadata
        self.cursor.execute("""
            INSERT OR REPLACE INTO file_metadata
            (filepath, mtime, size, hash)
            VALUES (?, ?, ?, ?)
        """, (filepath, stat.st_mtime, stat.st_size, None))
        
        self.conn.commit()
        return True
```

## Performance Optimization {#performance-optimization}

### 1. Index Configuration

```python
# Optimize for storage space
cursor.execute("""
    CREATE VIRTUAL TABLE compact_index USING fts5(
        content,
        detail = 'none',      -- No position information
        columnsize = 0        -- Don't store column sizes
    )
""")

# Optimize for prefix searches
cursor.execute("""
    CREATE VIRTUAL TABLE prefix_index USING fts5(
        content,
        prefix = '2 3 4'      -- Index prefixes of length 2, 3, and 4
    )
""")
```

### 2. Query Optimization

```python
# Use the rank column instead of bm25() for sorting
# This is faster:
cursor.execute("""
    SELECT * FROM code_index
    WHERE code_index MATCH ?
    ORDER BY rank
""", (query,))

# Than this:
cursor.execute("""
    SELECT * FROM code_index
    WHERE code_index MATCH ?
    ORDER BY bm25(code_index)
""", (query,))
```

### 3. Maintenance Operations

```python
def optimize_index(conn):
    """Optimize FTS index for better performance"""
    cursor = conn.cursor()
    
    # Merge all segments into a single segment
    cursor.execute("INSERT INTO code_index(code_index) VALUES('optimize')")
    
    # Rebuild the index (more thorough but slower)
    # cursor.execute("INSERT INTO code_index(code_index) VALUES('rebuild')")
    
    conn.commit()

def analyze_index(conn):
    """Analyze index statistics"""
    cursor = conn.cursor()
    
    # Get index statistics
    cursor.execute("""
        SELECT * FROM code_index_stat
    """)
    
    stats = cursor.fetchall()
    return stats
```

### 4. Batch Operations

```python
def batch_index_files(file_list, batch_size=100):
    """Index files in batches for better performance"""
    conn = sqlite3.connect('code_index.db')
    cursor = conn.cursor()
    
    # Disable auto-commit for batch operations
    conn.execute("BEGIN TRANSACTION")
    
    try:
        for i in range(0, len(file_list), batch_size):
            batch = file_list[i:i + batch_size]
            
            for filepath in batch:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                cursor.execute("""
                    INSERT INTO code_index (filepath, content)
                    VALUES (?, ?)
                """, (filepath, content))
            
            # Commit after each batch
            conn.commit()
            conn.execute("BEGIN TRANSACTION")
        
        # Final optimization
        cursor.execute("INSERT INTO code_index(code_index) VALUES('optimize')")
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
```

### 5. Memory Management

```python
# Configure cache size for better performance
conn = sqlite3.connect('code_index.db')
conn.execute("PRAGMA cache_size = -64000")  # 64MB cache
conn.execute("PRAGMA temp_store = MEMORY")  # Use memory for temp tables
```

## MCP Server Implementation Patterns {#mcp-server-implementation}

### 1. Basic MCP Server Structure

```python
import json
import sqlite3
from typing import Dict, List, Any

class CodeIndexMCPServer:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize FTS5 tables"""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS code_search
            USING fts5(
                filepath,
                filename,
                content,
                language,
                symbols,  -- Function/class names
                tokenize = 'porter unicode61'
            )
        """)
        self.conn.commit()
    
    def handle_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Route MCP requests to appropriate handlers"""
        handlers = {
            'search': self._handle_search,
            'index_file': self._handle_index_file,
            'get_definition': self._handle_get_definition,
            'find_references': self._handle_find_references,
            'update_index': self._handle_update_index
        }
        
        if method in handlers:
            return handlers[method](params)
        else:
            return {'error': f'Unknown method: {method}'}
    
    def _handle_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code search requests"""
        query = params.get('query', '')
        language = params.get('language')
        limit = params.get('limit', 20)
        
        cursor = self.conn.cursor()
        
        if language:
            sql = """
                SELECT 
                    filepath,
                    filename,
                    snippet(code_search, 2, '<mark>', '</mark>', '...', 32),
                    rank
                FROM code_search
                WHERE code_search MATCH ? AND language = ?
                ORDER BY rank
                LIMIT ?
            """
            results = cursor.execute(sql, (query, language, limit)).fetchall()
        else:
            sql = """
                SELECT 
                    filepath,
                    filename,
                    snippet(code_search, 2, '<mark>', '</mark>', '...', 32),
                    rank
                FROM code_search
                WHERE code_search MATCH ?
                ORDER BY rank
                LIMIT ?
            """
            results = cursor.execute(sql, (query, limit)).fetchall()
        
        return {
            'results': [
                {
                    'filepath': r[0],
                    'filename': r[1],
                    'snippet': r[2],
                    'score': r[3]
                }
                for r in results
            ]
        }
    
    def _handle_index_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Index a single file"""
        filepath = params['filepath']
        language = params.get('language', 'unknown')
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract symbols (simplified example)
            symbols = self._extract_symbols(content, language)
            
            cursor = self.conn.cursor()
            
            # Remove old entry if exists
            cursor.execute("""
                DELETE FROM code_search WHERE filepath = ?
            """, (filepath,))
            
            # Insert new entry
            cursor.execute("""
                INSERT INTO code_search 
                (filepath, filename, content, language, symbols)
                VALUES (?, ?, ?, ?, ?)
            """, (
                filepath,
                os.path.basename(filepath),
                content,
                language,
                ' '.join(symbols)
            ))
            
            self.conn.commit()
            
            return {'status': 'success', 'filepath': filepath}
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _extract_symbols(self, content: str, language: str) -> List[str]:
        """Extract function/class names from code"""
        symbols = []
        
        if language == 'python':
            import ast
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        symbols.append(node.name)
                    elif isinstance(node, ast.ClassDef):
                        symbols.append(node.name)
            except:
                pass
        
        # Add extractors for other languages
        
        return symbols
```

### 2. Advanced MCP Features

```python
class AdvancedCodeIndexMCP:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._initialize_advanced_tables()
    
    def _initialize_advanced_tables(self):
        """Create advanced indexing tables"""
        cursor = self.conn.cursor()
        
        # Main code index
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS code_index
            USING fts5(
                filepath,
                content,
                tokenize = 'porter unicode61',
                prefix = '2 3'
            )
        """)
        
        # Symbol index for quick navigation
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS symbol_index
            USING fts5(
                symbol_name,
                symbol_type,  -- function, class, variable
                filepath,
                line_number,
                definition
            )
        """)
        
        # Documentation index
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS doc_index
            USING fts5(
                filepath,
                docstring,
                comments
            )
        """)
        
        self.conn.commit()
    
    def handle_semantic_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle semantic code search"""
        query = params['query']
        search_type = params.get('type', 'all')  # all, symbols, docs
        
        results = []
        
        if search_type in ['all', 'code']:
            code_results = self._search_code(query)
            results.extend(code_results)
        
        if search_type in ['all', 'symbols']:
            symbol_results = self._search_symbols(query)
            results.extend(symbol_results)
        
        if search_type in ['all', 'docs']:
            doc_results = self._search_documentation(query)
            results.extend(doc_results)
        
        # Sort by relevance
        results.sort(key=lambda x: x['score'])
        
        return {'results': results[:params.get('limit', 20)]}
    
    def handle_find_definition(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Find symbol definition"""
        symbol = params['symbol']
        context_file = params.get('context_file')
        
        cursor = self.conn.cursor()
        
        # Search in symbol index
        sql = """
            SELECT 
                filepath,
                line_number,
                definition,
                symbol_type
            FROM symbol_index
            WHERE symbol_index MATCH ?
            ORDER BY rank
            LIMIT 5
        """
        
        results = cursor.execute(sql, (f'symbol_name:{symbol}',)).fetchall()
        
        # If context file provided, prioritize results from same file
        if context_file and results:
            results.sort(key=lambda x: 0 if x[0] == context_file else 1)
        
        return {
            'definitions': [
                {
                    'filepath': r[0],
                    'line': r[1],
                    'definition': r[2],
                    'type': r[3]
                }
                for r in results
            ]
        }
    
    def handle_find_references(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Find all references to a symbol"""
        symbol = params['symbol']
        
        cursor = self.conn.cursor()
        
        # Search for symbol in code content
        sql = """
            SELECT 
                filepath,
                snippet(code_index, 1, '<ref>', '</ref>', '...', 20),
                rank
            FROM code_index
            WHERE code_index MATCH ?
            ORDER BY rank
            LIMIT 50
        """
        
        # Use word boundaries for more accurate matching
        query = f'"{symbol}"'
        results = cursor.execute(sql, (query,)).fetchall()
        
        return {
            'references': [
                {
                    'filepath': r[0],
                    'snippet': r[1],
                    'score': r[2]
                }
                for r in results
            ]
        }
```

### 3. MCP Server Configuration

```json
{
  "mcpServers": {
    "code-index": {
      "command": "python",
      "args": [
        "/path/to/code_index_mcp_server.py",
        "--db-path",
        "/path/to/code_index.db",
        "--watch-dirs",
        "/path/to/project1,/path/to/project2"
      ]
    }
  }
}
```

### 4. Integration with File Watchers

```python
import watchdog.observers
import watchdog.events

class CodeIndexWatcher(watchdog.events.FileSystemEventHandler):
    def __init__(self, mcp_server):
        self.mcp_server = mcp_server
        self.supported_extensions = {
            '.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs'
        }
    
    def on_modified(self, event):
        if not event.is_directory:
            self._handle_file_change(event.src_path)
    
    def on_created(self, event):
        if not event.is_directory:
            self._handle_file_change(event.src_path)
    
    def _handle_file_change(self, filepath):
        ext = os.path.splitext(filepath)[1]
        if ext in self.supported_extensions:
            # Re-index the file
            self.mcp_server.handle_request('index_file', {
                'filepath': filepath,
                'language': self._detect_language(ext)
            })
    
    def _detect_language(self, ext):
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust'
        }
        return language_map.get(ext, 'unknown')

def start_file_watcher(mcp_server, watch_dirs):
    """Start watching directories for changes"""
    observer = watchdog.observers.Observer()
    handler = CodeIndexWatcher(mcp_server)
    
    for directory in watch_dirs:
        observer.schedule(handler, directory, recursive=True)
    
    observer.start()
    return observer
```

## Best Practices and Tips

### 1. Error Handling

```python
def safe_index_file(filepath, conn):
    """Safely index a file with error handling"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Try different encoding
        try:
            with open(filepath, 'r', encoding='latin-1') as f:
                content = f.read()
        except:
            return {'error': 'Failed to read file'}
    except Exception as e:
        return {'error': str(e)}
    
    # Index the content
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO code_index (filepath, content)
            VALUES (?, ?)
        """, (filepath, content))
        conn.commit()
        return {'success': True}
    except Exception as e:
        conn.rollback()
        return {'error': f'Database error: {str(e)}'}
```

### 2. Security Considerations

```python
def sanitize_search_query(query):
    """Sanitize user input for FTS queries"""
    # Remove potentially problematic characters
    query = query.replace('"', '""')  # Escape quotes
    
    # Limit query length
    max_length = 1000
    if len(query) > max_length:
        query = query[:max_length]
    
    return query
```

### 3. Testing

```python
import unittest

class TestCodeIndex(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE VIRTUAL TABLE code_index
            USING fts5(filepath, content)
        """)
    
    def test_basic_search(self):
        # Insert test data
        self.cursor.execute("""
            INSERT INTO code_index VALUES (?, ?)
        """, ('test.py', 'def hello_world(): print("Hello")'))
        
        # Search
        results = self.cursor.execute("""
            SELECT * FROM code_index WHERE code_index MATCH 'hello'
        """).fetchall()
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], 'test.py')
    
    def test_ranking(self):
        # Insert test data with different relevance
        test_data = [
            ('file1.py', 'hello world hello'),
            ('file2.py', 'hello'),
            ('file3.py', 'world hello world world')
        ]
        
        self.cursor.executemany("""
            INSERT INTO code_index VALUES (?, ?)
        """, test_data)
        
        # Search and check ranking
        results = self.cursor.execute("""
            SELECT filepath, rank FROM code_index
            WHERE code_index MATCH 'hello'
            ORDER BY rank
        """).fetchall()
        
        # File with more 'hello' occurrences should rank higher
        self.assertEqual(results[0][0], 'file1.py')
```

## Conclusion

SQLite FTS5 provides a powerful and efficient solution for implementing full-text search in code indexing applications. When combined with Python and the MCP server pattern, it offers:

- Fast, scalable search capabilities
- Flexible query syntax suitable for code search
- Built-in ranking and highlighting features
- Easy integration with existing SQLite databases
- Low resource requirements

Key takeaways:
1. Use appropriate tokenizers for your use case
2. Implement incremental indexing for large codebases
3. Optimize queries using the rank column and auxiliary functions
4. Consider security implications when handling user input
5. Regular maintenance (OPTIMIZE) improves performance

This guide provides a foundation for building robust code search functionality in your applications using SQLite FTS5.