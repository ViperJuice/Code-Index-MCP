# Full-Repo Benchmark Analysis (2026-03-05)

This report summarizes the latest full-repository benchmark rerun after hybrid timeout hardening and benchmark-suite upgrades.

## Scope

- Full repository indexing (`1282` files)
- Retrieval modes: `classic`, `bm25`, `fuzzy`, `semantic`, `hybrid`
- Semantic providers in one run:
  - Qwen via Fireworks: `fireworks/qwen3-embedding-8b`
  - Voyage: `voyage-code-3`
  - Local Qwen endpoint on tailnet: `Qwen/Qwen3-Embedding-8B`
- Native baseline methods: `rg`, `grep`, `glob`
- Repeated-run stability with `--iterations 5` and p50/p95 reporting

Primary artifacts (latest rerun):

- `docs/benchmarks/e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.json`
- `docs/benchmarks/e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md`
- `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.json`
- `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md`

Previous comparable artifacts:

- `docs/benchmarks/e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage_local_iter5.json`
- `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_local_iter5.json`

## Headline Results

| Metric | Previous | Latest Rerun | Delta |
|---|---:|---:|---:|
| Indexed files | 1280 | 1282 | +2 |
| MCP Top-1 pass rate (E2E) | 33.3% | 33.3% | 0.0 |
| MCP Top-3 pass rate (E2E) | 55.6% | 64.4% | +8.8 |
| Native pass rate (`rg`/`grep`/`glob`) | 44.4% | 44.4% | 0.0 |
| MCP pass rate (`mcp_vs_native`) | 33.3% | 33.3% | 0.0 |

## Mode Detail (Latest E2E)

| Mode | Category | Top-1 | Top-3 | p50 (ms) | p95 (ms) | Notes |
|---|---|---:|---:|---:|---:|---|
| classic | semantic | 0.0% | 0.0% | 2.88 | 3.83 | still dominated by benchmark-doc matches |
| bm25 | symbol_precise | 100.0% | 100.0% | 46.45 | 51.8 | stable and accurate |
| fuzzy | noisy | 100.0% | 100.0% | 10.11 | 13.16 | stable and fast |
| semantic | general | 100.0% | 100.0% | 265.01 | 271.96 | stable on direct intent probe |
| hybrid | semantic_intent | 0.0% | 80.0% | 5093.14 | 9388.48 | better recall, still poor Top-1 and high tail |
| bm25 | symbol_precise (`class SemanticIndexer`) | 0.0% | 100.0% | 18.44 | 21.94 | candidate present but rank-1 wrong |
| semantic | semantic_intent | 0.0% | 0.0% | 265.27 | 275.95 | intent query still points to docs |
| fuzzy | noisy (`SemnticIndexer`) | 0.0% | 100.0% | 18.4 | 22.02 | candidate present but rank-1 wrong |
| hybrid | persistence | 0.0% | 0.0% | 8381.4 | 8434.29 | remains critical bottleneck |

## Provider Latency Comparison (Latest E2E)

| Provider mode | Top-1 | Top-3 | p50 (ms) | p95 (ms) |
|---|---:|---:|---:|---:|
| `semantic_qwen_local` | 100.0% | 100.0% | 49.22 | 70.26 |
| `semantic_voyage` | 100.0% | 100.0% | 116.68 | 134.45 |
| `semantic_qwen` (Fireworks) | 100.0% | 100.0% | 238.5 | 1123.12 |

Interpretation:

- Local Qwen remains the lowest-latency provider for this workload.
- Voyage remains significantly faster than cloud Qwen on p50 and p95.

## What Improved

- Hybrid branch timeout handling no longer collapses all branch output in benchmark runs.
- Hybrid semantic-intent Top-3 moved from `0.0%` to `80.0%`, confirming candidate recall improvement.
- End-to-end benchmark output now consistently includes p50/p95 and Top-1/Top-3 metrics.

## What Still Fails

- Top-1 ranking quality is still low in key intent and persistence queries.
- Hybrid latency remains very high in intent/persistence paths (>5s p50).
- Classic benchmark probe still surfaces benchmark artifacts instead of source implementation.

## Root Causes (Current)

1. **Ranking objective mismatch**: source code vs docs/benchmark artifacts is not strongly encoded in ranking.
2. **Hybrid tail latency**: one slow branch (often semantic) still dominates overall latency in difficult queries.
3. **Fusion/reranking gap**: candidates are often present in Top-3 but not promoted to Top-1.

## Next Engineering Actions

1. Add code-vs-doc prior in post-fusion ranking (`.py` source preferred for implementation-seeking queries).
2. Add branch-level budgets and adaptive limits for hybrid (`semantic` cap lower for broad queries).
3. Enable second-stage reranking for hybrid top-k candidates and evaluate Top-1 lift.
4. Add benchmark query labels for implementation-vs-explanation intent and score separately.

## Reproduction Commands

```bash
# Full-repo E2E (Fireworks Qwen + Voyage + Local Qwen)
uv run python scripts/run_e2e_retrieval_validation.py \
  --repo . \
  --max-files 5000 \
  --semantic-max-chars 5000000 \
  --iterations 5 \
  --limit 5 \
  --qdrant-url http://localhost:6333 \
  --fireworks-base https://api.fireworks.ai/inference/v1 \
  --fireworks-api-key "$FIREWORKS_API_KEY" \
  --qwen-model fireworks/qwen3-embedding-8b \
  --qwen-dim 4096 \
  --enable-voyage \
  --local-openai-base http://ai:8001/v1 \
  --local-qwen-model Qwen/Qwen3-Embedding-8B

# MCP vs native benchmark (same provider setup)
uv run python scripts/run_mcp_vs_native_benchmark.py \
  --repo . \
  --max-files 5000 \
  --semantic-max-chars 5000000 \
  --iterations 5 \
  --qdrant-url http://localhost:6333 \
  --fireworks-base https://api.fireworks.ai/inference/v1 \
  --fireworks-api-key "$FIREWORKS_API_KEY" \
  --qwen-model fireworks/qwen3-embedding-8b \
  --qwen-dim 4096 \
  --enable-voyage \
  --local-openai-base http://ai:8001/v1 \
  --local-qwen-model Qwen/Qwen3-Embedding-8B
```
