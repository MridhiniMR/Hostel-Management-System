from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from hms.models import Allocation, Room, Student


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
