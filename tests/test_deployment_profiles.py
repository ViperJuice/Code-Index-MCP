"""Tests for INFERPROFILES deployment-profile contract (IF-0-INFERPROFILES-1).

These tests are network-free: no provider or reranker is ever constructed. The
profile registry is declarative (provider *name strings* + a reranker-path
enum), so wiring assertions read the declared identifiers rather than building
``VoyageEmbeddingProvider`` (which imports voyageai and demands an API key).

The load-bearing test is ``test_fleet_provider_down_degrades_without_collection_mutation``:
it drives the COMMITTED, fail-closed ``ensure_qdrant_collection`` (INFERSAFE /
EMBEDPROV no-mutation) with a spy client under a shape mismatch and asserts a
``blocked`` result with zero destructive collection calls, alongside a clean
degraded diagnostic from the profile degradation policy.
"""

import pytest

from mcp_server.config.settings import (
    DEFAULT_DEPLOYMENT_PROFILE,
    DEPLOYMENT_PROFILES,
    CommercialEgressNotOptedIn,
    DegradationDiagnostic,
    DeploymentProfile,
    DeploymentProfileContract,
    RerankerPath,
    apply_degradation_policy,
    resolve_deployment_profile,
)


# ---------------------------------------------------------------------------
# Per-profile wiring
# ---------------------------------------------------------------------------


def test_all_four_profiles_registered():
    assert set(DEPLOYMENT_PROFILES) == {
        DeploymentProfile.STANDALONE_LOCAL,
        DeploymentProfile.FLEET_LOCAL,
        DeploymentProfile.COMMERCIAL,
        DeploymentProfile.LEXICAL_ONLY,
    }
    for profile, contract in DEPLOYMENT_PROFILES.items():
        assert contract.profile is profile
        assert isinstance(contract, DeploymentProfileContract)
        assert contract.egress_disclosure  # always present


def test_standalone_local_wiring():
    contract = resolve_deployment_profile(DeploymentProfile.STANDALONE_LOCAL)
    assert contract.embedding_provider == "openai_compatible"
    assert contract.embedding_provider_locality == "local"
    assert contract.reranker_path is RerankerPath.STANDALONE_IN_PROCESS
    assert contract.requires_learned_models is True
    assert contract.commercial_egress is False
    assert contract.fallback_profile is DeploymentProfile.LEXICAL_ONLY


def test_fleet_local_wiring():
    contract = resolve_deployment_profile("fleet_local")
    assert contract.embedding_provider == "openai_compatible"
    assert contract.embedding_provider_locality == "private_endpoint"
    assert contract.reranker_path is RerankerPath.ENDPOINT
    assert contract.requires_learned_models is True
    assert contract.commercial_egress is False
    assert contract.fallback_profile is DeploymentProfile.LEXICAL_ONLY


def test_commercial_wiring():
    contract = resolve_deployment_profile("commercial", allow_commercial=True)
    assert contract.embedding_provider == "voyage"
    assert contract.embedding_provider_locality == "commercial"
    assert contract.reranker_path is RerankerPath.COMMERCIAL_ENDPOINT
    assert contract.requires_learned_models is True
    assert contract.commercial_egress is True
    assert contract.fallback_profile is DeploymentProfile.LEXICAL_ONLY


def test_lexical_only_wiring():
    contract = resolve_deployment_profile(DeploymentProfile.LEXICAL_ONLY)
    assert contract.embedding_provider is None
    assert contract.embedding_provider_locality == "none"
    assert contract.reranker_path is RerankerPath.NONE
    assert contract.commercial_egress is False


# ---------------------------------------------------------------------------
# lexical_only has NO learned-model dependency
# ---------------------------------------------------------------------------


