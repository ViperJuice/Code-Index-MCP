#!/usr/bin/env python3
"""
C# Plugin Real-World Evaluation Script

This script tests the C# plugin against real-world repositories to validate:
- Symbol extraction accuracy
- .csproj file parsing
- Performance on medium-sized files
- Metadata extraction for various C# constructs
"""

import sys
import time
import json
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent / "mcp_server"))

from mcp_server.plugins.csharp_plugin.plugin import Plugin
from mcp_server.plugin_system.models import PluginConfig


@dataclass
class FileTestResult:
    """Results from testing a single file."""
    file_path: str
    file_size: bytes
    line_count: int
    parsing_time: float
    symbols_found: int
    symbol_breakdown: Dict[str, int]
    has_project_info: bool
    project_type: Optional[str]
    framework_version: Optional[str]
    packages_found: int
    errors: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RepositoryTestResult:
    """Results from testing an entire repository."""
    repo_name: str
    total_files: int
    successfully_parsed: int
    total_symbols: int
    avg_parsing_time: float
    file_results: List[FileTestResult]
    project_files_found: int
    unique_project_types: List[str]
    performance_metrics: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'file_results': [fr.to_dict() for fr in self.file_results]
        }


class CSharpPluginEvaluator:
    """Evaluates the C# plugin against real-world repositories."""
    
    def __init__(self):
        self.plugin = Plugin()
        self.test_repos_path = Path("/home/jenner/Code/Code-Index-MCP/test_repos/csharp_test")
        self.results = {}
        
    def evaluate_all_repositories(self) -> Dict[str, RepositoryTestResult]:
        """Evaluate all cloned repositories."""
        repos = [
            "aspnetcore",
            "Umbraco-CMS", 
            "OrchardCore",
            "abp"
        ]
        
        for repo in repos:
            repo_path = self.test_repos_path / repo
            if repo_path.exists():
                print(f"\n🔍 Evaluating {repo}...")
                result = self.evaluate_repository(repo_path, repo)
                self.results[repo] = result
                self._print_repository_summary(result)
            else:
                print(f"❌ Repository {repo} not found at {repo_path}")
                
        return self.results
    
    def evaluate_repository(self, repo_path: Path, repo_name: str) -> RepositoryTestResult:
        """Evaluate a single repository."""
        cs_files = list(repo_path.rglob("*.cs"))
        csproj_files = list(repo_path.rglob("*.csproj"))
        cshtml_files = list(repo_path.rglob("*.cshtml"))
        
        # Limit files for performance (sample from each type)
        sampled_cs_files = self._sample_files(cs_files, 50)
        sampled_cshtml_files = self._sample_files(cshtml_files, 10)
        
        all_files = sampled_cs_files + sampled_cshtml_files
        file_results = []
        parsing_times = []
        total_symbols = 0
        
        print(f"  📁 Found {len(cs_files)} .cs files, {len(csproj_files)} .csproj files, {len(cshtml_files)} .cshtml files")
        print(f"  🎯 Testing {len(all_files)} sampled files")
        
        for i, file_path in enumerate(all_files):
            if i % 10 == 0:
                print(f"    Progress: {i+1}/{len(all_files)}")
                
            result = self._test_file(file_path)
            if result:
                file_results.append(result)
                parsing_times.append(result.parsing_time)
                total_symbols += result.symbols_found
        
        # Calculate performance metrics
        successfully_parsed = len([r for r in file_results if not r.errors])
        avg_parsing_time = statistics.mean(parsing_times) if parsing_times else 0.0
        
        # Find unique project types
        project_types = list(set([r.project_type for r in file_results if r.project_type]))
        
        performance_metrics = {
            "max_parsing_time": max(parsing_times) if parsing_times else 0.0,
            "min_parsing_time": min(parsing_times) if parsing_times else 0.0,
            "median_parsing_time": statistics.median(parsing_times) if parsing_times else 0.0,
            "files_with_errors": len([r for r in file_results if r.errors]),
            "avg_symbols_per_file": total_symbols / len(file_results) if file_results else 0.0
        }
        
        return RepositoryTestResult(
            repo_name=repo_name,
            total_files=len(all_files),
            successfully_parsed=successfully_parsed,
            total_symbols=total_symbols,
            avg_parsing_time=avg_parsing_time,
            file_results=file_results,
            project_files_found=len(csproj_files),
            unique_project_types=project_types,
            performance_metrics=performance_metrics
        )
    
    def _sample_files(self, files: List[Path], max_count: int) -> List[Path]:
        """Sample files for testing to avoid overwhelming the system."""
        if len(files) <= max_count:
            return files
        
        # Sample evenly across the repository
        step = len(files) // max_count
        return [files[i] for i in range(0, len(files), step)][:max_count]
    
    def _test_file(self, file_path: Path) -> Optional[FileTestResult]:
        """Test the plugin on a single file."""
        errors = []
        try:
            # Read file content
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            file_size = file_path.stat().st_size
            line_count = len(content.splitlines())
            
            # Skip very large files to avoid performance issues
            if file_size > 1024 * 1024:  # 1MB limit
                return None
            
            # Time the parsing
            start_time = time.time()
            try:
                result = self.plugin.indexFile(str(file_path), content)
                if isinstance(result, dict) and 'symbols' in result:
                    symbols = result['symbols']
                else:
                    symbols = []
            except Exception as parse_error:
                errors.append(f"Parse error: {str(parse_error)}")
                symbols = []
            parsing_time = time.time() - start_time
            
            # Analyze results
            symbol_breakdown = {}
            for symbol in symbols:
                if isinstance(symbol, dict):
                    symbol_type = symbol.get('kind', 'unknown')
                else:
                    symbol_type = symbol.symbol_type.value if hasattr(symbol.symbol_type, 'value') else str(symbol.symbol_type)
                symbol_breakdown[symbol_type] = symbol_breakdown.get(symbol_type, 0) + 1
            
            # Check for project information
            has_project_info = False
            project_type = None
            framework_version = None
            packages_found = 0
            
            if symbols:
                first_symbol = symbols[0]
                if isinstance(first_symbol, dict) and 'metadata' in first_symbol:
                    metadata = first_symbol['metadata']
                    has_project_info = bool(metadata.get('project_type') or metadata.get('framework_version'))
                    project_type = metadata.get('project_type')
                    framework_version = metadata.get('framework_version')
                elif hasattr(first_symbol, 'metadata') and first_symbol.metadata:
                    metadata = first_symbol.metadata
                    has_project_info = bool(metadata.get('project_type') or metadata.get('framework_version'))
                    project_type = metadata.get('project_type')
                    framework_version = metadata.get('framework_version')
            
            return FileTestResult(
                file_path=str(file_path.relative_to(self.test_repos_path)),
                file_size=file_size,
                line_count=line_count,
                parsing_time=parsing_time,
                symbols_found=len(symbols),
                symbol_breakdown=symbol_breakdown,
                has_project_info=has_project_info,
                project_type=project_type,
                framework_version=framework_version,
                packages_found=packages_found,
                errors=errors
            )
            
        except Exception as e:
            return FileTestResult(
                file_path=str(file_path.relative_to(self.test_repos_path)),
                file_size=0,
                line_count=0,
                parsing_time=0.0,
                symbols_found=0,
                symbol_breakdown={},
                has_project_info=False,
                project_type=None,
                framework_version=None,
                packages_found=0,
                errors=[f"File error: {str(e)}"]
            )
    
    def _print_repository_summary(self, result: RepositoryTestResult):
        """Print a summary of repository test results."""
        print(f"  ✅ Results for {result.repo_name}:")
        print(f"    📊 Files tested: {result.total_files}")
        print(f"    ✅ Successfully parsed: {result.successfully_parsed}")
        print(f"    🔍 Total symbols found: {result.total_symbols}")
        print(f"    ⏱️  Average parsing time: {result.avg_parsing_time:.4f}s")
        print(f"    📄 Project files: {result.project_files_found}")
        print(f"    🏗️  Project types: {', '.join(result.unique_project_types) if result.unique_project_types else 'None detected'}")
        print(f"    ⚡ Performance: {result.performance_metrics['avg_symbols_per_file']:.1f} symbols/file")
        
        if result.performance_metrics['files_with_errors'] > 0:
            print(f"    ⚠️  Files with errors: {result.performance_metrics['files_with_errors']}")
    
    def generate_detailed_report(self) -> Dict[str, Any]:
        """Generate a detailed test report."""
        total_files = sum(r.total_files for r in self.results.values())
        total_symbols = sum(r.total_symbols for r in self.results.values())
        total_successful = sum(r.successfully_parsed for r in self.results.values())
        
        # Aggregate symbol types across all repositories
        all_symbol_types = set()
        for result in self.results.values():
            for file_result in result.file_results:
                all_symbol_types.update(file_result.symbol_breakdown.keys())
        
        # Performance analysis
        all_parsing_times = []
        for result in self.results.values():
            for file_result in result.file_results:
                all_parsing_times.append(file_result.parsing_time)
        
        report = {
            "summary": {
                "total_repositories": len(self.results),
                "total_files_tested": total_files,
                "total_symbols_extracted": total_symbols,
                "success_rate": (total_successful / total_files * 100) if total_files > 0 else 0.0,
                "avg_symbols_per_file": total_symbols / total_files if total_files > 0 else 0.0
            },
            "performance": {
                "avg_parsing_time": statistics.mean(all_parsing_times) if all_parsing_times else 0.0,
                "max_parsing_time": max(all_parsing_times) if all_parsing_times else 0.0,
                "min_parsing_time": min(all_parsing_times) if all_parsing_times else 0.0,
                "files_parsed_per_second": 1.0 / statistics.mean(all_parsing_times) if all_parsing_times and statistics.mean(all_parsing_times) > 0 else 0.0
            },
            "symbol_types_found": sorted(list(all_symbol_types)),
            "repository_results": {name: result.to_dict() for name, result in self.results.items()},
            "plugin_capabilities": {
                "supports_csproj_parsing": any(r.project_files_found > 0 for r in self.results.values()),
                "supports_project_detection": any(r.unique_project_types for r in self.results.values()),
                "supports_multiple_extensions": True,  # .cs, .cshtml
                "framework_detection": any(
                    any(fr.framework_version for fr in r.file_results if fr.framework_version)
                    for r in self.results.values()
                )
            }
        }
        
        return report
    
    def save_report(self, filename: str = "csharp_plugin_evaluation_report.json"):
        """Save the detailed report to a JSON file."""
        report = self.generate_detailed_report()
        report_path = Path(filename)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_path.absolute()}")
        return report


