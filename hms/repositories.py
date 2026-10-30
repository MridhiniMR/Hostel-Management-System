from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from hms.models import Allocation, AuditEvent, Room, Student, User

def find_student(db: Session, student_id: str) -> Student | None:
    return db.scalar(select(Student).where(Student.student_id == student_id))


def search_students(db: Session, query: str | None = None) -> list[Student]:
    stmt = select(Student).order_by(Student.student_id)
    if query:
        stmt = stmt.where(Student.student_id == query)
    return list(db.scalars(stmt))


def find_room(db: Session, room_id: str) -> Room | None:
    return db.scalar(select(Room).where(Room.room_id == room_id))


def find_allocation(db: Session, allocation_id: int) -> Allocation | None:
    stmt = select(Allocation).options(joinedload(Allocation.student), joinedload(Allocation.room)).where(Allocation.id == allocation_id)
    return db.scalar(stmt)


def active_allocation_for_student(db: Session, student_db_id: int) -> Allocation | None:
    stmt = select(Allocation).options(joinedload(Allocation.student), joinedload(Allocation.room)).where(
        Allocation.student_id == student_db_id,
        Allocation.status == "ACTIVE",
    )
    return db.scalar(stmt)


def occupancy_count(db: Session, room_db_id: int, excluding_allocation_id: int | None = None) -> int:
    stmt = select(func.count(Allocation.id)).where(
        Allocation.room_id == room_db_id,
        Allocation.status == "ACTIVE",
    )
    if excluding_allocation_id is not None:
        stmt = stmt.where(Allocation.id != excluding_allocation_id)
    return int(db.scalar(stmt) or 0)

def dashboard_counts(db: Session) -> dict:
    """Return summary counts used by the dashboard."""
    return {
        "students": int(db.scalar(select(func.count(Student.id))) or 0),
        "rooms": int(db.scalar(select(func.count(Room.id))) or 0),
        "active_allocations": int(
            db.scalar(
                select(func.count(Allocation.id)).where(
                    Allocation.status == "ACTIVE"
                )
            )
            or 0
        ),
    }
def find_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(
        select(User).where(User.username == username)
    )


def create_record(db: Session, record):
    db.add(record)
    return record


def save_record(db: Session, record):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(record)
    return record


def list_rooms_ordered(db: Session) -> list[Room]:
    """Return all rooms ordered by room identifier."""
    return list(db.scalars(select(Room).order_by(Room.room_id)))


def list_allocations_ordered(db: Session) -> list[Allocation]:
    """Return allocations with student and room details, newest first."""
    stmt = (
        select(Allocation)
        .options(joinedload(Allocation.student), joinedload(Allocation.room))
        .order_by(Allocation.id.desc())
    )
    return list(db.scalars(stmt))


def find_student_by_account_user_id(db: Session, user_id: int) -> Student | None:
    """Find the student linked to a user account."""
    return db.scalar(
        select(Student).where(Student.account_user_id == user_id)
    )


def recent_audit_events_ordered(db: Session, limit: int = 100) -> list[AuditEvent]:
    """Return the most recent audit events."""
    stmt = (
        select(AuditEvent)
        .order_by(AuditEvent.timestamp.desc(), AuditEvent.id.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))