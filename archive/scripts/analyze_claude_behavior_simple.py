#!/usr/bin/env python3
"""
Analyze Claude Code behavior from transcripts - simplified version.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
from datetime import datetime


class ClaudeTranscriptAnalyzer:
    """Analyze Claude Code transcripts for MCP vs direct tool usage."""
    
    def __init__(self):
        self.mcp_tools = {
            'mcp__code-index-mcp__symbol_lookup',
            'mcp__code-index-mcp__search_code', 
            'mcp__code-index-mcp__get_status',
            'mcp__code-index-mcp__list_plugins',
            'mcp__code-index-mcp__reindex'
        }
        self.direct_search_tools = {'Grep', 'Glob', 'LS'}
        self.direct_read_tools = {'Read'}
        self.edit_tools = {'Edit', 'MultiEdit', 'Write'}
        
        # Track statistics
        self.stats = {
            'total_tool_uses': 0,
            'mcp_uses': 0,
            'direct_search_uses': 0,
            'read_uses': 0,
            'edit_uses': 0,
            'tool_sequences': [],
            'read_patterns': [],
            'edit_patterns': [],
            'mcp_queries': [],
            'grep_patterns': []
        }
    
    def analyze_transcript(self, transcript_path: Path) -> Dict[str, Any]:
        """Analyze a single transcript file."""
        print(f"\nAnalyzing {transcript_path.name}...")
        
        with open(transcript_path, 'r') as f:
            for line_num, line in enumerate(f):
                try:
                    entry = json.loads(line.strip())
                    
                    # Look for assistant messages with tool uses
                    if entry.get('type') == 'assistant' and 'message' in entry:
                        self._process_message(entry['message'])
                        
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"  Error on line {line_num}: {e}")
        
        return self.get_summary()
    
    def _process_message(self, message: Dict):
        """Process an assistant message for tool uses."""
        content = message.get('content', [])
        
        if isinstance(content, list):
            current_sequence = []
            
            for item in content:
                if item.get('type') == 'tool_use':
                    tool_name = item.get('name', '')
                    tool_input = item.get('input', {})
                    
                    self.stats['total_tool_uses'] += 1
                    current_sequence.append(tool_name)
                    
                    # Categorize tool use
                    if tool_name in self.mcp_tools:
                        self.stats['mcp_uses'] += 1
                        self._analyze_mcp_use(tool_name, tool_input)
                    elif tool_name in self.direct_search_tools:
                        self.stats['direct_search_uses'] += 1
                        self._analyze_search_use(tool_name, tool_input)
                    elif tool_name in self.direct_read_tools:
                        self.stats['read_uses'] += 1
                        self._analyze_read_use(tool_input)
                    elif tool_name in self.edit_tools:
                        self.stats['edit_uses'] += 1
                        self._analyze_edit_use(tool_name, tool_input)
            
            if current_sequence:
                self.stats['tool_sequences'].append(current_sequence)
    
    def _analyze_mcp_use(self, tool_name: str, tool_input: Dict):
        """Analyze MCP tool usage."""
        query_info = {
            'tool': tool_name,
            'query': tool_input.get('query') or tool_input.get('symbol', ''),
            'semantic': tool_input.get('semantic', False),
            'limit': tool_input.get('limit', 20)
        }
        self.stats['mcp_queries'].append(query_info)
    
    def _analyze_search_use(self, tool_name: str, tool_input: Dict):
        """Analyze direct search tool usage."""
        if tool_name == 'Grep':
            pattern_info = {
                'pattern': tool_input.get('pattern', ''),
                'include': tool_input.get('include', ''),
                'path': tool_input.get('path', '')
            }
            self.stats['grep_patterns'].append(pattern_info)
    
    def _analyze_read_use(self, tool_input: Dict):
        """Analyze Read tool usage."""
        read_info = {
            'has_limit': 'limit' in tool_input,
            'limit': tool_input.get('limit', 'full'),
            'has_offset': 'offset' in tool_input,
            'offset': tool_input.get('offset', 0)
        }
        self.stats['read_patterns'].append(read_info)
    
    def _analyze_edit_use(self, tool_name: str, tool_input: Dict):
        """Analyze edit tool usage."""
        if tool_name == 'Edit':
            edit_type = 'partial' if 'old_string' in tool_input else 'unknown'
        elif tool_name == 'Write':
            edit_type = 'full_rewrite'
        else:
            edit_type = 'multi_edit'
        
        self.stats['edit_patterns'].append(edit_type)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get analysis summary."""
        total = self.stats['total_tool_uses']
        if total == 0:
            return self.stats
        
        # Calculate read patterns
        read_with_limit = sum(1 for r in self.stats['read_patterns'] if r['has_limit'])
        read_full = len(self.stats['read_patterns']) - read_with_limit
        
        # Calculate edit patterns
        edit_counts = defaultdict(int)
        for pattern in self.stats['edit_patterns']:
            edit_counts[pattern] += 1
        
        return {
            'total_tool_uses': total,
            'mcp_percentage': (self.stats['mcp_uses'] / total * 100) if total > 0 else 0,
            'direct_search_percentage': (self.stats['direct_search_uses'] / total * 100) if total > 0 else 0,
            'read_percentage': (self.stats['read_uses'] / total * 100) if total > 0 else 0,
            'read_with_limit_percentage': (read_with_limit / len(self.stats['read_patterns']) * 100) if self.stats['read_patterns'] else 0,
            'read_full_file_percentage': (read_full / len(self.stats['read_patterns']) * 100) if self.stats['read_patterns'] else 0,
            'edit_patterns': dict(edit_counts),
            'unique_mcp_queries': len(set(q['query'] for q in self.stats['mcp_queries'])),
            'unique_grep_patterns': len(set(g['pattern'] for g in self.stats['grep_patterns'])),
            'common_sequences': self._find_common_sequences()
        }
    
    def _find_common_sequences(self) -> List[List[str]]:
        """Find common tool usage sequences."""
        sequence_counts = defaultdict(int)
        
        for seq in self.stats['tool_sequences']:
            # Look at sequences of 2-3 tools
            for i in range(len(seq) - 1):
                pair = tuple(seq[i:i+2])
                sequence_counts[pair] += 1
                
                if i < len(seq) - 2:
                    triple = tuple(seq[i:i+3])
                    sequence_counts[triple] += 1
        
        # Return most common sequences
        sorted_sequences = sorted(sequence_counts.items(), key=lambda x: x[1], reverse=True)
        return [list(seq) for seq, count in sorted_sequences[:5] if count > 1]


