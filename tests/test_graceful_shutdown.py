"""
Tests for graceful shutdown integration.
"""
import os
import asyncio
import signal
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from mcp_server.features.graceful_shutdown import GracefulShutdown


class TestGracefulShutdown:
    """Test graceful shutdown integration."""
    
    @pytest.fixture
    async def graceful_shutdown(self):
        """Create graceful shutdown instance."""
        server_mock = Mock()
        server_mock.shutdown = AsyncMock()
        
        shutdown = GracefulShutdown(server_mock)
        await shutdown.initialize()
        yield shutdown
        # Don't call shutdown.shutdown() here as it's being tested
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test graceful shutdown initialization."""
        server_mock = Mock()
        shutdown = GracefulShutdown(server_mock)
        
        assert not shutdown._shutdown_requested
        assert shutdown._active_operations == 0
        
        await shutdown.initialize()
        
        # Should have registered signal handlers
        assert shutdown._original_sigint is not None
        assert shutdown._original_sigterm is not None
    
    @pytest.mark.asyncio
    async def test_shutdown_request(self, graceful_shutdown):
        """Test requesting shutdown."""
        assert not graceful_shutdown.is_shutdown_requested()
        
        graceful_shutdown.request_shutdown()
        
        assert graceful_shutdown.is_shutdown_requested()
        assert graceful_shutdown._shutdown_event.is_set()
    
    @pytest.mark.asyncio
    async def test_track_operation(self, graceful_shutdown):
        """Test tracking active operations."""
        assert graceful_shutdown._active_operations == 0
        
        # Start tracking an operation
        async def test_operation():
            await asyncio.sleep(0.1)
            return "result"
        
        # Track operation
        result = await graceful_shutdown.track_operation(test_operation())
        
        assert result == "result"
        assert graceful_shutdown._active_operations == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_tracking(self, graceful_shutdown):
        """Test tracking multiple concurrent operations."""
        async def slow_operation(n):
            await asyncio.sleep(0.1)
            return n
        
        # Start multiple operations
        tasks = []
        for i in range(5):
            tasks.append(
                asyncio.create_task(
                    graceful_shutdown.track_operation(slow_operation(i))
                )
            )
        
        # Check active operations while running
        await asyncio.sleep(0.05)
        assert graceful_shutdown._active_operations == 5
        
        # Wait for completion
        results = await asyncio.gather(*tasks)
        assert results == [0, 1, 2, 3, 4]
        assert graceful_shutdown._active_operations == 0
    
    @pytest.mark.asyncio
    async def test_wait_for_operations(self, graceful_shutdown):
        """Test waiting for active operations to complete."""
        # Start some operations
        async def slow_op():
            await asyncio.sleep(0.2)
        
        # Start operations without awaiting
        for i in range(3):
            asyncio.create_task(
                graceful_shutdown.track_operation(slow_op())
            )
        
        await asyncio.sleep(0.05)  # Let them start
        assert graceful_shutdown._active_operations > 0
        
        # Wait for all to complete
        await graceful_shutdown.wait_for_operations(timeout=1.0)
        
        assert graceful_shutdown._active_operations == 0
    
    @pytest.mark.asyncio
    async def test_wait_for_operations_timeout(self, graceful_shutdown):
        """Test timeout while waiting for operations."""
        # Start a very slow operation
        async def very_slow_op():
            await asyncio.sleep(2.0)
        
        asyncio.create_task(
            graceful_shutdown.track_operation(very_slow_op())
        )
        
        await asyncio.sleep(0.05)  # Let it start
        
        # Wait with short timeout
        start_time = asyncio.get_event_loop().time()
        await graceful_shutdown.wait_for_operations(timeout=0.1)
        elapsed = asyncio.get_event_loop().time() - start_time
        
        # Should timeout
        assert elapsed < 0.5
        assert graceful_shutdown._active_operations > 0
    
    @pytest.mark.asyncio
    async def test_signal_handling(self, graceful_shutdown):
        """Test signal handler registration."""
        # Mock signal handlers
        with patch('signal.signal') as mock_signal:
            shutdown = GracefulShutdown(graceful_shutdown.server)
            await shutdown.initialize()
            
            # Should register handlers for SIGINT and SIGTERM
            calls = mock_signal.call_args_list
            signals_registered = [call[0][0] for call in calls]
            
            assert signal.SIGINT in signals_registered
            assert signal.SIGTERM in signals_registered
    
    @pytest.mark.asyncio
    async def test_handle_shutdown_signal(self, graceful_shutdown):
        """Test handling shutdown signal."""
        # Simulate signal
        graceful_shutdown._handle_signal(signal.SIGINT, None)
        
        assert graceful_shutdown.is_shutdown_requested()
    
    @pytest.mark.asyncio
    async def test_multiple_signals_handling(self, graceful_shutdown):
        """Test handling multiple shutdown signals."""
        force_shutdown_called = False
        
        def mock_force_shutdown():
            nonlocal force_shutdown_called
            force_shutdown_called = True
            os._exit(1)
        
        with patch('os._exit', mock_force_shutdown):
            # First signal - graceful
            graceful_shutdown._handle_signal(signal.SIGINT, None)
            assert graceful_shutdown._shutdown_count == 1
            
            # Second signal - force
            graceful_shutdown._handle_signal(signal.SIGINT, None)
            assert force_shutdown_called
    
    @pytest.mark.asyncio
    async def test_shutdown_sequence(self, graceful_shutdown):
        """Test complete shutdown sequence."""
        # Track shutdown steps
        steps = []
        
        async def mock_server_shutdown():
            steps.append('server_shutdown')
        
        graceful_shutdown.server.shutdown = mock_server_shutdown
        
        # Add some active operations
        async def operation():
            steps.append('operation_start')
            await asyncio.sleep(0.1)
            steps.append('operation_end')
        
        task = asyncio.create_task(
            graceful_shutdown.track_operation(operation())
        )
        
        await asyncio.sleep(0.05)  # Let operation start
        
        # Trigger shutdown
        shutdown_task = asyncio.create_task(graceful_shutdown.shutdown())
        
        # Wait for everything
        await task
        await shutdown_task
        
        # Verify sequence
        assert 'operation_start' in steps
        assert 'operation_end' in steps
        assert 'server_shutdown' in steps
        assert steps.index('operation_end') < steps.index('server_shutdown')
    
    @pytest.mark.asyncio
    async def test_wait_for_shutdown(self, graceful_shutdown):
        """Test waiting for shutdown signal."""
        wait_task = asyncio.create_task(
            graceful_shutdown.wait_for_shutdown()
        )
        
        # Should be waiting
        await asyncio.sleep(0.05)
        assert not wait_task.done()
        
        # Request shutdown
        graceful_shutdown.request_shutdown()
        
        # Should complete
        await wait_task
        assert wait_task.done()
    
    @pytest.mark.asyncio
    async def test_cleanup_resources(self, graceful_shutdown):
        """Test resource cleanup during shutdown."""
        cleanup_called = False
        
        async def cleanup_callback():
            nonlocal cleanup_called
            cleanup_called = True
        
        graceful_shutdown.add_cleanup_callback(cleanup_callback)
        
        await graceful_shutdown.shutdown()
        
        assert cleanup_called
    
    @pytest.mark.asyncio
    async def test_restore_signal_handlers(self, graceful_shutdown):
        """Test restoring original signal handlers."""
        # Store original handlers
        original_sigint = graceful_shutdown._original_sigint
        original_sigterm = graceful_shutdown._original_sigterm
        
        with patch('signal.signal') as mock_signal:
            await graceful_shutdown.shutdown()
            
            # Should restore original handlers
            calls = mock_signal.call_args_list
            assert any(
                call[0] == (signal.SIGINT, original_sigint)
                for call in calls
            )
            assert any(
                call[0] == (signal.SIGTERM, original_sigterm)
                for call in calls
            )
    
    @pytest.mark.asyncio
    async def test_shutdown_with_errors(self, graceful_shutdown):
        """Test shutdown continues despite errors."""
        # Mock server shutdown to raise error
        graceful_shutdown.server.shutdown = AsyncMock(
            side_effect=Exception("Shutdown error")
        )
        
        # Should not raise
        await graceful_shutdown.shutdown()
        
        # Should still complete shutdown process
        assert graceful_shutdown.is_shutdown_requested()
    
    @pytest.mark.asyncio
    async def test_operation_error_handling(self, graceful_shutdown):
        """Test error handling in tracked operations."""
        async def failing_operation():
            await asyncio.sleep(0.05)
            raise ValueError("Operation failed")
        
        # Should propagate error but still track properly
        with pytest.raises(ValueError):
            await graceful_shutdown.track_operation(failing_operation())
        
        # Should have cleaned up tracking
        assert graceful_shutdown._active_operations == 0