#!/usr/bin/env python3
"""
Test Progress Dashboard - Visual overview of test execution status.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import sys


class TestProgressDashboard:
    def __init__(self):
        self.test_dir = Path("test_results/performance_tests")
        self.results_dir = self.test_dir / "results"
        
    def get_batch_progress(self, batch_name: str) -> Tuple[int, int]:
        """Get completed and total tests for a batch."""
        # Find batch file
        batch_files = list(self.test_dir.glob(f"test_batch_{batch_name}_*.json"))
        if not batch_files:
            return 0, 0
            
        with open(batch_files[0], 'r') as f:
            batch_data = json.load(f)
            total = batch_data['test_count']
            
        # Check checkpoint
        checkpoint_file = self.results_dir / f"checkpoint_{batch_name}.json"
        completed = 0
        
        if checkpoint_file.exists():
            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                completed = len(checkpoint.get('completed', []))
                
        return completed, total
        
    def create_progress_bar(self, completed: int, total: int, width: int = 30) -> str:
        """Create a text progress bar."""
        if total == 0:
            return "[" + " " * width + "]"
            
        filled = int(width * completed / total)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}]"
        
    def format_time_estimate(self, completed: int, total: int, avg_time_minutes: float = 5) -> str:
        """Estimate remaining time based on average test time."""
        remaining = total - completed
        if remaining == 0:
            return "Complete!"
            
        total_minutes = remaining * avg_time_minutes
        hours = int(total_minutes // 60)
        minutes = int(total_minutes % 60)
        
        if hours > 0:
            return f"~{hours}h {minutes}m remaining"
        else:
            return f"~{minutes}m remaining"
            
    def display_dashboard(self):
        """Display the test progress dashboard."""
        print("\n" + "="*70)
        print(" "*20 + "TEST PROGRESS DASHBOARD")
        print("="*70)
        print(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        repositories = ['go_gin', 'python_django', 'javascript_react', 'rust_tokio']
        
        total_completed = 0
        total_tests = 0
        
        print("Repository Progress:")
        print("-" * 70)
        
        for repo in repositories:
            completed, total = self.get_batch_progress(repo)
            total_completed += completed
            total_tests += total
            
            if total > 0:
                percentage = completed / total * 100
                progress_bar = self.create_progress_bar(completed, total)
                time_est = self.format_time_estimate(completed, total)
                
                # Language emoji mapping
                emoji_map = {
                    'go_gin': '🔵',
                    'python_django': '🐍',
                    'javascript_react': '📜',
                    'rust_tokio': '🦀'
                }
                emoji = emoji_map.get(repo, '📁')
                
                print(f"\n{emoji} {repo:20} {progress_bar} {completed:2d}/{total:2d} ({percentage:5.1f}%)")
                print(f"   {' '*20} {time_est}")
                
                # Show recent completions
                result_files = list(self.results_dir.glob(f"result_{repo}_*.json"))
                if result_files:
                    recent_files = sorted(result_files, key=lambda x: x.stat().st_mtime, reverse=True)[:2]
                    print(f"   Recent: ", end="")
                    for rf in recent_files:
                        with open(rf, 'r') as f:
                            data = json.load(f)
                            test_id = data.get('test_id', 'unknown').split('_')[-1]
                            status = "✓" if data.get('success', False) else "✗"
                            print(f"{test_id}({status}) ", end="")
                    print()
                    
        print("\n" + "-" * 70)
        overall_percentage = total_completed / total_tests * 100 if total_tests > 0 else 0
        overall_bar = self.create_progress_bar(total_completed, total_tests, width=40)
        
        print(f"\nOVERALL PROGRESS: {overall_bar}")
        print(f"                  {total_completed}/{total_tests} tests completed ({overall_percentage:.1f}%)")
        
        # Performance summary if we have results
        all_results = []
        for result_file in self.results_dir.glob("result_*.json"):
            with open(result_file, 'r') as f:
                all_results.append(json.load(f))
                
        if all_results:
            print("\n" + "-" * 70)
            print("\nPERFORMANCE SUMMARY:")
            
            mcp_results = [r for r in all_results if r.get('mode') == 'mcp']
            native_results = [r for r in all_results if r.get('mode') == 'native']
            
            if mcp_results:
                avg_mcp_time = sum(r.get('execution_time_ms', 0) for r in mcp_results) / len(mcp_results)
                avg_mcp_tokens = sum(r.get('token_estimate', 0) for r in mcp_results) / len(mcp_results)
                mcp_success = sum(1 for r in mcp_results if r.get('success', False))
                
                print(f"\n🔷 MCP Mode ({len(mcp_results)} tests):")
                print(f"   Average Time: {avg_mcp_time:,.0f}ms")
                print(f"   Average Tokens: {avg_mcp_tokens:,.0f}")
                print(f"   Success Rate: {mcp_success}/{len(mcp_results)} ({mcp_success/len(mcp_results)*100:.0f}%)")
                
            if native_results:
                avg_native_time = sum(r.get('execution_time_ms', 0) for r in native_results) / len(native_results)
                avg_native_tokens = sum(r.get('token_estimate', 0) for r in native_results) / len(native_results)
                native_success = sum(1 for r in native_results if r.get('success', False))
                
                print(f"\n🔶 Native Mode ({len(native_results)} tests):")
                print(f"   Average Time: {avg_native_time:,.0f}ms")
                print(f"   Average Tokens: {avg_native_tokens:,.0f}")
                print(f"   Success Rate: {native_success}/{len(native_results)} ({native_success/len(native_results)*100:.0f}%)")
                
            # Winner so far
            if mcp_results and native_results:
                print(f"\n🏆 Current Leader:")
                if avg_mcp_time < avg_native_time:
                    print(f"   Speed: MCP ({avg_native_time/avg_mcp_time:.1f}x faster)")
                else:
                    print(f"   Speed: Native ({avg_mcp_time/avg_native_time:.1f}x faster)")
                    
                if avg_mcp_tokens < avg_native_tokens:
                    print(f"   Efficiency: MCP ({(1-avg_mcp_tokens/avg_native_tokens)*100:.0f}% fewer tokens)")
                else:
                    print(f"   Efficiency: Native ({(1-avg_native_tokens/avg_mcp_tokens)*100:.0f}% fewer tokens)")
                    
        print("\n" + "="*70)
        
        # Next actions
        if total_completed < total_tests:
            print("\nNEXT STEPS:")
            for repo in repositories:
                completed, total = self.get_batch_progress(repo)
                if completed < total:
                    print(f"  python scripts/run_test_batch.py --next {repo}")
                    break
                    
        else:
            print("\n✅ ALL TESTS COMPLETE! Ready for analysis:")
            print("  python scripts/run_comprehensive_performance_test.py --analyze")
            print("  python scripts/create_performance_visualization.py")
            
        print()


def main():
    dashboard = TestProgressDashboard()
    dashboard.display_dashboard()
    
    # Check if watch mode requested
    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        import time
        while True:
            time.sleep(30)  # Update every 30 seconds
            print("\033[2J\033[H")  # Clear screen
            dashboard.display_dashboard()


if __name__ == "__main__":
    main()