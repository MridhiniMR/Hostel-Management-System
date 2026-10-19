from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from hms.database import Base, get_db
from hms.main import app
from hms.services import create_user


@pytest.fixture
def system():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    db = TestingSessionLocal()
    create_user(db, "warden", "CorrectHorseBattery9!", "ADMIN")
    create_user(db, "student1", "StudentPassphrase9!", "STUDENT")
    create_user(db, "student2", "StudentPassphrase10!", "STUDENT")
    db.close()

    with TestClient(app) as client:
        yield {"client": client, "session_factory": TestingSessionLocal}

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def login(client, username: str = "warden", password: str = "CorrectHorseBattery9!") -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"identifier": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
