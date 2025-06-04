"""
Advanced MCP protocol features.

Implements sampling/completion, streaming, and batch operations.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, AsyncIterator, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid

from .errors import McpError, ErrorCode
from .jsonrpc import JsonRpcMessage, JsonRpcRequest, JsonRpcResponse, JsonRpcNotification

logger = logging.getLogger(__name__)


class SamplingMode(Enum):
    """Sampling modes for completion."""
    DETERMINISTIC = "deterministic"
    RANDOM = "random"
    TEMPERATURE = "temperature"
    TOP_K = "top_k"
    TOP_P = "top_p"


@dataclass
class SamplingConfig:
    """Configuration for sampling/completion."""
    mode: SamplingMode = SamplingMode.DETERMINISTIC
    temperature: float = 0.7
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    max_tokens: int = 100
    stop_sequences: List[str] = field(default_factory=list)
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0


@dataclass
class CompletionRequest:
    """Request for text completion."""
    prompt: str
    model: str = "default"
    sampling: SamplingConfig = field(default_factory=SamplingConfig)
    stream: bool = False
    context: Optional[Dict[str, Any]] = None


@dataclass
class CompletionChoice:
    """A completion choice."""
    text: str
    index: int
    finish_reason: str
    score: Optional[float] = None
    tokens: Optional[List[str]] = None


@dataclass
class CompletionResponse:
    """Response for text completion."""
    id: str
    choices: List[CompletionChoice]
    model: str
    created: float = field(default_factory=time.time)
    usage: Optional[Dict[str, int]] = None


@dataclass
class StreamingChunk:
    """A chunk in a streaming response."""
    id: str
    chunk_type: str
    data: Any
    index: int
    timestamp: float = field(default_factory=time.time)
    is_final: bool = False


@dataclass
class BatchRequest:
    """A batch request containing multiple operations."""
    id: str
    requests: List[JsonRpcRequest]
    parallel: bool = True
    max_concurrent: Optional[int] = None
    timeout: Optional[float] = None
    continue_on_error: bool = False


@dataclass
class BatchResponse:
    """Response for a batch request."""
    id: str
    responses: List[Union[JsonRpcResponse, McpError]]
    duration: float
    completed: int
    failed: int


class CompletionEngine:
    """Engine for text completion and sampling."""
    
    def __init__(self):
        self._models: Dict[str, Callable] = {}
        self._default_model = "echo"  # Simple echo model for testing
        self._register_default_models()
    
    def _register_default_models(self) -> None:
        """Register default models."""
        # Echo model - just returns the prompt
        async def echo_model(prompt: str, config: SamplingConfig) -> CompletionResponse:
            return CompletionResponse(
                id=str(uuid.uuid4()),
                choices=[
                    CompletionChoice(
                        text=f"Echo: {prompt}",
                        index=0,
                        finish_reason="complete"
                    )
                ],
                model="echo"
            )
        
        # Template model - basic template completion
        async def template_model(prompt: str, config: SamplingConfig) -> CompletionResponse:
            # Simple template completion
            if "function" in prompt.lower():
                completion = "def example_function():\n    pass"
            elif "class" in prompt.lower():
                completion = "class ExampleClass:\n    def __init__(self):\n        pass"
            elif "import" in prompt.lower():
                completion = "import os\nimport sys"
            else:
                completion = f"# Completion for: {prompt}\npass"
            
            return CompletionResponse(
                id=str(uuid.uuid4()),
                choices=[
                    CompletionChoice(
                        text=completion,
                        index=0,
                        finish_reason="complete"
                    )
                ],
                model="template"
            )
        
        self._models["echo"] = echo_model
        self._models["template"] = template_model
    
    def register_model(self, name: str, model_fn: Callable) -> None:
        """Register a model for completion."""
        self._models[name] = model_fn
        logger.info(f"Registered completion model: {name}")
    
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Generate completion for a request."""
        model_fn = self._models.get(request.model, self._models[self._default_model])
        
        try:
            response = await model_fn(request.prompt, request.sampling)
            logger.debug(f"Generated completion with model {request.model}")
            return response
        except Exception as e:
            logger.error(f"Completion error: {e}")
            raise McpError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Completion failed: {str(e)}"
            )
    
    async def stream_complete(self, request: CompletionRequest) -> AsyncIterator[StreamingChunk]:
        """Generate streaming completion."""
        try:
            # For demonstration, we'll simulate streaming by breaking response into chunks
            response = await self.complete(request)
            
            if response.choices:
                text = response.choices[0].text
                chunk_size = max(1, len(text) // 10)  # Break into ~10 chunks
                
                for i in range(0, len(text), chunk_size):
                    chunk_text = text[i:i + chunk_size]
                    is_final = i + chunk_size >= len(text)
                    
                    yield StreamingChunk(
                        id=response.id,
                        chunk_type="text",
                        data=chunk_text,
                        index=i // chunk_size,
                        is_final=is_final
                    )
                    
                    # Small delay to simulate streaming
                    await asyncio.sleep(0.1)
        
        except Exception as e:
            logger.error(f"Streaming completion error: {e}")
            yield StreamingChunk(
                id=str(uuid.uuid4()),
                chunk_type="error",
                data=str(e),
                index=0,
                is_final=True
            )


class StreamingManager:
    """Manager for streaming responses."""
    
    def __init__(self):
        self._active_streams: Dict[str, AsyncIterator] = {}
        self._stream_handlers: Dict[str, Callable] = {}
    
    def register_stream_handler(self, stream_type: str, handler: Callable) -> None:
        """Register a handler for a stream type."""
        self._stream_handlers[stream_type] = handler
        logger.info(f"Registered stream handler: {stream_type}")
    
    async def start_stream(self, stream_id: str, stream_type: str, 
                          params: Dict[str, Any]) -> None:
        """Start a new stream."""
        if stream_id in self._active_streams:
            raise McpError(
                code=ErrorCode.INVALID_PARAMS,
                message=f"Stream already exists: {stream_id}"
            )
        
        handler = self._stream_handlers.get(stream_type)
        if not handler:
            raise McpError(
                code=ErrorCode.METHOD_NOT_FOUND,
                message=f"Unknown stream type: {stream_type}"
            )
        
        try:
            stream = handler(params)
            self._active_streams[stream_id] = stream
            logger.info(f"Started stream {stream_id} of type {stream_type}")
        except Exception as e:
            logger.error(f"Failed to start stream {stream_id}: {e}")
            raise McpError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to start stream: {str(e)}"
            )
    
    async def get_stream_chunk(self, stream_id: str) -> Optional[StreamingChunk]:
        """Get next chunk from a stream."""
        stream = self._active_streams.get(stream_id)
        if not stream:
            return None
        
        try:
            chunk = await stream.__anext__()
            if chunk.is_final:
                await self.close_stream(stream_id)
            return chunk
        except StopAsyncIteration:
            await self.close_stream(stream_id)
            return None
        except Exception as e:
            logger.error(f"Stream {stream_id} error: {e}")
            await self.close_stream(stream_id)
            return StreamingChunk(
                id=stream_id,
                chunk_type="error",
                data=str(e),
                index=0,
                is_final=True
            )
    
    async def close_stream(self, stream_id: str) -> bool:
        """Close a stream."""
        if stream_id in self._active_streams:
            del self._active_streams[stream_id]
            logger.info(f"Closed stream {stream_id}")
            return True
        return False
    
    def get_active_streams(self) -> List[str]:
        """Get list of active stream IDs."""
        return list(self._active_streams.keys())
    
    async def close_all_streams(self) -> int:
        """Close all active streams."""
        count = len(self._active_streams)
        self._active_streams.clear()
        logger.info(f"Closed {count} streams")
        return count