def main():
    """Main analysis function."""
    print("Claude Code Behavior Analysis")
    print("=" * 50)
    
    # Find transcript directory
    transcript_dir = Path.home() / '.claude' / 'projects' / '-workspaces-Code-Index-MCP'
    
    if not transcript_dir.exists():
        print(f"Transcript directory not found: {transcript_dir}")
        return
    
    # Analyze all transcripts
    analyzer = ClaudeTranscriptAnalyzer()
    transcript_files = list(transcript_dir.glob('*.jsonl'))
    
    print(f"Found {len(transcript_files)} transcript files")
    
    for transcript_file in transcript_files:
        analyzer.analyze_transcript(transcript_file)
    
    # Get and display summary
    summary = analyzer.get_summary()
    
    print("\n" + "=" * 50)
    print("ANALYSIS SUMMARY")
    print("=" * 50)
    
    print(f"\nTotal tool uses analyzed: {summary['total_tool_uses']}")
    
    print("\nTool Usage Distribution:")
    print(f"  - MCP tools: {summary['mcp_percentage']:.1f}%")
    print(f"  - Direct search (Grep/Glob/LS): {summary['direct_search_percentage']:.1f}%")
    print(f"  - Read operations: {summary['read_percentage']:.1f}%")
    
    print("\nRead Patterns:")
    print(f"  - Reads with limit parameter: {summary['read_with_limit_percentage']:.1f}%")
    print(f"  - Full file reads: {summary['read_full_file_percentage']:.1f}%")
    
    print("\nEdit Patterns:")
    for edit_type, count in summary['edit_patterns'].items():
        print(f"  - {edit_type}: {count}")
    
    print(f"\nUnique MCP queries: {summary['unique_mcp_queries']}")
    print(f"Unique grep patterns: {summary['unique_grep_patterns']}")
    
    if summary['common_sequences']:
        print("\nCommon Tool Sequences:")
        for seq in summary['common_sequences']:
            print(f"  - {' -> '.join(seq)}")
    
    # Save detailed results
    output_file = Path('/workspaces/Code-Index-MCP/claude_transcript_analysis.json')
    with open(output_file, 'w') as f:
        json.dump({
            'summary': summary,
            'raw_stats': analyzer.stats,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")


if __name__ == "__main__":
    main()