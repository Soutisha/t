# Phase 20 — Staging Deployment and Integration Validation

## Delivered
- Added a staging Compose override with bounded service resources and configurable web port.
- Added `.env.staging.example` and deploy/down/status scripts.
- Wired TrustVision evidence upload and protected file retrieval through the configured object-storage abstraction. Local storage remains the development default; staging Compose selects private MinIO/S3.
- Added consistent logical object keys, path-style addressing for MinIO, server-side encryption request for S3-compatible storage, and delete support.
- Added local-storage and fake-S3 contract tests for round-trip, prefixing, traversal rejection and deletion.
- CI now builds backend and frontend container images.

## Deploy to a real staging host
1. Copy `.env.staging.example` to `.env.staging` and replace all placeholders with strong URL-safe secrets and real Twilio credentials.
2. Set `CORS_ORIGINS` to the exact HTTPS staging frontend origin. Configure DNS and TLS at a trusted reverse proxy/load balancer.
3. Ensure the host has Docker Engine, the Compose plugin, outbound access to image registries, and sufficient disk/backup capacity.
4. Run `./scripts/staging-deploy.sh`.
5. Inspect `./scripts/staging-status.sh`, then verify login OTP delivery, admin evidence review, evidence image retrieval, database migrations, logs, backup and restore.
6. Keep Postgres, Redis, MinIO API and MinIO console private. Do not publish them to the public internet.

To stop the stack without deleting persistent volumes, run `./scripts/staging-down.sh`. Do not use `docker compose down -v` on a staging environment unless data destruction is intended.

## Important operational notes
- MinIO uses the root credentials in this baseline compose stack. For a hardened staging/production deployment, create a dedicated least-privilege service account and pass its credentials to the API; retain root credentials only for bucket administration.
- S3 server-side encryption is requested as AES256. Confirm the selected object store supports it and enable encryption-at-rest on the underlying volume.
- The API image migration command runs at container startup. For multi-replica deployment, use a dedicated one-shot migration job before scaling API replicas.
- TLS termination is external. Configure secure headers, request limits, rate limits and access logs at ingress.
- The staging deploy script performs preflight, Compose config/build/up and HTTP smoke checks. It does not verify a real Twilio send, public TLS, penetration resistance, backup restoration or production load.

## Validation performed in this workspace
- Backend test suite and Python compilation: run as part of Phase 20 local verification.
- Shell syntax and YAML parsing: run locally.
- Docker image build and live staging deployment: not run unless Docker Engine and credentials are available in the execution environment.


## Phase 22 security update
The initial Phase 20 staging baseline used MinIO root credentials for the API. Phase 22 supersedes that arrangement: the API now receives a bucket-scoped `MINIO_APP_USER` / `MINIO_APP_PASSWORD` identity. Root credentials are confined to the MinIO bootstrap and administrative backup/restore utility. Use the Phase 22 setup and rotation instructions for current deployments.
