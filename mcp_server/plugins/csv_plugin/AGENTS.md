# CSV Plugin Agent Instructions

## Overview
The CSV plugin provides comprehensive support for CSV (Comma-Separated Values) and TSV (Tab-Separated Values) files, enabling advanced data analysis and indexing capabilities within the Code-Index-MCP system.

## Key Features

### 1. Multi-Format Support
- **CSV**: Standard comma-separated values
- **TSV**: Tab-separated values
- **Custom Delimiters**: Pipe (|), semicolon (;), colon (:), space
- **Extensions**: .csv, .tsv, .tab, .dat

### 2. Intelligent Schema Detection
- **Delimiter Detection**: Automatically identifies the delimiter used
- **Header Detection**: Determines if the first row contains column headers
- **Quote Character Detection**: Identifies quote characters for escaped values
- **Encoding Detection**: UTF-8 support (extensible)

### 3. Column Analysis
- **Data Type Inference**: Automatically detects column types
  - String
  - Number (integer/float)
  - Date/DateTime
  - Boolean
  - Mixed (heterogeneous data)
- **Statistical Analysis**: For numeric columns
  - Mean, median, min, max
  - Standard deviation
  - Distribution metrics
- **Uniqueness Analysis**: Identifies potential key columns
- **Null Value Detection**: Tracks missing data

### 4. Advanced Features
- **Large File Support**: Efficient streaming for large datasets
- **Multi-line Cell Support**: Handles cells with embedded newlines
- **Quoted String Handling**: Proper parsing of quoted values
- **Schema Validation**: Validates data against expected schema
- **Data Profiling**: Comprehensive data quality metrics

## Symbol Types

### Schema Symbol
- **Name**: `{filename}_schema`
- **Type**: `schema`
- **Contains**: Complete file structure information
- **Metadata**: Delimiter, row count, column count, encoding

### Header Symbols
- **Name**: Column name
- **Type**: `header`
- **Contains**: Column metadata
- **Metadata**: Data type, nullable, unique values, statistics

### Statistic Symbols
- **Name**: `{filename}_statistics`
- **Type**: `statistic`
- **Contains**: Overall file statistics
- **Metadata**: Type distribution, data quality metrics

## Search Capabilities

### Standard Search
- Search within cell values
- Search column names
- Pattern matching across rows

### Column-Based Queries
```
column:age > 25
column:status = "active"
column:price between 10 and 100
```

### Statistical Queries
- Find files with specific data characteristics
- Identify datasets by schema properties

## Usage Examples

### Basic Indexing
```python
# Index a CSV file
shard = plugin.indexFile("data.csv", content)

# Access schema information
schema = shard["symbols"][0]["metadata"]["schema"]
print(f"Columns: {schema['column_count']}")
print(f"Rows: {schema['row_count']}")
```

### Column Analysis
```python
# Get column information
for symbol in shard["symbols"]:
    if symbol["kind"] == "header":
        print(f"Column: {symbol['symbol']}")
        print(f"Type: {symbol['metadata']['data_type']}")
        if symbol['metadata'].get('statistics'):
            print(f"Stats: {symbol['metadata']['statistics']}")
```

### Advanced Search
```python
# Search for numeric columns
results = plugin.search("column:* type:number")

# Search for specific values
results = plugin.search('column:price > 100')
```

## Best Practices

### 1. File Preparation
- Use consistent delimiters throughout the file
- Include headers for better column identification
- Ensure consistent data types within columns
- Use standard date formats

### 2. Performance Optimization
- For large files, the plugin samples rows for type inference
- Statistical analysis is performed on configurable sample sizes
- Caching is used for repeated queries

### 3. Data Quality
- The plugin identifies data quality issues:
  - Mixed types in columns
  - Missing values
  - Inconsistent formatting
  - Delimiter conflicts

## Tree-Sitter Integration

When available, the CSV plugin uses tree-sitter-csv for enhanced parsing:
- More accurate cell boundary detection
- Better handling of edge cases
- Structured AST for complex queries

## Configuration

```python
config = PluginConfig(
    max_file_size=50 * 1024 * 1024,  # 50MB limit
    enable_caching=True,
    cache_ttl=3600,
    enable_semantic_analysis=True
)

plugin = CSVPlugin(config=config)
```

## Extensibility

The CSV plugin can be extended for:
- Additional file formats (Excel, JSON, XML)
- Custom data type detection
- Domain-specific analysis (financial, scientific)
- Integration with data validation frameworks

## Technical Notes

### Memory Efficiency
- Streaming parser for large files
- Configurable sampling for analysis
- Lazy loading of data

### Error Handling
- Graceful handling of malformed CSV
- Clear error messages for debugging
- Fallback parsing strategies

### Integration Points
- Works with semantic search for data discovery
- Integrates with storage layer for persistence
- Supports cross-file analysis and joins

## Future Enhancements

1. **Excel Support**: Native .xlsx/.xls parsing
2. **Data Transformations**: Built-in data cleaning
3. **Schema Evolution**: Track schema changes over time
4. **Data Lineage**: Track data flow between files
5. **Advanced Analytics**: Machine learning integration