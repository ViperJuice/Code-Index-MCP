"""Common utilities for plugin development.

This module provides shared utilities, helper functions, and common patterns
that can be used across different language plugins.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Union
from dataclasses import dataclass
from enum import Enum

from .plugin_template import ParsedSymbol, SymbolType

T = TypeVar('T')


class CacheStrategy(Enum):
    """Cache strategies for plugin operations."""
    NONE = "none"
    MEMORY = "memory"
    PERSISTENT = "persistent"
    HYBRID = "hybrid"


@dataclass
class PluginMetrics:
    """Metrics tracking for plugin performance."""
    files_processed: int = 0
    symbols_extracted: int = 0
    total_processing_time: float = 0.0
    average_processing_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    
    def add_processing_time(self, time_taken: float):
        """Add processing time and update averages."""
        self.total_processing_time += time_taken
        self.files_processed += 1
        self.average_processing_time = self.total_processing_time / self.files_processed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "files_processed": self.files_processed,
            "symbols_extracted": self.symbols_extracted,
            "total_processing_time": self.total_processing_time,
            "average_processing_time": self.average_processing_time,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0,
            "errors": self.errors
        }


class PluginCache:
    """Simple in-memory cache for plugin operations."""
    
    def __init__(self, max_size: int = 1000, ttl: Optional[int] = None):
        """Initialize cache with optional TTL."""
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._access_order: List[str] = []
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self._cache:
            return None
        
        value, timestamp = self._cache[key]
        
        # Check TTL
        if self.ttl and time.time() - timestamp > self.ttl:
            self.remove(key)
            return None
        
        # Update access order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        # Remove oldest if at capacity
        if len(self._cache) >= self.max_size and key not in self._cache:
            oldest_key = self._access_order.pop(0)
            del self._cache[oldest_key]
        
        self._cache[key] = (value, time.time())
        
        # Update access order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def remove(self, key: str) -> None:
        """Remove key from cache."""
        if key in self._cache:
            del self._cache[key]
        if key in self._access_order:
            self._access_order.remove(key)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._access_order.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
            "keys": list(self._cache.keys())
        }


def timing_decorator(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to measure function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            elapsed = end_time - start_time
            logger = logging.getLogger(func.__module__)
            logger.debug(f"{func.__name__} took {elapsed:.4f} seconds")
    
    return wrapper


def error_handler(
    default_return: Any = None,
    reraise: bool = False,
    log_error: bool = True
) -> Callable:
    """Decorator for handling plugin errors gracefully."""
    def decorator(func: Callable[..., T]) -> Callable[..., Union[T, Any]]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Union[T, Any]:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger = logging.getLogger(func.__module__)
                    logger.error(f"Error in {func.__name__}: {e}")
                
                if reraise:
                    raise
                
                return default_return
        
        return wrapper
    
    return decorator


def cached_method(
    cache_key_func: Optional[Callable] = None,
    ttl: Optional[int] = None,
    cache_attr: str = "_method_cache"
) -> Callable:
    """Decorator for caching method results."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(self, *args, **kwargs) -> T:
            # Initialize cache if not present
            if not hasattr(self, cache_attr):
                setattr(self, cache_attr, PluginCache(ttl=ttl))
            
            cache = getattr(self, cache_attr)
            
            # Generate cache key
            if cache_key_func:
                key = cache_key_func(self, *args, **kwargs)
            else:
                key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Compute and cache result
            result = func(self, *args, **kwargs)
            cache.set(key, result)
            
            return result
        
        return wrapper
    
    return decorator


