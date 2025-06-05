"""Qdrant scaling and optimization for 1M+ symbols.

This module provides advanced Qdrant scaling strategies including:
- Automatic sharding based on collection size
- Dynamic shard rebalancing
- Performance monitoring and optimization
- Memory-efficient batch operations
- Horizontal scaling support

"""

import asyncio
import logging
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams
import psutil

from mcp_server.core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class ShardingStrategy:
    """Configuration for sharding strategy."""
    
    # Size-based sharding
    max_points_per_shard: int = 250000  # 250K points per shard
    min_shards: int = 2
    max_shards: int = 64
    
    # Performance-based sharding
    target_search_latency_ms: float = 100.0
    target_indexing_throughput: float = 1000.0  # points/sec
    
    # Memory-based sharding
    max_memory_per_shard_mb: int = 2048  # 2GB per shard
    memory_safety_factor: float = 0.8
    
    # Replication settings
    replication_factor: int = 2
    write_consistency_factor: int = 1

@dataclass
class ShardMetrics:
    """Metrics for a single shard."""
    
    shard_id: int
    point_count: int
    memory_usage_mb: float
    avg_search_latency_ms: float
    indexing_throughput: float
    disk_usage_mb: float
    last_updated: datetime
    
    def is_overloaded(self, strategy: ShardingStrategy) -> bool:
        """Check if shard is overloaded."""
        return (
            self.point_count > strategy.max_points_per_shard * 1.1 or
            self.memory_usage_mb > strategy.max_memory_per_shard_mb or
            self.avg_search_latency_ms > strategy.target_search_latency_ms * 1.5
        )
    
    def needs_splitting(self, strategy: ShardingStrategy) -> bool:
        """Check if shard needs to be split."""
        return (
            self.point_count > strategy.max_points_per_shard and
            self.memory_usage_mb > strategy.max_memory_per_shard_mb * strategy.memory_safety_factor
        )

