#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
missing=0
required() {
  local cmd="$1"
  shift
  if command -v "$cmd" >/dev/null 2>&1 && "$cmd" "$@" 2>/dev/null; then
    echo "REQUIRED OK: $cmd"
  else
    echo "REQUIRED MISSING/BROKEN: $cmd" >&2
    missing=1
  fi
}
required uv --version
required git --version
required node --version
required npm --version
required codex --version
required make --version
if command -v uv >/dev/null 2>&1 && uv run --locked python -c 'import sys; print(sys.version); sys.exit(0 if sys.version_info[:2] == (3, 11) else 1)'; then
  echo "REQUIRED OK: project Python 3.11"
else
  echo "REQUIRED MISSING/BROKEN: project Python 3.11" >&2
  missing=1
fi
if command -v docker >/dev/null 2>&1; then
  docker --version
  docker compose version || echo "OPTIONAL UNAVAILABLE: Docker Compose"
  if docker info >/dev/null 2>&1; then
    echo "OPTIONAL OK: Docker daemon"
    if docker compose ps --status running --services 2>/dev/null | grep -qx postgres; then
      docker compose exec -T postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' ||
        echo "OPTIONAL UNAVAILABLE: Compose PostgreSQL readiness"
    else
      echo "OPTIONAL UNAVAILABLE: Compose PostgreSQL not running"
    fi
  else
    echo "OPTIONAL UNAVAILABLE: Docker daemon"
  fi
else
  echo "OPTIONAL UNAVAILABLE: Docker"
fi
if command -v pg_isready >/dev/null 2>&1; then
  pg_isready -h 127.0.0.1 -p "${POSTGRES_PORT:-5433}" -t 2 ||
    echo "OPTIONAL UNAVAILABLE: PostgreSQL connectivity"
else
  echo "OPTIONAL UNAVAILABLE: PostgreSQL client readiness tool"
fi
for cmd in curl wget jq gcc g++ psql direnv nvidia-smi; do
  command -v "$cmd" >/dev/null 2>&1 &&
    echo "OPTIONAL PRESENT: $cmd" || echo "OPTIONAL MISSING: $cmd"
done
exit "$missing"

