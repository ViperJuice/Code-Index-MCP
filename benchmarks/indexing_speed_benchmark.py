#!/usr/bin/env python3
"""
Indexing speed performance benchmark.
Target: 10K files/minute
"""

import time
import os
import tempfile
import shutil
import random
import json
import threading
from pathlib import Path
from typing import List, Dict, Any
import multiprocessing as mp

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.plugins.plugin_factory import PluginFactory
from mcp_server.watcher import FileWatcher


class IndexingSpeedBenchmark:
    """Benchmark indexing speed performance."""
    
    def __init__(self):
        self.temp_dir = None
        self.db_path = None
        self.store = None
        self.results = {}
        
    def setup(self):
        """Set up test environment."""
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp(prefix="index_benchmark_")
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            self.db_path = tmp.name
        
        self.store = SQLiteStore(self.db_path)
        
        print(f"Test directory: {self.temp_dir}")
        print(f"Database: {self.db_path}")
    
    def generate_test_files(self, num_files: int, language_distribution: Dict[str, float]):
        """Generate test files with specified language distribution."""
        print(f"\nGenerating {num_files} test files...")
        
        files_created = 0
        
        for lang, percentage in language_distribution.items():
            num_lang_files = int(num_files * percentage)
            
            for i in range(num_lang_files):
                if files_created >= num_files:
                    break
                
                # Create directory structure
                module_dir = Path(self.temp_dir) / f"module_{files_created // 100}"
                module_dir.mkdir(exist_ok=True)
                
                # Generate file content
                content = self._generate_code_content(lang, i)
                
                # Determine file extension
                ext = {
                    'python': '.py',
                    'javascript': '.js',
                    'java': '.java',
                    'go': '.go',
                    'rust': '.rs',
                    'c': '.c',
                    'cpp': '.cpp',
                    'markdown': '.md',
                    'plaintext': '.txt'
                }.get(lang, '.txt')
                
                # Write file
                file_path = module_dir / f"file_{files_created}{ext}"
                file_path.write_text(content)
                
                files_created += 1
        
        print(f"Generated {files_created} files")
        return files_created
    
    def _generate_code_content(self, language: str, index: int) -> str:
        """Generate realistic code content for a language."""
        templates = {
            'python': '''
# Module {index}
import os
import sys
from typing import List, Dict

class Component{index}:
    """A sample component class."""
    
    def __init__(self, name: str):
        self.name = name
        self.data = {{}}
    
    def process(self, items: List[str]) -> Dict[str, Any]:
        """Process items and return results."""
        results = {{}}
        for item in items:
            results[item] = self._analyze(item)
        return results
    
    def _analyze(self, item: str) -> int:
        """Analyze a single item."""
        return len(item) * {index}

def main():
    """Main entry point."""
    component = Component{index}("test")
    print(component.process(["a", "b", "c"]))

if __name__ == "__main__":
    main()
''',
            'javascript': '''
// Module {index}
const {{ EventEmitter }} = require('events');

class Component{index} extends EventEmitter {{
    constructor(name) {{
        super();
        this.name = name;
        this.data = {{}};
    }}
    
    async process(items) {{
        const results = {{}};
        for (const item of items) {{
            results[item] = await this.analyze(item);
        }}
        return results;
    }}
    
    analyze(item) {{
        return new Promise(resolve => {{
            setTimeout(() => resolve(item.length * {index}), 10);
        }});
    }}
}}

module.exports = Component{index};
''',
            'java': '''
package com.example.module{index};

import java.util.*;
import java.util.stream.*;

public class Component{index} {{
    private String name;
    private Map<String, Object> data;
    
    public Component{index}(String name) {{
        this.name = name;
        this.data = new HashMap<>();
    }}
    
    public Map<String, Integer> process(List<String> items) {{
        return items.stream()
            .collect(Collectors.toMap(
                item -> item,
                item -> analyze(item)
            ));
    }}
    
    private int analyze(String item) {{
        return item.length() * {index};
    }}
}}
''',
            'markdown': '''
# Component {index} Documentation

## Overview
This component provides functionality for module {index}.

## Installation
```bash
pip install component-{index}
```

## Usage
```python
from component{index} import Component{index}

component = Component{index}("example")
results = component.process(["item1", "item2"])
```

## API Reference

### Class: Component{index}

#### Methods

- `__init__(name: str)`: Initialize the component
- `process(items: List[str]) -> Dict[str, Any]`: Process items
- `_analyze(item: str) -> int`: Internal analysis method

## Examples

See the `examples/` directory for more usage examples.
''',
            'plaintext': f'''
Technical Specification Document
Component {index}

1. INTRODUCTION
This document describes the technical specifications for Component {index}.

2. REQUIREMENTS
- Python 3.8 or higher
- Memory: 512MB minimum
- Storage: 100MB available space

3. FUNCTIONALITY
The component processes input items and returns analyzed results.
Each item is analyzed based on its length multiplied by {index}.

4. PERFORMANCE
- Processing speed: 1000 items/second
- Memory usage: O(n) where n is number of items
- Latency: < 10ms per item

5. ERROR HANDLING
All errors are logged and gracefully handled.
Invalid inputs return empty results.
'''
        }
        
        return templates.get(language, templates['plaintext']).format(index=index)
    
    def benchmark_single_threaded(self, num_files: int) -> Dict[str, Any]:
        """Benchmark single-threaded indexing."""
        print("\nRunning single-threaded indexing benchmark...")
        
        files_indexed = 0
        start_time = time.time()
        
        # Index all files
        for file_path in Path(self.temp_dir).rglob("*"):
            if file_path.is_file():
                # Determine language
                ext = file_path.suffix.lower()
                language = {
                    '.py': 'python',
                    '.js': 'javascript',
                    '.java': 'java',
                    '.go': 'go',
                    '.rs': 'rust',
                    '.c': 'c',
                    '.cpp': 'cpp',
                    '.md': 'markdown',
                    '.txt': 'plaintext'
                }.get(ext, 'plaintext')
                
                try:
                    # Create plugin and index
                    plugin = PluginFactory.create_plugin(language, self.store)
                    content = file_path.read_text()
                    result = plugin.extract_symbols(content, str(file_path))
                    
                    # Store symbols
                    for symbol in result.symbols:
                        self.store.add_symbol(
                            file_path=str(file_path),
                            symbol_name=symbol.name,
                            symbol_type=symbol.symbol_type,
                            line_number=symbol.line,
                            metadata=symbol.metadata
                        )
                    
                    files_indexed += 1
                    
                    if files_indexed % 100 == 0:
                        print(f"  Indexed {files_indexed} files...")
                        
                except Exception as e:
                    print(f"  Error indexing {file_path}: {e}")
        
        end_time = time.time()
        elapsed_seconds = end_time - start_time
        
        return {
            'files_indexed': files_indexed,
            'elapsed_seconds': elapsed_seconds,
            'files_per_second': files_indexed / elapsed_seconds if elapsed_seconds > 0 else 0,
            'files_per_minute': (files_indexed / elapsed_seconds * 60) if elapsed_seconds > 0 else 0
        }
    
    def benchmark_multi_threaded(self, num_files: int, num_workers: int = 4) -> Dict[str, Any]:
        """Benchmark multi-threaded indexing."""
        print(f"\nRunning multi-threaded indexing benchmark ({num_workers} workers)...")
        
        # Get all files
        all_files = list(Path(self.temp_dir).rglob("*"))
        all_files = [f for f in all_files if f.is_file()]
        
        # Split files among workers
        chunk_size = len(all_files) // num_workers
        file_chunks = [all_files[i:i + chunk_size] for i in range(0, len(all_files), chunk_size)]
        
        files_indexed = 0
        start_time = time.time()
        
        with mp.Pool(num_workers) as pool:
            results = pool.map(self._index_file_chunk, file_chunks)
            files_indexed = sum(results)
        
        end_time = time.time()
        elapsed_seconds = end_time - start_time
        
        return {
            'files_indexed': files_indexed,
            'elapsed_seconds': elapsed_seconds,
            'files_per_second': files_indexed / elapsed_seconds if elapsed_seconds > 0 else 0,
            'files_per_minute': (files_indexed / elapsed_seconds * 60) if elapsed_seconds > 0 else 0,
            'num_workers': num_workers
        }
    
    def _index_file_chunk(self, files: List[Path]) -> int:
        """Index a chunk of files (for multiprocessing)."""
        # Create new store for this process
        store = SQLiteStore(self.db_path)
        indexed = 0
        
        for file_path in files:
            ext = file_path.suffix.lower()
            language = {
                '.py': 'python',
                '.js': 'javascript',
                '.java': 'java',
                '.go': 'go',
                '.rs': 'rust',
                '.c': 'c',
                '.cpp': 'cpp',
                '.md': 'markdown',
                '.txt': 'plaintext'
            }.get(ext, 'plaintext')
            
            try:
                plugin = PluginFactory.create_plugin(language, store)
                content = file_path.read_text()
                result = plugin.extract_symbols(content, str(file_path))
                
                for symbol in result.symbols:
                    store.add_symbol(
                        file_path=str(file_path),
                        symbol_name=symbol.name,
                        symbol_type=symbol.symbol_type,
                        line_number=symbol.line,
                        metadata=symbol.metadata
                    )
                
                indexed += 1
            except Exception:
                pass
        
        store.close()
        return indexed
    
    def benchmark_language_specific(self) -> Dict[str, Any]:
        """Benchmark indexing speed per language."""
        print("\nBenchmarking language-specific indexing speeds...")
        
        results = {}
        languages = ['python', 'javascript', 'java', 'markdown', 'plaintext']
        
        for lang in languages:
            # Generate 100 files of this language
            temp_lang_dir = tempfile.mkdtemp(prefix=f"index_{lang}_")
            
            for i in range(100):
                content = self._generate_code_content(lang, i)
                ext = {
                    'python': '.py',
                    'javascript': '.js',
                    'java': '.java',
                    'markdown': '.md',
                    'plaintext': '.txt'
                }.get(lang, '.txt')
                
                file_path = Path(temp_lang_dir) / f"file_{i}{ext}"
                file_path.write_text(content)
            
            # Benchmark this language
            start_time = time.time()
            plugin = PluginFactory.create_plugin(lang, self.store)
            
            for file_path in Path(temp_lang_dir).glob(f"*{ext}"):
                content = file_path.read_text()
                result = plugin.extract_symbols(content, str(file_path))
            
            elapsed = time.time() - start_time
            
            results[lang] = {
                'files': 100,
                'elapsed_seconds': elapsed,
                'files_per_second': 100 / elapsed,
                'avg_ms_per_file': (elapsed / 100) * 1000
            }
            
            # Cleanup
            shutil.rmtree(temp_lang_dir)
        
        return results
    
    def cleanup(self):
        """Clean up test environment."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if self.store:
            self.store.close()
        if self.db_path and os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def save_results(self, results: dict, filename: str = "indexing_speed_benchmark_results.json"):
        """Save benchmark results."""
        output_path = f"/app/benchmarks/{filename}"
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {output_path}")
    
    def print_summary(self, results: dict):
        """Print benchmark summary."""
        print("\n" + "="*60)
        print("INDEXING SPEED BENCHMARK RESULTS")
        print("="*60)
        
        single = results['single_threaded']
        print(f"\nSingle-threaded Performance:")
        print(f"  Files indexed: {single['files_indexed']}")
        print(f"  Time: {single['elapsed_seconds']:.2f}s")
        print(f"  Speed: {single['files_per_minute']:.0f} files/minute")
        
        target = 10000  # 10K files/minute
        meets_requirement = single['files_per_minute'] >= target
        print(f"  Target: {target} files/minute")
        print(f"  Status: {'✅ PASS' if meets_requirement else '❌ FAIL'}")
        
        if 'multi_threaded' in results:
            for config in results['multi_threaded']:
                print(f"\nMulti-threaded ({config['num_workers']} workers):")
                print(f"  Files indexed: {config['files_indexed']}")
                print(f"  Time: {config['elapsed_seconds']:.2f}s")
                print(f"  Speed: {config['files_per_minute']:.0f} files/minute")
                print(f"  Speedup: {config['files_per_minute'] / single['files_per_minute']:.2f}x")


def main():
    """Run indexing speed benchmark."""
    benchmark = IndexingSpeedBenchmark()
    
    try:
        benchmark.setup()
        
        # Generate test files
        language_distribution = {
            'python': 0.25,
            'javascript': 0.25,
            'java': 0.15,
            'markdown': 0.15,
            'plaintext': 0.10,
            'c': 0.05,
            'cpp': 0.05
        }
        
        num_files = 1000  # Start with 1K files
        benchmark.generate_test_files(num_files, language_distribution)
        
        # Run benchmarks
        single_results = benchmark.benchmark_single_threaded(num_files)
        
        # Multi-threaded benchmarks
        multi_results = []
        for workers in [2, 4, 8]:
            result = benchmark.benchmark_multi_threaded(num_files, workers)
            multi_results.append(result)
        
        # Language-specific benchmarks
        lang_results = benchmark.benchmark_language_specific()
        
        # Combine results
        all_results = {
            'single_threaded': single_results,
            'multi_threaded': multi_results,
            'language_specific': lang_results,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'test_configuration': {
                'total_files': num_files,
                'language_distribution': language_distribution
            }
        }
        
        # Save and display
        benchmark.save_results(all_results)
        benchmark.print_summary(all_results)
        
        # Print language-specific results
        print("\n\nLanguage-Specific Indexing Speeds:")
        for lang, stats in lang_results.items():
            print(f"  {lang}: {stats['files_per_second']:.1f} files/sec, "
                  f"{stats['avg_ms_per_file']:.1f}ms/file")
        
    finally:
        benchmark.cleanup()


if __name__ == "__main__":
    main()