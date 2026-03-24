#!/usr/bin/env bash
# Build the xmind skill package into build/xmind-skill.zip
# Usage: bash scripts/build-skill.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILL_DIR="$REPO_ROOT/skills/xmind"
BUILD_DIR="$REPO_ROOT/build"

mkdir -p "$BUILD_DIR"

# Remove old build artifact
rm -f "$BUILD_DIR/xmind-skill.zip"

# Package with xmind/ prefix so unzip directly creates the right structure
cd "$SKILL_DIR/.."
zip -r "$BUILD_DIR/xmind-skill.zip" \
  xmind/SKILL.md \
  xmind/scripts/create_xmind.mjs \
  xmind/scripts/read_xmind.mjs

echo ""
echo "Built: $BUILD_DIR/xmind-skill.zip"
echo "Contents:"
unzip -l "$BUILD_DIR/xmind-skill.zip"
echo ""
echo "Install:"
echo "  unzip -o $BUILD_DIR/xmind-skill.zip -d ~/.claude/skills/"
