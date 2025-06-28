#!/usr/bin/env python3
"""
Real Performance Data Consolidation Script

Consolidates all real performance data from MCP vs Native testing
into a single queryable dataset for analysis and reporting.

Usage: python scripts/consolidate_real_performance_data.py
"""

import json
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from mcp_server.core.path_utils import PathUtils
# import pandas as pd  # Not available, using built-in statistics

@dataclass
class ConsolidatedResult:
    """Consolidated performance result with all metrics"""
    session_id: str
    test_date: str
    query_id: str
    query_text: str
    category: str
    complexity: str
    approach: str  # 'mcp' or 'native'
    
    # Performance metrics
    response_time_ms: float
    success: bool
    
    # Token metrics
    input_tokens_user: int
    input_tokens_context: int
    input_tokens_tools: int
    input_tokens_files: int
    input_tokens_total: int
    
    output_tokens_reasoning: int
    output_tokens_tools: int
    output_tokens_code: int
    output_tokens_explanations: int
    output_tokens_total: int
    
    # Cache metrics
    cache_read_tokens: int
    cache_creation_tokens: int
    
    # Efficiency metrics
    tokens_per_result: float
    context_utilization: float
    generation_efficiency: float
    
    # Tool usage
    tool_call_count: int
    tools_used: List[str]
    file_reads: List[str]
    file_writes: List[str]
    
    # Results
    accuracy_score: Optional[float]
    result_quality: str
    