def test_lexical_only_has_no_learned_model_dependency():
    contract = resolve_deployment_profile(DeploymentProfile.LEXICAL_ONLY)
    assert contract.requires_learned_models is False
    assert contract.is_lexical_only is True
    assert contract.embedding_provider is None
    assert contract.reranker_path is RerankerPath.NONE
    # It is the only profile with no learned-model dependency.
    learned = {
        p for p, c in DEPLOYMENT_PROFILES.items() if not c.requires_learned_models
    }
    assert learned == {DeploymentProfile.LEXICAL_ONLY}


def test_lexical_only_is_the_safe_default():
    assert DEFAULT_DEPLOYMENT_PROFILE is DeploymentProfile.LEXICAL_ONLY
    # Resolving with no arguments must yield a non-egress, no-learned-model path.
    contract = resolve_deployment_profile()
    assert contract.commercial_egress is False
    assert contract.requires_learned_models is False


# ---------------------------------------------------------------------------
# commercial is opt-in + egress-flagged, never implicit
# ---------------------------------------------------------------------------


def test_commercial_requires_explicit_opt_in():
    with pytest.raises(CommercialEgressNotOptedIn):
        resolve_deployment_profile(DeploymentProfile.COMMERCIAL)
    with pytest.raises(CommercialEgressNotOptedIn):
        resolve_deployment_profile("commercial", allow_commercial=False)


def test_commercial_is_flagged_as_source_code_egress():
    contract = resolve_deployment_profile("commercial", allow_commercial=True)
    assert contract.commercial_egress is True
    assert "EGRESS" in contract.egress_disclosure.upper()
    assert "source code" in contract.egress_disclosure.lower()


def test_commercial_is_the_only_egress_profile():
    egress = {p for p, c in DEPLOYMENT_PROFILES.items() if c.commercial_egress}
    assert egress == {DeploymentProfile.COMMERCIAL}


def test_default_resolution_is_never_commercial():
    # No profile resolves to commercial without the explicit opt-in flag.
    for profile in DeploymentProfile:
        if profile is DeploymentProfile.COMMERCIAL:
            continue
        contract = resolve_deployment_profile(profile)
        assert contract.commercial_egress is False


def test_unknown_profile_raises():
    with pytest.raises(ValueError):
        resolve_deployment_profile("nonexistent_profile")


# ---------------------------------------------------------------------------
# Degradation policy
# ---------------------------------------------------------------------------


def test_degradation_healthy_probe_keeps_profile():
    contract = resolve_deployment_profile("fleet_local")
    active, diag = apply_degradation_policy(contract, probe=lambda: None)
    assert active.profile is DeploymentProfile.FLEET_LOCAL
    assert diag.degraded is False
    assert diag.collection_mutated is False


def test_no_fallback_ever_escalates_into_commercial():
    for profile, contract in DEPLOYMENT_PROFILES.items():
        if contract.fallback_profile is None:
            continue
        fallback = DEPLOYMENT_PROFILES[contract.fallback_profile]
        assert fallback.commercial_egress is False
        assert fallback.profile is DeploymentProfile.LEXICAL_ONLY


# ---------------------------------------------------------------------------
# Spy Qdrant client for the committed fail-closed collection lifecycle.
# ---------------------------------------------------------------------------


class _FakeVectors:
    def __init__(self, size, distance):
        self.size = size
        self.distance = distance


class _FakeParams:
    def __init__(self, vectors):
        self.vectors = vectors


class _FakeConfig:
    def __init__(self, params):
        self.params = params


class _FakeCollectionInfo:
    def __init__(self, vectors):
        self.config = _FakeConfig(_FakeParams(vectors))


class _FakeCollectionDescription:
    def __init__(self, name):
        self.name = name


class _FakeCollections:
    def __init__(self, names):
        self.collections = [_FakeCollectionDescription(n) for n in names]


