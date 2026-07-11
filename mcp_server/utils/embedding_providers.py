"""Embedding provider abstractions for semantic indexing.

Providers emit the frozen ``embedding-response.v1`` contract via
:meth:`EmbeddingProvider.embed_with_provenance` with correct per-field
provenance authority (IF-0-EMBEDPROV-1). The legacy bare-vector
:meth:`EmbeddingProvider.embed` is preserved for back-compat and delegates to
``embed_with_provenance``.
"""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Sequence

from mcp_server.interfaces.inference_contracts import (
    EmbeddingItem,
    EmbeddingItemStatus,
    EmbeddingResponseV1,
    EmbeddingRole,
    ProviderCapability,
    ProvenanceField,
)


def _role_from_input_type(input_type: str) -> EmbeddingRole:
    """Map a caller ``input_type`` string to an :class:`EmbeddingRole`.

    Preserves the role end to end. Unknown/absent values default to
    ``document`` (the contract's neutral default), never silently dropped.
    """
    if input_type in {r.value for r in EmbeddingRole}:
        return EmbeddingRole(input_type)
    return EmbeddingRole.DOCUMENT


class EmbeddingProvider(ABC):
    """Provider interface for generating vector embeddings."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier used in metadata."""

    @abstractmethod
    def embed_with_provenance(
        self, texts: Sequence[str], input_type: str = "document"
    ) -> EmbeddingResponseV1:
        """Embed texts and return a provenance-bearing ``embedding-response.v1``.

        Implementations MUST preserve ``input_type``/role end to end and populate
        every provenance field with its correct :class:`ProvenanceAuthority` (a
        server-origin value is ``reported``; a config value is ``declared``; an
        unavailable value is ``unknown``). Per-item ``index``/``status``/``error``/
        ``vector`` and overall ``latency_ms`` are filled.
        """

    @abstractmethod
    def capability(self) -> ProviderCapability:
        """Declare supported roles and which provenance fields are reportable."""

    def embed(self, texts: List[str], input_type: str = "document") -> List[List[float]]:
        """Bare-vector back-compat shim.

        Delegates to :meth:`embed_with_provenance` and returns just the vectors,
        so callers not yet migrated keep working unchanged.
        """
        response = self.embed_with_provenance(texts, input_type)
        return [item.vector for item in response.items]