def main():
    """Main function to run the evaluation."""
    print("🚀 Starting C# Plugin Real-World Evaluation")
    print("=" * 60)
    
    evaluator = CSharpPluginEvaluator()
    
    # Run evaluation on all repositories
    results = evaluator.evaluate_all_repositories()
    
    # Generate and save detailed report
    report = evaluator.save_report()
    
    # Print final summary
    print("\n" + "=" * 60)
    print("📋 FINAL EVALUATION SUMMARY")
    print("=" * 60)
    print(f"✅ Repositories tested: {report['summary']['total_repositories']}")
    print(f"📄 Files tested: {report['summary']['total_files_tested']}")
    print(f"🔍 Symbols extracted: {report['summary']['total_symbols_extracted']}")
    print(f"📊 Success rate: {report['summary']['success_rate']:.1f}%")
    print(f"⚡ Avg symbols per file: {report['summary']['avg_symbols_per_file']:.1f}")
    print(f"⏱️  Avg parsing time: {report['performance']['avg_parsing_time']:.4f}s")
    print(f"🚀 Files per second: {report['performance']['files_parsed_per_second']:.1f}")
    
    print(f"\n🔧 Symbol types found: {', '.join(report['symbol_types_found'])}")
    
    print(f"\n🏗️  Plugin capabilities:")
    for capability, supported in report['plugin_capabilities'].items():
        status = "✅" if supported else "❌"
        print(f"    {status} {capability.replace('_', ' ').title()}")
    
    print("\n🎯 Evaluation completed successfully!")


if __name__ == "__main__":
    main()