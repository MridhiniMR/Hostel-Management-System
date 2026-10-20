from __future__ import annotations

import re
from datetime import timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from hms.errors import DomainError
from hms.models import Allocation, AuditEvent, Room, Student, User, utcnow
from hms.repositories import (
    active_allocation_for_student,
    find_allocation,
    find_room,
    find_student,
    occupancy_count,
    search_students,
)
from hms.security import hash_password, log_event
from hms.schemas import validate_identifier


def create_user(db: Session, username: str, password: str, role: str = "STUDENT") -> User:
    username = username.strip()
    if not username or len(username) > 64:
        raise ValueError("Username must contain 1–64 characters.")
    if not re.fullmatch(r"[A-Za-z0-9_.@+-]+", username):
        raise ValueError("Username contains unsupported characters.")
    if len(password) < 10:
        raise ValueError("Password must contain at least 10 characters.")
    role = role.upper()
    if role not in {"ADMIN", "STUDENT"}:
        raise ValueError("Role must be ADMIN or STUDENT.")
    if db.scalar(select(User).where(User.username == username)):
        raise ValueError("Username already exists.")
    user = User(username=username, password_hash=hash_password(password), role=role, is_active=True)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Username already exists.")
    db.refresh(user)
    return user


def create_student(db: Session, data: dict, actor: User) -> Student:
    data = dict(data)
    student_id = validate_identifier(str(data.get("student_id", "")))
    name = str(data.get("name", "")).strip()
    if not name:
        raise DomainError(422, "VALIDATION_ERROR", "Student name is required.", {"name": "Required"})
    if find_student(db, student_id):
        raise DomainError(409, "STUDENT_ALREADY_EXISTS", "A student with this identifier already exists.")

    account_username = data.pop("account_username", None)
    account_user_id = None
    if account_username:
        linked_user = db.scalar(select(User).where(User.username == account_username))
        if linked_user is None or linked_user.role != "STUDENT":
            raise DomainError(422, "INVALID_STUDENT_ACCOUNT", "The linked account must exist and have the STUDENT role.")
        if linked_user.student_profile is not None:
            raise DomainError(409, "ACCOUNT_ALREADY_LINKED", "This student account is already linked to a student record.")
        account_user_id = linked_user.id

    student = Student(
        student_id=student_id,
        name=name,
        email=data.get("email") or None,
        phone=data.get("phone") or None,
        department=data.get("department") or None,
        year_of_study=data.get("year_of_study"),
        account_user_id=account_user_id,
    )
    db.add(student)
    log_event(db, event_type="STUDENT_CREATED", outcome="SUCCESS", actor=actor, details={"student_id": student_id})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DomainError(409, "STUDENT_ALREADY_EXISTS", "A conflicting student record or account link already exists.")
    db.refresh(student)
    return student


def update_student(db: Session, student_id: str, changes: dict, actor: User) -> Student:
    student = find_student(db, student_id)
    if student is None:
        raise DomainError(404, "STUDENT_NOT_FOUND", "Student was not found.")
    allowed = {"name", "email", "phone", "department", "year_of_study"}
    changes = {key: value for key, value in changes.items() if key in allowed}
    if not changes:
        raise DomainError(422, "VALIDATION_ERROR", "Provide at least one editable student field.")
    if "name" in changes and (changes["name"] is None or not str(changes["name"]).strip()):
        raise DomainError(422, "VALIDATION_ERROR", "Student name cannot be blank.", {"name": "Required"})
    for key, value in changes.items():
        setattr(student, key, value.strip() if isinstance(value, str) else value)
    student.updated_at = utcnow()
    log_event(db, event_type="STUDENT_UPDATED", outcome="SUCCESS", actor=actor, details={"student_id": student_id, "fields": sorted(changes)})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DomainError(409, "STUDENT_UPDATE_CONFLICT", "Student update conflicts with an existing record.")
    db.refresh(student)
    return student


