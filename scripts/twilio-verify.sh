#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"
[[ -f "$ENV_FILE" ]] || { echo "ERROR: $ENV_FILE not found."; exit 2; }
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
python3 "$ROOT/scripts/twilio-verify.py" "$@"
