#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then echo "Usage: $0 <backup.tar.gz.age>"; exit 2; fi
ARCHIVE="$1"
: "${AGE_IDENTITY_FILE:?Set AGE_IDENTITY_FILE to the age private identity file.}"
[[ -f "$ARCHIVE" && -f "$AGE_IDENTITY_FILE" ]] || { echo "ERROR: archive and age identity file must exist."; exit 2; }
command -v age >/dev/null || { echo "ERROR: age is required."; exit 2; }
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
if [[ -f "$ARCHIVE.sha256" ]]; then
  (cd "$(dirname "$ARCHIVE")" && sha256sum -c "$(basename "$ARCHIVE").sha256")
fi
age -d -i "$AGE_IDENTITY_FILE" -o "$WORK/backup.tar.gz" "$ARCHIVE"
tar -tzf "$WORK/backup.tar.gz" > "$WORK/contents.txt"
grep -qx 'database.dump' "$WORK/contents.txt"
grep -qx 'object-store.tar.gz' "$WORK/contents.txt"
tar -xzf "$WORK/backup.tar.gz" -C "$WORK"
tar -tzf "$WORK/object-store.tar.gz" >/dev/null
if command -v pg_restore >/dev/null; then
  pg_restore --list "$WORK/database.dump" >/dev/null
else
  echo "NOTE: pg_restore is not installed; database archive structure was checked, but PostgreSQL dump parsing was skipped."
fi
echo "Backup verification passed: age decryption, bundle members and object archive are readable."