def create_room(db: Session, room_id: str, capacity: int, actor: User) -> Room:
    room_id = validate_identifier(room_id)
    if capacity < 1 or capacity > 1000:
        raise DomainError(422, "VALIDATION_ERROR", "Room capacity must be between 1 and 1000.", {"capacity": "Out of range"})
    if find_room(db, room_id):
        raise DomainError(409, "ROOM_ALREADY_EXISTS", "A room with this identifier already exists.")
    room = Room(room_id=room_id, capacity=capacity)
    db.add(room)
    log_event(db, event_type="ROOM_CREATED", outcome="SUCCESS", actor=actor, details={"room_id": room_id})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DomainError(409, "ROOM_ALREADY_EXISTS", "A room with this identifier already exists.")
    db.refresh(room)
    return room


def update_room(db: Session, room_id: str, capacity: int, actor: User) -> Room:
    room = find_room(db, room_id)
    if room is None:
        raise DomainError(404, "ROOM_NOT_FOUND", "Room was not found.")
    if capacity < 1 or capacity > 1000:
        raise DomainError(422, "VALIDATION_ERROR", "Room capacity must be between 1 and 1000.")
    occupied = occupancy_count(db, room.id)
    if capacity < occupied:
        raise DomainError(409, "CAPACITY_BELOW_OCCUPANCY", "Capacity cannot be lower than the number of active occupants.", {"occupied": occupied})
    room.capacity = capacity
    room.updated_at = utcnow()
    log_event(db, event_type="ROOM_UPDATED", outcome="SUCCESS", actor=actor, details={"room_id": room_id, "capacity": capacity})
    db.commit()
    db.refresh(room)
    return room


def room_representation(db: Session, room: Room) -> dict:
    occupied = occupancy_count(db, room.id)
    return {"room_id": room.room_id, "capacity": room.capacity, "occupied": occupied, "available": max(0, room.capacity - occupied)}


def get_room(db: Session, room_id: str) -> Room:
    room = find_room(db, room_id)
    if room is None:
        raise DomainError(404, "ROOM_NOT_FOUND", "Room was not found.")
    return room


def list_rooms(db: Session, available_only: bool = False) -> list[Room]:
    """Return rooms ordered by identifier; optionally only rooms with a free bed (FR-05)."""
    rooms = list(db.scalars(select(Room).order_by(Room.room_id)))
    if available_only:
        rooms = [room for room in rooms if occupancy_count(db, room.id) < room.capacity]
    return rooms
def list_students(db: Session, query: str | None = None) -> list[Student]:
    return search_students(db, query)


def _write_allocation_failure(db: Session, actor: User, event_type: str, details: dict) -> None:
    db.rollback()
    log_event(db, event_type=event_type, outcome="FAILURE", actor=actor, details=details)
    db.commit()


def create_allocation(db: Session, student_id: str, room_id: str, actor: User) -> Allocation:
    event_type = "ALLOCATION_CREATED"
    try:
        student_id = validate_identifier(student_id)
        room_id = validate_identifier(room_id)
        # Locking protects the capacity check on databases that support row-level locks.
        student = db.scalar(select(Student).where(Student.student_id == student_id).with_for_update())
        if student is None:
            raise DomainError(404, "STUDENT_NOT_FOUND", "Student was not found.")
        room = db.scalar(select(Room).where(Room.room_id == room_id).with_for_update())
        if room is None:
            raise DomainError(404, "ROOM_NOT_FOUND", "Room was not found.")
        if active_allocation_for_student(db, student.id):
            raise DomainError(409, "STUDENT_ALREADY_ALLOCATED", "This student already has an active room allocation.")
        occupied = occupancy_count(db, room.id)
        if occupied >= room.capacity:
            raise DomainError(409, "ROOM_FULL", "The selected room has no available capacity.", {"occupied": occupied, "capacity": room.capacity})
        allocation = Allocation(student_id=student.id, room_id=room.id, status="ACTIVE")
        db.add(allocation)
        db.flush()
        log_event(db, event_type=event_type, outcome="SUCCESS", actor=actor, details={"student_id": student_id, "room_id": room_id})
        db.commit()
        db.refresh(allocation)
        return allocation
    except DomainError as exc:
        _write_allocation_failure(db, actor, event_type, {"requested_student_id": str(student_id)[:32], "requested_room_id": str(room_id)[:32], "error_code": exc.code})
        raise
    except IntegrityError:
        _write_allocation_failure(db, actor, event_type, {"requested_student_id": str(student_id)[:32], "requested_room_id": str(room_id)[:32], "error_code": "INTEGRITY_CONFLICT"})
        raise DomainError(409, "ALLOCATION_CONFLICT", "The allocation conflicts with an existing allocation or database constraint.")


