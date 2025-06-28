#!/usr/bin/env python3
"""
MCP Method Detection System
Real-time monitoring and classification of MCP retrieval methods.
"""

import json
import time
import re
import subprocess
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime
from dataclasses import dataclass, asdict
import logging
import threading
import queue
from collections import defaultdict
import psutil
from mcp_server.core.path_utils import PathUtils

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.enhanced_mcp_analysis_framework import RetrievalMethod, RetrievalMethodMetrics

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class MCPMethodEvent:
    """Single MCP method detection event"""
    timestamp: datetime
    event_type: str  # "search_code", "symbol_lookup", "query_start", "query_end"
    method_used: RetrievalMethod
    parameters: Dict[str, Any]
    response_data: Optional[Dict[str, Any]] = None
    schema_detected: Optional[str] = None
    collection_detected: Optional[str] = None
    performance_metrics: Dict[str, float] = None
    
    def __post_init__(self):
        if self.performance_metrics is None:
            self.performance_metrics = {}


@dataclass
class MCPSession:
    """MCP session tracking"""
    session_id: str
    start_time: datetime
    events: List[MCPMethodEvent]
    method_usage_counts: Dict[str, int]
    schema_usage_counts: Dict[str, int]
    collection_usage_counts: Dict[str, int]
    active_queries: Dict[str, MCPMethodEvent]
    
    def __post_init__(self):
        if not self.events:
            self.events = []
        if not self.method_usage_counts:
            self.method_usage_counts = defaultdict(int)
        if not self.schema_usage_counts:
            self.schema_usage_counts = defaultdict(int)
        if not self.collection_usage_counts:
            self.collection_usage_counts = defaultdict(int)
        if not self.active_queries:
            self.active_queries = {}


