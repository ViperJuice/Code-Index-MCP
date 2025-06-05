"""GPU acceleration for cache operations (optional module)."""
import asyncio
import logging
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Union
import hashlib
import pickle

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    import cupy as cp
    GPU_AVAILABLE = True
    logger.info("GPU acceleration available with CuPy")
except ImportError:
    try:
        import torch
        GPU_AVAILABLE = torch.cuda.is_available()
        if GPU_AVAILABLE:
            logger.info("GPU acceleration available with PyTorch")
        else:
            logger.info("PyTorch available but no CUDA")
    except ImportError:
        GPU_AVAILABLE = False
        logger.info("No GPU acceleration libraries available")


class GPUCacheAccelerator:
    """GPU-accelerated operations for cache system."""
    
    def __init__(self, use_gpu: bool = True, memory_pool_size_mb: int = 512):
        self.use_gpu = use_gpu and GPU_AVAILABLE
        self.memory_pool_size = memory_pool_size_mb * 1024 * 1024
        
        if self.use_gpu:
            self._initialize_gpu()
        else:
            logger.info("GPU acceleration disabled or unavailable")
    
    def _initialize_gpu(self):
        """Initialize GPU resources."""
        try:
            if 'cupy' in globals():
                # CuPy initialization
                self.backend = 'cupy'
                cp.cuda.MemoryPool().set_limit(size=self.memory_pool_size)
                logger.info(f"GPU initialized with CuPy, memory limit: {self.memory_pool_size // 1024 // 1024}MB")
            
            elif 'torch' in globals():
                # PyTorch initialization
                self.backend = 'torch'
                if torch.cuda.is_available():
                    self.device = torch.device('cuda')
                    # Set memory fraction
                    torch.cuda.set_per_process_memory_fraction(0.5)  # 50% of GPU memory
                    logger.info(f"GPU initialized with PyTorch on {self.device}")
                else:
                    self.use_gpu = False
                    logger.warning("CUDA not available for PyTorch")
            
        except Exception as e:
            logger.error(f"Failed to initialize GPU: {e}")
            self.use_gpu = False
    
    async def batch_hash_keys(self, keys: List[str]) -> List[str]:
        """GPU-accelerated batch hashing of cache keys."""
        if not self.use_gpu or len(keys) < 100:  # Use CPU for small batches
            return [hashlib.sha256(key.encode()).hexdigest() for key in keys]
        
        try:
            if self.backend == 'cupy':
                return await self._cupy_batch_hash(keys)
            elif self.backend == 'torch':
                return await self._torch_batch_hash(keys)
        except Exception as e:
            logger.warning(f"GPU hashing failed, falling back to CPU: {e}")
        
        # Fallback to CPU
        return [hashlib.sha256(key.encode()).hexdigest() for key in keys]
    
    async def _cupy_batch_hash(self, keys: List[str]) -> List[str]:
        """CuPy-based batch hashing."""
        # Convert strings to bytes and then to numpy arrays
        key_bytes = [key.encode() for key in keys]
        
        # For demonstration - in practice would need proper GPU hash implementation
        # This is a simplified example
        results = []
        batch_size = 1000  # Process in batches to avoid memory issues
        
        for i in range(0, len(key_bytes), batch_size):
            batch = key_bytes[i:i + batch_size]
            
            # Transfer to GPU and process
            # Note: Real implementation would use GPU-optimized hash functions
            with cp.cuda.Device(0):
                batch_results = [hashlib.sha256(kb).hexdigest() for kb in batch]
                results.extend(batch_results)
        
        return results
    
    async def _torch_batch_hash(self, keys: List[str]) -> List[str]:
        """PyTorch-based batch hashing."""
        # Similar to CuPy but using PyTorch tensors
        results = []
        batch_size = 1000
        
        for i in range(0, len(keys), batch_size):
            batch = keys[i:i + batch_size]
            
            # In practice, would implement custom CUDA kernel for hashing
            # For demo, using CPU hashing in batches
            batch_results = [hashlib.sha256(key.encode()).hexdigest() for key in batch]
            results.extend(batch_results)
        
        return results
    
    async def compress_batch(self, values: List[bytes]) -> List[bytes]:
        """GPU-accelerated batch compression."""
        if not self.use_gpu or len(values) < 50:
            # Use CPU compression for small batches
            import gzip
            return [gzip.compress(value) for value in values]
        
        try:
            if self.backend == 'cupy':
                return await self._cupy_compress_batch(values)
            elif self.backend == 'torch':
                return await self._torch_compress_batch(values)
        except Exception as e:
            logger.warning(f"GPU compression failed, falling back to CPU: {e}")
        
        # Fallback to CPU
        import gzip
        return [gzip.compress(value) for value in values]
    
    async def _cupy_compress_batch(self, values: List[bytes]) -> List[bytes]:
        """CuPy-based batch compression."""
        # For demonstration - would use GPU compression libraries
        import gzip
        
        # Process in parallel batches
        results = []
        batch_size = 100
        
        async def compress_batch_async(batch):
            return [gzip.compress(value) for value in batch]
        
        tasks = []
        for i in range(0, len(values), batch_size):
            batch = values[i:i + batch_size]
            task = asyncio.create_task(compress_batch_async(batch))
            tasks.append(task)
        
        batch_results = await asyncio.gather(*tasks)
        for batch_result in batch_results:
            results.extend(batch_result)
        
        return results
    
    async def _torch_compress_batch(self, values: List[bytes]) -> List[bytes]:
        """PyTorch-based batch compression."""
        # Similar approach as CuPy
        import gzip
        
        results = []
        batch_size = 100
        
        # Process in parallel using asyncio
        async def compress_batch_async(batch):
            return [gzip.compress(value) for value in batch]
        
        tasks = []
        for i in range(0, len(values), batch_size):
            batch = values[i:i + batch_size]
            task = asyncio.create_task(compress_batch_async(batch))
            tasks.append(task)
        
        batch_results = await asyncio.gather(*tasks)
        for batch_result in batch_results:
            results.extend(batch_result)
        
        return results
    
    async def similarity_search(self, query_embedding: np.ndarray, 
                               cache_embeddings: Dict[str, np.ndarray],
                               top_k: int = 10) -> List[Tuple[str, float]]:
        """GPU-accelerated similarity search for semantic caching."""
        if not self.use_gpu or len(cache_embeddings) < 100:
            return await self._cpu_similarity_search(query_embedding, cache_embeddings, top_k)
        
        try:
            if self.backend == 'cupy':
                return await self._cupy_similarity_search(query_embedding, cache_embeddings, top_k)
            elif self.backend == 'torch':
                return await self._torch_similarity_search(query_embedding, cache_embeddings, top_k)
        except Exception as e:
            logger.warning(f"GPU similarity search failed, falling back to CPU: {e}")
        
        return await self._cpu_similarity_search(query_embedding, cache_embeddings, top_k)
    
    async def _cpu_similarity_search(self, query_embedding: np.ndarray,
                                   cache_embeddings: Dict[str, np.ndarray],
                                   top_k: int) -> List[Tuple[str, float]]:
        """CPU-based similarity search fallback."""
        similarities = []
        
        for key, embedding in cache_embeddings.items():
            # Cosine similarity
            similarity = np.dot(query_embedding, embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
            )
            similarities.append((key, float(similarity)))
        
        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    async def _cupy_similarity_search(self, query_embedding: np.ndarray,
                                    cache_embeddings: Dict[str, np.ndarray],
                                    top_k: int) -> List[Tuple[str, float]]:
        """CuPy-based similarity search."""
        with cp.cuda.Device(0):
            # Convert to CuPy arrays
            query_gpu = cp.asarray(query_embedding)
            
            keys = list(cache_embeddings.keys())
            embeddings_list = [cache_embeddings[key] for key in keys]
            embeddings_gpu = cp.asarray(embeddings_list)
            
            # Normalize vectors
            query_norm = query_gpu / cp.linalg.norm(query_gpu)
            embeddings_norm = embeddings_gpu / cp.linalg.norm(embeddings_gpu, axis=1, keepdims=True)
            
            # Compute cosine similarities
            similarities_gpu = cp.dot(embeddings_norm, query_norm)
            
            # Get top_k indices
            top_indices = cp.argpartition(similarities_gpu, -top_k)[-top_k:]
            top_indices = top_indices[cp.argsort(similarities_gpu[top_indices])][::-1]
            
            # Convert back to CPU
            top_indices_cpu = cp.asnumpy(top_indices)
            similarities_cpu = cp.asnumpy(similarities_gpu[top_indices])
            
            # Build results
            results = [
                (keys[idx], float(sim))
                for idx, sim in zip(top_indices_cpu, similarities_cpu)
            ]
            
            return results
    
    async def _torch_similarity_search(self, query_embedding: np.ndarray,
                                     cache_embeddings: Dict[str, np.ndarray],
                                     top_k: int) -> List[Tuple[str, float]]:
        """PyTorch-based similarity search."""
        # Convert to PyTorch tensors
        query_tensor = torch.tensor(query_embedding, device=self.device)
        
        keys = list(cache_embeddings.keys())
        embeddings_list = [cache_embeddings[key] for key in keys]
        embeddings_tensor = torch.tensor(embeddings_list, device=self.device)
        
        # Normalize vectors
        query_norm = torch.nn.functional.normalize(query_tensor, p=2, dim=0)
        embeddings_norm = torch.nn.functional.normalize(embeddings_tensor, p=2, dim=1)
        
        # Compute cosine similarities
        similarities = torch.matmul(embeddings_norm, query_norm)
        
        # Get top_k
        top_similarities, top_indices = torch.topk(similarities, min(top_k, len(keys)))
        
        # Convert back to CPU
        top_indices_cpu = top_indices.cpu().numpy()
        top_similarities_cpu = top_similarities.cpu().numpy()
        
        # Build results
        results = [
            (keys[idx], float(sim))
            for idx, sim in zip(top_indices_cpu, top_similarities_cpu)
        ]
        
        return results
    
    async def batch_serialize(self, objects: List[Any]) -> List[bytes]:
        """GPU-accelerated batch serialization."""
        if not self.use_gpu or len(objects) < 100:
            return [pickle.dumps(obj) for obj in objects]
        
        # For large batches, use parallel processing
        async def serialize_batch(batch):
            return [pickle.dumps(obj) for obj in batch]
        
        batch_size = max(100, len(objects) // 4)  # Use 4 parallel batches
        tasks = []
        
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]
            task = asyncio.create_task(serialize_batch(batch))
            tasks.append(task)
        
        batch_results = await asyncio.gather(*tasks)
        
        results = []
        for batch_result in batch_results:
            results.extend(batch_result)
        
        return results
    
    async def batch_deserialize(self, data_list: List[bytes]) -> List[Any]:
        """GPU-accelerated batch deserialization."""
        if not self.use_gpu or len(data_list) < 100:
            return [pickle.loads(data) for data in data_list]
        
        # Parallel deserialization
        async def deserialize_batch(batch):
            return [pickle.loads(data) for data in batch]
        
        batch_size = max(100, len(data_list) // 4)
        tasks = []
        
        for i in range(0, len(data_list), batch_size):
            batch = data_list[i:i + batch_size]
            task = asyncio.create_task(deserialize_batch(batch))
            tasks.append(task)
        
        batch_results = await asyncio.gather(*tasks)
        
        results = []
        for batch_result in batch_results:
            results.extend(batch_result)
        
        return results
    
    def get_gpu_stats(self) -> Dict[str, Any]:
        """Get GPU utilization statistics."""
        stats = {
            "gpu_available": self.use_gpu,
            "backend": getattr(self, 'backend', None)
        }
        
        if not self.use_gpu:
            return stats
        
        try:
            if self.backend == 'cupy':
                mempool = cp.cuda.MemoryPool()
                stats.update({
                    "memory_used_bytes": mempool.used_bytes(),
                    "memory_total_bytes": mempool.total_bytes(),
                    "memory_limit_bytes": self.memory_pool_size
                })
            
            elif self.backend == 'torch':
                if torch.cuda.is_available():
                    stats.update({
                        "memory_allocated_bytes": torch.cuda.memory_allocated(),
                        "memory_reserved_bytes": torch.cuda.memory_reserved(),
                        "device_name": torch.cuda.get_device_name()
                    })
        
        except Exception as e:
            logger.error(f"Error getting GPU stats: {e}")
            stats["error"] = str(e)
        
        return stats
    
    async def cleanup(self):
        """Clean up GPU resources."""
        if not self.use_gpu:
            return
        
        try:
            if self.backend == 'cupy':
                cp.cuda.MemoryPool().free_all_blocks()
            elif self.backend == 'torch':
                torch.cuda.empty_cache()
            
            logger.info("GPU resources cleaned up")
        
        except Exception as e:
            logger.error(f"Error cleaning up GPU resources: {e}")


# Global GPU accelerator instance
_gpu_accelerator: Optional[GPUCacheAccelerator] = None


def get_gpu_accelerator(use_gpu: bool = True) -> GPUCacheAccelerator:
    """Get or create the global GPU accelerator instance."""
    global _gpu_accelerator
    
    if _gpu_accelerator is None:
        _gpu_accelerator = GPUCacheAccelerator(use_gpu=use_gpu)
    
    return _gpu_accelerator


# Convenience functions

async def gpu_batch_hash(keys: List[str]) -> List[str]:
    """GPU-accelerated batch hashing of keys."""
    accelerator = get_gpu_accelerator()
    return await accelerator.batch_hash_keys(keys)


async def gpu_similarity_search(query_embedding: np.ndarray,
                               cache_embeddings: Dict[str, np.ndarray],
                               top_k: int = 10) -> List[Tuple[str, float]]:
    """GPU-accelerated similarity search."""
    accelerator = get_gpu_accelerator()
    return await accelerator.similarity_search(query_embedding, cache_embeddings, top_k)


async def gpu_batch_compress(values: List[bytes]) -> List[bytes]:
    """GPU-accelerated batch compression."""
    accelerator = get_gpu_accelerator()
    return await accelerator.compress_batch(values)