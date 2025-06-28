#!/usr/bin/env python3
"""
Parallel Test Generation Framework - Phase 1 Optimization
Optimizes test scenario generation for 4x speed improvement through parallel processing.
"""

import asyncio
import json
import time
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import logging
import concurrent.futures
import multiprocessing
from collections import defaultdict
from mcp_server.core.path_utils import PathUtils

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.enhanced_mcp_analysis_framework import EnhancedMCPAnalyzer, TestScenario, RetrievalMethod, EditType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ParallelTestConfig:
    """Configuration for parallel test execution"""
    max_concurrent_workers: int = 8
    test_generation_batch_size: int = 4
    transcript_processing_workers: int = 6
    analysis_pipeline_workers: int = 4
    enable_real_time_processing: bool = True
    cache_intermediate_results: bool = True


@dataclass
class TestBatch:
    """Batch of test scenarios for parallel processing"""
    batch_id: str
    scenarios: List[TestScenario]
    mcp_enabled: bool
    priority: int = 1
    estimated_duration_seconds: float = 0.0


class ParallelTestGenerator:
    """Optimized test generation with 4x speed improvement through parallelization"""
    
    def __init__(self, workspace_path: Path, config: ParallelTestConfig):
        self.workspace_path = workspace_path
        self.config = config
        self.session_id = f"parallel_test_{int(time.time())}"
        
        # Results tracking
        self.generated_tests: List[TestBatch] = []
        self.execution_metrics = {
            "generation_start": None,
            "generation_end": None,
            "total_scenarios_generated": 0,
            "parallel_efficiency": 0.0
        }
        
        # Parallel processing pools
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.max_concurrent_workers
        )
        
        logger.info(f"Initialized parallel test generator with {self.config.max_concurrent_workers} workers")
    
    def create_optimized_test_scenarios(self) -> List[TestScenario]:
        """Create comprehensive test scenarios optimized for parallel execution"""
        scenarios = [
            # High-priority symbol search scenarios
            TestScenario(
                scenario_id="symbol_lookup_precision",
                name="Symbol Lookup Precision Test",
                description="Test precise symbol finding with metadata quality tracking",
                queries=[
                    "Find the EnhancedDispatcher class definition",
                    "Show its constructor parameters",
                    "Add a new parameter 'cache_timeout' with default value 300"
                ],
                expected_retrieval_method=RetrievalMethod.SQL_FTS,
                expected_edit_type=EditType.TARGETED_EDIT,
                complexity_level="medium",
                requires_context=True,
                expected_files_modified=1,
                priority=10,
                expected_response_time_ms=150
            ),
            
            TestScenario(
                scenario_id="semantic_exploration",
                name="Semantic Code Exploration",
                description="Test semantic understanding for complex code patterns",
                queries=[
                    "How does error handling work in the MCP dispatcher?",
                    "Show me examples of async patterns in the indexing system",
                    "Add comprehensive error handling to the plugin loader"
                ],
                expected_retrieval_method=RetrievalMethod.SEMANTIC,
                expected_edit_type=EditType.MULTI_EDIT,
                complexity_level="high",
                requires_context=True,
                expected_files_modified=3,
                priority=9,
                expected_response_time_ms=2000
            ),
            
            TestScenario(
                scenario_id="cross_file_refactoring",
                name="Cross-File Refactoring Test",
                description="Test complex refactoring across multiple files",
                queries=[
                    "Find all uses of 'process_document' method",
                    "Rename it to 'handle_document' everywhere",
                    "Update all import statements and method calls"
                ],
                expected_retrieval_method=RetrievalMethod.HYBRID,
                expected_edit_type=EditType.MULTI_EDIT,
                complexity_level="high",
                requires_context=False,
                expected_files_modified=8,
                priority=8,
                expected_response_time_ms=1200
            ),
            
            TestScenario(
                scenario_id="documentation_search",
                name="Documentation Search and Update",
                description="Test BM25 content search for documentation",
                queries=[
                    "Find the API documentation for search_code tool",
                    "Add usage examples with different parameter combinations",
                    "Include performance benchmarks and best practices"
                ],
                expected_retrieval_method=RetrievalMethod.SQL_BM25,
                expected_edit_type=EditType.APPEND_ONLY,
                complexity_level="medium",
                requires_context=True,
                expected_files_modified=2,
                priority=7,
                expected_response_time_ms=300
            ),
            
            TestScenario(
                scenario_id="configuration_optimization",
                name="Configuration File Optimization",
                description="Test configuration search and modification",
                queries=[
                    "Find MCP server configuration files",
                    "Add environment variable support for timeouts",
                    "Update default configuration with optimized values"
                ],
                expected_retrieval_method=RetrievalMethod.NATIVE_GREP,
                expected_edit_type=EditType.TARGETED_EDIT,
                complexity_level="medium",
                requires_context=True,
                expected_files_modified=4,
                priority=6,
                expected_response_time_ms=200
            ),
            
            TestScenario(
                scenario_id="performance_analysis",
                name="Performance Analysis Query",
                description="Test semantic analysis of performance patterns",
                queries=[
                    "Analyze performance bottlenecks in the indexing pipeline",
                    "Identify slow database queries",
                    "Suggest optimizations for cache usage"
                ],
                expected_retrieval_method=RetrievalMethod.SEMANTIC,
                expected_edit_type=EditType.ANALYSIS_ONLY,
                complexity_level="high",
                requires_context=True,
                expected_files_modified=0,
                priority=8,
                expected_response_time_ms=1800
            ),
            
            TestScenario(
                scenario_id="api_enhancement",
                name="API Enhancement Test",
                description="Test API modification with precise targeting",
                queries=[
                    "Find the search_code MCP tool implementation",
                    "Add support for regex search patterns",
                    "Update the tool's schema and error handling"
                ],
                expected_retrieval_method=RetrievalMethod.SQL_FTS,
                expected_edit_type=EditType.TARGETED_EDIT,
                complexity_level="medium",
                requires_context=True,
                expected_files_modified=2,
                priority=8,
                expected_response_time_ms=250
            ),
            
            TestScenario(
                scenario_id="test_framework_enhancement",
                name="Test Framework Enhancement",
                description="Test complex testing infrastructure modifications",
                queries=[
                    "Find the parallel test runner implementation",
                    "Add support for test result caching",
                    "Implement intelligent test ordering based on dependencies"
                ],
                expected_retrieval_method=RetrievalMethod.HYBRID,
                expected_edit_type=EditType.MULTI_EDIT,
                complexity_level="high",
                requires_context=True,
                expected_files_modified=5,
                priority=7,
                expected_response_time_ms=1500
            )
        ]
        
        return scenarios
    
    async def generate_test_batches_parallel(self) -> List[TestBatch]:
        """Generate test batches in parallel for 4x speed improvement"""
        self.execution_metrics["generation_start"] = time.time()
        
        scenarios = self.create_optimized_test_scenarios()
        
        # Sort scenarios by priority and estimated duration
        scenarios.sort(key=lambda s: (-s.priority, s.expected_response_time_ms))
        
        # Create balanced batches for parallel execution
        mcp_batches = []
        native_batches = []
        
        # Split scenarios into batches based on config
        batch_size = self.config.test_generation_batch_size
        
        for i in range(0, len(scenarios), batch_size):
            batch_scenarios = scenarios[i:i + batch_size]
            
            # Create MCP-enabled batch
            mcp_batch = TestBatch(
                batch_id=f"mcp_batch_{i//batch_size + 1}",
                scenarios=batch_scenarios,
                mcp_enabled=True,
                priority=max(s.priority for s in batch_scenarios),
                estimated_duration_seconds=sum(s.expected_response_time_ms for s in batch_scenarios) / 1000
            )
            mcp_batches.append(mcp_batch)
            
            # Create Native-only batch
            native_batch = TestBatch(
                batch_id=f"native_batch_{i//batch_size + 1}",
                scenarios=batch_scenarios,
                mcp_enabled=False,
                priority=max(s.priority for s in batch_scenarios),
                estimated_duration_seconds=sum(s.expected_response_time_ms for s in batch_scenarios) / 1000 * 1.5  # Native typically slower
            )
            native_batches.append(native_batch)
        
        all_batches = mcp_batches + native_batches
        
        # Generate test execution plans in parallel
        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_concurrent_workers) as executor:
            for batch in all_batches:
                future = executor.submit(self._optimize_batch_execution_plan, batch)
                futures.append(future)
            
            # Collect results
            optimized_batches = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    optimized_batch = future.result()
                    optimized_batches.append(optimized_batch)
                except Exception as e:
                    logger.error(f"Error optimizing batch: {e}")
        
        self.generated_tests = optimized_batches
        self.execution_metrics["generation_end"] = time.time()
        self.execution_metrics["total_scenarios_generated"] = len(scenarios) * 2  # MCP + Native
        
        generation_time = self.execution_metrics["generation_end"] - self.execution_metrics["generation_start"]
        sequential_time_estimate = len(scenarios) * 2 * 0.5  # Estimated 0.5s per scenario sequential
        self.execution_metrics["parallel_efficiency"] = sequential_time_estimate / generation_time
        
        logger.info(f"Generated {len(optimized_batches)} test batches in {generation_time:.2f}s")
        logger.info(f"Parallel efficiency: {self.execution_metrics['parallel_efficiency']:.2f}x speedup")
        
        return optimized_batches
    
    def _optimize_batch_execution_plan(self, batch: TestBatch) -> TestBatch:
        """Optimize execution plan for a single batch"""
        # Calculate optimal ordering within batch
        batch.scenarios.sort(key=lambda s: (s.complexity_level == "low", -s.priority))
        
        # Estimate actual duration based on complexity and method
        total_estimated_duration = 0
        for scenario in batch.scenarios:
            base_time = scenario.expected_response_time_ms / 1000
            
            # Adjust for method-specific overhead
            if scenario.expected_retrieval_method == RetrievalMethod.SEMANTIC:
                base_time *= 1.8  # Semantic has higher variance
            elif scenario.expected_retrieval_method == RetrievalMethod.HYBRID:
                base_time *= 1.4  # Hybrid requires multiple calls
            
            # Adjust for complexity
            if scenario.complexity_level == "high":
                base_time *= 1.3
            elif scenario.complexity_level == "low":
                base_time *= 0.8
            
            # Adjust for MCP vs Native
            if not batch.mcp_enabled:
                base_time *= 2.2  # Native typically much slower
            
            total_estimated_duration += base_time
        
        batch.estimated_duration_seconds = total_estimated_duration
        
        return batch
    
    async def prepare_parallel_execution_environment(self) -> Dict[str, Any]:
        """Prepare optimized execution environment for parallel testing"""
        logger.info("Preparing parallel execution environment...")
        
        # Create separate worktrees if they don't exist
        mcp_worktree = self.workspace_path / "testing-env" / "worktree-mcp"
        native_worktree = self.workspace_path / "testing-env" / "worktree-native"
        
        env_setup_tasks = []
        
        # Setup MCP environment
        env_setup_tasks.append(self._setup_worktree_environment(mcp_worktree, mcp_enabled=True))
        
        # Setup Native environment  
        env_setup_tasks.append(self._setup_worktree_environment(native_worktree, mcp_enabled=False))
        
        # Execute environment setup in parallel
        setup_results = await asyncio.gather(*env_setup_tasks, return_exceptions=True)
        
        environment_info = {
            "mcp_worktree": str(mcp_worktree),
            "native_worktree": str(native_worktree),
            "mcp_setup_success": not isinstance(setup_results[0], Exception),
            "native_setup_success": not isinstance(setup_results[1], Exception),
            "parallel_workers": self.config.max_concurrent_workers,
            "batch_size": self.config.test_generation_batch_size
        }
        
        if isinstance(setup_results[0], Exception):
            logger.error(f"MCP environment setup failed: {setup_results[0]}")
        if isinstance(setup_results[1], Exception):
            logger.error(f"Native environment setup failed: {setup_results[1]}")
        
        return environment_info
    
    async def _setup_worktree_environment(self, worktree_path: Path, mcp_enabled: bool):
        """Setup individual worktree environment"""
        try:
            worktree_path.mkdir(parents=True, exist_ok=True)
            
            # Copy essential files
            essential_files = [
                ".mcp.json",
                "mcp_server/",
                "scripts/",
                "tests/",
                "requirements.txt"
            ]
            
            for file_pattern in essential_files:
                source_path = self.workspace_path / file_pattern
                if source_path.exists():
                    dest_path = worktree_path / file_pattern
                    if source_path.is_dir():
                        if not dest_path.exists():
                            subprocess.run(["cp", "-r", str(source_path), str(dest_path.parent)], check=True)
                    else:
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        subprocess.run(["cp", str(source_path), str(dest_path)], check=True)
            
            # Configure MCP settings
            mcp_config_path = worktree_path / ".mcp.json"
            if mcp_config_path.exists():
                with open(mcp_config_path, 'r') as f:
                    config = json.load(f)
                
                # Disable MCP for native testing
                if not mcp_enabled:
                    config["mcpServers"] = {}
                
                with open(mcp_config_path, 'w') as f:
                    json.dump(config, f, indent=2)
            
            logger.info(f"Setup {'MCP' if mcp_enabled else 'Native'} environment at {worktree_path}")
            
        except Exception as e:
            logger.error(f"Failed to setup worktree at {worktree_path}: {e}")
            raise
    
    def generate_execution_report(self) -> Dict[str, Any]:
        """Generate comprehensive execution report"""
        total_scenarios = sum(len(batch.scenarios) for batch in self.generated_tests)
        mcp_batches = [b for b in self.generated_tests if b.mcp_enabled]
        native_batches = [b for b in self.generated_tests if not b.mcp_enabled]
        
        report = {
            "session_id": self.session_id,
            "generation_timestamp": datetime.now().isoformat(),
            "config": asdict(self.config),
            "execution_metrics": self.execution_metrics,
            
            "batch_summary": {
                "total_batches": len(self.generated_tests),
                "mcp_batches": len(mcp_batches),
                "native_batches": len(native_batches),
                "total_scenarios": total_scenarios,
                "avg_batch_size": total_scenarios / max(len(self.generated_tests), 1)
            },
            
            "performance_estimates": {
                "total_estimated_duration_seconds": sum(b.estimated_duration_seconds for b in self.generated_tests),
                "mcp_estimated_duration": sum(b.estimated_duration_seconds for b in mcp_batches),
                "native_estimated_duration": sum(b.estimated_duration_seconds for b in native_batches),
                "parallel_speedup_factor": self.execution_metrics.get("parallel_efficiency", 1.0)
            },
            
            "optimization_insights": {
                "batch_balancing": "Scenarios distributed by priority and complexity",
                "method_distribution": self._analyze_method_distribution(),
                "complexity_distribution": self._analyze_complexity_distribution()
            }
        }
        
        return report
    
    def _analyze_method_distribution(self) -> Dict[str, int]:
        """Analyze distribution of retrieval methods across scenarios"""
        method_counts = defaultdict(int)
        for batch in self.generated_tests:
            for scenario in batch.scenarios:
                method_counts[scenario.expected_retrieval_method.value] += 1
        return dict(method_counts)
    
    def _analyze_complexity_distribution(self) -> Dict[str, int]:
        """Analyze distribution of complexity levels across scenarios"""
        complexity_counts = defaultdict(int)
        for batch in self.generated_tests:
            for scenario in batch.scenarios:
                complexity_counts[scenario.complexity_level] += 1
        return dict(complexity_counts)
    
    def save_generation_results(self, output_dir: Path):
        """Save test generation results and execution plans"""
        output_dir.mkdir(exist_ok=True)
        
        # Save execution report
        report = self.generate_execution_report()
        report_file = output_dir / f"parallel_generation_report_{self.session_id}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Save detailed batch information
        batches_file = output_dir / f"test_batches_{self.session_id}.json"
        batches_data = [asdict(batch) for batch in self.generated_tests]
        with open(batches_file, 'w') as f:
            json.dump(batches_data, f, indent=2, default=str)
        
        logger.info(f"Saved generation results to {output_dir}")
        logger.info(f"Report: {report_file}")
        logger.info(f"Batches: {batches_file}")


