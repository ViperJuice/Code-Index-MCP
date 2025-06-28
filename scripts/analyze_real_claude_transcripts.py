#!/usr/bin/env python3
"""
Enhanced Real Transcript Analyzer with Granular Token Tracking
Integrates with the enhanced agent launcher's TokenBreakdown structure.
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from mcp_server.core.path_utils import PathUtils

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import the TokenBreakdown structure from enhanced_agent_launcher
try:
    from scripts.enhanced_agent_launcher import TokenBreakdown, QueryMetrics
except ImportError:
    print("Warning: Could not import TokenBreakdown from enhanced_agent_launcher")
    TokenBreakdown = None
    QueryMetrics = None


@dataclass
class TranscriptTokenAnalysis:
    """Enhanced token analysis for transcript interactions"""
    interaction_id: str
    timestamp: datetime
    
    # Input token breakdown
    user_prompt_tokens: int
    context_tokens: int
    tool_result_tokens: int
    file_content_tokens: int
    total_input_tokens: int
    
    # Output token breakdown
    reasoning_tokens: int
    tool_call_tokens: int
    code_generation_tokens: int
    explanation_tokens: int
    total_output_tokens: int
    
    # Tool usage
    tools_used: List[str]
    mcp_tools_used: List[str]
    native_tools_used: List[str]
    
    # Efficiency metrics
    token_efficiency: float
    mcp_vs_native_ratio: float
    context_utilization: float


class RealTranscriptAnalyzer:
    """Enhanced analyzer for real Claude Code transcripts with granular token tracking."""
    
    def __init__(self):
        self.tool_usage = defaultdict(int)
        self.tool_patterns = []
        self.grep_to_read_patterns = []
        self.mcp_usage = []
        self.native_usage = []
        
        # Enhanced token tracking
        self.token_analyses: List[TranscriptTokenAnalysis] = []
        self.token_breakdowns: List[TokenBreakdown] = []
        
        # Detailed token counts by category
        self.token_stats = {
            "input_tokens": {
                "user_prompts": [],
                "context": [],
                "tool_results": [],
                "file_content": []
            },
            "output_tokens": {
                "reasoning": [],
                "tool_calls": [],
                "code_generation": [],
                "explanations": []
            },
            "efficiency_metrics": {
                "token_ratios": [],
                "context_utilization": [],
                "mcp_vs_native_efficiency": []
            }
        }
        
        # Tool performance tracking
        self.tool_performance = {
            "mcp_tools": defaultdict(list),
            "native_tools": defaultdict(list)
        }
    
    def estimate_token_count(self, text: str) -> int:
        """Estimate token count using improved heuristics for code/technical text."""
        if not text:
            return 0
        
        # More accurate estimation for different content types
        if '<function_calls>' in text or '<invoke' in text:
            # Tool calls are typically more compact
            return max(1, len(text) // 3)
        elif 'def ' in text or 'class ' in text or 'import ' in text:
            # Code content
            return max(1, len(text) // 3.5)
        else:
            # Regular text
            return max(1, len(text) // 4)
    
    def analyze_transcript_enhanced(self, transcript_path: Path, session_type: str = "unknown") -> Dict[str, Any]:
        """Enhanced transcript analysis with granular token tracking."""
        print(f"\nAnalyzing transcript: {transcript_path.name} (type: {session_type})")
        
        with open(transcript_path, 'r') as f:
            content = f.read()
        
        # Try different formats
        if transcript_path.suffix == '.jsonl':
            return self._analyze_jsonl_transcript(content, session_type)
        elif transcript_path.suffix == '.json':
            return self._analyze_json_transcript(content, session_type)
        else:
            return self._analyze_text_transcript(content, session_type)
    
    def _analyze_jsonl_transcript(self, content: str, session_type: str) -> Dict[str, Any]:
        """Analyze JSONL format transcript."""
        lines = content.strip().split('\n')
        current_interaction = {}
        interaction_count = 0
        
        for line in lines:
            if not line.strip():
                continue
                
            try:
                entry = json.loads(line.strip())
                interaction_count += 1
                
                # Extract tokens and tools from the entry
                analysis = self._extract_interaction_analysis(entry, interaction_count, session_type)
                if analysis:
                    self.token_analyses.append(analysis)
                    self._update_token_stats(analysis)
                    
            except json.JSONDecodeError:
                continue
        
        return self._generate_transcript_summary(session_type, interaction_count)
    
    def _extract_interaction_analysis(self, entry: Dict[str, Any], interaction_id: int, session_type: str) -> Optional[TranscriptTokenAnalysis]:
        """Extract detailed token analysis from a single interaction."""
        if entry.get('type') not in ['user', 'assistant']:
            return None
        
        content = entry.get('content', '')
        timestamp = datetime.fromisoformat(entry.get('timestamp', datetime.now().isoformat()))
        
        # Initialize token counts
        user_prompt_tokens = 0
        context_tokens = 0
        tool_result_tokens = 0
        file_content_tokens = 0
        reasoning_tokens = 0
        tool_call_tokens = 0
        code_generation_tokens = 0
        explanation_tokens = 0
        
        tools_used = []
        mcp_tools_used = []
        native_tools_used = []
        
        if entry['type'] == 'user':
            user_prompt_tokens = self.estimate_token_count(content)
        elif entry['type'] == 'assistant':
            # Analyze assistant response content
            if '<function_calls>' in content:
                # Extract tool calls
                tools = self._extract_tool_calls(content)
                for tool in tools:
                    tools_used.append(tool['name'])
                    if tool['name'].startswith('mcp__'):
                        mcp_tools_used.append(tool['name'])
                        self.mcp_usage.append(tool)
                    else:
                        native_tools_used.append(tool['name'])
                        self.native_usage.append(tool)
                
                tool_call_tokens = self.estimate_token_count(content)
            
            # Extract reasoning (text before tool calls)
            reasoning_part = content.split('<function_calls>')[0] if '<function_calls>' in content else content
            reasoning_tokens = self.estimate_token_count(reasoning_part)
            
            # Extract code blocks
            code_blocks = re.findall(r'```[\w]*\n(.*?)\n```', content, re.DOTALL)
            for code_block in code_blocks:
                code_generation_tokens += self.estimate_token_count(code_block)
            
            # Extract function results (context from previous tools)
            if '<function_results>' in content:
                results = self._extract_function_results(content)
                tool_result_tokens = self.estimate_token_count(results)
                
                # Analyze file content in results
                if any(tool.startswith('Read') for tool in tools_used):
                    file_content_tokens = tool_result_tokens // 2  # Estimate portion that's file content
            
            explanation_tokens = reasoning_tokens  # Simple approximation
        
        total_input_tokens = user_prompt_tokens + context_tokens + tool_result_tokens + file_content_tokens
        total_output_tokens = reasoning_tokens + tool_call_tokens + code_generation_tokens + explanation_tokens
        
        # Calculate efficiency metrics
        token_efficiency = total_output_tokens / max(1, total_input_tokens)
        mcp_vs_native_ratio = len(mcp_tools_used) / max(1, len(native_tools_used) + len(mcp_tools_used))
        context_utilization = context_tokens / max(1, total_input_tokens)
        
        return TranscriptTokenAnalysis(
            interaction_id=f"{session_type}_{interaction_id}",
            timestamp=timestamp,
            user_prompt_tokens=user_prompt_tokens,
            context_tokens=context_tokens,
            tool_result_tokens=tool_result_tokens,
            file_content_tokens=file_content_tokens,
            total_input_tokens=total_input_tokens,
            reasoning_tokens=reasoning_tokens,
            tool_call_tokens=tool_call_tokens,
            code_generation_tokens=code_generation_tokens,
            explanation_tokens=explanation_tokens,
            total_output_tokens=total_output_tokens,
            tools_used=tools_used,
            mcp_tools_used=mcp_tools_used,
            native_tools_used=native_tools_used,
            token_efficiency=token_efficiency,
            mcp_vs_native_ratio=mcp_vs_native_ratio,
            context_utilization=context_utilization
        )
    
    def _update_token_stats(self, analysis: TranscriptTokenAnalysis):
        """Update token statistics with analysis data."""
        # Input token stats
        self.token_stats["input_tokens"]["user_prompts"].append(analysis.user_prompt_tokens)
        self.token_stats["input_tokens"]["context"].append(analysis.context_tokens)
        self.token_stats["input_tokens"]["tool_results"].append(analysis.tool_result_tokens)
        self.token_stats["input_tokens"]["file_content"].append(analysis.file_content_tokens)
        
        # Output token stats
        self.token_stats["output_tokens"]["reasoning"].append(analysis.reasoning_tokens)
        self.token_stats["output_tokens"]["tool_calls"].append(analysis.tool_call_tokens)
        self.token_stats["output_tokens"]["code_generation"].append(analysis.code_generation_tokens)
        self.token_stats["output_tokens"]["explanations"].append(analysis.explanation_tokens)
        
        # Efficiency metrics
        self.token_stats["efficiency_metrics"]["token_ratios"].append(analysis.token_efficiency)
        self.token_stats["efficiency_metrics"]["context_utilization"].append(analysis.context_utilization)
        self.token_stats["efficiency_metrics"]["mcp_vs_native_efficiency"].append(analysis.mcp_vs_native_ratio)
        
        # Tool performance tracking
        for tool in analysis.mcp_tools_used:
            self.tool_performance["mcp_tools"][tool].append({
                "tokens_in": analysis.total_input_tokens,
                "tokens_out": analysis.total_output_tokens,
                "efficiency": analysis.token_efficiency
            })
        
        for tool in analysis.native_tools_used:
            self.tool_performance["native_tools"][tool].append({
                "tokens_in": analysis.total_input_tokens,
                "tokens_out": analysis.total_output_tokens,
                "efficiency": analysis.token_efficiency
            })
    
    def _analyze_json_transcript(self, content: str, session_type: str) -> Dict[str, Any]:
        """Analyze JSON format transcript."""
        try:
            data = json.loads(content)
            # Handle different JSON structures
            if isinstance(data, list):
                interactions = data
            elif isinstance(data, dict) and 'messages' in data:
                interactions = data['messages']
            else:
                interactions = [data]
            
            for i, entry in enumerate(interactions):
                analysis = self._extract_interaction_analysis(entry, i + 1, session_type)
                if analysis:
                    self.token_analyses.append(analysis)
                    self._update_token_stats(analysis)
            
            return self._generate_transcript_summary(session_type, len(interactions))
            
        except json.JSONDecodeError:
            return {"error": "Invalid JSON format"}
    
    def _analyze_text_transcript(self, content: str, session_type: str) -> Dict[str, Any]:
        """Analyze plain text transcript."""
        # Simple text analysis - extract basic metrics
        lines = content.split('\n')
        interaction_count = 0
        
        for line in lines:
            if line.strip().startswith('User:') or line.strip().startswith('Assistant:'):
                interaction_count += 1
                
                # Create basic analysis
                tokens = self.estimate_token_count(line)
                tools_used = []
                
                # Look for tool patterns in text
                if 'mcp__code-index-mcp__' in line:
                    tools_used.extend(re.findall(r'mcp__code-index-mcp__\w+', line))
                
                if tools_used:
                    analysis = TranscriptTokenAnalysis(
                        interaction_id=f"{session_type}_{interaction_count}",
                        timestamp=datetime.now(),
                        user_prompt_tokens=tokens if line.startswith('User:') else 0,
                        context_tokens=0,
                        tool_result_tokens=0,
                        file_content_tokens=0,
                        total_input_tokens=tokens if line.startswith('User:') else 0,
                        reasoning_tokens=tokens if line.startswith('Assistant:') else 0,
                        tool_call_tokens=len(tools_used) * 10,
                        code_generation_tokens=0,
                        explanation_tokens=tokens if line.startswith('Assistant:') else 0,
                        total_output_tokens=tokens if line.startswith('Assistant:') else 0,
                        tools_used=tools_used,
                        mcp_tools_used=[t for t in tools_used if t.startswith('mcp__')],
                        native_tools_used=[t for t in tools_used if not t.startswith('mcp__')],
                        token_efficiency=1.0,
                        mcp_vs_native_ratio=len([t for t in tools_used if t.startswith('mcp__')]) / max(1, len(tools_used)),
                        context_utilization=0.0
                    )
                    
                    self.token_analyses.append(analysis)
                    self._update_token_stats(analysis)
        
        return self._generate_transcript_summary(session_type, interaction_count)
    
    def _generate_transcript_summary(self, session_type: str, interaction_count: int) -> Dict[str, Any]:
        """Generate summary for the analyzed transcript."""
        if not self.token_analyses:
            return {"session_type": session_type, "interactions": interaction_count, "error": "No analyzable interactions found"}
        
        # Calculate averages and totals
        total_input_tokens = sum(a.total_input_tokens for a in self.token_analyses)
        total_output_tokens = sum(a.total_output_tokens for a in self.token_analyses)
        avg_token_efficiency = sum(a.token_efficiency for a in self.token_analyses) / len(self.token_analyses)
        avg_mcp_ratio = sum(a.mcp_vs_native_ratio for a in self.token_analyses) / len(self.token_analyses)
        
        # Tool usage summary
        all_tools = []
        all_mcp_tools = []
        all_native_tools = []
        
        for analysis in self.token_analyses:
            all_tools.extend(analysis.tools_used)
            all_mcp_tools.extend(analysis.mcp_tools_used)
            all_native_tools.extend(analysis.native_tools_used)
        
        tool_usage = {}
        for tool in set(all_tools):
            tool_usage[tool] = all_tools.count(tool)
        
        return {
            "session_type": session_type,
            "total_interactions": interaction_count,
            "analyzed_interactions": len(self.token_analyses),
            "token_summary": {
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
                "avg_token_efficiency": avg_token_efficiency,
                "avg_mcp_vs_native_ratio": avg_mcp_ratio
            },
            "tool_usage": tool_usage,
            "mcp_tool_count": len(all_mcp_tools),
            "native_tool_count": len(all_native_tools),
            "mcp_adoption_rate": len(all_mcp_tools) / max(1, len(all_tools)) * 100
        }
    
    def analyze_transcript(self, transcript_path: Path) -> Dict[str, Any]:
        """Analyze a single transcript file (legacy method)."""
        print(f"\nAnalyzing transcript: {transcript_path.name}")
        
        with open(transcript_path, 'r') as f:
            lines = f.readlines()
        
        current_sequence = []
        
        for line in lines:
            try:
                entry = json.loads(line.strip())
                
                # Skip summaries and other non-content entries
                if entry.get('type') not in ['user', 'assistant']:
                    continue
                
                content = entry.get('content', '')
                
                # Look for tool usage in assistant responses
                if entry['type'] == 'assistant':
                    # Check for tool calls
                    if '<function_calls>' in content:
                        tools_used = self._extract_tool_calls(content)
                        for tool in tools_used:
                            self.tool_usage[tool['name']] += 1
                            current_sequence.append(tool)
                            
                            # Check for MCP tools
                            if tool['name'].startswith('mcp__'):
                                self.mcp_usage.append(tool)
                            
                            # Track Read tool parameters
                            if tool['name'] == 'Read' and 'limit' in tool.get('params', {}):
                                self.read_limits.append(tool['params']['limit'])
                    
                    # Check for function results
                    if '<function_results>' in content:
                        result_content = self._extract_function_results(content)
                        if current_sequence and result_content:
                            last_tool = current_sequence[-1]
                            last_tool['result'] = result_content
                            
                            # Estimate tokens
                            tokens = len(result_content) // 4  # Rough estimate
                            if last_tool['name'] == 'Grep':
                                self.token_counts['grep_outputs'].append(tokens)
                            elif last_tool['name'] == 'Read':
                                self.token_counts['read_limits'].append(tokens)
                            elif last_tool['name'].startswith('mcp__'):
                                self.token_counts['mcp_responses'].append(tokens)
                
                # Detect patterns when sequence changes
                if entry['type'] == 'user' and current_sequence:
                    self._analyze_sequence(current_sequence)
                    current_sequence = []
                    
            except json.JSONDecodeError:
                continue
        
        return {
            "tool_usage": dict(self.tool_usage),
            "patterns": self._summarize_patterns(),
            "mcp_adoption": len(self.mcp_usage),
            "total_tools": sum(self.tool_usage.values())
        }
    
    def _extract_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """Extract tool calls from assistant content."""
        tools = []
        
        # Find all function calls
        function_pattern = r'<invoke name="([^"]+)">(.*?)</invoke>'
        matches = re.findall(function_pattern, content, re.DOTALL)
        
        for tool_name, params_content in matches:
            tool_info = {"name": tool_name, "params": {}}
            
            # Extract parameters
            param_pattern = r'<parameter name="([^"]+)">([^<]*)</parameter>'
            param_matches = re.findall(param_pattern, params_content)
            
            for param_name, param_value in param_matches:
                tool_info["params"][param_name] = param_value
            
            tools.append(tool_info)
        
        return tools
    
    def _extract_function_results(self, content: str) -> str:
        """Extract function results from content."""
        match = re.search(r'<function_results>(.*?)</function_results>', content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
    
    def _analyze_sequence(self, sequence: List[Dict[str, Any]]):
        """Analyze a sequence of tool calls."""
        if len(sequence) < 2:
            return
        
        # Look for grep -> read patterns
        for i in range(len(sequence) - 1):
            if sequence[i]['name'] == 'Grep' and sequence[i+1]['name'] == 'Read':
                self.grep_to_read_patterns.append({
                    'grep_query': sequence[i]['params'].get('pattern', ''),
                    'read_file': sequence[i+1]['params'].get('file_path', ''),
                    'read_limit': sequence[i+1]['params'].get('limit', 'full'),
                    'read_offset': sequence[i+1]['params'].get('offset', 0)
                })
        
        # Record full pattern
        pattern = ' -> '.join([t['name'] for t in sequence])
        self.tool_patterns.append(pattern)
    
    def _summarize_patterns(self) -> Dict[str, Any]:
        """Summarize the patterns found."""
        pattern_counts = defaultdict(int)
        for pattern in self.tool_patterns:
            pattern_counts[pattern] += 1
        
        return {
            "common_patterns": dict(sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "grep_to_read_count": len(self.grep_to_read_patterns),
            "grep_to_read_examples": self.grep_to_read_patterns[:5]
        }
    
    def analyze_all_transcripts_enhanced(self, project_dir: Path, session_type: str = "claude_code") -> Dict[str, Any]:
        """Enhanced analysis of all transcripts with granular token tracking."""
        all_results = {
            "session_type": session_type,
            "total_sessions": 0,
            "total_interactions": 0,
            "total_analyzed_interactions": 0,
            "enhanced_token_analysis": {
                "input_tokens": {
                    "total_user_prompts": 0,
                    "total_context": 0,
                    "total_tool_results": 0,
                    "total_file_content": 0,
                    "avg_user_prompts": 0,
                    "avg_context": 0,
                    "avg_tool_results": 0,
                    "avg_file_content": 0
                },
                "output_tokens": {
                    "total_reasoning": 0,
                    "total_tool_calls": 0,
                    "total_code_generation": 0,
                    "total_explanations": 0,
                    "avg_reasoning": 0,
                    "avg_tool_calls": 0,
                    "avg_code_generation": 0,
                    "avg_explanations": 0
                },
                "efficiency_metrics": {
                    "avg_token_efficiency": 0,
                    "avg_context_utilization": 0,
                    "avg_mcp_vs_native_ratio": 0,
                    "token_efficiency_distribution": [],
                    "context_utilization_distribution": [],
                    "mcp_vs_native_distribution": []
                }
            },
            "tool_performance": {
                "mcp_tools": {},
                "native_tools": {},
                "tool_usage_counts": defaultdict(int),
                "tool_efficiency_comparison": {}
            },
            "session_summaries": []
        }
        
        transcript_files = list(project_dir.glob("*.jsonl")) + list(project_dir.glob("*.json"))
        
        for transcript in transcript_files:
            print(f"Analyzing {transcript.name}...")
            session_summary = self.analyze_transcript_enhanced(transcript, session_type)
            
            if "error" not in session_summary:
                all_results["total_sessions"] += 1
                all_results["total_interactions"] += session_summary["total_interactions"]
                all_results["total_analyzed_interactions"] += session_summary["analyzed_interactions"]
                all_results["session_summaries"].append(session_summary)
        
        # Aggregate all token analyses
        if self.token_analyses:
            self._aggregate_enhanced_results(all_results)
        
        return all_results
    
    def _aggregate_enhanced_results(self, all_results: Dict[str, Any]):
        """Aggregate enhanced token analysis results."""
        total_analyses = len(self.token_analyses)
        
        if total_analyses == 0:
            return
        
        # Aggregate input tokens
        input_stats = all_results["enhanced_token_analysis"]["input_tokens"]
        input_stats["total_user_prompts"] = sum(a.user_prompt_tokens for a in self.token_analyses)
        input_stats["total_context"] = sum(a.context_tokens for a in self.token_analyses)
        input_stats["total_tool_results"] = sum(a.tool_result_tokens for a in self.token_analyses)
        input_stats["total_file_content"] = sum(a.file_content_tokens for a in self.token_analyses)
        
        input_stats["avg_user_prompts"] = input_stats["total_user_prompts"] / total_analyses
        input_stats["avg_context"] = input_stats["total_context"] / total_analyses
        input_stats["avg_tool_results"] = input_stats["total_tool_results"] / total_analyses
        input_stats["avg_file_content"] = input_stats["total_file_content"] / total_analyses
        
        # Aggregate output tokens
        output_stats = all_results["enhanced_token_analysis"]["output_tokens"]
        output_stats["total_reasoning"] = sum(a.reasoning_tokens for a in self.token_analyses)
        output_stats["total_tool_calls"] = sum(a.tool_call_tokens for a in self.token_analyses)
        output_stats["total_code_generation"] = sum(a.code_generation_tokens for a in self.token_analyses)
        output_stats["total_explanations"] = sum(a.explanation_tokens for a in self.token_analyses)
        
        output_stats["avg_reasoning"] = output_stats["total_reasoning"] / total_analyses
        output_stats["avg_tool_calls"] = output_stats["total_tool_calls"] / total_analyses
        output_stats["avg_code_generation"] = output_stats["total_code_generation"] / total_analyses
        output_stats["avg_explanations"] = output_stats["total_explanations"] / total_analyses
        
        # Aggregate efficiency metrics
        efficiency_stats = all_results["enhanced_token_analysis"]["efficiency_metrics"]
        efficiency_stats["avg_token_efficiency"] = sum(a.token_efficiency for a in self.token_analyses) / total_analyses
        efficiency_stats["avg_context_utilization"] = sum(a.context_utilization for a in self.token_analyses) / total_analyses
        efficiency_stats["avg_mcp_vs_native_ratio"] = sum(a.mcp_vs_native_ratio for a in self.token_analyses) / total_analyses
        
        efficiency_stats["token_efficiency_distribution"] = [a.token_efficiency for a in self.token_analyses]
        efficiency_stats["context_utilization_distribution"] = [a.context_utilization for a in self.token_analyses]
        efficiency_stats["mcp_vs_native_distribution"] = [a.mcp_vs_native_ratio for a in self.token_analyses]
        
        # Aggregate tool performance
        tool_perf = all_results["tool_performance"]
        
        # Count tool usage
        for analysis in self.token_analyses:
            for tool in analysis.tools_used:
                tool_perf["tool_usage_counts"][tool] += 1
        
        # Calculate tool efficiency
        for tool_type in ["mcp_tools", "native_tools"]:
            for tool, performances in self.tool_performance[tool_type].items():
                if performances:
                    avg_efficiency = sum(p["efficiency"] for p in performances) / len(performances)
                    avg_tokens_in = sum(p["tokens_in"] for p in performances) / len(performances)
                    avg_tokens_out = sum(p["tokens_out"] for p in performances) / len(performances)
                    
                    tool_perf[tool_type][tool] = {
                        "usage_count": len(performances),
                        "avg_efficiency": avg_efficiency,
                        "avg_tokens_in": avg_tokens_in,
                        "avg_tokens_out": avg_tokens_out,
                        "total_tokens": avg_tokens_in + avg_tokens_out
                    }
        
        # Tool efficiency comparison
        mcp_efficiencies = []
        native_efficiencies = []
        
        for tool, data in tool_perf["mcp_tools"].items():
            mcp_efficiencies.append(data["avg_efficiency"])
        
        for tool, data in tool_perf["native_tools"].items():
            native_efficiencies.append(data["avg_efficiency"])
        
        if mcp_efficiencies and native_efficiencies:
            tool_perf["tool_efficiency_comparison"] = {
                "mcp_avg_efficiency": sum(mcp_efficiencies) / len(mcp_efficiencies),
                "native_avg_efficiency": sum(native_efficiencies) / len(native_efficiencies),
                "mcp_vs_native_efficiency_ratio": (sum(mcp_efficiencies) / len(mcp_efficiencies)) / (sum(native_efficiencies) / len(native_efficiencies)) if native_efficiencies else 1.0
            }
    
    def analyze_all_transcripts(self, project_dir: Path) -> Dict[str, Any]:
        """Analyze all transcripts in a project directory (legacy method)."""
        all_results = {
            "total_sessions": 0,
            "total_tool_usage": defaultdict(int),
            "mcp_adoption_rate": 0,
            "common_patterns": defaultdict(int),
            "read_limits": [],
            "token_analysis": {
                "grep_avg": 0,
                "read_avg": 0,
                "mcp_avg": 0
            }
        }
        
        transcript_files = sorted(project_dir.glob("*.jsonl"))
        
        for transcript in transcript_files:
            result = self.analyze_transcript(transcript)
            all_results["total_sessions"] += 1
            
            # Aggregate tool usage
            for tool, count in result["tool_usage"].items():
                all_results["total_tool_usage"][tool] += count
            
            # Aggregate patterns
            for pattern, count in result["patterns"]["common_patterns"].items():
                all_results["common_patterns"][pattern] += count
        
        # Calculate MCP adoption rate
        total_tools = sum(all_results["total_tool_usage"].values())
        mcp_tools = sum(count for tool, count in all_results["total_tool_usage"].items() 
                       if tool.startswith("mcp__"))
        
        if total_tools > 0:
            all_results["mcp_adoption_rate"] = (mcp_tools / total_tools) * 100
        
        # Calculate token averages
        if self.token_counts["grep_outputs"]:
            all_results["token_analysis"]["grep_avg"] = sum(self.token_counts["grep_outputs"]) / len(self.token_counts["grep_outputs"])
        if self.token_counts["read_limits"]:
            all_results["token_analysis"]["read_avg"] = sum(self.token_counts["read_limits"]) / len(self.token_counts["read_limits"])
        if self.token_counts["mcp_responses"]:
            all_results["token_analysis"]["mcp_avg"] = sum(self.token_counts["mcp_responses"]) / len(self.token_counts["mcp_responses"])
        
        return dict(all_results)


def generate_comprehensive_report(results: Dict[str, Any], output_dir: Path):
    """Generate a comprehensive token analysis report."""
    output_dir.mkdir(exist_ok=True)
    
    # Save main results
    with open(output_dir / "enhanced_transcript_analysis.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Generate summary report
    summary_path = output_dir / "token_analysis_summary.md"
    with open(summary_path, 'w') as f:
        f.write("# Enhanced Transcript Analysis Report\n\n")
        f.write(f"**Session Type:** {results.get('session_type', 'Unknown')}\n")
        f.write(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Overview\n")
        f.write(f"- **Total Sessions:** {results['total_sessions']}\n")
        f.write(f"- **Total Interactions:** {results['total_interactions']}\n")
        f.write(f"- **Analyzed Interactions:** {results['total_analyzed_interactions']}\n\n")
        
        if 'enhanced_token_analysis' in results:
            token_analysis = results['enhanced_token_analysis']
            
            f.write("## Input Token Analysis\n")
            input_tokens = token_analysis['input_tokens']
            f.write(f"- **User Prompts:** {input_tokens['total_user_prompts']:,} total, {input_tokens['avg_user_prompts']:.0f} avg\n")
            f.write(f"- **Context:** {input_tokens['total_context']:,} total, {input_tokens['avg_context']:.0f} avg\n")
            f.write(f"- **Tool Results:** {input_tokens['total_tool_results']:,} total, {input_tokens['avg_tool_results']:.0f} avg\n")
            f.write(f"- **File Content:** {input_tokens['total_file_content']:,} total, {input_tokens['avg_file_content']:.0f} avg\n\n")
            
            f.write("## Output Token Analysis\n")
            output_tokens = token_analysis['output_tokens']
            f.write(f"- **Reasoning:** {output_tokens['total_reasoning']:,} total, {output_tokens['avg_reasoning']:.0f} avg\n")
            f.write(f"- **Tool Calls:** {output_tokens['total_tool_calls']:,} total, {output_tokens['avg_tool_calls']:.0f} avg\n")
            f.write(f"- **Code Generation:** {output_tokens['total_code_generation']:,} total, {output_tokens['avg_code_generation']:.0f} avg\n")
            f.write(f"- **Explanations:** {output_tokens['total_explanations']:,} total, {output_tokens['avg_explanations']:.0f} avg\n\n")
            
            f.write("## Efficiency Metrics\n")
            efficiency = token_analysis['efficiency_metrics']
            f.write(f"- **Average Token Efficiency:** {efficiency['avg_token_efficiency']:.3f}\n")
            f.write(f"- **Average Context Utilization:** {efficiency['avg_context_utilization']:.3f}\n")
            f.write(f"- **Average MCP vs Native Ratio:** {efficiency['avg_mcp_vs_native_ratio']:.3f}\n\n")
        
        if 'tool_performance' in results:
            tool_perf = results['tool_performance']
            
            f.write("## Tool Performance\n")
            f.write("### Tool Usage Counts\n")
            for tool, count in sorted(tool_perf['tool_usage_counts'].items(), key=lambda x: x[1], reverse=True)[:10]:
                f.write(f"- **{tool}:** {count}\n")
            
            f.write("\n### MCP Tool Performance\n")
            for tool, data in tool_perf['mcp_tools'].items():
                f.write(f"- **{tool}:** {data['usage_count']} uses, {data['avg_efficiency']:.3f} efficiency, {data['total_tokens']:.0f} avg tokens\n")
            
            f.write("\n### Native Tool Performance\n")
            for tool, data in tool_perf['native_tools'].items():
                f.write(f"- **{tool}:** {data['usage_count']} uses, {data['avg_efficiency']:.3f} efficiency, {data['total_tokens']:.0f} avg tokens\n")
            
            if 'tool_efficiency_comparison' in tool_perf:
                comp = tool_perf['tool_efficiency_comparison']
                f.write(f"\n### Tool Efficiency Comparison\n")
                f.write(f"- **MCP Average Efficiency:** {comp.get('mcp_avg_efficiency', 0):.3f}\n")
                f.write(f"- **Native Average Efficiency:** {comp.get('native_avg_efficiency', 0):.3f}\n")
                f.write(f"- **MCP vs Native Efficiency Ratio:** {comp.get('mcp_vs_native_efficiency_ratio', 0):.3f}\n")
    
    print(f"Comprehensive report saved to: {summary_path}")


def main():
    """Enhanced analysis of real Claude Code transcripts with granular token tracking."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze Claude Code transcripts with enhanced token tracking')
    parser.add_argument('--project-dir', type=Path, 
                       default=Path.home() / ".claude/projects/-workspaces-Code-Index-MCP",
                       help='Path to Claude project directory')
    parser.add_argument('--session-type', type=str, default="claude_code",
                       help='Session type identifier')
    parser.add_argument('--output-dir', type=Path, 
                       default=Path("PathUtils.get_workspace_root()/enhanced_analysis_results"),
                       help='Output directory for results')
    parser.add_argument('--legacy', action='store_true',
                       help='Use legacy analysis method')
    
    args = parser.parse_args()
    
    analyzer = RealTranscriptAnalyzer()
    
    if not args.project_dir.exists():
        print(f"Project directory not found: {args.project_dir}")
        print("Available directories:")
        claude_dir = Path.home() / ".claude/projects"
        if claude_dir.exists():
            for d in claude_dir.iterdir():
                if d.is_dir():
                    print(f"  {d}")
        return
    
    print("Enhanced Real Claude Code Transcript Analysis")
    print("=" * 80)
    print(f"Project Directory: {args.project_dir}")
    print(f"Session Type: {args.session_type}")
    print(f"Output Directory: {args.output_dir}")
    
    if args.legacy:
        print("\nUsing legacy analysis method...")
        results = analyzer.analyze_all_transcripts(args.project_dir)
        
        # Print legacy results
        print(f"\nTotal Sessions Analyzed: {results['total_sessions']}")
        print(f"\nTool Usage Summary:")
        for tool, count in sorted(results['total_tool_usage'].items(), key=lambda x: x[1], reverse=True)[:20]:
            print(f"  {tool}: {count}")
        
        print(f"\nMCP Adoption Rate: {results['mcp_adoption_rate']:.2f}%")
        
        # Save legacy results
        output_path = args.output_dir / "legacy_transcript_analysis.json"
        args.output_dir.mkdir(exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nLegacy results saved to: {output_path}")
    else:
        print("\nUsing enhanced analysis method...")
        results = analyzer.analyze_all_transcripts_enhanced(args.project_dir, args.session_type)
        
        # Print enhanced results
        print(f"\nEnhanced Analysis Results:")
        print(f"Total Sessions: {results['total_sessions']}")
        print(f"Total Interactions: {results['total_interactions']}")
        print(f"Analyzed Interactions: {results['total_analyzed_interactions']}")
        
        if 'enhanced_token_analysis' in results:
            token_analysis = results['enhanced_token_analysis']
            input_total = sum(token_analysis['input_tokens'].values())
            output_total = sum(token_analysis['output_tokens'].values())
            print(f"\nToken Summary:")
            print(f"  Total Input Tokens: {input_total:,}")
            print(f"  Total Output Tokens: {output_total:,}")
            print(f"  Total Tokens: {input_total + output_total:,}")
            
            efficiency = token_analysis['efficiency_metrics']
            print(f"\nEfficiency Metrics:")
            print(f"  Average Token Efficiency: {efficiency['avg_token_efficiency']:.3f}")
            print(f"  Average Context Utilization: {efficiency['avg_context_utilization']:.3f}")
            print(f"  Average MCP vs Native Ratio: {efficiency['avg_mcp_vs_native_ratio']:.3f}")
        
        # Generate comprehensive report
        generate_comprehensive_report(results, args.output_dir)
        
        print(f"\nDetailed results saved to: {args.output_dir}")


if __name__ == "__main__":
    main()