class BatchProcessor:
    """Processor for batch operations."""
    
    def __init__(self, handler: Optional[Callable[[JsonRpcRequest], JsonRpcResponse]] = None):
        # Use a dummy handler if none provided (for testing)
        if handler is None:
            def dummy_handler(request):
                return JsonRpcResponse.success(request.id, {"status": "ok"})
            handler = dummy_handler
        
        self.handler = handler
        self._active_batches: Dict[str, asyncio.Task] = {}
    
    async def process_batch(self, batch: BatchRequest) -> BatchResponse:
        """Process a batch request."""
        if batch.id in self._active_batches:
            raise McpError(
                code=ErrorCode.INVALID_PARAMS,
                message=f"Batch already processing: {batch.id}"
            )
        
        start_time = time.time()
        
        try:
            if batch.parallel:
                responses = await self._process_parallel(batch)
            else:
                responses = await self._process_sequential(batch)
            
            duration = time.time() - start_time
            completed = sum(1 for r in responses if not isinstance(r, McpError))
            failed = len(responses) - completed
            
            return BatchResponse(
                id=batch.id,
                responses=responses,
                duration=duration,
                completed=completed,
                failed=failed
            )
        
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            raise McpError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Batch processing failed: {str(e)}"
            )
        finally:
            if batch.id in self._active_batches:
                del self._active_batches[batch.id]
    
    async def _process_parallel(self, batch: BatchRequest) -> List[Union[JsonRpcResponse, McpError]]:
        """Process batch requests in parallel."""
        # Limit concurrency
        max_concurrent = batch.max_concurrent or len(batch.requests)
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_request(request: JsonRpcRequest) -> Union[JsonRpcResponse, McpError]:
            async with semaphore:
                try:
                    if batch.timeout:
                        response = await asyncio.wait_for(
                            self.handler(request),
                            timeout=batch.timeout
                        )
                    else:
                        response = await self.handler(request)
                    return response
                except asyncio.TimeoutError:
                    return McpError(
                        code=ErrorCode.INTERNAL_ERROR,
                        message="Request timeout"
                    )
                except Exception as e:
                    if batch.continue_on_error:
                        return McpError(
                            code=ErrorCode.INTERNAL_ERROR,
                            message=str(e)
                        )
                    else:
                        raise
        
        # Create tasks
        tasks = [process_request(req) for req in batch.requests]
        
        # Store batch task for cancellation support
        batch_task = asyncio.create_task(asyncio.gather(*tasks, return_exceptions=True))
        self._active_batches[batch.id] = batch_task
        
        # Wait for completion
        results = await batch_task
        
        # Convert exceptions to errors
        responses = []
        for result in results:
            if isinstance(result, Exception):
                responses.append(McpError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=str(result)
                ))
            else:
                responses.append(result)
        
        return responses
    
    async def _process_sequential(self, batch: BatchRequest) -> List[Union[JsonRpcResponse, McpError]]:
        """Process batch requests sequentially."""
        responses = []
        
        for request in batch.requests:
            try:
                if batch.timeout:
                    response = await asyncio.wait_for(
                        self.handler(request),
                        timeout=batch.timeout
                    )
                else:
                    response = await self.handler(request)
                responses.append(response)
            except asyncio.TimeoutError:
                error = McpError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Request timeout"
                )
                responses.append(error)
                if not batch.continue_on_error:
                    break
            except Exception as e:
                error = McpError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=str(e)
                )
                responses.append(error)
                if not batch.continue_on_error:
                    break
        
        return responses
    
    async def cancel_batch(self, batch_id: str) -> bool:
        """Cancel a batch operation."""
        task = self._active_batches.get(batch_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self._active_batches[batch_id]
            logger.info(f"Cancelled batch {batch_id}")
            return True
        return False
    
    def get_active_batches(self) -> List[str]:
        """Get list of active batch IDs."""
        return list(self._active_batches.keys())


class AdvancedProtocolHandler:
    """Handler for advanced MCP protocol features."""
    
    def __init__(self, base_handler: Callable[[JsonRpcRequest], JsonRpcResponse]):
        self.base_handler = base_handler
        self.completion_engine = CompletionEngine()
        self.streaming_manager = StreamingManager()
        self.batch_processor = BatchProcessor(base_handler)
        
        # Register default stream handlers
        self._register_stream_handlers()
    
    def _register_stream_handlers(self) -> None:
        """Register default stream handlers."""
        # Completion streaming
        async def completion_stream(params: Dict[str, Any]) -> AsyncIterator[StreamingChunk]:
            request = CompletionRequest(**params)
            async for chunk in self.completion_engine.stream_complete(request):
                yield chunk
        
        # Log streaming (example)
        async def log_stream(params: Dict[str, Any]) -> AsyncIterator[StreamingChunk]:
            level = params.get("level", "INFO")
            count = 0
            while count < 10:  # Limit for demo
                yield StreamingChunk(
                    id=str(uuid.uuid4()),
                    chunk_type="log",
                    data=f"[{level}] Log message {count}",
                    index=count,
                    is_final=count == 9
                )
                count += 1
                await asyncio.sleep(0.5)
        
        self.streaming_manager.register_stream_handler("completion", completion_stream)
        self.streaming_manager.register_stream_handler("logs", log_stream)
    
    async def handle_completion(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle completion request."""
        try:
            request = CompletionRequest(**params)
            response = await self.completion_engine.complete(request)
            
            return {
                "id": response.id,
                "choices": [
                    {
                        "text": choice.text,
                        "index": choice.index,
                        "finish_reason": choice.finish_reason,
                        "score": choice.score
                    }
                    for choice in response.choices
                ],
                "model": response.model,
                "created": response.created,
                "usage": response.usage
            }
        except Exception as e:
            logger.error(f"Completion error: {e}")
            raise McpError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Completion failed: {str(e)}"
            )
    
    async def handle_stream_start(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stream start request."""
        stream_id = params.get("stream_id") or str(uuid.uuid4())
        stream_type = params.get("type")
        stream_params = params.get("params", {})
        
        if not stream_type:
            raise McpError(
                code=ErrorCode.INVALID_PARAMS,
                message="Missing stream type"
            )
        
        await self.streaming_manager.start_stream(stream_id, stream_type, stream_params)
        
        return {
            "stream_id": stream_id,
            "type": stream_type,
            "status": "started"
        }
    
    async def handle_stream_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stream read request."""
        stream_id = params.get("stream_id")
        if not stream_id:
            raise McpError(
                code=ErrorCode.INVALID_PARAMS,
                message="Missing stream_id"
            )
        
        chunk = await self.streaming_manager.get_stream_chunk(stream_id)
        
        if chunk:
            return {
                "stream_id": stream_id,
                "chunk": {
                    "id": chunk.id,
                    "type": chunk.chunk_type,
                    "data": chunk.data,
                    "index": chunk.index,
                    "timestamp": chunk.timestamp,
                    "is_final": chunk.is_final
                }
            }
        else:
            return {
                "stream_id": stream_id,
                "chunk": None,
                "status": "ended"
            }
    
    async def handle_stream_close(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stream close request."""
        stream_id = params.get("stream_id")
        if not stream_id:
            raise McpError(
                code=ErrorCode.INVALID_PARAMS,
                message="Missing stream_id"
            )
        
        closed = await self.streaming_manager.close_stream(stream_id)
        
        return {
            "stream_id": stream_id,
            "closed": closed
        }
    
    async def handle_batch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle batch request."""
        try:
            batch = BatchRequest(**params)
            response = await self.batch_processor.process_batch(batch)
            
            return {
                "id": response.id,
                "responses": [
                    r.to_dict() if hasattr(r, 'to_dict') else {"error": str(r)}
                    for r in response.responses
                ],
                "duration": response.duration,
                "completed": response.completed,
                "failed": response.failed
            }
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            raise McpError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Batch processing failed: {str(e)}"
            )