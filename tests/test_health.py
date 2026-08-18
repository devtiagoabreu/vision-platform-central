from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.storage.database import Base, get_db

TEST_DB_URL = "sqlite:///test_central.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=test_engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def patch_sessions():
    with patch("src.main.SessionLocal", TestSession):
        yield


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "vision-platform-central"
    assert data["version"] == "0.1.0"
    assert "storage" in data
    assert "locals_count" in data


def test_status_endpoint():
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert data["central_id"] == "CENTRAL-001"
    assert data["version"] == "0.1.0"


def test_list_locals_empty():
    response = client.get("/api/v1/locals")
    assert response.status_code == 200
    data = response.json()
    assert data["locals"] == []


def test_list_observations_empty():
    response = client.get("/api/v1/observations")
    assert response.status_code == 200
    data = response.json()
    assert data["observations"] == []


def test_receive_observation():
    payload = {
        "observation_id": "obs_test_001",
        "camera_id": "CAM-001",
        "local_id": "LOCAL-001",
        "captured_at": "2026-08-17T12:00:00Z",
        "sha256": "abc123",
        "width": 1920,
        "height": 1080,
        "quality_score": 0.95,
        "algorithm_version": "capture-0.1.0",
    }
    response = client.post(
        "/api/v1/observations",
        json=payload,
        headers={"X-Api-Token": "change-me"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["observation_id"] == "obs_test_001"
    assert data["status"] == "received"


def test_receive_observation_duplicate():
    payload = {
        "observation_id": "obs_test_002",
        "local_id": "LOCAL-001",
        "camera_id": "CAM-001",
        "captured_at": "2026-08-17T12:00:00Z",
    }
    client.post(
        "/api/v1/observations",
        json=payload,
        headers={"X-Api-Token": "change-me"},
    )
    response = client.post(
        "/api/v1/observations",
        json=payload,
        headers={"X-Api-Token": "change-me"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "already_received"


def test_receive_observation_unauthorized():
    response = client.post("/api/v1/observations", json={"observation_id": "test"})
    assert response.status_code == 422


def test_receive_observation_missing_id():
    response = client.post(
        "/api/v1/observations",
        json={"local_id": "LOCAL-001"},
        headers={"X-Api-Token": "change-me"},
    )
    assert response.status_code == 400