class SymbolExtractor:
    """Utility class for common symbol extraction patterns."""
    
    @staticmethod
    def extract_function_signatures(content: str, language: str) -> List[str]:
        """Extract function signatures from content."""
        patterns = {
            "python": r"^\s*def\s+\w+\([^)]*\):",
            "javascript": r"^\s*function\s+\w+\([^)]*\)",
            "java": r"^\s*(?:public|private|protected)?\s*(?:static)?\s*\w+\s+\w+\([^)]*\)",
            "cpp": r"^\s*(?:\w+\s+)*\w+\s+\w+\([^)]*\)",
            "go": r"^\s*func\s+\w+\([^)]*\)",
            "rust": r"^\s*fn\s+\w+\([^)]*\)",
        }
        
        pattern = patterns.get(language, r"^\s*\w+\s+\w+\([^)]*\)")
        return re.findall(pattern, content, re.MULTILINE)
    
    @staticmethod
    def extract_class_names(content: str, language: str) -> List[str]:
        """Extract class names from content."""
        patterns = {
            "python": r"^\s*class\s+(\w+)",
            "javascript": r"^\s*class\s+(\w+)",
            "java": r"^\s*(?:public|private|protected)?\s*class\s+(\w+)",
            "cpp": r"^\s*class\s+(\w+)",
            "go": r"^\s*type\s+(\w+)\s+struct",
            "rust": r"^\s*struct\s+(\w+)",
        }
        
        pattern = patterns.get(language, r"^\s*(?:class|struct)\s+(\w+)")
        return re.findall(pattern, content, re.MULTILINE)
    
    @staticmethod
    def extract_imports(content: str, language: str) -> List[str]:
        """Extract import statements from content."""
        patterns = {
            "python": r"^\s*(?:import\s+(\w+)|from\s+(\w+)\s+import)",
            "javascript": r"^\s*import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]",
            "java": r"^\s*import\s+([^;]+);",
            "cpp": r"^\s*#include\s*[<\"]([^>\"]+)[>\"]",
            "go": r"^\s*import\s+[\"']([^\"']+)[\"']",
            "rust": r"^\s*use\s+([^;]+);",
        }
        
        pattern = patterns.get(language, r"^\s*(?:import|include|use)\s+([^;\s]+)")
        matches = re.findall(pattern, content, re.MULTILINE)
        
        # Flatten tuples from multiple groups
        imports = []
        for match in matches:
            if isinstance(match, tuple):
                imports.extend([m for m in match if m])
            else:
                imports.append(match)
        
        return imports
    
    @staticmethod
    def find_symbol_at_line(symbols: List[ParsedSymbol], line_number: int) -> Optional[ParsedSymbol]:
        """Find symbol at specific line number."""
        for symbol in symbols:
            if symbol.line <= line_number <= (symbol.end_line or symbol.line):
                return symbol
        return None
    
    @staticmethod
    def filter_symbols_by_type(symbols: List[ParsedSymbol], symbol_types: List[SymbolType]) -> List[ParsedSymbol]:
        """Filter symbols by type."""
        return [s for s in symbols if s.symbol_type in symbol_types]
    
    @staticmethod
    def group_symbols_by_scope(symbols: List[ParsedSymbol]) -> Dict[str, List[ParsedSymbol]]:
        """Group symbols by their scope."""
        groups = {}
        for symbol in symbols:
            scope = symbol.scope or "global"
            if scope not in groups:
                groups[scope] = []
            groups[scope].append(symbol)
        return groups
    
    @staticmethod
    def deduplicate_symbols(symbols: List[ParsedSymbol]) -> List[ParsedSymbol]:
        """Remove duplicate symbols based on name, type, and line."""
        seen = set()
        unique = []
        
        for symbol in symbols:
            key = (symbol.name, symbol.symbol_type, symbol.line)
            if key not in seen:
                unique.append(symbol)
                seen.add(key)
        
        return unique


class FileAnalyzer:
    """Utility class for analyzing file characteristics."""
    
    @staticmethod
    def estimate_complexity(content: str) -> int:
        """Estimate code complexity based on simple metrics."""
        lines = content.splitlines()
        
        # Count various complexity indicators
        complexity = 0
        
        for line in lines:
            line = line.strip()
            
            # Control flow statements
            if any(keyword in line for keyword in ['if ', 'elif ', 'else:', 'for ', 'while ', 'try:']):
                complexity += 1
            
            # Function definitions
            if 'def ' in line or 'function ' in line:
                complexity += 2
            
            # Class definitions
            if 'class ' in line:
                complexity += 3
            
            # Nested structures
            indentation = len(line) - len(line.lstrip())
            if indentation > 8:  # Deep nesting
                complexity += 1
        
        return complexity
    
    @staticmethod
    def detect_language_from_content(content: str) -> Optional[str]:
        """Detect programming language from content patterns."""
        # Simple heuristics based on common patterns
        if 'def ' in content and 'import ' in content:
            return 'python'
        elif 'function ' in content and 'var ' in content:
            return 'javascript'
        elif 'public class ' in content or 'private class ' in content:
            return 'java'
        elif '#include' in content and 'int main' in content:
            return 'cpp'
        elif 'fn ' in content and 'let ' in content:
            return 'rust'
        elif 'func ' in content and 'package ' in content:
            return 'go'
        
        return None
    
    @staticmethod
    def estimate_symbol_count(content: str) -> int:
        """Estimate number of symbols in content."""
        # Count lines that likely contain symbol definitions
        lines = content.splitlines()
        count = 0
        
        symbol_indicators = [
            'def ', 'class ', 'function ', 'var ', 'let ', 'const ',
            'struct ', 'enum ', 'interface ', 'type ', 'fn '
        ]
        
        for line in lines:
            line = line.strip().lower()
            if any(indicator in line for indicator in symbol_indicators):
                count += 1
        
        return count
    
    @staticmethod
    def get_file_stats(file_path: Path) -> Dict[str, Any]:
        """Get comprehensive file statistics."""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.splitlines()
            
            return {
                "path": str(file_path),
                "size_bytes": len(content),
                "size_lines": len(lines),
                "non_empty_lines": len([l for l in lines if l.strip()]),
                "estimated_complexity": FileAnalyzer.estimate_complexity(content),
                "estimated_symbols": FileAnalyzer.estimate_symbol_count(content),
                "detected_language": FileAnalyzer.detect_language_from_content(content),
                "extension": file_path.suffix.lower()
            }
        except Exception as e:
            return {
                "path": str(file_path),
                "error": str(e)
            }


