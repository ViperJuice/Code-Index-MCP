"""
Tests for health monitoring integration.
"""
import os
import asyncio
import time
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from mcp_server.features.health_integration import HealthMonitor


class TestHealthMonitor:
    """Test health monitoring integration."""
    
    @pytest.fixture
    async def health_monitor(self):
        """Create health monitor instance."""
        server_mock = Mock()
        server_mock.session_manager = Mock()
        server_mock.session_manager.get_active_sessions = Mock(return_value=[])
        
        monitor = HealthMonitor(server_mock)
        await monitor.initialize()
        yield monitor
        await monitor.shutdown()
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test health monitor initialization."""
        server_mock = Mock()
        monitor = HealthMonitor(server_mock)
        
        assert not monitor.enabled
        assert monitor._monitoring_task is None
        
        # Enable and initialize
        with patch.dict(os.environ, {'MCP_ENABLE_HEALTH': 'true'}):
            monitor = HealthMonitor(server_mock)
            await monitor.initialize()
            
            assert monitor.enabled
            assert monitor._monitoring_task is not None
            assert monitor._start_time > 0
    
    @pytest.mark.asyncio
    async def test_health_check_components(self, health_monitor):
        """Test checking individual components."""
        # Mock server components
        health_monitor.server.session_manager = Mock()
        health_monitor.server.session_manager.get_active_sessions = Mock(
            return_value=['session1', 'session2']
        )
        
        # Check server health
        server_health = await health_monitor._check_server_health()
        assert server_health['status'] == 'healthy'
        assert server_health['uptime'] > 0
        assert server_health['active_sessions'] == 2
        
        # Check storage health
        with patch('mcp_server.storage.sqlite_store.SQLiteStore') as MockStore:
            mock_store = AsyncMock()
            mock_store.ping = AsyncMock(return_value=True)
            MockStore.return_value = mock_store
            
            storage_health = await health_monitor._check_storage_health()
            assert storage_health['status'] == 'healthy'
            assert storage_health['type'] == 'sqlite'
    
    @pytest.mark.asyncio
    async def test_memory_health_check(self, health_monitor):
        """Test memory health checking."""
        # Mock psutil
        with patch('psutil.Process') as MockProcess:
            mock_process = Mock()
            mock_process.memory_info.return_value = Mock(rss=100 * 1024 * 1024)  # 100MB
            mock_process.memory_percent.return_value = 5.0
            MockProcess.return_value = mock_process
            
            memory_health = await health_monitor._check_memory_health()
            
            assert memory_health['status'] == 'healthy'
            assert memory_health['used_mb'] == 100
            assert memory_health['percent'] == 5.0
    
    @pytest.mark.asyncio
    async def test_memory_warning_threshold(self, health_monitor):
        """Test memory warning threshold."""
        with patch('psutil.Process') as MockProcess:
            mock_process = Mock()
            # Set memory to 85% (above warning threshold)
            mock_process.memory_percent.return_value = 85.0
            mock_process.memory_info.return_value = Mock(rss=850 * 1024 * 1024)
            MockProcess.return_value = mock_process
            
            memory_health = await health_monitor._check_memory_health()
            
            assert memory_health['status'] == 'warning'
            assert 'High memory usage' in memory_health['message']
    
    @pytest.mark.asyncio
    async def test_full_health_report(self, health_monitor):
        """Test generating full health report."""
        # Mock all health checks
        health_monitor._check_server_health = AsyncMock(
            return_value={'status': 'healthy', 'uptime': 100}
        )
        health_monitor._check_storage_health = AsyncMock(
            return_value={'status': 'healthy', 'type': 'sqlite'}
        )
        health_monitor._check_memory_health = AsyncMock(
            return_value={'status': 'healthy', 'percent': 50}
        )
        
        report = await health_monitor.get_health_report()
        
        assert report['overall_status'] == 'healthy'
        assert 'timestamp' in report
        assert 'components' in report
        assert 'server' in report['components']
        assert 'storage' in report['components']
        assert 'memory' in report['components']
    
    @pytest.mark.asyncio
    async def test_health_degraded_status(self, health_monitor):
        """Test degraded health status."""
        # One component unhealthy
        health_monitor._check_server_health = AsyncMock(
            return_value={'status': 'healthy'}
        )
        health_monitor._check_storage_health = AsyncMock(
            return_value={'status': 'warning', 'message': 'Slow response'}
        )
        health_monitor._check_memory_health = AsyncMock(
            return_value={'status': 'healthy'}
        )
        
        report = await health_monitor.get_health_report()
        
        assert report['overall_status'] == 'degraded'
    
    @pytest.mark.asyncio
    async def test_health_unhealthy_status(self, health_monitor):
        """Test unhealthy status."""
        # Critical component failure
        health_monitor._check_server_health = AsyncMock(
            return_value={'status': 'healthy'}
        )
        health_monitor._check_storage_health = AsyncMock(
            return_value={'status': 'unhealthy', 'error': 'Connection failed'}
        )
        health_monitor._check_memory_health = AsyncMock(
            return_value={'status': 'healthy'}
        )
        
        report = await health_monitor.get_health_report()
        
        assert report['overall_status'] == 'unhealthy'
    
    @pytest.mark.asyncio
    async def test_monitoring_loop(self, health_monitor):
        """Test the monitoring loop updates metrics."""
        health_monitor._check_interval = 0.1  # Fast interval for testing
        health_monitor._last_check_time = 0
        
        # Let monitoring run briefly
        await asyncio.sleep(0.3)
        
        # Should have performed checks
        assert health_monitor._last_check_time > 0
        assert health_monitor._check_count > 0
    
    @pytest.mark.asyncio
    async def test_error_handling_in_checks(self, health_monitor):
        """Test error handling during health checks."""
        # Mock a failing health check
        health_monitor._check_storage_health = AsyncMock(
            side_effect=Exception("Storage check failed")
        )
        
        # Should not crash
        report = await health_monitor.get_health_report()
        
        assert 'storage' in report['components']
        assert report['components']['storage']['status'] == 'unhealthy'
        assert 'error' in report['components']['storage']
    
    @pytest.mark.asyncio
    async def test_shutdown(self, health_monitor):
        """Test health monitor shutdown."""
        # Verify monitoring task is cancelled
        monitoring_task = health_monitor._monitoring_task
        assert monitoring_task is not None
        assert not monitoring_task.cancelled()
        
        await health_monitor.shutdown()
        
        assert monitoring_task.cancelled()
        assert health_monitor._monitoring_task is None
    
    @pytest.mark.asyncio
    async def test_disabled_health_monitor(self):
        """Test health monitor when disabled."""
        server_mock = Mock()
        
        with patch.dict(os.environ, {'MCP_ENABLE_HEALTH': 'false'}):
            monitor = HealthMonitor(server_mock)
            await monitor.initialize()
            
            assert not monitor.enabled
            assert monitor._monitoring_task is None
            
            # Should return minimal report
            report = await monitor.get_health_report()
            assert report['overall_status'] == 'disabled'
    
    @pytest.mark.asyncio
    async def test_custom_check_interval(self):
        """Test custom health check interval."""
        server_mock = Mock()
        
        with patch.dict(os.environ, {
            'MCP_ENABLE_HEALTH': 'true',
            'MCP_HEALTH_CHECK_INTERVAL': '60'
        }):
            monitor = HealthMonitor(server_mock)
            await monitor.initialize()
            
            assert monitor._check_interval == 60
            
            await monitor.shutdown()
    
    @pytest.mark.asyncio
    async def test_health_endpoint_data(self, health_monitor):
        """Test data format for health endpoint."""
        report = await health_monitor.get_health_report()
        
        # Verify structure for API consumption
        assert isinstance(report, dict)
        assert 'overall_status' in report
        assert report['overall_status'] in ['healthy', 'degraded', 'unhealthy', 'disabled']
        assert 'timestamp' in report
        assert isinstance(report['timestamp'], (int, float))
        assert 'components' in report
        assert isinstance(report['components'], dict)