#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
command -v uv >/dev/null || { echo "Install uv using the official Astral installer first." >&2; exit 1; }
uv python install 3.11
uv sync --locked
bash scripts/check_environment.sh
