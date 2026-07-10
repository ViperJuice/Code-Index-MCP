# Phase roadmap v10 panel review and reconciliation

Review requested and reconciled before implementation on 2026-07-10.

## Panel Evidence

The first `phase_loop_runtime.panel_invoker` attempt did not qualify as a
three-agent review:

| Leg | Requested model | Runtime status | Qualified |
|---|---|---|---|
| Codex | `gpt-5.5` | `DEGRADED` | No |
| Gemini | `Gemini 3.1 Pro (High)` | `DEGRADED` | No |
| Fable | `claude-fable-5` | `UNAVAILABLE` | No |

That attempt remains preserved in `specs/phase-plans-v10_panel_results.json`.
It was not counted as the requested panel.

After subscription-auth preflight, the same self-contained roadmap and review
brief were sent independently through the three direct read-only harness paths:

| Leg | Model | Status | Verdict |
|---|---|---|---|
| Codex | `gpt-5.5` | `OK` | `PARTIALLY AGREE` |
| Gemini | `Gemini 3.1 Pro (High)` | `OK` | `PARTIALLY AGREE` |
| Fable | `claude-fable-5` | `OK` | `PARTIALLY AGREE` |

Qualified raw output is preserved in
`specs/phase-plans-v10_panel_retry_results.json`.

## Converged Blocking Recommendations

The following amendments were accepted:

1. Add a findings-to-gates matrix that gives each finding one owner phase, IF
   gate, regression path, refusal or recovery behavior, and closeout artifact.
2. Make FastAPI structurally default-deny with a route inventory, explicit public
   allowlist, forged-token cases, low-privilege mutation checks, and fail-closed
   behavior when JWT signing configuration is missing or invalid.
3. Freeze repository selector precedence as exact ID, exact name, then
   canonicalized path; test ambiguity, symlinks, allowed roots, git-common-dir,
   nested paths, duplicate identities, and sibling worktrees.
4. Give corrupt, missing-schema, and missing-provenance indexes an actionable
   quarantine-and-rebuild path instead of a remediation that reindex refuses.
5. Replace soft reindex atomicity wording with a per-repo lock, sibling temporary
   build, validation, atomic replacement, provenance publication ordering, and
   failure-injection/concurrency tests.
6. Split summarization from plugin lifecycle so the worker-resource contract gets
   independent planning, evidence, and closeout.
7. Make `MemoryAwarePluginManager` the single lifecycle owner and require lazy
   allocation, child-RSS and worker-count caps, deterministic LRU/backpressure,
   idle expiry, repo eviction, graceful shutdown, and killed-parent reaping.
8. Make type-gate recovery evidence-driven: zero errors in every phase-owned core
   module, with only an enumerated shrinking baseline allowed for bounded legacy
   debt after a mandatory census.
9. Add static workflow-policy tests for immutable action SHAs, full-history
   ancestry checks, and an in-job protected-main guard immediately before every
   external release mutation.
10. Require every finding's regression to fail at the base commit and pass at its
    owning phase close, with no new failures relative to the frozen baseline.
11. Extend final evidence with an explicit browser console policy, unmarked-network
    audit, STDIO handshake smoke, hard-kill worker test, and workflow-policy proof.

## Reconciled Judgment Calls

### Quality phase placement

Gemini recommended moving QUALITY first because a red baseline can hide
regressions. Codex and Fable kept QUALITY after behavioral repair. The amended
roadmap keeps QUALITY after the behavioral phases because many current failures
are direct symptoms of those defects, but every earlier phase must freeze the base
failure inventory, run scoped tests, and prove it introduces no new failures.
QUALITY then removes the remaining known failures and installs the final gate.

### Summarization and plugin lifecycle

Codex recommended splitting the combined phase; Fable considered two disjoint
lanes sufficient. The roadmap splits them. Summarization is a bounded internal
contract fix, while plugin lifecycle includes process ownership, memory policy,
backpressure, platform behavior, and hard-kill reaping. Separate closeout evidence
is safer and easier to plan without overlapping ownership.

### Type checking

The original all-project mypy-zero criterion was replaced with an evidence-gated
contract. Core phase-owned runtime modules must reach zero. If the entry census
shows legacy debt is unbounded for this roadmap, an exact per-module baseline may
be introduced only with a CI ratchet that forbids growth or new excluded modules.
This closes the missing-gate defect without an unmeasured repository-wide rewrite.

## Non-Blocking Recommendations Retained For Planning

- Use typed error codes consistently for auth, selector, readiness, reindex, and
  worker-budget refusals.
- Keep cold-start latency bounded after lazy plugin loading.
- Prefer corrupt-index quarantine over deletion for diagnostic preservation.
- Consider GitHub environment required reviewers as release defense in depth.
- Keep AUTHBOUND and REPOSEL serial for shared-fixture merge safety even though
  their production contracts are orthogonal.

## Recommendation

The amended roadmap passes `phase-loop validate-roadmap` with eight phases and is
approved for `codex-plan-phase` followed by `codex-execute-phase` in DAG order.
