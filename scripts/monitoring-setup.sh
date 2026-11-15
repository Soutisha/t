#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"
[[ -f "$ENV_FILE" ]] || { echo "ERROR: $ENV_FILE not found."; exit 2; }
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
: "${METRICS_TOKEN:?METRICS_TOKEN is required in the environment file.}"
if (( ${#METRICS_TOKEN} < 32 )); then echo "ERROR: METRICS_TOKEN must be at least 32 characters."; exit 2; fi
mkdir -p "$ROOT/secrets"
umask 077
printf '%s' "$METRICS_TOKEN" > "$ROOT/secrets/metrics_token"
chmod 600 "$ROOT/secrets/metrics_token"
echo "Monitoring scrape credential written to secrets/metrics_token."
echo "Start optional monitoring with: docker compose --profile monitoring up -d"
