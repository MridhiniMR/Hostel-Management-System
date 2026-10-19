from __future__ import annotations

import os

APP_NAME = "Hostel Management System"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hostel.db")
SESSION_COOKIE_NAME = "hms_session"
SESSION_HOURS = int(os.getenv("HMS_SESSION_HOURS", "12"))
# Set HMS_SECURE_COOKIES=1 behind HTTPS in deployed environments.
SECURE_COOKIES = os.getenv("HMS_SECURE_COOKIES", "0").lower() in {"1", "true", "yes"}
REQUIRE_HTTPS = os.getenv("HMS_REQUIRE_HTTPS", "0").lower() in {"1", "true", "yes"}
