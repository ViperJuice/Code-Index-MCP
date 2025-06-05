"""
Utility functions for embedding providers

Common functionality shared across providers.
"""

import hashlib
import re
from typing import List, Tuple, Optional, Any, Dict
import tiktoken
import logging

logger = logging.getLogger(__name__)


def estimate_tokens_default(text: str, chars_per_token: float = 4.0) -> int:
    """
    Default token estimation based on character count
    
    Args:
        text: Text to estimate
        chars_per_token: Average characters per token
        
    Returns:
        Estimated token count
    """
    return max(1, int(len(text) / chars_per_token))


def estimate_tokens_tiktoken(texts: List[str], model: str = "cl100k_base") -> int:
    """
    Estimate tokens using tiktoken (OpenAI's tokenizer)
    
    Args:
        texts: List of texts
        model: Encoding model name
        
    Returns:
        Total token count
    """
    try:
        encoding = tiktoken.get_encoding(model)
        total = 0
        for text in texts:
            total += len(encoding.encode(text))
        return total
    except Exception as e:
        logger.warning(f"Failed to use tiktoken: {e}, falling back to default estimation")
        return sum(estimate_tokens_default(text) for text in texts)


def split_text_by_tokens(
    text: str,
    max_tokens: int,
    overlap_tokens: int = 50,
    model: str = "cl100k_base"
) -> List[str]:
    """
    Split text into chunks by token count
    
    Args:
        text: Text to split
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Number of overlapping tokens
        model: Tokenizer model
        
    Returns:
        List of text chunks
    """
    try:
        encoding = tiktoken.get_encoding(model)
        tokens = encoding.encode(text)
        
        chunks = []
        start = 0
        
        while start < len(tokens):
            end = min(start + max_tokens, len(tokens))
            chunk_tokens = tokens[start:end]
            chunks.append(encoding.decode(chunk_tokens))
            
            # Move start with overlap
            start = end - overlap_tokens if end < len(tokens) else end
            
        return chunks
        
    except Exception as e:
        logger.warning(f"Failed to split with tiktoken: {e}, using character split")
        return split_text_by_chars(text, max_tokens * 4, overlap_tokens * 4)


def split_text_by_chars(
    text: str,
    max_chars: int,
    overlap_chars: int = 200
) -> List[str]:
    """
    Split text into chunks by character count
    
    Args:
        text: Text to split
        max_chars: Maximum characters per chunk
        overlap_chars: Number of overlapping characters
        
    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + max_chars, len(text))
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence end
            sentence_end = text.rfind('.', start, end)
            if sentence_end > start + max_chars // 2:
                end = sentence_end + 1
        
        chunks.append(text[start:end])
        
        # Move start with overlap
        start = end - overlap_chars if end < len(text) else end
    
    return chunks


def preprocess_code_text(text: str, language: Optional[str] = None) -> str:
    """
    Preprocess code text for embedding
    
    Args:
        text: Code text
        language: Programming language (optional)
        
    Returns:
        Preprocessed text
    """
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    
    # Remove comments if requested (basic implementation)
    if language in ['python', 'py']:
        # Remove Python comments
        text = re.sub(r'#.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'"""[\s\S]*?"""', '', text)
        text = re.sub(r"'''[\s\S]*?'''", '', text)
    elif language in ['javascript', 'js', 'typescript', 'ts']:
        # Remove JS comments
        text = re.sub(r'//.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'/\*[\s\S]*?\*/', '', text)
    
    # Trim
    return text.strip()


def generate_cache_key(
    text: str,
    model: str,
    embedding_type: str,
    version: str = "v1"
) -> str:
    """
    Generate a cache key for an embedding
    
    Args:
        text: Original text
        model: Model name
        embedding_type: Type of embedding
        version: Cache version
        
    Returns:
        Cache key string
    """
    # Create a hash of the text
    text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
    
    # Combine with other parameters
    key_parts = [
        "emb",
        version,
        model.replace('/', '-'),
        embedding_type,
        text_hash
    ]
    
    return ":".join(key_parts)


def batch_texts(
    texts: List[str],
    batch_size: int,
    max_tokens_per_batch: Optional[int] = None
) -> List[List[str]]:
    """
    Batch texts by count and optionally by token limit
    
    Args:
        texts: List of texts to batch
        batch_size: Maximum texts per batch
        max_tokens_per_batch: Optional maximum tokens per batch
        
    Returns:
        List of batches
    """
    if not max_tokens_per_batch:
        # Simple batching by count
        return [
            texts[i:i + batch_size]
            for i in range(0, len(texts), batch_size)
        ]
    
    # Batching by token limit
    batches = []
    current_batch = []
    current_tokens = 0
    
    for text in texts:
        text_tokens = estimate_tokens_default(text)
        
        # Check if adding this text would exceed limits
        if current_batch and (
            len(current_batch) >= batch_size or
            current_tokens + text_tokens > max_tokens_per_batch
        ):
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0
        
        current_batch.append(text)
        current_tokens += text_tokens
    
    if current_batch:
        batches.append(current_batch)
    
    return batches


def normalize_embedding(embedding: List[float]) -> List[float]:
    """
    Normalize embedding vector to unit length
    
    Args:
        embedding: Embedding vector
        
    Returns:
        Normalized embedding
    """
    import math
    
    # Calculate magnitude
    magnitude = math.sqrt(sum(x * x for x in embedding))
    
    # Avoid division by zero
    if magnitude == 0:
        return embedding
    
    # Normalize
    return [x / magnitude for x in embedding]


def validate_embeddings(
    embeddings: List[List[float]],
    expected_dim: int,
    normalize: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Validate embedding dimensions and optionally normalize
    
    Args:
        embeddings: List of embedding vectors
        expected_dim: Expected dimension
        normalize: Whether to normalize vectors
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not embeddings:
        return False, "Empty embeddings list"
    
    for i, emb in enumerate(embeddings):
        if len(emb) != expected_dim:
            return False, f"Embedding {i} has dimension {len(emb)}, expected {expected_dim}"
        
        if normalize:
            embeddings[i] = normalize_embedding(emb)
    
    return True, None


def truncate_text_to_tokens(
    text: str,
    max_tokens: int,
    model: str = "cl100k_base"
) -> str:
    """
    Truncate text to maximum token count
    
    Args:
        text: Text to truncate
        max_tokens: Maximum tokens
        model: Tokenizer model
        
    Returns:
        Truncated text
    """
    try:
        encoding = tiktoken.get_encoding(model)
        tokens = encoding.encode(text)
        
        if len(tokens) <= max_tokens:
            return text
        
        # Truncate and decode
        truncated_tokens = tokens[:max_tokens]
        return encoding.decode(truncated_tokens)
        
    except Exception as e:
        logger.warning(f"Failed to truncate with tiktoken: {e}")
        # Fallback to character truncation
        estimated_chars = max_tokens * 4
        return text[:estimated_chars]


def merge_metadata(
    base_metadata: Dict[str, Any],
    *additional_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge multiple metadata dictionaries
    
    Args:
        base_metadata: Base metadata dict
        *additional_metadata: Additional metadata dicts to merge
        
    Returns:
        Merged metadata
    """
    result = base_metadata.copy()
    
    for metadata in additional_metadata:
        if metadata:
            result.update(metadata)
    
    return result