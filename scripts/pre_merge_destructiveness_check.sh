#!/usr/bin/env bash
# Pre-merge destructiveness check for lane branches.
# Usage: pre_merge_destructiveness_check.sh <lane_sha> <merge_target> [whitelist_file]
#
# Exit codes / verdicts printed to stdout:
#   SAFE                  — no unwhitelisted destructive changes; merge proceeds
#   STALE_BASE_DETECTED   — lane_sha is not an ancestor of merge_target tip
#   CONFLICT              — merge would conflict OR unwhitelisted destructive changes found

set -euo pipefail

LANE_SHA="${1:-}"
MERGE_TARGET="${2:-main}"
WHITELIST_FILE="${3:-}"

die() { echo "ERROR: $*" >&2; exit 2; }

[[ -n "$LANE_SHA" ]] || die "Usage: $0 <lane_sha> <merge_target> [whitelist_file]"

# Resolve refs to full SHAs
LANE_SHA=$(git rev-parse --verify "$LANE_SHA" 2>/dev/null) \
  || die "Cannot resolve lane SHA: $1"
TARGET_SHA=$(git rev-parse --verify "$MERGE_TARGET" 2>/dev/null) \
  || die "Cannot resolve merge target: $MERGE_TARGET"
MERGE_BASE=$(git merge-base "$LANE_SHA" "$TARGET_SHA" 2>/dev/null) \
  || die "No common ancestor between $LANE_SHA and $TARGET_SHA"

# ── 1. Stale-base check ──────────────────────────────────────────────────────
# A lane is stale when its merge-base is NOT the current tip of the target.
# (i.e. new commits landed on the target after the lane branched.)
if [[ "$MERGE_BASE" != "$TARGET_SHA" ]]; then
  echo "STALE_BASE_DETECTED"
  echo "  lane base : $MERGE_BASE"
  echo "  target tip: $TARGET_SHA"
  exit 1
fi

# ── 2. Conflict check ────────────────────────────────────────────────────────
CONFLICT_FILES=$(
  git merge-tree "$MERGE_BASE" "$TARGET_SHA" "$LANE_SHA" 2>/dev/null \
    | grep -c "^<<<<<<" || true
)
if [[ "$CONFLICT_FILES" -gt 0 ]]; then
  echo "CONFLICT"
  echo "  merge-tree reports $CONFLICT_FILES conflict marker(s)"
  exit 1
fi

# ── 3. Destructiveness check ─────────────────────────────────────────────────
# Collect files deleted or renamed (D/R) by the lane relative to the merge base.
DESTRUCTIVE_CHANGES=$(
  git diff --name-status "$MERGE_BASE" "$LANE_SHA" \
    | awk '$1 ~ /^[DR]/ { print $NF }' \
    | sort
)

if [[ -z "$DESTRUCTIVE_CHANGES" ]]; then
  echo "SAFE"
  exit 0
fi

# Load whitelist (one pattern per line; blank lines and # comments ignored).
WHITELISTED=()
if [[ -n "$WHITELIST_FILE" && -f "$WHITELIST_FILE" ]]; then
  while IFS= read -r line; do
    [[ "$line" =~ ^[[:space:]]*$ || "$line" =~ ^# ]] && continue
    WHITELISTED+=("$line")
  done < "$WHITELIST_FILE"
fi

UNWHITELISTED=()
while IFS= read -r path; do
  matched=0
  for pattern in "${WHITELISTED[@]:-}"; do
    # shellcheck disable=SC2254
    case "$path" in
      $pattern) matched=1; break ;;
    esac
  done
  [[ "$matched" -eq 0 ]] && UNWHITELISTED+=("$path")
done <<< "$DESTRUCTIVE_CHANGES"

if [[ "${#UNWHITELISTED[@]}" -gt 0 ]]; then
  echo "CONFLICT"
  echo "  Unwhitelisted destructive changes (${#UNWHITELISTED[@]}):"
  for f in "${UNWHITELISTED[@]}"; do
    echo "    - $f"
  done
  exit 1
fi

echo "SAFE"
echo "  All destructive changes are whitelisted (${#WHITELISTED[@]} entries)"
exit 0
