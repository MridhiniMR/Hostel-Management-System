# Deployment / Infrastructure / Environment Setup

## 1. Deployment Architecture

The Hostel Management System uses the following architecture:

- User browser: Accesses the application through its web interface.
- Application server: FastAPI application served using Uvicorn.
- Database: SQLite database accessed through SQLAlchemy.
- Protected application logging storage: Application security and audit events are managed by the application.

The database is not directly exposed to client browsers. Database access is handled by the application backend.

## 2. Team-Specific Environment

| Component | Implementation |
|---|---|
| Operating System | Windows (local development environment) |
| Language | Python |
| Local Python Version | Python 3.14 |
| CI Python Version | Python 3.12 |
| Framework | FastAPI |
| Application Server | Uvicorn |
| ORM | SQLAlchemy |
| Database | SQLite |
| Database Driver | SQLite (built into Python) |
| Browser | Browser used to access the local application |
| Hosting | Local development environment; production hosting not yet verified |

## 3. Installation

Clone the repository:

```powershell
git clone https://github.com/MridhiniMR/Hostel-Management-System.git
cd Hostel-Management-System
```

Create a virtual environment:

```powershell
py -m venv .venv
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Upgrade pip and install project dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Configuration

The application configuration is maintained in `hms/config.py`.

The following environment variables are supported:

| Variable | Default | Purpose |
|---|---|---|
| DATABASE_URL | sqlite:///./hostel.db | Database connection URL |
| HMS_SESSION_HOURS | 12 | Session duration in hours |
| HMS_SECURE_COOKIES | 0 | Enables secure session cookies |
| HMS_REQUIRE_HTTPS | 0 | Enables HTTP-to-HTTPS redirection |

For a PowerShell deployment environment with HTTPS configured, set:

```powershell
$env:HMS_REQUIRE_HTTPS="1"
$env:HMS_SECURE_COOKIES="1"
```

These settings must only be enabled when the application is actually served over HTTPS, either directly or through a correctly configured trusted TLS-terminating reverse proxy.

The application redirects HTTP requests to HTTPS when `HMS_REQUIRE_HTTPS` is enabled.

## 5. Database Setup

The project uses SQLite with SQLAlchemy.

The default database URL is:

```text
sqlite:///./hostel.db
```

Database engine and session management are implemented in:

```text
hms/database.py
```

Database tables are initialized automatically through:

```python
Base.metadata.create_all(bind=engine)
```

This initialization is present in `hms/main.py` and `hms/cli.py`. The application registers its SQLAlchemy models before creating the tables.

No separate database migration command is currently documented.

## 6. Create the Initial Administrator

Create an administrator account using the project CLI:

```powershell
python -m hms.cli create-user --username warden --role ADMIN
```

The CLI prompts for a password. Use a password containing at least 10 characters.

To create a student account after creating the corresponding student record:

```powershell
python -m hms.cli create-user --username student001 --role STUDENT --student-id S001
```

## 7. Run the Application

Start the application using Uvicorn:

```powershell
uvicorn hms.main:app --reload
```

The local application is available at:

```text
http://127.0.0.1:8000/
```

API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

Stop the development server using `CTRL+C`.

## 8. Testing and Verification

Run the complete automated test suite:

```powershell
python -m pytest -q
```

The local test execution recorded on 12 November 2026 produced:

- 60 tests passed.
- 0 test failures.
- 14 warnings.

The HTTPS-specific test can be executed using:

```powershell
python -m pytest -q -k "https"
```

The HTTPS test verifies HTTP-to-HTTPS redirection using status code 307 and checks that the redirect destination begins with `https://`.

### Verification Checklist

- [x] Automated test suite executed successfully (60 passed).
- [x] HTTPS redirection test passed.
- [x] HTTPS enforcement configuration identified.
- [x] Secure-cookie configuration identified.
- [ ] Application deployment on a production server verified.
- [ ] Actual TLS certificate and HTTPS connection verified in a deployed environment.
- [ ] Production database and protected logging infrastructure verified.

Other functional checks, including login, protected endpoint access, room allocation, occupancy display and security logging, should be supported by their respective test execution evidence.

## 9. HTTPS/TLS Deployment Limitation

The project implements configurable HTTPS enforcement through `HMS_REQUIRE_HTTPS`.

When enabled, HTTP requests are redirected to HTTPS with status code 307.

Session cookies can also be configured with the secure flag through `HMS_SECURE_COOKIES`.

The automated HTTPS test verifies redirection behavior. It does not verify:

- Installation or validity of a TLS certificate.
- A live HTTPS connection to a production server.
- Production reverse-proxy configuration.
- Production infrastructure security.

Therefore, production TLS verification remains pending until the application is deployed in an HTTPS-enabled environment.

## 10. Continuous Integration

The project includes a GitHub Actions workflow:

```text
.github/workflows/ci.yml
```

The workflow runs automated tests using Python 3.12 and installs dependencies from `requirements.txt`.

The test command used by CI is:

```powershell
python -m pytest -q
```

This supports automated testing during repository pushes and pull requests.
