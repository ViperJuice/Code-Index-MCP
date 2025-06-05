"""CSV and TSV plugin for indexing and analyzing structured data files."""

from __future__ import annotations

import csv
import io
import re
import statistics as stats_module
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from ..plugin_template import (
    LanguagePluginBase,
    ParsedSymbol,
    PluginConfig,
    SymbolType,
    ParsingError,
)
from ...plugin_base import IndexShard
from ...core.logging import get_logger


# Define CSV-specific symbol types as constants
class CSVSymbolTypes:
    """CSV-specific symbol types."""
    HEADER = "header"
    ROW = "row"
    COLUMN = "column"
    CELL = "cell"
    SCHEMA = "schema"
    STATISTIC = "statistic"


@dataclass
class ColumnInfo:
    """Information about a CSV column."""
    name: str
    index: int
    data_type: str  # string, number, date, boolean, mixed
    nullable: bool
    unique_values: int
    sample_values: List[Any]
    statistics: Optional[Dict[str, Any]] = None


@dataclass
class CSVSchema:
    """CSV file schema information."""
    delimiter: str
    quote_char: str
    has_header: bool
    columns: List[ColumnInfo]
    row_count: int
    encoding: str
    line_terminator: str


class CSVPlugin(LanguagePluginBase):
    """Plugin for parsing and indexing CSV/TSV files."""
    
    def __init__(
        self,
        config: Optional[PluginConfig] = None,
        sqlite_store: Optional[Any] = None,
        cache_manager: Optional[Any] = None
    ):
        """Initialize CSV plugin with enhanced configuration."""
        # CSV-specific configuration
        self.max_sample_rows = 1000  # For type inference
        self.max_unique_values = 100  # For categorical detection
        self.date_formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%d-%m-%Y %H:%M:%S",
        ]
        
        super().__init__(config, sqlite_store, cache_manager)
        
    def get_language(self) -> str:
        """Return the language this plugin supports."""
        return "csv"
    
    def get_supported_extensions(self) -> List[str]:
        """Return list of file extensions this plugin supports."""
        return [".csv", ".tsv", ".tab", ".dat"]
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        """Return regex patterns for CSV structures."""
        return {
            SymbolType.UNKNOWN: r'^(.+)$',  # Basic pattern for any row
        }
    
    def supports_tree_sitter(self) -> bool:
        """CSV supports tree-sitter through tree-sitter-csv."""
        return True
    
    def _extract_symbols(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Extract symbols from CSV content."""
        symbols = []
        
        try:
            # Detect CSV properties
            schema = self._detect_schema(content, file_path)
            
            # Add schema as a symbol
            symbols.append(ParsedSymbol(
                name=Path(file_path).stem + "_schema",
                symbol_type=SymbolType.UNKNOWN,  # Using standard type
                line=1,
                column=0,
                signature=f"delimiter={repr(schema.delimiter)}, columns={len(schema.columns)}, rows={schema.row_count}",
                docstring=self._generate_schema_doc(schema),
                metadata={
                    "kind": CSVSymbolTypes.SCHEMA,
                    "schema": {
                        "delimiter": schema.delimiter,
                        "quote_char": schema.quote_char,
                        "has_header": schema.has_header,
                        "column_count": len(schema.columns),
                        "row_count": schema.row_count,
                        "encoding": schema.encoding,
                        "line_terminator": schema.line_terminator,
                    },
                    "delimiter": schema.delimiter,
                    "has_header": schema.has_header,
                    "column_count": len(schema.columns),
                    "row_count": schema.row_count,
                }
            ))
            
            # Add headers as symbols
            if schema.has_header:
                for col in schema.columns:
                    symbols.append(ParsedSymbol(
                        name=col.name,
                        symbol_type=SymbolType.FIELD,  # Using standard field type
                        line=1,
                        column=col.index,
                        signature=f"{col.name}: {col.data_type}",
                        docstring=self._generate_column_doc(col),
                        metadata={
                            "kind": CSVSymbolTypes.HEADER,
                            "column_index": col.index,
                            "data_type": col.data_type,
                            "nullable": col.nullable,
                            "unique_values": col.unique_values,
                            "statistics": col.statistics,
                        }
                    ))
            
            # Add statistical symbols
            stats_symbols = self._extract_statistics(schema, content)
            symbols.extend(stats_symbols)
            
            # If Tree-sitter is available, use it for more detailed parsing
            if self._parser and self.supports_tree_sitter():
                try:
                    tree_symbols = self._extract_symbols_tree_sitter(content, file_path)
                    # Merge tree-sitter symbols with our analysis
                    symbols.extend(tree_symbols)
                except Exception as e:
                    self.logger.debug(f"Tree-sitter parsing not available: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to parse CSV {file_path}: {e}")
            raise ParsingError(f"CSV parsing failed: {e}") from e
        
        return symbols
    
    def _detect_schema(self, content: str, file_path: str) -> CSVSchema:
        """Detect CSV schema including delimiter, headers, and column types."""
        # Detect delimiter
        delimiter = self._detect_delimiter(content)
        
        # Detect quote character
        quote_char = self._detect_quote_char(content)
        
        # Parse CSV
        reader = csv.reader(io.StringIO(content), delimiter=delimiter, quotechar=quote_char)
        rows = list(reader)
        
        if not rows:
            raise ParsingError("Empty CSV file")
        
        # Detect if first row is header
        has_header = self._detect_header(rows)
        
        # Extract column information
        columns = self._analyze_columns(rows, has_header)
        
        # Detect line terminator
        line_terminator = '\r\n' if '\r\n' in content else '\n'
        
        return CSVSchema(
            delimiter=delimiter,
            quote_char=quote_char,
            has_header=has_header,
            columns=columns,
            row_count=len(rows) - (1 if has_header else 0),
            encoding='utf-8',  # Assumed for now
            line_terminator=line_terminator
        )
    
    def _detect_delimiter(self, content: str) -> str:
        """Detect the delimiter used in the CSV file."""
        # Try common delimiters
        delimiters = [',', '\t', '|', ';', ':', ' ']
        sample_lines = content.split('\n')[:10]  # Sample first 10 lines
        
        delimiter_scores = {}
        for delimiter in delimiters:
            counts = [line.count(delimiter) for line in sample_lines if line.strip()]
            if counts and len(set(counts)) == 1 and counts[0] > 0:
                # Consistent delimiter count across lines
                delimiter_scores[delimiter] = counts[0]
        
        if not delimiter_scores:
            # Fall back to comma
            return ','
        
        # Return delimiter with highest consistent count
        return max(delimiter_scores.items(), key=lambda x: x[1])[0]
    
    def _detect_quote_char(self, content: str) -> str:
        """Detect the quote character used in the CSV file."""
        # Count occurrences of single and double quotes
        double_quotes = content.count('"')
        single_quotes = content.count("'")
        
        if double_quotes > single_quotes:
            return '"'
        elif single_quotes > double_quotes:
            return "'"
        else:
            return '"'  # Default to double quotes
    
    def _detect_header(self, rows: List[List[str]]) -> bool:
        """Detect if the first row contains headers."""
        if len(rows) < 2:
            return True  # Assume single row is header
        
        first_row = rows[0]
        other_rows = rows[1:min(11, len(rows))]  # Sample next 10 rows
        
        # Check if first row has different characteristics
        header_score = 0
        
        # Check if all values in first row are non-numeric
        for val in first_row:
            try:
                float(val.strip())
            except ValueError:
                header_score += 1
        
        # Check if other rows have numeric values
        numeric_count = 0
        for row in other_rows:
            for val in row:
                try:
                    float(val.strip())
                    numeric_count += 1
                except ValueError:
                    pass
        
        # If first row is mostly non-numeric and other rows have numbers, it's likely a header
        return header_score > len(first_row) * 0.7 and numeric_count > len(other_rows) * len(first_row) * 0.3
    
    def _analyze_columns(self, rows: List[List[str]], has_header: bool) -> List[ColumnInfo]:
        """Analyze columns to determine data types and statistics."""
        if not rows:
            return []
        
        # Get column names
        if has_header:
            column_names = rows[0]
            data_rows = rows[1:self.max_sample_rows + 1]
        else:
            column_names = [f"column_{i}" for i in range(len(rows[0]))]
            data_rows = rows[:self.max_sample_rows]
        
        columns = []
        for idx, name in enumerate(column_names):
            # Extract column values
            values = []
            for row in data_rows:
                if idx < len(row):
                    values.append(row[idx])
            
            # Analyze column
            col_info = self._analyze_column(name, idx, values)
            columns.append(col_info)
        
        return columns
    
    def _analyze_column(self, name: str, index: int, values: List[str]) -> ColumnInfo:
        """Analyze a single column to determine its properties."""
        # Clean values
        clean_values = [v.strip() for v in values if v.strip()]
        
        # Check for nulls
        nullable = len(clean_values) < len(values)
        
        # Count unique values
        unique_values = len(set(clean_values))
        
        # Determine data type
        data_type = self._infer_data_type(clean_values)
        
        # Calculate statistics if numeric
        statistics = None
        if data_type == "number" and clean_values:
            numeric_values = []
            for val in clean_values:
                try:
                    numeric_values.append(float(val))
                except ValueError:
                    pass
            
            if numeric_values:
                statistics = {
                    "mean": stats_module.mean(numeric_values),
                    "median": stats_module.median(numeric_values),
                    "min": min(numeric_values),
                    "max": max(numeric_values),
                    "std_dev": stats_module.stdev(numeric_values) if len(numeric_values) > 1 else 0,
                }
        
        # Sample values
        sample_values = clean_values[:5] if clean_values else []
        
        return ColumnInfo(
            name=name,
            index=index,
            data_type=data_type,
            nullable=nullable,
            unique_values=unique_values,
            sample_values=sample_values,
            statistics=statistics
        )
    
    def _infer_data_type(self, values: List[str]) -> str:
        """Infer the data type of a column from its values."""
        if not values:
            return "string"
        
        type_counts = Counter()
        
        for val in values[:100]:  # Sample first 100 values
            val = val.strip()
            if not val:
                continue
            
            # Check boolean
            if val.lower() in ('true', 'false', 'yes', 'no', '1', '0'):
                type_counts['boolean'] += 1
                continue
            
            # Check number
            try:
                float(val)
                type_counts['number'] += 1
                continue
            except ValueError:
                pass
            
            # Check date
            is_date = False
            for date_format in self.date_formats:
                try:
                    datetime.strptime(val, date_format)
                    type_counts['date'] += 1
                    is_date = True
                    break
                except ValueError:
                    pass
            
            if not is_date:
                type_counts['string'] += 1
        
        # Determine predominant type
        if not type_counts:
            return "string"
        
        total = sum(type_counts.values())
        predominant_type = type_counts.most_common(1)[0]
        
        # If more than 80% of values are of one type, use that type
        if predominant_type[1] / total > 0.8:
            return predominant_type[0]
        else:
            return "mixed"
    
    def _generate_schema_doc(self, schema: CSVSchema) -> str:
        """Generate documentation for the CSV schema."""
        doc_lines = [
            f"CSV Schema for {schema.row_count} rows",
            f"Delimiter: {repr(schema.delimiter)}",
            f"Quote Character: {repr(schema.quote_char)}",
            f"Has Header: {schema.has_header}",
            f"Columns: {len(schema.columns)}",
            "",
            "Column Summary:",
        ]
        
        for col in schema.columns:
            doc_lines.append(f"  - {col.name} ({col.data_type}): {col.unique_values} unique values")
        
        return "\n".join(doc_lines)
    
    def _generate_column_doc(self, col: ColumnInfo) -> str:
        """Generate documentation for a column."""
        doc_lines = [
            f"Column: {col.name}",
            f"Type: {col.data_type}",
            f"Nullable: {col.nullable}",
            f"Unique Values: {col.unique_values}",
        ]
        
        if col.sample_values:
            doc_lines.append(f"Sample Values: {', '.join(repr(v) for v in col.sample_values[:3])}")
        
        if col.statistics:
            doc_lines.append("")
            doc_lines.append("Statistics:")
            for stat, value in col.statistics.items():
                doc_lines.append(f"  {stat}: {value:.2f}")
        
        return "\n".join(doc_lines)
    
    def _extract_statistics(self, schema: CSVSchema, content: str) -> List[ParsedSymbol]:
        """Extract statistical symbols from the CSV data."""
        symbols = []
        
        # Overall statistics
        stats_name = Path(schema.columns[0].name).stem + "_statistics" if schema.columns else "statistics"
        
        stats_info = {
            "total_rows": schema.row_count,
            "total_columns": len(schema.columns),
            "delimiter": schema.delimiter,
            "has_header": schema.has_header,
            "numeric_columns": sum(1 for col in schema.columns if col.data_type == "number"),
            "string_columns": sum(1 for col in schema.columns if col.data_type == "string"),
            "date_columns": sum(1 for col in schema.columns if col.data_type == "date"),
            "boolean_columns": sum(1 for col in schema.columns if col.data_type == "boolean"),
            "mixed_columns": sum(1 for col in schema.columns if col.data_type == "mixed"),
        }
        
        symbols.append(ParsedSymbol(
            name=stats_name,
            symbol_type=SymbolType.UNKNOWN,  # Using standard type
            line=1,
            column=0,
            signature=f"rows={schema.row_count}, columns={len(schema.columns)}",
            docstring=self._format_statistics(stats_info),
            metadata={
                "kind": CSVSymbolTypes.STATISTIC,
                **stats_info
            }
        ))
        
        return symbols
    
    def _format_statistics(self, stats: Dict[str, Any]) -> str:
        """Format statistics as documentation."""
        lines = ["CSV File Statistics:"]
        for key, value in stats.items():
            formatted_key = key.replace('_', ' ').title()
            lines.append(f"  {formatted_key}: {value}")
        return "\n".join(lines)
    
    def _extract_symbols_tree_sitter(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Extract symbols using Tree-sitter CSV parser."""
        if not self._parser:
            return []
        
        try:
            # Parse with tree-sitter
            tree = self._parser.parse(content)
            if not tree:
                return []
            
            symbols = []
            
            # Tree-sitter CSV query for rows and cells
            # This assumes tree-sitter-csv provides these node types
            query = """
            (row) @row
            (field) @field
            (header) @header
            """
            
            # Execute query if parser supports it
            if hasattr(self._parser, 'query'):
                captures = self._parser.query(query, tree.root_node)
                
                for node, capture_name in captures:
                    if capture_name == "header":
                        symbols.append(ParsedSymbol(
                            name=node.text.decode('utf-8'),
                            symbol_type=SymbolType.FIELD,
                            line=node.start_point[0] + 1,
                            column=node.start_point[1],
                            end_line=node.end_point[0] + 1,
                            end_column=node.end_point[1],
                            signature=node.text.decode('utf-8'),
                            metadata={"kind": CSVSymbolTypes.HEADER, "node_type": "header"}
                        ))
            
            return symbols
            
        except Exception as e:
            self.logger.debug(f"Tree-sitter parsing failed: {e}")
            return []
    
    def _create_index_shard(self, file_path: str, symbols: List[ParsedSymbol]) -> IndexShard:
        """Convert parsed symbols to IndexShard format with CSV-specific handling."""
        symbol_dicts = []
        for symbol in symbols:
            # Use the custom kind from metadata if available
            kind = symbol.metadata.get("kind", symbol.symbol_type.value)
            
            symbol_dicts.append({
                "symbol": symbol.name,
                "kind": kind,
                "signature": symbol.signature or "",
                "line": symbol.line,
                "span": (symbol.line, symbol.end_line or symbol.line),
                "docstring": symbol.docstring,
                "scope": symbol.scope,
                "modifiers": list(symbol.modifiers),
                "metadata": symbol.metadata
            })
        
        return {
            "file": file_path,
            "symbols": symbol_dicts,
            "language": self.lang
        }
    
    def search(self, query: str, opts: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Enhanced search for CSV files supporting column and value queries."""
        opts = opts or {}
        
        # Check if this is a column-based query (e.g., "column:age > 25")
        column_match = re.match(r'column:(\w+)\s*([><=!]+)\s*(.+)', query)
        if column_match:
            column_name = column_match.group(1)
            operator = column_match.group(2)
            value = column_match.group(3).strip('"\'')
            
            # Search for files with matching column values
            results = self._search_column_values(column_name, operator, value, opts.get("limit", 20))
            return results
        
        # Fall back to standard search
        return super().search(query, opts)
    
    def _search_column_values(self, column: str, operator: str, value: str, limit: int) -> List[Dict[str, Any]]:
        """Search for rows with specific column values."""
        results = []
        
        # This would typically query the indexed data
        # For now, return a placeholder
        self.logger.info(f"Searching for {column} {operator} {value}")
        
        return results


# Make plugin available at package level
__all__ = ["CSVPlugin"]