class VoyageEmbeddingProvider(EmbeddingProvider):
    """Voyage AI embedding provider.

    Voyage returns only embeddings + token usage: no server-origin model
    revision or normalization. So ``served_model_id`` and ``normalization`` are
    ``declared`` (from config), ``model_revision`` is ``unknown``, ``dimension``
    is ``reported`` (measured from the returned vector), and ``role`` is
    ``reported`` (we send ``input_type`` to the API).
    """

    def __init__(
        self,
        model_name: str,
        vector_dimension: int,
        normalization: Optional[str] = None,
    ) -> None:
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
        self.normalization = normalization

    @property
    def provider_name(self) -> str:
        return "voyage"

    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            provider=self.provider_name,
            supported_roles=frozenset({EmbeddingRole.QUERY, EmbeddingRole.DOCUMENT}),
            reportable_fields={
                "served_model_id": False,  # declared from configured model name
                "model_revision": False,  # API supplies none
                "dimension": True,  # measured from returned vector
                "normalization": False,  # declared from config, else unknown
                "role": True,  # input_type is sent to the API
                "processor_id": False,
            },
        )

    def embed_with_provenance(
        self, texts: Sequence[str], input_type: str = "document"
    ) -> EmbeddingResponseV1:
        role = _role_from_input_type(input_type)

        started = time.perf_counter()
        response = self.client.embed(
            list(texts),
            model=self.model_name,
            input_type=input_type,
            output_dimension=self.vector_dimension,
            output_dtype="float",
        )
        latency_ms = (time.perf_counter() - started) * 1000.0

        vectors = response.embeddings
        items = [
            EmbeddingItem(
                index=idx,
                status=EmbeddingItemStatus.OK,
                error=None,
                vector=list(vector),
            )
            for idx, vector in enumerate(vectors)
        ]

        dimension = len(vectors[0]) if vectors else self.vector_dimension

        if self.normalization is not None:
            normalization = ProvenanceField.declared(self.normalization)
        else:
            normalization = ProvenanceField.unknown()

        return EmbeddingResponseV1(
            provider=self.provider_name,
            served_model_id=ProvenanceField.declared(self.model_name),
            model_revision=ProvenanceField.unknown(),
            dimension=ProvenanceField.reported(dimension),
            normalization=normalization,
            role=ProvenanceField.reported(role.value),
            processor_id=ProvenanceField.unknown(),
            items=items,
            latency_ms=latency_ms,
        )


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """OpenAI-compatible provider (vLLM, hosted gateways, etc.).

    The response echoes the served model id (``response.model``) so
    ``served_model_id`` is ``reported``; ``dimension`` is ``reported`` (measured
    from the returned vector). ``role`` is ``declared`` (config/local): the
    ``/v1/embeddings`` request carries only ``{model, input}`` -- ``input_type``
    never reaches the endpoint and the endpoint does not vary behavior by role,
    so the role is a locally-remembered value the server never attested. The API
    supplies no immutable revision, so ``model_revision`` is ``unknown``;
    ``normalization`` is ``declared`` from config (else ``unknown``).
    """

    def __init__(
        self,
        model_name: str,
        vector_dimension: int,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        normalization: Optional[str] = None,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI-compatible embeddings require the openai package. "
                "Run uv sync --locked to install the default client dependencies."
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
        self.normalization = normalization
        # Records the role we were last asked to embed for. The role is preserved
        # into the response as a *declared* value; the endpoint never sees it.
        self.last_input_type: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            provider=self.provider_name,
            supported_roles=frozenset({EmbeddingRole.QUERY, EmbeddingRole.DOCUMENT}),
            reportable_fields={
                "served_model_id": True,  # echoed by response.model
                "model_revision": False,  # API supplies no immutable revision
                "dimension": True,  # measured from returned vector
                "normalization": False,  # declared from config, else unknown
                "role": False,  # input_type never reaches the endpoint; role is declared
                "processor_id": False,
            },
        )

    def embed_with_provenance(
        self, texts: Sequence[str], input_type: str = "document"
    ) -> EmbeddingResponseV1:
        role = _role_from_input_type(input_type)
        # Record input_type locally. It is NOT sent to the endpoint (the request
        # below carries only {model, input}); the role is preserved as a declared
        # value, never a server-attested one.
        self.last_input_type = input_type

        texts_list = list(texts)
        request_size = len(texts_list)

        started = time.perf_counter()
        response = self.client.embeddings.create(model=self.model_name, input=texts_list)
        latency_ms = (time.perf_counter() - started) * 1000.0

        # Fail closed on the request<->response index mapping. Each response item
        # carries the server-assigned ``index`` naming which request position it
        # answers. We MUST honor that index instead of the enumeration order of
        # ``response.data`` (which may be reordered): otherwise a reordered batch
        # silently misattaches a vector to the wrong input. Missing / duplicate /
        # out-of-range / arity-mismatched indices raise rather than renumber.
        raw_items = list(getattr(response, "data", []) or [])
        if len(raw_items) != request_size:
            raise RuntimeError(
                "OpenAI-compatible embedding arity mismatch for model "
                f"{self.model_name}: requested {request_size} inputs but the "
                f"response carried {len(raw_items)} items. Refusing to "
                "positionally attach a partial/short embedding batch."
            )

        by_index: dict[int, list] = {}
        for position, item in enumerate(raw_items):
            server_index = getattr(item, "index", None)
            if not isinstance(server_index, int) or isinstance(server_index, bool):
                raise RuntimeError(
                    "OpenAI-compatible embedding response item at position "
                    f"{position} lacks a usable integer server ``index`` "
                    f"(got {server_index!r}); refusing to renumber and risk "
                    "misattaching a vector to the wrong input."
                )
            if not (0 <= server_index < request_size):
                raise RuntimeError(
                    "OpenAI-compatible embedding response index is out of range: "
                    f"item at position {position} carries index {server_index} "
                    f"but only [0, {request_size}) is valid."
                )
            if server_index in by_index:
                raise RuntimeError(
                    "OpenAI-compatible embedding response has a duplicate server "
                    f"index {server_index}; a one-to-one request<->vector mapping "
                    "is required."
                )
            by_index[server_index] = item.embedding

        # ``by_index`` now has exactly ``request_size`` unique in-range indices
        # (arity + range + duplicate checks passed), so this covers 0..n-1.
        vectors = [by_index[i] for i in range(request_size)]

        if vectors:
            first_len = len(vectors[0])
            if self.vector_dimension and first_len != self.vector_dimension:
                raise RuntimeError(
                    "Embedding dimension mismatch for model "
                    f"{self.model_name}: expected {self.vector_dimension}, got {first_len}."
                )

        items = [
            EmbeddingItem(
                index=idx,
                status=EmbeddingItemStatus.OK,
                error=None,
                vector=list(vector),
            )
            for idx, vector in enumerate(vectors)
        ]

        dimension = len(vectors[0]) if vectors else self.vector_dimension

        served_model = getattr(response, "model", None)
        if served_model is not None:
            served_model_id = ProvenanceField.reported(served_model)
        else:
            served_model_id = ProvenanceField.declared(self.model_name)

        if self.normalization is not None:
            normalization = ProvenanceField.declared(self.normalization)
        else:
            normalization = ProvenanceField.unknown()

        return EmbeddingResponseV1(
            provider=self.provider_name,
            served_model_id=served_model_id,
            model_revision=ProvenanceField.unknown(),
            dimension=ProvenanceField.reported(dimension),
            normalization=normalization,
            role=ProvenanceField.declared(role.value),
            processor_id=ProvenanceField.unknown(),
            items=items,
            latency_ms=latency_ms,
        )


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
