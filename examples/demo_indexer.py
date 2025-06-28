#!/usr/bin/env python3
"""
Demonstration script for the Index Engine implementation.

This script shows how to use the IndexEngine and QueryOptimizer
to index code files and optimize search queries.
"""

import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock

from mcp_server.indexer import (
    IndexEngine, IndexOptions, QueryOptimizer, Query, QueryType
)
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.fuzzy_indexer import FuzzyIndexer


def create_mock_plugin_manager():
    """Create a mock plugin manager for demonstration."""
    mock_plugin = Mock()
    mock_plugin.parse_file.return_value = {
        'language': 'python',
        'symbols': [
            {
                'name': 'calculate_sum',
                'kind': 'function',
                'line_start': 1,
                'line_end': 3,
                'signature': 'def calculate_sum(a, b):',
                'documentation': 'Calculate the sum of two numbers'
            },
            {
                'name': 'DataProcessor',
                'kind': 'class',
                'line_start': 5,
                'line_end': 10,
                'signature': 'class DataProcessor:',
                'documentation': 'Process data efficiently'
            }
        ],
        'references': [],
        'metadata': {'complexity': 'low'}
    }
    
    manager = Mock()
    manager.get_plugin_for_file.return_value = mock_plugin
    return manager


async def demonstrate_indexing():
    """Demonstrate the indexing capabilities."""
    print("🚀 Index Engine Demonstration")
    print("=" * 50)
    
    # Create temporary directory and files for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create sample Python files
        (temp_path / "math_utils.py").write_text("""
def calculate_sum(a, b):
    \"\"\"Calculate the sum of two numbers.\"\"\"
    return a + b

class DataProcessor:
    \"\"\"Process data efficiently.\"\"\"
    
    def process(self, data):
        return [x * 2 for x in data]
""")
        
        (temp_path / "string_utils.py").write_text("""
def reverse_string(s):
    \"\"\"Reverse a string.\"\"\"
    return s[::-1]

def capitalize_words(text):
    \"\"\"Capitalize each word in text.\"\"\"
    return ' '.join(word.capitalize() for word in text.split())
""")
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as db_file:
            db_path = db_file.name
        
        try:
            # Initialize components
            print("🔧 Initializing components...")
            storage = SQLiteStore(db_path)
            fuzzy_indexer = FuzzyIndexer(storage)
            plugin_manager = create_mock_plugin_manager()
            
            # Create index engine
            engine = IndexEngine(
                plugin_manager=plugin_manager,
                storage=storage,
                fuzzy_indexer=fuzzy_indexer,
                repository_path=str(temp_path)
            )
            
            print("✅ Components initialized successfully")
            
            # Index individual file
            print("\n📁 Indexing individual file...")
            math_file = str(temp_path / "math_utils.py")
            result = await engine.index_file(math_file)
            
            print(f"  📄 {result.file_path}")
            print(f"  ✅ Success: {result.success}")
            print(f"  🔢 Symbols: {result.symbols_count}")
            print(f"  ⏱️  Duration: {result.duration_ms:.2f}ms")
            print(f"  🐍 Language: {result.language}")
            
            # Index entire directory
            print("\n📂 Indexing entire directory...")
            batch_result = await engine.index_directory(str(temp_path))
            
            print(f"  📊 Total files: {batch_result.total_files}")
            print(f"  ✅ Successful: {batch_result.successful}")
            print(f"  ❌ Failed: {batch_result.failed}")
            print(f"  ⏱️  Total duration: {batch_result.total_duration_ms:.2f}ms")
            
            # Show progress tracking
            print("\n📈 Progress tracking...")
            progress = engine.get_progress()
            print(f"  📊 Total: {progress.total}")
            print(f"  ✅ Completed: {progress.completed}")
            print(f"  ❌ Failed: {progress.failed}")
            if progress.throughput > 0:
                print(f"  🚀 Throughput: {progress.throughput:.2f} files/sec")
            
            # Test fuzzy search
            print("\n🔍 Testing fuzzy search...")
            fuzzy_results = fuzzy_indexer.search_symbols("calc")
            print(f"  🎯 Found {len(fuzzy_results)} matches for 'calc'")
            for result in fuzzy_results[:3]:
                print(f"    • {result.get('name', 'Unknown')} in {Path(result.get('file_path', '')).name}")
            
            # Get index status
            print("\n📊 Index status...")
            status = engine.get_index_status(str(temp_path))
            print(f"  📁 Total files: {status.get('total_files', 0)}")
            print(f"  🔤 Total symbols: {status.get('total_symbols', 0)}")
            print(f"  🔗 Total references: {status.get('total_references', 0)}")
            
            # Demonstrate query optimization
            print("\n🔧 Query Optimization Demonstration")
            print("=" * 50)
            
            optimizer = QueryOptimizer(storage)
            
            # Test different query types
            queries = [
                Query(QueryType.SYMBOL_SEARCH, "calculate", {"kind": "function"}),
                Query(QueryType.FUZZY_SEARCH, "proc"),
                Query(QueryType.TEXT_SEARCH, "sum numbers"),
            ]
            
            for i, query in enumerate(queries, 1):
                print(f"\n🔍 Query {i}: {query.query_type.value}")
                print(f"  📝 Text: '{query.text}'")
                print(f"  🏷️  Filters: {query.filters}")
                
                # Optimize query
                optimized = optimizer.optimize_query(query)
                print(f"  🔧 Rewritten: '{optimized.rewritten_text}'")
                print(f"  📊 Index choice: {optimized.index_choice.index_name}")
                print(f"  💰 Estimated cost: {optimized.estimated_cost.total_cost:.2f}")
                print(f"  ⏱️  Estimated time: {optimized.estimated_cost.estimated_time_ms:.2f}ms")
                
                # Create search plan
                plan = optimizer.plan_search(query)
                print(f"  📋 Plan steps: {len(plan.steps)}")
                for step in plan.steps:
                    print(f"    • {step['type']}")
            
            # Test index suggestions
            print("\n💡 Index suggestions...")
            suggestions = optimizer.suggest_indexes(queries)
            print(f"  📊 Generated {len(suggestions)} suggestions:")
            for suggestion in suggestions[:3]:
                print(f"    • {suggestion.index_type.value} on {suggestion.columns}")
                print(f"      Benefit: {suggestion.estimated_benefit:.1f}, Cost: {suggestion.creation_cost:.1f}")
                print(f"      Reason: {suggestion.reason}")
            
            # Test task scheduling
            print("\n⏰ Task Scheduling Demonstration")
            print("=" * 50)
            
            # Schedule reindex tasks
            task_id1 = await engine.schedule_reindex(math_file, priority=5)
            task_id2 = await engine.schedule_reindex(str(temp_path / "string_utils.py"), priority=3)
            
            print(f"  📋 Scheduled task 1: {task_id1}")
            print(f"  📋 Scheduled task 2: {task_id2}")
            
            # Show pending tasks
            pending = engine.get_pending_tasks()
            print(f"  ⏳ Pending tasks: {len(pending)}")
            for task in pending:
                print(f"    • {task.id[:8]}... - {Path(task.path).name} (priority: {task.priority})")
            
            # Cancel a task
            cancelled = engine.cancel_task(task_id2)
            print(f"  ❌ Cancelled task 2: {cancelled}")
            
            # Show updated pending tasks
            pending = engine.get_pending_tasks()
            print(f"  ⏳ Remaining tasks: {len(pending)}")
            
            print("\n🎉 Demonstration completed successfully!")
            
        finally:
            # Cleanup
            try:
                os.unlink(db_path)
            except OSError:
                pass


if __name__ == "__main__":
    asyncio.run(demonstrate_indexing())