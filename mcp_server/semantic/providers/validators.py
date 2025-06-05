"""
Input validators for embedding providers

Validates inputs before processing to ensure data quality and prevent errors.
"""

import re
from typing import List, Tuple, Optional, Any, Dict
from pathlib import Path

from .exceptions import ValidationError


def validate_api_key(
    api_key: Optional[str],
    provider: str,
    required_prefix: Optional[str] = None,
    min_length: int = 20
) -> Tuple[bool, Optional[str]]:
    """
    Validate an API key format
    
    Args:
        api_key: API key to validate
        provider: Provider name for error messages
        required_prefix: Optional required prefix (e.g., 'sk-' for OpenAI)
        min_length: Minimum key length
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not api_key:
        return False, f"No API key provided for {provider}"
    
    if not isinstance(api_key, str):
        return False, f"API key must be a string for {provider}"
    
    if len(api_key) < min_length:
        return False, f"API key too short for {provider} (minimum {min_length} characters)"
    
    if required_prefix and not api_key.startswith(required_prefix):
        return False, f"API key for {provider} must start with '{required_prefix}'"
    
    # Check for common placeholder values
    if api_key.lower() in ['your-api-key', 'your-api-key-here', 'xxx', 'todo']:
        return False, f"API key appears to be a placeholder for {provider}"
    
    return True, None


def validate_model_name(
    model_name: str,
    supported_models: List[str],
    allow_custom: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Validate model name
    
    Args:
        model_name: Model name to validate
        supported_models: List of supported models
        allow_custom: Whether to allow custom model names
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not model_name:
        return False, "Model name cannot be empty"
    
    if not isinstance(model_name, str):
        return False, "Model name must be a string"
    
    if not allow_custom and model_name not in supported_models:
        return False, f"Model '{model_name}' not supported. Available: {', '.join(supported_models)}"
    
    return True, None


def validate_dimension(
    dimension: int,
    allowed_dimensions: Optional[List[int]] = None,
    min_dimension: int = 1,
    max_dimension: int = 4096
) -> Tuple[bool, Optional[str]]:
    """
    Validate embedding dimension
    
    Args:
        dimension: Dimension to validate
        allowed_dimensions: Optional list of allowed dimensions
        min_dimension: Minimum dimension
        max_dimension: Maximum dimension
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(dimension, int):
        return False, "Dimension must be an integer"
    
    if dimension < min_dimension:
        return False, f"Dimension must be at least {min_dimension}"
    
    if dimension > max_dimension:
        return False, f"Dimension cannot exceed {max_dimension}"
    
    if allowed_dimensions and dimension not in allowed_dimensions:
        return False, f"Dimension must be one of: {allowed_dimensions}"
    
    return True, None


def validate_batch_size(
    batch_size: int,
    max_batch_size: int = 2048,
    min_batch_size: int = 1
) -> Tuple[bool, Optional[str]]:
    """
    Validate batch size
    
    Args:
        batch_size: Batch size to validate
        max_batch_size: Maximum allowed batch size
        min_batch_size: Minimum allowed batch size
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(batch_size, int):
        return False, "Batch size must be an integer"
    
    if batch_size < min_batch_size:
        return False, f"Batch size must be at least {min_batch_size}"
    
    if batch_size > max_batch_size:
        return False, f"Batch size cannot exceed {max_batch_size}"
    
    return True, None


def validate_texts(
    texts: List[str],
    max_length: Optional[int] = None,
    min_length: int = 1,
    max_count: int = 10000
) -> Tuple[bool, Optional[str]]:
    """
    Validate a list of texts
    
    Args:
        texts: List of texts to validate
        max_length: Maximum length per text
        min_length: Minimum length per text
        max_count: Maximum number of texts
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(texts, list):
        return False, "Texts must be a list"
    
    if not texts:
        return False, "Texts list cannot be empty"
    
    if len(texts) > max_count:
        return False, f"Too many texts ({len(texts)}), maximum is {max_count}"
    
    for i, text in enumerate(texts):
        if not isinstance(text, str):
            return False, f"Text at index {i} is not a string"
        
        if len(text) < min_length:
            return False, f"Text at index {i} is too short (minimum {min_length} characters)"
        
        if max_length and len(text) > max_length:
            return False, f"Text at index {i} is too long (maximum {max_length} characters)"
    
    return True, None


