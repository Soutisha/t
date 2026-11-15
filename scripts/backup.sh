#!/usr/bin/env bash
set -euo pipefail
OUT_DIR="${1:-./backups}"
: "${AGE_RECIPIENT:?Set AGE_RECIPIENT to the age public recipient before creating backups.}"
command -v age >/dev/null || { echo "ERROR: age is required."; exit 2; }
mkdir -p "$OUT_DIR"
chmod 700 "$OUT_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
umask 077

docker compose exec -T postgres pg_dump -U pitstop -d pitstop -Fc > "$WORK/database.dump"
# Export the private MinIO bucket through a short-lived mc container.
docker compose run --rm --no-deps -T --entrypoint /bin/sh minio-init -c \
  'mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null && mkdir -p /tmp/objects && mc cp --recursive local/pitstop-private /tmp/objects/pitstop-private/ >/dev/null && tar -czf - -C /tmp/objects .' \
  > "$WORK/object-store.tar.gz"
tar -czf "$WORK/pitstop-backup.tar.gz" -C "$WORK" database.dump object-store.tar.gz
age -r "$AGE_RECIPIENT" -o "$OUT_DIR/pitstop-$STAMP.tar.gz.age" "$WORK/pitstop-backup.tar.gz"
(cd "$OUT_DIR" && sha256sum "pitstop-$STAMP.tar.gz.age" > "pitstop-$STAMP.tar.gz.age.sha256")
chmod 600 "$OUT_DIR/pitstop-$STAMP.tar.gz.age" "$OUT_DIR/pitstop-$STAMP.tar.gz.age.sha256"
echo "Encrypted backup created: $OUT_DIR/pitstop-$STAMP.tar.gz.age"
echo "Verify with scripts/backup-verify.sh and copy the encrypted file off-host."
