#!/usr/bin/env bash
set -euo pipefail
ENV_FILE="${1:-.env}"
if [[ ! -f "$ENV_FILE" ]]; then echo "ERROR: $ENV_FILE not found. Copy .env.example to .env and configure it."; exit 2; fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
fail=0
require_value() {
  local key="$1" value="${!1:-}"
  if [[ -z "$value" || "$value" == *CHANGE_ME* ]]; then echo "ERROR: $key is missing or still a placeholder."; fail=1; fi
}
for key in POSTGRES_PASSWORD REDIS_PASSWORD MINIO_ROOT_USER MINIO_ROOT_PASSWORD MINIO_APP_USER MINIO_APP_PASSWORD JWT_SECRET CLIENT_FINGERPRINT_SECRET CORS_ORIGINS SMS_PROVIDER TWILIO_ACCOUNT_SID TWILIO_AUTH_TOKEN TWILIO_FROM_NUMBER METRICS_TOKEN; do require_value "$key"; done
for key in POSTGRES_PASSWORD REDIS_PASSWORD MINIO_ROOT_PASSWORD MINIO_APP_PASSWORD JWT_SECRET CLIENT_FINGERPRINT_SECRET METRICS_TOKEN; do
  value="${!key:-}"
  if (( ${#value} < 24 )); then echo "ERROR: $key must be at least 24 characters."; fail=1; fi
  if [[ ! "$value" =~ ^[A-Za-z0-9_-]+$ ]]; then echo "ERROR: $key must use URL-safe characters A-Z, a-z, 0-9, underscore or hyphen."; fail=1; fi
done
if [[ "${#JWT_SECRET}" -lt 32 || "${#CLIENT_FINGERPRINT_SECRET}" -lt 32 || "${#METRICS_TOKEN}" -lt 32 || "${#MINIO_APP_PASSWORD}" -lt 32 ]]; then echo "ERROR: JWT_SECRET, CLIENT_FINGERPRINT_SECRET, METRICS_TOKEN and MINIO_APP_PASSWORD must each be at least 32 characters."; fail=1; fi
if [[ "${SMS_PROVIDER:-}" != "twilio" ]]; then echo "ERROR: SMS_PROVIDER must be twilio for production."; fail=1; fi
if [[ "${CORS_ORIGINS:-}" == *"*"* || "${CORS_ORIGINS:-}" != https://* || "${CORS_ORIGINS:-}" == *"example.com"* ]]; then echo "ERROR: CORS_ORIGINS must be your explicit HTTPS origin list; wildcard, HTTP and example domains are rejected."; fail=1; fi
if (( fail )); then echo "Preflight FAILED. No deployment should be started."; exit 1; fi
echo "Production environment preflight passed. Provider credentials still require a live send/receive verification."
