# Frozen Retrieval Evaluation Dataset (BENCHFREEZE)

This directory is the **frozen, human-reviewed retrieval evaluation contract**
for the roadmap-v10 retrieval rollout gate (phase `BENCHFREEZE`). It fixes the
query set, the corpus, and the numeric pass/fail thresholds **before any
provider run or tuning**, so the default-enablement decision rests on a
pre-committed measure rather than a post-hoc one.

**FROZEN.** Do not edit `queries.jsonl`, `gate_thresholds.json`,
`corpus_manifest.json`, or `MANIFEST.json` as part of tuning. A reviewer MAY
revise threshold *values* before provider work begins, but any change must be
followed by regenerating the checksums in `MANIFEST.json` — the files and their
recorded sha256 digests are the binding contract. The evaluation harness
(Lane B) refuses to run if `MANIFEST.json` is missing, unsigned, or its
checksums do not match the on-disk files.

## Files

| File | Schema | Purpose |
|------|--------|---------|
| `queries.jsonl` | one JSON object per line | Curated query set with relevant + hard-negative doc ids and a holdout flag. |
| `corpus_manifest.json` | — | The fixed corpus: repo, commit, included globs, doc count, and the corpus path-list checksum. |
| `gate_thresholds.json` | `gate.v1` | Pre-declared per-arm/per-depth quality, latency, error, and egress thresholds plus the decision algorithm. |
| `MANIFEST.json` | `manifest.v1` | Binds the three artifacts by checksum, lists holdout ids, and records the signed review. |

## `queries.jsonl` fields

Each line: `{"id","query","category","relevant_doc_ids":[...],
"hard_negative_doc_ids":[...],"holdout":true|false}`.

- `relevant_doc_ids` / `hard_negative_doc_ids` are repo-relative paths that are
  real and git-tracked at the pinned commit, and are all members of the frozen
  corpus.
- Categories: `exact_identifier`, `implementation_intent`, `error_operational`,
  `config_doc_lookup`, `architectural_conceptual`, `cross_file_relationship`,
  `hard_negative_vocab`.

## Holdout

Queries with `holdout: true` (also enumerated in `MANIFEST.json`
`holdout_query_ids`) form the held-out split. **The holdout must never be used
for tuning, threshold selection, weight fitting, or reranker selection.**
`gate_thresholds.json` sets `holdout_unused_required: true`; a run is invalid if
any holdout id influenced tuning.

## How checksums are computed

All digests are SHA-256, lowercase hex.

- **`dataset_sha256`** — SHA-256 of the raw bytes of `queries.jsonl` as written
  (UTF-8, one compact JSON object per line, `\n`-terminated including a trailing
  newline).
- **`thresholds_sha256`** — SHA-256 of the raw bytes of `gate_thresholds.json`
  as written (UTF-8, `json.dumps(indent=2)` plus a trailing newline).
- **`corpus_sha256`** — SHA-256 of the UTF-8 bytes of the **sorted list of
  included relative paths** joined by a single newline (`\n`), with **no**
  trailing newline. This is a checksum of the path list, not of
  `corpus_manifest.json`. The same value appears in both `corpus_manifest.json`
  and `MANIFEST.json`.

Reproduce, e.g.:

```bash
sha256sum queries.jsonl gate_thresholds.json
# corpus digest:
python3 - <<'PY'
import json, hashlib, subprocess, fnmatch
m = json.load(open("corpus_manifest.json"))
tracked = subprocess.run(["git","ls-files"],capture_output=True,text=True).stdout.splitlines()
# (see corpus_manifest.included_globs for the match rule)
PY
```

The verification is order-sensitive: `queries.jsonl` and `gate_thresholds.json`
are written first, then their bytes are hashed into `MANIFEST.json` last, so the
recorded digests always match the shipped files.
