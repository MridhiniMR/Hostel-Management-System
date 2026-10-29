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
