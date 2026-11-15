# Phase 7 — TrustVision AI: Computer Vision and Fraud Prevention

## Delivered implementation

### 1. Evidence intake and secure local storage
- Authenticated multipart upload for JPEG, PNG and WebP evidence.
- Evidence kinds: invoice, fitment, product image and product QR.
- 10 MB default upload limit, content-type and actual image-format checks, image dimension limit, random server-side storage keys, restrictive local file permissions and path-safe administrator file retrieval.
- Evidence metadata, SHA-256 digest and perceptual image hash persisted in the database.
- Evidence can be linked to a mechanic-owned fitment or recommendation.

### 2. QR product identification
- OpenCV QR decoder reads QR images.
- Decoded product token is checked using the HMAC-signed product QR token issued in Phase 6.
- Valid scans are linked to the product; invalid or unreadable tokens create a review case.
- Repeated scans of the same token by the same account within a short window can generate an unusual-scan-pattern case. The threshold is a review signal, not proof of replay or counterfeiting.

### 3. Invoice OCR
- OCR adapter uses Tesseract through `pytesseract`.
- Extracts candidate invoice number, dealer/seller, date, product name, SKU, quantity and total amount using transparent text patterns.
- OCR confidence and raw extracted text are stored for authorised review.
- Missing invoice number, low OCR confidence and repeated invoice references contribute risk indicators.
- Manual correction endpoint lets an authorised reviewer correct extracted fields.
- If the Tesseract binary is unavailable, OCR reports `unavailable`; the upload is not represented as successfully processed.

### 4. Image reuse and quality checks
- Exact duplicate detection uses SHA-256.
- Possible image reuse detection uses an 8x8 perceptual hash and Hamming distance threshold.
- Basic image-quality heuristics flag small, low-contrast or potentially blurred images.
- These heuristics are screening signals only; they do not establish image manipulation or fraud.

### 5. Fraud intelligence and human review
- Explainable configurable rule scoring returns risk score, risk level and reason codes.
- Signals include exact duplicate image, possible image reuse, duplicate invoice reference, unusually frequent QR scans, missing invoice number, low OCR confidence and image quality warnings.
- Fraud review cases persist with evidence references and reviewer disposition.
- Review decisions are `cleared`, `confirmed_fraud` or `needs_information`.
- No mechanic, claim or reward is automatically rejected by the risk score.

## API endpoints
- `POST /api/v1/trustvision/evidence` — authenticated evidence upload.
- `GET /api/v1/trustvision/me/evidence` — submitter's evidence list.
- `GET /api/v1/admin/trustvision/review-queue` — pending cases for authorised administrators.
- `GET /api/v1/admin/trustvision/evidence/{evidence_id}` — evidence metadata, OCR and linked cases.
- `GET /api/v1/admin/trustvision/evidence/{evidence_id}/file` — protected evidence file retrieval.
- `PATCH /api/v1/admin/trustvision/cases/{case_id}/decision` — human review decision.
- `PATCH /api/v1/admin/trustvision/evidence/{evidence_id}/ocr-correction` — manual OCR correction.

## Configuration
- `TRUSTVISION_STORAGE_DIR` — local private evidence directory.
- `TRUSTVISION_MAX_UPLOAD_BYTES` — upload cap; default 10 MiB.
- `TRUSTVISION_OCR_ENABLED` — OCR feature toggle.
- Install the Tesseract OCR system binary separately; installing the Python wrapper alone is insufficient.
- Local storage is for development. Production must use private object storage, malware scanning, encryption, retention policies and signed access controls.

## Known limitations
- OCR patterns are generic and are not trained or calibrated on actual Eurogrip dealer invoice formats.
- No invoice authenticity verification against a dealer ERP, tax network or authorised invoice registry is connected.
- The current CV checks do not use a trained YOLO model or claim manipulation-detection accuracy.
- Image upload supports raster image files; PDF invoice ingestion is not implemented in this phase.
- QR replay detection is a heuristic based on scan frequency, not cryptographic one-time QR issuance. Product QR codes remain reusable labels.
- No labelled fraud dataset or model accuracy claims are provided.
- Frontend TrustVision dashboard integration remains pending; current UI fixtures are still demo data.
- Automated tests cover core hashing, parser, risk scoring, persistence and an authenticated multipart evidence-upload API flow. The full backend suite currently passes 15 tests. Full authenticated review-decision workflow tests, load testing and security scanning remain outstanding.
