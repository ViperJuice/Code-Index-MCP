#!/usr/bin/env python3
"""
Parallel Claude Code Integration - Phase 3 Optimization
Integrates parallelized transcript processing with Claude Code session analysis.
"""

import asyncio
import json
import time
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass, asdict
import logging
import concurrent.futures
import multiprocessing
from collections import defaultdict
import uuid
from mcp_server.core.path_utils import PathUtils

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.parallel_test_generator import ParallelTestGenerator, ParallelTestConfig, TestBatch
from scripts.realtime_parallel_analyzer import ParallelAnalysisPipeline, RealTimeAnalysisConfig
from scripts.enhanced_mcp_analysis_framework import EnhancedMCPAnalyzer, RetrievalMethod
from scripts.mcp_method_detector import MCPServerMonitor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ClaudeSessionConfig:
    """Configuration for Claude Code session integration"""
    claude_timeout_seconds: int = 120
    max_concurrent_sessions: int = 4
    session_retry_attempts: int = 3
    capture_full_transcripts: bool = True
    enable_method_monitoring: bool = True
    real_time_analysis: bool = True


@dataclass
class SessionResult:
    """Result from a Claude Code session"""
    session_id: str
    batch_id: str
    scenario_id: str
    source_type: str  # "mcp" or "native"
    start_time: datetime
    end_time: datetime
    success: bool
    transcript_content: str
    error_message: Optional[str] = None
    method_usage: Dict[str, Any] = None
    performance_metrics: Dict[str, Any] = None


