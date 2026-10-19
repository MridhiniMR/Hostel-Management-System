# Hostel Management System

A small web-based Hostel Management System implementation based on the project's submitted SRS, Architecture and Design document, and Test Plan. The documents require a layered three-tier architecture, a JSON API, a relational database, authenticated role-based access, input validation, transactional allocation handling, and security-event logging. The framework is not mandated in those documents.

## Current implementation

This first implementation uses **FastAPI + SQLAlchemy + SQLite**. FastAPI is the API/presentation boundary, `hms/services.py` holds business rules, `hms/repositories.py` holds data-access queries, and `hms/models.py` defines relational entities. The choice is an implementation decision, not something prescribed by the submitted documents; the team should use this same stack for all branches unless the team agrees otherwise before merging.

The app currently includes:

- Passwords hashed using PBKDF2-HMAC-SHA256; passwords are never stored in plaintext.
- Login by registered username or linked student identifier; opaque tokens are stored as hashes.
- Administrator and student roles.
- Student create, update, and exact-identifier search.
- Room create/update, occupancy and remaining-capacity display.
- Allocation create, move, and deallocation with capacity and duplicate-active-allocation checks.
- Student self-service allocation lookup with server-side ownership checks.
- Security audit events for successful/failed login and allocation changes/attempts; login attempts are throttled after five failures per source/identifier pair within ten minutes.
- Browser pages and JSON API endpoints.
- Automated tests and GitHub Actions CI.

This is a development baseline, not a claim that all SRS and NFR acceptance targets have been verified. HTTPS must be configured for deployed environments; the performance and availability targets need separate evidence. The test cases in the submitted PDF should be updated from “Not Executed” only after the team runs and records those tests.

## Run locally

Requirements: Python 3.11+ and pip.

### 1. Create a virtual environment

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Create the first administrator account

```bash
python -m hms.cli create-user --username warden --role ADMIN
```

Enter a password of at least 10 characters when prompted. Do not commit credentials or share them in Issues/PRs.

### 3. Start the application

```bash
uvicorn hms.main:app --reload
```

Open `http://127.0.0.1:8000/` for the browser interface or `http://127.0.0.1:8000/docs` for interactive JSON API documentation. The first run creates the local `hostel.db` file. For a directly HTTPS-served deployment, set both `HMS_REQUIRE_HTTPS=1` and `HMS_SECURE_COOKIES=1`. If TLS terminates at a reverse proxy, configure Uvicorn to trust only that proxy’s forwarded scheme so the HTTPS check does not redirect-loop; never trust arbitrary forwarded headers from the public internet.

### 4. Create/link a student login for FR-09

First create the student record in the administrator interface. Then create the matching student login and link it to the existing record:

```bash
python -m hms.cli create-user --username student001 --role STUDENT --student-id S001
```

Change `S001` to the actual student identifier. The account will only be linked if that student record exists and has no other linked account.

### 5. Run tests

```bash
python -m pytest -q
```

GitHub Actions runs the same test suite on pushes and pull requests targeting `main`. Failed checks should be fixed before requesting merge.

## Principal API endpoints

| Method | Endpoint | Purpose / access |
|---|---|---|
| `POST` | `/api/v1/auth/login` | Login; returns an opaque bearer token and sets an HttpOnly cookie |
| `POST` | `/api/v1/auth/logout` | Revoke the current token |
| `GET` | `/api/v1/students` | List/search students; administrator only |
| `POST` | `/api/v1/students` | Create student; administrator only |
| `GET` | `/api/v1/students/{student_id}` | Administrator can read any; a student can read only their linked record |
| `PUT` | `/api/v1/students/{student_id}` | Update student; administrator only |
| `GET` | `/api/v1/rooms` | View occupancy; authenticated users |
| `POST`, `PUT` | `/api/v1/rooms`, `/api/v1/rooms/{room_id}` | Create/update room; administrator only |
| `GET`, `POST` | `/api/v1/allocations` | List/create allocations; administrator only |
| `PUT`, `DELETE` | `/api/v1/allocations/{allocation_id}` | Move/deallocate; administrator only |
| `GET` | `/api/v1/me/allocation` | Student's own active allocation |
| `GET` | `/api/v1/audit-events` | Audit log; administrator only |

Errors use JSON containing `error_code`, `message`, and `details`. Validation failures return 422, missing authentication 401, authorization failures 403, missing records 404, and capacity/duplicate conflicts 409.

## Team Git workflow

1. Pull the shared `main` branch.
2. Create a feature branch for the assigned Issue (example: `feature/fr02-student-records`).
3. Implement the assigned change and tests; do not commit directly to `main`.
4. Run `python -m pytest -q` locally.
5. Open a pull request and include `Closes #2` (replace with the actual issue number).
6. A repository owner reviews the diff and waits for the `Python CI` check to pass before merging.

## Project documents

- SRS: `1-SRS-and-Work-Breakdown/SRS.pdf`
- Work breakdown: `1-SRS-and-Work-Breakdown/WORK_BREAKDOWN.md`
- Test Plan: `2-Test-Planning/Test_Plan.pdf`
- Test cases / RTM: `3-Requirements-Engineering/Test_Cases_and_RTM.pdf`
- Architecture and Design: `4-Architecture-and-Design/Architecture_and_Design.pdf`

Do not mark documented test cases as passed until they have actually been run and recorded. If implementation choices differ from submitted documentation, record the deviations for the final demo as instructed.
