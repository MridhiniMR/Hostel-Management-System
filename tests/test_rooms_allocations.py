"""Tests for FR-04 (room records), FR-05 (allocate to available rooms) and
FR-06 (prevent invalid or conflicting allocations)."""
from __future__ import annotations



def login(client, username: str = "warden", password: str = "CorrectHorseBattery9!") -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"identifier": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _student(client, headers, student_id: str, **extra):
    response = client.post("/api/v1/students", headers=headers, json={"student_id": student_id, "name": f"Student {student_id}", **extra})
    assert response.status_code == 201, response.text


def _room(client, headers, room_id: str, capacity: int):
    response = client.post("/api/v1/rooms", headers=headers, json={"room_id": room_id, "capacity": capacity})
    assert response.status_code == 201, response.text


def _allocate(client, headers, student_id: str, room_id: str):
    return client.post("/api/v1/allocations", headers=headers, json={"student_id": student_id, "room_id": room_id})


def _error_codes(client, headers) -> list[tuple[str, str]]:
    events = client.get("/api/v1/audit-events", headers=headers).json()
    return [(e["event_type"], e["outcome"]) for e in events]


# ---------------------------------------------------------------- FR-04

def test_fr04_create_room_returns_occupancy_fields(system):
    client = system["client"]
    headers = login(client)
    response = client.post("/api/v1/rooms", headers=headers, json={"room_id": "R101", "capacity": 3})
    assert response.status_code == 201
    assert response.json() == {"room_id": "R101", "capacity": 3, "occupied": 0, "available": 3}


def test_fr04_duplicate_room_is_rejected(system):
    client = system["client"]
    headers = login(client)
    _room(client, headers, "R101", 2)
    response = client.post("/api/v1/rooms", headers=headers, json={"room_id": "R101", "capacity": 4})
    assert response.status_code == 409
    assert response.json()["error_code"] == "ROOM_ALREADY_EXISTS"
    # The original room must be unchanged.
    assert client.get("/api/v1/rooms/R101", headers=headers).json()["capacity"] == 2


def test_fr04_invalid_room_input_is_rejected(system):
    client = system["client"]
    headers = login(client)
    for payload in (
        {"room_id": "R1", "capacity": 0},
        {"room_id": "R1", "capacity": -2},
        {"room_id": "R1", "capacity": 1001},
        {"room_id": "   ", "capacity": 2},
        {"room_id": "' OR 1=1--", "capacity": 2},
        {"room_id": "R1"},
    ):
        response = client.post("/api/v1/rooms", headers=headers, json=payload)
        assert response.status_code == 422, payload
    assert client.get("/api/v1/rooms", headers=headers).json() == []


def test_fr04_update_room_capacity(system):
    client = system["client"]
    headers = login(client)
    _room(client, headers, "R101", 2)
    response = client.put("/api/v1/rooms/R101", headers=headers, json={"capacity": 5})
    assert response.status_code == 200
    assert response.json()["capacity"] == 5
    assert response.json()["available"] == 5


def test_fr04_update_unknown_room_returns_404(system):
    client = system["client"]
    headers = login(client)
    response = client.put("/api/v1/rooms/NOPE", headers=headers, json={"capacity": 2})
    assert response.status_code == 404
    assert response.json()["error_code"] == "ROOM_NOT_FOUND"


