"""Contextual embeddings service using Claude for enhanced semantic understanding."""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from anthropic import AsyncAnthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    AsyncAnthropic = None

from .document_interfaces import ChunkType, DocumentChunk

logger = logging.getLogger(__name__)


class DocumentCategory(Enum):
    """Categories of documents for context generation."""

    CODE = "code"
    DOCUMENTATION = "documentation"
    TUTORIAL = "tutorial"
    REFERENCE = "reference"
    CONFIGURATION = "configuration"
    GENERAL = "general"


@dataclass
class ContextGenerationMetrics:
    """Metrics for context generation."""

    total_chunks: int = 0
    processed_chunks: int = 0
    cached_chunks: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_cost: float = 0.0
    processing_time: float = 0.0
    errors: List[str] = field(default_factory=list)

    def add_usage(self, input_tokens: int, output_tokens: int):
        """Add token usage and calculate cost."""
        self.total_tokens_input += input_tokens
        self.total_tokens_output += output_tokens
        # Claude 3.5 Sonnet pricing (as of 2024)
        # Input: $3 per million tokens, Output: $15 per million tokens
        self.total_cost += (input_tokens * 0.003 + output_tokens * 0.015) / 1000


@dataclass
class ContextPromptTemplate:
    """Template for generating contextual prompts."""

    category: DocumentCategory
    system_prompt: str
    user_prompt_template: str
    examples: List[Dict[str, str]] = field(default_factory=list)

    def format_user_prompt(self, chunk: DocumentChunk, document_context: Dict[str, Any]) -> str:
        """Format the user prompt with chunk and document context."""
        return self.user_prompt_template.format(
            content=chunk.content,
            chunk_type=chunk.type.value,
            section_hierarchy=" > ".join(chunk.metadata.section_hierarchy),
            document_path=chunk.metadata.document_path,
            **document_context,
        )


class PromptTemplateRegistry:
    """Registry of prompt templates for different document types."""

    def __init__(self):
        self.templates = self._initialize_templates()

    def _initialize_templates(self) -> Dict[DocumentCategory, ContextPromptTemplate]:
        """Initialize default prompt templates."""
        return {
            DocumentCategory.CODE: ContextPromptTemplate(
                category=DocumentCategory.CODE,
                system_prompt="""You are an expert code analyst. Generate a concise, searchable context 
                for the given code chunk that captures its purpose, functionality, and relationships 
                to other parts of the codebase. Focus on making the content easily discoverable through 
                semantic search.""",
                user_prompt_template="""Analyze this code chunk and provide a brief context (2-3 sentences):

File: {document_path}
Location: {section_hierarchy}
Type: {chunk_type}

Code:
{content}

Include: main purpose, key functions/classes, dependencies, and search-relevant keywords.""",
            ),
            DocumentCategory.DOCUMENTATION: ContextPromptTemplate(
                category=DocumentCategory.DOCUMENTATION,
                system_prompt="""You are a technical documentation expert. Generate searchable context 
                that captures the key concepts, purpose, and relationships of this documentation chunk.""",
                user_prompt_template="""Provide context for this documentation chunk (2-3 sentences):

Document: {document_path}
Section: {section_hierarchy}

Content:
{content}

Focus on: main topic, key concepts, related topics, and searchable terms.""",
            ),
            DocumentCategory.TUTORIAL: ContextPromptTemplate(
                category=DocumentCategory.TUTORIAL,
                system_prompt="""You are an educational content expert. Generate context that helps 
                users find relevant tutorial content based on what they want to learn or accomplish.""",
                user_prompt_template="""Generate learning-focused context for this tutorial chunk (2-3 sentences):

Tutorial: {document_path}
Section: {section_hierarchy}

Content:
{content}

Include: learning objectives, prerequisites, skills taught, and problem-solving keywords.""",
            ),
            DocumentCategory.REFERENCE: ContextPromptTemplate(
                category=DocumentCategory.REFERENCE,
                system_prompt="""You are a technical reference expert. Generate precise, searchable 
                context for API references, configuration options, and technical specifications.""",
                user_prompt_template="""Create reference context for this chunk (2-3 sentences):

Reference: {document_path}
Section: {section_hierarchy}

Content:
{content}

Focus on: API/config names, parameters, return values, use cases, and technical terms.""",
            ),
            DocumentCategory.CONFIGURATION: ContextPromptTemplate(
                category=DocumentCategory.CONFIGURATION,
                system_prompt="""You are a configuration expert. Generate context that helps users 
                find specific configuration options and understand their purpose.""",
                user_prompt_template="""Provide configuration context for this chunk (2-3 sentences):

Config File: {document_path}
Section: {section_hierarchy}

Content:
{content}

Include: option names, purposes, valid values, dependencies, and common use cases.""",
            ),
            DocumentCategory.GENERAL: ContextPromptTemplate(
                category=DocumentCategory.GENERAL,
                system_prompt="""You are a content analysis expert. Generate searchable context 
                that captures the essence and purpose of this content.""",
                user_prompt_template="""Generate context for this content chunk (2-3 sentences):

File: {document_path}
Section: {section_hierarchy}

Content:
{content}

Focus on: main topic, key points, relationships, and relevant search terms.""",
            ),
        }

    def get_template(self, category: DocumentCategory) -> ContextPromptTemplate:
        """Get template for a specific category."""
        return self.templates.get(category, self.templates[DocumentCategory.GENERAL])


