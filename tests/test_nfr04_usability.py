"""NFR-04 (usability) / TP-13: a trained administrator completes a valid allocation in
no more than five primary data-entry steps after login.

Counted workflow after login: open Allocations (navigation, not data entry), then
1) choose the student, 2) choose the room, 3) press Allocate = 3 data-entry steps.
"""
from __future__ import annotations

import re

MAX_STEPS = 5


def _login_and_seed(client):
    assert client.post("/login", data={"identifier": "warden", "password": "CorrectHorseBattery9!"}).status_code == 200
    assert client.post("/students", data={"student_id": "S101", "name": "Demo Student"}).status_code == 200
    assert client.post("/students", data={"student_id": "S102", "name": "Second Student"}).status_code == 200
    assert client.post("/rooms", data={"room_id": "R101", "capacity": "1"}).status_code == 200
    assert client.post("/rooms", data={"room_id": "R102", "capacity": "2"}).status_code == 200


def _allocation_form(html: str) -> str:
    match = re.search(r'<form action="/allocations" method="post".*?</form>', html, re.S)
    assert match, "allocation form not found on the Allocations page"
    return match.group(0)


def test_tp13_valid_allocation_needs_at_most_five_data_entry_steps(system):
    client = system["client"]
    _login_and_seed(client)
    form = _allocation_form(client.get("/allocations").text)

    entry_fields = len(re.findall(r"<select |<input (?!type=\"hidden\")", form))
    submit_buttons = len(re.findall(r'<button type="submit"', form))
    steps = entry_fields + submit_buttons
    assert entry_fields == 2          # student + room
    assert submit_buttons == 1        # Allocate
    assert steps == 3
    assert steps <= MAX_STEPS

    # The counted steps really complete a valid allocation.
    done = client.post("/allocations", data={"student_id": "S101", "room_id": "R101"})
    assert done.status_code == 200
    assert "ACTIVE" in done.text


def test_nfr04_room_dropdown_offers_only_rooms_with_space(system):
    client = system["client"]
    _login_and_seed(client)
    assert client.post("/allocations", data={"student_id": "S101", "room_id": "R101"}).status_code == 200  # R101 now full
    form = _allocation_form(client.get("/allocations").text)
    assert 'value="R102"' in form
    assert 'value="R101"' not in form


def test_nfr04_success_message_names_student_and_room(system):
    client = system["client"]
    _login_and_seed(client)
    done = client.post("/allocations", data={"student_id": "S101", "room_id": "R102"})
    assert "Allocated S101 to room R102" in done.text


def test_nfr04_error_messages_are_plain_language(system):
    client = system["client"]
    _login_and_seed(client)
    client.post("/allocations", data={"student_id": "S101", "room_id": "R101"})
    duplicate = client.post("/allocations", data={"student_id": "S101", "room_id": "R102"})
    assert "already has an active room allocation" in duplicate.text
    full = client.post("/allocations", data={"student_id": "S102", "room_id": "R101"})
    assert "no available capacity" in full.text

def test_fr07_modify_allocation_through_web_form(system):
    client = system["client"]
    _login_and_seed(client)

    # Create an allocation in R101.
    created = client.post(
        "/allocations",
        data={"student_id": "S101", "room_id": "R101"},
    )
    assert created.status_code == 200

    # Find the allocation ID from the allocations API.
    api_login = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "warden",
            "password": "CorrectHorseBattery9!",
        },
    )
    assert api_login.status_code == 200
    headers = {
        "Authorization": f"Bearer {api_login.json()['access_token']}"
    }
    allocations = client.get("/api/v1/allocations", headers=headers)
    assert allocations.status_code == 200
    allocation = next(
        a for a in allocations.json() if a["student_id"] == "S101"
    )

    # Move the allocation from R101 to R102.
    response = client.post(
        f"/allocations/{allocation['allocation_id']}/modify",
        data={"room_id": "R102"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "moved to room R102" in response.text

    updated = client.get("/api/v1/allocations", headers=headers).json()
    moved = next(a for a in updated if a["student_id"] == "S101")
    assert moved["room_id"] == "R102"


def test_fr07_modify_form_is_shown_for_active_allocations(system):
    client = system["client"]
    _login_and_seed(client)

    client.post(
        "/allocations",
        data={"student_id": "S101", "room_id": "R101"},
    )

    page = client.get("/allocations")
    assert page.status_code == 200
    assert "/modify" in page.text
    assert "Change room" in page.text
    assert "Deallocate" in page.text
