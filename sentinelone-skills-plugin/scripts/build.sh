#!/usr/bin/env bash
# build.sh -- build individual .skill files and the combined .plugin for sentinelone-skills
#
# Usage (run from anywhere inside the repo):
#   ./scripts/build.sh            # build everything into dist/
#   ./scripts/build.sh --clean    # remove old .skill/.plugin from dist/ first, then build
#
# Source layout expected:
#   claude-skills/
#     sentinelone-mgmt-console-api/   <- source skill
#     sentinelone-powerquery/          <- source skill
#     sentinelone-sdl-api/             <- source skill
#     sentinelone-sdl-log-parser/      <- source skill
#     sentinelone-skills-plugin/
#       .claude-plugin/plugin.json
#       skills/
#         sentinelone-hyperautomation/ <- only skill that lives here (no standalone source)
#       scripts/build.sh  (this file)
#       dist/                          <- output
#
# Output in dist/:
#   sentinelone-hyperautomation.skill
#   sentinelone-mgmt-console-api.skill
#   sentinelone-powerquery.skill
#   sentinelone-sdl-api.skill
#   sentinelone-sdl-log-parser.skill
#   sentinelone-skills-v{version}.plugin

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$PLUGIN_DIR/.." && pwd)"
DIST_DIR="$PLUGIN_DIR/dist"

# Skills sourced directly from the repo root (no copies needed)
SOURCE_SKILLS=(
    sentinelone-mgmt-console-api
    sentinelone-powerquery
    sentinelone-sdl-api
    sentinelone-sdl-log-parser
)

# Skills that only exist inside the plugin folder
PLUGIN_ONLY_SKILLS=(
    sentinelone-hyperautomation
)

# Read version from plugin.json
PLUGIN_JSON="$PLUGIN_DIR/.claude-plugin/plugin.json"
if [ ! -f "$PLUGIN_JSON" ]; then
    echo "ERROR: $PLUGIN_JSON not found" >&2
    exit 1
fi

VERSION="$(python3 -c "import json; print(json.load(open('$PLUGIN_JSON'))['version'])")"
if [ -z "$VERSION" ]; then
    echo "ERROR: could not read version from $PLUGIN_JSON" >&2
    exit 1
fi

echo "Building sentinelone-skills v$VERSION"
echo "  Repo root : $REPO_ROOT"
echo "  Plugin dir: $PLUGIN_DIR"

# Build into a temp directory first to avoid filesystem permission issues
TMP_DIST="$(mktemp -d)"
trap 'rm -rf "$TMP_DIST"' EXIT

# ---------------------------------------------------------------------------
# 1. Build individual .skill files
# ---------------------------------------------------------------------------
echo ""
echo "Building individual .skill files..."

zip_skill() {
    local skill_name="$1"
    local skill_path="$2"
    local out_file="$TMP_DIST/${skill_name}.skill"

    if [ ! -d "$skill_path" ]; then
        echo "  ERROR: $skill_path not found" >&2
        exit 1
    fi

    echo "  $skill_name.skill  (from $skill_path)"
    local tmp_skill
    tmp_skill="$(mktemp -d)"
    cp -r "$skill_path" "$tmp_skill/$skill_name"
    (cd "$tmp_skill" && zip -qr "$out_file" "$skill_name/")
    rm -rf "$tmp_skill"
}

# Source skills from repo root
for skill_name in "${SOURCE_SKILLS[@]}"; do
    zip_skill "$skill_name" "$REPO_ROOT/$skill_name"
done

# Plugin-only skills from inside the plugin folder
for skill_name in "${PLUGIN_ONLY_SKILLS[@]}"; do
    zip_skill "$skill_name" "$PLUGIN_DIR/skills/$skill_name"
done

# ---------------------------------------------------------------------------
# 2. Build the combined .plugin file
# ---------------------------------------------------------------------------
echo ""
PLUGIN_FILENAME="sentinelone-skills-v${VERSION}.plugin"
PLUGIN_FILE="$TMP_DIST/$PLUGIN_FILENAME"
echo "Building plugin: $PLUGIN_FILENAME"

# Stage a clean plugin tree into a temp dir so we can include source skills
# without polluting the actual plugin directory.
TMP_PLUGIN="$(mktemp -d)"
trap 'rm -rf "$TMP_DIST" "$TMP_PLUGIN"' EXIT

# Copy the plugin metadata and plugin-only skills
cp -r "$PLUGIN_DIR/.claude-plugin" "$TMP_PLUGIN/"
mkdir -p "$TMP_PLUGIN/skills"
for skill_name in "${PLUGIN_ONLY_SKILLS[@]}"; do
    cp -r "$PLUGIN_DIR/skills/$skill_name" "$TMP_PLUGIN/skills/"
done

# Copy source skills in
for skill_name in "${SOURCE_SKILLS[@]}"; do
    cp -r "$REPO_ROOT/$skill_name" "$TMP_PLUGIN/skills/"
done

# Copy credentials example if present
[ -f "$REPO_ROOT/credentials.example.json" ] && cp "$REPO_ROOT/credentials.example.json" "$TMP_PLUGIN/"

(cd "$TMP_PLUGIN" && zip -qr "$PLUGIN_FILE" . \
    --exclude ".git/*" \
    --exclude "*.orig" \
    --exclude ".DS_Store" \
    --exclude "*/__pycache__/*" \
    --exclude "*.pyc")

# ---------------------------------------------------------------------------
# 3. Copy artifacts to dist/
# ---------------------------------------------------------------------------
echo ""
echo "Copying to dist/..."

if [[ "${1:-}" == "--clean" ]]; then
    echo "  Removing old .skill and .plugin files from dist/"
    rm -f "$DIST_DIR"/*.skill "$DIST_DIR"/*.plugin
fi

mkdir -p "$DIST_DIR"
cp "$TMP_DIST"/*.skill "$TMP_DIST"/*.plugin "$DIST_DIR/"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "Done. Contents of dist/:"
ls -lh "$DIST_DIR"
