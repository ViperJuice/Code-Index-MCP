"""Semantic stack readiness checks for CLI and gateway startup."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib import error, request

from mcp_server.artifacts.semantic_profiles import SemanticProfileRegistry
from mcp_server.config.settings import Settings


class ServiceStatus(str, Enum):
    """Result status for a preflight check."""

    READY = "ready"
    UNREACHABLE = "unreachable"
    MISCONFIGURED = "misconfigured"
    DISABLED = "disabled"


@dataclass(frozen=True)
class CheckResult:
    """Single check result returned by preflight."""

    name: str
    status: ServiceStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    fixes: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when the check passed."""
        return self.status == ServiceStatus.READY


@dataclass(frozen=True)
class SemanticPreflightReport:
    """Full readiness report for semantic stack usage."""

    overall_ready: bool
    strict_mode: bool
    qdrant: CheckResult
    embedding: CheckResult
    profiles: CheckResult
    warnings: List[str] = field(default_factory=list)
    effective_config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize report for status APIs and JSON CLI output."""

        def _check_to_dict(check: CheckResult) -> Dict[str, Any]:
            return {
                "name": check.name,
                "status": check.status.value,
                "message": check.message,
                "details": check.details,
                "fixes": check.fixes,
            }

        return {
            "overall_ready": self.overall_ready,
            "strict_mode": self.strict_mode,
            "qdrant": _check_to_dict(self.qdrant),
            "embedding": _check_to_dict(self.embedding),
            "profiles": _check_to_dict(self.profiles),
            "warnings": list(self.warnings),
            "effective_config": dict(self.effective_config),
        }


def _http_get_json(url: str, timeout_s: float) -> Dict[str, Any]:
    req = request.Request(url, method="GET")
    with request.urlopen(req, timeout=timeout_s) as response:
        content = response.read().decode("utf-8")
    return json.loads(content)


def check_qdrant(qdrant_url: str, timeout_s: float = 5.0) -> CheckResult:
    """Check Qdrant API reachability."""
    probe = qdrant_url.rstrip("/") + "/collections"
    try:
        payload = _http_get_json(probe, timeout_s=timeout_s)
        collections = payload.get("result", {}).get("collections", [])
        return CheckResult(
            name="qdrant",
            status=ServiceStatus.READY,
            message="Qdrant is reachable",
            details={"url": qdrant_url, "collections": len(collections)},
        )
    except (error.URLError, error.HTTPError, TimeoutError, ValueError, OSError) as exc:
        return CheckResult(
            name="qdrant",
            status=ServiceStatus.UNREACHABLE,
            message=f"Qdrant is not reachable at {qdrant_url}: {exc}",
            details={"url": qdrant_url, "error": str(exc)},
            fixes=[
                "Run setup semantic to auto-start local Qdrant via Docker",
                "Or set QDRANT_URL to a reachable server endpoint",
            ],
        )


def check_openai_compatible(base_url: str, timeout_s: float = 5.0) -> CheckResult:
    """Check OpenAI-compatible embeddings endpoint reachability."""
    probe = base_url.rstrip("/") + "/models"
    try:
        payload = _http_get_json(probe, timeout_s=timeout_s)
        data = payload.get("data") or []
        model_ids = [item.get("id") for item in data if isinstance(item, dict)]
        return CheckResult(
            name="embedding_openai_compatible",
            status=ServiceStatus.READY,
            message="OpenAI-compatible embedding endpoint is reachable",
            details={"base_url": base_url, "models": model_ids[:5]},
        )
    except (error.URLError, error.HTTPError, TimeoutError, ValueError, OSError) as exc:
        return CheckResult(
            name="embedding_openai_compatible",
            status=ServiceStatus.UNREACHABLE,
            message=f"OpenAI-compatible endpoint is not reachable at {base_url}: {exc}",
            details={"base_url": base_url, "error": str(exc)},
            fixes=[
                "Start vLLM or another OpenAI-compatible embeddings server",
                "Or set OPENAI_API_BASE to a reachable endpoint",
            ],
        )


def check_voyage_key_present() -> CheckResult:
    """Check voyage credential presence."""
    key = os.getenv("VOYAGE_API_KEY") or os.getenv("VOYAGE_AI_API_KEY")
    if key:
        return CheckResult(
            name="embedding_voyage",
            status=ServiceStatus.READY,
            message="Voyage API key is configured",
            details={"key_prefix": key[:8] + "..."},
        )
    return CheckResult(
        name="embedding_voyage",
        status=ServiceStatus.MISCONFIGURED,
        message="Voyage API key is missing",
        fixes=[
            "Set VOYAGE_API_KEY or VOYAGE_AI_API_KEY",
            "Use `op item get` to load the key from 1Password",
        ],
    )


def check_profile_registry(settings: Settings) -> CheckResult:
    """Validate semantic profile registry from effective settings."""
    try:
        registry = SemanticProfileRegistry.from_raw(
            settings.get_semantic_profiles_config(),
            settings.get_semantic_default_profile(),
            tool_version=settings.app_version,
        )
        profile_ids = list(registry.list().keys())
        return CheckResult(
            name="semantic_profiles",
            status=ServiceStatus.READY,
            message="Semantic profile configuration is valid",
            details={
                "default_profile": registry.default_profile,
                "profiles": profile_ids,
            },
        )
    except Exception as exc:
        return CheckResult(
            name="semantic_profiles",
            status=ServiceStatus.MISCONFIGURED,
            message=f"Semantic profile configuration is invalid: {exc}",
            details={"error": str(exc)},
            fixes=[
                "Validate code-index-mcp.profiles.yaml syntax and profile IDs",
                "Validate SEMANTIC_PROFILES_JSON and SEMANTIC_DEFAULT_PROFILE",
            ],
        )


def run_semantic_preflight(
    settings: Settings,
    profile: Optional[str] = None,
    strict: bool = False,
    timeout_s: Optional[float] = None,
) -> SemanticPreflightReport:
    """Run semantic preflight checks and return structured report."""
    timeout = float(
        timeout_s
        if timeout_s is not None
        else settings.semantic_preflight_timeout_seconds
    )
    if not settings.semantic_search_enabled:
        disabled = CheckResult(
            name="semantic",
            status=ServiceStatus.DISABLED,
            message="Semantic search is disabled (SEMANTIC_SEARCH_ENABLED=false)",
        )
        return SemanticPreflightReport(
            overall_ready=False,
            strict_mode=strict,
            qdrant=disabled,
            embedding=disabled,
            profiles=disabled,
            warnings=[
                "Enable SEMANTIC_SEARCH_ENABLED=true to initialize semantic search"
            ],
            effective_config={
                "semantic_enabled": False,
                "strict_mode": strict,
            },
        )

    profile_check = check_profile_registry(settings)

    selected_profile = profile or settings.get_semantic_default_profile()
    profile_payload = settings.get_semantic_profiles_config().get(selected_profile, {})
    provider = str(profile_payload.get("provider", "voyage")).lower()

    if provider in {"openai_compatible", "openai-compatible", "openai", "qwen", "vllm"}:
        metadata_base = (profile_payload.get("build_metadata") or {}).get(
            "openai_api_base"
        )
        base_url = str(
            settings.openai_api_base or metadata_base or "http://localhost:8001/v1"
        )
        embedding_check = check_openai_compatible(base_url, timeout_s=timeout)
    else:
        embedding_check = check_voyage_key_present()

    qdrant_url = os.getenv(
        "QDRANT_URL", f"http://{settings.qdrant_host}:{settings.qdrant_port}"
    )
    qdrant_check = check_qdrant(qdrant_url, timeout_s=timeout)

    warnings: List[str] = []
    for check in [profile_check, embedding_check, qdrant_check]:
        if not check.ok:
            warnings.append(check.message)

    overall_ready = all(
        check.ok for check in [profile_check, embedding_check, qdrant_check]
    )
    if strict and not overall_ready:
        warnings.append(
            "Strict semantic mode enabled: startup/setup should fail until checks pass"
        )

    return SemanticPreflightReport(
        overall_ready=overall_ready,
        strict_mode=strict,
        qdrant=qdrant_check,
        embedding=embedding_check,
        profiles=profile_check,
        warnings=warnings,
        effective_config={
            "semantic_enabled": settings.semantic_search_enabled,
            "selected_profile": selected_profile,
            "provider": provider,
            "qdrant_url": qdrant_url,
            "openai_api_base": settings.openai_api_base,
            "autostart_qdrant": settings.semantic_autostart_qdrant,
            "strict_mode": strict,
            "timeout_seconds": timeout,
        },
    )
