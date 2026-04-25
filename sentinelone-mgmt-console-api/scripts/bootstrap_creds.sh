#!/usr/bin/env bash
# Copy SentinelOne credentials from a Cowork-accessible folder to a
# sandbox-local path that every S1 skill reads from.
#
# Source (priority order):
#   1. $COWORK_WORKSPACE/.sentinelone/credentials.json       (recommended explicit)
#   2. $COWORK_WORKSPACE/.claude/sentinelone/credentials.json (legacy layout)
#   3. $HOME/mnt/<folder>/.sentinelone/credentials.json       (any mounted folder)
#   4. $HOME/mnt/<folder>/.claude/sentinelone/credentials.json (legacy)
#
# Destination: $HOME/.claude/sentinelone/credentials.json
#   In the Cowork bash sandbox this resolves to
#   /sessions/<id>/.claude/sentinelone/credentials.json — sandbox-local,
#   ephemeral per session, readable by every script and CLI in the skill.
#
# Idempotent. Safe to run before every workflow. Returns the path it used.
# Exit 0 on success, 1 if no source was found.
#
# Usage:
#   bash scripts/bootstrap_creds.sh
#   # or, sourcing for the path:
#   CREDS_PATH=$(bash scripts/bootstrap_creds.sh) && export CREDS_PATH

set -eu

DEST="$HOME/.claude/sentinelone/credentials.json"
DEST_DIR="$(dirname "$DEST")"

# If the destination already exists and is non-empty, no-op. This makes
# repeated calls cheap and avoids overwriting a user-managed file.
if [ -s "$DEST" ]; then
    echo "$DEST"
    exit 0
fi

mkdir -p "$DEST_DIR"
chmod 700 "$DEST_DIR" 2>/dev/null || true

# Build the search list. Use eval-free globbing: shell expands the patterns
# directly. Missing matches expand to a literal that we then test with -f.
shopt -s nullglob 2>/dev/null || true

candidates=()
if [ -n "${COWORK_WORKSPACE:-}" ]; then
    candidates+=("$COWORK_WORKSPACE/.sentinelone/credentials.json")
    candidates+=("$COWORK_WORKSPACE/.claude/sentinelone/credentials.json")
fi
# Glob any folder under ~/mnt for the two layouts. Skip system mounts.
for mnt in "$HOME"/mnt/*/; do
    base="$(basename "$mnt")"
    case "$base" in
        .claude|.auto-memory|.remote-plugins|outputs|uploads) continue ;;
    esac
    candidates+=("$mnt.sentinelone/credentials.json")
    candidates+=("$mnt.claude/sentinelone/credentials.json")
done

for src in "${candidates[@]}"; do
    if [ -f "$src" ]; then
        cp "$src" "$DEST"
        chmod 600 "$DEST" 2>/dev/null || true
        echo "$DEST"
        exit 0
    fi
done

echo "bootstrap_creds: no credentials.json found." >&2
echo "  Drop it at \$COWORK_WORKSPACE/.sentinelone/credentials.json" >&2
echo "  (or any folder Cowork has access to under .sentinelone/credentials.json)" >&2
exit 1
