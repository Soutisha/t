# Database Design — Initial Logical Model

PostgreSQL is the system of record. Use UUID primary keys, UTC timestamps, foreign keys, check constraints and explicit status enums. Enable PostGIS for consented shop/territory geometry. Store large files outside the relational database and retain immutable metadata and checksums.

## Core tables

### Identity
- `users(id, phone_e164, email, status, created_at, updated_at)`
- `roles(id, code, name)`
- `user_roles(user_id, role_id, scope_type, scope_id)`
- `consents(id, user_id, purpose, policy_version, granted_at, revoked_at)`
- `audit_logs(id, actor_user_id, action, resource_type, resource_id, before_json, after_json, created_at)`

### Mechanic and shop
- `mechanics(id, user_id, mechanic_code, display_name, experience_years, languages, verification_status)`
- `shops(id, owner_user_id, name, shop_type, address_text, location geography(Point,4326), location_consent_id)`
- `mechanic_shop_memberships(id, mechanic_id, shop_id, membership_role, valid_from, valid_to)`

### Catalogue and fitment
- `products(id, sku, name, category, specifications_json, source_document_id, active)`
- `vehicle_types(id, make, model, variant, year_from, year_to)`
- `fitment_records(id, product_id, vehicle_type_id, source_document_id, verification_status, verified_by, verified_at)`

### Advocacy
- `recommendations(id, mechanic_id, product_id, customer_reference_hash, source, submitted_at, status)`
- `fitment_submissions(id, recommendation_id, shop_id, evidence_id, status, reviewed_by, reviewed_at)`
- `stocking_records(id, dealer_id, product_id, quantity, source_reference, verification_status, recorded_at)`
- `advocacy_events(id, mechanic_id, event_type, source_record_type, source_record_id, occurred_at, verification_status)`

### Evidence and fraud review
- `evidence_files(id, uploader_user_id, object_key, sha256, mime_type, size_bytes, created_at)`
- `ocr_extractions(id, evidence_file_id, engine, engine_version, result_json, confidence_json, created_at)`
- `fraud_cases(id, subject_type, subject_id, risk_score, reason_codes, status, assigned_to, created_at, resolved_at)`
- `fraud_case_evidence(id, fraud_case_id, evidence_file_id, note)`

### Tools and rewards
- `tools(id, sku, name, category, specifications_json, active)`
- `tool_inventory(id, tool_id, location_id, quantity_available, source, last_verified_at)`
- `tool_requests(id, mechanic_id, tool_id, quantity, justification, status, requested_at, decided_by, decided_at)`
- `reward_accounts(id, mechanic_id, balance_version)`
- `reward_transactions(id, mechanic_id, transaction_type, points, source_type, source_id, idempotency_key, status, created_at)`
- `tool_allocations(id, tool_request_id, asset_reference, status, allocated_at, returned_at)`

### Training
- `courses(id, title, language, version, published)`
- `course_modules(id, course_id, title, content_reference, sequence_no)`
- `assessments(id, course_id, pass_mark, version)`
- `assessment_attempts(id, assessment_id, mechanic_id, score, passed, attempted_at)`
- `certificates(id, mechanic_id, course_id, certificate_number, issued_at, revoked_at)`

### Platform operations
- `documents(id, title, document_type, version, approval_status, object_key, checksum)`
- `document_chunks(id, document_id, chunk_index, content, embedding, page_reference)`
- `notifications(id, user_id, channel, template_key, payload_json, status, sent_at)`
- `domain_outbox(id, aggregate_type, aggregate_id, event_type, payload_json, occurred_at, processed_at)`
- `idempotency_records(id, actor_user_id, key, request_hash, response_json, expires_at)`

## Integrity rules
- Unique constraints on user phone, mechanic code, product SKU, certificate number and idempotency scope.
- Reward transactions are append-only; corrections use compensating entries.
- A recommendation, fitment and stocking record are separate entities and must not be conflated.
- Evidence files are immutable after submission; replacement creates a new evidence record.
- High-value tool approvals require authorised approver identity and audit trail.
- Location is collected only with purpose-specific consent and access is scoped.

This is a logical baseline. Alembic migrations and final field types/indexes are created alongside implementation, not assumed to exist yet.
