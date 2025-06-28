#!/usr/bin/env python3
"""
Comprehensive Claude Code behavior analysis comparing MCP vs non-MCP usage.
Analyzes real transcripts to understand:
1. How Claude Code uses MCP tools vs grep/find
2. Token usage patterns (partial reads vs full file reads)
3. Edit patterns (diffs vs rewrites)
"""

import json
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Tuple
import hashlib


class ClaudeCodeBehaviorAnalyzer:
    """Analyze Claude Code behavior from transcripts."""
    
    def __init__(self):
        self.mcp_patterns = {
            'symbol_lookup': r'symbol_lookup.*?"symbol":\s*"([^"]+)"',
            'search_code': r'search_code.*?"query":\s*"([^"]+)"',
            'reindex': r'reindex.*?"path":\s*"([^"]+)"',
        }
        
        self.native_patterns = {
            'grep': r'Grep.*?"pattern":\s*"([^"]+)"',
            'find': r'Bash.*?find\s+[^\s]+\s+-name\s+"([^"]+)"',
            'read': r'Read.*?"file_path":\s*"([^"]+)".*?"offset":\s*(\d+).*?"limit":\s*(\d+)',
            'read_simple': r'Read.*?"file_path":\s*"([^"]+)"(?!.*offset)',
        }
        
        self.edit_patterns = {
            'edit': r'Edit.*?"file_path":\s*"([^"]+)".*?"old_string".*?"new_string"',
            'multi_edit': r'MultiEdit.*?"file_path":\s*"([^"]+)".*?"edits"',
            'write': r'Write.*?"file_path":\s*"([^"]+)".*?"content"',
        }
    
    def analyze_transcript(self, transcript_path: Path) -> Dict[str, Any]:
        """Analyze a single transcript file."""
        content = transcript_path.read_text()
        
        results = {
            'file': transcript_path.name,
            'mcp_usage': defaultdict(list),
            'native_usage': defaultdict(list),
            'edit_patterns': defaultdict(int),
            'read_patterns': {
                'partial_reads': 0,
                'full_reads': 0,
                'total_lines_read': 0,
            },
            'workflow_patterns': [],
            'token_estimates': {
                'mcp_tokens': 0,
                'native_tokens': 0,
                'edit_tokens': 0,
            }
        }
        
        # Analyze MCP usage
        for tool, pattern in self.mcp_patterns.items():
            matches = re.findall(pattern, content, re.DOTALL)
            results['mcp_usage'][tool].extend(matches)
        
        # Analyze native tool usage
        for tool, pattern in self.native_patterns.items():
            if tool == 'read':
                # Special handling for Read with offset/limit
                matches = re.findall(pattern, content, re.DOTALL)
                for match in matches:
                    file_path, offset, limit = match
                    results['native_usage']['read_partial'].append({
                        'file': file_path,
                        'offset': int(offset),
                        'limit': int(limit)
                    })
                    results['read_patterns']['partial_reads'] += 1
                    results['read_patterns']['total_lines_read'] += int(limit)
            elif tool == 'read_simple':
                matches = re.findall(pattern, content, re.DOTALL)
                results['native_usage']['read_full'].extend(matches)
                results['read_patterns']['full_reads'] += len(matches)
                # Estimate 2000 lines for full reads (default)
                results['read_patterns']['total_lines_read'] += len(matches) * 2000
            else:
                matches = re.findall(pattern, content, re.DOTALL)
                results['native_usage'][tool].extend(matches)
        
        # Analyze edit patterns
        for edit_type, pattern in self.edit_patterns.items():
            matches = re.findall(pattern, content, re.DOTALL)
            results['edit_patterns'][edit_type] = len(matches)
        
        # Analyze workflow patterns
        results['workflow_patterns'] = self._analyze_workflow_patterns(content)
        
        # Estimate token usage
        results['token_estimates'] = self._estimate_tokens(results)
        
        return results
    
    def _analyze_workflow_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Identify common workflow patterns."""
        patterns = []
        
        # Pattern: Search -> Read -> Edit
        search_read_edit = re.findall(
            r'(Grep|search_code).*?"([^"]+)".*?Read.*?"([^"]+)".*?(Edit|MultiEdit)',
            content, re.DOTALL
        )
        if search_read_edit:
            patterns.append({
                'type': 'search_read_edit',
                'count': len(search_read_edit),
                'details': search_read_edit[:3]  # First 3 examples
            })
        
        # Pattern: Symbol lookup -> Read at specific line
        symbol_read = re.findall(
            r'symbol_lookup.*?"symbol":\s*"([^"]+)".*?Read.*?offset":\s*(\d+)',
            content, re.DOTALL
        )
        if symbol_read:
            patterns.append({
                'type': 'symbol_lookup_targeted_read',
                'count': len(symbol_read),
                'examples': symbol_read[:3]
            })
        
        # Pattern: Multiple edits without full file reads
        multi_edit_no_full_read = re.findall(
            r'Read.*?offset.*?MultiEdit.*?"edits":\s*\[(.*?)\]',
            content, re.DOTALL
        )
        if multi_edit_no_full_read:
            patterns.append({
                'type': 'efficient_multi_edit',
                'count': len(multi_edit_no_full_read)
            })
        
        return patterns
    
    def _estimate_tokens(self, results: Dict[str, Any]) -> Dict[str, int]:
        """Estimate token usage for different approaches."""
        tokens = {
            'mcp_tokens': 0,
            'native_tokens': 0,
            'edit_tokens': 0,
        }
        
        # MCP tokens (assuming efficient snippets ~100 tokens per result)
        for tool, queries in results['mcp_usage'].items():
            tokens['mcp_tokens'] += len(queries) * 100
        
        # Native tokens
        # Full file reads: ~5000 tokens per file
        tokens['native_tokens'] += results['read_patterns']['full_reads'] * 5000
        # Partial reads: ~50 tokens per line
        tokens['native_tokens'] += results['read_patterns']['total_lines_read'] * 50
        # Grep results: ~200 tokens per search
        tokens['native_tokens'] += len(results['native_usage'].get('grep', [])) * 200
        
        # Edit tokens
        # Edits: ~200 tokens per edit
        for edit_type, count in results['edit_patterns'].items():
            if edit_type == 'write':
                tokens['edit_tokens'] += count * 5000  # Full file rewrites
            else:
                tokens['edit_tokens'] += count * 200   # Targeted edits
        
        return tokens
    
    def generate_comparison_report(self, transcripts_dir: Path) -> Dict[str, Any]:
        """Generate comprehensive comparison report from multiple transcripts."""
        all_results = []
        
        # Analyze all transcript files
        for transcript_file in transcripts_dir.glob("*.json"):
            try:
                results = self.analyze_transcript(transcript_file)
                all_results.append(results)
            except Exception as e:
                print(f"Error analyzing {transcript_file}: {e}")
        
        # Aggregate results
        report = {
            'total_transcripts': len(all_results),
            'mcp_adoption': {
                'symbol_lookup_usage': sum(len(r['mcp_usage']['symbol_lookup']) for r in all_results),
                'search_code_usage': sum(len(r['mcp_usage']['search_code']) for r in all_results),
                'reindex_usage': sum(len(r['mcp_usage']['reindex']) for r in all_results),
            },
            'native_tool_usage': {
                'grep_usage': sum(len(r['native_usage'].get('grep', [])) for r in all_results),
                'find_usage': sum(len(r['native_usage'].get('find', [])) for r in all_results),
                'full_file_reads': sum(r['read_patterns']['full_reads'] for r in all_results),
                'partial_reads': sum(r['read_patterns']['partial_reads'] for r in all_results),
            },
            'efficiency_metrics': {
                'avg_lines_per_read': sum(r['read_patterns']['total_lines_read'] for r in all_results) / 
                                     max(1, sum(r['read_patterns']['partial_reads'] + r['read_patterns']['full_reads'] for r in all_results)),
                'partial_read_percentage': sum(r['read_patterns']['partial_reads'] for r in all_results) * 100 / 
                                          max(1, sum(r['read_patterns']['partial_reads'] + r['read_patterns']['full_reads'] for r in all_results)),
            },
            'edit_efficiency': {
                'targeted_edits': sum(r['edit_patterns']['edit'] + r['edit_patterns']['multi_edit'] for r in all_results),
                'full_rewrites': sum(r['edit_patterns']['write'] for r in all_results),
            },
            'token_comparison': {
                'total_mcp_tokens': sum(r['token_estimates']['mcp_tokens'] for r in all_results),
                'total_native_tokens': sum(r['token_estimates']['native_tokens'] for r in all_results),
                'total_edit_tokens': sum(r['token_estimates']['edit_tokens'] for r in all_results),
            },
            'workflow_patterns': self._aggregate_workflow_patterns(all_results),
        }
        
        # Calculate potential savings
        if report['token_comparison']['total_native_tokens'] > 0:
            report['potential_savings'] = {
                'token_reduction_percentage': 
                    (report['token_comparison']['total_native_tokens'] - report['token_comparison']['total_mcp_tokens']) * 100 / 
                    report['token_comparison']['total_native_tokens'],
                'estimated_time_savings': 'High (targeted reads vs full file scans)',
                'accuracy_improvement': 'High (direct symbol lookup vs pattern matching)',
            }
        
        return report
    
    def _aggregate_workflow_patterns(self, all_results: List[Dict[str, Any]]) -> Dict[str, int]:
        """Aggregate workflow patterns across all transcripts."""
        patterns = defaultdict(int)
        
        for result in all_results:
            for pattern in result['workflow_patterns']:
                patterns[pattern['type']] += pattern['count']
        
        return dict(patterns)
    
    def create_visual_report(self, report: Dict[str, Any]) -> str:
        """Create a visual text-based report."""
        lines = []
        lines.append("=" * 80)
        lines.append("Claude Code Behavior Analysis: MCP vs Native Tools")
        lines.append("=" * 80)
        
        # MCP Adoption
        lines.append("\n1. MCP Tool Adoption:")
        lines.append(f"   - Symbol Lookup: {report['mcp_adoption']['symbol_lookup_usage']} uses")
        lines.append(f"   - Code Search: {report['mcp_adoption']['search_code_usage']} uses")
        lines.append(f"   - Reindex: {report['mcp_adoption']['reindex_usage']} uses")
        lines.append(f"   - TOTAL MCP: {sum(report['mcp_adoption'].values())} uses")
        
        # Native Tool Usage
        lines.append("\n2. Native Tool Usage:")
        lines.append(f"   - Grep: {report['native_tool_usage']['grep_usage']} uses")
        lines.append(f"   - Find: {report['native_tool_usage']['find_usage']} uses")
        lines.append(f"   - Full File Reads: {report['native_tool_usage']['full_file_reads']}")
        lines.append(f"   - Partial Reads: {report['native_tool_usage']['partial_reads']}")
        
        # Efficiency Metrics
        lines.append("\n3. Read Efficiency:")
        lines.append(f"   - Average lines per read: {report['efficiency_metrics']['avg_lines_per_read']:.1f}")
        lines.append(f"   - Partial read percentage: {report['efficiency_metrics']['partial_read_percentage']:.1f}%")
        
        # Edit Patterns
        lines.append("\n4. Edit Patterns:")
        lines.append(f"   - Targeted edits (Edit/MultiEdit): {report['edit_efficiency']['targeted_edits']}")
        lines.append(f"   - Full file rewrites (Write): {report['edit_efficiency']['full_rewrites']}")
        edit_efficiency = report['edit_efficiency']['targeted_edits'] * 100 / max(1, sum(report['edit_efficiency'].values()))
        lines.append(f"   - Edit efficiency: {edit_efficiency:.1f}% targeted")
        
        # Token Usage
        lines.append("\n5. Token Usage Comparison:")
        lines.append(f"   - MCP approach: {report['token_comparison']['total_mcp_tokens']:,} tokens")
        lines.append(f"   - Native approach: {report['token_comparison']['total_native_tokens']:,} tokens")
        lines.append(f"   - Edit operations: {report['token_comparison']['total_edit_tokens']:,} tokens")
        
        # Workflow Patterns
        lines.append("\n6. Common Workflow Patterns:")
        for pattern, count in report['workflow_patterns'].items():
            lines.append(f"   - {pattern}: {count} occurrences")
        
        # Potential Savings
        if 'potential_savings' in report:
            lines.append("\n7. Potential Savings with Full MCP Adoption:")
            lines.append(f"   - Token reduction: {report['potential_savings']['token_reduction_percentage']:.1f}%")
            lines.append(f"   - Time savings: {report['potential_savings']['estimated_time_savings']}")
            lines.append(f"   - Accuracy: {report['potential_savings']['accuracy_improvement']}")
        
        lines.append("\n" + "=" * 80)
        
        return "\n".join(lines)


def main():
    """Run comprehensive behavior analysis."""
    analyzer = ClaudeCodeBehaviorAnalyzer()
    
    # For demo, create a sample transcript
    sample_transcript = Path("/tmp/sample_transcript.json")
    sample_content = '''
    User: Find the BM25Indexer class and show me its search method
    
    Assistant: I'll help you find the BM25Indexer class and its search method.
    
    <function_calls>
    <invoke name="Grep">
    <parameter name="pattern">class BM25Indexer