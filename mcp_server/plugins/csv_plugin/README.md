# CSV Plugin for Code-Index-MCP

A comprehensive plugin for indexing and analyzing CSV (Comma-Separated Values) and TSV (Tab-Separated Values) files within the Code-Index-MCP system.

## Features

### 🔍 Intelligent Format Detection
- **Automatic Delimiter Detection**: Identifies comma, tab, pipe, semicolon, colon, and space delimiters
- **Quote Character Recognition**: Handles single and double quotes with proper escaping
- **Header Detection**: Automatically determines if the first row contains column headers
- **Multi-line Cell Support**: Correctly parses cells containing newlines

### 📊 Data Type Analysis
- **Automatic Type Inference**: Detects string, number, date, boolean, and mixed types
- **Null Value Tracking**: Identifies nullable columns and missing data
- **Unique Value Counting**: Tracks cardinality for each column
- **Sample Value Collection**: Stores representative values for quick inspection

### 📈 Statistical Analysis
- **Numeric Column Statistics**: Mean, median, min, max, standard deviation
- **Data Distribution**: Analyzes value distributions and patterns
- **Data Quality Metrics**: Identifies potential data quality issues
- **Column Profiling**: Comprehensive analysis of each column's characteristics

### 🎯 Advanced Search
- **Text Search**: Find values across all cells
- **Column-based Queries**: Search specific columns with operators
- **Pattern Matching**: Support for complex search patterns
- **Statistical Queries**: Find files based on data characteristics

## Supported Formats

| Extension | Format | Description |
|-----------|--------|-------------|
| `.csv` | CSV | Standard comma-separated values |
| `.tsv` | TSV | Tab-separated values |
| `.tab` | TAB | Alternative tab-separated format |
| `.dat` | DAT | Generic delimited data files |

## Usage

### Basic Example

```python
from mcp_server.plugins.csv_plugin import CSVPlugin

# Initialize the plugin
plugin = CSVPlugin()

# Index a CSV file
with open("data.csv", "r") as f:
    content = f.read()
    result = plugin.indexFile("data.csv", content)

# Access schema information
schema = next(s for s in result["symbols"] if s["kind"] == "schema")
print(f"Columns: {schema['metadata']['column_count']}")
print(f"Rows: {schema['metadata']['row_count']}")

# Get column information
headers = [s for s in result["symbols"] if s["kind"] == "header"]
for header in headers:
    print(f"{header['symbol']}: {header['metadata']['data_type']}")
```

### Advanced Search

```python
# Search for specific values
results = plugin.search("California")

# Column-based queries
results = plugin.search("column:age > 25")
results = plugin.search("column:status = 'active'")
results = plugin.search("column:price between 100 and 500")
```

## Symbol Types

### Schema Symbol
Contains overall file structure and metadata:
- Delimiter used
- Quote character
- Header presence
- Row and column counts
- Encoding information

### Header Symbols
Represent individual columns with:
- Column name and index
- Data type (inferred)
- Nullable status
- Unique value count
- Statistical information (for numeric columns)
- Sample values

### Statistic Symbols
Provide file-level statistics:
- Total rows and columns
- Column type distribution
- Data quality metrics

## Configuration

```python
from mcp_server.plugins.plugin_template import PluginConfig

config = PluginConfig(
    max_file_size=50 * 1024 * 1024,  # 50MB limit
    enable_caching=True,
    cache_ttl=3600,  # 1 hour
    enable_semantic_analysis=True
)

plugin = CSVPlugin(config=config)
```

## Tree-sitter Integration

When available, the plugin uses tree-sitter-csv for enhanced parsing capabilities:

```scheme
; Extract headers
(header
  (field) @name) @definition.field

; Extract numeric fields
(field
  (#match? @number "^-?[0-9]+\\.?[0-9]*$")) @number

; Extract date fields
(field
  (#match? @constant.builtin "^[0-9]{4}-[0-9]{2}-[0-9]{2}")) @constant.builtin
```

## Data Type Detection

The plugin automatically detects the following data types:

### String
- Text values that don't match other patterns
- Mixed content with special characters

### Number
- Integers and floating-point values
- Scientific notation supported
- Negative numbers handled

### Date
- Common date formats (YYYY-MM-DD, MM/DD/YYYY, etc.)
- DateTime with time components
- Configurable format patterns

### Boolean
- true/false, yes/no, 1/0
- Case-insensitive matching

### Mixed
- Columns with multiple data types
- Indicates potential data quality issues

## Performance Considerations

- **Streaming Parser**: Handles large files efficiently
- **Sample-based Analysis**: Uses configurable sample sizes for type inference
- **Caching**: Results are cached for repeated queries
- **Parallel Processing**: Can analyze multiple files concurrently

## Limitations

1. **File Size**: Default limit of 10MB (configurable)
2. **Encoding**: Currently supports UTF-8 (extensible)
3. **Complex Formats**: Limited support for nested structures
4. **Binary Formats**: Text-based formats only (no Excel support yet)

## Examples

See the `examples/demo_csv_analysis.py` file for comprehensive usage examples.

## Testing

Run the test suite:

```bash
pytest tests/test_csv_plugin.py -v
```

## Future Enhancements

- [ ] Excel file support (.xlsx, .xls)
- [ ] JSON and XML structured data
- [ ] Advanced data transformations
- [ ] Schema validation rules
- [ ] Data lineage tracking
- [ ] Integration with data visualization tools

## Contributing

Contributions are welcome! Please see the main project's contributing guidelines.

## License

This plugin is part of the Code-Index-MCP project and follows the same license terms.