"""
Standard I/O transport implementation for MCP.

Provides stdin/stdout communication for subprocess-based MCP usage with support for:
- Async reading from stdin and writing to stdout
- Line-based message framing for JSON-RPC messages
- Process lifecycle management
- Proper buffering for large messages
- Both subprocess and direct stdio usage
"""

import asyncio
import json
import logging
import sys
from typing import AsyncIterator, Optional, TextIO, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import signal
from contextlib import contextmanager

from .base import Transport
from ..protocol.jsonrpc import JSONRPCParser, JSONRPCError, JSONRPCErrorCode

logger = logging.getLogger(__name__)


class ProcessState(Enum):
    """Process states for stdio transport."""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ProcessInfo:
    """Information about the stdio process."""
    pid: Optional[int]
    started_at: datetime
    state: ProcessState
    message_count: int = 0
    error_count: int = 0
    last_activity: datetime = field(default_factory=datetime.now)
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    def increment_messages(self):
        """Increment message count and update activity."""
        self.message_count += 1
        self.update_activity()
    
    def increment_errors(self):
        """Increment error count."""
        self.error_count += 1


class StdioTransport(Transport):
    """
    Standard I/O transport implementation for MCP.
    
    This transport handles communication through stdin/stdout with line-based
    JSON-RPC message framing. Each message must be a complete JSON object on
    a single line, terminated with a newline character.
    """
    
    def __init__(
        self,
        stdin: Optional[TextIO] = None,
        stdout: Optional[TextIO] = None,
        process: Optional[asyncio.subprocess.Process] = None,
        buffer_size: int = 65536,  # 64KB buffer
        max_message_size: int = 10 * 1024 * 1024,  # 10MB max message
        encoding: str = "utf-8"
    ):
        """
        Initialize stdio transport.
        
        Args:
            stdin: Input stream (defaults to sys.stdin)
            stdout: Output stream (defaults to sys.stdout)
            process: Optional subprocess.Process for subprocess mode
            buffer_size: Buffer size for reading
            max_message_size: Maximum message size in bytes
            encoding: Text encoding for messages
        """
        self._stdin = stdin or sys.stdin
        self._stdout = stdout or sys.stdout
        self._process = process
        self._buffer_size = buffer_size
        self._max_message_size = max_message_size
        self._encoding = encoding
        
        # Internal state
        self._closed = False
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._receive_queue: asyncio.Queue[str] = asyncio.Queue()
        self._reader_task: Optional[asyncio.Task] = None
        self._read_buffer = ""
        
        # Process info
        self.process_info = ProcessInfo(
            pid=process.pid if process else None,
            started_at=datetime.now(),
            state=ProcessState.STARTING
        )
        
        # Setup signal handlers for graceful shutdown
        if not process:  # Only for direct stdio mode
            self._setup_signal_handlers()
        
        logger.info(
            f"Stdio transport initialized (subprocess={bool(process)}, "
            f"pid={self.process_info.pid})"
        )
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown")
            asyncio.create_task(self.close())
        
        # Register handlers for common termination signals
        for sig in [signal.SIGTERM, signal.SIGINT]:
            try:
                signal.signal(sig, signal_handler)
            except Exception as e:
                logger.warning(f"Could not register handler for {sig}: {e}")
    
    async def _setup_streams(self):
        """Setup async streams for stdin/stdout."""
        if self._process:
            # Subprocess mode
            self._reader = self._process.stdout
            self._writer = self._process.stdin
        else:
            # Direct stdio mode
            loop = asyncio.get_event_loop()
            
            # Create stream reader for stdin
            self._reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(self._reader)
            await loop.connect_read_pipe(lambda: protocol, self._stdin)
            
            # Create stream writer for stdout
            transport, protocol = await loop.connect_write_pipe(
                lambda: asyncio.StreamReaderProtocol(asyncio.StreamReader()),
                self._stdout
            )
            self._writer = asyncio.StreamWriter(transport, protocol, self._reader, loop)
        
        self.process_info.state = ProcessState.RUNNING
        
        # Start reader task
        self._reader_task = asyncio.create_task(self._read_loop())
    
    async def send(self, message: str) -> None:
        """
        Send a message over stdio.
        
        Messages are sent as single lines terminated with newline.
        
        Args:
            message: JSON-RPC message to send
            
        Raises:
            ConnectionError: If transport is closed
            ValueError: If message exceeds max size or contains newlines
        """
        if self._closed:
            raise ConnectionError("Stdio transport is closed")
        
        # Ensure streams are setup
        if not self._writer:
            await self._setup_streams()
        
        # Validate message
        if '\n' in message or '\r' in message:
            raise ValueError("Message cannot contain newline characters")
        
        # Check message size
        message_bytes = message.encode(self._encoding)
        if len(message_bytes) > self._max_message_size:
            raise ValueError(
                f"Message size ({len(message_bytes)} bytes) exceeds maximum "
                f"({self._max_message_size} bytes)"
            )
        
        try:
            # Send message with newline terminator
            self._writer.write(message_bytes + b'\n')
            await self._writer.drain()
            
            self.process_info.increment_messages()
            logger.debug(f"Sent message via stdio: {len(message)} chars")
            
        except (BrokenPipeError, ConnectionError) as e:
            self.process_info.state = ProcessState.ERROR
            self.process_info.increment_errors()
            self._closed = True
            raise ConnectionError(f"Failed to send message: {e}")
        except Exception as e:
            self.process_info.increment_errors()
            logger.error(f"Error sending message: {e}")
            raise
    
    async def receive(self) -> AsyncIterator[str]:
        """
        Receive messages from stdio.
        
        Yields complete JSON-RPC messages read from stdin.
        
        Yields:
            Complete JSON-RPC messages as strings
            
        Raises:
            ConnectionError: If transport is closed or encounters an error
        """
        # Ensure streams are setup
        if not self._reader:
            await self._setup_streams()
        
        try:
            while not self._closed:
                try:
                    # Wait for a message with timeout
                    message = await asyncio.wait_for(
                        self._receive_queue.get(),
                        timeout=1.0
                    )
                    yield message
                except asyncio.TimeoutError:
                    # Check if process is still alive (subprocess mode)
                    if self._process and self._process.returncode is not None:
                        logger.info(
                            f"Subprocess exited with code {self._process.returncode}"
                        )
                        self._closed = True
                        self.process_info.state = ProcessState.STOPPED
                        break
                except Exception as e:
                    logger.error(f"Error receiving message: {e}")
                    self.process_info.increment_errors()
                    raise
        finally:
            # Cleanup is handled in close()
            pass
    
    async def _read_loop(self):
        """Background task to read messages from stdin."""
        try:
            while not self._closed:
                try:
                    # Read data with timeout
                    data = await asyncio.wait_for(
                        self._reader.read(self._buffer_size),
                        timeout=0.1
                    )
                    
                    if not data:
                        # EOF reached
                        logger.info("EOF reached on stdin")
                        break
                    
                    # Decode and add to buffer
                    text = data.decode(self._encoding, errors='replace')
                    self._read_buffer += text
                    
                    # Process complete lines
                    await self._process_buffer()
                    
                except asyncio.TimeoutError:
                    # Normal timeout, continue reading
                    continue
                except Exception as e:
                    logger.error(f"Error in read loop: {e}")
                    self.process_info.increment_errors()
                    if not isinstance(e, (asyncio.CancelledError, GeneratorExit)):
                        self.process_info.state = ProcessState.ERROR
                    break
                
        except asyncio.CancelledError:
            logger.debug("Read loop cancelled")
        finally:
            self._closed = True
            if self.process_info.state == ProcessState.RUNNING:
                self.process_info.state = ProcessState.STOPPED
    
    async def _process_buffer(self):
        """Process the read buffer to extract complete messages."""
        while '\n' in self._read_buffer:
            # Extract one line
            line, self._read_buffer = self._read_buffer.split('\n', 1)
            line = line.strip()
            
            if not line:
                # Skip empty lines
                continue
            
            # Validate JSON-RPC message
            try:
                # Parse JSON
                data = json.loads(line)
                
                # Validate as JSON-RPC
                try:
                    JSONRPCParser.parse_request(data)
                except JSONRPCError:
                    # Not a request, try response
                    try:
                        JSONRPCParser.parse_response(data)
                    except JSONRPCError as e:
                        logger.warning(f"Invalid JSON-RPC message: {e}")
                        self.process_info.increment_errors()
                        continue
                
                # Valid message, add to queue
                await self._receive_queue.put(line)
                self.process_info.increment_messages()
                
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in message: {e}")
                self.process_info.increment_errors()
                continue
    
    async def close(self) -> None:
        """Close the stdio transport and cleanup resources."""
        if self._closed:
            return
        
        logger.info("Closing stdio transport")
        self._closed = True
        self.process_info.state = ProcessState.STOPPING
        
        # Cancel reader task
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
        
        # Close streams
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception as e:
                logger.error(f"Error closing writer: {e}")
        
        # Terminate subprocess if needed
        if self._process:
            if self._process.returncode is None:
                # Process still running
                logger.info("Terminating subprocess")
                try:
                    self._process.terminate()
                    # Wait for process to exit
                    await asyncio.wait_for(self._process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    # Force kill if still running
                    logger.warning("Subprocess did not terminate, killing")
                    self._process.kill()
                    await self._process.wait()
                except Exception as e:
                    logger.error(f"Error terminating subprocess: {e}")
        
        self.process_info.state = ProcessState.STOPPED
        logger.info("Stdio transport closed")
    
    async def connect(self, **kwargs) -> None:
        """
        Establish the stdio connection.
        
        For stdio transport, this sets up the async streams and starts the reader task.
        
        Args:
            **kwargs: Additional connection parameters (unused for stdio)
            
        Raises:
            ConnectionError: If connection cannot be established
        """
        if self._closed:
            raise ConnectionError("Stdio transport is closed")
        
        try:
            # Setup streams if not already done
            if not self._reader or not self._writer:
                await self._setup_streams()
            
            # Ensure reader task is running
            if not self._reader_task or self._reader_task.done():
                self._reader_task = asyncio.create_task(self._read_loop())
            
            self.process_info.state = ProcessState.RUNNING
            self.process_info.update_activity()
            
            logger.info(f"Stdio transport connected (subprocess={self.is_subprocess}, pid={self.process_info.pid})")
            
        except Exception as e:
            self.process_info.state = ProcessState.ERROR
            self.process_info.increment_errors()
            raise ConnectionError(f"Failed to establish stdio connection: {e}")

    async def disconnect(self) -> None:
        """
        Gracefully disconnect the stdio transport.
        
        This is equivalent to close() for stdio connections.
        """
        await self.close()

    async def is_alive(self) -> bool:
        """
        Check if the stdio connection is alive and functional.
        
        Returns:
            True if the connection is alive and can send/receive messages
        """
        if self._closed:
            return False
        
        # Check process state
        if self.process_info.state in (ProcessState.ERROR, ProcessState.STOPPED):
            return False
        
        # For subprocess mode, check if process is still running
        if self._process:
            if self._process.returncode is not None:
                return False
        
        # Check if streams are available
        if not self._reader or not self._writer:
            return False
        
        # Check if reader task is running
        if not self._reader_task or self._reader_task.done():
            return False
        
        try:
            # Update activity timestamp when checking if alive
            self.process_info.update_activity()
            return self.process_info.state == ProcessState.RUNNING
        except Exception:
            return False

    @property
    def is_closed(self) -> bool:
        """Check if transport is closed."""
        return self._closed
    
    @property
    def is_subprocess(self) -> bool:
        """Check if this is a subprocess transport."""
        return self._process is not None


class StdioSubprocessTransport(StdioTransport):
    """
    Stdio transport specifically for subprocess communication.
    
    This class provides a convenient way to spawn a subprocess and communicate
    with it via stdio using the MCP protocol.
    """
    
    @classmethod
    async def spawn(
        cls,
        command: str,
        args: Optional[list] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        **transport_kwargs
    ) -> "StdioSubprocessTransport":
        """
        Spawn a subprocess and create a transport for it.
        
        Args:
            command: Command to execute
            args: Command arguments
            cwd: Working directory for subprocess
            env: Environment variables for subprocess
            **transport_kwargs: Additional arguments for StdioTransport
            
        Returns:
            StdioSubprocessTransport instance
            
        Raises:
            OSError: If subprocess cannot be started
        """
        # Prepare full command
        cmd = [command]
        if args:
            cmd.extend(args)
        
        logger.info(f"Spawning subprocess: {' '.join(cmd)}")
        
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env
            )
            
            # Create transport
            transport = cls(
                process=process,
                **transport_kwargs
            )
            
            # Start stderr reader
            asyncio.create_task(transport._read_stderr())
            
            return transport
            
        except Exception as e:
            logger.error(f"Failed to spawn subprocess: {e}")
            raise OSError(f"Failed to spawn subprocess: {e}")
    
    async def _read_stderr(self):
        """Read and log stderr from subprocess."""
        if not self._process or not self._process.stderr:
            return
        
        try:
            while not self._closed:
                line = await self._process.stderr.readline()
                if not line:
                    break
                
                # Log stderr output
                text = line.decode(self._encoding, errors='replace').strip()
                if text:
                    logger.info(f"Subprocess stderr: {text}")
                    
        except Exception as e:
            logger.error(f"Error reading stderr: {e}")
    
    async def wait(self) -> int:
        """
        Wait for subprocess to exit.
        
        Returns:
            Process exit code
        """
        if not self._process:
            return 0
        
        return await self._process.wait()


