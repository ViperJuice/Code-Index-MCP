#!/usr/bin/env python3
"""
Simple analysis of Claude Code transcripts to extract real tool usage data.
"""

import json
import re
from pathlib import Path
from collections import defaultdict


def analyze_transcript(file_path):
    """Analyze a single transcript for tool usage."""
    tool_sequences = []
    current_sequence = []
    read_details = []
    grep_details = []
    mcp_details = []
    
    with open(file_path, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                
                # Look for tool uses in assistant messages
                if entry.get('type') == 'assistant' and entry.get('message'):
                    content_items = entry['message'].get('content', [])
                    
                    for item in content_items:
                        if item.get('type') == 'tool_use':
                            tool_name = item.get('name', '')
                            tool_input = item.get('input', {})
                            
                            tool_info = {
                                'name': tool_name,
                                'params': tool_input
                            }
                            current_sequence.append(tool_info)
                            
                            # Collect specific details
                            if tool_name == 'Read':
                                read_details.append({
                                    'file': tool_input.get('file_path', ''),
                                    'offset': tool_input.get('offset', 0),
                                    'limit': tool_input.get('limit', 'full')
                                })
                            elif tool_name == 'Grep':
                                grep_details.append({
                                    'pattern': tool_input.get('pattern', ''),
                                    'path': tool_input.get('path', '.')
                                })
                            elif tool_name.startswith('mcp__'):
                                mcp_details.append(tool_info)
                
                # Look for tool results to estimate tokens
                if entry.get('type') == 'user' and entry.get('toolUseResult'):
                    result = entry.get('toolUseResult', {})
                    
                    # Track result sizes
                    if isinstance(result, dict):
                        if result.get('type') == 'text':
                            if result.get('file'):
                                # Read result
                                lines = result['file'].get('numLines', 0)
                                if current_sequence and current_sequence[-1]['name'] == 'Read':
                                    current_sequence[-1]['result_lines'] = lines
                            elif result.get('filenames'):
                                # Grep result
                                num_files = result.get('numFiles', 0)
                                if current_sequence and current_sequence[-1]['name'] == 'Grep':
                                    current_sequence[-1]['result_files'] = num_files
                
                # New user message starts new sequence
                if entry.get('type') == 'user' and entry.get('userType') == 'external':
                    if current_sequence:
                        tool_sequences.append(current_sequence)
                        current_sequence = []
                        
            except json.JSONDecodeError:
                continue
    
    # Add final sequence
    if current_sequence:
        tool_sequences.append(current_sequence)
    
    return {
        'sequences': tool_sequences,
        'read_details': read_details,
        'grep_details': grep_details,
        'mcp_details': mcp_details
    }


def main():
    """Analyze all transcripts in the project."""
    project_dir = Path.home() / ".claude/projects/-workspaces-Code-Index-MCP"
    
    all_reads = []
    all_greps = []
    all_mcps = []
    all_patterns = []
    
    # Analyze each transcript
    for transcript_file in sorted(project_dir.glob("*.jsonl")):
        print(f"\nAnalyzing {transcript_file.name}...")
        
        result = analyze_transcript(transcript_file)
        
        all_reads.extend(result['read_details'])
        all_greps.extend(result['grep_details'])
        all_mcps.extend(result['mcp_details'])
        
        # Extract patterns
        for sequence in result['sequences']:
            if len(sequence) > 0:
                pattern = ' -> '.join([t['name'] for t in sequence])
                all_patterns.append(pattern)
    
    # Print summary
    print("\n" + "=" * 80)
    print("REAL CLAUDE CODE TOOL USAGE ANALYSIS")
    print("=" * 80)
    
    print(f"\nTotal tool calls analyzed:")
    print(f"  Read: {len(all_reads)}")
    print(f"  Grep: {len(all_greps)}")
    print(f"  MCP: {len(all_mcps)}")
    
    # Analyze Read patterns
    if all_reads:
        print(f"\nRead tool usage:")
        limits = [r['limit'] for r in all_reads if r['limit'] != 'full']
        if limits:
            avg_limit = sum(limits) / len(limits)
            print(f"  Reads with limit: {len(limits)} ({len(limits)/len(all_reads)*100:.1f}%)")
            print(f"  Average limit: {avg_limit:.0f} lines")
            print(f"  Common limits: {sorted(set(limits))[:10]}")
        full_reads = len([r for r in all_reads if r['limit'] == 'full'])
        print(f"  Full file reads: {full_reads} ({full_reads/len(all_reads)*100:.1f}%)")
    
    # Analyze Grep patterns
    if all_greps:
        print(f"\nGrep tool usage:")
        print(f"  Total grep searches: {len(all_greps)}")
        print(f"  Example patterns: {[g['pattern'] for g in all_greps[:5]]}")
    
    # Analyze tool sequences
    if all_patterns:
        print(f"\nCommon tool sequences:")
        pattern_counts = defaultdict(int)
        for p in all_patterns:
            pattern_counts[p] += 1
        
        for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {pattern}: {count}")
    
    # MCP adoption
    total_tools = len(all_reads) + len(all_greps) + len(all_mcps)
    if total_tools > 0:
        mcp_rate = len(all_mcps) / total_tools * 100
        print(f"\nMCP Adoption Rate: {mcp_rate:.2f}%")
    
    # Look for grep->read patterns
    grep_to_read = 0
    for pattern in all_patterns:
        if 'Grep -> Read' in pattern:
            grep_to_read += 1
    
    print(f"\nGrep followed by Read: {grep_to_read} occurrences")


if __name__ == "__main__":
    main()