def validate_local_model_path(
    model_path: str,
    must_exist: bool = True
) -> Tuple[bool, Optional[str]]:
    """
    Validate local model path
    
    Args:
        model_path: Path to model directory or file
        must_exist: Whether the path must exist
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not model_path:
        return False, "Model path cannot be empty"
    
    path = Path(model_path)
    
    if must_exist and not path.exists():
        return False, f"Model path does not exist: {model_path}"
    
    if path.exists() and not (path.is_dir() or path.is_file()):
        return False, f"Model path is neither a file nor directory: {model_path}"
    
    return True, None


def validate_url(
    url: str,
    require_https: bool = False,
    allowed_hosts: Optional[List[str]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate URL format
    
    Args:
        url: URL to validate
        require_https: Whether to require HTTPS
        allowed_hosts: Optional list of allowed hosts
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "URL cannot be empty"
    
    # Basic URL pattern
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    if not url_pattern.match(url):
        return False, "Invalid URL format"
    
    if require_https and not url.startswith('https://'):
        return False, "URL must use HTTPS"
    
    if allowed_hosts:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.hostname not in allowed_hosts:
            return False, f"Host '{parsed.hostname}' not in allowed hosts: {allowed_hosts}"
    
    return True, None


def validate_cache_config(
    cache_config: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """
    Validate cache configuration
    
    Args:
        cache_config: Cache configuration dict
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(cache_config, dict):
        return False, "Cache config must be a dictionary"
    
    # Validate TTL
    if 'ttl' in cache_config:
        ttl = cache_config['ttl']
        if not isinstance(ttl, (int, float)) or ttl <= 0:
            return False, "Cache TTL must be a positive number"
    
    # Validate max size
    if 'max_size' in cache_config:
        max_size = cache_config['max_size']
        if not isinstance(max_size, int) or max_size <= 0:
            return False, "Cache max_size must be a positive integer"
    
    # Validate backend
    if 'backend' in cache_config:
        backend = cache_config['backend']
        allowed_backends = ['memory', 'redis', 'disk']
        if backend not in allowed_backends:
            return False, f"Cache backend must be one of: {allowed_backends}"
    
    return True, None


class InputValidator:
    """Convenience class for validating multiple inputs"""
    
    def __init__(self):
        self.errors: List[str] = []
    
    def validate_api_key(self, api_key: Optional[str], provider: str, **kwargs) -> 'InputValidator':
        """Validate API key and collect errors"""
        valid, error = validate_api_key(api_key, provider, **kwargs)
        if not valid:
            self.errors.append(error)
        return self
    
    def validate_model_name(self, model_name: str, supported_models: List[str], **kwargs) -> 'InputValidator':
        """Validate model name and collect errors"""
        valid, error = validate_model_name(model_name, supported_models, **kwargs)
        if not valid:
            self.errors.append(error)
        return self
    
    def validate_texts(self, texts: List[str], **kwargs) -> 'InputValidator':
        """Validate texts and collect errors"""
        valid, error = validate_texts(texts, **kwargs)
        if not valid:
            self.errors.append(error)
        return self
    
    def validate_dimension(self, dimension: int, **kwargs) -> 'InputValidator':
        """Validate dimension and collect errors"""
        valid, error = validate_dimension(dimension, **kwargs)
        if not valid:
            self.errors.append(error)
        return self
    
    def is_valid(self) -> bool:
        """Check if all validations passed"""
        return len(self.errors) == 0
    
    def raise_if_invalid(self) -> None:
        """Raise ValidationError if any validation failed"""
        if self.errors:
            raise ValidationError(f"Validation failed: {'; '.join(self.errors)}")