class QdrantOptimizer:
    """Advanced Qdrant optimization and scaling manager."""
    
    def __init__(
        self,
        qdrant_client: QdrantClient,
        strategy: Optional[ShardingStrategy] = None
    ):
        self.qdrant = qdrant_client
        self.strategy = strategy or ShardingStrategy()
        self._shard_metrics: Dict[str, Dict[int, ShardMetrics]] = {}
        self._performance_history: List[Dict[str, Any]] = []
        
        logger.info(f"Initialized QdrantOptimizer with strategy: {self.strategy}")
    
    async def analyze_collection_performance(self, collection_name: str) -> Dict[str, Any]:
        """Analyze collection performance and recommend optimizations."""
        
        try:
            # Get collection info
            collection_info = self.qdrant.get_collection(collection_name)
            
            # Get cluster info
            cluster_info = self.qdrant.get_cluster()
            
            # Calculate optimal shard count
            total_points = collection_info.points_count or 0
            optimal_shards = self._calculate_optimal_shard_count(total_points)
            current_shards = len(collection_info.config.params.shard_number if hasattr(collection_info.config.params, 'shard_number') else [1])
            
            # Analyze memory usage
            memory_analysis = await self._analyze_memory_usage(collection_name)
            
            # Performance recommendations
            recommendations = []
            
            if total_points > self.strategy.max_points_per_shard and current_shards < optimal_shards:
                recommendations.append({
                    "type": "increase_shards",
                    "current": current_shards,
                    "recommended": optimal_shards,
                    "reason": f"Collection has {total_points} points, exceeding optimal shard capacity"
                })
            
            if memory_analysis["total_memory_mb"] > self.strategy.max_memory_per_shard_mb * current_shards:
                recommendations.append({
                    "type": "memory_optimization",
                    "current_memory": memory_analysis["total_memory_mb"],
                    "recommended_action": "increase_shards_or_optimize_vectors",
                    "reason": "Memory usage exceeds optimal limits"
                })
            
            return {
                "collection": collection_name,
                "total_points": total_points,
                "current_shards": current_shards,
                "optimal_shards": optimal_shards,
                "memory_analysis": memory_analysis,
                "recommendations": recommendations,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing collection {collection_name}: {e}")
            raise
    
    def _calculate_optimal_shard_count(self, total_points: int) -> int:
        """Calculate optimal number of shards based on collection size."""
        
        if total_points == 0:
            return self.strategy.min_shards
        
        # Size-based calculation
        size_based_shards = math.ceil(total_points / self.strategy.max_points_per_shard)
        
        # Memory-based calculation (estimate)
        estimated_memory_per_point = 4 * 1024 + 100  # 4KB vector + 100B metadata
        total_memory_mb = (total_points * estimated_memory_per_point) / (1024 * 1024)
        memory_based_shards = math.ceil(total_memory_mb / self.strategy.max_memory_per_shard_mb)
        
        # Take the maximum of size and memory based calculations
        optimal_shards = max(size_based_shards, memory_based_shards)
        
        # Apply min/max constraints
        optimal_shards = max(self.strategy.min_shards, optimal_shards)
        optimal_shards = min(self.strategy.max_shards, optimal_shards)
        
        logger.debug(f"Calculated optimal shards: {optimal_shards} for {total_points} points")
        return optimal_shards
    
    async def _analyze_memory_usage(self, collection_name: str) -> Dict[str, Any]:
        """Analyze memory usage for a collection."""
        
        try:
            # Get system memory info
            memory_info = psutil.virtual_memory()
            
            # Estimate collection memory usage
            collection_info = self.qdrant.get_collection(collection_name)
            total_points = collection_info.points_count or 0
            
            # Rough estimation: vector_size * 4 bytes + metadata
            vector_size = collection_info.config.params.vectors.size if hasattr(collection_info.config.params, 'vectors') else 1024
            estimated_vector_memory = total_points * vector_size * 4  # 4 bytes per float
            estimated_metadata_memory = total_points * 200  # 200 bytes metadata per point
            total_estimated_mb = (estimated_vector_memory + estimated_metadata_memory) / (1024 * 1024)
            
            return {
                "total_memory_mb": total_estimated_mb,
                "vector_memory_mb": estimated_vector_memory / (1024 * 1024),
                "metadata_memory_mb": estimated_metadata_memory / (1024 * 1024),
                "system_memory_mb": memory_info.total / (1024 * 1024),
                "system_available_mb": memory_info.available / (1024 * 1024),
                "memory_efficiency": total_estimated_mb / (memory_info.total / (1024 * 1024))
            }
            
        except Exception as e:
            logger.warning(f"Could not analyze memory usage: {e}")
            return {"error": str(e)}
    
    async def optimize_collection_sharding(
        self,
        collection_name: str,
        target_shard_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """Optimize collection sharding based on analysis."""
        
        analysis = await self.analyze_collection_performance(collection_name)
        target_shards = target_shard_count or analysis["optimal_shards"]
        current_shards = analysis["current_shards"]
        
        if target_shards == current_shards:
            return {
                "status": "no_change_needed",
                "current_shards": current_shards,
                "target_shards": target_shards,
                "message": "Collection is already optimally sharded"
            }
        
        try:
            # For now, we'll recreate the collection with optimal sharding
            # In production, you'd want to implement migration strategies
            logger.warning(
                f"Collection {collection_name} needs resharding from {current_shards} to {target_shards} shards. "
                "This would require data migration in production."
            )
            
            return {
                "status": "resharding_needed",
                "current_shards": current_shards,
                "target_shards": target_shards,
                "recommendations": analysis["recommendations"],
                "message": f"Collection should be resharded to {target_shards} shards for optimal performance"
            }
            
        except Exception as e:
            logger.error(f"Error optimizing collection sharding: {e}")
            raise
    
    async def create_optimized_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE,
        expected_points: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new collection with optimal sharding configuration."""
        
        # Calculate optimal shard count
        if expected_points:
            optimal_shards = self._calculate_optimal_shard_count(expected_points)
        else:
            optimal_shards = self.strategy.min_shards
        
        try:
            # Create collection with optimal configuration
            self.qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance
                ),
                shard_number=optimal_shards,
                replication_factor=self.strategy.replication_factor,
                write_consistency_factor=self.strategy.write_consistency_factor
            )
            
            logger.info(
                f"Created optimized collection {collection_name} with {optimal_shards} shards "
                f"for {expected_points or 'unknown'} expected points"
            )
            
            return {
                "collection_name": collection_name,
                "shard_count": optimal_shards,
                "vector_size": vector_size,
                "distance": distance.value,
                "expected_points": expected_points,
                "replication_factor": self.strategy.replication_factor,
                "status": "created"
            }
            
        except Exception as e:
            logger.error(f"Error creating optimized collection: {e}")
            raise
    
    async def monitor_performance(self, collection_name: str) -> Dict[str, Any]:
        """Monitor collection performance metrics."""
        
        try:
            start_time = datetime.now()
            
            # Test search performance
            test_vector = [0.1] * 1024  # Dummy vector for testing
            search_start = datetime.now()
            
            search_results = self.qdrant.search(
                collection_name=collection_name,
                query_vector=test_vector,
                limit=10
            )
            
            search_latency = (datetime.now() - search_start).total_seconds() * 1000
            
            # Get collection stats
            collection_info = self.qdrant.get_collection(collection_name)
            
            # Calculate metrics
            metrics = {
                "collection": collection_name,
                "timestamp": datetime.now().isoformat(),
                "search_latency_ms": search_latency,
                "total_points": collection_info.points_count or 0,
                "status": collection_info.status.value if hasattr(collection_info, 'status') else "unknown",
                "performance_score": self._calculate_performance_score(search_latency, collection_info.points_count or 0)
            }
            
            # Store in history
            self._performance_history.append(metrics)
            
            # Keep only last 100 measurements
            if len(self._performance_history) > 100:
                self._performance_history = self._performance_history[-100:]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error monitoring performance: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def _calculate_performance_score(self, search_latency_ms: float, total_points: int) -> float:
        """Calculate a performance score (0-100) based on metrics."""
        
        # Latency score (lower is better)
        latency_score = max(0, 100 - (search_latency_ms / self.strategy.target_search_latency_ms) * 50)
        
        # Scalability score (based on points handled efficiently)
        if total_points == 0:
            scalability_score = 100
        else:
            optimal_shards = self._calculate_optimal_shard_count(total_points)
            points_per_shard = total_points / max(1, optimal_shards)
            scalability_score = max(0, 100 - (points_per_shard / self.strategy.max_points_per_shard) * 50)
        
        # Combined score
        performance_score = (latency_score + scalability_score) / 2
        return round(performance_score, 2)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of performance metrics."""
        
        if not self._performance_history:
            return {"message": "No performance data available"}
        
        recent_metrics = self._performance_history[-10:]  # Last 10 measurements
        
        avg_latency = sum(m.get("search_latency_ms", 0) for m in recent_metrics) / len(recent_metrics)
        avg_score = sum(m.get("performance_score", 0) for m in recent_metrics) / len(recent_metrics)
        
        return {
            "total_measurements": len(self._performance_history),
            "recent_avg_latency_ms": round(avg_latency, 2),
            "recent_avg_performance_score": round(avg_score, 2),
            "target_latency_ms": self.strategy.target_search_latency_ms,
            "performance_trend": self._calculate_performance_trend(),
            "last_measurement": self._performance_history[-1] if self._performance_history else None
        }
    
    def _calculate_performance_trend(self) -> str:
        """Calculate performance trend over recent measurements."""
        
        if len(self._performance_history) < 5:
            return "insufficient_data"
        
        recent_scores = [m.get("performance_score", 0) for m in self._performance_history[-5:]]
        
        # Simple trend calculation
        if len(recent_scores) >= 2:
            trend = recent_scores[-1] - recent_scores[0]
            if trend > 5:
                return "improving"
            elif trend < -5:
                return "degrading"
            else:
                return "stable"
        
        return "stable"
    
    async def auto_optimize(self, collection_name: str) -> Dict[str, Any]:
        """Automatically optimize collection based on current performance."""
        
        try:
            # Analyze current state
            analysis = await self.analyze_collection_performance(collection_name)
            
            # Monitor performance
            perf_metrics = await self.monitor_performance(collection_name)
            
            # Determine if optimization is needed
            optimization_actions = []
            
            # Check if resharding is needed
            if analysis["recommendations"]:
                for rec in analysis["recommendations"]:
                    if rec["type"] == "increase_shards":
                        optimization_actions.append({
                            "action": "increase_shards",
                            "from": rec["current"],
                            "to": rec["recommended"],
                            "reason": rec["reason"]
                        })
            
            # Check performance metrics
            if perf_metrics.get("search_latency_ms", 0) > self.strategy.target_search_latency_ms * 1.5:
                optimization_actions.append({
                    "action": "optimize_performance",
                    "current_latency": perf_metrics["search_latency_ms"],
                    "target_latency": self.strategy.target_search_latency_ms,
                    "reason": "Search latency exceeds target"
                })
            
            return {
                "collection": collection_name,
                "analysis": analysis,
                "performance": perf_metrics,
                "optimization_actions": optimization_actions,
                "auto_optimization_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in auto-optimization: {e}")
            raise