class SpyQdrantClient:
    """Records every mutating call so a test can assert zero collection mutation.

    Reports an EXISTING collection whose vector shape mismatches the expected
    dimension, driving the committed ``ensure_qdrant_collection`` down its
    fail-closed ``blocked`` branch (``allow_recreate`` defaults to ``False``).
    """

    def __init__(self, *, existing_name, actual_size, actual_distance):
        self._existing_name = existing_name
        self._actual_size = actual_size
        self._actual_distance = actual_distance
        self.create_calls = []
        self.recreate_calls = []
        self.delete_calls = []

    def get_collections(self):
        return _FakeCollections([self._existing_name])

    def get_collection(self, name):
        return _FakeCollectionInfo(
            _FakeVectors(self._actual_size, self._actual_distance)
        )

    # Mutating operations — must NOT be called on the fail-closed path.
    def create_collection(self, *args, **kwargs):
        self.create_calls.append((args, kwargs))

    def recreate_collection(self, *args, **kwargs):
        self.recreate_calls.append((args, kwargs))

    def delete_collection(self, *args, **kwargs):
        self.delete_calls.append((args, kwargs))


def test_fleet_provider_down_degrades_without_collection_mutation():
    """Provider-down under a fleet profile: clean degraded diagnostic AND the
    committed collection lifecycle stays fail-closed with zero mutation.

    This composes the INFERPROFILES degradation policy with the committed
    EMBEDPROV no-mutation / INFERSAFE fail-closed ``ensure_qdrant_collection``.
    """
    # Import the COMMITTED lifecycle function; skip honestly if the qdrant dep is
    # unavailable in this env rather than degrading to a tautology.
    semantic_indexer = pytest.importorskip(
        "mcp_server.utils.semantic_indexer"
    )
    from mcp_server.utils.semantic_indexer import SemanticIndexer, ensure_qdrant_collection

    # 1) Degradation policy: fleet provider is down -> degrade to lexical_only.
    contract = resolve_deployment_profile("fleet_local")

    def _provider_down():
        raise ConnectionError("ai-stack embedding endpoint unreachable")

    active, diag = apply_degradation_policy(contract, probe=_provider_down)

    assert diag.degraded is True
    assert diag.requested_profile is DeploymentProfile.FLEET_LOCAL
    assert diag.active_profile is DeploymentProfile.LEXICAL_ONLY
    assert active.profile is DeploymentProfile.LEXICAL_ONLY
    assert active.requires_learned_models is False
    # Diagnostic names the ACTUAL path taken and the failed component.
    assert "fleet_local" in diag.actual_path
    assert "lexical_only" in diag.actual_path
    assert diag.failed_component == "openai_compatible"
    assert "ConnectionError" in (diag.reason or "")
    assert diag.collection_mutated is False

    # 2) Composition with the committed fail-closed collection lifecycle: a live
    # collection with a mismatched shape must yield ``blocked`` and touch nothing.
    expected_distance = SemanticIndexer.resolve_qdrant_distance("cosine")
    spy = SpyQdrantClient(
        existing_name="code-embeddings",
        actual_size=512,  # mismatches expected 1024 below
        actual_distance=expected_distance,
    )

    result = ensure_qdrant_collection(
        spy,
        collection_name="code-embeddings",
        expected_dimension=1024,
        distance_metric="cosine",
        # allow_recreate defaults False (runtime path) — do not pass it.
    )

    assert result.status == "blocked"
    # Zero collection mutation on a provider/shape fault.
    assert spy.recreate_calls == []
    assert spy.create_calls == []
    assert spy.delete_calls == []
    assert diag.collection_mutated is False


def test_degradation_diagnostic_serializes():
    contract = resolve_deployment_profile("standalone_local")
    _, diag = apply_degradation_policy(
        contract, probe=lambda: (_ for _ in ()).throw(RuntimeError("model missing"))
    )
    payload = diag.as_dict()
    assert payload["requested_profile"] == "standalone_local"
    assert payload["active_profile"] == "lexical_only"
    assert payload["degraded"] is True
    assert payload["collection_mutated"] is False
    assert isinstance(diag, DegradationDiagnostic)
