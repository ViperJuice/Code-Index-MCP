"""INFERLIVEGATE Lane A: collection-resident provenance (IF-0-INFERLIVEGATE-1).

These tests are fully offline. The qdrant client is a deterministic in-memory
double (no network, no server). They lock in the collection-resident provenance
contract that a live-collection benchmark (Lane B) depends on:

* a producer writes ONE reserved sentinel point whose payload is the
  ``collection-provenance.v1`` manifest, and a reader round-trips the full
  manifest back;
* the reserved provenance point is NEVER returned by ordinary semantic search;
* ``point_set_id`` is deterministic for the same build and differs across builds;
* a reader returns ``None`` when the provenance sentinel is absent;
* a provenance-write failure is best-effort (logged, swallowed) and never
  corrupts the successful build.
"""

from __future__ import annotations

from types import SimpleNamespace

from mcp_server.artifacts.semantic_profiles import SemanticProfile
from mcp_server.utils.semantic_indexer import (
    SemanticIndexer,
    read_collection_provenance,
)


# ---------------------------------------------------------------------------
# In-memory doubles (no network, no SDK)
# ---------------------------------------------------------------------------


class FakeQdrant:
    """Minimal in-memory qdrant double supporting upsert/retrieve/search."""

    def __init__(self) -> None:
        # id -> SimpleNamespace(id, vector, payload)
        self.points: dict = {}
        self.upserts: list = []

    def upsert(self, *, collection_name, points):
        for point in points:
            self.upserts.append((collection_name, point.id))
            self.points[point.id] = SimpleNamespace(
                id=point.id,
                vector=list(point.vector),
                payload=dict(point.payload or {}),
            )

    def retrieve(self, *, collection_name, ids, with_payload=True):
        out = []
        for pid in ids:
            stored = self.points.get(pid)
            if stored is not None:
                out.append(SimpleNamespace(id=stored.id, payload=dict(stored.payload)))
        return out

    def search(self, *, collection_name, query_vector, limit):
        results = []
        for stored in self.points.values():
            results.append(
                SimpleNamespace(id=stored.id, score=1.0, payload=dict(stored.payload))
            )
        return results[:limit]


class _RaisingUpsertQdrant(FakeQdrant):
    def upsert(self, *, collection_name, points):
        raise RuntimeError("qdrant backend unreachable during provenance upsert")


class _LegacyProvider:
    """Bare-``embed`` provider double (no provenance contract)."""

    provider_name = "voyage"

    def __init__(self, dim=8):
        self._dim = dim

    def embed(self, texts, input_type="document"):
        return [[0.1] * self._dim for _ in texts]


def _profile(dim=8, model="srv-model", **overrides):
    payload = {
        "provider": "openai_compatible",
        "model_name": model,
        "model_version": "v1",
        "vector_dimension": dim,
        "distance_metric": "cosine",
        "normalization_policy": "none",
        "chunk_schema_version": "v1",
        "chunker_version": "chunker@1",
        "build_metadata": {"collection_name": "semantic-oss-high"},
    }
    payload.update(overrides)
    return SemanticProfile.from_dict("oss-high", payload)


def _make_indexer(
    qdrant, *, profile=None, attestation=None, provider=None, available=True
):
    profile = profile or _profile()
    ix = SemanticIndexer.__new__(SemanticIndexer)
    ix.semantic_profile = profile
    ix._profile_active = True
    ix.embedding_model = profile.model_name
    ix.embedding_model_version = profile.model_version
    ix.embedding_dimension = profile.vector_dimension
    ix.distance_metric = profile.distance_metric
    ix.normalization_policy = profile.normalization_policy
    ix.chunk_schema_version = profile.chunk_schema_version
    ix.compatibility_fingerprint = profile.compatibility_fingerprint
    ix.collection = "semantic-oss-high"
    ix.qdrant = qdrant
    ix.qdrant_path = ":memory:"
    ix._qdrant_available = available
    ix._attestation = attestation
    ix.embedding_client = provider
    ix._get_git_commit_hash = lambda: "deadbeefcafe"  # type: ignore[assignment]
    return ix


def _attestation(*, served_model="srv-model", revision_source="declared", revision="v1"):
    """Minimal attestation double carrying the derived provenance fields."""
    return SimpleNamespace(
        derived={
            "served_model_id": {"value": served_model, "source": "reported"},
            "model_revision": {"value": revision, "source": revision_source},
        }
    )


# ===========================================================================
# 1. write -> read round-trip returns the full manifest
# ===========================================================================


def test_write_read_round_trip_returns_full_manifest():
    qdrant = FakeQdrant()
    ix = _make_indexer(qdrant, attestation=_attestation())

    written = ix.write_collection_provenance(point_ids=[101, 202, 303])
    read_back = ix.read_collection_provenance()

    assert read_back == written
    # Exactly the collection-provenance.v1 schema keys — no more, no less.
    assert set(read_back) == {
        "provenance_version",
        "collection",
        "indexed_commit",
        "corpus_sha256",
        "profile_fingerprint",
        "provider_id",
        "provider_revision",
        "point_set_id",
        "written_at",
    }
    assert read_back["provenance_version"] == "collection-provenance.v1"
    assert read_back["collection"] == "semantic-oss-high"
    assert read_back["indexed_commit"] == "deadbeefcafe"
    assert read_back["corpus_sha256"] is None
    assert read_back["profile_fingerprint"] == ix.compatibility_fingerprint
    # provider provenance reuses the served-model attestation.
    assert read_back["provider_id"] == "srv-model"
    assert read_back["provider_revision"] == "declared"
    # The reader strips the internal sentinel tag.
    assert "__provenance__" not in read_back


