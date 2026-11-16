# EUROGRIP PITSTOP OS — Local setup with real SMS OTP and Copilot

This local stack runs PostgreSQL, Redis, the FastAPI backend, and the React frontend. It uses persistent local object storage rather than MinIO. OTP delivery uses Twilio Programmable SMS and never returns a development code.

## Prerequisites

- Docker Desktop running with Linux containers.
- A Twilio account with an active project, an SMS-capable sender, and permission to send to the destination country.
- Twilio Account SID, Auth Token, and sender phone number in E.164 format.
- Optional: an OpenAI-compatible LLM API key for generated answers. Copilot still has a cited extractive fallback when no LLM is configured.

## Configure the untracked root .env

Copy `.env.example` to `.env`. Keep existing `POSTGRES_PASSWORD` and `REDIS_PASSWORD` unchanged when reusing existing database volumes. Set the Twilio values locally; never commit them or paste them into chat.

Required entries:

```dotenv
POSTGRES_PASSWORD=<existing database password>
REDIS_PASSWORD=<existing redis password>
JWT_SECRET=<at least 32 random characters>
CLIENT_FINGERPRINT_SECRET=<at least 32 random characters>
METRICS_TOKEN=<at least 32 random characters>
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=<Twilio auth token>
TWILIO_FROM_NUMBER=+1...
```

Optional Copilot generation settings:

```dotenv
RAG_EMBEDDING_PROVIDER=hashing
RAG_MIN_SIMILARITY=0.12
RAG_LLM_BASE_URL=https://api.openai.com/v1
RAG_LLM_API_KEY=<your API key>
RAG_LLM_MODEL=gpt-4o-mini
RAG_LLM_TIMEOUT_SECONDS=45
```

The LLM key is a paid-provider credential and may incur usage charges. Keep it only in the local `.env`. The default hashing embedding is deterministic lexical retrieval, not semantic transformer embeddings. Do not lower the similarity threshold just to force answers; validate it against approved source documents and known questions.

Generate application secrets in PowerShell (run separately for JWT_SECRET, CLIENT_FINGERPRINT_SECRET and METRICS_TOKEN):

```powershell
$bytes = New-Object byte[] 48
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$secret = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_')
$rng.Dispose()
$secret
```

Use alphanumeric-only database and Redis passwords because they are embedded in internal service URLs.

## Start the local stack

Run from the repository root:

```powershell
docker info
docker compose -p eurogrip-pitstop-local -f docker-compose.local.yml --env-file .env config --quiet
docker compose -p eurogrip-pitstop-local -f docker-compose.local.yml --env-file .env build --no-cache api web
docker compose -p eurogrip-pitstop-local -f docker-compose.local.yml --env-file .env up -d
docker compose -p eurogrip-pitstop-local -f docker-compose.local.yml --env-file .env ps
```

Use the same project name every time so Docker reuses the same persistent volumes. Do not run `down -v`, `volume prune`, or delete the PostgreSQL volume.

## Verify services

```powershell
Invoke-RestMethod http://localhost:8000/health/live
Invoke-RestMethod http://localhost:8000/health/ready
(Invoke-WebRequest http://localhost:3000/healthz -UseBasicParsing).StatusCode
Start-Process http://localhost:3000
Start-Process http://localhost:8000/docs
```

The web app is at http://localhost:3000 and API docs are at http://localhost:8000/docs.

If the API container is unhealthy, inspect the actual cause before restarting:

```powershell
docker compose -p eurogrip-pitstop-local -f docker-compose.local.yml --env-file .env logs --tail 200 postgres
docker compose -p eurogrip-pitstop-local -f docker-compose.local.yml --env-file .env logs --tail 250 api
docker compose -p eurogrip-pitstop-local -f docker-compose.local.yml --env-file .env logs --tail 100 redis
```

A PostgreSQL `password authentication failed` error commonly means the password in the current `.env` differs from the password stored when the persistent database volume was first initialized. Changing `POSTGRES_PASSWORD` in `.env` does not rotate the existing database user's password. Do not delete the volume to work around this; reconcile the database user's password with the local configuration using an authorised database session.

## Register the first account and grant local administrator access

1. Open http://localhost:3000 and choose **Register mechanic**.
2. Enter your phone number in E.164 format, e.g. `+91XXXXXXXXXX`.
3. Request the OTP and enter the code delivered by Twilio.
4. Complete the mechanic profile registration.
5. Run the guarded operator script from the repository root:

```powershell
docker compose -p eurogrip-pitstop-local -f docker-compose.local.yml --env-file .env exec api python scripts/bootstrap_admin.py --phone +91XXXXXXXXXX --confirm GRANT-ADMIN
```

Replace the example number with the same registered number. This script is intentionally limited to development/staging, requires explicit confirmation, and only promotes an existing active account. It does not bypass OTP or create an unauthenticated admin endpoint.

6. Sign out, request a fresh OTP, and sign in again. The newly issued JWT will include the administrator role.
7. Open the **AI Copilot** workspace. The administrator can upload a trusted PDF, DOCX, TXT or Markdown knowledge source. The document first appears as `pending_review`.
8. Select that document and approve it only after verifying the source. Pending/rejected documents are never used by Copilot.
9. Sign in as a normal mechanic account (or use a separate browser session) and ask a question answered explicitly by the approved source. Check that the answer includes a citation. Ask an unrelated question and verify that Copilot abstains.

Do not upload confidential, copyrighted, or unapproved product data without permission. Do not treat a Copilot response as a formal tyre-fitment or safety approval.

## Real OTP notes

Twilio credentials must be valid and the sender must be authorised to message the destination. Trial accounts generally restrict delivery to verified recipients. For Indian destinations, confirm the applicable sender, DLT/template, and account geo-permission requirements in Twilio. A successful API acceptance does not guarantee handset delivery.

## Logs and restart

```powershell
docker compose -p eurogrip-pitstop-local -f docker-compose.local.yml --env-file .env logs --tail 200 api
docker compose -p eurogrip-pitstop-local -f docker-compose.local.yml --env-file .env logs --tail 100 web
docker compose -p eurogrip-pitstop-local -f docker-compose.local.yml --env-file .env restart api web
```

PostgreSQL uses a persistent Docker volume. Capacity is limited by available host/Docker Desktop disk; there is no artificial database-size cap in this Compose file.
