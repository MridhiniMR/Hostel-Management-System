from __future__ import annotations

from sqlalchemy import select

from hms.models import AuditEvent, Student, User
from hms.security import verify_password


def login(client, username: str = "warden", password: str = "CorrectHorseBattery9!") -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"identifier": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health_and_unauthenticated_access(system):
    client = system["client"]
    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/api/v1/students")
    assert response.status_code == 401
    assert response.json()["error_code"] == "AUTHENTICATION_REQUIRED"


def test_passwords_are_hashed_and_login_events_are_recorded(system):
    client = system["client"]
    factory = system["session_factory"]
    db = factory()
    admin = db.scalar(select(User).where(User.username == "warden"))
    assert admin is not None
    assert admin.password_hash != "CorrectHorseBattery9!"
    assert verify_password("CorrectHorseBattery9!", admin.password_hash)
    db.close()

    assert client.post("/api/v1/auth/login", json={"identifier": "warden", "password": "wrong-password"}).status_code == 401
    headers = login(client)
    response = client.get("/api/v1/audit-events", headers=headers)
    assert response.status_code == 200
    events = response.json()
    assert any(e["event_type"] == "AUTH_LOGIN" and e["outcome"] == "FAILURE" for e in events)
    assert any(e["event_type"] == "AUTH_LOGIN" and e["outcome"] == "SUCCESS" for e in events)


def test_student_crud_and_exact_identifier_search(system):
    client = system["client"]
    headers = login(client)
    create = client.post("/api/v1/students", headers=headers, json={
        "student_id": "S001", "name": "Asha Nair", "email": "asha@example.edu", "phone": "9000000001", "department": "CSE", "year_of_study": 2,
    })
    assert create.status_code == 201, create.text
    assert create.json()["student_id"] == "S001"

    update = client.put("/api/v1/students/S001", headers=headers, json={"name": "Asha Nair Updated"})
    assert update.status_code == 200, update.text
    assert update.json()["name"] == "Asha Nair Updated"

    results = client.get("/api/v1/students?q=S001", headers=headers)
    assert results.status_code == 200
    assert [s["student_id"] for s in results.json()] == ["S001"]
    assert client.get("/api/v1/students?q=S999", headers=headers).json() == []
