# End-to-End Testing and Benchmarking

This guide covers how to validate indexing/retrieval end-to-end and benchmark MCP
against native retrieval methods (`grep`, `rg`, `glob`).

## Prerequisites

- Qdrant reachable (`http://localhost:6333` by default)
- Fireworks API key (for cloud Qwen profile)
- Optional local OpenAI-compatible endpoint (for local Qwen profile)
- Voyage key configured when running commercial profile benchmarks

### Recommended Cloud Provider for Qwen

Use Fireworks AI for cloud-hosted Qwen embeddings:

- Base URL: `https://api.fireworks.ai/inference/v1`
- Model: `fireworks/qwen3-embedding-8b`
- Env key: `FIREWORKS_API_KEY`

Example shell setup:

```bash
export OPENAI_API_BASE=https://api.fireworks.ai/inference/v1
export FIREWORKS_BASE=https://api.fireworks.ai/inference/v1
export FIREWORKS_API_KEY="<fireworks_api_key>"
export VOYAGE_API_KEY="<voyage_api_key>"
export LOCAL_OPENAI_BASE=http://ai:8001/v1
```

## 1) E2E Retrieval Validation

Run full retrieval validation on this repository:

```bash
uv run python scripts/run_e2e_retrieval_validation.py \
  --repo . \
  --max-files 5000 \
  --semantic-max-chars 5000000 \
  --iterations 5 \
  --limit 5 \
  --qdrant-url http://localhost:6333 \
  --fireworks-base ${FIREWORKS_BASE:-https://api.fireworks.ai/inference/v1} \
  --fireworks-api-key ${FIREWORKS_API_KEY} \
  --qwen-model fireworks/qwen3-embedding-8b \
  --qwen-dim 4096 \
  --enable-voyage \
  --local-openai-base ${LOCAL_OPENAI_BASE:-http://ai:8001/v1} \
  --local-qwen-model Qwen/Qwen3-Embedding-8B \
  --json-out docs/benchmarks/e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.json \
  --md-out docs/benchmarks/e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md
```

Outputs:

- `docs/benchmarks/e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.json`
- `docs/benchmarks/e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md`

Validated modes:

- `classic` (SQLite FTS)
- `bm25`
- `fuzzy`
- `semantic` (Qwen)
- `hybrid`
- semantic model comparison (Qwen vs Voyage)

## 2) MCP vs Native Benchmark

```bash
uv run python scripts/run_mcp_vs_native_benchmark.py --repo .

# Cloud Qwen + Voyage
uv run python scripts/run_mcp_vs_native_benchmark.py \
  --repo . \
  --max-files 5000 \
  --semantic-max-chars 5000000 \
  --iterations 5 \
  --qdrant-url http://localhost:6333 \
  --fireworks-base ${FIREWORKS_BASE:-https://api.fireworks.ai/inference/v1} \
  --fireworks-api-key ${FIREWORKS_API_KEY} \
  --qwen-model fireworks/qwen3-embedding-8b \
  --qwen-dim 4096 \
  --enable-voyage \
  --local-openai-base ${LOCAL_OPENAI_BASE:-http://ai:8001/v1} \
  --local-qwen-model Qwen/Qwen3-Embedding-8B \
  --out-json docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.json \
  --out-md docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md
```

Outputs:

- `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.json`
- `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md`

Benchmark compares:

- MCP retrieval suite pass-rate
- `rg` pass-rate and latency
- `grep` pass-rate and latency
- `glob` filename-oriented baseline

## 3) Matrix Benchmark (Rerankers × Embeddings × Modes)

Runs 17 curated queries across all embedding configs, retrieval modes, and rerankers:

```bash
VOYAGE_API_KEY=$VOYAGE_API_KEY SEMANTIC_SEARCH_ENABLED=true \
  python scripts/run_matrix_benchmark.py \
    --md-out docs/benchmarks/matrix_benchmark.md \
    --json-out docs/benchmarks/matrix_benchmark.json
```

Outputs:
- `docs/benchmarks/matrix_benchmark.md` — results table
- `docs/benchmarks/matrix_benchmark.json` — for CI regression checks

Current results (2026-04-01): voyage-code-3 and Qwen3-Embedding-8B both hit **17/17**
top-1 pass rate with semantic search enabled. BM25-only achieves 12–13/17.

## 4) Interpreting Results

- If lexical pass-rate regresses: inspect BM25/FTS indexing and symbol upserts.
- If semantic pass-rate regresses: inspect embedding endpoint, profile dimensions, and vector collection.
- If hybrid regresses: tune BM25/semantic/fuzzy weights and top-k limits.
- If hybrid p95 remains high (>5s): inspect branch timeout logs and per-branch latency budgets.