class ClaudeCodeSessionManager:
    """Manages parallel Claude Code sessions with integrated analysis"""
    
    def __init__(self, workspace_path: Path, session_config: ClaudeSessionConfig):
        self.workspace_path = workspace_path
        self.config = session_config
        self.session_id = f"claude_integration_{int(time.time())}"
        
        # Session tracking
        self.active_sessions: Dict[str, subprocess.Popen] = {}
        self.session_results: List[SessionResult] = []
        self.method_monitors: Dict[str, MCPServerMonitor] = {}
        
        # Performance tracking
        self.execution_metrics = {
            "total_sessions_started": 0,
            "successful_sessions": 0,
            "failed_sessions": 0,
            "avg_session_duration": 0.0,
            "parallel_efficiency": 0.0
        }
        
        logger.info(f"Initialized Claude Code session manager for session {self.session_id}")
    
    async def execute_test_batch_parallel(self, batch: TestBatch) -> List[SessionResult]:
        """Execute test batch with parallel Claude Code sessions"""
        logger.info(f"Executing batch {batch.batch_id} with {len(batch.scenarios)} scenarios")
        
        batch_results = []
        semaphore = asyncio.Semaphore(self.config.max_concurrent_sessions)
        
        async def execute_scenario_with_semaphore(scenario):
            async with semaphore:
                return await self._execute_scenario_session(scenario, batch)
        
        # Create tasks for all scenarios in batch
        tasks = []
        for scenario in batch.scenarios:
            task = asyncio.create_task(execute_scenario_with_semaphore(scenario))
            tasks.append(task)
        
        # Execute all scenarios concurrently
        for completed_task in asyncio.as_completed(tasks):
            try:
                result = await completed_task
                batch_results.append(result)
                self.session_results.append(result)
                
                # Update metrics
                self.execution_metrics["total_sessions_started"] += 1
                if result.success:
                    self.execution_metrics["successful_sessions"] += 1
                else:
                    self.execution_metrics["failed_sessions"] += 1
                
                logger.info(f"Completed scenario {result.scenario_id}: {'SUCCESS' if result.success else 'FAILED'}")
                
            except Exception as e:
                logger.error(f"Error in scenario execution: {e}")
                self.execution_metrics["failed_sessions"] += 1
        
        return batch_results
    
    async def _execute_scenario_session(self, scenario, batch: TestBatch) -> SessionResult:
        """Execute a single scenario with Claude Code"""
        session_id = f"{self.session_id}_{batch.batch_id}_{scenario.scenario_id}"
        start_time = datetime.now()
        
        # Start method monitoring if enabled
        if self.config.enable_method_monitoring and batch.mcp_enabled:
            monitor = MCPServerMonitor(self.workspace_path)
            monitor.start_monitoring(session_id)
            self.method_monitors[session_id] = monitor
        
        try:
            # Prepare session environment
            worktree_path = await self._prepare_session_environment(batch.mcp_enabled)
            
            # Execute all queries in scenario
            full_transcript = ""
            for i, query in enumerate(scenario.queries):
                logger.info(f"Executing query {i+1}/{len(scenario.queries)}: {query[:50]}...")
                
                transcript_chunk = await self._execute_claude_query(
                    query, worktree_path, batch.mcp_enabled, session_id
                )
                full_transcript += f"\n--- Query {i+1} ---\n{transcript_chunk}\n"
                
                # Small delay between queries
                await asyncio.sleep(1.0)
            
            end_time = datetime.now()
            
            # Stop method monitoring
            method_usage = {}
            if session_id in self.method_monitors:
                self.method_monitors[session_id].stop_monitoring()
                method_usage = self.method_monitors[session_id].get_session_summary(session_id)
            
            # Calculate performance metrics
            duration = (end_time - start_time).total_seconds()
            performance_metrics = {
                "duration_seconds": duration,
                "queries_executed": len(scenario.queries),
                "avg_query_time": duration / len(scenario.queries),
                "transcript_length": len(full_transcript)
            }
            
            result = SessionResult(
                session_id=session_id,
                batch_id=batch.batch_id,
                scenario_id=scenario.scenario_id,
                source_type="mcp" if batch.mcp_enabled else "native",
                start_time=start_time,
                end_time=end_time,
                success=True,
                transcript_content=full_transcript,
                method_usage=method_usage,
                performance_metrics=performance_metrics
            )
            
            return result
            
        except Exception as e:
            end_time = datetime.now()
            
            # Stop monitoring on error
            if session_id in self.method_monitors:
                self.method_monitors[session_id].stop_monitoring()
            
            result = SessionResult(
                session_id=session_id,
                batch_id=batch.batch_id,
                scenario_id=scenario.scenario_id,
                source_type="mcp" if batch.mcp_enabled else "native",
                start_time=start_time,
                end_time=end_time,
                success=False,
                transcript_content="",
                error_message=str(e)
            )
            
            logger.error(f"Session {session_id} failed: {e}")
            return result
    
    async def _prepare_session_environment(self, mcp_enabled: bool) -> Path:
        """Prepare environment for Claude Code session"""
        if mcp_enabled:
            worktree_path = self.workspace_path / "testing-env" / "worktree-mcp"
        else:
            worktree_path = self.workspace_path / "testing-env" / "worktree-native"
        
        # Ensure worktree exists
        if not worktree_path.exists():
            logger.warning(f"Worktree {worktree_path} does not exist, using main workspace")
            return self.workspace_path
        
        return worktree_path
    
    async def _execute_claude_query(self, query: str, worktree_path: Path, 
                                  mcp_enabled: bool, session_id: str) -> str:
        """Execute a single Claude Code query"""
        
        # Create unique temporary transcript file
        transcript_file = Path(f"/tmp/claude_transcript_{session_id}_{uuid.uuid4().hex[:8]}.txt")
        
        cmd = [
            "claude",
            "--",
            query
        ]
        
        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(worktree_path),
            "MCP_ENABLED": "true" if mcp_enabled else "false",
            "CLAUDE_TRANSCRIPT_FILE": str(transcript_file)
        }
        
        try:
            # Execute with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=worktree_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.claude_timeout_seconds
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise TimeoutError(f"Claude query timed out after {self.config.claude_timeout_seconds}s")
            
            # Combine output
            transcript = f"STDOUT:\n{stdout.decode('utf-8')}\n\nSTDERR:\n{stderr.decode('utf-8')}"
            
            # Try to read transcript file if it exists
            if transcript_file.exists():
                try:
                    with open(transcript_file, 'r') as f:
                        file_transcript = f.read()
                    transcript += f"\n\nTRANSCRIPT FILE:\n{file_transcript}"
                    transcript_file.unlink()  # Clean up
                except Exception as e:
                    logger.debug(f"Could not read transcript file: {e}")
            
            return transcript
            
        except Exception as e:
            logger.error(f"Error executing Claude query: {e}")
            raise


