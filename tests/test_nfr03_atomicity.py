"""NFR-03 (data integrity): an allocation and its capacity effect are atomic.

Covers test case TP-12 (forced failure mid-transaction leaves no partial state)
and a concurrency check (two requests cannot both take the last bed).
"""
from __future__ import annotations

import threading

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

import hms.services as services
from hms.database import Base
from hms.errors import DomainError
from hms.models import Allocation, AuditEvent, Room, Student
from hms.services import create_allocation, create_room, create_student, create_user


def login(client, username: str = "warden", password: str = "CorrectHorseBattery9!") -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"identifier": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _count(factory, model) -> int:
    db = factory()
    try:
        return int(db.scalar(select(func.count(model.id))) or 0)
    finally:
        db.close()


# ------------------------------------------------------------------ TP-12

def test_tp12_forced_failure_mid_allocation_leaves_no_partial_state(system, monkeypatch):
    """Force a failure after the allocation row is written but before commit."""
    client = system["client"]
    factory = system["session_factory"]
    headers = login(client)
    assert client.post("/api/v1/students", headers=headers, json={"student_id": "S001", "name": "Student One"}).status_code == 201
    assert client.post("/api/v1/rooms", headers=headers, json={"room_id": "R101", "capacity": 1}).status_code == 201

    def exploding_log_event(*args, **kwargs):
        raise RuntimeError("simulated failure during allocation transaction")

    monkeypatch.setattr(services, "log_event", exploding_log_event)
    with pytest.raises(RuntimeError):
        client.post("/api/v1/allocations", headers=headers, json={"student_id": "S001", "room_id": "R101"})
    monkeypatch.undo()

    # Nothing from the failed transaction may remain.
    assert _count(factory, Allocation) == 0
    room = client.get("/api/v1/rooms/R101", headers=headers).json()
    assert (room["occupied"], room["available"]) == (0, 1)

    # The system stays usable: the same allocation now succeeds.
    ok = client.post("/api/v1/allocations", headers=headers, json={"student_id": "S001", "room_id": "R101"})
    assert ok.status_code == 201
    room = client.get("/api/v1/rooms/R101", headers=headers).json()
    assert (room["occupied"], room["available"]) == (1, 0)


def test_tp12_session_is_rolled_back_by_service_on_unexpected_error(system, monkeypatch):
    """The service itself must roll back, not rely on the caller closing the session."""
    factory = system["session_factory"]
    db = factory()
    admin = create_user(db, "warden2", "CorrectHorseBattery9!", "ADMIN")
    create_student(db, {"student_id": "S001", "name": "Student One"}, admin)
    create_room(db, "R101", 1, admin)

    def exploding_log_event(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(services, "log_event", exploding_log_event)
    with pytest.raises(RuntimeError):
        create_allocation(db, "S001", "R101", admin)
    monkeypatch.undo()

    assert not db.in_transaction() or db.scalar(select(func.count(Allocation.id))) == 0
    assert db.scalar(select(func.count(Allocation.id))) == 0
    db.close()


def test_tp12_rejected_allocation_changes_no_capacity_state(system):
    """A domain rejection (full room) must also leave occupancy untouched."""
    client = system["client"]
    headers = login(client)
    for sid in ("S001", "S002"):
        assert client.post("/api/v1/students", headers=headers, json={"student_id": sid, "name": sid}).status_code == 201
    assert client.post("/api/v1/rooms", headers=headers, json={"room_id": "R101", "capacity": 1}).status_code == 201
    assert client.post("/api/v1/allocations", headers=headers, json={"student_id": "S001", "room_id": "R101"}).status_code == 201
    assert client.post("/api/v1/allocations", headers=headers, json={"student_id": "S002", "room_id": "R101"}).status_code == 409
    room = client.get("/api/v1/rooms/R101", headers=headers).json()
    assert (room["occupied"], room["available"]) == (1, 0)


# ------------------------------------------------- concurrency: last bed

def test_nfr03_two_concurrent_requests_cannot_both_take_the_last_bed(tmp_path):
    """Two admins allocate different students to the one remaining bed at the same time."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'race.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    setup = factory()
    admin = create_user(setup, "warden", "CorrectHorseBattery9!", "ADMIN")
    for sid in ("S001", "S002", "S003", "S004"):
        create_student(setup, {"student_id": sid, "name": sid}, admin)
    create_room(setup, "R101", 1, admin)
    setup.close()

    attempts = [("S001", "R101"), ("S002", "R101"), ("S003", "R101"), ("S004", "R101")]
    barrier = threading.Barrier(len(attempts))
    outcomes: list[str] = []
    lock = threading.Lock()

    def worker(student_id: str, room_id: str) -> None:
        db = factory()
        try:
            actor = db.scalar(select(services.User).where(services.User.username == "warden"))
            barrier.wait()
            try:
                create_allocation(db, student_id, room_id, actor)
                result = "ok"
            except DomainError as exc:
                result = exc.code
            except Exception as exc:  # noqa: BLE001 - recorded and asserted below
                result = f"unexpected:{type(exc).__name__}"
        finally:
            db.close()
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=worker, args=a) for a in attempts]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    check = factory()
    active = check.scalar(select(func.count(Allocation.id)).where(Allocation.status == "ACTIVE"))
    capacity = check.scalar(select(Room.capacity).where(Room.room_id == "R101"))
    check.close()
    engine.dispose()

    assert len(outcomes) == len(attempts), outcomes
    assert not any(o.startswith("unexpected") for o in outcomes), outcomes
    assert outcomes.count("ok") == 1, outcomes
    assert active == capacity == 1


def test_nfr03_concurrent_moves_cannot_overfill_a_room(tmp_path):
    """Several students try to move into the single free bed of another room at once."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'move_race.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    setup = factory()
    admin = create_user(setup, "warden", "CorrectHorseBattery9!", "ADMIN")
    allocation_ids = []
    for index in range(1, 5):
        sid, rid = f"S00{index}", f"R10{index}"
        create_student(setup, {"student_id": sid, "name": sid}, admin)
        create_room(setup, rid, 1, admin)
        allocation_ids.append(create_allocation(setup, sid, rid, admin).id)
    create_room(setup, "TARGET", 1, admin)
    setup.close()

    barrier = threading.Barrier(len(allocation_ids))
    outcomes: list[str] = []
    lock = threading.Lock()

    def worker(allocation_id: int) -> None:
        db = factory()
        try:
            actor = db.scalar(select(services.User).where(services.User.username == "warden"))
            barrier.wait()
            try:
                services.update_allocation(db, allocation_id, "TARGET", actor)
                result = "ok"
            except DomainError as exc:
                result = exc.code
            except Exception as exc:  # noqa: BLE001 - recorded and asserted below
                result = f"unexpected:{type(exc).__name__}"
        finally:
            db.close()
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=worker, args=(a,)) for a in allocation_ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    check = factory()
    in_target = check.scalar(
        select(func.count(Allocation.id))
        .join(Room, Room.id == Allocation.room_id)
        .where(Room.room_id == "TARGET", Allocation.status == "ACTIVE")
    )
    check.close()
    engine.dispose()

    assert len(outcomes) == len(allocation_ids), outcomes
    assert not any(o.startswith("unexpected") for o in outcomes), outcomes
    assert outcomes.count("ok") == 1, outcomes
    assert in_target == 1
