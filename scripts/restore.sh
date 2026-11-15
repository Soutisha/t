#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then echo "Usage: AGE_IDENTITY_FILE=/path/to/identity.txt $0 <backup.tar.gz.age>"; exit 2; fi
ARCHIVE="$1"
: "${AGE_IDENTITY_FILE:?Set AGE_IDENTITY_FILE to the age private identity file.}"
[[ -f "$ARCHIVE" && -f "$AGE_IDENTITY_FILE" ]] || { echo "ERROR: backup archive and age identity file must exist."; exit 2; }
command -v age >/dev/null || { echo "ERROR: age is required."; exit 2; }
if [[ -f "$ARCHIVE.sha256" ]]; then
  (cd "$(dirname "$ARCHIVE")" && sha256sum -c "$(basename "$ARCHIVE").sha256")
fi
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
chmod 700 "$WORK"
age -d -i "$AGE_IDENTITY_FILE" -o "$WORK/backup.tar.gz" "$ARCHIVE"
tar -xzf "$WORK/backup.tar.gz" -C "$WORK"
[[ -s "$WORK/database.dump" && -s "$WORK/object-store.tar.gz" ]] || { echo "ERROR: backup bundle is incomplete."; exit 2; }
echo "WARNING: this overwrites the Pitstop database and private evidence bucket."
read -r -p "Type RESTORE to continue: " answer
[[ "$answer" == "RESTORE" ]] || { echo "Restore cancelled."; exit 1; }
docker compose stop api web
docker compose exec -T postgres pg_restore --clean --if-exists --no-owner -U pitstop -d pitstop < "$WORK/database.dump"
docker compose run --rm --no-deps -T --entrypoint /bin/sh minio-init -c \
  'set -e; mkdir -p /tmp/restore; tar -xzf - -C /tmp/restore; mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null; mc rm --recursive --force local/pitstop-private/ >/dev/null 2>&1 || true; mc cp --recursive /tmp/restore/pitstop-private/ local/pitstop-private/' \
  < "$WORK/object-store.tar.gz"
docker compose start api web
echo "Restore commands completed. Verify /health/ready, evidence retrieval and a functional smoke test before reopening traffic."
