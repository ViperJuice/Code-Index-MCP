#!/usr/bin/env python3
"""
Claude Code Edit Pattern Analyzer
Analyzes how Claude Code makes code changes with MCP vs non-MCP queries
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict, Counter
import asyncio
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from tqdm import tqdm

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.utils.token_counter import TokenCounter


class ClaudeCodeTranscriptAnalyzer:
    """Analyzes Claude Code transcripts for edit patterns."""
    
    def __init__(self):
        self.token_counter = TokenCounter()
        self.mcp_tools = {
            'mcp__code-index-mcp__symbol_lookup',
            'mcp__code-index-mcp__search_code',
            'mcp_symbol_lookup',
            'mcp_search_code'
        }
        self.edit_tools = {
            'Edit', 'MultiEdit', 'edit', 'multiedit'
        }
        self.write_tools = {
            'Write', 'write'
        }
        self.search_tools = {
            'Grep', 'grep', 'Find', 'find', 'Glob', 'glob'
        }
        self.read_tools = {
            'Read', 'read'
        }
        
    def parse_jsonl_chunk(self, chunk: str) -> List[Dict[str, Any]]:
        """Parse a chunk of JSONL data."""
        events = []
        for line in chunk.strip().split('\n'):
            if line.strip():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return events
    
    def extract_tool_sequence(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract tool usage sequence from events."""
        tool_sequence = []
        
        for event in events:
            # Check for tool use in message
            if 'message' in event and event.get('message'):
                message = event['message']
                
                # Extract tool calls from message
                if isinstance(message, dict):
                    tool_name = message.get('tool', message.get('name'))
                    if tool_name:
                        tool_sequence.append({
                            'tool': tool_name,
                            'timestamp': event.get('timestamp'),
                            'params': message.get('params', {}),
                            'uuid': event.get('uuid')
                        })
                elif isinstance(message, str):
                    # Try to extract tool from string message
                    tool_patterns = [
                        r'Tool: (\w+)',
                        r'<tool>(\w+)</tool>',
                        r'mcp__[\w-]+__(\w+)',
                        r'Running (\w+) tool'
                    ]
                    for pattern in tool_patterns:
                        match = re.search(pattern, message)
                        if match:
                            tool_sequence.append({
                                'tool': match.group(1),
                                'timestamp': event.get('timestamp'),
                                'raw_message': message[:200],
                                'uuid': event.get('uuid')
                            })
                            break
            
            # Check for tool results
            if 'toolUseResult' in event and event.get('toolUseResult'):
                result = event['toolUseResult']
                if isinstance(result, dict):
                    tool_name = result.get('tool', result.get('name'))
                    if tool_name:
                        tool_sequence.append({
                            'tool': tool_name,
                            'timestamp': event.get('timestamp'),
                            'type': 'result',
                            'success': result.get('success', True),
                            'uuid': event.get('uuid')
                        })
        
        return tool_sequence
    
    def identify_edit_patterns(self, tool_sequence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify edit patterns from tool sequences."""
        patterns = []
        
        for i in range(len(tool_sequence)):
            tool = tool_sequence[i]
            tool_name = tool['tool']
            
            # Check if this is an edit/write tool
            if tool_name in self.edit_tools or tool_name in self.write_tools:
                # Look back to find what preceded this edit
                search_context = {
                    'edit_tool': tool_name,
                    'edit_type': 'diff' if tool_name in self.edit_tools else 'full_file',
                    'timestamp': tool['timestamp'],
                    'preceding_tools': []
                }
                
                # Look at previous 5 tools
                for j in range(max(0, i-5), i):
                    prev_tool = tool_sequence[j]
                    prev_name = prev_tool['tool']
                    
                    if prev_name in self.mcp_tools:
                        search_context['search_type'] = 'mcp'
                        search_context['mcp_tool'] = prev_name
                    elif prev_name in self.search_tools:
                        search_context['search_type'] = 'traditional'
                        search_context['search_tool'] = prev_name
                    elif prev_name in self.read_tools:
                        search_context['read_count'] = search_context.get('read_count', 0) + 1
                    
                    search_context['preceding_tools'].append(prev_name)
                
                # Determine pattern type
                if search_context.get('search_type') == 'mcp':
                    if tool_name in self.edit_tools:
                        search_context['pattern'] = 'mcp_targeted_edit'
                    else:
                        search_context['pattern'] = 'mcp_full_write'
                elif search_context.get('search_type') == 'traditional':
                    if tool_name in self.edit_tools:
                        search_context['pattern'] = 'traditional_targeted_edit'
                    else:
                        search_context['pattern'] = 'traditional_full_write'
                else:
                    search_context['pattern'] = 'direct_edit'
                
                patterns.append(search_context)
        
        return patterns
    
    def calculate_edit_metrics(self, patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate metrics from edit patterns."""
        metrics = {
            'total_edits': len(patterns),
            'edit_types': Counter(p['edit_type'] for p in patterns),
            'search_types': Counter(p.get('search_type', 'none') for p in patterns),
            'pattern_distribution': Counter(p['pattern'] for p in patterns),
            'mcp_vs_traditional': {
                'mcp_edits': sum(1 for p in patterns if p.get('search_type') == 'mcp'),
                'traditional_edits': sum(1 for p in patterns if p.get('search_type') == 'traditional'),
                'direct_edits': sum(1 for p in patterns if p.get('search_type') is None)
            },
            'efficiency_metrics': {
                'avg_tools_before_mcp_edit': 0,
                'avg_tools_before_traditional_edit': 0,
                'avg_reads_before_traditional_edit': 0
            }
        }
        
        # Calculate efficiency metrics
        mcp_tool_counts = []
        traditional_tool_counts = []
        traditional_read_counts = []
        
        for pattern in patterns:
            tool_count = len(pattern['preceding_tools'])
            if pattern.get('search_type') == 'mcp':
                mcp_tool_counts.append(tool_count)
            elif pattern.get('search_type') == 'traditional':
                traditional_tool_counts.append(tool_count)
                traditional_read_counts.append(pattern.get('read_count', 0))
        
        if mcp_tool_counts:
            metrics['efficiency_metrics']['avg_tools_before_mcp_edit'] = np.mean(mcp_tool_counts)
        if traditional_tool_counts:
            metrics['efficiency_metrics']['avg_tools_before_traditional_edit'] = np.mean(traditional_tool_counts)
        if traditional_read_counts:
            metrics['efficiency_metrics']['avg_reads_before_traditional_edit'] = np.mean(traditional_read_counts)
        
        # Calculate success rates (would need actual success data)
        metrics['edit_precision'] = {
            'mcp_diff_ratio': (
                metrics['pattern_distribution'].get('mcp_targeted_edit', 0) / 
                max(1, metrics['mcp_vs_traditional']['mcp_edits'])
            ),
            'traditional_diff_ratio': (
                metrics['pattern_distribution'].get('traditional_targeted_edit', 0) / 
                max(1, metrics['mcp_vs_traditional']['traditional_edits'])
            )
        }
        
        return metrics
    
    async def analyze_transcript_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single transcript file."""
        try:
            # Read file in chunks for large files
            events = []
            with open(file_path, 'r') as f:
                chunk_size = 1024 * 1024  # 1MB chunks
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    events.extend(self.parse_jsonl_chunk(chunk))
            
            # Extract tool sequences
            tool_sequence = self.extract_tool_sequence(events)
            
            # Identify edit patterns
            patterns = self.identify_edit_patterns(tool_sequence)
            
            # Calculate metrics
            metrics = self.calculate_edit_metrics(patterns)
            
            return {
                'file': file_path.name,
                'total_events': len(events),
                'tool_sequence_length': len(tool_sequence),
                'edit_patterns': patterns[:10],  # Sample patterns
                'metrics': metrics,
                'success': True
            }
            
        except Exception as e:
            return {
                'file': file_path.name,
                'success': False,
                'error': str(e)
            }
    
    async def analyze_all_transcripts(self, transcript_dir: Path) -> Dict[str, Any]:
        """Analyze all transcript files in parallel."""
        transcript_files = list(transcript_dir.glob("*.jsonl"))
        
        if not transcript_files:
            return {
                'error': 'No transcript files found',
                'directory': str(transcript_dir)
            }
        
        print(f"Found {len(transcript_files)} transcript files to analyze")
        
        # Process files in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            loop = asyncio.get_event_loop()
            tasks = []
            
            for file_path in transcript_files:
                task = loop.run_in_executor(
                    executor,
                    asyncio.run,
                    self.analyze_transcript_file(file_path)
                )
                tasks.append(task)
            
            # Process with progress bar
            results = []
            for task in tqdm(asyncio.as_completed(tasks), 
                           total=len(tasks), 
                           desc="Analyzing transcripts"):
                result = await task
                results.append(result)
        
        # Aggregate results
        aggregated = self.aggregate_results(results)
        aggregated['files_analyzed'] = len(results)
        aggregated['successful_analyses'] = sum(1 for r in results if r.get('success'))
        
        return aggregated
    
    def aggregate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate results from multiple transcript analyses."""
        all_patterns = []
        total_events = 0
        
        for result in results:
            if result.get('success'):
                all_patterns.extend(result.get('edit_patterns', []))
                total_events += result.get('total_events', 0)
        
        if not all_patterns:
            return {'error': 'No patterns found'}
        
        # Aggregate metrics
        aggregated_metrics = self.calculate_edit_metrics(all_patterns)
        aggregated_metrics['total_events_analyzed'] = total_events
        
        # Pattern examples
        pattern_examples = defaultdict(list)
        for pattern in all_patterns:
            pattern_type = pattern['pattern']
            if len(pattern_examples[pattern_type]) < 3:
                pattern_examples[pattern_type].append({
                    'tools': pattern['preceding_tools'][-3:],
                    'edit_type': pattern['edit_type']
                })
        
        return {
            'aggregated_metrics': aggregated_metrics,
            'pattern_examples': dict(pattern_examples),
            'insights': self.generate_insights(aggregated_metrics)
        }
    
    def generate_insights(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights from aggregated metrics."""
        insights = {
            'mcp_advantage': {},
            'edit_efficiency': {},
            'recommendations': []
        }
        
        # MCP advantage analysis
        mcp_edits = metrics['mcp_vs_traditional']['mcp_edits']
        traditional_edits = metrics['mcp_vs_traditional']['traditional_edits']
        total_edits = mcp_edits + traditional_edits
        
        if total_edits > 0:
            insights['mcp_advantage']['usage_rate'] = mcp_edits / total_edits
            insights['mcp_advantage']['diff_preference'] = metrics['edit_precision']['mcp_diff_ratio']
            insights['mcp_advantage']['efficiency_gain'] = (
                metrics['efficiency_metrics']['avg_tools_before_traditional_edit'] /
                max(1, metrics['efficiency_metrics']['avg_tools_before_mcp_edit'])
            )
        
        # Edit efficiency
        insights['edit_efficiency']['mcp_targeted_edit_rate'] = metrics['edit_precision']['mcp_diff_ratio']
        insights['edit_efficiency']['traditional_targeted_edit_rate'] = metrics['edit_precision']['traditional_diff_ratio']
        insights['edit_efficiency']['avg_reads_saved'] = (
            metrics['efficiency_metrics']['avg_reads_before_traditional_edit'] - 1
        )
        
        # Generate recommendations
        if insights['mcp_advantage'].get('usage_rate', 0) < 0.5:
            insights['recommendations'].append(
                "MCP is underutilized - consider promoting MCP-first search"
            )
        
        if metrics['edit_precision']['mcp_diff_ratio'] > 0.8:
            insights['recommendations'].append(
                "MCP enables highly targeted edits - 80%+ use Edit vs Write"
            )
        
        if metrics['efficiency_metrics']['avg_reads_before_traditional_edit'] > 3:
            insights['recommendations'].append(
                f"Traditional search requires {metrics['efficiency_metrics']['avg_reads_before_traditional_edit']:.1f} "
                "file reads on average - significant token overhead"
            )
        
        return insights


async def main():
    """Main entry point."""
    analyzer = ClaudeCodeTranscriptAnalyzer()
    
    # Claude Code transcript directory
    transcript_dir = Path.home() / ".claude" / "projects" / "-workspaces-Code-Index-MCP"
    
    if not transcript_dir.exists():
        print(f"❌ Transcript directory not found: {transcript_dir}")
        return
    
    print("🔍 Analyzing Claude Code Edit Patterns...")
    
    start_time = time.time()
    results = await analyzer.analyze_all_transcripts(transcript_dir)
    execution_time = time.time() - start_time
    
    # Save results
    output = {
        'timestamp': datetime.now().isoformat(),
        'execution_time': execution_time,
        'results': results
    }
    
    output_file = Path("claude_code_edit_analysis.json")
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    # Print summary
    print(f"\n📊 Analysis Complete in {execution_time:.1f} seconds")
    
    if 'aggregated_metrics' in results:
        metrics = results['aggregated_metrics']
        print(f"\n📈 Edit Pattern Summary:")
        print(f"   Total edits analyzed: {metrics['total_edits']}")
        print(f"   MCP-based edits: {metrics['mcp_vs_traditional']['mcp_edits']}")
        print(f"   Traditional edits: {metrics['mcp_vs_traditional']['traditional_edits']}")
        print(f"   Direct edits: {metrics['mcp_vs_traditional']['direct_edits']}")
        
        print(f"\n🎯 Edit Precision:")
        print(f"   MCP targeted edit rate: {metrics['edit_precision']['mcp_diff_ratio']:.1%}")
        print(f"   Traditional targeted edit rate: {metrics['edit_precision']['traditional_diff_ratio']:.1%}")
        
        print(f"\n⚡ Efficiency Metrics:")
        print(f"   Avg tools before MCP edit: {metrics['efficiency_metrics']['avg_tools_before_mcp_edit']:.1f}")
        print(f"   Avg tools before traditional edit: {metrics['efficiency_metrics']['avg_tools_before_traditional_edit']:.1f}")
        print(f"   Avg file reads before traditional edit: {metrics['efficiency_metrics']['avg_reads_before_traditional_edit']:.1f}")
        
        if 'insights' in results:
            print(f"\n💡 Key Insights:")
            insights = results['insights']
            for rec in insights.get('recommendations', []):
                print(f"   • {rec}")
    
    print(f"\n📄 Full analysis saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())