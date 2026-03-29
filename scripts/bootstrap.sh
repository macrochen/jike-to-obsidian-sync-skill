#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ ! -x "${SKILL_DIR}/.venv/bin/python" ]]; then
  echo "Missing virtual environment at ${SKILL_DIR}/.venv"
  echo "Create it first with: python3 -m venv ${SKILL_DIR}/.venv"
  exit 1
fi

"${SKILL_DIR}/.venv/bin/pip" install playwright
"${SKILL_DIR}/.venv/bin/playwright" install chromium

echo "Bootstrap complete."
