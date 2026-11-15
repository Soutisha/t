# EUROGRIP PITSTOP OS — Controlled Pilot Protocol

## Purpose and scope
Use this protocol to run a limited, supervised validation of the deployed product. The pilot owner must define the geography, shops, participants, features enabled, dates and success criteria before inviting participants. Do not infer or expand the pilot scope from the software feature list.

## Required owners
| Role | Responsibility |
|---|---|
| Business pilot owner | Approves scope, participant communications, go/no-go and stop decisions |
| Technical owner | Deployment, secrets, monitoring, backups, restore and rollback |
| Support contact | Receives user-reported issues and coordinates triage |
| Privacy/data owner | Approves notice, consent, purpose, retention, deletion and access rules |
| Shop/field coordinator | Schedules participating shops and records operational feedback |

Record actual names and contact methods in the organization's controlled operations record, not in this template.

## Entry gates
All gates must be checked and signed before first participant onboarding:
- [ ] Pilot scope, dates, participant/shop list and feature set approved.
- [ ] Privacy notice and consent language approved for each data purpose.
- [ ] Data retention, deletion, access and incident-notification procedures approved.
- [ ] HTTPS, DNS, firewall, CORS and secret management verified.
- [ ] Twilio credentials checked and a dedicated test OTP journey completed.
- [ ] MinIO app identity tested; API has no MinIO root credentials.
- [ ] PostgreSQL, Redis and object storage readiness all pass.
- [ ] Encrypted backup copied off-host and isolated restore rehearsal completed.
- [ ] Alerts, request IDs, logs and support escalation tested.
- [ ] `pilot-acceptance.py` passes using separate mechanic/admin accounts.
- [ ] Manual end-to-end journeys signed off by technical and business owners.
- [ ] Rollback/stop procedure and decision-maker confirmed.

## Daily operating cycle
1. Technical owner checks gateway health, API readiness, error/latency indicators, storage and backup status.
2. Shop/field coordinator confirms participating locations are operating within the approved scope.
3. Support contact reviews new issues and records severity, timestamp and sanitized request ID.
4. Privacy/data owner reviews consent withdrawal, access requests or data-handling concerns under the approved procedure.
5. Pilot owner reviews unresolved high-severity issues and decides continue, restrict or pause.
6. Record aggregate activity and issue counts in `templates/daily-operations-log.csv`; avoid unnecessary personal data.

## Incident severity and response
- **Critical:** suspected account compromise, cross-role data exposure, evidence disclosure, material data loss or active abuse. Stop affected activity, preserve sanitized evidence, notify technical and business owners immediately, and follow the approved incident response plan.
- **High:** core authentication, storage or a key workflow unavailable for multiple participants. Pause the affected workflow and escalate.
- **Normal:** isolated usability defect or non-critical workflow issue. Record, prioritize and agree a workaround.

Do not promise notification timelines in this template; use the organization's approved incident response and legal obligations.

## Stop / rollback
The business pilot owner authorizes a stop. The technical owner:
1. Stops new onboarding and communicates the pause to the coordinator.
2. Captures sanitized logs, request IDs, deployment version and incident time.
3. Determines whether the issue is application, infrastructure, provider or data related.
4. Uses the approved deployment rollback or maintenance procedure. `scripts/staging-down.sh` stops the Compose stack; it is not itself a rollback plan or backup restore.
5. Restores data only from a verified backup and only after explicit approval. Restore must be rehearsed in an isolated environment first.
6. Verifies health/readiness, access boundaries and data integrity before reopening.
7. Records root cause, affected scope, corrective action and owner.

## Exit criteria
The pilot owner records whether the pilot:
- Met its predefined business and operational success criteria.
- Had no unresolved critical/high security or privacy incidents.
- Has a documented defect backlog with owners and target dates.
- Has reconciled pilot data according to the approved retention/deletion schedule.
- Has an approved decision to expand, repeat, redesign or end the pilot.

## Sign-off record
| Gate | Owner | Decision | Date | Evidence/reference |
|---|---|---|---|---|
| Business scope |  |  |  |  |
| Privacy and consent |  |  |  |  |
| Infrastructure and security |  |  |  |  |
| Product workflows |  |  |  |  |
| Backup and rollback |  |  |  |  |
| Final go/no-go |  |  |  |  |