class AsyncPluginHelper:
    """Helper for async plugin operations."""
    
    @staticmethod
    async def process_files_batch(
        files: List[Path],
        processor: Callable[[Path], Any],
        batch_size: int = 10,
        max_concurrent: int = 5
    ) -> List[Any]:
        """Process files in batches with concurrency control."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_file(file_path: Path) -> Any:
            async with semaphore:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, processor, file_path)
        
        results = []
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[process_file(f) for f in batch],
                return_exceptions=True
            )
            results.extend(batch_results)
        
        return results
    
    @staticmethod
    async def process_with_timeout(
        coro: Callable,
        timeout: float,
        default_result: Any = None
    ) -> Any:
        """Process async operation with timeout."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logging.warning(f"Operation timed out after {timeout} seconds")
            return default_result


class PluginValidator:
    """Validator for plugin implementations."""
    
    @staticmethod
    def validate_symbol(symbol: ParsedSymbol) -> List[str]:
        """Validate a parsed symbol and return list of issues."""
        issues = []
        
        if not symbol.name or not symbol.name.strip():
            issues.append("Symbol name is empty")
        
        if symbol.line <= 0:
            issues.append("Invalid line number")
        
        if symbol.column < 0:
            issues.append("Invalid column number")
        
        if symbol.end_line and symbol.end_line < symbol.line:
            issues.append("End line is before start line")
        
        if symbol.symbol_type == SymbolType.UNKNOWN:
            issues.append("Unknown symbol type")
        
        return issues
    
    @staticmethod
    def validate_plugin_config(config: Dict[str, Any]) -> List[str]:
        """Validate plugin configuration."""
        issues = []
        
        required_fields = ['language', 'extensions']
        for field in required_fields:
            if field not in config:
                issues.append(f"Missing required field: {field}")
        
        if 'extensions' in config and not isinstance(config['extensions'], list):
            issues.append("Extensions must be a list")
        
        if 'max_file_size' in config and config['max_file_size'] <= 0:
            issues.append("Max file size must be positive")
        
        return issues


def create_cache_key(*args, **kwargs) -> str:
    """Create a cache key from arguments."""
    key_parts = []
    
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        elif isinstance(arg, Path):
            key_parts.append(str(arg))
        else:
            key_parts.append(str(hash(str(arg))))
    
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")
    
    key_string = ":".join(key_parts)
    return hashlib.sha256(key_string.encode()).hexdigest()[:16]


def safe_file_read(file_path: Path, encoding: str = 'utf-8', max_size: int = 10 * 1024 * 1024) -> Optional[str]:
    """Safely read file with size and encoding checks."""
    try:
        # Check file size
        if file_path.stat().st_size > max_size:
            logging.warning(f"File {file_path} exceeds max size {max_size}")
            return None
        
        # Try to read with specified encoding
        try:
            return file_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            # Try with utf-8 and ignore errors
            return file_path.read_text(encoding='utf-8', errors='ignore')
    
    except Exception as e:
        logging.error(f"Failed to read file {file_path}: {e}")
        return None


def normalize_symbol_name(name: str) -> str:
    """Normalize symbol name for consistent processing."""
    if not name:
        return ""
    
    # Remove leading/trailing whitespace
    name = name.strip()
    
    # Remove quotes if present
    if (name.startswith('"') and name.endswith('"')) or (name.startswith("'") and name.endswith("'")):
        name = name[1:-1]
    
    return name


def get_file_language_from_extension(file_path: Path) -> Optional[str]:
    """Get programming language from file extension."""
    extension_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.kt': 'kotlin',
        '.cpp': 'cpp',
        '.cxx': 'cpp',
        '.cc': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.hpp': 'cpp',
        '.rs': 'rust',
        '.go': 'go',
        '.rb': 'ruby',
        '.php': 'php',
        '.dart': 'dart',
        '.html': 'html',
        '.css': 'css',
    }
    
    return extension_map.get(file_path.suffix.lower())


# Export commonly used items
__all__ = [
    'CacheStrategy',
    'PluginMetrics',
    'PluginCache',
    'timing_decorator',
    'error_handler',
    'cached_method',
    'SymbolExtractor',
    'FileAnalyzer',
    'AsyncPluginHelper',
    'PluginValidator',
    'create_cache_key',
    'safe_file_read',
    'normalize_symbol_name',
    'get_file_language_from_extension'
]