@contextmanager
def stdio_context():
    """
    Context manager to temporarily redirect stdio for transport usage.
    
    This is useful when using StdioTransport in a larger application that
    also uses stdio for other purposes.
    """
    # Save original streams
    original_stdin = sys.stdin
    original_stdout = sys.stdout
    
    try:
        # Could potentially redirect to pipes here if needed
        yield
    finally:
        # Restore original streams
        sys.stdin = original_stdin
        sys.stdout = original_stdout


# Example usage
async def example_direct_stdio():
    """Example of using stdio transport directly."""
    transport = StdioTransport()
    
    try:
        # Send a message
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"name": "stdio-example"},
            "id": 1
        }
        await transport.send(json.dumps(request))
        
        # Receive messages
        async for message in transport.receive():
            logger.info(f"Received: {message}")
            
            # Parse and handle message
            data = json.loads(message)
            if "method" in data:
                # Handle request
                response = {
                    "jsonrpc": "2.0",
                    "result": {"status": "ok"},
                    "id": data.get("id")
                }
                await transport.send(json.dumps(response))
                
    except KeyboardInterrupt:
        await transport.close()


async def example_subprocess():
    """Example of using stdio transport with subprocess."""
    # Spawn a subprocess
    transport = await StdioSubprocessTransport.spawn(
        "python",
        ["-m", "mcp_server.example_process"],
        env={"MCP_MODE": "subprocess"}
    )
    
    try:
        # Send initialization
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"name": "parent-process"},
            "id": 1
        }
        await transport.send(json.dumps(request))
        
        # Process messages
        async for message in transport.receive():
            logger.info(f"Subprocess message: {message}")
            
    except KeyboardInterrupt:
        await transport.close()
    
    # Wait for subprocess to exit
    exit_code = await transport.wait()
    logger.info(f"Subprocess exited with code {exit_code}")


if __name__ == "__main__":
    # Run example
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "subprocess":
        asyncio.run(example_subprocess())
    else:
        asyncio.run(example_direct_stdio())
