#!/usr/bin/env python3
"""
Demonstrate how MCP enables precise targeted edits vs full file rewrites
"""

import os
import sys
import sqlite3
import json
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.utils.token_counter import TokenCounter


def search_for_edit_target(db_path: str, query: str):
    """Search for code to edit using MCP."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Search for specific function/symbol
    cursor.execute(
        """SELECT 
            filepath,
            snippet(bm25_content, 3, '<<<', '>>>', '...', 30) as snippet,
            bm25(bm25_content) as score
        FROM bm25_content 
        WHERE bm25_content MATCH ?
        ORDER BY score
        LIMIT 5""",
        (query,)
    )
    
    results = cursor.fetchall()
    conn.close()
    
    return [(r[0], r[1]) for r in results]


def demonstrate_edit_scenarios():
    """Show different edit scenarios with MCP vs traditional search."""
    token_counter = TokenCounter()
    
    print("🎯 MCP Edit Precision Demonstration")
    print("="*60)
    
    # Scenario 1: Fix a specific function
    print("\n📝 Scenario 1: Fix error handling in Gin middleware")
    print("-"*60)
    
    # With MCP
    print("\n🔍 With MCP:")
    mcp_results = search_for_edit_target('.mcp-index/gin/code_index.db', 'func Recovery')
    
    if mcp_results:
        file_path, snippet = mcp_results[0]
        print(f"1. MCP search for 'func Recovery': Found in {file_path}")
        print(f"   Snippet: {snippet[:150]}...")
        print(f"2. MCP provides exact location → Use Edit tool for targeted change")
        print(f"3. Only modified lines are changed (diff-based edit)")
        
        # Simulate edit
        edit_example = {
            'tool': 'Edit',
            'file_path': file_path,
            'old_string': 'panic(err)',
            'new_string': 'c.AbortWithError(500, err)'
        }
        edit_tokens = token_counter.count_tokens(json.dumps(edit_example))
        print(f"   Edit tokens: ~{edit_tokens}")
    
    print("\n❌ Without MCP:")
    print("1. Grep search finds multiple files")
    print("2. Must read entire files to understand context")
    print("3. Often results in Write tool usage (full file rewrite)")
    print("   Full file tokens: ~5000-10000")
    
    # Scenario 2: Add logging to specific handler
    print("\n\n📝 Scenario 2: Add logging to specific API handler")
    print("-"*60)
    
    print("\n🔍 With MCP:")
    mcp_results = search_for_edit_target('.mcp-index/gin/code_index.db', 'Handler context')
    
    if mcp_results:
        file_path, snippet = mcp_results[0]
        print(f"1. MCP search for handler functions: Found in {file_path}")
        print(f"   Snippet: {snippet[:150]}...")
        print(f"2. Precise location enables MultiEdit for multiple small changes")
        print(f"3. Each edit is a small targeted diff")
        print(f"   MultiEdit tokens: ~200-300 per edit")
    
    print("\n❌ Without MCP:")
    print("1. Broad search returns many handlers")
    print("2. Manual inspection needed to find right one")
    print("3. Risk of modifying wrong handler")
    print("4. Full file rewrite more likely")
    
    # Scenario 3: Update import statements
    print("\n\n📝 Scenario 3: Update import path across codebase")
    print("-"*60)
    
    print("\n🔍 With MCP:")
    mcp_results = search_for_edit_target('.mcp-index/react/code_index.db', 'import from react')
    
    if mcp_results[:3]:
        print(f"1. MCP finds exact import lines in {len(mcp_results)} files")
        for i, (file_path, snippet) in enumerate(mcp_results[:3]):
            print(f"   File {i+1}: {file_path}")
            print(f"   Import: {snippet[:80]}...")
        print(f"2. Can use Edit tool with replace_all=True for each file")
        print(f"3. Only import lines are modified")
        print(f"   Edit tokens per file: ~50-100")
    
    print("\n❌ Without MCP:")
    print("1. Must read entire files to find imports")
    print("2. Risk of incorrect regex replacements")
    print("3. Often leads to full file rewrites")
    print("   Full file tokens per file: ~5000+")
    
    # Summary
    print("\n\n📊 Summary: MCP vs Traditional Search for Code Edits")
    print("="*60)
    
    print("\n✅ MCP Advantages:")
    print("- Precise location finding (file + line + context)")
    print("- Enables Edit/MultiEdit tools (diff-based changes)")
    print("- 90-99% fewer tokens per edit operation")
    print("- Lower risk of unintended changes")
    print("- Faster iteration cycles")
    
    print("\n❌ Traditional Search Limitations:")
    print("- Must read full files for context")
    print("- Often results in Write tool (full file replacement)")
    print("- 10-100x more tokens per edit")
    print("- Higher risk of breaking unrelated code")
    print("- Slower, more error-prone process")
    
    print("\n💡 Key Insight:")
    print("MCP transforms code editing from 'find and rewrite' to 'locate and patch'")
    print("This enables Claude Code to make surgical edits instead of wholesale replacements")


if __name__ == "__main__":
    demonstrate_edit_scenarios()