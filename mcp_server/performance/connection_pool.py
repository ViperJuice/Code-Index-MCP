"""
Connection pooling implementation for database and external service connections.

Provides connection reuse, health monitoring, and automatic recovery.
"""

import asyncio
import time
import logging
from typing import Any, Dict, List, Optional, Protocol, TypeVar, Generic, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum
from contextlib import asynccontextmanager
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection states."""
    IDLE = "idle"
    ACTIVE = "active"
    STALE = "stale"
    BROKEN = "broken"


@dataclass
class ConnectionPoolConfig:
    """Configuration for connection pool."""
    min_connections: int = 5
    max_connections: int = 20
    connection_timeout: float = 30.0
    idle_timeout: float = 300.0  # 5 minutes
    max_lifetime: float = 3600.0  # 1 hour
    health_check_interval: float = 60.0  # 1 minute
    retry_attempts: int = 3
    retry_delay: float = 1.0
    enable_health_checks: bool = True
    enable_metrics: bool = True


@dataclass
class PoolStats:
    """Connection pool statistics."""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    stale_connections: int = 0
    broken_connections: int = 0
    created_connections: int = 0
    destroyed_connections: int = 0
    health_check_failures: int = 0
    connection_errors: int = 0
    checkout_timeouts: int = 0
    avg_checkout_time: float = 0.0
    avg_connection_age: float = 0.0


class IConnection(Protocol):
    """Interface for pooled connections."""
    
    async def is_healthy(self) -> bool:
        """Check if connection is healthy."""
        pass
    
    async def reset(self) -> None:
        """Reset connection state."""
        pass
    
    async def close(self) -> None:
        """Close the connection."""
        pass


TConnection = TypeVar('TConnection', bound=IConnection)


class PooledConnection(Generic[TConnection]):
    """Wrapper for pooled connections with metadata."""
    
    def __init__(self, connection: TConnection, pool: 'ConnectionPool'):
        self.connection = connection
        self.pool = pool
        self.created_at = time.time()
        self.last_used = time.time()
        self.state = ConnectionState.IDLE
        self.use_count = 0
        self.health_check_failures = 0
    
    @property
    def age(self) -> float:
        """Get connection age in seconds."""
        return time.time() - self.created_at
    
    @property
    def idle_time(self) -> float:
        """Get idle time in seconds."""
        return time.time() - self.last_used
    
    def mark_active(self) -> None:
        """Mark connection as active."""
        self.state = ConnectionState.ACTIVE
        self.last_used = time.time()
        self.use_count += 1
    
    def mark_idle(self) -> None:
        """Mark connection as idle."""
        self.state = ConnectionState.IDLE
        self.last_used = time.time()
    
    def mark_broken(self) -> None:
        """Mark connection as broken."""
        self.state = ConnectionState.BROKEN
    
    def mark_stale(self) -> None:
        """Mark connection as stale."""
        self.state = ConnectionState.STALE
    
    async def is_healthy(self) -> bool:
        """Check if connection is healthy."""
        try:
            return await self.connection.is_healthy()
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            self.health_check_failures += 1
            return False
    
    async def reset(self) -> None:
        """Reset connection state."""
        try:
            await self.connection.reset()
        except Exception as e:
            logger.warning(f"Connection reset failed: {e}")
            self.mark_broken()
            raise
    
    async def close(self) -> None:
        """Close the connection."""
        try:
            await self.connection.close()
        except Exception as e:
            logger.warning(f"Connection close failed: {e}")


class ConnectionFactory(ABC, Generic[TConnection]):
    """Abstract factory for creating connections."""
    
    @abstractmethod
    async def create_connection(self) -> TConnection:
        """Create a new connection."""
        pass
    
    @abstractmethod
    async def validate_connection(self, connection: TConnection) -> bool:
        """Validate a connection."""
        pass


class ConnectionPool(Generic[TConnection]):
    """Generic connection pool implementation."""
    
    def __init__(self, factory: Optional[ConnectionFactory[TConnection]] = None, config: Optional[ConnectionPoolConfig] = None, 
                 max_size: Optional[int] = None, timeout: Optional[int] = None):
        # Support simplified constructor for testing
        if config is None:
            config = ConnectionPoolConfig(
                min_connections=1,
                max_connections=max_size or 10,
                connection_timeout=timeout or 30,
                idle_timeout=300,
                health_check_interval=60
            )
        
        # Use a dummy factory if none provided (for testing)
        if factory is None:
            class DummyConnection:
                async def is_healthy(self): return True
                async def reset(self): pass
                async def close(self): pass
            
            class DummyFactory(ConnectionFactory):
                async def create_connection(self):
                    return DummyConnection()
                
                async def validate_connection(self, connection):
                    return True
            
            factory = DummyFactory()
        
        self.factory = factory
        self.config = config
        self._connections: List[PooledConnection[TConnection]] = []
        self._lock = asyncio.Lock()
        self._condition = asyncio.Condition(self._lock)
        self._stats = PoolStats()
        self._running = False
        self._health_check_task: Optional[asyncio.Task] = None
        self._checkout_times: List[float] = []
    
    async def start(self) -> None:
        """Start the connection pool."""
        if self._running:
            return
        
        self._running = True
        
        # Create minimum connections
        async with self._lock:
            for _ in range(self.config.min_connections):
                try:
                    await self._create_connection()
                except Exception as e:
                    logger.error(f"Failed to create initial connection: {e}")
        
        # Start health check task
        if self.config.enable_health_checks:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info(f"Connection pool started with {len(self._connections)} connections")
    
    async def stop(self) -> None:
        """Stop the connection pool."""
        if not self._running:
            return
        
        self._running = False
        
        # Stop health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        async with self._lock:
            for pooled_conn in self._connections[:]:
                await self._destroy_connection(pooled_conn)
        
        logger.info("Connection pool stopped")
    
    async def _create_connection(self) -> PooledConnection[TConnection]:
        """Create a new pooled connection."""
        try:
            connection = await self.factory.create_connection()
            pooled_conn = PooledConnection(connection, self)
            self._connections.append(pooled_conn)
            self._stats.created_connections += 1
            self._stats.total_connections += 1
            logger.debug(f"Created new connection (total: {len(self._connections)})")
            return pooled_conn
        except Exception as e:
            self._stats.connection_errors += 1
            logger.error(f"Failed to create connection: {e}")
            raise
    
    async def _destroy_connection(self, pooled_conn: PooledConnection[TConnection]) -> None:
        """Destroy a pooled connection."""
        try:
            if pooled_conn in self._connections:
                self._connections.remove(pooled_conn)
            
            await pooled_conn.close()
            self._stats.destroyed_connections += 1
            self._stats.total_connections -= 1
            logger.debug(f"Destroyed connection (total: {len(self._connections)})")
        except Exception as e:
            logger.error(f"Error destroying connection: {e}")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool."""
        start_time = time.time()
        pooled_conn = None
        
        try:
            # Wait for available connection
            async with self._condition:
                while True:
                    # Look for idle connection
                    pooled_conn = await self._find_available_connection()
                    if pooled_conn:
                        break
                    
                    # Try to create new connection if under max
                    if len(self._connections) < self.config.max_connections:
                        try:
                            pooled_conn = await self._create_connection()
                            break
                        except Exception as e:
                            logger.warning(f"Failed to create connection: {e}")
                    
                    # Wait for connection to become available
                    try:
                        await asyncio.wait_for(
                            self._condition.wait(),
                            timeout=self.config.connection_timeout
                        )
                    except asyncio.TimeoutError:
                        self._stats.checkout_timeouts += 1
                        raise RuntimeError("Connection checkout timeout")
            
            # Mark as active
            pooled_conn.mark_active()
            checkout_time = time.time() - start_time
            self._record_checkout_time(checkout_time)
            
            yield pooled_conn.connection
            
        except Exception as e:
            if pooled_conn:
                pooled_conn.mark_broken()
            raise
        finally:
            if pooled_conn:
                # Return connection to pool
                async with self._lock:
                    if pooled_conn.state == ConnectionState.BROKEN:
                        await self._destroy_connection(pooled_conn)
                    else:
                        pooled_conn.mark_idle()
                
                # Notify waiting tasks
                async with self._condition:
                    self._condition.notify()
    
    async def _find_available_connection(self) -> Optional[PooledConnection[TConnection]]:
        """Find an available connection in the pool."""
        # Clean up expired connections first
        await self._cleanup_expired_connections()
        
        # Look for idle connections
        for pooled_conn in self._connections:
            if pooled_conn.state == ConnectionState.IDLE:
                # Quick health check for connections that haven't been used recently
                if pooled_conn.idle_time > 60:  # 1 minute
                    try:
                        if not await pooled_conn.is_healthy():
                            pooled_conn.mark_broken()
                            continue
                    except Exception:
                        pooled_conn.mark_broken()
                        continue
                
                return pooled_conn
        
        return None
    
    async def _cleanup_expired_connections(self) -> None:
        """Clean up expired and broken connections."""
        to_remove = []
        current_time = time.time()
        
        for pooled_conn in self._connections:
            # Check for broken connections
            if pooled_conn.state == ConnectionState.BROKEN:
                to_remove.append(pooled_conn)
                continue
            
            # Check for stale connections
            if (pooled_conn.idle_time > self.config.idle_timeout or
                pooled_conn.age > self.config.max_lifetime):
                pooled_conn.mark_stale()
                to_remove.append(pooled_conn)
                continue
        
        # Remove expired connections (but keep minimum)
        connections_to_keep = max(
            len(self._connections) - len(to_remove),
            self.config.min_connections
        )
        
        if connections_to_keep < len(self._connections):
            keep_count = len(self._connections) - connections_to_keep
            to_remove = to_remove[:keep_count]
        
        for pooled_conn in to_remove:
            await self._destroy_connection(pooled_conn)
    
    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while self._running:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all connections."""
        async with self._lock:
            broken_connections = []
            
            for pooled_conn in self._connections:
                if pooled_conn.state == ConnectionState.IDLE:
                    try:
                        if not await pooled_conn.is_healthy():
                            broken_connections.append(pooled_conn)
                            self._stats.health_check_failures += 1
                    except Exception as e:
                        logger.warning(f"Health check error: {e}")
                        broken_connections.append(pooled_conn)
                        self._stats.health_check_failures += 1
            
            # Remove broken connections
            for pooled_conn in broken_connections:
                await self._destroy_connection(pooled_conn)
            
            # Ensure minimum connections
            while len(self._connections) < self.config.min_connections:
                try:
                    await self._create_connection()
                except Exception as e:
                    logger.error(f"Failed to maintain minimum connections: {e}")
                    break
    
    def _record_checkout_time(self, checkout_time: float) -> None:
        """Record checkout time for statistics."""
        if not self.config.enable_metrics:
            return
        
        self._checkout_times.append(checkout_time)
        if len(self._checkout_times) > 1000:  # Keep last 1000 measurements
            self._checkout_times.pop(0)
        
        if self._checkout_times:
            self._stats.avg_checkout_time = sum(self._checkout_times) / len(self._checkout_times)
    
    async def get_stats(self) -> PoolStats:
        """Get pool statistics."""
        async with self._lock:
            # Update current counts
            self._stats.total_connections = len(self._connections)
            self._stats.active_connections = sum(
                1 for conn in self._connections if conn.state == ConnectionState.ACTIVE
            )
            self._stats.idle_connections = sum(
                1 for conn in self._connections if conn.state == ConnectionState.IDLE
            )
            self._stats.stale_connections = sum(
                1 for conn in self._connections if conn.state == ConnectionState.STALE
            )
            self._stats.broken_connections = sum(
                1 for conn in self._connections if conn.state == ConnectionState.BROKEN
            )
            
            # Calculate average connection age
            if self._connections:
                total_age = sum(conn.age for conn in self._connections)
                self._stats.avg_connection_age = total_age / len(self._connections)
        
        return self._stats
    
    async def invalidate_all(self) -> None:
        """Invalidate all connections in the pool."""
        async with self._lock:
            for pooled_conn in self._connections:
                if pooled_conn.state != ConnectionState.ACTIVE:
                    pooled_conn.mark_stale()
        
        logger.info("Invalidated all connections in pool")


class ConnectionPoolManager:
    """Manager for multiple connection pools."""
    
    def __init__(self):
        self._pools: Dict[str, ConnectionPool] = {}
    
    def register_pool(self, name: str, pool: ConnectionPool) -> None:
        """Register a connection pool."""
        self._pools[name] = pool
        logger.info(f"Registered connection pool: {name}")
    
    def get_pool(self, name: str) -> Optional[ConnectionPool]:
        """Get a connection pool by name."""
        return self._pools.get(name)
    
    async def start_all(self) -> None:
        """Start all registered pools."""
        for name, pool in self._pools.items():
            try:
                await pool.start()
            except Exception as e:
                logger.error(f"Failed to start pool {name}: {e}")
    
    async def stop_all(self) -> None:
        """Stop all registered pools."""
        for name, pool in self._pools.items():
            try:
                await pool.stop()
            except Exception as e:
                logger.error(f"Failed to stop pool {name}: {e}")
    
    async def get_all_stats(self) -> Dict[str, PoolStats]:
        """Get statistics for all pools."""
        stats = {}
        for name, pool in self._pools.items():
            try:
                stats[name] = await pool.get_stats()
            except Exception as e:
                logger.error(f"Failed to get stats for pool {name}: {e}")
        return stats


# Global instance
connection_pool_manager = ConnectionPoolManager()