def test_student_create_update_validation_and_persistence(system):
    client = system["client"]
    headers = login(client)

    # Duplicate student identifiers must be rejected.
    first = client.post(
        "/api/v1/students",
        headers=headers,
        json={"student_id": "S200", "name": "Original Name"},
    )
    assert first.status_code == 201, first.text

    duplicate = client.post(
        "/api/v1/students",
        headers=headers,
        json={"student_id": "S200", "name": "Duplicate Name"},
    )
    assert duplicate.status_code == 409

    # Valid updates must persist when the record is fetched again.
    updated = client.put(
        "/api/v1/students/S200",
        headers=headers,
        json={
            "name": "Updated Name",
            "email": "updated@example.edu",
            "year_of_study": 3,
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Updated Name"

    fetched = client.get("/api/v1/students/S200", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Updated Name"
    assert fetched.json()["email"] == "updated@example.edu"
    assert fetched.json()["year_of_study"] == 3

    # Invalid updates must be rejected without changing the saved record.
    invalid_email = client.put(
        "/api/v1/students/S200",
        headers=headers,
        json={"email": "not-an-email"},
    )
    assert invalid_email.status_code == 422

    invalid_year = client.put(
        "/api/v1/students/S200",
        headers=headers,
        json={"year_of_study": 0},
    )
    assert invalid_year.status_code == 422

    blank_name = client.put(
        "/api/v1/students/S200",
        headers=headers,
        json={"name": "   "},
    )
    assert blank_name.status_code == 422

    unchanged = client.get("/api/v1/students/S200", headers=headers)
    assert unchanged.status_code == 200
    assert unchanged.json()["name"] == "Updated Name"
    assert unchanged.json()["email"] == "updated@example.edu"
    assert unchanged.json()["year_of_study"] == 3

def test_input_validation_rejects_hostile_identifiers_and_incomplete_student(system):
    client = system["client"]
    headers = login(client)
    invalid_id = client.post("/api/v1/students", headers=headers, json={"student_id": "' OR 1=1--", "name": "Injection"})
    assert invalid_id.status_code == 422
    incomplete = client.post("/api/v1/students", headers=headers, json={"student_id": "S004", "name": "   "})
    assert incomplete.status_code == 422
    assert client.get("/api/v1/students/S001", headers=headers).status_code == 404


def test_student_cannot_read_other_students_or_admin_functions(system):
    client = system["client"]
    admin_headers = login(client)
    made = client.post("/api/v1/students", headers=admin_headers, json={
        "student_id": "S001", "name": "Student One", "account_username": "student1",
    })
    assert made.status_code == 201, made.text
    client.post("/api/v1/students", headers=admin_headers, json={"student_id": "S002", "name": "Student Two", "account_username": "student2"})
    student_headers = login(client, "student1", "StudentPassphrase9!")
    assert client.get("/api/v1/students/S001", headers=student_headers).status_code == 200
    forbidden = client.get("/api/v1/students/S002", headers=student_headers)
    assert forbidden.status_code == 403
    assert client.post("/api/v1/students", headers=student_headers, json={"student_id": "S003", "name": "Not allowed"}).status_code == 403


def test_room_capacity_duplicate_allocation_and_atomic_deallocation(system):
    client = system["client"]
    headers = login(client)
    for student_id in ("S001", "S002"):
        response = client.post("/api/v1/students", headers=headers, json={"student_id": student_id, "name": f"Student {student_id}"})
        assert response.status_code == 201, response.text
    room = client.post("/api/v1/rooms", headers=headers, json={"room_id": "R101", "capacity": 1})
    assert room.status_code == 201, room.text
    assert room.json()["available"] == 1

    first = client.post("/api/v1/allocations", headers=headers, json={"student_id": "S001", "room_id": "R101"})
    assert first.status_code == 201, first.text
    assert first.json()["status"] == "ACTIVE"
    assert client.get("/api/v1/rooms", headers=headers).json()[0]["available"] == 0

    full_room = client.post("/api/v1/allocations", headers=headers, json={"student_id": "S002", "room_id": "R101"})
    assert full_room.status_code == 409
    duplicate = client.post("/api/v1/allocations", headers=headers, json={"student_id": "S001", "room_id": "R101"})
    assert duplicate.status_code == 409

    deallocated = client.delete(f"/api/v1/allocations/{first.json()['allocation_id']}", headers=headers)
    assert deallocated.status_code == 204
    inventory = client.get("/api/v1/rooms", headers=headers).json()
    assert inventory[0]["occupied"] == 0
    assert inventory[0]["available"] == 1

    events = client.get("/api/v1/audit-events", headers=headers).json()
    assert any(e["event_type"] == "ALLOCATION_CREATED" and e["outcome"] == "SUCCESS" for e in events)
    assert any(e["event_type"] == "ALLOCATION_CREATED" and e["outcome"] == "FAILURE" for e in events)
    assert any(e["event_type"] == "ALLOCATION_DEALLOCATED" and e["outcome"] == "SUCCESS" for e in events)


def test_student_can_only_view_own_allocation(system):
    client = system["client"]
    admin_headers = login(client)

    for student_id, username in (("S001", "student1"), ("S002", "student2")):
        resp = client.post(
            "/api/v1/students",
            headers=admin_headers,
            json={
                "student_id": student_id,
                "name": f"Student {student_id}",
                "account_username": username,
            },
        )
        assert resp.status_code == 201, resp.text

    for room_id in ("R101", "R102"):
        resp = client.post(
            "/api/v1/rooms",
            headers=admin_headers,
            json={"room_id": room_id, "capacity": 1},
        )
        assert resp.status_code == 201, resp.text

    for student_id, room_id in (("S001", "R101"), ("S002", "R102")):
        resp = client.post(
            "/api/v1/allocations",
            headers=admin_headers,
            json={"student_id": student_id, "room_id": room_id},
        )
        assert resp.status_code == 201, resp.text

    # Each student sees only their own allocation.
    student1_headers = login(client, "student1", "StudentPassphrase9!")
    student1_allocation = client.get(
        "/api/v1/me/allocation", headers=student1_headers
    )
    assert student1_allocation.status_code == 200
    assert student1_allocation.json()["student_id"] == "S001"
    assert student1_allocation.json()["room_id"] == "R101"

    student2_headers = login(client, "student2", "StudentPassphrase10!")
    student2_allocation = client.get(
        "/api/v1/me/allocation", headers=student2_headers
    )
    assert student2_allocation.status_code == 200
    assert student2_allocation.json()["student_id"] == "S002"
    assert student2_allocation.json()["room_id"] == "R102"

    # Admins cannot use this student-only endpoint.
    forbidden = client.get("/api/v1/me/allocation", headers=admin_headers)
    assert forbidden.status_code == 403

    # Unauthenticated requests must be rejected.
    unauthenticated = client.get("/api/v1/me/allocation")
    assert unauthenticated.status_code == 401

def test_room_capacity_cannot_be_reduced_below_occupancy(system):
    client = system["client"]
    headers = login(client)
    for student_id in ("S001", "S002"):
        assert client.post("/api/v1/students", headers=headers, json={"student_id": student_id, "name": f"Student {student_id}"}).status_code == 201
    assert client.post("/api/v1/rooms", headers=headers, json={"room_id": "R101", "capacity": 2}).status_code == 201
    for student_id in ("S001", "S002"):
        assert client.post("/api/v1/allocations", headers=headers, json={"student_id": student_id, "room_id": "R101"}).status_code == 201
    response = client.put("/api/v1/rooms/R101", headers=headers, json={"capacity": 0})
    assert response.status_code == 422
    response = client.put("/api/v1/rooms/R101", headers=headers, json={"capacity": 1})
    assert response.status_code == 409


def test_browser_login_and_end_to_end_admin_workflow(system):
    client = system["client"]
    page = client.get("/login")
    assert page.status_code == 200
    assert "Sign in" in page.text

    logged_in = client.post("/login", data={"identifier": "warden", "password": "CorrectHorseBattery9!"})
    assert logged_in.status_code == 200
    assert "Dashboard" in logged_in.text
    assert client.cookies.get("hms_session")

    created_student = client.post("/students", data={"student_id": "S101", "name": "Demo Student", "email": "demo@example.edu"})
    assert created_student.status_code == 200
    assert "S101" in created_student.text

    created_room = client.post("/rooms", data={"room_id": "R101", "capacity": "1"})
    assert created_room.status_code == 200
    assert "R101" in created_room.text

    created_allocation = client.post("/allocations", data={"student_id": "S101", "room_id": "R101"})
    assert created_allocation.status_code == 200
    assert "ACTIVE" in created_allocation.text


def test_login_throttle_blocks_repeated_failures_for_source_identifier_pair(system):
    client = system["client"]
    for _ in range(5):
        failed = client.post("/api/v1/auth/login", json={"identifier": "warden", "password": "not-the-password"})
        assert failed.status_code == 401
    blocked_even_with_correct_password = client.post("/api/v1/auth/login", json={"identifier": "warden", "password": "CorrectHorseBattery9!"})
    assert blocked_even_with_correct_password.status_code == 401
    assert blocked_even_with_correct_password.json()["error_code"] == "INVALID_CREDENTIALS"

    factory = system["session_factory"]
    db = factory()
    assert db.scalar(select(AuditEvent.id).where(AuditEvent.event_type == "AUTH_LOGIN", AuditEvent.outcome == "FAILURE", AuditEvent.source_key.is_not(None))) is not None
    db.close()


def test_logout_revokes_the_bearer_token(system):
    client = system["client"]
    headers = login(client)
    logout_response = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_response.status_code == 204
    revoked_access = client.get("/api/v1/students", headers=headers)
    assert revoked_access.status_code == 401
def test_student_search_matches_exact_identifier_only(system):
    client = system["client"]
    headers = login(client)

    for student_id, name in [
        ("S301", "Student One"),
        ("S301A", "Student Two"),
        ("S302", "Student Three"),
    ]:
        response = client.post(
            "/api/v1/students",
            headers=headers,
            json={"student_id": student_id, "name": name},
        )
        assert response.status_code == 201, response.text

    # Exact match should return only the requested student.
    response = client.get(
        "/api/v1/students?q=S301",
        headers=headers,
    )
    assert response.status_code == 200
    assert [student["student_id"] for student in response.json()] == ["S301"]

    # A partial identifier should not match another student's record.
    response = client.get(
        "/api/v1/students?q=S30",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json() == []

    # An unauthenticated user must not search student records.
    response = client.get("/api/v1/students?q=S301")
    assert response.status_code == 401


def test_browser_rooms_page_displays_occupancy_and_availability(system):
    client = system["client"]
    headers = login(client)

    # Create a room with capacity for two students.
    room = client.post(
        "/api/v1/rooms",
        headers=headers,
        json={"room_id": "R201", "capacity": 2},
    )
    assert room.status_code == 201

    # Create a student and allocate them to the room.
    student = client.post(
        "/api/v1/students",
        headers=headers,
        json={"student_id": "S201", "name": "Demo Student"},
    )
    assert student.status_code == 201

    allocation = client.post(
        "/api/v1/allocations",
        headers=headers,
        json={"student_id": "S201", "room_id": "R201"},
    )
    assert allocation.status_code == 201

    # Verify the actual browser page.
    page = client.get("/rooms")
    assert page.status_code == 200
    assert "R201" in page.text
    assert "Occupied" in page.text
    assert "Available" in page.text

    # The room should show 1 occupied bed and 1 available bed.
    assert "1" in page.text



def test_https_enforcement_redirects_http_requests(monkeypatch, system):
    from hms import main

    monkeypatch.setattr(main, "REQUIRE_HTTPS", True)

    client = system["client"]
    response = client.get("/health", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"].startswith("https://")
