# EUROGRIP PITSTOP OS — Local setup with real SMS OTP

This local stack runs PostgreSQL, Redis, the FastAPI backend, and the React frontend. It uses persistent local object storage instead of MinIO. OTP delivery uses the existing Twilio Programmable SMS integration and never returns a development code.

## Prerequisites

- Docker Desktop running with Linux containers.
- A Twilio account with an active project, an SMS-capable sender, and permission to send to the destination country. Trial accounts may only send to verified recipient numbers.
- Twilio Account SID, Auth Token, and sender phone number in E.164 format.

Real SMS delivery cannot work until valid Twilio credentials and sender configuration are supplied. Never paste credentials into chat or commit them to Git.

## Configure the untracked root .env

Keep existing POSTGRES_PASSWORD and REDIS_PASSWORD unchanged if their database volumes already contain data. Ensure the root .env has these entries:

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

Generate new application secrets in PowerShell (run three times; do not regenerate database passwords for existing data):

```powershell
$bytes = New-Object byte[] 48
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$secret = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_')
$rng.Dispose()
$secret
```

Assign the three outputs to JWT_SECRET, CLIENT_FINGERPRINT_SECRET, and METRICS_TOKEN. Use alphanumeric-only database and Redis passwords because they are embedded in internal service URLs.

## Start

Run from the repository root:

```powershell
docker compose -p eurogrip_all_integrations_local_ready -f docker-compose.local.yml --env-file .env config --quiet
docker compose -p eurogrip_all_integrations_local_ready -f docker-compose.local.yml --env-file .env build api web
docker compose -p eurogrip_all_integrations_local_ready -f docker-compose.local.yml --env-file .env up -d
docker compose -p eurogrip_all_integrations_local_ready -f docker-compose.local.yml --env-file .env ps
```

Keep the Compose project name fixed so Docker reuses the same persistent volumes.

## Verify

```powershell
Invoke-RestMethod http://localhost:8000/health/live
Invoke-RestMethod http://localhost:8000/health/ready
(Invoke-WebRequest http://localhost:3000/healthz -UseBasicParsing).StatusCode
Start-Process http://localhost:3000
```

API documentation: http://localhost:8000/docs

## Test a real OTP

1. Register or sign in from the web interface.
2. Enter a mobile number in E.164 format, for example `+9198XXXXXXXX`.
3. Request an OTP. The backend sends it through Twilio; the API response does not contain the code.
4. Enter the received SMS code before it expires.

Trial accounts require recipient verification in Twilio Console. Check Twilio Messaging logs if a message is rejected. Indian destinations may require sender registration, DLT/template compliance, and account geo-permissions. An accepted API request does not guarantee handset delivery.

## Logs and restart

```powershell
docker compose -p eurogrip_all_integrations_local_ready -f docker-compose.local.yml --env-file .env logs --tail 150 api
docker compose -p eurogrip_all_integrations_local_ready -f docker-compose.local.yml --env-file .env logs --tail 100 web
docker compose -p eurogrip_all_integrations_local_ready -f docker-compose.local.yml --env-file .env restart api web
```

## Database storage

PostgreSQL uses a persistent Docker volume and has no artificial database-size cap in this Compose file. Capacity is limited by available host/Docker Desktop disk. Do not run `docker compose down -v`, `docker volume prune`, or remove the PostgreSQL volume. This local file does not resize a remote Render database.
