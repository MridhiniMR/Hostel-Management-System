from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from hms.database import get_db
from hms.errors import DomainError
from hms.models import User
from hms.security import user_for_token


def raw_request_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    # API requests require an explicit bearer token; browser pages use the HttpOnly cookie.
    user = user_for_token(db, raw_request_token(request))
    if user is None:
        raise DomainError(401, "AUTHENTICATION_REQUIRED", "Authentication is required to access this resource.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "ADMIN":
        raise DomainError(403, "ADMIN_REQUIRED", "This operation requires the administrator role.")
    return user
