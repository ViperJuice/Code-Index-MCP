#!/usr/bin/env python3
"""
Tool Usage Analyzer for MCP Verification
Analyzes Claude Code's tool usage patterns to verify MCP-first behavior
"""

import json
import re
from typing import List, Dict, Any, Tuple
from datetime import datetime
from collections import defaultdict, Counter


class ToolUsageAnalyzer:
    """Analyzes tool usage patterns from Claude Code sessions"""
    
    def __init__(self):
        self.mcp_tools = {
            'mcp__code-index-mcp__symbol_lookup',
            'mcp__code-index-mcp__search_code',
            'mcp__code-index-mcp__get_status',
            'mcp__code-index-mcp__list_plugins',
            'mcp__code-index-mcp__reindex'
        }
        
        self.native_search_tools = {
            'Grep', 'grep',
            'Find', 'find',
            'Glob', 'glob'
        }
        
        self.file_tools = {
            'Read', 'read',
            'LS', 'ls'
        }
        
    def parse_tool_sequence(self, session_log: str) -> List[Dict[str, Any]]:
        """Parse tool usage from a session log"""
        tools_used = []
        
        # Patterns to match different tool invocations
        patterns = [
            # MCP tools
            r'mcp__code-index-mcp__(\w+)\((.*?)\)',
            # Native tools (from logs)
            r'Tool: (\w+)(?:\((.*?)\))?',
            r'Running: (grep|find|ls) (.*)',
            r'<tool>(\w+)</tool>',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, session_log, re.MULTILINE | re.DOTALL)
            for match in matches:
                tool_name = match.group(1)
                params = match.group(2) if len(match.groups()) > 1 else ''
                
                # Normalize tool names
                if 'mcp__' in match.group(0):
                    tool_name = f'mcp__code-index-mcp__{tool_name}'
                
                tools_used.append({
                    'tool': tool_name,
                    'params': params,
                    'position': match.start()
                })
        
        # Sort by position to get chronological order
        tools_used.sort(key=lambda x: x['position'])
        
        return tools_used
    
    def analyze_mcp_first_pattern(self, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze if MCP tools were used before native search"""
        analysis = {
            'mcp_first': True,
            'violations': [],
            'mcp_usage_count': 0,
            'native_search_count': 0,
            'total_tools': len(tools)
        }
        
        first_mcp_pos = None
        first_native_search_pos = None
        
        for i, tool_info in enumerate(tools):
            tool = tool_info['tool']
            
            if tool in self.mcp_tools:
                analysis['mcp_usage_count'] += 1
                if first_mcp_pos is None:
                    first_mcp_pos = i
                    
            elif tool in self.native_search_tools:
                analysis['native_search_count'] += 1
                if first_native_search_pos is None:
                    first_native_search_pos = i
                
                # Check if this violates MCP-first
                if first_mcp_pos is None or i < first_mcp_pos:
                    analysis['mcp_first'] = False
                    analysis['violations'].append({
                        'position': i,
                        'tool': tool,
                        'reason': 'Native search used before MCP'
                    })
        
        return analysis
    
    def calculate_performance_metrics(self, tools: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate performance metrics based on tool usage"""
        metrics = {
            'total_time_estimated': 0.0,
            'mcp_time': 0.0,
            'native_time': 0.0,
            'file_reads': 0
        }
        
        # Estimated times (in seconds)
        tool_times = {
            'mcp__code-index-mcp__symbol_lookup': 0.1,
            'mcp__code-index-mcp__search_code': 0.5,
            'mcp__code-index-mcp__get_status': 0.05,
            'mcp__code-index-mcp__list_plugins': 0.1,
            'mcp__code-index-mcp__reindex': 2.0,
            'Grep': 30.0,
            'grep': 30.0,
            'Find': 20.0,
            'find': 20.0,
            'Glob': 5.0,
            'glob': 5.0,
            'Read': 0.5,
            'read': 0.5,
            'LS': 0.1,
            'ls': 0.1
        }
        
        for tool_info in tools:
            tool = tool_info['tool']
            time_taken = tool_times.get(tool, 1.0)
            
            metrics['total_time_estimated'] += time_taken
            
            if tool in self.mcp_tools:
                metrics['mcp_time'] += time_taken
            elif tool in self.native_search_tools:
                metrics['native_time'] += time_taken
            elif tool in self.file_tools:
                metrics['file_reads'] += 1
        
        return metrics
    
    def generate_usage_report(self, tools: List[Dict[str, Any]]) -> str:
        """Generate a comprehensive usage report"""
        analysis = self.analyze_mcp_first_pattern(tools)
        metrics = self.calculate_performance_metrics(tools)
        
        report = [
            "# Tool Usage Analysis Report",
            f"\nGenerated: {datetime.now().isoformat()}",
            "\n## Summary",
            f"- Total Tools Used: {analysis['total_tools']}",
            f"- MCP Tools: {analysis['mcp_usage_count']}",
            f"- Native Search Tools: {analysis['native_search_count']}",
            f"- MCP-First Compliance: {'✅ YES' if analysis['mcp_first'] else '❌ NO'}",
            "\n## Performance Metrics",
            f"- Estimated Total Time: {metrics['total_time_estimated']:.1f}s",
            f"- MCP Time: {metrics['mcp_time']:.1f}s",
            f"- Native Search Time: {metrics['native_time']:.1f}s",
            f"- File Reads: {metrics['file_reads']}",
        ]
        
        if metrics['native_time'] > 0:
            speedup = metrics['native_time'] / max(metrics['mcp_time'], 0.1)
            report.append(f"- Potential Speedup: {speedup:.0f}x faster with MCP")
        
        if analysis['violations']:
            report.extend([
                "\n## ⚠️ Violations Found",
                "The following violations of MCP-first strategy were detected:"
            ])
            for v in analysis['violations']:
                report.append(f"- Position {v['position']}: {v['tool']} - {v['reason']}")
        
        report.extend([
            "\n## Tool Usage Sequence",
            "```"
        ])
        
        for i, tool_info in enumerate(tools):
            prefix = "✅" if tool_info['tool'] in self.mcp_tools else "⚠️"
            report.append(f"{i+1}. {prefix} {tool_info['tool']}")
            if tool_info['params']:
                report.append(f"   Params: {tool_info['params'][:50]}...")
        
        report.append("```")
        
        return "\n".join(report)
    
    def analyze_session_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a Claude Code session file"""
        with open(file_path, 'r') as f:
            session_log = f.read()
        
        tools = self.parse_tool_sequence(session_log)
        analysis = self.analyze_mcp_first_pattern(tools)
        metrics = self.calculate_performance_metrics(tools)
        
        return {
            'tools': tools,
            'analysis': analysis,
            'metrics': metrics,
            'report': self.generate_usage_report(tools)
        }
    
    def parse_session_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse a session file and extract tool calls"""
        with open(file_path, 'r') as f:
            content = f.read()
        
        tools_used = []
        
        # Parse [Tool Call] entries
        tool_pattern = r'\[Tool Call\]: (\w+(?:__[\w-]+)*)\((.*?)\)'
        matches = re.finditer(tool_pattern, content, re.MULTILINE)
        
        for match in matches:
            tool_name = match.group(1)
            params = match.group(2)
            
            tools_used.append({
                'tool': tool_name,
                'params': params,
                'position': match.start()
            })
        
        return tools_used


def create_mock_session_log() -> str:
    """Create a mock session log for testing"""
    return """
    User: Find where PluginManager is defined
    
    Assistant: I'll help you find the PluginManager class definition.
    
    Using mcp__code-index-mcp__symbol_lookup(symbol="PluginManager")
    
    Found: PluginManager in plugin_manager.py at line 45
    
    Now let me read the file to show you the implementation:
    
    Tool: Read(file_path="mcp_server/plugin_system/plugin_manager.py")
    
    User: Search for all process_ functions
    
    Assistant: I'll search for all functions starting with process_
    
    Tool: Grep(pattern="def process_")  # This is wrong!
    
    Actually, let me use the MCP search instead:
    
    mcp__code-index-mcp__search_code(query="def process_.*", limit=20)
    """


if __name__ == "__main__":
    import sys
    analyzer = ToolUsageAnalyzer()
    
    # Check if a session file was provided
    if len(sys.argv) > 1:
        session_file = sys.argv[1]
        print(f"🔍 Analyzing session file: {session_file}")
        print("=" * 60)
        
        # Parse the actual session file
        tools = analyzer.parse_session_file(session_file)
        
        print("\nTools detected:")
        for i, tool in enumerate(tools):
            print(f"{i+1}. {tool['tool']}")
        
        report = analyzer.generate_usage_report(tools)
        print("\n" + report)
        
        # Save analysis
        output_file = session_file.replace('.log', '_analysis.md')
        with open(output_file, 'w') as f:
            f.write(report)
        print(f"\n📊 Analysis saved to: {output_file}")
    else:
        # Test with mock data
        print("🔍 Testing Tool Usage Analyzer")
        print("=" * 60)
        
        mock_log = create_mock_session_log()
        tools = analyzer.parse_tool_sequence(mock_log)
        
        print("\nTools detected:")
        for i, tool in enumerate(tools):
            print(f"{i+1}. {tool['tool']}")
        
        print("\n" + analyzer.generate_usage_report(tools))
        
        # Save mock analysis
        with open('mock_usage_analysis.md', 'w') as f:
            f.write(analyzer.generate_usage_report(tools))