def test_fr04_get_single_room_and_unknown_room(system):
    client = system["client"]
    headers = login(client)
    _room(client, headers, "R101", 2)
    found = client.get("/api/v1/rooms/R101", headers=headers)
    assert found.status_code == 200
    assert found.json()["room_id"] == "R101"
    missing = client.get("/api/v1/rooms/R999", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["error_code"] == "ROOM_NOT_FOUND"


def test_fr04_room_list_is_sorted_and_requires_login(system):
    client = system["client"]
    headers = login(client)
    for room_id in ("R300", "R100", "R200"):
        _room(client, headers, room_id, 1)
    assert [r["room_id"] for r in client.get("/api/v1/rooms", headers=headers).json()] == ["R100", "R200", "R300"]
    assert client.get("/api/v1/rooms").status_code == 401
    assert client.get("/api/v1/rooms/R100").status_code == 401


def test_fr04_students_cannot_create_or_change_rooms(system):
    client = system["client"]
    admin = login(client)
    _room(client, admin, "R101", 2)
    student = login(client, "student1", "StudentPassphrase9!")
    assert client.post("/api/v1/rooms", headers=student, json={"room_id": "R202", "capacity": 2}).status_code == 403
    assert client.put("/api/v1/rooms/R101", headers=student, json={"capacity": 9}).status_code == 403
    # Students may still read room information.
    assert client.get("/api/v1/rooms/R101", headers=student).status_code == 200


def test_fr04_room_changes_are_audited(system):
    client = system["client"]
    headers = login(client)
    _room(client, headers, "R101", 2)
    client.put("/api/v1/rooms/R101", headers=headers, json={"capacity": 3})
    events = _error_codes(client, headers)
    assert ("ROOM_CREATED", "SUCCESS") in events
    assert ("ROOM_UPDATED", "SUCCESS") in events


# ---------------------------------------------------------------- FR-05

def test_fr05_allocate_student_to_available_room(system):
    client = system["client"]
    headers = login(client)
    _student(client, headers, "S001")
    _room(client, headers, "R101", 2)
    response = _allocate(client, headers, "S001", "R101")
    assert response.status_code == 201
    body = response.json()
    assert body["student_id"] == "S001"
    assert body["room_id"] == "R101"
    assert body["status"] == "ACTIVE"
    assert body["created_at"]
    room = client.get("/api/v1/rooms/R101", headers=headers).json()
    assert (room["occupied"], room["available"]) == (1, 1)


def test_fr05_allocations_listed_with_student_and_room(system):
    client = system["client"]
    headers = login(client)
    _student(client, headers, "S001")
    _room(client, headers, "R101", 2)
    _allocate(client, headers, "S001", "R101")
    listing = client.get("/api/v1/allocations", headers=headers).json()
    assert [(a["student_id"], a["room_id"]) for a in listing] == [("S001", "R101")]


def test_fr05_available_only_filter_hides_full_rooms(system):
    client = system["client"]
    headers = login(client)
    for sid in ("S001", "S002"):
        _student(client, headers, sid)
    _room(client, headers, "R101", 1)
    _room(client, headers, "R102", 2)
    assert _allocate(client, headers, "S001", "R101").status_code == 201

    everything = client.get("/api/v1/rooms", headers=headers).json()
    assert [r["room_id"] for r in everything] == ["R101", "R102"]
    available = client.get("/api/v1/rooms?available_only=true", headers=headers).json()
    assert [r["room_id"] for r in available] == ["R102"]

    # Freed capacity makes the room available again.
    allocation_id = client.get("/api/v1/allocations", headers=headers).json()[0]["allocation_id"]
    assert client.delete(f"/api/v1/allocations/{allocation_id}", headers=headers).status_code == 204
    available = client.get("/api/v1/rooms?available_only=true", headers=headers).json()
    assert [r["room_id"] for r in available] == ["R101", "R102"]


def test_fr05_student_can_be_reallocated_after_deallocation(system):
    client = system["client"]
    headers = login(client)
    _student(client, headers, "S001")
    _room(client, headers, "R101", 1)
    _room(client, headers, "R102", 1)
    first = _allocate(client, headers, "S001", "R101").json()
    assert client.delete(f"/api/v1/allocations/{first['allocation_id']}", headers=headers).status_code == 204
    second = _allocate(client, headers, "S001", "R102")
    assert second.status_code == 201
    assert second.json()["room_id"] == "R102"


def test_fr05_only_admin_can_allocate(system):
    client = system["client"]
    admin = login(client)
    _student(client, admin, "S001", account_username="student1")
    _room(client, admin, "R101", 1)
    student = login(client, "student1", "StudentPassphrase9!")
    assert _allocate(client, student, "S001", "R101").status_code == 403
    assert _allocate(client, {}, "S001", "R101").status_code == 401


# ---------------------------------------------------------------- FR-06

def test_fr06_unknown_student_or_room_is_rejected(system):
    client = system["client"]
    headers = login(client)
    _student(client, headers, "S001")
    _room(client, headers, "R101", 1)
    no_student = _allocate(client, headers, "S999", "R101")
    assert no_student.status_code == 404
    assert no_student.json()["error_code"] == "STUDENT_NOT_FOUND"
    no_room = _allocate(client, headers, "S001", "R999")
    assert no_room.status_code == 404
    assert no_room.json()["error_code"] == "ROOM_NOT_FOUND"
    assert client.get("/api/v1/allocations", headers=headers).json() == []


def test_fr06_malformed_identifiers_are_rejected(system):
    client = system["client"]
    headers = login(client)
    for payload in (
        {"student_id": "' OR 1=1--", "room_id": "R101"},
        {"student_id": "S001", "room_id": "R1 01"},
        {"student_id": "", "room_id": "R101"},
        {"student_id": "S001"},
    ):
        assert client.post("/api/v1/allocations", headers=headers, json=payload).status_code == 422, payload


def test_fr06_full_room_is_rejected_and_state_is_unchanged(system):
    client = system["client"]
    headers = login(client)
    for sid in ("S001", "S002", "S003"):
        _student(client, headers, sid)
    _room(client, headers, "R101", 2)
    assert _allocate(client, headers, "S001", "R101").status_code == 201
    assert _allocate(client, headers, "S002", "R101").status_code == 201
    rejected = _allocate(client, headers, "S003", "R101")
    assert rejected.status_code == 409
    assert rejected.json()["error_code"] == "ROOM_FULL"
    room = client.get("/api/v1/rooms/R101", headers=headers).json()
    assert (room["occupied"], room["available"]) == (2, 0)
    assert len(client.get("/api/v1/allocations", headers=headers).json()) == 2


def test_fr06_student_cannot_hold_two_active_allocations(system):
    client = system["client"]
    headers = login(client)
    _student(client, headers, "S001")
    _room(client, headers, "R101", 2)
    _room(client, headers, "R102", 2)
    assert _allocate(client, headers, "S001", "R101").status_code == 201
    for room_id in ("R101", "R102"):
        response = _allocate(client, headers, "S001", room_id)
        assert response.status_code == 409
        assert response.json()["error_code"] == "STUDENT_ALREADY_ALLOCATED"
    assert len(client.get("/api/v1/allocations", headers=headers).json()) == 1


def test_fr06_moving_into_a_full_room_is_rejected(system):
    client = system["client"]
    headers = login(client)
    for sid in ("S001", "S002"):
        _student(client, headers, sid)
    _room(client, headers, "R101", 1)
    _room(client, headers, "R102", 1)
    _allocate(client, headers, "S001", "R101")
    mover = _allocate(client, headers, "S002", "R102").json()
    response = client.put(f"/api/v1/allocations/{mover['allocation_id']}", headers=headers, json={"room_id": "R101"})
    assert response.status_code == 409
    assert response.json()["error_code"] == "ROOM_FULL"
    still_there = [a for a in client.get("/api/v1/allocations", headers=headers).json() if a["student_id"] == "S002"]
    assert still_there[0]["room_id"] == "R102"


def test_fr06_move_to_room_with_space_succeeds_and_frees_old_room(system):
    client = system["client"]
    headers = login(client)
    _student(client, headers, "S001")
    _room(client, headers, "R101", 1)
    _room(client, headers, "R102", 1)
    allocation = _allocate(client, headers, "S001", "R101").json()
    moved = client.put(f"/api/v1/allocations/{allocation['allocation_id']}", headers=headers, json={"room_id": "R102"})
    assert moved.status_code == 200
    assert moved.json()["room_id"] == "R102"
    assert client.get("/api/v1/rooms/R101", headers=headers).json()["available"] == 1
    assert client.get("/api/v1/rooms/R102", headers=headers).json()["available"] == 0


def test_fr06_cannot_modify_or_deallocate_inactive_or_unknown_allocation(system):
    client = system["client"]
    headers = login(client)
    _student(client, headers, "S001")
    _room(client, headers, "R101", 1)
    _room(client, headers, "R102", 1)
    allocation = _allocate(client, headers, "S001", "R101").json()
    allocation_id = allocation["allocation_id"]
    assert client.delete(f"/api/v1/allocations/{allocation_id}", headers=headers).status_code == 204
    again = client.delete(f"/api/v1/allocations/{allocation_id}", headers=headers)
    assert again.status_code == 409
    assert again.json()["error_code"] == "ALLOCATION_NOT_ACTIVE"
    moved = client.put(f"/api/v1/allocations/{allocation_id}", headers=headers, json={"room_id": "R102"})
    assert moved.status_code == 409
    assert client.delete("/api/v1/allocations/99999", headers=headers).status_code == 404


def test_fr06_rejected_attempts_are_audited_as_failures(system):
    client = system["client"]
    headers = login(client)
    _student(client, headers, "S001")
    _room(client, headers, "R101", 1)
    _allocate(client, headers, "S001", "R101")
    _allocate(client, headers, "S001", "R101")  # duplicate, rejected
    _allocate(client, headers, "S404", "R101")  # unknown student, rejected
    events = _error_codes(client, headers)
    assert events.count(("ALLOCATION_CREATED", "SUCCESS")) == 1
    assert events.count(("ALLOCATION_CREATED", "FAILURE")) == 2
