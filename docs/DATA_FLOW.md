# Data Flow

## Mechanic onboarding
Client -> API -> Identity module -> User/profile transaction -> audit log + outbox event -> notification worker. OTP provider is a mock until configured.

## Advocacy and fitment
Mechanic submits recommendation -> API validates actor and product -> recommendation record persists -> evidence uploaded to private object storage -> evidence metadata persists -> reviewer verifies fitment -> advocacy event is recorded. Stocking remains a separate dealer-confirmed record.

## Tool request and reward
Mechanic requests a tool -> eligibility service calculates advisory eligibility -> request enters pending review -> authorised approver decides -> audit log and status update -> allocation is recorded only after verified inventory and fulfilment confirmation. Reward ledger uses append-only idempotent transactions.

## TrustVision
Evidence upload -> file validation -> OCR/vision worker -> structured extraction and confidence -> duplicate/risk checks -> fraud case if thresholds require review -> human reviewer decision. Model output does not automatically reject the user.

## RAG Copilot
Approved document ingestion -> OCR if needed -> chunking with page/source metadata -> embeddings -> pgvector -> query retrieval -> answer generated only from retrieved approved content -> citations returned. If evidence is insufficient, answer says so.

## Agent workflows
Business event or authorised user request -> LangGraph workflow -> scoped read tools -> structured recommendation -> approval task if a protected action is proposed -> human decision -> permitted application service executes -> audit/outbox.

## Analytics
Operational tables and verified events -> aggregate queries/materialised views -> dashboard. Synthetic demo records are tagged and excluded from production reporting. Estimates and measured outcomes are shown separately.
