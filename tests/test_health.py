from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.storage.database import Base, LocalRecord, ObservationRecord, get_db

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


def _seed_observation(obs_id="obs_test_001", status="received", local_id="LOCAL-001"):
    db = TestSession()
    record = ObservationRecord(
        observation_id=obs_id,
        local_id=local_id,
        camera_id="CAM-001",
        captured_at="2026-08-17T12:00:00Z",
        sha256="abc123",
        width=800,
        height=600,
        quality_score=0.95,
        algorithm_version="capture-0.1.0",
        status=status,
    )
    db.add(record)
    db.commit()
    db.close()


def _seed_local(local_id="LOCAL-001", name="Test Local"):
    db = TestSession()
    loc = LocalRecord(
        local_id=local_id,
        local_name=name,
        api_url="http://192.168.1.100:8080",
        api_token="token123",
        status="active",
    )
    db.add(loc)
    db.commit()
    db.close()


class TestHealthEndpoint:
    def test_health_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "vision-platform-central"
        assert data["version"] == "0.1.0"

    def test_health_has_storage(self):
        response = client.get("/health")
        storage = response.json()["storage"]
        assert "free_bytes" in storage
        assert "total_bytes" in storage
        assert "queue_pending" in storage

    def test_health_counts_observations(self):
        _seed_received = _seed_observation("obs_pending", "received")
        response = client.get("/health")
        assert response.json()["storage"]["queue_pending"] == 1

    def test_health_counts_locals(self):
        _seed_local()
        response = client.get("/health")
        assert response.json()["locals_count"] == 1


class TestStatusEndpoint:
    def test_status(self):
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["central_id"] == "CENTRAL-001"
        assert data["version"] == "0.1.0"


class TestLocalsEndpoint:
    def test_list_locals_empty(self):
        response = client.get("/api/v1/locals")
        assert response.status_code == 200
        assert response.json()["locals"] == []

    def test_list_locals(self):
        _seed_local()
        response = client.get("/api/v1/locals")
        data = response.json()
        assert len(data["locals"]) == 1
        assert data["locals"][0]["local_id"] == "LOCAL-001"

    def test_register_local(self):
        response = client.post(
            "/api/v1/locals?local_id=L2&local_name=Local2&api_url=http://x&api_token=t",
            headers={"X-Api-Token": "change-me"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "registered"

    def test_register_local_unauthorized(self):
        response = client.post("/api/v1/locals?local_id=L2&local_name=L2&api_url=http://x&api_token=t")
        assert response.status_code == 422

    def test_register_local_update_existing(self):
        _seed_local()
        response = client.post(
            "/api/v1/locals?local_id=LOCAL-001&local_name=Updated&api_url=http://new&api_token=new",
            headers={"X-Api-Token": "change-me"},
        )
        assert response.status_code == 200

        db = TestSession()
        loc = db.query(LocalRecord).filter_by(local_id="LOCAL-001").first()
        assert loc.local_name == "Updated"
        assert loc.api_url == "http://new"
        db.close()


class TestObservationsEndpoint:
    def test_list_empty(self):
        response = client.get("/api/v1/observations")
        assert response.status_code == 200
        assert response.json()["observations"] == []

    def test_list_with_data(self):
        _seed_observation("obs1")
        _seed_observation("obs2", status="acknowledged")

        response = client.get("/api/v1/observations")
        assert len(response.json()["observations"]) == 2

    def test_filter_by_status(self):
        _seed_observation("obs1", "received")
        _seed_observation("obs2", "acknowledged")

        response = client.get("/api/v1/observations?status=received")
        data = response.json()
        assert len(data["observations"]) == 1
        assert data["observations"][0]["status"] == "received"

    def test_filter_by_local_id(self):
        _seed_observation("obs1", local_id="LOCAL-A")
        _seed_observation("obs2", local_id="LOCAL-B")

        response = client.get("/api/v1/observations?local_id=LOCAL-A")
        data = response.json()
        assert len(data["observations"]) == 1
        assert data["observations"][0]["local_id"] == "LOCAL-A"

    def test_limit(self):
        for i in range(5):
            _seed_observation(f"obs{i}")

        response = client.get("/api/v1/observations?limit=2")
        assert len(response.json()["observations"]) == 2


class TestReceiveObservation:
    def test_receive_success(self):
        payload = {
            "observation_id": "obs_new_001",
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
        assert data["observation_id"] == "obs_new_001"
        assert data["status"] == "received"

    def test_receive_duplicate(self):
        payload = {"observation_id": "obs_dup", "local_id": "LOCAL-001", "camera_id": "CAM-001", "captured_at": "x"}
        client.post("/api/v1/observations", json=payload, headers={"X-Api-Token": "change-me"})
        response = client.post("/api/v1/observations", json=payload, headers={"X-Api-Token": "change-me"})
        assert response.json()["status"] == "already_received"

    def test_receive_unauthorized(self):
        response = client.post("/api/v1/observations", json={"observation_id": "test"})
        assert response.status_code == 422

    def test_receive_missing_id(self):
        response = client.post(
            "/api/v1/observations",
            json={"local_id": "LOCAL-001"},
            headers={"X-Api-Token": "change-me"},
        )
        assert response.status_code == 400

    def test_receive_stores_correctly(self):
        payload = {
            "observation_id": "obs_stored",
            "local_id": "LOCAL-001",
            "camera_id": "CAM-001",
            "captured_at": "2026-08-17T12:00:00Z",
            "sha256": "abc123def",
            "width": 800,
            "height": 600,
            "quality_score": 0.9,
            "algorithm_version": "capture-0.1.0",
        }
        client.post("/api/v1/observations", json=payload, headers={"X-Api-Token": "change-me"})

        db = TestSession()
        obs = db.query(ObservationRecord).filter_by(observation_id="obs_stored").first()
        assert obs is not None
        assert obs.local_id == "LOCAL-001"
        assert obs.camera_id == "CAM-001"
        assert obs.sha256 == "abc123def"
        assert obs.status == "received"
        db.close()


class TestPollEndpoint:
    @patch("src.api.routes.collect_from_local")
    def test_poll_trigger(self, mock_collect):
        mock_collect.return_value = {
            "status": "ok",
            "observations_collected": 1,
            "observations_acked": 1,
        }

        response = client.post(
            "/api/v1/collector/poll",
            headers={"X-Api-Token": "change-me"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["observations_collected"] == 1
        mock_collect.assert_called_once()

    def test_poll_unauthorized(self):
        response = client.post("/api/v1/collector/poll")
        assert response.status_code == 422
