# End-to-End Testing and Benchmarking

This guide covers how to validate indexing/retrieval end-to-end and benchmark MCP
against native retrieval methods (`grep`, `rg`, `glob`).

## Prerequisites

- Qdrant reachable (`http://localhost:6333` by default)
- OpenAI-compatible embedding endpoint (for Qwen profile)
- Voyage key configured when running commercial profile benchmarks

### Recommended Cloud Provider for Qwen

Use Fireworks AI for cloud-hosted Qwen embeddings (OpenAI-compatible API):

- Base URL: `https://api.fireworks.ai/inference/v1`
- Model: `fireworks/qwen3-embedding-8b`
- Env key: `OPENAI_API_KEY` (Fireworks API key)

Example shell setup:

```bash
export OPENAI_API_BASE=https://api.fireworks.ai/inference/v1
export OPENAI_API_KEY="<fireworks_api_key>"
```

## 1) E2E Retrieval Validation

Run full retrieval validation on this repository:

```bash
uv run python scripts/run_e2e_retrieval_validation.py \
  --repo . \
  --qdrant-url http://localhost:6333 \
  --openai-base ${OPENAI_API_BASE:-https://api.fireworks.ai/inference/v1} \
  --openai-key ${OPENAI_API_KEY} \
  --qwen-model fireworks/qwen3-embedding-8b \
  --enable-voyage
```

Outputs:

- `docs/benchmarks/e2e_retrieval_validation.json`
- `docs/benchmarks/e2e_retrieval_validation.md`

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
  --qdrant-url http://localhost:6333 \
  --openai-base ${OPENAI_API_BASE:-https://api.fireworks.ai/inference/v1} \
  --openai-key ${OPENAI_API_KEY} \
  --qwen-model fireworks/qwen3-embedding-8b \
  --enable-voyage
```

Outputs:

- `docs/benchmarks/mcp_vs_native_benchmark.json`
- `docs/benchmarks/mcp_vs_native_benchmark.md`

Benchmark compares:

- MCP retrieval suite pass-rate
- `rg` pass-rate and latency
- `grep` pass-rate and latency
- `glob` filename-oriented baseline

## 3) Interpreting Results

- If lexical pass-rate regresses: inspect BM25/FTS indexing and symbol upserts.
- If semantic pass-rate regresses: inspect embedding endpoint, profile dimensions, and vector collection.
- If hybrid regresses: tune BM25/semantic/fuzzy weights and top-k limits.