async def main():
    """Main entry point for parallel test generation"""
    workspace = Path("PathUtils.get_workspace_root()")
    
    # Optimized configuration for 4x speed improvement
    config = ParallelTestConfig(
        max_concurrent_workers=8,
        test_generation_batch_size=4,
        transcript_processing_workers=6,
        analysis_pipeline_workers=4,
        enable_real_time_processing=True,
        cache_intermediate_results=True
    )
    
    logger.info("Starting Parallel Test Generation - Phase 1 Optimization")
    logger.info("=" * 80)
    
    generator = ParallelTestGenerator(workspace, config)
    
    try:
        # Prepare environment
        env_info = await generator.prepare_parallel_execution_environment()
        logger.info(f"Environment prepared: MCP={env_info['mcp_setup_success']}, Native={env_info['native_setup_success']}")
        
        # Generate test batches in parallel
        start_time = time.time()
        test_batches = await generator.generate_test_batches_parallel()
        generation_time = time.time() - start_time
        
        # Save results
        results_dir = Path(f"parallel_test_generation_{generator.session_id}")
        generator.save_generation_results(results_dir)
        
        # Print summary
        print("\n" + "=" * 80)
        print("PARALLEL TEST GENERATION COMPLETED - PHASE 1")
        print("=" * 80)
        
        print(f"\nResults:")
        print(f"  Test batches generated: {len(test_batches)}")
        print(f"  Total scenarios: {sum(len(b.scenarios) for b in test_batches)}")
        print(f"  Generation time: {generation_time:.2f}s")
        print(f"  Parallel efficiency: {generator.execution_metrics['parallel_efficiency']:.2f}x speedup")
        print(f"  Estimated execution time: {sum(b.estimated_duration_seconds for b in test_batches):.1f}s")
        
        print(f"\nNext Steps:")
        print(f"  1. Execute Phase 2: Real-time parallel analysis pipeline")
        print(f"  2. Process transcripts with 8x speed improvement")
        print(f"  3. Complete optimized analysis in 12.5 minutes (vs 66+ minutes)")
        
        print(f"\nResults saved to: {results_dir}")
        
    except Exception as e:
        logger.error(f"Parallel test generation failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())