#!/bin/sh
set -eu
: "${MINIO_ROOT_USER:?MINIO_ROOT_USER is required}"
: "${MINIO_ROOT_PASSWORD:?MINIO_ROOT_PASSWORD is required}"
: "${MINIO_APP_USER:?MINIO_APP_USER is required}"
: "${MINIO_APP_PASSWORD:?MINIO_APP_PASSWORD is required}"
until mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1; do
  sleep 2
done
mc mb --ignore-existing local/pitstop-private
if ! mc admin policy info local pitstop-evidence-rw >/dev/null 2>&1; then
  mc admin policy create local pitstop-evidence-rw /policies/pitstop-evidence-rw.json
fi
if ! mc admin user info local "$MINIO_APP_USER" >/dev/null 2>&1; then
  mc admin user add local "$MINIO_APP_USER" "$MINIO_APP_PASSWORD"
fi
mc admin policy attach local pitstop-evidence-rw --user "$MINIO_APP_USER"
echo "Private bucket and least-privilege application identity are ready."
