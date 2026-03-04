# End-to-End Testing and Benchmarking

This guide covers how to validate indexing/retrieval end-to-end and benchmark MCP
against native retrieval methods (`grep`, `rg`, `glob`).

## Prerequisites

- Qdrant reachable (`http://localhost:6333` by default)
- OpenAI-compatible embedding endpoint (for Qwen profile)
- Voyage key configured when running commercial profile benchmarks

## 1) E2E Retrieval Validation

Run full retrieval validation on this repository:

```bash
uv run python scripts/run_e2e_retrieval_validation.py \
  --repo . \
  --qdrant-url http://localhost:6333 \
  --openai-base http://ai:8001/v1 \
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
