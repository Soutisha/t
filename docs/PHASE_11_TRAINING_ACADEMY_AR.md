# Phase 11 — Training Academy and AR-ready Learning

## Objective
Implement a mechanic learning lifecycle: administrator-authored courses, structured lessons, enrolment, lesson completion, graded quizzes, progress tracking and verifiable completion certificates. Support lesson asset types that can later host interactive 3D and AR learning experiences.

## Implemented capabilities

### Course authoring and publication
- Administrator creates courses with code, title, description, category, difficulty, language, duration and pass threshold.
- Course creation accepts ordered lessons and quiz questions in one validated request.
- Lessons support `article`, `video`, `document`, `interactive_3d` and `ar_demo` asset types.
- Courses start in `draft` and are visible to learners only after administrator publication.
- Publication requires at least one lesson and one quiz question.

### Learner experience APIs
- Authenticated users browse published courses and inspect course lessons.
- Learners enrol once per course; duplicate enrolment returns the existing record.
- Lesson completion is idempotent and scoped to the learner's own enrolment.
- Progress percentage is calculated from required lesson completion, not arbitrary client input.
- Quiz questions expose prompt and options but never expose the correct option or answer explanation before submission.
- Quiz submission must contain exactly one valid option index for every question.
- All required lessons must be completed before a quiz attempt.
- Pass/fail is calculated server-side against the course threshold.
- A certificate is issued only after a passing attempt. Failed attempts do not issue a certificate.
- Learners can view their certificates and a public verification endpoint can verify certificate codes.

## API endpoints

### Administrator
- `POST /api/v1/admin/academy/courses` — create draft course with lessons and quiz.
- `GET /api/v1/admin/academy/courses` — list courses.
- `PATCH /api/v1/admin/academy/courses/{course_id}/publish` — publish course.

### Learner
- `GET /api/v1/academy/courses` — browse published courses.
- `GET /api/v1/academy/courses/{course_id}` — course detail, lessons and answer-safe quiz questions.
- `POST /api/v1/academy/courses/{course_id}/enroll` — enrol.
- `GET /api/v1/academy/my-learning` — learner's enrolments and progress.
- `POST /api/v1/academy/enrollments/{enrollment_id}/lessons/{lesson_id}/complete` — mark a lesson complete.
- `POST /api/v1/academy/enrollments/{enrollment_id}/quiz/submit` — submit quiz answers.
- `GET /api/v1/academy/certificates/me` — list own certificates.
- `GET /api/v1/academy/certificates/verify/{certificate_code}` — verify a certificate.

## AR and interactive 3D readiness
Lesson records can reference interactive 3D or AR lesson assets using the `asset_type` and `asset_reference` fields. This is a content contract only. There is no Three.js scene, WebXR runtime, marker tracking, device camera experience, 3D tyre model or AR asset library implemented in this phase. A later client implementation must check device/browser WebXR support, provide a non-AR fallback, and use approved product geometry and safety content.

## Safety and integrity
- Correct answers remain server-side and are excluded from learner course responses.
- Course publication is administrator-only.
- Enrolments, lesson completion, quiz attempts and certificates are scoped to the authenticated user.
- Quiz answer indices and question sets are validated server-side.
- Course progress cannot be manually set by the client.
- Certificate codes are randomly generated and unique at the database level.
- Course certificates represent completion of this platform's configured learning assessment; they do not imply statutory, manufacturer or trade licensing unless separately accredited.

## Limitations
- No Eurogrip-authored course content, product videos, 3D models, or AR assets have been supplied. The database starts empty.
- The existing frontend Training Academy page still contains illustrative demo metrics/cards and is not connected to these APIs.
- No video hosting, SCORM/xAPI/LMS integration, instructor review, practical skills assessment, proctoring, certificate PDF generation or revocation workflow exists yet.
- AR lesson references are metadata only; there is no WebXR/Three.js experience.
- Certificate verification confirms the platform record exists; it does not prove identity of the presenter.
- Production use requires Alembic migrations, operational backups, content review and an audited certificate policy.

## Integration note\nThe API CORS policy also permits `DELETE` for the Phase 10 location-withdrawal endpoint.\n\n## Verification
- 60 backend Python files pass syntax compilation.
- Full backend test suite passes 28 tests.
- Tests cover course creation/publication, learner enrolment, lesson gating, quiz grading, certificate issue/verification, and no certificate on failed assessment.
- FastAPI route and database metadata registration are checked separately.