class MCPServerMonitor:
    """Monitor MCP server activity to detect method usage"""
    
    def __init__(self, workspace_path: Path, mcp_server_process_name: str = "python"):
        self.workspace_path = workspace_path
        self.mcp_server_process_name = mcp_server_process_name
        self.monitoring = False
        self.event_queue = queue.Queue()
        self.sessions: Dict[str, MCPSession] = {}
        self.current_session_id = None
        
        # Detection patterns
        self.patterns = {
            "semantic_search": [
                r"QdrantClient.*search",
                r"voyage.*embed",
                r"collection.*search",
                r"semantic=true",
                r"score.*\d+\.\d+"
            ],
            "sql_fts_search": [
                r"fts_code.*MATCH",
                r"fts5.*search",
                r"SELECT.*fts_code",
                r"bm25\(fts_code\)"
            ],
            "sql_bm25_search": [
                r"bm25_content.*MATCH",
                r"SELECT.*bm25_content",
                r"bm25\(bm25_content\)"
            ],
            "symbol_lookup": [
                r"symbols.*WHERE.*name",
                r"SELECT.*symbols.*name",
                r"symbol_lookup"
            ]
        }
        
        # Schema detection patterns
        self.schema_patterns = {
            "fts_code": [
                r"fts_code",
                r"CREATE.*VIRTUAL.*TABLE.*fts5"
            ],
            "bm25_content": [
                r"bm25_content",
                r"bm25\(bm25_content\)"
            ],
            "symbols": [
                r"symbols.*table",
                r"SELECT.*symbols"
            ]
        }
        
        # Collection detection patterns (for semantic search)
        self.collection_patterns = {
            "codebase_collection": [
                r"codebase-[a-f0-9]+",
                r"code-embeddings"
            ],
            "test_collection": [
                r"typescript-\d+",
                r"test-collection"
            ]
        }
        
        # MCP server log monitoring
        self.log_files = self._discover_mcp_logs()
        self.process_monitor = None
        
    def _discover_mcp_logs(self) -> List[Path]:
        """Discover MCP server log files"""
        log_candidates = [
            self.workspace_path / ".mcp" / "logs" / "server.log",
            Path("PathUtils.get_temp_path() / "mcp_server.log"),
            self.workspace_path / "mcp_server.log",
            Path.home() / ".mcp" / "logs" / "server.log"
        ]
        
        found_logs = []
        for log_path in log_candidates:
            if log_path.exists():
                found_logs.append(log_path)
                logger.info(f"Found MCP log: {log_path}")
        
        return found_logs
    
    def start_monitoring(self, session_id: str):
        """Start monitoring MCP server activity"""
        self.current_session_id = session_id
        self.sessions[session_id] = MCPSession(
            session_id=session_id,
            start_time=datetime.now(),
            events=[],
            method_usage_counts=defaultdict(int),
            schema_usage_counts=defaultdict(int),
            collection_usage_counts=defaultdict(int),
            active_queries={}
        )
        
        self.monitoring = True
        
        # Start log monitoring threads
        for log_file in self.log_files:
            log_thread = threading.Thread(
                target=self._monitor_log_file,
                args=(log_file, session_id),
                daemon=True
            )
            log_thread.start()
        
        # Start process monitoring
        self.process_monitor = threading.Thread(
            target=self._monitor_mcp_processes,
            args=(session_id,),
            daemon=True
        )
        self.process_monitor.start()
        
        logger.info(f"Started MCP monitoring for session {session_id}")
    
    def stop_monitoring(self):
        """Stop monitoring MCP server activity"""
        self.monitoring = False
        logger.info("Stopped MCP monitoring")
    
    def _monitor_log_file(self, log_file: Path, session_id: str):
        """Monitor a specific log file for MCP activity"""
        try:
            with open(log_file, 'r') as f:
                # Start from end of file
                f.seek(0, 2)
                
                while self.monitoring:
                    line = f.readline()
                    if not line:
                        time.sleep(0.1)
                        continue
                    
                    self._process_log_line(line, session_id)
                    
        except Exception as e:
            logger.error(f"Error monitoring log file {log_file}: {e}")
    
    def _monitor_mcp_processes(self, session_id: str):
        """Monitor MCP server processes for memory/CPU usage"""
        while self.monitoring:
            try:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    if 'mcp_server' in ' '.join(proc.info['cmdline'] or []):
                        # Record process metrics
                        event = MCPMethodEvent(
                            timestamp=datetime.now(),
                            event_type="process_metrics",
                            method_used=RetrievalMethod.SEMANTIC,  # Default
                            parameters={},
                            performance_metrics={
                                "cpu_percent": proc.cpu_percent(),
                                "memory_mb": proc.memory_info().rss / 1024 / 1024
                            }
                        )
                        self.sessions[session_id].events.append(event)
                        
            except Exception as e:
                logger.debug(f"Process monitoring error: {e}")
            
            time.sleep(1.0)
    
    def _process_log_line(self, line: str, session_id: str):
        """Process a single log line for method detection"""
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        timestamp = datetime.now()
        
        # Detect retrieval method
        method = self._detect_method_from_line(line)
        if method == RetrievalMethod.NATIVE_GREP:  # No detection
            return
        
        # Detect schema used
        schema = self._detect_schema_from_line(line)
        
        # Detect collection used (for semantic)
        collection = self._detect_collection_from_line(line)
        
        # Extract parameters
        parameters = self._extract_parameters_from_line(line)
        
        # Create event
        event = MCPMethodEvent(
            timestamp=timestamp,
            event_type="method_detected",
            method_used=method,
            parameters=parameters,
            schema_detected=schema,
            collection_detected=collection
        )
        
        # Update session tracking
        session.events.append(event)
        session.method_usage_counts[method.value] += 1
        
        if schema:
            session.schema_usage_counts[schema] += 1
        
        if collection:
            session.collection_usage_counts[collection] += 1
        
        logger.debug(f"Detected {method.value} method with schema {schema}")
    
    def _detect_method_from_line(self, line: str) -> RetrievalMethod:
        """Detect retrieval method from log line"""
        line_lower = line.lower()
        
        # Check for semantic search indicators
        for pattern in self.patterns["semantic_search"]:
            if re.search(pattern, line_lower):
                return RetrievalMethod.SEMANTIC
        
        # Check for SQL FTS search
        for pattern in self.patterns["sql_fts_search"]:
            if re.search(pattern, line_lower):
                return RetrievalMethod.SQL_FTS
        
        # Check for SQL BM25 search
        for pattern in self.patterns["sql_bm25_search"]:
            if re.search(pattern, line_lower):
                return RetrievalMethod.SQL_BM25
        
        # Check for symbol lookup
        for pattern in self.patterns["symbol_lookup"]:
            if re.search(pattern, line_lower):
                return RetrievalMethod.SQL_FTS  # Symbol lookup typically uses SQL
        
        return RetrievalMethod.NATIVE_GREP  # No detection
    
    def _detect_schema_from_line(self, line: str) -> Optional[str]:
        """Detect database schema from log line"""
        line_lower = line.lower()
        
        for schema, patterns in self.schema_patterns.items():
            for pattern in patterns:
                if re.search(pattern, line_lower):
                    return schema
        
        return None
    
    def _detect_collection_from_line(self, line: str) -> Optional[str]:
        """Detect Qdrant collection from log line"""
        for collection_type, patterns in self.collection_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    return match.group(0)  # Return the actual collection name
        
        return None
    
    def _extract_parameters_from_line(self, line: str) -> Dict[str, Any]:
        """Extract query parameters from log line"""
        parameters = {}
        
        # Extract query text
        query_match = re.search(r'query["\']:\s*["\']([^"\']+)', line)
        if query_match:
            parameters["query"] = query_match.group(1)
        
        # Extract semantic parameter
        if "semantic=true" in line.lower():
            parameters["semantic"] = True
        elif "semantic=false" in line.lower():
            parameters["semantic"] = False
        
        # Extract limit parameter
        limit_match = re.search(r'limit["\']:\s*(\d+)', line)
        if limit_match:
            parameters["limit"] = int(limit_match.group(1))
        
        return parameters
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive session summary"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        # Calculate statistics
        total_events = len(session.events)
        method_distribution = dict(session.method_usage_counts)
        schema_distribution = dict(session.schema_usage_counts)
        collection_distribution = dict(session.collection_usage_counts)
        
        # Calculate performance metrics
        semantic_events = [e for e in session.events if e.method_used == RetrievalMethod.SEMANTIC]
        sql_events = [e for e in session.events if e.method_used in [RetrievalMethod.SQL_FTS, RetrievalMethod.SQL_BM25]]
        
        summary = {
            "session_id": session_id,
            "start_time": session.start_time.isoformat(),
            "duration_minutes": (datetime.now() - session.start_time).total_seconds() / 60,
            "total_events": total_events,
            
            "method_distribution": method_distribution,
            "schema_distribution": schema_distribution,
            "collection_distribution": collection_distribution,
            
            "semantic_usage": {
                "count": len(semantic_events),
                "percentage": len(semantic_events) / max(total_events, 1) * 100
            },
            
            "sql_usage": {
                "count": len(sql_events),
                "percentage": len(sql_events) / max(total_events, 1) * 100
            },
            
            "hybrid_usage_detected": self._detect_hybrid_usage(session),
            
            "performance_insights": self._analyze_performance_patterns(session)
        }
        
        return summary
    
    def _detect_hybrid_usage(self, session: MCPSession) -> bool:
        """Detect if hybrid search (semantic + SQL) was used"""
        # Look for rapid sequential usage of different methods
        events = sorted(session.events, key=lambda e: e.timestamp)
        
        for i in range(len(events) - 1):
            current = events[i]
            next_event = events[i + 1]
            
            # Check if different methods used within 1 second
            time_diff = (next_event.timestamp - current.timestamp).total_seconds()
            if time_diff < 1.0 and current.method_used != next_event.method_used:
                return True
        
        return False
    
    def _analyze_performance_patterns(self, session: MCPSession) -> Dict[str, Any]:
        """Analyze performance patterns from session"""
        insights = {}
        
        # Group events by method
        method_events = defaultdict(list)
        for event in session.events:
            method_events[event.method_used].append(event)
        
        # Analyze each method
        for method, events in method_events.items():
            if not events:
                continue
            
            # Get performance metrics
            perf_events = [e for e in events if e.performance_metrics]
            if perf_events:
                avg_response_time = sum(
                    e.performance_metrics.get("response_time_ms", 0) 
                    for e in perf_events
                ) / len(perf_events)
                
                insights[method.value] = {
                    "event_count": len(events),
                    "avg_response_time_ms": avg_response_time,
                    "has_performance_data": True
                }
            else:
                insights[method.value] = {
                    "event_count": len(events),
                    "has_performance_data": False
                }
        
        return insights
    
    def save_session_data(self, session_id: str, output_path: Path):
        """Save session data to file"""
        if session_id not in self.sessions:
            return
        
        session_data = {
            "session": asdict(self.sessions[session_id]),
            "summary": self.get_session_summary(session_id)
        }
        
        output_file = output_path / f"mcp_method_detection_{session_id}.json"
        with open(output_file, 'w') as f:
            json.dump(session_data, f, indent=2, default=str)
        
        logger.info(f"Saved session data to {output_file}")


class MCPMethodValidator:
    """Validate MCP method detection against actual database queries"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.index_paths = self._discover_index_paths()
    
    def _discover_index_paths(self) -> List[Path]:
        """Discover available index database paths"""
        index_paths = []
        
        # Standard locations
        candidates = [
            self.workspace_path / ".indexes" / "f7b49f5d0ae0" / "current.db",
            self.workspace_path / ".mcp-index" / "index.db",
            self.workspace_path / "test_indexes" / "javascript_react" / "code_index.db"
        ]
        
        for candidate in candidates:
            if candidate.exists():
                index_paths.append(candidate)
        
        return index_paths
    
    def validate_sql_schema_detection(self, detected_schema: str, query: str) -> bool:
        """Validate that the detected SQL schema is correct"""
        for index_path in self.index_paths:
            try:
                conn = sqlite3.connect(str(index_path))
                cursor = conn.cursor()
                
                # Check if schema table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (detected_schema,))
                result = cursor.fetchone()
                
                if result:
                    # Try to execute a query on this table
                    test_query = f"SELECT COUNT(*) FROM {detected_schema}"
                    cursor.execute(test_query)
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        conn.close()
                        return True
                
                conn.close()
                
            except Exception as e:
                logger.debug(f"Schema validation error for {index_path}: {e}")
                continue
        
        return False
    
    def validate_semantic_collection_detection(self, detected_collection: str) -> bool:
        """Validate that the detected semantic collection exists"""
        try:
            from qdrant_client import QdrantClient
            
            # Check main qdrant path
            qdrant_path = self.workspace_path / ".indexes" / "qdrant" / "main.qdrant"
            if qdrant_path.exists():
                client = QdrantClient(path=str(qdrant_path))
                collections = client.get_collections()
                
                for collection in collections.collections:
                    if collection.name == detected_collection:
                        return True
                        
        except Exception as e:
            logger.debug(f"Collection validation error: {e}")
        
        return False
    
    def cross_reference_with_logs(self, session_id: str, monitor: MCPServerMonitor) -> Dict[str, Any]:
        """Cross-reference detected methods with actual database/collection usage"""
        if session_id not in monitor.sessions:
            return {}
        
        session = monitor.sessions[session_id]
        validation_report = {
            "total_events": len(session.events),
            "validated_events": 0,
            "schema_validations": {},
            "collection_validations": {},
            "accuracy_score": 0.0
        }
        
        for event in session.events:
            if event.schema_detected:
                is_valid = self.validate_sql_schema_detection(event.schema_detected, "")
                validation_report["schema_validations"][event.schema_detected] = is_valid
                if is_valid:
                    validation_report["validated_events"] += 1
            
            if event.collection_detected:
                is_valid = self.validate_semantic_collection_detection(event.collection_detected)
                validation_report["collection_validations"][event.collection_detected] = is_valid
                if is_valid:
                    validation_report["validated_events"] += 1
        
        if validation_report["total_events"] > 0:
            validation_report["accuracy_score"] = validation_report["validated_events"] / validation_report["total_events"]
        
        return validation_report


def main():
    """Example usage of MCP method detection"""
    workspace = Path("PathUtils.get_workspace_root()")
    session_id = f"method_detection_{int(time.time())}"
    
    # Initialize monitor
    monitor = MCPServerMonitor(workspace)
    validator = MCPMethodValidator(workspace)
    
    try:
        # Start monitoring
        monitor.start_monitoring(session_id)
        
        logger.info(f"MCP method detection started for session {session_id}")
        logger.info("Run some MCP queries now...")
        
        # In a real scenario, this would run in parallel with MCP testing
        time.sleep(10)  # Simulate monitoring period
        
        # Stop monitoring and get results
        monitor.stop_monitoring()
        
        # Get session summary
        summary = monitor.get_session_summary(session_id)
        if summary:
            print("\nMethod Detection Summary:")
            print(f"Total Events: {summary['total_events']}")
            print(f"Method Distribution: {summary['method_distribution']}")
            print(f"Schema Distribution: {summary['schema_distribution']}")
            print(f"Hybrid Usage: {summary['hybrid_usage_detected']}")
        
        # Validate results
        validation = validator.cross_reference_with_logs(session_id, monitor)
        print(f"\nValidation Accuracy: {validation['accuracy_score']:.1%}")
        
        # Save results
        output_dir = Path("mcp_method_analysis")
        output_dir.mkdir(exist_ok=True)
        monitor.save_session_data(session_id, output_dir)
        
    except KeyboardInterrupt:
        monitor.stop_monitoring()
        logger.info("Monitoring stopped by user")


if __name__ == "__main__":
    main()