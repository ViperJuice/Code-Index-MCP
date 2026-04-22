"""Embedding provider abstractions for semantic indexing."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import List, Optional


class EmbeddingProvider(ABC):
    """Provider interface for generating vector embeddings."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier used in metadata."""

    @abstractmethod
    def embed(self, texts: List[str], input_type: str = "document") -> List[List[float]]:
        """Embed a list of texts and return vectors."""


class VoyageEmbeddingProvider(EmbeddingProvider):
    """Voyage AI embedding provider."""

    def __init__(self, model_name: str, vector_dimension: int) -> None:
        try:
            import voyageai
        except ImportError as exc:
            raise RuntimeError(
                "Voyage embeddings require the voyageai package. "
                "Install semantic dependencies first."
            ) from exc

        api_key = os.environ.get("VOYAGE_API_KEY")
        if api_key:
            self.client = voyageai.Client(api_key=api_key)
        else:
            try:
                self.client = voyageai.Client()
            except Exception as exc:
                raise RuntimeError(
                    "Semantic search requires Voyage AI API key. " "Set VOYAGE_API_KEY."
                ) from exc

        self.model_name = model_name
        self.vector_dimension = vector_dimension

    @property
    def provider_name(self) -> str:
        return "voyage"

    def embed(self, texts: List[str], input_type: str = "document") -> List[List[float]]:
        response = self.client.embed(
            texts,
            model=self.model_name,
            input_type=input_type,
            output_dimension=self.vector_dimension,
            output_dtype="float",
        )
        return response.embeddings


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """OpenAI-compatible provider (vLLM, hosted gateways, etc.)."""

    def __init__(
        self,
        model_name: str,
        vector_dimension: int,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI-compatible embeddings require the openai package. "
                "Install dependencies with requirements-semantic.txt or pip install openai."
            ) from exc

        resolved_api_key = api_key or os.environ.get("OPENAI_API_KEY") or "vllm-local"
        resolved_base_url = (
            base_url
            or os.environ.get("OPENAI_API_BASE")
            or os.environ.get("OPENAI_BASE_URL")
            or "http://localhost:8001/v1"
        )

        self.client = OpenAI(api_key=resolved_api_key, base_url=resolved_base_url)
        self.model_name = model_name
        self.vector_dimension = vector_dimension

    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    def embed(self, texts: List[str], input_type: str = "document") -> List[List[float]]:
        del input_type
        response = self.client.embeddings.create(model=self.model_name, input=texts)
        vectors = [item.embedding for item in response.data]

        if vectors:
            first_len = len(vectors[0])
            if self.vector_dimension and first_len != self.vector_dimension:
                raise RuntimeError(
                    "Embedding dimension mismatch for model "
                    f"{self.model_name}: expected {self.vector_dimension}, got {first_len}."
                )

        return vectors


def create_embedding_provider(
    provider_name: str,
    model_name: str,
    vector_dimension: int,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> EmbeddingProvider:
    """Create embedding provider instance from semantic profile provider name."""
    normalized = (provider_name or "").strip().lower()

    if normalized in {"voyage", "voyageai"}:
        return VoyageEmbeddingProvider(
            model_name=model_name,
            vector_dimension=vector_dimension,
        )

    if normalized in {
        "openai_compatible",
        "openai-compatible",
        "openai",
        "vllm",
        "qwen",
    }:
        return OpenAICompatibleEmbeddingProvider(
            model_name=model_name,
            vector_dimension=vector_dimension,
            api_key=api_key,
            base_url=base_url,
        )

    raise ValueError(
        "Unsupported semantic profile provider "
        f"'{provider_name}'. Supported providers: voyage, openai_compatible."
    )
