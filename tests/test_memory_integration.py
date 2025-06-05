"""
Tests for memory monitoring integration.
"""
import os
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from mcp_server.features.memory_integration import MemoryMonitor


class TestMemoryMonitor:
    """Test memory monitoring integration."""
    
    @pytest.fixture
    async def memory_monitor(self):
        """Create memory monitor instance."""
        server_mock = Mock()
        
        with patch.dict(os.environ, {
            'MCP_MONITOR_MEMORY': 'true',
            'MCP_MEMORY_LIMIT_MB': '512'
        }):
            monitor = MemoryMonitor(server_mock)
            await monitor.initialize()
            yield monitor
            await monitor.shutdown()
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test memory monitor initialization."""
        server_mock = Mock()
        monitor = MemoryMonitor(server_mock)
        
        assert not monitor.enabled
        assert monitor._monitoring_task is None
        
        # Enable and initialize
        with patch.dict(os.environ, {'MCP_MONITOR_MEMORY': 'true'}):
            monitor = MemoryMonitor(server_mock)
            await monitor.initialize()
            
            assert monitor.enabled
            assert monitor._monitoring_task is not None
            assert monitor._memory_limit_mb == 512  # default
    
    @pytest.mark.asyncio
    async def test_get_memory_usage(self, memory_monitor):
        """Test getting current memory usage."""
        with patch('psutil.Process') as MockProcess:
            mock_process = Mock()
            mock_process.memory_info.return_value = Mock(
                rss=200 * 1024 * 1024,  # 200MB
                vms=300 * 1024 * 1024   # 300MB
            )
            mock_process.memory_percent.return_value = 10.5
            MockProcess.return_value = mock_process
            
            usage = await memory_monitor.get_memory_usage()
            
            assert usage['rss_mb'] == 200
            assert usage['vms_mb'] == 300
            assert usage['percent'] == 10.5
            assert usage['limit_mb'] == 512
    
    @pytest.mark.asyncio
    async def test_check_memory_threshold(self, memory_monitor):
        """Test memory threshold checking."""
        # Normal usage
        with patch('psutil.Process') as MockProcess:
            mock_process = Mock()
            mock_process.memory_info.return_value = Mock(rss=200 * 1024 * 1024)
            MockProcess.return_value = mock_process
            
            is_exceeded = await memory_monitor.check_memory_threshold()
            assert is_exceeded is False
        
        # Exceeded usage
        with patch('psutil.Process') as MockProcess:
            mock_process = Mock()
            mock_process.memory_info.return_value = Mock(rss=600 * 1024 * 1024)
            MockProcess.return_value = mock_process
            
            is_exceeded = await memory_monitor.check_memory_threshold()
            assert is_exceeded is True
    
    @pytest.mark.asyncio
    async def test_memory_alert_callback(self, memory_monitor):
        """Test memory alert callback execution."""
        callback_called = False
        alert_info = None
        
        async def alert_callback(info):
            nonlocal callback_called, alert_info
            callback_called = True
            alert_info = info
        
        memory_monitor.set_alert_callback(alert_callback)
        
        # Trigger high memory condition
        with patch('psutil.Process') as MockProcess:
            mock_process = Mock()
            mock_process.memory_info.return_value = Mock(rss=600 * 1024 * 1024)
            MockProcess.return_value = mock_process
            
            # Simulate monitoring loop check
            await memory_monitor._check_memory()
            
            assert callback_called
            assert alert_info is not None
            assert alert_info['current_mb'] == 600
            assert alert_info['limit_mb'] == 512
    
    @pytest.mark.asyncio
    async def test_memory_history_tracking(self, memory_monitor):
        """Test tracking memory usage history."""
        # Simulate several memory readings
        readings = [100, 150, 200, 180, 220]
        
        for reading in readings:
            with patch('psutil.Process') as MockProcess:
                mock_process = Mock()
                mock_process.memory_info.return_value = Mock(rss=reading * 1024 * 1024)
                MockProcess.return_value = mock_process
                
                await memory_monitor._check_memory()
                await asyncio.sleep(0.01)
        
        history = memory_monitor.get_memory_history()
        
        assert len(history) == 5
        assert history[-1]['rss_mb'] == 220
        assert max(h['rss_mb'] for h in history) == 220
    
    @pytest.mark.asyncio
    async def test_memory_report(self, memory_monitor):
        """Test comprehensive memory report."""
        with patch('psutil.Process') as MockProcess:
            mock_process = Mock()
            mock_process.memory_info.return_value = Mock(
                rss=250 * 1024 * 1024,
                vms=350 * 1024 * 1024
            )
            mock_process.memory_percent.return_value = 12.5
            MockProcess.return_value = mock_process
            
            # Add some history
            await memory_monitor._check_memory()
            
            report = await memory_monitor.get_memory_report()
            
            assert 'current' in report
            assert report['current']['rss_mb'] == 250
            assert 'peak' in report
            assert 'average' in report
            assert 'status' in report
    
    @pytest.mark.asyncio
    async def test_garbage_collection_trigger(self, memory_monitor):
        """Test automatic garbage collection on high memory."""
        import gc
        
        with patch('gc.collect') as mock_gc_collect:
            # Simulate high memory
            with patch('psutil.Process') as MockProcess:
                mock_process = Mock()
                # Set to 90% of limit
                mock_process.memory_info.return_value = Mock(rss=460 * 1024 * 1024)
                MockProcess.return_value = mock_process
                
                await memory_monitor._check_memory()
                
                # Should trigger GC
                mock_gc_collect.assert_called()
    
    @pytest.mark.asyncio
    async def test_monitoring_interval(self, memory_monitor):
        """Test custom monitoring interval."""
        memory_monitor._check_interval = 0.1  # Fast interval for testing
        memory_monitor._check_count = 0
        
        # Let it run for a bit
        await asyncio.sleep(0.35)
        
        # Should have performed multiple checks
        assert memory_monitor._check_count >= 3
    
    @pytest.mark.asyncio
    async def test_memory_pressure_levels(self, memory_monitor):
        """Test different memory pressure levels."""
        test_cases = [
            (100, 'normal'),    # ~20% of 512MB limit
            (350, 'warning'),   # ~68% of limit
            (450, 'critical'),  # ~88% of limit
            (550, 'exceeded'),  # Over limit
        ]
        
        for memory_mb, expected_level in test_cases:
            with patch('psutil.Process') as MockProcess:
                mock_process = Mock()
                mock_process.memory_info.return_value = Mock(rss=memory_mb * 1024 * 1024)
                MockProcess.return_value = mock_process
                
                level = await memory_monitor.get_memory_pressure_level()
                assert level == expected_level
    
    @pytest.mark.asyncio
    async def test_memory_cleanup_suggestions(self, memory_monitor):
        """Test memory cleanup suggestions."""
        # Simulate high memory
        with patch('psutil.Process') as MockProcess:
            mock_process = Mock()
            mock_process.memory_info.return_value = Mock(rss=450 * 1024 * 1024)
            MockProcess.return_value = mock_process
            
            suggestions = await memory_monitor.get_cleanup_suggestions()
            
            assert isinstance(suggestions, list)
            assert len(suggestions) > 0
            assert any('cache' in s.lower() for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_disabled_monitor(self):
        """Test memory monitor when disabled."""
        server_mock = Mock()
        
        with patch.dict(os.environ, {'MCP_MONITOR_MEMORY': 'false'}):
            monitor = MemoryMonitor(server_mock)
            await monitor.initialize()
            
            assert not monitor.enabled
            assert monitor._monitoring_task is None
            
            # Should return minimal info
            report = await monitor.get_memory_report()
            assert report['status'] == 'disabled'
    
    @pytest.mark.asyncio
    async def test_memory_limit_configuration(self):
        """Test configuring memory limit."""
        server_mock = Mock()
        
        with patch.dict(os.environ, {
            'MCP_MONITOR_MEMORY': 'true',
            'MCP_MEMORY_LIMIT_MB': '1024'
        }):
            monitor = MemoryMonitor(server_mock)
            await monitor.initialize()
            
            assert monitor._memory_limit_mb == 1024
            
            await monitor.shutdown()
    
    @pytest.mark.asyncio
    async def test_error_handling(self, memory_monitor):
        """Test error handling in memory checks."""
        # Mock psutil to raise error
        with patch('psutil.Process') as MockProcess:
            MockProcess.side_effect = Exception("psutil error")
            
            # Should not crash
            usage = await memory_monitor.get_memory_usage()
            
            assert usage['error'] is not None
            assert 'psutil error' in usage['error']
    
    @pytest.mark.asyncio
    async def test_shutdown(self, memory_monitor):
        """Test memory monitor shutdown."""
        monitoring_task = memory_monitor._monitoring_task
        assert monitoring_task is not None
        assert not monitoring_task.cancelled()
        
        await memory_monitor.shutdown()
        
        assert monitoring_task.cancelled()
        assert memory_monitor._monitoring_task is None
        assert len(memory_monitor._memory_history) == 0