class IntegratedParallelOrchestrator:
    """Orchestrates the complete parallelized MCP analysis workflow"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.session_id = f"integrated_parallel_{int(time.time())}"
        
        # Component configurations
        self.test_config = ParallelTestConfig(
            max_concurrent_workers=8,
            test_generation_batch_size=4,
            transcript_processing_workers=6,
            analysis_pipeline_workers=4,
            enable_real_time_processing=True,
            cache_intermediate_results=True
        )
        
        self.analysis_config = RealTimeAnalysisConfig(
            max_concurrent_analyzers=8,
            transcript_buffer_size=100,
            analysis_batch_size=16,
            streaming_enabled=True,
            real_time_reporting=True,
            cache_analysis_results=True,
            performance_monitoring=True
        )
        
        self.claude_config = ClaudeSessionConfig(
            claude_timeout_seconds=120,
            max_concurrent_sessions=4,
            session_retry_attempts=3,
            capture_full_transcripts=True,
            enable_method_monitoring=True,
            real_time_analysis=True
        )
        
        # Initialize components
        self.test_generator = ParallelTestGenerator(workspace_path, self.test_config)
        self.analysis_pipeline = ParallelAnalysisPipeline(workspace_path, self.analysis_config)
        self.session_manager = ClaudeCodeSessionManager(workspace_path, self.claude_config)
        
        # Results directories
        self.results_dir = Path(f"integrated_parallel_analysis_{self.session_id}")
        self.transcripts_dir = self.results_dir / "transcripts"
        
        # Create directories
        self.results_dir.mkdir(exist_ok=True)
        self.transcripts_dir.mkdir(exist_ok=True)
        
        logger.info(f"Initialized integrated parallel orchestrator for session {self.session_id}")
    
    async def execute_complete_analysis(self) -> Dict[str, Any]:
        """Execute complete parallelized MCP analysis workflow"""
        logger.info("Starting Complete Integrated Parallel Analysis")
        logger.info("=" * 80)
        
        workflow_start = time.time()
        workflow_results = {
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "phases": {}
        }
        
        try:
            # Phase 1: Generate test batches (4x speedup)
            logger.info("\n🔄 Phase 1: Parallel Test Generation")
            phase1_start = time.time()
            
            await self.test_generator.prepare_parallel_execution_environment()
            test_batches = await self.test_generator.generate_test_batches_parallel()
            
            phase1_time = time.time() - phase1_start
            workflow_results["phases"]["test_generation"] = {
                "duration_seconds": phase1_time,
                "batches_generated": len(test_batches),
                "parallel_efficiency": self.test_generator.execution_metrics.get("parallel_efficiency", 1.0)
            }
            
            logger.info(f"✅ Phase 1 completed in {phase1_time:.2f}s with {len(test_batches)} batches")
            
            # Phase 2: Execute Claude Code sessions in parallel
            logger.info("\n🔄 Phase 2: Parallel Claude Code Execution")
            phase2_start = time.time()
            
            all_session_results = []
            
            # Execute batches with controlled parallelism
            semaphore = asyncio.Semaphore(2)  # Limit concurrent batches to avoid overload
            
            async def execute_batch_with_semaphore(batch):
                async with semaphore:
                    return await self.session_manager.execute_test_batch_parallel(batch)
            
            batch_tasks = []
            for batch in test_batches:
                task = asyncio.create_task(execute_batch_with_semaphore(batch))
                batch_tasks.append(task)
            
            # Collect results as they complete
            for completed_task in asyncio.as_completed(batch_tasks):
                batch_results = await completed_task
                all_session_results.extend(batch_results)
                
                # Save intermediate transcripts
                await self._save_session_transcripts(batch_results)
                
                logger.info(f"Completed batch with {len(batch_results)} sessions")
            
            phase2_time = time.time() - phase2_start
            workflow_results["phases"]["claude_execution"] = {
                "duration_seconds": phase2_time,
                "total_sessions": len(all_session_results),
                "successful_sessions": sum(1 for r in all_session_results if r.success),
                "session_metrics": self.session_manager.execution_metrics
            }
            
            logger.info(f"✅ Phase 2 completed in {phase2_time:.2f}s with {len(all_session_results)} sessions")
            
            # Phase 3: Real-time parallel analysis (8x speedup)
            logger.info("\n🔄 Phase 3: Real-time Parallel Analysis")
            phase3_start = time.time()
            
            # Process transcripts in real-time
            analysis_results = []
            async for result in self.analysis_pipeline.process_transcript_directory(self.transcripts_dir):
                analysis_results.append(result)
                
                # Real-time progress reporting
                if len(analysis_results) % 10 == 0:
                    logger.info(f"Processed {len(analysis_results)} transcripts...")
            
            phase3_time = time.time() - phase3_start
            workflow_results["phases"]["parallel_analysis"] = {
                "duration_seconds": phase3_time,
                "transcripts_analyzed": len(analysis_results),
                "parallel_efficiency": self.analysis_pipeline.performance_metrics.get("parallel_efficiency", 1.0),
                "analysis_summary": self.analysis_pipeline.aggregate_live_results()
            }
            
            logger.info(f"✅ Phase 3 completed in {phase3_time:.2f}s with {len(analysis_results)} analyses")
            
            # Calculate overall metrics
            total_time = time.time() - workflow_start
            estimated_sequential_time = len(test_batches) * 30 + len(all_session_results) * 10  # Conservative estimates
            overall_speedup = estimated_sequential_time / total_time
            
            workflow_results.update({
                "end_time": datetime.now().isoformat(),
                "total_duration_seconds": total_time,
                "estimated_sequential_time": estimated_sequential_time,
                "overall_speedup": overall_speedup,
                "time_reduction_percent": (1 - total_time / estimated_sequential_time) * 100
            })
            
            # Save comprehensive results
            await self._save_comprehensive_results(workflow_results)
            
            return workflow_results
            
        except Exception as e:
            logger.error(f"Integrated analysis workflow failed: {e}")
            workflow_results["error"] = str(e)
            workflow_results["end_time"] = datetime.now().isoformat()
            workflow_results["total_duration_seconds"] = time.time() - workflow_start
            raise
    
    async def _save_session_transcripts(self, session_results: List[SessionResult]):
        """Save session transcripts for analysis"""
        for result in session_results:
            if result.transcript_content:
                transcript_file = self.transcripts_dir / f"{result.session_id}.json"
                
                transcript_data = {
                    "session_id": result.session_id,
                    "scenario_id": result.scenario_id,
                    "source_type": result.source_type,
                    "timestamp": result.start_time.isoformat(),
                    "success": result.success,
                    "transcript": result.transcript_content,
                    "method_usage": result.method_usage,
                    "performance_metrics": result.performance_metrics
                }
                
                with open(transcript_file, 'w') as f:
                    json.dump(transcript_data, f, indent=2, default=str)
    
    async def _save_comprehensive_results(self, workflow_results: Dict[str, Any]):
        """Save comprehensive workflow results"""
        
        # Save main workflow results
        workflow_file = self.results_dir / "integrated_workflow_results.json"
        with open(workflow_file, 'w') as f:
            json.dump(workflow_results, f, indent=2, default=str)
        
        # Save component-specific results
        self.test_generator.save_generation_results(self.results_dir / "test_generation")
        self.analysis_pipeline.save_analysis_results(self.results_dir / "analysis_pipeline")
        
        # Save session manager results
        session_results_file = self.results_dir / "session_results.json"
        session_data = [asdict(result) for result in self.session_manager.session_results]
        with open(session_results_file, 'w') as f:
            json.dump(session_data, f, indent=2, default=str)
        
        logger.info(f"Comprehensive results saved to {self.results_dir}")


async def main():
    """Main entry point for integrated parallel analysis"""
    workspace = Path("PathUtils.get_workspace_root()")
    
    logger.info("Starting Integrated Parallel MCP Analysis - Phase 3 Optimization")
    logger.info("=" * 80)
    
    orchestrator = IntegratedParallelOrchestrator(workspace)
    
    try:
        results = await orchestrator.execute_complete_analysis()
        
        print("\n" + "=" * 80)
        print("INTEGRATED PARALLEL ANALYSIS COMPLETED")
        print("=" * 80)
        
        print(f"\nOverall Results:")
        print(f"  Total Duration: {results['total_duration_seconds']:.1f}s")
        print(f"  Overall Speedup: {results.get('overall_speedup', 1):.2f}x")
        print(f"  Time Reduction: {results.get('time_reduction_percent', 0):.1f}%")
        
        print(f"\nPhase Breakdown:")
        for phase_name, phase_data in results.get("phases", {}).items():
            duration = phase_data.get("duration_seconds", 0)
            efficiency = phase_data.get("parallel_efficiency", 1)
            print(f"  {phase_name}: {duration:.1f}s ({efficiency:.1f}x speedup)")
        
        print(f"\nResults saved to: {orchestrator.results_dir}")
        
    except Exception as e:
        logger.error(f"Integrated parallel analysis failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())