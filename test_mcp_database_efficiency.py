#!/usr/bin/env python3
"""
MCP Database Efficiency Test

Tests and demonstrates efficient database management strategies for MCP server.
"""

import sys
import os
import time
import tempfile
import sqlite3
from pathlib import Path
from typing import Dict, List, Any
from contextlib import contextmanager

sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.plugins.plugin_factory import PluginFactory


class DatabaseEfficiencyTester:
    """Test database efficiency strategies."""
    
    def __init__(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="mcp_db_test_"))
        self.results = {}
    
    @contextmanager
    def timer(self, operation: str):
        """Time an operation."""
        start = time.time()
        yield
        duration = time.time() - start
        if operation not in self.results:
            self.results[operation] = []
        self.results[operation].append(duration)
    
    def test_in_memory_database(self) -> Dict[str, Any]:
        """Test in-memory database performance."""
        print("\n1. Testing In-Memory Database")
        print("-" * 40)
        
        results = {
            "type": "in-memory",
            "operations": {}
        }
        
        # Create in-memory store
        store = SQLiteStore(":memory:")
        
        # Test write performance
        with self.timer("in_memory_write"):
            for i in range(1000):
                store.conn.execute(
                    "INSERT INTO symbols (file_path, symbol, kind, line, character) VALUES (?, ?, ?, ?, ?)",
                    (f"test{i}.py", f"func{i}", "function", i, 0)
                )
            store.conn.commit()
        
        # Test read performance
        with self.timer("in_memory_read"):
            cursor = store.conn.execute("SELECT * FROM symbols")
            rows = cursor.fetchall()
        
        # Test search performance
        with self.timer("in_memory_search"):
            cursor = store.conn.execute(
                "SELECT * FROM symbols WHERE symbol LIKE ?",
                ("%func5%",)
            )
            rows = cursor.fetchall()
        
        results["operations"] = {
            "write_1000": self.results["in_memory_write"][-1],
            "read_all": self.results["in_memory_read"][-1],
            "search": self.results["in_memory_search"][-1],
            "total_rows": len(rows)
        }
        
        print(f"✅ Write 1000 rows: {results['operations']['write_1000']:.3f}s")
        print(f"✅ Read all rows: {results['operations']['read_all']:.3f}s")
        print(f"✅ Search: {results['operations']['search']:.3f}s")
        
        return results
    
    def test_wal_mode_database(self) -> Dict[str, Any]:
        """Test WAL mode database performance."""
        print("\n2. Testing WAL Mode Database")
        print("-" * 40)
        
        results = {
            "type": "wal_mode",
            "operations": {}
        }
        
        # Create file-based store with WAL mode
        db_path = self.test_dir / "wal_test.db"
        store = SQLiteStore(str(db_path))
        
        # Enable WAL mode
        store.conn.execute("PRAGMA journal_mode=WAL")
        store.conn.execute("PRAGMA synchronous=NORMAL")
        
        # Test concurrent write performance
        with self.timer("wal_write"):
            for i in range(1000):
                store.conn.execute(
                    "INSERT INTO symbols (file_path, symbol, kind, line, character) VALUES (?, ?, ?, ?, ?)",
                    (f"test{i}.py", f"func{i}", "function", i, 0)
                )
            store.conn.commit()
        
        # Test read while writing (simulate concurrent access)
        with self.timer("wal_concurrent"):
            # Create a second connection for reading
            read_conn = sqlite3.connect(str(db_path))
            read_conn.execute("PRAGMA journal_mode=WAL")
            
            # Read while the main connection might be writing
            cursor = read_conn.execute("SELECT COUNT(*) FROM symbols")
            count = cursor.fetchone()[0]
            read_conn.close()
        
        results["operations"] = {
            "write_1000": self.results["wal_write"][-1],
            "concurrent_read": self.results["wal_concurrent"][-1],
            "row_count": count
        }
        
        print(f"✅ Write 1000 rows (WAL): {results['operations']['write_1000']:.3f}s")
        print(f"✅ Concurrent read: {results['operations']['concurrent_read']:.3f}s")
        print(f"✅ Total rows: {results['operations']['row_count']}")
        
        return results
    
    def test_batch_operations(self) -> Dict[str, Any]:
        """Test batch operation performance."""
        print("\n3. Testing Batch Operations")
        print("-" * 40)
        
        results = {
            "type": "batch_operations",
            "operations": {}
        }
        
        store = SQLiteStore(":memory:")
        
        # Test individual inserts
        with self.timer("individual_inserts"):
            for i in range(100):
                store.conn.execute(
                    "INSERT INTO symbols (file_path, symbol, kind, line, character) VALUES (?, ?, ?, ?, ?)",
                    (f"test{i}.py", f"func{i}", "function", i, 0)
                )
                store.conn.commit()  # Commit each insert
        
        # Test batch inserts
        with self.timer("batch_inserts"):
            batch_data = [
                (f"batch{i}.py", f"bfunc{i}", "function", i, 0)
                for i in range(100)
            ]
            store.conn.executemany(
                "INSERT INTO symbols (file_path, symbol, kind, line, character) VALUES (?, ?, ?, ?, ?)",
                batch_data
            )
            store.conn.commit()  # Single commit
        
        # Test transaction batching
        with self.timer("transaction_batch"):
            store.conn.execute("BEGIN TRANSACTION")
            for i in range(100):
                store.conn.execute(
                    "INSERT INTO symbols (file_path, symbol, kind, line, character) VALUES (?, ?, ?, ?, ?)",
                    (f"trans{i}.py", f"tfunc{i}", "function", i, 0)
                )
            store.conn.commit()
        
        results["operations"] = {
            "individual_100": self.results["individual_inserts"][-1],
            "batch_100": self.results["batch_inserts"][-1],
            "transaction_100": self.results["transaction_batch"][-1],
            "speedup_batch": self.results["individual_inserts"][-1] / self.results["batch_inserts"][-1],
            "speedup_transaction": self.results["individual_inserts"][-1] / self.results["transaction_batch"][-1]
        }
        
        print(f"✅ Individual inserts (100): {results['operations']['individual_100']:.3f}s")
        print(f"✅ Batch inserts (100): {results['operations']['batch_100']:.3f}s (speedup: {results['operations']['speedup_batch']:.1f}x)")
        print(f"✅ Transaction batch (100): {results['operations']['transaction_100']:.3f}s (speedup: {results['operations']['speedup_transaction']:.1f}x)")
        
        return results
    
    def test_index_optimization(self) -> Dict[str, Any]:
        """Test index optimization strategies."""
        print("\n4. Testing Index Optimization")
        print("-" * 40)
        
        results = {
            "type": "index_optimization",
            "operations": {}
        }
        
        # Create two databases - one with indexes, one without
        no_index_db = self.test_dir / "no_index.db"
        indexed_db = self.test_dir / "indexed.db"
        
        # Test without indexes
        store1 = SQLiteStore(str(no_index_db))
        
        # Insert test data
        test_data = [
            (f"file{i % 10}.py", f"func{i}", "function", i, 0)
            for i in range(10000)
        ]
        
        with self.timer("insert_no_index"):
            store1.conn.executemany(
                "INSERT INTO symbols (file_path, symbol, kind, line, character) VALUES (?, ?, ?, ?, ?)",
                test_data
            )
            store1.conn.commit()
        
        with self.timer("search_no_index"):
            cursor = store1.conn.execute(
                "SELECT * FROM symbols WHERE file_path = ? AND kind = ?",
                ("file5.py", "function")
            )
            rows1 = cursor.fetchall()
        
        # Test with indexes
        store2 = SQLiteStore(str(indexed_db))
        
        # Create indexes
        store2.conn.execute("CREATE INDEX idx_file_path ON symbols(file_path)")
        store2.conn.execute("CREATE INDEX idx_symbol ON symbols(symbol)")
        store2.conn.execute("CREATE INDEX idx_file_kind ON symbols(file_path, kind)")
        
        with self.timer("insert_indexed"):
            store2.conn.executemany(
                "INSERT INTO symbols (file_path, symbol, kind, line, character) VALUES (?, ?, ?, ?, ?)",
                test_data
            )
            store2.conn.commit()
        
        with self.timer("search_indexed"):
            cursor = store2.conn.execute(
                "SELECT * FROM symbols WHERE file_path = ? AND kind = ?",
                ("file5.py", "function")
            )
            rows2 = cursor.fetchall()
        
        results["operations"] = {
            "insert_no_index": self.results["insert_no_index"][-1],
            "insert_indexed": self.results["insert_indexed"][-1],
            "search_no_index": self.results["search_no_index"][-1],
            "search_indexed": self.results["search_indexed"][-1],
            "search_speedup": self.results["search_no_index"][-1] / self.results["search_indexed"][-1],
            "rows_found": len(rows2)
        }
        
        print(f"✅ Insert 10k rows (no index): {results['operations']['insert_no_index']:.3f}s")
        print(f"✅ Insert 10k rows (indexed): {results['operations']['insert_indexed']:.3f}s")
        print(f"✅ Search (no index): {results['operations']['search_no_index']:.3f}s")
        print(f"✅ Search (indexed): {results['operations']['search_indexed']:.3f}s (speedup: {results['operations']['search_speedup']:.1f}x)")
        print(f"✅ Rows found: {results['operations']['rows_found']}")
        
        return results
    
    def test_connection_pooling(self) -> Dict[str, Any]:
        """Test connection pooling strategies."""
        print("\n5. Testing Connection Pooling")
        print("-" * 40)
        
        results = {
            "type": "connection_pooling",
            "operations": {}
        }
        
        db_path = self.test_dir / "pool_test.db"
        
        # Test single connection reuse
        with self.timer("single_connection"):
            store = SQLiteStore(str(db_path))
            for i in range(100):
                cursor = store.conn.execute("SELECT COUNT(*) FROM symbols")
                count = cursor.fetchone()[0]
        
        # Test multiple connection creation
        with self.timer("multiple_connections"):
            for i in range(100):
                conn = sqlite3.connect(str(db_path))
                cursor = conn.execute("SELECT COUNT(*) FROM symbols")
                count = cursor.fetchone()[0]
                conn.close()
        
        results["operations"] = {
            "single_connection": self.results["single_connection"][-1],
            "multiple_connections": self.results["multiple_connections"][-1],
            "speedup": self.results["multiple_connections"][-1] / self.results["single_connection"][-1]
        }
        
        print(f"✅ Single connection (100 queries): {results['operations']['single_connection']:.3f}s")
        print(f"✅ Multiple connections (100 queries): {results['operations']['multiple_connections']:.3f}s")
        print(f"✅ Connection reuse speedup: {results['operations']['speedup']:.1f}x")
        
        return results
    
    def test_plugin_database_usage(self) -> Dict[str, Any]:
        """Test database usage by plugins."""
        print("\n6. Testing Plugin Database Usage")
        print("-" * 40)
        
        results = {
            "type": "plugin_usage",
            "languages": {}
        }
        
        # Test code for each language
        test_files = {
            "python": ("test.py", "def main():\n    pass\n"),
            "javascript": ("test.js", "function main() {}\n"),
            "java": ("Test.java", "public class Test {}\n")
        }
        
        for lang, (filename, code) in test_files.items():
            try:
                # Create plugin with dedicated database
                db_path = self.test_dir / f"{lang}_test.db"
                store = SQLiteStore(str(db_path))
                
                # Use basic plugins for speed
                if lang == "javascript":
                    from mcp_server.plugins.js_plugin import Plugin as JSPlugin
                    plugin = JSPlugin()
                elif lang == "java":
                    from mcp_server.plugins.java_plugin import JavaPlugin
                    plugin = JavaPlugin(store)
                else:  # python
                    from mcp_server.plugins.python_plugin import Plugin as PythonPlugin
                    plugin = PythonPlugin()
                
                # Time indexing
                file_path = self.test_dir / filename
                file_path.write_text(code)
                
                with self.timer(f"index_{lang}"):
                    shard = plugin.indexFile(file_path, code)
                
                # Check database size
                db_size = db_path.stat().st_size if db_path.exists() else 0
                
                results["languages"][lang] = {
                    "index_time": self.results[f"index_{lang}"][-1],
                    "symbols": len(shard.get('symbols', [])),
                    "db_size": db_size
                }
                
                print(f"✅ {lang}: {results['languages'][lang]['index_time']:.3f}s, "
                      f"{results['languages'][lang]['symbols']} symbols, "
                      f"{results['languages'][lang]['db_size'] / 1024:.1f}KB")
                
            except Exception as e:
                print(f"❌ {lang}: {str(e)}")
                results["languages"][lang] = {"error": str(e)}
        
        return results
    
    def generate_recommendations(self) -> List[str]:
        """Generate database efficiency recommendations."""
        recommendations = []
        
        # Analyze results and generate recommendations
        if "batch_operations" in self.results:
            batch_speedup = self.results["individual_inserts"][-1] / self.results["batch_inserts"][-1]
            if batch_speedup > 5:
                recommendations.append(
                    f"🚀 Use batch operations: {batch_speedup:.1f}x faster than individual inserts"
                )
        
        if "search_indexed" in self.results and "search_no_index" in self.results:
            search_speedup = self.results["search_no_index"][-1] / self.results["search_indexed"][-1]
            if search_speedup > 2:
                recommendations.append(
                    f"🔍 Add database indexes: {search_speedup:.1f}x faster search performance"
                )
        
        if "multiple_connections" in self.results:
            conn_overhead = self.results["multiple_connections"][-1] / self.results["single_connection"][-1]
            if conn_overhead > 2:
                recommendations.append(
                    f"♻️ Reuse database connections: {conn_overhead:.1f}x overhead from creating new connections"
                )
        
        recommendations.extend([
            "💾 Use in-memory databases for testing and temporary data",
            "📝 Enable WAL mode for better concurrent access",
            "🔄 Use transactions for multiple related operations",
            "📊 Monitor database size and implement cleanup strategies",
            "⚡ Consider connection pooling for high-concurrency scenarios"
        ])
        
        return recommendations
    
    def run_all_tests(self):
        """Run all efficiency tests."""
        print("🔬 MCP Database Efficiency Testing")
        print("=" * 50)
        
        all_results = {}
        
        # Run each test
        tests = [
            self.test_in_memory_database,
            self.test_wal_mode_database,
            self.test_batch_operations,
            self.test_index_optimization,
            self.test_connection_pooling,
            self.test_plugin_database_usage
        ]
        
        for test_func in tests:
            try:
                result = test_func()
                all_results[result["type"]] = result
            except Exception as e:
                print(f"❌ Test failed: {e}")
        
        # Generate recommendations
        print("\n📋 Efficiency Recommendations")
        print("=" * 50)
        
        recommendations = self.generate_recommendations()
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
        
        # Cleanup
        import shutil
        shutil.rmtree(self.test_dir)
        
        return all_results


def main():
    """Main entry point."""
    tester = DatabaseEfficiencyTester()
    results = tester.run_all_tests()
    
    print("\n✅ Database efficiency testing completed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())