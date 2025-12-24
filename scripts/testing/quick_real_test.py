#!/usr/bin/env python3
"""
Quick Real MCP Test - Get authentic performance data without timeouts
"""

import json
import time
import sqlite3
import subprocess
import sys
from pathlib import Path
from mcp_server.core.path_utils import PathUtils

def test_real_mcp_performance():
    """Test real MCP server performance with actual queries"""
    db_path = "PathUtils.get_workspace_root()/.indexes/f7b49f5d0ae0/current.db"
    
    print("=== REAL MCP vs NATIVE PERFORMANCE TEST ===\n")
    
    # Test 1: Real Database Query Performance
    print("1. Testing Real Database Performance:")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    queries = [
        ("Symbol lookup", "SELECT * FROM symbols WHERE name LIKE '%Dispatcher%' LIMIT 10"),
        ("FTS code search", "SELECT * FROM fts_code WHERE content MATCH 'class' LIMIT 10"), 
        ("BM25 content search", "SELECT * FROM bm25_content WHERE content MATCH 'error' LIMIT 10")
    ]
    
    db_results = {}
    for name, query in queries:
        start_time = time.time()
        try:
            cursor.execute(query)
            results = cursor.fetchall()
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            db_results[name] = {
                "response_time_ms": response_time,
                "results_count": len(results),
                "success": True
            }
            print(f"  {name}: {response_time:.1f}ms, {len(results)} results")
        except Exception as e:
            db_results[name] = {
                "response_time_ms": 0,
                "results_count": 0,
                "success": False,
                "error": str(e)
            }
            print(f"  {name}: FAILED - {e}")
    
    conn.close()
    
    # Test 2: Real Native Tool Performance  
    print("\n2. Testing Real Native Tool Performance:")
    
    native_tests = [
        ("ripgrep class search", ["rg", "-c", "class", "PathUtils.get_workspace_root()/mcp_server/"]),
        ("find Python files", ["find", "PathUtils.get_workspace_root()/mcp_server/", "-name", "*.py"])
    ]
    
    native_results = {}
    for name, cmd in native_tests:
        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            output_lines = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            native_results[name] = {
                "response_time_ms": response_time,
                "results_count": output_lines,
                "success": result.returncode == 0
            }
            print(f"  {name}: {response_time:.1f}ms, {output_lines} results")
        except subprocess.TimeoutExpired:
            native_results[name] = {
                "response_time_ms": 10000,
                "results_count": 0,
                "success": False,
                "error": "timeout"
            }
            print(f"  {name}: TIMEOUT")
        except Exception as e:
            native_results[name] = {
                "response_time_ms": 0,
                "results_count": 0,
                "success": False,
                "error": str(e)
            }
            print(f"  {name}: FAILED - {e}")
    
    # Test 3: Real MCP Tool Test (simplified)
    print("\n3. Testing Real MCP Tool Connectivity:")
    mcp_script = "PathUtils.get_workspace_root()/scripts/cli/mcp_server_cli.py"
    
    # Test if MCP server can start and respond
    start_time = time.time()
    try:
        # Quick MCP server startup test
        proc = subprocess.Popen(
            [sys.executable, mcp_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send a simple request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }
        
        stdout, stderr = proc.communicate(input=json.dumps(request) + "\n", timeout=5)
        end_time = time.time()
        
        mcp_startup_time = (end_time - start_time) * 1000
        mcp_working = "tools" in stdout.lower() or "symbol_lookup" in stdout.lower()
        
        print(f"  MCP server startup: {mcp_startup_time:.1f}ms")
        print(f"  MCP tools available: {mcp_working}")
        
    except subprocess.TimeoutExpired:
        print("  MCP server: TIMEOUT during startup")
        mcp_startup_time = 5000
        mcp_working = False
    except Exception as e:
        print(f"  MCP server: FAILED - {e}")
        mcp_startup_time = 0
        mcp_working = False
    
    # Test 4: Real Schema Analysis
    print("\n4. Real Database Schema Analysis:")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    schema_stats = {}
    for table in ["symbols", "fts_code", "bm25_content"]:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            
            # Test query performance
            if table == "symbols":
                test_query = f"SELECT * FROM {table} WHERE name LIKE '%class%' LIMIT 5"
            else:
                test_query = f"SELECT * FROM {table} WHERE content MATCH 'function' LIMIT 5"
            
            start_time = time.time()
            cursor.execute(test_query)
            cursor.fetchall()
            query_time = (time.time() - start_time) * 1000
            
            schema_stats[table] = {
                "record_count": count,
                "query_time_ms": query_time
            }
            print(f"  {table}: {count:,} records, {query_time:.1f}ms query time")
        except Exception as e:
            schema_stats[table] = {"error": str(e)}
            print(f"  {table}: ERROR - {e}")
    
    conn.close()
    
    # Generate Real Results Summary
    print("\n=== REAL PERFORMANCE SUMMARY ===")
    
    real_results = {
        "database_performance": db_results,
        "native_tool_performance": native_results,
        "mcp_connectivity": {
            "startup_time_ms": mcp_startup_time,
            "tools_available": mcp_working
        },
        "schema_analysis": schema_stats,
        "database_info": {
            "path": db_path,
            "size_mb": Path(db_path).stat().st_size / (1024 * 1024)
        }
    }
    
    # Save real results
    results_file = Path("PathUtils.get_workspace_root()/real_quick_results.json")
    with open(results_file, 'w') as f:
        json.dump(real_results, f, indent=2)
    
    print(f"Real results saved to: {results_file}")
    
    # Performance comparison
    print("\nPERFORMANCE COMPARISON (Real Data):")
    
    # Database schema comparison
    if all(table in schema_stats and "query_time_ms" in schema_stats[table] for table in ["fts_code", "bm25_content"]):
        fts_time = schema_stats["fts_code"]["query_time_ms"]
        bm25_time = schema_stats["bm25_content"]["query_time_ms"]
        if bm25_time > 0:
            improvement = ((bm25_time - fts_time) / bm25_time) * 100
            print(f"  FTS vs BM25: FTS is {improvement:.1f}% faster ({fts_time:.1f}ms vs {bm25_time:.1f}ms)")
    
    # Tool comparison
    db_avg = sum(r["response_time_ms"] for r in db_results.values() if r["success"]) / len([r for r in db_results.values() if r["success"]])
    native_avg = sum(r["response_time_ms"] for r in native_results.values() if r["success"]) / len([r for r in native_results.values() if r["success"]])
    
    if db_avg > 0 and native_avg > 0:
        ratio = native_avg / db_avg
        print(f"  Database vs Native: DB queries {ratio:.1f}x faster ({db_avg:.1f}ms vs {native_avg:.1f}ms)")
    
    return real_results

if __name__ == "__main__":
    results = test_real_mcp_performance()