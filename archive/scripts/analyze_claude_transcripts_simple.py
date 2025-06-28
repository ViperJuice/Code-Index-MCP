#!/usr/bin/env python3
"""
Analyze Claude Code transcripts to extract real MCP vs non-MCP performance data
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
import re


def analyze_transcript(file_path: Path) -> Dict[str, Any]:
    """Analyze a single Claude Code transcript."""
    mcp_searches = []
    traditional_searches = []
    edits = []
    
    with open(file_path, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                
                # Check if this is an assistant message with tool uses
                if entry.get('type') == 'assistant' and 'message' in entry:
                    message = entry['message']
                    
                    # Look for tool uses in content
                    if isinstance(message.get('content'), list):
                        for content_item in message['content']:
                            if content_item.get('type') == 'tool_use':
                                tool = content_item.get('name', '')
                                tool_input = content_item.get('input', {})
                                
                                # MCP search tools
                                if tool.startswith('mcp__') and ('search' in tool or 'lookup' in tool):
                                    mcp_searches.append({
                                        'tool': tool,
                                        'query': tool_input.get('query') or tool_input.get('symbol', ''),
                                        'timestamp': entry.get('timestamp', '')
                                    })
                                
                                # Traditional search tools
                                elif tool in ['Grep', 'Glob', 'Read', 'LS']:
                                    traditional_searches.append({
                                        'tool': tool,
                                        'input': tool_input,
                                        'timestamp': entry.get('timestamp', '')
                                    })
                                
                                # Edit tools
                                elif tool in ['Edit', 'MultiEdit', 'Write']:
                                    edits.append({
                                        'tool': tool,
                                        'file': tool_input.get('file_path', ''),
                                        'timestamp': entry.get('timestamp', '')
                                    })
                        
            except json.JSONDecodeError:
                continue
    
    return {
        'file': file_path.name,
        'mcp_searches': mcp_searches,
        'traditional_searches': traditional_searches,
        'edits': edits,
        'mcp_search_count': len(mcp_searches),
        'traditional_search_count': len(traditional_searches),
        'edit_count': len(edits)
    }


def main():
    """Analyze all Claude Code transcripts."""
    transcript_dir = Path.home() / '.claude' / 'projects' / '-workspaces-Code-Index-MCP'
    
    if not transcript_dir.exists():
        print(f"❌ Transcript directory not found: {transcript_dir}")
        return
    
    transcripts = list(transcript_dir.glob('*.jsonl'))
    print(f"📄 Found {len(transcripts)} Claude Code transcripts")
    
    all_results = []
    
    for transcript in transcripts:
        print(f"\n📋 Analyzing {transcript.name}...")
        result = analyze_transcript(transcript)
        all_results.append(result)
        
        print(f"   MCP searches: {result['mcp_search_count']}")
        print(f"   Traditional searches: {result['traditional_search_count']}")
        print(f"   Edits: {result['edit_count']}")
        
        # Show examples
        if result['mcp_searches']:
            print(f"   Example MCP search: {result['mcp_searches'][0]['tool']} - '{result['mcp_searches'][0]['query']}'")
        if result['traditional_searches']:
            print(f"   Example traditional: {result['traditional_searches'][0]['tool']}")
    
    # Aggregate statistics
    total_mcp = sum(r['mcp_search_count'] for r in all_results)
    total_traditional = sum(r['traditional_search_count'] for r in all_results)
    total_edits = sum(r['edit_count'] for r in all_results)
    
    print("\n" + "="*60)
    print("AGGREGATE STATISTICS")
    print("="*60)
    print(f"Total transcripts analyzed: {len(all_results)}")
    print(f"Total MCP searches: {total_mcp}")
    print(f"Total traditional searches: {total_traditional}")
    print(f"Total edits: {total_edits}")
    
    if total_mcp + total_traditional > 0:
        mcp_ratio = total_mcp / (total_mcp + total_traditional) * 100
        print(f"\nMCP search usage: {mcp_ratio:.1f}%")
        print(f"Traditional search usage: {100 - mcp_ratio:.1f}%")
    
    # Analyze edit patterns
    edit_tools = {}
    for result in all_results:
        for edit in result['edits']:
            tool = edit['tool']
            edit_tools[tool] = edit_tools.get(tool, 0) + 1
    
    if edit_tools:
        print("\nEdit tool usage:")
        for tool, count in sorted(edit_tools.items(), key=lambda x: x[1], reverse=True):
            percentage = count / total_edits * 100
            print(f"  {tool}: {count} ({percentage:.1f}%)")
            if tool in ['Edit', 'MultiEdit']:
                print(f"    → Targeted edits (diffs)")
            elif tool == 'Write':
                print(f"    → Full file rewrites")
    
    # Save detailed results
    output = {
        'summary': {
            'transcripts_analyzed': len(all_results),
            'total_mcp_searches': total_mcp,
            'total_traditional_searches': total_traditional,
            'total_edits': total_edits,
            'mcp_search_ratio': total_mcp / max(1, total_mcp + total_traditional),
            'edit_tool_distribution': edit_tools
        },
        'details': all_results
    }
    
    with open('claude_transcript_analysis.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Detailed results saved to claude_transcript_analysis.json")


if __name__ == "__main__":
    main()