# CSV Plugin - Claude Integration Guide

This document provides guidance for Claude when working with the CSV plugin in the Code-Index-MCP system.

## Plugin Overview

The CSV plugin enables comprehensive analysis and indexing of structured data files (CSV, TSV, and related formats). It provides intelligent schema detection, data type inference, and statistical analysis capabilities.

## Core Capabilities

### File Format Support
- **Primary**: .csv (comma-separated)
- **Secondary**: .tsv (tab-separated), .tab, .dat
- **Delimiters**: Automatic detection of comma, tab, pipe, semicolon, colon, space

### Intelligent Analysis
- Automatic delimiter and quote character detection
- Header row identification
- Column data type inference (string, number, date, boolean, mixed)
- Statistical analysis for numeric columns
- Data quality assessment

## When to Use This Plugin

Use the CSV plugin when:
- Working with structured tabular data
- Analyzing data exports from databases or spreadsheets
- Processing ETL pipelines or data transformations
- Performing data quality assessments
- Building data catalogs or documentation

## Key Implementation Details

### Symbol Types
1. **Schema Symbol**: Contains overall file structure
2. **Header Symbols**: Represent individual columns
3. **Statistic Symbols**: Provide data insights

### Search Capabilities
- Standard text search within data
- Column-based queries: `column:name operator value`
- Statistical queries for data profiling

## Best Practices for Claude

### When Helping Users

1. **Data Analysis Tasks**
   - Suggest using the CSV plugin for structured data files
   - Explain the automatic schema detection capabilities
   - Highlight statistical analysis features for numeric data

2. **Data Quality Issues**
   - The plugin identifies mixed data types, missing values, and inconsistencies
   - Guide users on interpreting data quality metrics
   - Suggest data cleaning strategies based on plugin output

3. **Performance Considerations**
   - Large files are handled efficiently through sampling
   - Explain the trade-offs between full analysis and performance
   - Mention caching benefits for repeated queries

### Code Examples

When demonstrating CSV plugin usage:

```python
# Basic usage
plugin = CSVPlugin()
result = plugin.indexFile("data.csv", content)

# Accessing schema information
schema_symbol = next(s for s in result["symbols"] if s["kind"] == "schema")
print(f"File has {schema_symbol['metadata']['column_count']} columns")

# Column analysis
headers = [s for s in result["symbols"] if s["kind"] == "header"]
for header in headers:
    print(f"{header['symbol']}: {header['metadata']['data_type']}")
```

### Common User Scenarios

1. **"How do I analyze my CSV file?"**
   - The plugin automatically detects structure and data types
   - Provides statistical summaries for numeric columns
   - Identifies data quality issues

2. **"Can it handle large datasets?"**
   - Yes, through efficient streaming and sampling
   - Configurable limits for performance tuning
   - Caching for repeated analysis

3. **"What about non-standard formats?"**
   - Automatic delimiter detection handles most cases
   - Supports various quote characters and escaping
   - Handles multi-line cells correctly

## Integration Points

- Works with the semantic search system for data discovery
- Integrates with the storage layer for persistence
- Compatible with other plugins for cross-format analysis

## Limitations to Mention

1. Currently focuses on text-based formats (not binary like Excel)
2. Statistical analysis limited to numeric columns
3. No built-in data transformation capabilities (analysis only)

## Future Capabilities

When users ask about roadmap:
- Excel format support planned
- Advanced data profiling features
- Schema evolution tracking
- Data lineage capabilities