class PerformanceDataConsolidator:
    """Consolidates performance data from multiple sources"""
    
    def __init__(self, base_dir: str = "PathUtils.get_workspace_root()"):
        self.base_dir = Path(base_dir)
        self.results_dir = self.base_dir / "comprehensive_test_results"
        self.transcript_dir = Path("Path.home() / ".claude"/projects")
        
        self.consolidated_data: List[ConsolidatedResult] = []
        
    def collect_all_data(self) -> List[ConsolidatedResult]:
        """Collect and consolidate all performance data"""
        print("🔍 Collecting performance data from all sources...")
        
        # Collect from comprehensive test results
        self._collect_comprehensive_results()
        
        # Collect from Claude Code transcripts
        self._collect_transcript_data()
        
        # Collect from intermediate results
        self._collect_intermediate_results()
        
        print(f"✅ Consolidated {len(self.consolidated_data)} performance data points")
        return self.consolidated_data
    
    def _collect_comprehensive_results(self):
        """Collect from comprehensive test result files"""
        if not self.results_dir.exists():
            print(f"⚠️  Results directory not found: {self.results_dir}")
            return
            
        for result_file in self.results_dir.glob("comprehensive_analysis_*.json"):
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    self._process_comprehensive_data(data, result_file.name)
            except Exception as e:
                print(f"❌ Error processing {result_file}: {e}")
    
    def _collect_transcript_data(self):
        """Collect from Claude Code session transcripts"""
        transcript_patterns = [
            "-workspaces-Code-Index-MCP-testing-env-worktree-mcp/*.jsonl",
            "-workspaces-Code-Index-MCP-testing-env-worktree-native/*.jsonl"
        ]
        
        for pattern in transcript_patterns:
            for transcript_file in self.transcript_dir.glob(pattern):
                try:
                    self._process_transcript_file(transcript_file)
                except Exception as e:
                    print(f"❌ Error processing transcript {transcript_file}: {e}")
    
    def _collect_intermediate_results(self):
        """Collect from intermediate result files"""
        for result_file in self.results_dir.glob("intermediate_results_*.json"):
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    self._process_intermediate_data(data, result_file.name)
            except Exception as e:
                print(f"❌ Error processing intermediate {result_file}: {e}")
    
    def _process_comprehensive_data(self, data: Dict, filename: str):
        """Process comprehensive analysis data"""
        session_id = filename.replace("comprehensive_analysis_mcp_vs_native_", "").replace(".json", "")
        
        for query_result in data.get('query_results', []):
            # Process MCP result
            if 'mcp_result' in query_result:
                mcp_result = self._create_consolidated_result(
                    query_result['mcp_result'], 
                    query_result,
                    session_id,
                    'mcp'
                )
                if mcp_result:
                    self.consolidated_data.append(mcp_result)
            
            # Process Native result  
            if 'native_result' in query_result:
                native_result = self._create_consolidated_result(
                    query_result['native_result'],
                    query_result,
                    session_id, 
                    'native'
                )
                if native_result:
                    self.consolidated_data.append(native_result)
    
    def _process_intermediate_data(self, data: List[Dict], filename: str):
        """Process intermediate result data"""
        session_id = filename.replace("intermediate_results_mcp_vs_native_", "").replace(".json", "")
        
        for query_result in data:
            # Process MCP result
            if 'mcp_result' in query_result:
                mcp_result = self._create_consolidated_result(
                    query_result['mcp_result'],
                    query_result,
                    session_id,
                    'mcp'
                )
                if mcp_result:
                    self.consolidated_data.append(mcp_result)
            
            # Process Native result
            if 'native_result' in query_result:
                native_result = self._create_consolidated_result(
                    query_result['native_result'],
                    query_result,
                    session_id,
                    'native'
                )
                if native_result:
                    self.consolidated_data.append(native_result)
    
    def _process_transcript_file(self, transcript_file: Path):
        """Process individual transcript file"""
        approach = 'mcp' if 'worktree-mcp' in str(transcript_file) else 'native'
        session_id = transcript_file.stem
        
        with open(transcript_file, 'r') as f:
            lines = f.readlines()
            
        current_query = None
        current_interaction = None
        
        for line in lines:
            try:
                entry = json.loads(line.strip())
                
                if entry.get('type') == 'user':
                    current_query = entry['message']['content']
                    current_interaction = {
                        'query': current_query,
                        'start_time': entry['timestamp'],
                        'session_id': session_id
                    }
                
                elif entry.get('type') == 'assistant' and current_interaction:
                    usage = entry.get('message', {}).get('usage', {})
                    if usage:
                        result = self._create_consolidated_from_transcript(
                            current_interaction,
                            entry,
                            approach
                        )
                        if result:
                            self.consolidated_data.append(result)
                        current_interaction = None
                        
            except (json.JSONDecodeError, KeyError) as e:
                continue  # Skip malformed entries
    
    def _create_consolidated_result(self, result_data: Dict, query_data: Dict, 
                                  session_id: str, approach: str) -> Optional[ConsolidatedResult]:
        """Create consolidated result from test data"""
        try:
            token_breakdown = result_data.get('token_breakdown', {})
            
            return ConsolidatedResult(
                session_id=session_id,
                test_date=result_data.get('start_time', ''),
                query_id=query_data.get('query_id', ''),
                query_text=query_data.get('query_text', ''),
                category=query_data.get('category', ''),
                complexity=query_data.get('complexity', ''),
                approach=approach,
                
                # Performance
                response_time_ms=result_data.get('response_time_ms', 0),
                success=result_data.get('success', False),
                
                # Input tokens
                input_tokens_user=token_breakdown.get('user_prompt', 0),
                input_tokens_context=token_breakdown.get('context_history', 0),
                input_tokens_tools=token_breakdown.get('tool_results', 0),
                input_tokens_files=token_breakdown.get('file_content', 0),
                input_tokens_total=token_breakdown.get('total_input', 0),
                
                # Output tokens
                output_tokens_reasoning=token_breakdown.get('reasoning', 0),
                output_tokens_tools=token_breakdown.get('tool_calls', 0),
                output_tokens_code=token_breakdown.get('code_generation', 0),
                output_tokens_explanations=token_breakdown.get('explanations', 0),
                output_tokens_total=token_breakdown.get('total_output', 0),
                
                # Cache
                cache_read_tokens=0,  # Not available in test data
                cache_creation_tokens=0,
                
                # Efficiency
                tokens_per_result=token_breakdown.get('tokens_per_result', 0),
                context_utilization=token_breakdown.get('context_utilization', 0),
                generation_efficiency=token_breakdown.get('generation_efficiency', 0),
                
                # Tool usage
                tool_call_count=result_data.get('tool_call_count', 0),
                tools_used=result_data.get('tools_used', []),
                file_reads=result_data.get('file_reads', []),
                file_writes=result_data.get('file_writes', []),
                
                # Results
                accuracy_score=result_data.get('accuracy_score'),
                result_quality='success' if result_data.get('success') else 'failure'
            )
            
        except Exception as e:
            print(f"❌ Error creating consolidated result: {e}")
            return None
    
    def _create_consolidated_from_transcript(self, interaction: Dict, assistant_entry: Dict, 
                                           approach: str) -> Optional[ConsolidatedResult]:
        """Create consolidated result from transcript data"""
        try:
            usage = assistant_entry.get('message', {}).get('usage', {})
            
            return ConsolidatedResult(
                session_id=interaction['session_id'],
                test_date=interaction['start_time'],
                query_id=f"transcript_{interaction['session_id']}",
                query_text=interaction['query'],
                category='transcript_query',
                complexity='unknown',
                approach=approach,
                
                # Performance (estimated)
                response_time_ms=0,  # Not available in transcripts
                success=True,  # Assume success if response exists
                
                # Input tokens
                input_tokens_user=usage.get('input_tokens', 0),
                input_tokens_context=0,
                input_tokens_tools=0,
                input_tokens_files=0,
                input_tokens_total=usage.get('input_tokens', 0),
                
                # Output tokens
                output_tokens_reasoning=0,
                output_tokens_tools=0,
                output_tokens_code=0,
                output_tokens_explanations=usage.get('output_tokens', 0),
                output_tokens_total=usage.get('output_tokens', 0),
                
                # Cache
                cache_read_tokens=usage.get('cache_read_input_tokens', 0),
                cache_creation_tokens=usage.get('cache_creation_input_tokens', 0),
                
                # Efficiency (calculated)
                tokens_per_result=usage.get('output_tokens', 0),
                context_utilization=0.5,  # Default estimate
                generation_efficiency=0.25,  # Default estimate
                
                # Tool usage (not available in transcripts)
                tool_call_count=0,
                tools_used=[],
                file_reads=[],
                file_writes=[],
                
                # Results
                accuracy_score=None,
                result_quality='transcript_response'
            )
            
        except Exception as e:
            print(f"❌ Error creating transcript result: {e}")
            return None
    
    def export_to_csv(self, output_file: str = "consolidated_performance_data.csv"):
        """Export consolidated data to CSV"""
        if not self.consolidated_data:
            print("⚠️  No data to export")
            return
            
        output_path = self.base_dir / output_file
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write header
            fields = list(asdict(self.consolidated_data[0]).keys())
            writer.writerow(fields)
            
            # Write data
            for result in self.consolidated_data:
                row = []
                for field in fields:
                    value = getattr(result, field)
                    if isinstance(value, list):
                        value = ','.join(str(v) for v in value)
                    row.append(value)
                writer.writerow(row)
        
        print(f"✅ Exported {len(self.consolidated_data)} records to {output_path}")
    
    def export_to_json(self, output_file: str = "consolidated_performance_data.json"):
        """Export consolidated data to JSON"""
        if not self.consolidated_data:
            print("⚠️  No data to export")
            return
            
        output_path = self.base_dir / output_file
        
        data = [asdict(result) for result in self.consolidated_data]
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"✅ Exported {len(self.consolidated_data)} records to {output_path}")
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate summary statistics from consolidated data"""
        if not self.consolidated_data:
            return {}
        
        # Separate data by approach
        mcp_data = [r for r in self.consolidated_data if r.approach == 'mcp']
        native_data = [r for r in self.consolidated_data if r.approach == 'native']
        
        # Calculate averages
        def safe_avg(values):
            return sum(values) / len(values) if values else 0
        
        mcp_response_times = [r.response_time_ms for r in mcp_data if r.response_time_ms > 0]
        native_response_times = [r.response_time_ms for r in native_data if r.response_time_ms > 0]
        
        # Count categories
        categories = {}
        complexities = {}
        for result in self.consolidated_data:
            categories[result.category] = categories.get(result.category, 0) + 1
            complexities[result.complexity] = complexities.get(result.complexity, 0) + 1
        
        summary = {
            'total_records': len(self.consolidated_data),
            'date_range': {
                'earliest': min(r.test_date for r in self.consolidated_data if r.test_date),
                'latest': max(r.test_date for r in self.consolidated_data if r.test_date)
            },
            'approaches': {
                'mcp_count': len(mcp_data),
                'native_count': len(native_data)
            },
            'performance_summary': {
                'mcp_avg_response_time': safe_avg(mcp_response_times),
                'native_avg_response_time': safe_avg(native_response_times),
                'mcp_success_rate': safe_avg([1 if r.success else 0 for r in mcp_data]),
                'native_success_rate': safe_avg([1 if r.success else 0 for r in native_data])
            },
            'token_summary': {
                'mcp_avg_input_tokens': safe_avg([r.input_tokens_total for r in mcp_data]),
                'native_avg_input_tokens': safe_avg([r.input_tokens_total for r in native_data]),
                'mcp_avg_output_tokens': safe_avg([r.output_tokens_total for r in mcp_data]),
                'native_avg_output_tokens': safe_avg([r.output_tokens_total for r in native_data])
            },
            'categories': categories,
            'complexity_distribution': complexities
        }
        
        return summary

def main():
    """Main consolidation process"""
    print("🚀 Starting Performance Data Consolidation")
    print("=" * 50)
    
    # Initialize consolidator
    consolidator = PerformanceDataConsolidator()
    
    # Collect all data
    results = consolidator.collect_all_data()
    
    if not results:
        print("❌ No performance data found to consolidate")
        return
    
    # Export to different formats
    print("\n📊 Exporting consolidated data...")
    consolidator.export_to_csv()
    consolidator.export_to_json()
    
    # Generate summary report
    print("\n📈 Generating summary report...")
    summary = consolidator.generate_summary_report()
    
    summary_path = Path("PathUtils.get_workspace_root()/consolidated_performance_summary.json")
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    print(f"✅ Summary report saved to {summary_path}")
    
    # Print key statistics
    print("\n🎯 Key Statistics:")
    print(f"   • Total Records: {summary['total_records']}")
    print(f"   • MCP Tests: {summary['approaches']['mcp_count']}")
    print(f"   • Native Tests: {summary['approaches']['native_count']}")
    
    if summary['performance_summary']['mcp_avg_response_time']:
        mcp_time = summary['performance_summary']['mcp_avg_response_time']
        native_time = summary['performance_summary']['native_avg_response_time']
        print(f"   • MCP Avg Response: {mcp_time:.1f}ms")
        print(f"   • Native Avg Response: {native_time:.1f}ms")
        
        if native_time > 0:
            improvement = ((native_time - mcp_time) / native_time) * 100
            print(f"   • Speed Difference: {improvement:+.1f}% (MCP vs Native)")
    
    print("\n✅ Consolidation complete!")
    print("📁 Output files:")
    print("   • consolidated_performance_data.csv")
    print("   • consolidated_performance_data.json")
    print("   • consolidated_performance_summary.json")

if __name__ == "__main__":
    main()