def update_allocation(db: Session, allocation_id: int, target_room_id: str, actor: User) -> Allocation:
    try:
        allocation = find_allocation(db, allocation_id)
        if allocation is None:
            raise DomainError(404, "ALLOCATION_NOT_FOUND", "Allocation was not found.")
        if allocation.status != "ACTIVE":
            raise DomainError(409, "ALLOCATION_NOT_ACTIVE", "Only active allocations can be modified.")
        room = db.scalar(select(Room).where(Room.room_id == validate_identifier(target_room_id)).with_for_update())
        if room is None:
            raise DomainError(404, "ROOM_NOT_FOUND", "Target room was not found.")
        occupied = occupancy_count(db, room.id, excluding_allocation_id=allocation.id)
        if room.id != allocation.room_id and occupied >= room.capacity:
            raise DomainError(409, "ROOM_FULL", "The target room has no available capacity.", {"occupied": occupied, "capacity": room.capacity})
        old_room_id = allocation.room.room_id
        allocation.room = room
        allocation.updated_at = utcnow()
        log_event(db, event_type="ALLOCATION_MODIFIED", outcome="SUCCESS", actor=actor, details={"allocation_id": allocation.id, "student_id": allocation.student.student_id, "old_room_id": old_room_id, "new_room_id": room.room_id})
        db.commit()
        return find_allocation(db, allocation.id)
    except DomainError as exc:
        _write_allocation_failure(db, actor, "ALLOCATION_MODIFIED", {"allocation_id": allocation_id, "error_code": exc.code})
        raise
    except IntegrityError:
        _write_allocation_failure(db, actor, "ALLOCATION_MODIFIED", {"allocation_id": allocation_id, "error_code": "INTEGRITY_CONFLICT"})
        raise DomainError(409, "ALLOCATION_CONFLICT", "Allocation modification conflicts with an existing allocation.")


def deallocate(db: Session, allocation_id: int, actor: User) -> None:
    try:
        allocation = find_allocation(db, allocation_id)
        if allocation is None:
            raise DomainError(404, "ALLOCATION_NOT_FOUND", "Allocation was not found.")
        if allocation.status != "ACTIVE":
            raise DomainError(409, "ALLOCATION_NOT_ACTIVE", "Only active allocations can be deallocated.")
        allocation.status = "DEALLOCATED"
        allocation.updated_at = utcnow()
        allocation.deallocated_at = utcnow()
        log_event(db, event_type="ALLOCATION_DEALLOCATED", outcome="SUCCESS", actor=actor, details={"allocation_id": allocation.id, "student_id": allocation.student.student_id, "room_id": allocation.room.room_id})
        db.commit()
    except DomainError as exc:
        _write_allocation_failure(db, actor, "ALLOCATION_DEALLOCATED", {"allocation_id": allocation_id, "error_code": exc.code})
        raise


def allocation_representation(allocation: Allocation) -> dict:
    return {
        "allocation_id": allocation.id,
        "student_id": allocation.student.student_id,
        "room_id": allocation.room.room_id,
        "status": allocation.status,
        "created_at": allocation.created_at,
        "updated_at": allocation.updated_at,
        "deallocated_at": allocation.deallocated_at,
    }


def list_allocations(db: Session) -> list[Allocation]:
    stmt = select(Allocation).options(joinedload(Allocation.student), joinedload(Allocation.room)).order_by(Allocation.id.desc())
    return list(db.scalars(stmt))


def my_active_allocation(db: Session, user: User) -> Allocation | None:
    student = db.scalar(select(Student).where(Student.account_user_id == user.id))
    if student is None:
        return None
    return active_allocation_for_student(db, student.id)


def recent_audit_events(db: Session, limit: int = 100) -> list[AuditEvent]:
    return list(db.scalars(select(AuditEvent).order_by(AuditEvent.timestamp.desc(), AuditEvent.id.desc()).limit(limit)))
