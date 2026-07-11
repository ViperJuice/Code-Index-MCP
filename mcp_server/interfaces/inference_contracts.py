"""Inference wire contracts (INFERFREEZE, additive freeze).

This module defines the frozen, versioned ``embedding-response.v1`` contract, the
per-field provenance-authority model, a provider capability declaration, and a
fail-closed provenance-validation interface (IF-0-INFERFREEZE-1 and
IF-0-INFERFREEZE-3).

**Additive only.** Nothing here changes the signature or behavior of the concrete
embedding providers in ``mcp_server/utils/embedding_providers.py``. Those still
expose ``embed(texts, input_type) -> List[List[float]]``. The compat shim
:func:`embed_with_provenance` wraps that existing bare-vector call into a fully
populated ``embedding-response.v1`` *without* touching the provider, proving the
contract is populatable today. The full provider migration (providers emitting
their own provenance) is a later phase (EMBEDPROV).

The module is intentionally dependency-free (stdlib only) and does not import
``embedding_providers`` — the shim duck-types the provider so it works against the
real providers and against test fakes with the same attribute shape.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence, runtime_checkable

CONTRACT_VERSION = "embedding-response.v1"


# ========================================
# Enums
# ========================================


class ProvenanceAuthority(str, Enum):
    """Origin authority for a single provenance field.

    - ``reported``: the value came from the inference server itself (server-origin,
      the highest-trust authority for cross-checking model identity).
    - ``declared``: the value was asserted by local config/capability, not by the
      server (e.g. the dimension the caller *expects*, not one the server echoed).
    - ``unknown``: the value could not be established from either source.
    """

    REPORTED = "reported"
    DECLARED = "declared"
    UNKNOWN = "unknown"


class EmbeddingRole(str, Enum):
    """Semantic role the embedding was produced for."""

    QUERY = "query"
    DOCUMENT = "document"


class EmbeddingItemStatus(str, Enum):
    """Per-item embedding status (independent small vocabulary)."""

    OK = "ok"
    ERROR = "error"


# Canonical provenance field names. These are the fields that carry a
# per-field :class:`ProvenanceAuthority` tag on an ``embedding-response.v1``.
PROVENANCE_FIELDS: tuple[str, ...] = (
    "served_model_id",
    "model_revision",
    "dimension",
    "normalization",
    "role",
    "processor_id",
)

# Compatibility-critical provenance fields (IF-0-INFERFREEZE-3). A mismatch or an
# ``unknown`` authority on any of these MUST fail validation closed. ``role`` is
# deliberately excluded: it is preserved end-to-end but is not a compatibility
# gate (a provider may embed both roles against one served model).
COMPATIBILITY_CRITICAL_FIELDS: tuple[str, ...] = (
    "dimension",
    "served_model_id",
    "model_revision",
    "normalization",
)

# Named ai-stack server-side contract (IF-0-INFERFREEZE-3): the fields an ai-stack
# embedding endpoint is expected to emit as ``reported`` (server-origin) so that
# provenance validation can run against real server metadata rather than merely
# ``declared`` config. A conformant ai-stack endpoint SHOULD report every field
# below; the compatibility-critical subset MUST be reported for the provenance
# validator to pass without falling back to ``declared``.
AI_STACK_REPORTED_FIELDS: tuple[str, ...] = PROVENANCE_FIELDS


# ========================================
# Provenance field wrapper
# ========================================


@dataclass
class ProvenanceField:
    """A single provenance value plus the authority that vouches for it."""

    value: Any
    authority: ProvenanceAuthority = ProvenanceAuthority.UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        return {"value": _plain(self.value), "authority": self.authority.value}

    @classmethod
    def reported(cls, value: Any) -> "ProvenanceField":
        return cls(value=value, authority=ProvenanceAuthority.REPORTED)

    @classmethod
    def declared(cls, value: Any) -> "ProvenanceField":
        return cls(value=value, authority=ProvenanceAuthority.DECLARED)

    @classmethod
    def unknown(cls, value: Any = None) -> "ProvenanceField":
        return cls(value=value, authority=ProvenanceAuthority.UNKNOWN)


# ========================================
# Per-item entry
# ========================================


@dataclass
class EmbeddingItem:
    """A single per-input result entry of an ``embedding-response.v1``."""

    index: int
    status: EmbeddingItemStatus = EmbeddingItemStatus.OK
    error: Optional[str] = None
    vector: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "status": self.status.value,
            "error": self.error,
            "vector": list(self.vector) if self.vector is not None else None,
        }


# ========================================
# embedding-response.v1
# ========================================


@dataclass
class EmbeddingResponseV1:
    """Frozen, versioned embedding response contract (IF-0-INFERFREEZE-1).

    Every provenance field is a :class:`ProvenanceField` carrying its own
    :class:`ProvenanceAuthority`. ``to_dict`` is fully JSON-serializable (enums are
    unwrapped to their ``.value``; nested dataclasses recurse).
    """

    provider: str
    served_model_id: ProvenanceField
    model_revision: ProvenanceField
    dimension: ProvenanceField
    normalization: ProvenanceField
    role: ProvenanceField
    processor_id: ProvenanceField
    items: List[EmbeddingItem] = field(default_factory=list)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    latency_ms: Optional[float] = None
    route: Dict[str, Any] = field(default_factory=dict)
    contract_version: str = CONTRACT_VERSION

    def provenance_field(self, name: str) -> ProvenanceField:
        """Return the :class:`ProvenanceField` for a named provenance field."""
        if name not in PROVENANCE_FIELDS:
            raise KeyError(f"{name!r} is not a provenance field; expected one of {PROVENANCE_FIELDS}")
        return getattr(self, name)

    def authority_of(self, name: str) -> ProvenanceAuthority:
        """Return just the authority tag for a named provenance field."""
        return self.provenance_field(name).authority

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "request_id": self.request_id,
            "provider": self.provider,
            "served_model_id": self.served_model_id.to_dict(),
            "model_revision": self.model_revision.to_dict(),
            "dimension": self.dimension.to_dict(),
            "normalization": self.normalization.to_dict(),
            "role": self.role.to_dict(),
            "processor_id": self.processor_id.to_dict(),
            "items": [item.to_dict() for item in self.items],
            "latency_ms": self.latency_ms,
            "route": dict(self.route),
        }


# ========================================
# Provider capability declaration
# ========================================


@dataclass
class ProviderCapability:
    """What a provider can declare about role support and provenance reporting.

    - ``supported_roles``: which :class:`EmbeddingRole` values the provider serves.
    - ``reportable_fields``: for each provenance field name, whether the provider
      can emit it as ``reported`` (server-origin). Absent/false means the provider
      cannot report that field, so a value can only be ``declared`` or ``unknown``.
    """

    provider: str
    supported_roles: frozenset = field(default_factory=lambda: frozenset(EmbeddingRole))
    reportable_fields: Dict[str, bool] = field(default_factory=dict)

    def supports_role(self, role: EmbeddingRole) -> bool:
        return role in self.supported_roles

    def can_report(self, field_name: str) -> bool:
        return bool(self.reportable_fields.get(field_name, False))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "supported_roles": sorted(r.value for r in self.supported_roles),
            "reportable_fields": {
                name: self.can_report(name) for name in PROVENANCE_FIELDS
            },
        }


# ========================================
# Provenance validation (fail-closed)
# ========================================


@dataclass
class ExpectedProfile:
    """The provenance an operator expects an actual response to satisfy."""

    served_model_id: Optional[str] = None
    model_revision: Optional[str] = None
    dimension: Optional[int] = None
    normalization: Optional[str] = None
    role: Optional[EmbeddingRole] = None
    processor_id: Optional[str] = None

    def expected_value(self, name: str) -> Any:
        return getattr(self, name)


@dataclass
class ValidationResult:
    """Outcome of :func:`validate_profile`."""

    ok: bool
    failures: List[str] = field(default_factory=list)
    checked_fields: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "failures": list(self.failures),
            "checked_fields": list(self.checked_fields),
        }


def validate_profile(
    expected: ExpectedProfile,
    actual_response: EmbeddingResponseV1,
) -> ValidationResult:
    """Compare an expected profile against an actual ``embedding-response.v1``.

    Fails closed (``ok=False``) when any compatibility-critical field
    (:data:`COMPATIBILITY_CRITICAL_FIELDS`) has authority ``unknown`` or a value
    that mismatches the expectation. A ``reported`` or ``declared`` value that
    matches passes. Only critical fields are gated; ``role`` is not.
    """
    failures: List[str] = []
    checked: List[str] = []

    for name in COMPATIBILITY_CRITICAL_FIELDS:
        checked.append(name)
        pf = actual_response.provenance_field(name)

        # Fail closed on unknown authority for a compatibility-critical field.
        if pf.authority == ProvenanceAuthority.UNKNOWN:
            failures.append(
                f"{name}: authority is 'unknown' (compatibility-critical field must be "
                f"reported or declared)"
            )
            continue

        exp = expected.expected_value(name)
        if exp is not None and _plain(pf.value) != _plain(exp):
            failures.append(
                f"{name}: expected {_plain(exp)!r} but response carries "
                f"{_plain(pf.value)!r} (authority={pf.authority.value})"
            )

    return ValidationResult(ok=not failures, failures=failures, checked_fields=checked)


# ========================================
# Compat shim
# ========================================


@runtime_checkable
class _BareEmbeddingProvider(Protocol):
    """Structural type of the existing bare-vector providers (duck-typed).

    Matches ``mcp_server.utils.embedding_providers.EmbeddingProvider`` without a
    runtime import: ``provider_name`` property plus ``embed(texts, input_type)``.
    """

    @property
    def provider_name(self) -> str: ...

    def embed(self, texts: List[str], input_type: str = "document") -> List[List[float]]: ...


def _provenance(
    capability: Optional[ProviderCapability],
    field_name: str,
    reported_value: Any,
    declared_value: Any,
) -> ProvenanceField:
    """Resolve one provenance field's value + authority.

    Precedence: a server-``reported`` value (only if the capability says the
    provider can report this field) beats a config-``declared`` value, which beats
    ``unknown``.
    """
    if capability is not None and capability.can_report(field_name) and reported_value is not None:
        return ProvenanceField.reported(reported_value)
    if declared_value is not None:
        return ProvenanceField.declared(declared_value)
    return ProvenanceField.unknown()


def embed_with_provenance(
    provider: _BareEmbeddingProvider,
    texts: Sequence[str],
    input_type: str = "document",
    *,
    capability: Optional[ProviderCapability] = None,
    declared: Optional[Mapping[str, Any]] = None,
    reported: Optional[Mapping[str, Any]] = None,
    request_id: Optional[str] = None,
    route: Optional[Mapping[str, Any]] = None,
) -> EmbeddingResponseV1:
    """Wrap the EXISTING ``provider.embed(...)`` into an ``embedding-response.v1``.

    This calls the provider's unchanged bare-vector ``embed`` and populates the
    contract around it. Fields the provider cannot supply as ``reported`` are
    marked ``declared`` (from ``declared`` overrides, or duck-typed provider
    config: ``model_name`` -> served_model_id, ``vector_dimension`` -> dimension)
    or ``unknown``. No provider signature is changed.

    ``role`` is derived from ``input_type`` and preserved end to end.
    """
    declared = dict(declared or {})
    reported = dict(reported or {})

    role = EmbeddingRole(input_type) if input_type in {r.value for r in EmbeddingRole} else EmbeddingRole.DOCUMENT

    started = time.perf_counter()
    vectors = provider.embed(list(texts), input_type)
    latency_ms = (time.perf_counter() - started) * 1000.0

    items: List[EmbeddingItem] = []
    for idx, vector in enumerate(vectors):
        items.append(
            EmbeddingItem(
                index=idx,
                status=EmbeddingItemStatus.OK,
                error=None,
                vector=list(vector),
            )
        )

    # Duck-typed config fallbacks (present on the real providers today).
    declared_model = declared.get("served_model_id", getattr(provider, "model_name", None))
    declared_dim = declared.get("dimension", getattr(provider, "vector_dimension", None))

    served_model_id = _provenance(
        capability, "served_model_id", reported.get("served_model_id"), declared_model
    )
    model_revision = _provenance(
        capability, "model_revision", reported.get("model_revision"), declared.get("model_revision")
    )
    dimension = _provenance(
        capability, "dimension", reported.get("dimension"), declared_dim
    )
    normalization = _provenance(
        capability, "normalization", reported.get("normalization"), declared.get("normalization")
    )
    # Role is always known locally (derived from input_type). If the server can
    # report it, honor that; otherwise it is a declared value from the caller.
    if capability is not None and capability.can_report("role") and reported.get("role") is not None:
        role_field = ProvenanceField.reported(EmbeddingRole(reported["role"]).value)
    else:
        role_field = ProvenanceField.declared(role.value)
    processor_id = _provenance(
        capability, "processor_id", reported.get("processor_id"), declared.get("processor_id")
    )

    provider_name = getattr(provider, "provider_name", declared.get("provider", "unknown"))

    return EmbeddingResponseV1(
        provider=provider_name,
        served_model_id=served_model_id,
        model_revision=model_revision,
        dimension=dimension,
        normalization=normalization,
        role=role_field,
        processor_id=processor_id,
        items=items,
        request_id=request_id or str(uuid.uuid4()),
        latency_ms=latency_ms,
        route=dict(route or {}),
    )


# ========================================
# Serialization helper
# ========================================


def _plain(value: Any) -> Any:
    """Unwrap enums/dataclasses to JSON-plain values, recursing into containers."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, ProvenanceField):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value
