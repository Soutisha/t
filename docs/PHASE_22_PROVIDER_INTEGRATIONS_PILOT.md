# Phase 22 — Real Provider Integrations and Production Pilot Foundation

## Delivered

### Twilio SMS provider
- Extracted Twilio messaging into a dedicated `TwilioSmsProvider` with bounded connect/read timeouts and a typed delivery receipt.
- OTP issuance now calls the provider adapter rather than embedding HTTP logic in the authentication service.
- Provider failures return a generic API error; credentials, phone numbers and provider response bodies are not included in logs or API error details.
- Added `scripts/twilio-verify.sh` / `scripts/twilio-verify.py`. The default command verifies Twilio account credentials with a read-only account API request and sends no message.
- A chargeable test SMS requires all of `--send-test-sms`, `--to +E164_NUMBER` and `--confirm-send`.

### MinIO least-privilege identity
- Added a bucket-scoped policy limited to listing `pitstop-private` and reading, writing or deleting objects inside it.
- MinIO bootstrap creates the private bucket, dedicated `MINIO_APP_USER`, and policy attachment.
- The API receives only `MINIO_APP_USER` / `MINIO_APP_PASSWORD`; MinIO root credentials remain confined to the administrative bootstrap/backup utility.
- Production configuration validation and preflight require the dedicated S3 identity.
- S3 readiness is checked by `head_bucket` in `/health/ready`, so the API does not become ready until it can reach its configured private bucket.

### Pilot operations
- Added a provider validation checklist and environment templates for the separate MinIO application identity.
- Added contract tests for Twilio success/failure receipts and S3 credential scoping/readiness.
- Version bumped to `0.22.0`.

## Configure and validate on staging

### 1. MinIO application identity
1. Copy `.env.staging.example` to `.env.staging`.
2. Set a unique, URL-safe `MINIO_APP_PASSWORD` of at least 32 characters. Keep `MINIO_ROOT_PASSWORD` separate and stronger.
3. Keep `MINIO_APP_USER=pitstop-api` or choose another non-root service username.
4. Deploy with `ENV_FILE=.env.staging ./scripts/staging-deploy.sh`.
5. Confirm the `minio-init` container completed successfully and the API `/health/ready` response reports database, Redis and object storage as connected.
6. The API must not receive `MINIO_ROOT_USER` or `MINIO_ROOT_PASSWORD`.

For credential rotation, provision the new user secret in MinIO, update `MINIO_APP_PASSWORD`, redeploy the API, verify readiness and evidence retrieval, then disable the old identity. Do not rotate the root identity and app identity together.

### 2. Twilio credential verification
1. Set the real Twilio Account SID, Auth Token and sender in `.env.staging`.
2. Run `ENV_FILE=.env.staging ./scripts/twilio-verify.sh`. This checks credentials and account status only; it does not send an SMS.
3. If a chargeable test is explicitly approved, run `ENV_FILE=.env.staging ./scripts/twilio-verify.sh --send-test-sms --to +<E164_NUMBER> --confirm-send`.
4. Confirm receipt on the destination device and inspect the message status in Twilio Console.
5. Run the application OTP request/verify journey with a test account and confirm the OTP is delivered and accepted.

### 3. Pilot go/no-go checklist
- [ ] Public HTTPS and exact CORS origin verified.
- [ ] Twilio credential check passes and test SMS is received.
- [ ] OTP request and verification work with a pilot test account.
- [ ] API readiness reports database, Redis and S3 bucket connected.
- [ ] API credentials are the MinIO app identity, not root.
- [ ] TrustVision evidence upload, authorized retrieval and deletion tested.
- [ ] Admin access and role boundaries tested with non-admin accounts.
- [ ] Prometheus scrape succeeds from the private network and alert notifications are routed.
- [ ] Encrypted backup copied off-host and restore rehearsed in an isolated environment.
- [ ] Privacy notice, consent language, support contact and incident response owner approved.
- [ ] Pilot operator, participating shops, rollback owner and pilot end date documented.

## Important limitations
- This workspace cannot reach the user's Twilio account or MinIO deployment; no real credentials, SMS sends, or cloud storage requests were made.
- MinIO bootstrap, bucket-scoped permissions and app credential wiring are implemented but require live verification against the selected MinIO release.
- MinIO's root identity is still used by the one-shot bootstrap and administrative backup/restore utility; it is not passed to the API service.
- A live pilot, alert notification delivery, public TLS verification, backup restore drill, penetration test and production load test have not been performed.
- The included pilot checklist is an operator gate, not a certification or claim of production approval.
