#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

DEFAULT_START_URL="https://web.okjike.com/u/548BF245-5632-4652-B4AA-B87307BEC0FA"
DEFAULT_OUTPUT_ROOT="/Users/shi/workspace/my-skills/Obsidian-Knowledge-Base"

START_URL="${JKE_START_URL:-$DEFAULT_START_URL}"
OUTPUT_ROOT="${JKE_OUTPUT_ROOT:-$DEFAULT_OUTPUT_ROOT}"

"${SKILL_DIR}/.venv/bin/python" "${SCRIPT_DIR}/sync_jike.py" \
  --source jike-web \
  --start-url "${START_URL}" \
  --output-root "${OUTPUT_ROOT}"
