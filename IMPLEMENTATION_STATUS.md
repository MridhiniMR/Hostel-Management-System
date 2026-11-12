# Implementation Status — Hostel Management System

## 1. Implemented Features

The following application features are implemented:

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
- GitHub Actions workflow for automated testing on pushes and pull requests.
- Browser admin views for students, rooms, and allocations; student view for the linked user's own allocation (FR-09).

## 2. Sprint 1 — Assigned Implementation Work

The following issues were assigned to Manasi Jadhav and are marked closed in the GitHub repository:

| Issue | Requirement | Status |
|---|---|---|
| #1 | FR-01 — Implement user authentication | Closed |
| #10 | SEC-01 — Enforce authentication for protected functions | Closed |
| #11 | SEC-02 — Role-based access control | Closed |
| #12 | SEC-03 — Secure password storage | Closed |
| #13 | SEC-04 — HTTPS/TLS enforcement | Closed |

### Implementation and Manual Verification

- Administrator account creation and login were tested locally.
- Access to the protected `/students` page without authentication redirected to the sign-in page.
- A student account was created and used to test role-based access restrictions.
- Student access to the protected `/api/v1/students` endpoint was denied.
- Password storage uses PBKDF2-HMAC-SHA256 with a unique 16-byte salt and 600,000 iterations.
- Password comparison uses `hmac.compare_digest`.
- HTTPS enforcement is configurable through `HMS_REQUIRE_HTTPS`.
- Secure session cookies are configurable through `HMS_SECURE_COOKIES`.

## 3. Automated Test Verification

### Complete Test Suite

Command:

```powershell
python -m pytest -q
```

Latest local execution: 12 November 2026.

Result:

- **60 tests passed**
- **0 test failures**
- **14 warnings**
- Execution time: 86.04 seconds

The warnings were deprecation warnings originating from installed dependencies.

### HTTPS-Specific Test

Command:

```powershell
python -m pytest -q -k "https"
```

Result:

- **1 passed**
- 59 deselected
- 14 warnings
- Execution time: 3.29 seconds

The test `test_https_enforcement_redirects_http_requests` in `tests/test_system.py` verifies that when HTTPS enforcement is enabled, an HTTP request receives a 307 redirect and the redirect location begins with `https://`.

## 4. Security Implementation Details

### Password Security

- PBKDF2-HMAC-SHA256 password hashing.
- Unique 16-byte salt.
- 600,000 hashing iterations.
- Constant-time password hash comparison using `hmac.compare_digest`.
- Password hashes are stored instead of plaintext passwords.

### Authentication and Authorization

- Session-based authentication.
- Hashed session tokens.
- Administrator and student roles.
- Authentication required for protected routes.
- Role and ownership checks enforced server-side.

### HTTPS Configuration

The application supports:

```text
HMS_REQUIRE_HTTPS=1
HMS_SECURE_COOKIES=1
```

The HTTPS middleware redirects HTTP requests to HTTPS when enforcement is enabled. Secure cookies can be enabled through the configuration variable.

**Deployment limitation:** The automated test verifies HTTP-to-HTTPS redirection only. A live TLS certificate, production HTTPS connection, and deployed reverse-proxy configuration have not yet been verified.

## 5. Remaining Verification and Documentation Work

The following items still require team execution or evidence:

- Execute and record the submitted TP-01 to TP-14 test cases and update their original execution statuses.
- Measure NFR-01 under the specified 50-concurrent-user workload and retain the test evidence.
- Maintain NFR-02 availability evidence for the specified service hours.
- Measure the NFR-04 allocation workflow with a trained administrator.
- Verify HTTPS/TLS using an actual deployed environment and valid certificate.
- Confirm that every requirement and final sprint scope match the approved sprint allocation and submitted documents.
- Record documented deviations or implementation choices for the final demo.
- Complete the required screenshots, demonstration evidence, and submission checklist.

## 6. Overall Status

The application has a working implementation baseline with 60 locally passing automated tests.

The five Sprint 1 issues assigned to Manasi Jadhav are marked closed in GitHub. Manual authentication and authorization checks, password-security implementation, and HTTPS redirection testing have also been performed.

However, passing automated tests and closing GitHub issues do not independently establish that every requirement has been fully accepted or that production deployment and TLS verification are complete.

This document records the implementation and verification evidence currently available. Remaining requirements must be completed and supported with their respective evidence before final submission.