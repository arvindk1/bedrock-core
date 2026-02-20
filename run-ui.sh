#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Load .env if present
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

if [ -z "${AGENTCORE_RUNTIME_ARN:-}" ]; then
  echo "Warning: AGENTCORE_RUNTIME_ARN not set. Set it in .env or export it."
fi

exec uv run uvicorn ui.server:app --reload --host 0.0.0.0 --port 8080
