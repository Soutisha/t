#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env.staging}"

usage() {
  cat <<'USAGE'
Usage:
  scripts/staging-deploy.sh --deploy

Deployment is a state-changing operation. The explicit --deploy flag is required.
Set ENV_FILE to use a non-default staging environment file.
USAGE
}
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then usage; exit 0; fi
if [[ "${1:-}" != "--deploy" || "$#" -ne 1 ]]; then
  usage >&2
  echo "ERROR: deployment not started; pass --deploy explicitly." >&2
  exit 2
fi

COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT/docker-compose.yml" -f "$ROOT/docker-compose.staging.yml")
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found. Copy .env.staging.example and configure it."
  exit 2
fi
if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker Engine is unavailable or the current user cannot access it."
  exit 2
fi

"$ROOT/scripts/production-preflight.sh" "$ENV_FILE"
"${COMPOSE[@]}" config --quiet
echo "Building staging images..."
"${COMPOSE[@]}" build
echo "Starting staging services..."
"${COMPOSE[@]}" up -d --remove-orphans

WEB_PORT="$(grep -E '^STAGING_WEB_PORT=' "$ENV_FILE" | tail -n1 | cut -d= -f2- | tr -d '\r' || true)"
WEB_PORT="${WEB_PORT:-8080}"
WEB_URL="http://127.0.0.1:${WEB_PORT}"
echo "Waiting for gateway and dependency readiness (up to 300 seconds)..."
for attempt in $(seq 1 60); do
  if curl -fsS "$WEB_URL/healthz" >/dev/null 2>&1 && \
     curl -fsS "$WEB_URL/health/live" >/dev/null 2>&1; then
    if "$ROOT/scripts/staging-verify.py" --web "$WEB_URL" --allow-http; then
      "${COMPOSE[@]}" ps
      echo "STAGING DEPLOYMENT GATE PASSED."
      echo "This verifies gateway/API health, security headers and DB/Redis/object-storage readiness."
      echo "It does not prove real SMS delivery, external HTTPS, backup restoration, load/security testing or pilot acceptance."
      exit 0
    fi
  fi
  sleep 5
done
"${COMPOSE[@]}" ps
echo "ERROR: staging did not pass health/readiness checks within 300 seconds."
exit 1
