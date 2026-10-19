from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import timedelta

from sqlalchemy import func, select

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from hms.config import SESSION_HOURS
from hms.models import AuthSession, AuditEvent, Student, User, utcnow

PBKDF2_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, UnicodeError):
        return False


def token_digest(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def log_event(
    db: Session,
    *,
    event_type: str,
    outcome: str,
    actor: User | None = None,
    actor_identifier: str | None = None,
    source_key: str | None = None,
    details: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_id=actor.id if actor else None,
        actor_identifier=(actor_identifier or (actor.username if actor else None)),
        source_key=source_key,
        event_type=event_type,
        outcome=outcome,
        details=details or {},
    )
    db.add(event)
    return event


def find_user_by_identifier(db: Session, identifier: str) -> User | None:
    username_match = db.scalar(select(User).where(User.username == identifier))
    if username_match is not None:
        return username_match
    linked_student = db.scalar(select(Student).where(Student.student_id == identifier))
    if linked_student and linked_student.account_user_id:
        return db.get(User, linked_student.account_user_id)
    return None


def authenticate_and_issue_token(db: Session, identifier: str, password: str, source_key: str | None = None) -> tuple[str, User]:
    identifier = identifier.strip()
    # Small persistent throttle: five failures for the same source/identifier pair in ten minutes
    # trigger a temporary block. Store a fingerprint, not the client's raw IP address.
    if source_key:
        recent_failures = db.scalar(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.event_type == "AUTH_LOGIN",
                AuditEvent.outcome == "FAILURE",
                AuditEvent.source_key == source_key,
                AuditEvent.timestamp >= utcnow() - timedelta(minutes=10),
            )
        ) or 0
        if recent_failures >= 5:
            log_event(
                db, event_type="AUTH_LOGIN", outcome="FAILURE",
                actor_identifier=identifier[:64], source_key=source_key,
                details={"reason": "rate_limited"},
            )
            db.commit()
            raise ValueError("Invalid identifier or password")

    user = find_user_by_identifier(db, identifier)
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        log_event(
            db,
            event_type="AUTH_LOGIN",
            outcome="FAILURE",
            actor_identifier=identifier[:64],
            source_key=source_key,
            details={"reason": "invalid_credentials"},
        )
        db.commit()
        raise ValueError("Invalid identifier or password")

    raw_token = secrets.token_urlsafe(32)
    session = AuthSession(
        token_hash=token_digest(raw_token),
        user_id=user.id,
        expires_at=utcnow() + timedelta(hours=SESSION_HOURS),
    )
    db.add(session)
    log_event(db, event_type="AUTH_LOGIN", outcome="SUCCESS", actor=user, source_key=source_key, details={"method": "password"})
    db.commit()
    return raw_token, user


def user_for_token(db: Session, raw_token: str | None) -> User | None:
    if not raw_token:
        return None
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_digest(raw_token)))
    if session is None or session.expires_at <= utcnow() or not session.user.is_active:
        return None
    return session.user


def revoke_token(db: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_digest(raw_token)))
    if session is not None:
        db.delete(session)
        db.commit()


def login_source_key(remote_address: str | None, identifier: str) -> str:
    """Return a non-reversible source/identifier fingerprint for login throttling."""
    material = f"{remote_address or 'unknown'}\0{identifier.strip().lower()}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()
