from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from hms.config import SESSION_COOKIE_NAME, SECURE_COOKIES
from hms.database import get_db
from hms.dependencies import get_current_user, raw_request_token, require_admin
from hms.errors import DomainError
from hms.models import Allocation, AuthSession, AuditEvent, Room, Student, User
from hms.repositories import find_student
from hms.schemas import (
    AllocationCreate, AllocationResponse, AllocationUpdate, AuditEventResponse,
    LoginRequest, LoginResponse, RoomCreate, RoomResponse, RoomUpdate,
    StudentCreate, StudentResponse, StudentUpdate, UserSummary,
)
from hms.security import authenticate_and_issue_token, log_event, login_source_key, revoke_token
from hms.services import (
    allocation_representation, create_allocation, create_room, create_student,
    deallocate, get_room, list_allocations, list_rooms, list_students, my_active_allocation,
    recent_audit_events, room_representation, update_allocation, update_room,
    update_student,
)

router = APIRouter(prefix="/api/v1", tags=["Hostel Management API"])


@router.post("/auth/login", response_model=LoginResponse)
def login(request: Request, body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    try:
        raw_token, user = authenticate_and_issue_token(db, body.identifier, body.password, login_source_key(request.client.host if request.client else None, body.identifier))
    except ValueError as exc:
        raise DomainError(401, "INVALID_CREDENTIALS", str(exc)) from exc
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=SECURE_COOKIES,
        samesite="lax",
        max_age=60 * 60 * 12,
        path="/",
    )
    return LoginResponse(access_token=raw_token, user=UserSummary(username=user.username, role=user.role))


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    revoke_token(db, raw_request_token(request))
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/students", response_model=list[StudentResponse])
def get_students(q: str | None = None, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if q is not None and q.strip():
        # Exact identifier search is intentional: it prevents broad, accidental record exposure.
        return list_students(db, q.strip())
    return list_students(db)


@router.post("/students", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def post_student(body: StudentCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    data = body.model_dump(exclude={"account_username"})
    data["account_username"] = body.account_username
    student = create_student(db, data, admin)
    return StudentResponse.model_validate(student)


@router.get("/students/{student_id}", response_model=StudentResponse)
def get_student(student_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    student = find_student(db, student_id)
    if student is None:
        raise DomainError(404, "STUDENT_NOT_FOUND", "Student was not found.")
    if user.role != "ADMIN" and student.account_user_id != user.id:
        raise DomainError(403, "STUDENT_RESOURCE_FORBIDDEN", "Students may view only their own student record.")
    return StudentResponse.model_validate(student)


@router.put("/students/{student_id}", response_model=StudentResponse)
def put_student(student_id: str, body: StudentUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    student = update_student(db, student_id, body.model_dump(exclude_unset=True), admin)
    return StudentResponse.model_validate(student)


@router.get("/rooms", response_model=list[RoomResponse])
def get_rooms(available_only: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [RoomResponse(**room_representation(db, room)) for room in list_rooms(db, available_only)]


@router.get("/rooms/{room_id}", response_model=RoomResponse)
def get_room_by_id(room_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return RoomResponse(**room_representation(db, get_room(db, room_id)))


@router.post("/rooms", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def post_room(body: RoomCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    room = create_room(db, body.room_id, body.capacity, admin)
    return RoomResponse(**room_representation(db, room))


@router.put("/rooms/{room_id}", response_model=RoomResponse)
def put_room(room_id: str, body: RoomUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    room = update_room(db, room_id, body.capacity, admin)
    return RoomResponse(**room_representation(db, room))


@router.get("/allocations", response_model=list[AllocationResponse])
def get_allocations(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return [AllocationResponse(**allocation_representation(a)) for a in list_allocations(db)]


@router.post("/allocations", response_model=AllocationResponse, status_code=status.HTTP_201_CREATED)
def post_allocation(body: AllocationCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    allocation = create_allocation(db, body.student_id, body.room_id, admin)
    return AllocationResponse(**allocation_representation(allocation))


@router.put("/allocations/{allocation_id}", response_model=AllocationResponse)
def put_allocation(allocation_id: int, body: AllocationUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    allocation = update_allocation(db, allocation_id, body.room_id, admin)
    return AllocationResponse(**allocation_representation(allocation))


@router.delete("/allocations/{allocation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_allocation(allocation_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    deallocate(db, allocation_id, admin)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me/allocation", response_model=AllocationResponse | None)
def get_my_allocation(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "STUDENT":
        raise DomainError(403, "STUDENT_ROLE_REQUIRED", "This endpoint is for student accounts.")
    allocation = my_active_allocation(db, user)
    return AllocationResponse(**allocation_representation(allocation)) if allocation else None


@router.get("/audit-events", response_model=list[AuditEventResponse])
def get_audit_events(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    events = recent_audit_events(db)
    return [
        AuditEventResponse(
            event_id=e.id,
            actor_identifier=e.actor_identifier,
            event_type=e.event_type,
            timestamp=e.timestamp,
            outcome=e.outcome,
            details=e.details,
        )
        for e in events
    ]
