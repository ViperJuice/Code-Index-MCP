# Inference Deployment Profiles

This guide describes the four supported **deployment profiles** for semantic and
reranked search, when to use each, the degradation policy when a provider is
unavailable, and the egress disclosure for each posture.

> **Experimental.** Semantic (dense/hybrid) and reranked search remain
> **EXPERIMENTAL**. Choosing a learned-model profile does not make them a
> default. The default-enablement verdict and the support-matrix wording are
> owned by the **INFERGATE** phase and are deferred to its benchmark gate — this
> guide does not assert any support verdict.

The profile contract is defined declaratively in
`mcp_server/config/settings.py` (`DeploymentProfile`, `DeploymentProfileContract`,
`DEPLOYMENT_PROFILES`, `resolve_deployment_profile`, `apply_degradation_policy`).
Resolving or degrading a profile is pure configuration: it constructs no
provider, performs no network I/O, and never touches a Qdrant collection.

## The four profiles

| Profile | Embedding provider | Reranker path | Learned models | Commercial egress |
|---|---|---|---|---|
| `standalone_local` | local OpenAI-compatible (optional) | in-process (FlashRank / cross-encoder) | opt-in | No |
| `fleet_local` | private OpenAI-compatible / ai-stack endpoint | `EndpointReranker` (`rerank.v1`) | yes | No |
| `commercial` | Voyage AI | Cohere `/v2/rerank` adapter | yes | **Yes — opt-in only** |
| `lexical_only` | none | none | **none** | No |

### `standalone_local`

Optional local/in-process inference. Reranking uses the in-process FlashRank or
cross-encoder rerankers, which are only constructable via
`RerankerFactory.create_standalone_reranker(..., standalone_profile=True)` — they
are never an implicit default. Local embedding is used only if you configure a
local endpoint. **No commercial egress.** Learned models are **opt-in**: you must
explicitly enable them.

**Use when:** you want on-box inference with no external calls and are willing to
carry the heavier local model dependencies.

### `fleet_local`

Endpoint inference against a **private** OpenAI-compatible / ai-stack endpoint:
OpenAI-compatible embeddings plus the canonical `EndpointReranker` over the
`rerank.v1` wire contract, backed by Qdrant. Inference stays on
operator-controlled infrastructure. **No commercial egress.**

**Use when:** you run a private inference stack (e.g. vLLM + a rerank endpoint)
and Qdrant, and want quality inference without sending code off your fleet.

### `commercial`

Commercial endpoint providers: Voyage AI embeddings and/or Cohere reranking
(`/v2/rerank`). **This profile sends your source code to a third-party commercial
API.** It is **opt-in only** and is visibly marked as source-code egress.

**Opt-in is enforced in code.** `resolve_deployment_profile("commercial")` raises
`CommercialEgressNotOptedIn`; you must pass `allow_commercial=True` to select it.
Commercial is never selected implicitly, and no degradation fallback ever
escalates *into* it.

**Use when:** you have explicitly accepted source-code egress to a commercial
vendor and want their hosted model quality without running your own stack.

### `lexical_only`

No learned-model dependency at all: BM25 / symbol search only. This is the
**dependency-free** path and the safe degradation target. No embedding provider,
no reranker, no commercial egress.

**Use when:** you want zero learned-model dependencies, or as the guaranteed
fallback when inference providers are unavailable.

## Degradation policy

`apply_degradation_policy(contract, probe=...)` implements the policy. The
`probe` is a caller-supplied check that raises when the profile's inference
provider is unavailable. On provider unavailability the resolver **degrades to
the profile's declared fallback**, which is always `lexical_only` for the
learned-model profiles.

Guarantees:

- **Documented fallback.** Every learned-model profile falls back to
  `lexical_only`. A fallback **never** escalates into `commercial` (that would be
  implicit egress) — this is asserted in code.
- **Truthful diagnostic.** The returned `DegradationDiagnostic` names the
  **actual path taken**: the requested profile, the active (fallback) profile,
  the failed component, and the reason (e.g.
  `fleet_local -> lexical_only (component 'openai_compatible' unavailable)`).
- **Zero collection mutation.** A fleet/provider outage must **never** corrupt
  collection metadata or trigger collection recreation. The degradation policy is
  pure configuration and touches no collection. This composes with the committed
  behavior from earlier phases:
  - **INFERSAFE** made `ensure_qdrant_collection` fail-closed: `allow_recreate`
    defaults to `False`, an incompatible or unreadable existing collection yields
    `blocked` (never a destructive recreate), and a `blocked` result raises an
    actionable diagnostic at runtime.
  - **EMBEDPROV** enforces no-mutation-on-failure: a provider fault leaves
    collection metadata untouched.
  Together, a provider-down event yields a clean degraded diagnostic and zero
  collection mutation (covered by
  `tests/test_deployment_profiles.py::test_fleet_provider_down_degrades_without_collection_mutation`).

## Egress disclosure

Every profile carries a human-readable `egress_disclosure` string.

- `standalone_local`, `fleet_local`, `lexical_only`: **No source-code egress** —
  inference stays on operator-controlled infrastructure (or is absent).
- `commercial`: **SOURCE-CODE EGRESS** — source code is sent to third-party
  commercial APIs (Voyage AI embeddings and/or Cohere reranking). Opt-in only;
  never selected implicitly.

## Selecting a profile in code

```python
from mcp_server.config.settings import (
    resolve_deployment_profile,
    apply_degradation_policy,
)

# Non-commercial profiles resolve directly.
contract = resolve_deployment_profile("fleet_local")

# Commercial requires an explicit opt-in; otherwise CommercialEgressNotOptedIn.
contract = resolve_deployment_profile("commercial", allow_commercial=True)

# Apply the degradation policy with a provider health probe.
active, diagnostic = apply_degradation_policy(contract, probe=check_endpoint)
if diagnostic.degraded:
    log.warning("inference degraded: %s", diagnostic.actual_path)
```
