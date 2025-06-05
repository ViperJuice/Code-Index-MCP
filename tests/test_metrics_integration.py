"""
Tests for metrics collection integration.
"""
import os
import asyncio
import time
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from mcp_server.features.metrics_integration import MetricsCollector


class TestMetricsCollector:
    """Test metrics collection integration."""
    
    @pytest.fixture
    async def metrics_collector(self):
        """Create metrics collector instance."""
        server_mock = Mock()
        server_mock.session_manager = Mock()
        server_mock.storage = Mock()
        
        # Enable metrics for this fixture
        with patch.dict(os.environ, {'MCP_ENABLE_METRICS': 'true'}):
            collector = MetricsCollector(server_mock)
            await collector.initialize()
            yield collector
            await collector.shutdown()
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test metrics collector initialization."""
        server_mock = Mock()
        collector = MetricsCollector(server_mock)
        
        assert not collector.enabled
        assert len(collector._metrics) == 0
        
        # Enable and initialize
        with patch.dict(os.environ, {'MCP_ENABLE_METRICS': 'true'}):
            collector = MetricsCollector(server_mock)
            await collector.initialize()
            
            assert collector.enabled
            assert 'requests' in collector._metrics
            assert 'errors' in collector._metrics
            assert 'indexed_files' in collector._metrics
    
    @pytest.mark.asyncio
    async def test_record_request_metrics(self, metrics_collector):
        """Test recording request metrics."""
        # Record several requests
        await metrics_collector.record_request_metrics('tools/call', 0.1, 'success')
        await metrics_collector.record_request_metrics('tools/call', 0.2, 'success')
        await metrics_collector.record_request_metrics('tools/list', 0.05, 'success')
        await metrics_collector.record_request_metrics('tools/call', 0.15, 'error')
        
        # Check metrics
        metrics = metrics_collector._metrics
        
        assert metrics['requests']['total'] == 4
        assert metrics['requests']['by_method']['tools/call'] == 3
        assert metrics['requests']['by_method']['tools/list'] == 1
        assert metrics['errors']['total'] == 1
        assert metrics['errors']['by_method']['tools/call'] == 1
        
        # Check response times
        assert len(metrics['response_times']['all']) == 4
        assert len(metrics['response_times']['by_method']['tools/call']) == 3
    
    @pytest.mark.asyncio
    async def test_update_index_metrics(self, metrics_collector):
        """Test updating index metrics."""
        # Mock storage to return index stats
        metrics_collector.server.storage = AsyncMock()
        metrics_collector.server.storage.get_stats = AsyncMock(
            return_value={
                'total_files': 150,
                'total_symbols': 1200,
                'last_indexed': time.time()
            }
        )
        
        await metrics_collector.update_index_metrics()
        
        metrics = metrics_collector._metrics
        assert metrics['indexed_files']['count'] == 150
        assert metrics['indexed_symbols']['count'] == 1200
        assert metrics['last_index_update'] > 0
    
    @pytest.mark.asyncio
    async def test_session_metrics(self, metrics_collector):
        """Test session-related metrics."""
        # Mock session manager
        mock_sessions = [
            Mock(id='session1', created_at=time.time() - 300),
            Mock(id='session2', created_at=time.time() - 100),
        ]
        metrics_collector.server.session_manager.get_active_sessions = Mock(
            return_value=mock_sessions
        )
        
        await metrics_collector.update_session_metrics()
        
        metrics = metrics_collector._metrics
        assert metrics['sessions']['active'] == 2
        assert metrics['sessions']['total'] >= 2
    
    @pytest.mark.asyncio
    async def test_memory_metrics(self, metrics_collector):
        """Test memory usage metrics."""
        with patch('psutil.Process') as MockProcess:
            mock_process = Mock()
            mock_process.memory_info.return_value = Mock(rss=200 * 1024 * 1024)  # 200MB
            MockProcess.return_value = mock_process
            
            await metrics_collector.update_memory_metrics()
            
            metrics = metrics_collector._metrics
            assert metrics['memory']['current_mb'] == 200
            assert metrics['memory']['peak_mb'] >= 200
    
    @pytest.mark.asyncio
    async def test_get_metrics_summary(self, metrics_collector):
        """Test getting metrics summary."""
        # Add some test data
        await metrics_collector.record_request_metrics('test', 0.1, 'success')
        await metrics_collector.record_request_metrics('test', 0.2, 'error')
        
        summary = await metrics_collector.get_metrics_summary()
        
        assert 'requests' in summary
        assert summary['requests']['total'] == 2
        assert summary['requests']['success_rate'] == 0.5
        assert 'average_response_time' in summary
        assert 'errors' in summary
        assert summary['errors']['total'] == 1
    
    @pytest.mark.asyncio
    async def test_prometheus_format(self, metrics_collector):
        """Test Prometheus metrics format export."""
        # Add test data
        await metrics_collector.record_request_metrics('tools/call', 0.1, 'success')
        
        prometheus_data = await metrics_collector.export_prometheus_format()
        
        assert isinstance(prometheus_data, str)
        assert '# HELP' in prometheus_data
        assert '# TYPE' in prometheus_data
        assert 'mcp_requests_total' in prometheus_data
        assert 'mcp_response_time_seconds' in prometheus_data
    
    @pytest.mark.asyncio
    async def test_metrics_persistence(self, metrics_collector):
        """Test metrics persistence across restarts."""
        # Record some metrics
        await metrics_collector.record_request_metrics('test', 0.1, 'success')
        
        # Save metrics
        await metrics_collector.save_metrics()
        
        # Create new collector and load
        new_collector = MetricsCollector(metrics_collector.server)
        await new_collector.initialize()
        await new_collector.load_metrics()
        
        # Verify metrics were loaded
        assert new_collector._metrics['requests']['total'] == 1
    
    @pytest.mark.asyncio
    async def test_metrics_reset(self, metrics_collector):
        """Test resetting metrics."""
        # Add data
        await metrics_collector.record_request_metrics('test', 0.1, 'success')
        assert metrics_collector._metrics['requests']['total'] > 0
        
        # Reset
        await metrics_collector.reset_metrics()
        
        # Verify reset
        assert metrics_collector._metrics['requests']['total'] == 0
        assert len(metrics_collector._metrics['response_times']['all']) == 0
    
    @pytest.mark.asyncio
    async def test_rate_calculation(self, metrics_collector):
        """Test rate calculations."""
        # Record requests over time
        for i in range(10):
            await metrics_collector.record_request_metrics('test', 0.1, 'success')
            await asyncio.sleep(0.1)
        
        summary = await metrics_collector.get_metrics_summary()
        
        assert 'request_rate' in summary
        assert summary['request_rate'] > 0
    
    @pytest.mark.asyncio
    async def test_percentile_calculations(self, metrics_collector):
        """Test response time percentile calculations."""
        # Record various response times
        times = [0.01, 0.02, 0.03, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0]
        for t in times:
            await metrics_collector.record_request_metrics('test', t, 'success')
        
        percentiles = metrics_collector._calculate_percentiles(
            metrics_collector._metrics['response_times']['all']
        )
        
        assert 'p50' in percentiles
        assert 'p95' in percentiles
        assert 'p99' in percentiles
        assert percentiles['p50'] < percentiles['p95']
        assert percentiles['p95'] < percentiles['p99']
    
    @pytest.mark.asyncio
    async def test_disabled_metrics(self):
        """Test metrics collector when disabled."""
        server_mock = Mock()
        
        with patch.dict(os.environ, {'MCP_ENABLE_METRICS': 'false'}):
            collector = MetricsCollector(server_mock)
            await collector.initialize()
            
            assert not collector.enabled
            
            # Should not record metrics
            await collector.record_request_metrics('test', 0.1, 'success')
            assert len(collector._metrics) == 0
    
    @pytest.mark.asyncio
    async def test_metrics_server_endpoint(self, metrics_collector):
        """Test metrics server endpoint setup."""
        with patch.dict(os.environ, {'MCP_METRICS_PORT': '9090'}):
            # Mock aiohttp server setup
            with patch('aiohttp.web.Application') as MockApp, \
                 patch('aiohttp.web.run_app') as mock_run:
                
                await metrics_collector._start_metrics_server()
                
                MockApp.assert_called_once()
                # Verify routes were added
                app_instance = MockApp.return_value
                app_instance.router.add_get.assert_called()
    
    @pytest.mark.asyncio
    async def test_concurrent_metric_updates(self, metrics_collector):
        """Test concurrent metric updates."""
        # Multiple concurrent updates
        tasks = []
        for i in range(100):
            tasks.append(
                metrics_collector.record_request_metrics(f'method_{i%5}', 0.1, 'success')
            )
        
        await asyncio.gather(*tasks)
        
        # Verify all were recorded
        assert metrics_collector._metrics['requests']['total'] == 100