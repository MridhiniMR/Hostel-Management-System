from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hms.config import SESSION_COOKIE_NAME, SESSION_HOURS, SECURE_COOKIES
from hms.database import get_db
from hms.errors import DomainError
from hms.models import Allocation, Room, Student, User
from hms.schemas import AllocationCreate, RoomCreate, StudentCreate, StudentUpdate
from hms.security import authenticate_and_issue_token, login_source_key, revoke_token, user_for_token
from hms.services import (
    allocation_representation, create_allocation, create_room, create_student,
    deallocate, list_allocations, list_rooms, list_students, my_active_allocation,
    room_representation, update_student,
)

router = APIRouter(tags=["Web interface"])
templates = Jinja2Templates(directory="hms/templates")


def _current_user(request: Request, db: Session) -> User | None:
    return user_for_token(db, request.cookies.get(SESSION_COOKIE_NAME))


def _login_redirect() -> RedirectResponse:
    return RedirectResponse("/login", status_code=303)


def _forbidden(request: Request, user: User | None = None) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={"user": user, "title": "Access denied", "message": "Administrator access is required."},
        status_code=403,
    )


def _admin_or_response(request: Request, db: Session):
    user = _current_user(request, db)
    if user is None:
        return None, _login_redirect()
    if user.role != "ADMIN":
        return user, _forbidden(request, user)
    return user, None


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str | None = None, db: Session = Depends(get_db)):
    if _current_user(request, db):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context={"user": None, "error": "Invalid identifier or password." if error else None})


@router.post("/login")
def login_submit(request: Request, identifier: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        token, _user = authenticate_and_issue_token(db, identifier, password, login_source_key(request.client.host if request.client else None, identifier))
    except ValueError:
        return templates.TemplateResponse(request=request, name="login.html", context={"user": None, "error": "Invalid identifier or password."}, status_code=401)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        secure=SECURE_COOKIES,
        samesite="lax",
        max_age=60 * 60 * SESSION_HOURS,
        path="/",
    )
    return response


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    revoke_token(db, request.cookies.get(SESSION_COOKIE_NAME))
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if user is None:
        return _login_redirect()
    counts = {
        "students": db.scalar(select(func.count(Student.id))) or 0,
        "rooms": db.scalar(select(func.count(Room.id))) or 0,
        "active_allocations": db.scalar(select(func.count(Allocation.id)).where(Allocation.status == "ACTIVE")) or 0,
    }
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"user": user, "counts": counts})


@router.get("/students", response_class=HTMLResponse)
def students_page(request: Request, q: str | None = None, error: str | None = None, success: str | None = None, db: Session = Depends(get_db)):
    user, response = _admin_or_response(request, db)
    if response:
        return response
    return templates.TemplateResponse(request=request, name="students.html", context={
        "user": user, "students": list_students(db, q.strip() if q and q.strip() else None),
        "q": q or "", "error": error, "success": success,
    })


@router.post("/students")
def create_student_page(
    request: Request,
    student_id: str = Form(...),
    name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    department: str = Form(""),
    year_of_study: str = Form(""),
    account_username: str = Form(""),
    db: Session = Depends(get_db),
):
    user, response = _admin_or_response(request, db)
    if response:
        return response
    try:
        payload = StudentCreate(
            student_id=student_id, name=name, email=email or None, phone=phone or None,
            department=department or None,
            year_of_study=int(year_of_study) if year_of_study else None,
            account_username=account_username or None,
        )
        create_student(db, {**payload.model_dump(), "account_username": payload.account_username}, user)
    except (ValidationError, ValueError, DomainError) as exc:
        message = exc.message if isinstance(exc, DomainError) else str(exc)
        return RedirectResponse(f"/students?error={_url_encode(message)}", status_code=303)
    return RedirectResponse("/students?success=Student+created", status_code=303)


@router.get("/students/{student_id}/edit", response_class=HTMLResponse)
def edit_student_page(request: Request, student_id: str, db: Session = Depends(get_db)):
    user, response = _admin_or_response(request, db)
    if response:
        return response
    from hms.repositories import find_student
    student = find_student(db, student_id)
    if student is None:
        return templates.TemplateResponse(request=request, name="error.html", context={"user": user, "title": "Not found", "message": "Student was not found."}, status_code=404)
    return templates.TemplateResponse(request=request, name="edit_student.html", context={"user": user, "student": student, "error": None})


