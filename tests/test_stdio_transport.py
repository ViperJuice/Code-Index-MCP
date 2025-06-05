"""
Tests for the stdio transport implementation.
"""

import asyncio
import json
import pytest
import sys
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch

from mcp_server.transport.stdio import (
    StdioTransport,
    StdioSubprocessTransport,
    ProcessState,
    ProcessInfo,
    stdio_context
)


class TestStdioTransport:
    """Tests for StdioTransport class."""
    
    def test_init_direct_mode(self):
        """Test initialization in direct stdio mode."""
        transport = StdioTransport()
        
        assert transport._stdin == sys.stdin
        assert transport._stdout == sys.stdout
        assert transport._process is None
        assert not transport.is_closed
        assert not transport.is_subprocess
        assert transport.process_info.state == ProcessState.STARTING
        assert transport.process_info.pid is None
    
    def test_init_subprocess_mode(self):
        """Test initialization in subprocess mode."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.stdout = Mock()
        mock_process.stdin = Mock()
        
        transport = StdioTransport(process=mock_process)
        
        assert transport._process == mock_process
        assert transport.is_subprocess
        assert transport.process_info.pid == 12345
    
    @pytest.mark.asyncio
    async def test_send_message_validation(self):
        """Test message validation in send method."""
        transport = StdioTransport()
        
        # Test newline rejection
        with pytest.raises(ValueError, match="cannot contain newline"):
            await transport.send("message\nwith\nnewlines")
        
        # Test carriage return rejection
        with pytest.raises(ValueError, match="cannot contain newline"):
            await transport.send("message\rwith\rreturns")
        
        # Test oversized message
        huge_message = "x" * (11 * 1024 * 1024)  # 11MB
        with pytest.raises(ValueError, match="exceeds maximum"):
            await transport.send(huge_message)
        
        await transport.close()
    
    @pytest.mark.asyncio
    async def test_send_when_closed(self):
        """Test sending when transport is closed."""
        transport = StdioTransport()
        await transport.close()
        
        with pytest.raises(ConnectionError, match="closed"):
            await transport.send("test")
    
    @pytest.mark.asyncio
    async def test_message_buffering(self):
        """Test message buffering and line parsing."""
        transport = StdioTransport()
        
        # Test partial message
        transport._read_buffer = '{"jsonrpc":"2.0","method":"test"'
        await transport._process_buffer()
        assert transport._receive_queue.empty()
        
        # Complete the message
        transport._read_buffer += ',"id":1}\n'
        await transport._process_buffer()
        
        # Should have one message
        assert not transport._receive_queue.empty()
        message = await transport._receive_queue.get()
        data = json.loads(message)
        assert data["method"] == "test"
        assert data["id"] == 1
        
        await transport.close()
    
    @pytest.mark.asyncio
    async def test_multiple_messages_in_buffer(self):
        """Test handling multiple messages in buffer."""
        transport = StdioTransport()
        
        # Add multiple complete messages
        transport._read_buffer = (
            '{"jsonrpc":"2.0","method":"first","id":1}\n'
            '{"jsonrpc":"2.0","method":"second","id":2}\n'
            '{"jsonrpc":"2.0","method":"third","id":3}\n'
        )
        
        await transport._process_buffer()
        
        # Should have three messages
        messages = []
        while not transport._receive_queue.empty():
            messages.append(await transport._receive_queue.get())
        
        assert len(messages) == 3
        assert json.loads(messages[0])["method"] == "first"
        assert json.loads(messages[1])["method"] == "second"
        assert json.loads(messages[2])["method"] == "third"
        
        await transport.close()
    
    @pytest.mark.asyncio
    async def test_invalid_json_handling(self):
        """Test handling of invalid JSON in buffer."""
        transport = StdioTransport()
        
        # Invalid JSON
        transport._read_buffer = 'not valid json\n'
        await transport._process_buffer()
        
        # Should not add to queue and should increment errors
        assert transport._receive_queue.empty()
        assert transport.process_info.error_count > 0
        
        await transport.close()
    
    @pytest.mark.asyncio
    async def test_invalid_jsonrpc_handling(self):
        """Test handling of valid JSON but invalid JSON-RPC."""
        transport = StdioTransport()
        
        # Valid JSON but not JSON-RPC
        transport._read_buffer = '{"not":"jsonrpc"}\n'
        await transport._process_buffer()
        
        # Should not add to queue and should increment errors
        assert transport._receive_queue.empty()
        assert transport.process_info.error_count > 0
        
        await transport.close()
    
    @pytest.mark.asyncio
    async def test_empty_lines_ignored(self):
        """Test that empty lines are ignored."""
        transport = StdioTransport()
        
        transport._read_buffer = '\n\n{"jsonrpc":"2.0","method":"test","id":1}\n\n'
        await transport._process_buffer()
        
        # Should have only one message
        assert transport._receive_queue.qsize() == 1
        
        await transport.close()
    
    @pytest.mark.asyncio
    async def test_process_info_tracking(self):
        """Test process info tracking."""
        transport = StdioTransport()
        
        # Mock successful send
        transport._writer = AsyncMock()
        transport.process_info.state = ProcessState.RUNNING
        
        initial_count = transport.process_info.message_count
        await transport.send('{"test":"message"}')
        
        assert transport.process_info.message_count == initial_count + 1
        assert transport.process_info.last_activity > transport.process_info.started_at
        
        await transport.close()


class TestStdioSubprocessTransport:
    """Tests for StdioSubprocessTransport class."""
    
    @pytest.mark.asyncio
    async def test_spawn_subprocess(self):
        """Test spawning a subprocess."""
        # Create a simple echo script
        echo_script = '''
import sys
import json
for line in sys.stdin:
    data = json.loads(line.strip())
    response = {"jsonrpc": "2.0", "result": {"echo": data}, "id": data.get("id")}
    print(json.dumps(response))
    sys.stdout.flush()
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(echo_script)
            script_path = f.name
        
        try:
            # Spawn subprocess
            transport = await StdioSubprocessTransport.spawn(
                sys.executable,
                [script_path]
            )
            
            assert transport.is_subprocess
            assert transport.process_info.pid is not None
            assert transport.process_info.state == ProcessState.RUNNING
            
            # Test communication
            request = {"jsonrpc": "2.0", "method": "test", "id": 1}
            await transport.send(json.dumps(request))
            
            # Get response
            received = False
            async for message in transport.receive():
                data = json.loads(message)
                assert data["id"] == 1
                assert "echo" in data.get("result", {})
                received = True
                break
            
            assert received, "Should have received response"
            
            # Close and wait
            await transport.close()
            exit_code = await transport.wait()
            assert exit_code in (-15, 0)  # SIGTERM or clean exit
            
        finally:
            os.unlink(script_path)
    
    @pytest.mark.asyncio
    async def test_spawn_failure(self):
        """Test handling of subprocess spawn failure."""
        with pytest.raises(OSError):
            await StdioSubprocessTransport.spawn(
                "/nonexistent/command",
                ["arg1", "arg2"]
            )
    
    @pytest.mark.asyncio
    async def test_subprocess_stderr_logging(self):
        """Test that stderr is logged from subprocess."""
        # Create a script that writes to stderr
        stderr_script = '''
import sys
sys.stderr.write("Error message\\n")
sys.stderr.flush()
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(stderr_script)
            script_path = f.name
        
        try:
            transport = await StdioSubprocessTransport.spawn(
                sys.executable,
                [script_path]
            )
            
            # Give time for stderr to be read
            await asyncio.sleep(0.1)
            
            await transport.close()
            await transport.wait()
            
        finally:
            os.unlink(script_path)


def test_stdio_context():
    """Test stdio_context context manager."""
    original_stdin = sys.stdin
    original_stdout = sys.stdout
    
    with stdio_context():
        # Should preserve original streams
        assert sys.stdin == original_stdin
        assert sys.stdout == original_stdout
    
    # Should restore after context
    assert sys.stdin == original_stdin
    assert sys.stdout == original_stdout


def test_process_state_enum():
    """Test ProcessState enum values."""
    assert ProcessState.STARTING.value == "starting"
    assert ProcessState.RUNNING.value == "running"
    assert ProcessState.STOPPING.value == "stopping"
    assert ProcessState.STOPPED.value == "stopped"
    assert ProcessState.ERROR.value == "error"


def test_process_info():
    """Test ProcessInfo dataclass."""
    info = ProcessInfo(
        pid=12345,
        started_at=asyncio.get_event_loop().time(),
        state=ProcessState.RUNNING
    )
    
    assert info.pid == 12345
    assert info.message_count == 0
    assert info.error_count == 0
    
    # Test increment methods
    info.increment_messages()
    assert info.message_count == 1
    
    info.increment_errors()
    assert info.error_count == 1
    
    # Test activity tracking
    old_activity = info.last_activity
    info.update_activity()
    assert info.last_activity >= old_activity