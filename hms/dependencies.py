
from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from hms.database import get_db
from hms.errors import DomainError
from hms.models import User
from hms.security import log_event, login_source_key, user_for_token


def raw_request_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = user_for_token(db, raw_request_token(request))
    if user is None:
        log_event(
            db,
            event_type="AUTH_ACCESS_DENIED",
            outcome="FAILURE",
            source_key=login_source_key(
                request.client.host if request.client else None,
                "unauthenticated",
            ),
            details={
                "path": request.url.path,
                "method": request.method,
                "reason": "authentication_required",
            },
        )
        db.commit()
        raise DomainError(
            401,
            "AUTHENTICATION_REQUIRED",
            "Authentication is required to access this resource.",
        )
    return user


def require_admin(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> User:
    if user.role != "ADMIN":
        log_event(
            db,
            event_type="AUTHORIZATION_DENIED",
            outcome="FAILURE",
            actor=user,
            details={
                "path": request.url.path,
                "method": request.method,
                "reason": "admin_role_required",
            },
        )
        db.commit()
        raise DomainError(
            403,
            "ADMIN_REQUIRED",
            "This operation requires the administrator role.",
        )
    return user