class ContextCache:
    """Cache for generated contexts to avoid redundant API calls."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path.home() / ".cache" / "mcp_server" / "contexts"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.memory_cache: Dict[str, str] = {}

    def _get_cache_key(self, chunk: DocumentChunk, template_category: DocumentCategory) -> str:
        """Generate cache key for a chunk."""
        content_hash = hashlib.sha256(
            f"{chunk.content}{chunk.metadata.document_path}{template_category.value}".encode()
        ).hexdigest()
        return content_hash[:16]

    def get(self, chunk: DocumentChunk, template_category: DocumentCategory) -> Optional[str]:
        """Get cached context if available."""
        cache_key = self._get_cache_key(chunk, template_category)

        # Check memory cache first
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]

        # Check disk cache
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with cache_file.open("r") as f:
                    data = json.load(f)
                    context = data.get("context")
                    self.memory_cache[cache_key] = context
                    return context
            except Exception as e:
                logger.warning(f"Failed to load cache file {cache_file}: {e}")

        return None

    def set(self, chunk: DocumentChunk, template_category: DocumentCategory, context: str):
        """Cache generated context."""
        cache_key = self._get_cache_key(chunk, template_category)

        # Update memory cache
        self.memory_cache[cache_key] = context

        # Save to disk
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with cache_file.open("w") as f:
                json.dump(
                    {
                        "context": context,
                        "chunk_id": chunk.id,
                        "document_path": chunk.metadata.document_path,
                        "timestamp": datetime.now().isoformat(),
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.warning(f"Failed to save cache file {cache_file}: {e}")


class ContextualEmbeddingService:
    """Service for generating contextual embeddings using Claude."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        max_concurrent_requests: int = 5,
        cache_dir: Optional[Path] = None,
        enable_prompt_caching: bool = True,
    ):
        """
        Initialize the contextual embedding service.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use
            max_concurrent_requests: Maximum concurrent API requests
            cache_dir: Directory for caching contexts
            enable_prompt_caching: Whether to use Anthropic's prompt caching
        """
        if not ANTHROPIC_AVAILABLE:
            logger.warning("Anthropic package not installed. Install with: pip install anthropic")
            self.client = None
        else:
            self.client = AsyncAnthropic(api_key=api_key)

        self.model = model
        self.max_concurrent_requests = max_concurrent_requests
        self.enable_prompt_caching = enable_prompt_caching

        self.template_registry = PromptTemplateRegistry()
        self.cache = ContextCache(cache_dir)
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)

        # Track metrics
        self.current_metrics = ContextGenerationMetrics()

    def detect_document_category(
        self, chunk: DocumentChunk, document_path: str
    ) -> DocumentCategory:
        """Detect the category of a document based on its content and path."""
        path_lower = document_path.lower()

        # Check by file extension and common patterns (order matters)
        if any(ext in path_lower for ext in [".py", ".js", ".java", ".cpp", ".go", ".rs"]):
            return DocumentCategory.CODE
        elif any(ext in path_lower for ext in [".yaml", ".yml", ".json", ".toml", ".ini"]):
            return DocumentCategory.CONFIGURATION
        elif any(name in path_lower for name in ["tutorial", "getting-started", "quickstart"]):
            return DocumentCategory.TUTORIAL
        elif any(name in path_lower for name in ["api", "reference", "spec"]):
            return DocumentCategory.REFERENCE
        elif any(name in path_lower for name in ["readme", "guide"]):
            # Could be tutorial or documentation, check content
            content_lower = chunk.content.lower()
            if any(word in content_lower for word in ["install", "setup", "getting started"]):
                return DocumentCategory.TUTORIAL
            else:
                return DocumentCategory.DOCUMENTATION
        elif path_lower.endswith(".md"):
            return DocumentCategory.DOCUMENTATION

        # Check by content patterns
        content_lower = chunk.content.lower()
        if chunk.type == ChunkType.CODE_BLOCK:
            return DocumentCategory.CODE
        elif any(word in content_lower for word in ["install", "setup", "getting started"]):
            return DocumentCategory.TUTORIAL

        return DocumentCategory.GENERAL

    async def generate_context_for_chunk(
        self,
        chunk: DocumentChunk,
        document_context: Optional[Dict[str, Any]] = None,
        category: Optional[DocumentCategory] = None,
    ) -> Tuple[str, bool]:
        """
        Generate context for a single chunk.

        Returns:
            Tuple of (context, was_cached)
        """
        # Detect category if not provided
        if category is None:
            category = self.detect_document_category(chunk, chunk.metadata.document_path)

        # Check cache first
        cached_context = self.cache.get(chunk, category)
        if cached_context:
            return cached_context, True

        # Get template
        template = self.template_registry.get_template(category)

        # Format prompts
        system_prompt = template.system_prompt
        user_prompt = template.format_user_prompt(chunk, document_context or {})

        # Check if client is available
        if not self.client:
            # Return a mock context if no client
            mock_context = f"Content from {chunk.metadata.document_path} ({category.value}): {chunk.content[:100]}..."
            self.cache.set(chunk, category, mock_context)
            return mock_context, False

        # Generate context using Claude
        async with self.semaphore:
            try:
                # Build messages with caching if enabled
                messages = [{"role": "user", "content": user_prompt}]

                extra_params = {}
                if self.enable_prompt_caching:
                    # Use prompt caching for system prompt
                    extra_params["system"] = [
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ]
                else:
                    extra_params["system"] = system_prompt

                response = await self.client.messages.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=150,  # Keep contexts concise
                    temperature=0.3,  # Lower temperature for consistency
                    **extra_params,
                )

                context = response.content[0].text.strip()

                # Update metrics
                if hasattr(response, "usage"):
                    self.current_metrics.add_usage(
                        response.usage.input_tokens, response.usage.output_tokens
                    )

                # Cache the result
                self.cache.set(chunk, category, context)

                return context, False

            except Exception as e:
                logger.error(f"Failed to generate context for chunk {chunk.id}: {e}")
                self.current_metrics.errors.append(f"Chunk {chunk.id}: {str(e)}")
                # Return a basic context on error
                return (
                    f"Content from {chunk.metadata.document_path}: {chunk.content[:100]}...",
                    False,
                )

    async def generate_contexts_batch(
        self,
        chunks: List[DocumentChunk],
        document_context: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, str]:
        """
        Generate contexts for a batch of chunks.

        Args:
            chunks: List of document chunks
            document_context: Additional context about the document
            progress_callback: Callback function(processed, total) for progress updates

        Returns:
            Dictionary mapping chunk IDs to generated contexts
        """
        start_time = time.time()
        self.current_metrics = ContextGenerationMetrics(total_chunks=len(chunks))

        contexts = {}
        tasks = []

        for chunk in chunks:
            task = self._process_chunk_with_progress(
                chunk, document_context, contexts, progress_callback
            )
            tasks.append(task)

        # Process all chunks
        await asyncio.gather(*tasks)

        self.current_metrics.processing_time = time.time() - start_time

        return contexts

    async def _process_chunk_with_progress(
        self,
        chunk: DocumentChunk,
        document_context: Optional[Dict[str, Any]],
        contexts: Dict[str, str],
        progress_callback: Optional[callable],
    ):
        """Process a single chunk and update progress."""
        context, was_cached = await self.generate_context_for_chunk(chunk, document_context)
        contexts[chunk.id] = context

        self.current_metrics.processed_chunks += 1
        if was_cached:
            self.current_metrics.cached_chunks += 1

        if progress_callback:
            progress_callback(
                self.current_metrics.processed_chunks, self.current_metrics.total_chunks
            )

    def get_metrics(self) -> ContextGenerationMetrics:
        """Get current processing metrics."""
        return self.current_metrics

    def clear_cache(self):
        """Clear the context cache."""
        self.cache.memory_cache.clear()
        if self.cache.cache_dir.exists():
            for cache_file in self.cache.cache_dir.glob("*.json"):
                cache_file.unlink()


async def create_contextual_embedding_service(
    api_key: Optional[str] = None, **kwargs
) -> ContextualEmbeddingService:
    """Factory function to create a contextual embedding service."""
    return ContextualEmbeddingService(api_key=api_key, **kwargs)
