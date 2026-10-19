# Implementation status — initial working baseline

## Implemented and exercised locally

- FastAPI JSON API and HTML browser interface.
- Relational models for User, Student, Room, Allocation, AuthSession, and AuditEvent.
- Password hashing with PBKDF2-HMAC-SHA256 and hashed opaque session tokens.
- Administrator/student roles and server-side student ownership checks.
- Student create/update/search (FR-02, FR-03).
- Room creation/update and calculated occupancy.
- Allocation create/move/deallocate with capacity checks and a database uniqueness constraint for one active allocation per student.
- Input validation, ORM-based data access, and standard validation/conflict responses (SEC-05).
- Audit events for successful/failed login and allocation create/modify/deallocate attempts (SEC-06).
- Persistent login throttling after five failures for a source/identifier pair within ten minutes.
- GitHub Actions runs the automated test suite on pushes and pull requests.
- Browser admin views for students, rooms, and allocations; student view for the linked user's own allocation (FR-09).

## Verification performed for this package

Command: `python -m pytest -q`

Result: **11 passed** in the package-building environment.

The CI workflow is included but has not yet run on the live GitHub repository. Team members must also install the declared dependencies and verify the app on their own machines.

## Still requires team execution/evidence

- Execute and record the submitted TP-01 to TP-14 test cases; the original PDF's `Not Executed` statuses remain unchanged.
- Measure NFR-01 under the specified 50-concurrent-user workload.
- Establish evidence for NFR-02 availability during scheduled service hours.
- Measure the NFR-04 allocation workflow with a trained administrator.
- Configure and verify HTTPS/TLS on the actual deployed environment (`HMS_REQUIRE_HTTPS=1` and `HMS_SECURE_COOKIES=1` when the deployment topology supports it).
- Confirm that every requirement and the final sprint scope match the team's approved sprint allocation and submitted documents.
- Record documented deviations or implementation choices for the final demo.

This is a tested initial baseline, not evidence that every non-functional test or deployment requirement has passed.