def test_module_level_reader_reads_from_raw_client():
    """Lane B's preferred integration seam: a module-level reader that takes a raw
    qdrant client + collection name (not a SemanticIndexer instance)."""
    qdrant = FakeQdrant()
    ix = _make_indexer(qdrant, attestation=_attestation())
    written = ix.write_collection_provenance(point_ids=[1, 2, 3])

    # Read purely through the module-level function against the raw client.
    manifest = read_collection_provenance(client=qdrant, collection="semantic-oss-high")
    assert manifest == written
    assert "__provenance__" not in manifest


def test_module_level_reader_returns_none_when_absent():
    assert read_collection_provenance(client=FakeQdrant(), collection="x") is None


def test_corpus_sha256_is_carried_when_provided():
    ix = _make_indexer(FakeQdrant())
    manifest = ix.write_collection_provenance(point_ids=[1], corpus_sha256="a" * 64)
    assert manifest["corpus_sha256"] == "a" * 64


def test_provider_revision_reported_uses_value():
    ix = _make_indexer(
        FakeQdrant(),
        attestation=_attestation(revision_source="reported", revision="rev-42"),
    )
    manifest = ix.write_collection_provenance(point_ids=[1])
    assert manifest["provider_revision"] == "rev-42"


def test_provider_provenance_defaults_without_attestation():
    ix = _make_indexer(FakeQdrant(), attestation=None)
    manifest = ix.write_collection_provenance(point_ids=[1])
    # Falls back to the declared model name and an 'unknown' revision.
    assert manifest["provider_id"] == "srv-model"
    assert manifest["provider_revision"] == "unknown"


# ===========================================================================
# 2. Sentinel is excluded from ordinary semantic search
# ===========================================================================


def test_sentinel_point_excluded_from_ordinary_search():
    qdrant = FakeQdrant()
    ix = _make_indexer(qdrant, provider=_LegacyProvider(dim=8))

    # A normal indexed point lives alongside the reserved provenance sentinel.
    qdrant.points[999] = SimpleNamespace(
        id=999,
        vector=[0.2] * 8,
        payload={
            "relative_path": "mcp_server/foo.py",
            "symbol": "foo",
            "kind": "function",
        },
    )
    ix.write_collection_provenance(point_ids=[999])

    # The sentinel is stored...
    assert SemanticIndexer.PROVENANCE_POINT_ID in qdrant.points
    assert qdrant.points[SemanticIndexer.PROVENANCE_POINT_ID].payload["__provenance__"] is True

    # ...but ordinary search never surfaces it.
    results = list(ix.query("where is foo implemented", limit=10))
    assert results, "expected the ordinary indexed point to be returned"
    assert all(not r.get("__provenance__") for r in results)
    assert all(r.get("provenance_version") is None for r in results)
    assert any(r.get("relative_path") == "mcp_server/foo.py" for r in results)


# ===========================================================================
# 3. point_set_id is deterministic per build and differs across builds
# ===========================================================================


def test_point_set_id_is_deterministic_and_order_independent():
    ix = _make_indexer(FakeQdrant())
    a = ix.build_collection_provenance_manifest(point_ids=[10, 20, 30])
    b = ix.build_collection_provenance_manifest(point_ids=[30, 20, 10, 10])
    # Same set of points (reordered + duplicated) -> identical id.
    assert a["point_set_id"] == b["point_set_id"]


def test_point_set_id_differs_across_builds():
    ix = _make_indexer(FakeQdrant())
    a = ix.build_collection_provenance_manifest(point_ids=[10, 20, 30])
    c = ix.build_collection_provenance_manifest(point_ids=[10, 20, 40])
    assert a["point_set_id"] != c["point_set_id"]


def test_point_set_id_ignores_reserved_sentinel_id():
    ix = _make_indexer(FakeQdrant())
    without = ix.build_collection_provenance_manifest(point_ids=[10, 20])
    withsentinel = ix.build_collection_provenance_manifest(
        point_ids=[SemanticIndexer.PROVENANCE_POINT_ID, 10, 20]
    )
    # The reserved sentinel id never contributes to the build's point_set_id.
    assert without["point_set_id"] == withsentinel["point_set_id"]


# ===========================================================================
# 4. Provenance absent -> reader returns None
# ===========================================================================


def test_read_returns_none_when_provenance_absent():
    ix = _make_indexer(FakeQdrant())
    assert ix.read_collection_provenance() is None


def test_read_returns_none_when_qdrant_unavailable():
    ix = _make_indexer(FakeQdrant(), available=False)
    # Even after a would-be write (which no-ops while unavailable), read is None.
    assert ix.write_collection_provenance(point_ids=[1]) is None
    assert ix.read_collection_provenance() is None


def test_read_ignores_non_provenance_point_at_reserved_id():
    qdrant = FakeQdrant()
    ix = _make_indexer(qdrant)
    # A stray point squatting the reserved id but without the provenance tag.
    qdrant.points[SemanticIndexer.PROVENANCE_POINT_ID] = SimpleNamespace(
        id=SemanticIndexer.PROVENANCE_POINT_ID,
        vector=[0.0] * 8,
        payload={"relative_path": "x.py"},
    )
    assert ix.read_collection_provenance() is None


# ===========================================================================
# 5. Provenance write is best-effort: a failure never corrupts the build
# ===========================================================================


def test_best_effort_write_swallows_failure():
    ix = _make_indexer(_RaisingUpsertQdrant())
    # The best-effort wrapper must NOT propagate the upsert failure.
    assert ix._write_collection_provenance_best_effort(point_ids=[1, 2]) is None
