# Full-Repo Benchmark Analysis (2026-03-04)

This document summarizes full-repository end-to-end testing and benchmark results for `Code-Index-MCP`, including persistence validation, retrieval quality, and latency observations.

## Scope

The benchmark run covered:

- Full repository indexing (`1266` files)
- Retrieval modes: `classic`, `bm25`, `fuzzy`, `semantic`, `hybrid`
- Semantic providers:
  - Qwen via Fireworks: `fireworks/qwen3-embedding-8b`
  - Voyage: `voyage-code-3`
- Native baselines: `rg`, `grep`, `glob`

Primary artifact files:

- `docs/benchmarks/e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage.json`
- `docs/benchmarks/e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage.md`
- `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage.json`
- `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage.md`

## High-Level Results

| Metric | Value |
|---|---:|
| Files indexed | 1266 |
| Semantic skipped files | 1 |
| MCP query-suite pass rate | 60.0% |
| Native tools pass rate | 55.6% |

### Mode-by-Mode (E2E Suite)

| Mode | Pass | Top-file behavior | Query latency |
|---|---|---|---:|
| classic | no | returned 0 results | 9.98 ms |
| bm25 | yes | correct target file surfaced | 41.58 ms |
| fuzzy | yes | typo-tolerant match correct | 12.94 ms |
| semantic | yes | correct target file surfaced | 402.88 ms |
| hybrid | no | result count present, top-file empty | 5090.93 ms |

### Semantic Provider Comparison

| Model | Pass | Top-file correctness | Latency |
|---|---|---|---:|
| Qwen (Fireworks) | yes | correct | 368.13 ms |
| Voyage code-3 | yes | correct | 116.5 ms |

## What Worked Well

1. **Dual semantic providers worked in the same run** (Qwen + Voyage).
2. **BM25 and fuzzy were reliable and fast** for code-focused probes.
3. **Semantic relevance was strong** on intent-style query (`where is qdrant autostart implemented`).
4. **Persistence workflow tests passed** (`tests/test_artifact_lifecycle.py`) for:
   - commit artifact create/extract
   - delta create/apply
   - delta chain resolution

## Issues Found

1. **Classic retrieval underperformed** for the benchmark suite’s semantic-preflight probe (`count=0`).
2. **Hybrid result shaping/scoring path has defects** (`Search error in method 2: 'score'` seen during benchmark execution).
3. **Hybrid latency is high** (~5s for the tested query), likely due to serial fallback and result normalization paths.
4. **Native baselines are noisy by design** for semantic intent probes; `glob` especially is weak for code-intent retrieval.

## Interpretation

- Current implementation already demonstrates meaningful value for MCP retrieval over native baselines in this mixed query suite.
- The measured gap is constrained by two known defects (`classic`, `hybrid`) rather than semantic model quality.
- Voyage latency is significantly lower than Qwen cloud in this specific run; Qwen still returns correct result quality.

## Improvement Plan

### Priority 1 (Correctness)

1. **Fix classic mode retrieval path** for benchmark probes.
2. **Fix hybrid score normalization/result shaping** so top-file is always populated when results exist.
3. Add regression tests for those two paths using the benchmark query suite.

### Priority 2 (Latency)

1. Reduce hybrid overhead by:
   - parallel branch execution hardening,
   - tighter per-branch limits,
   - score normalization safeguards when one branch returns sparse payloads.
2. Add p50/p95 reporting to benchmark scripts for repeated-run stability.

### Priority 3 (Benchmark Quality)

1. Expand query suite with:
   - symbol-precise queries,
   - semantic intent queries,
   - typo/noisy queries,
   - branch/recovery/persistence probes.
2. Track Top-1 and Top-3 accuracy in addition to simple pass/fail.

## Reproduction Commands

```bash
# Full-repo E2E (Qwen + Voyage)
uv run python scripts/run_e2e_retrieval_validation.py \
  --repo . \
  --max-files 5000 \
  --semantic-max-chars 5000000 \
  --limit 5 \
  --qdrant-url http://localhost:6333 \
  --openai-base https://api.fireworks.ai/inference/v1 \
  --openai-key $OPENAI_API_KEY \
  --qwen-model fireworks/qwen3-embedding-8b \
  --qwen-dim 4096 \
  --enable-voyage

# MCP vs native benchmark
uv run python scripts/run_mcp_vs_native_benchmark.py \
  --repo . \
  --max-files 5000 \
  --semantic-max-chars 5000000 \
  --qdrant-url http://localhost:6333 \
  --openai-base https://api.fireworks.ai/inference/v1 \
  --openai-key $OPENAI_API_KEY \
  --qwen-model fireworks/qwen3-embedding-8b \
  --qwen-dim 4096 \
  --enable-voyage
```
