#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env.staging}"
if [[ ! -f "$ENV_FILE" ]]; then echo "ERROR: $ENV_FILE not found."; exit 2; fi
docker compose --env-file "$ENV_FILE" -f "$ROOT/docker-compose.yml" -f "$ROOT/docker-compose.staging.yml" ps
