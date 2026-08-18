from fastapi.testclient import TestClient

from src.storage.database import LocalRecord, ObservationRecord
from tests.conftest import TestSession

TOKEN = {"X-Api-Token": "change-me"}


class TestE2EReceiveFlow:
    def test_receive_and_query(self, client: TestClient):
        payload = {
            "observation_id": "obs_e2e_001",
            "camera_id": "CAM-001",
            "local_id": "LOCAL-001",
            "captured_at": "2026-08-18T12:00:00Z",
            "sha256": "abc123def456",
            "width": 1920,
            "height": 1080,
            "quality_score": 0.95,
            "algorithm_version": "capture-0.1.0",
        }

        resp = client.post("/api/v1/observations", json=payload, headers=TOKEN)
        assert resp.status_code == 200
        data = resp.json()
        assert data["observation_id"] == "obs_e2e_001"
        assert data["status"] == "received"

        resp = client.get("/api/v1/observations")
        obs = resp.json()["observations"][0]
        assert obs["observation_id"] == "obs_e2e_001"
        assert obs["local_id"] == "LOCAL-001"
        assert obs["camera_id"] == "CAM-001"
        assert obs["sha256"] == "abc123def456"

    def test_receive_duplicate_is_idempotent(self, client: TestClient):
        payload = {
            "observation_id": "obs_dup_e2e",
            "local_id": "LOCAL-001",
            "camera_id": "CAM-001",
            "captured_at": "2026-08-18T12:00:00Z",
        }

        resp1 = client.post("/api/v1/observations", json=payload, headers=TOKEN)
        resp2 = client.post("/api/v1/observations", json=payload, headers=TOKEN)
        assert resp1.json()["status"] == "received"
        assert resp2.json()["status"] == "already_received"

        db = TestSession()
        count = db.query(ObservationRecord).filter_by(observation_id="obs_dup_e2e").count()
        assert count == 1
        db.close()


class TestE2ECollectorFlow:
    def test_poll_collects_and_stores(self, client: TestClient):
        from unittest.mock import patch

        with patch("src.api.routes.collect_from_local") as mock_collect:
            mock_collect.return_value = {
                "status": "ok",
                "observations_collected": 2,
                "observations_acked": 2,
            }
            resp = client.post("/api/v1/collector/poll", headers=TOKEN)
            assert resp.status_code == 200
            assert resp.json()["observations_collected"] == 2
            mock_collect.assert_called_once()

    def test_health_reflects_received_count(self, client: TestClient):
        db = TestSession()
        for i in range(3):
            obs = ObservationRecord(
                observation_id=f"obs_pending_{i}",
                local_id="LOCAL-001",
                camera_id="CAM-001",
                captured_at="2026-08-18T12:00:00Z",
                status="received",
            )
            db.add(obs)
        db.commit()
        db.close()

        resp = client.get("/health")
        assert resp.json()["storage"]["queue_pending"] == 3


class TestE2ELocalsFlow:
    def test_register_and_query_local(self, client: TestClient):
        resp = client.post(
            "/api/v1/locals?local_id=L1&local_name=OrangePi&api_url=http://192.168.1.10:8080&api_token=tok123",
            headers=TOKEN,
        )
        assert resp.status_code == 200

        resp = client.get("/api/v1/locals")
        locals_list = resp.json()["locals"]
        assert len(locals_list) == 1
        assert locals_list[0]["local_id"] == "L1"
        assert locals_list[0]["local_name"] == "OrangePi"

    def test_register_updates_existing(self, client: TestClient):
        client.post(
            "/api/v1/locals?local_id=L1&local_name=V1&api_url=http://x&api_token=t",
            headers=TOKEN,
        )
        client.post(
            "/api/v1/locals?local_id=L1&local_name=V2&api_url=http://y&api_token=t2",
            headers=TOKEN,
        )

        resp = client.get("/api/v1/locals")
        assert len(resp.json()["locals"]) == 1

        db = TestSession()
        loc = db.query(LocalRecord).filter_by(local_id="L1").first()
        assert loc.local_name == "V2"
        assert loc.api_url == "http://y"
        db.close()

    def test_health_counts_active_locals(self, client: TestClient):
        client.post(
            "/api/v1/locals?local_id=L1&local_name=Local1&api_url=http://x&api_token=t",
            headers=TOKEN,
        )
        client.post(
            "/api/v1/locals?local_id=L2&local_name=Local2&api_url=http://y&api_token=t",
            headers=TOKEN,
        )

        resp = client.get("/health")
        assert resp.json()["locals_count"] == 2


class TestE2EFilterFlow:
    def test_filter_by_status_and_local(self, client: TestClient):
        for i, (status, local) in enumerate([
            ("received", "L1"),
            ("received", "L2"),
            ("acknowledged", "L1"),
        ]):
            db = TestSession()
            obs = ObservationRecord(
                observation_id=f"obs_filter_{i}",
                local_id=local,
                camera_id="CAM-001",
                captured_at="2026-08-18T12:00:00Z",
                status=status,
            )
            db.add(obs)
            db.commit()
            db.close()

        resp = client.get("/api/v1/observations?status=received")
        assert len(resp.json()["observations"]) == 2

        resp = client.get("/api/v1/observations?local_id=L1")
        assert len(resp.json()["observations"]) == 2

        resp = client.get("/api/v1/observations?status=acknowledged&local_id=L1")
        assert len(resp.json()["observations"]) == 1
