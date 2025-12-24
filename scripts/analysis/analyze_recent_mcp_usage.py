#!/usr/bin/env python3
"""
Analyze only recent transcript entries from current session after MCP fix.
Focus on actual tool usage patterns, not fabricated data.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

def analyze_recent_transcript(transcript_path: Path, hours_back: int = 2):
    """Analyze recent entries in transcript file."""
    
    # Get cutoff time
    cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
    
    tool_usage = defaultdict(int)
    mcp_calls = []
    grep_calls = []
    read_calls = []
    tool_sequences = []
    current_sequence = []
    
    with open(transcript_path, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                
                # Skip if too old
                timestamp_str = entry.get('timestamp', '')
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        if timestamp < cutoff_time:
                            continue
                    except:
                        continue
                
                # Look for assistant messages with tool calls
                if entry.get('type') == 'assistant' and entry.get('message'):
                    message = entry['message']
                    content = message.get('content', [])
                    
                    for item in content:
                        if isinstance(item, dict) and item.get('type') == 'tool_use':
                            tool_name = item.get('name', '')
                            tool_input = item.get('input', {})
                            
                            tool_usage[tool_name] += 1
                            current_sequence.append(tool_name)
                            
                            # Track specific tools
                            if tool_name.startswith('mcp__'):
                                mcp_calls.append({
                                    'tool': tool_name,
                                    'params': tool_input,
                                    'timestamp': timestamp_str
                                })
                            elif tool_name == 'Grep':
                                grep_calls.append({
                                    'pattern': tool_input.get('pattern', ''),
                                    'path': tool_input.get('path', ''),
                                    'timestamp': timestamp_str
                                })
                            elif tool_name == 'Read':
                                read_calls.append({
                                    'file': tool_input.get('file_path', ''),
                                    'offset': tool_input.get('offset', 0),
                                    'limit': tool_input.get('limit', None),
                                    'timestamp': timestamp_str
                                })
                
                # New user message starts new sequence
                if entry.get('type') == 'user' and current_sequence:
                    if len(current_sequence) > 1:
                        tool_sequences.append(current_sequence)
                    current_sequence = []
                    
            except json.JSONDecodeError:
                continue
    
    return {
        'tool_usage': dict(tool_usage),
        'mcp_calls': mcp_calls,
        'grep_calls': grep_calls,
        'read_calls': read_calls,
        'sequences': tool_sequences
    }

def main():
    """Analyze recent transcript from current session."""
    # Current session transcript
    transcript_path = Path.home() / ".claude/projects/-workspaces-Code-Index-MCP/2ffb60c4-3fc8-41b4-b5da-5100ddb55f35.jsonl"
    
    print("Analyzing Recent MCP Usage (Last 2 Hours)")
    print("=" * 80)
    
    result = analyze_recent_transcript(transcript_path, hours_back=2)
    
    # Summary
    print(f"\nTool Usage Summary:")
    for tool, count in sorted(result['tool_usage'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {tool}: {count}")
    
    # MCP Usage
    print(f"\nMCP Tool Calls: {len(result['mcp_calls'])}")
    for mcp in result['mcp_calls'][:5]:
        print(f"  - {mcp['tool']} at {mcp['timestamp']}")
    
    # Grep vs Read patterns
    print(f"\nGrep Calls: {len(result['grep_calls'])}")
    print(f"Read Calls: {len(result['read_calls'])}")
    
    # Read with limits
    reads_with_limit = [r for r in result['read_calls'] if r['limit'] is not None]
    if reads_with_limit:
        avg_limit = sum(r['limit'] for r in reads_with_limit) / len(reads_with_limit)
        print(f"\nReads with limit: {len(reads_with_limit)} ({len(reads_with_limit)/len(result['read_calls'])*100:.1f}%)")
        print(f"Average limit: {avg_limit:.0f} lines")
    
    # Common sequences
    if result['sequences']:
        print(f"\nCommon Tool Sequences:")
        seq_counts = defaultdict(int)
        for seq in result['sequences']:
            pattern = ' -> '.join(seq)
            seq_counts[pattern] += 1
        
        for pattern, count in sorted(seq_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {pattern}: {count}")
    
    # MCP adoption rate
    total_search_tools = (result['tool_usage'].get('Grep', 0) + 
                         result['tool_usage'].get('Glob', 0) +
                         sum(1 for t in result['tool_usage'] if t.startswith('mcp__')))
    
    if total_search_tools > 0:
        mcp_rate = len(result['mcp_calls']) / total_search_tools * 100
        print(f"\nMCP Adoption Rate: {mcp_rate:.1f}%")

if __name__ == "__main__":
    main()