@router.post("/students/{student_id}/edit")
def edit_student_submit(
    request: Request, student_id: str,
    name: str = Form(...), email: str = Form(""), phone: str = Form(""),
    department: str = Form(""), year_of_study: str = Form(""), db: Session = Depends(get_db),
):
    user, response = _admin_or_response(request, db)
    if response:
        return response
    try:
        payload = StudentUpdate(
            name=name, email=email or None, phone=phone or None,
            department=department or None,
            year_of_study=int(year_of_study) if year_of_study else None,
        )
        update_student(db, student_id, payload.model_dump(exclude_unset=True), user)
    except (ValidationError, ValueError, DomainError) as exc:
        message = exc.message if isinstance(exc, DomainError) else str(exc)
        return RedirectResponse(f"/students/{student_id}/edit?error={_url_encode(message)}", status_code=303)
    return RedirectResponse("/students?success=Student+updated", status_code=303)


@router.get("/rooms", response_class=HTMLResponse)
def rooms_page(request: Request, error: str | None = None, success: str | None = None, db: Session = Depends(get_db)):
    user, response = _admin_or_response(request, db)
    if response:
        return response
    rooms = [{**room_representation(db, room)} for room in list_rooms(db)]
    return templates.TemplateResponse(request=request, name="rooms.html", context={"user": user, "rooms": rooms, "error": error, "success": success})


@router.post("/rooms")
def create_room_page(request: Request, room_id: str = Form(...), capacity: str = Form(...), db: Session = Depends(get_db)):
    user, response = _admin_or_response(request, db)
    if response:
        return response
    try:
        payload = RoomCreate(room_id=room_id, capacity=int(capacity))
        create_room(db, payload.room_id, payload.capacity, user)
    except (ValidationError, ValueError, DomainError) as exc:
        message = exc.message if isinstance(exc, DomainError) else str(exc)
        return RedirectResponse(f"/rooms?error={_url_encode(message)}", status_code=303)
    return RedirectResponse("/rooms?success=Room+created", status_code=303)


@router.post("/rooms/{room_id}/capacity")
def update_room_capacity_page(request: Request, room_id: str, capacity: str = Form(...), db: Session = Depends(get_db)):
    user, response = _admin_or_response(request, db)
    if response:
        return response
    from hms.services import update_room
    try:
        update_room(db, room_id, int(capacity), user)
    except (ValueError, DomainError) as exc:
        message = exc.message if isinstance(exc, DomainError) else "Capacity must be a positive whole number."
        return RedirectResponse(f"/rooms?error={_url_encode(message)}", status_code=303)
    return RedirectResponse("/rooms?success=Room+updated", status_code=303)


@router.get("/allocations", response_class=HTMLResponse)
def allocations_page(request: Request, error: str | None = None, success: str | None = None, db: Session = Depends(get_db)):
    user, response = _admin_or_response(request, db)
    if response:
        return response
    room_data = [{**room_representation(db, room)} for room in list_rooms(db)]
    return templates.TemplateResponse(request=request, name="allocations.html", context={
        "user": user, "students": list_students(db), "rooms": room_data,
        "allocations": [allocation_representation(a) for a in list_allocations(db)],
        "error": error, "success": success,
    })


@router.post("/allocations")
def create_allocation_page(request: Request, student_id: str = Form(...), room_id: str = Form(...), db: Session = Depends(get_db)):
    user, response = _admin_or_response(request, db)
    if response:
        return response
    try:
        payload = AllocationCreate(student_id=student_id, room_id=room_id)
        create_allocation(db, payload.student_id, payload.room_id, user)
    except (ValidationError, ValueError, DomainError) as exc:
        message = exc.message if isinstance(exc, DomainError) else str(exc)
        return RedirectResponse(f"/allocations?error={_url_encode(message)}", status_code=303)
    return RedirectResponse("/allocations?success=Allocation+created", status_code=303)


@router.post("/allocations/{allocation_id}/deallocate")
def deallocate_page(request: Request, allocation_id: int, db: Session = Depends(get_db)):
    user, response = _admin_or_response(request, db)
    if response:
        return response
    try:
        deallocate(db, allocation_id, user)
    except DomainError as exc:
        return RedirectResponse(f"/allocations?error={_url_encode(exc.message)}", status_code=303)
    return RedirectResponse("/allocations?success=Allocation+deallocated", status_code=303)


@router.get("/my-allocation", response_class=HTMLResponse)
def my_allocation_page(request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if user is None:
        return _login_redirect()
    if user.role != "STUDENT":
        return _forbidden(request, user)
    allocation = my_active_allocation(db, user)
    return templates.TemplateResponse(request=request, name="my_allocation.html", context={"user": user, "allocation": allocation})


def _url_encode(message: str) -> str:
    from urllib.parse import quote
    return quote(message[:300], safe="")
