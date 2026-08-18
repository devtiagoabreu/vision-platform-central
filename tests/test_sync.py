from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.collector.sync import collect_from_local
from src.storage.database import Base, ObservationRecord

TEST_DB_URL = "sqlite:///test_sync.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=test_engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def _make_obs(obs_id="obs_001"):
    return {
        "observation_id": obs_id,
        "camera_id": "CAM-001",
        "local_id": "LOCAL-001",
        "captured_at": "2026-08-17T12:00:00Z",
        "sha256": "abc123",
        "width": 800,
        "height": 600,
        "quality_score": 0.9,
        "algorithm_version": "capture-0.1.0",
        "file_path": "/tmp/obs.jpg",
    }


class TestCollectFromLocal:
    def test_local_unreachable(self):
        db = TestSession()
        client = MagicMock()
        client.health.return_value = None

        result = collect_from_local(client=client, db=db)
        assert result["status"] == "error"
        assert "unreachable" in result["message"].lower()
        db.close()

    def test_collect_new_observations(self):
        db = TestSession()
        client = MagicMock()
        client.health.return_value = {"status": "ok"}
        client.list_observations.return_value = {
            "observations": [_make_obs("obs1"), _make_obs("obs2")]
        }
        client.ack_observation.return_value = True

        result = collect_from_local(client=client, db=db)
        assert result["status"] == "ok"
        assert result["observations_collected"] == 2
        assert result["observations_acked"] == 2

        records = db.query(ObservationRecord).all()
        assert len(records) == 2
        assert all(r.status == "acknowledged" for r in records)
        db.close()

    def test_collect_empty(self):
        db = TestSession()
        client = MagicMock()
        client.health.return_value = {"status": "ok"}
        client.list_observations.return_value = {"observations": []}

        result = collect_from_local(client=client, db=db)
        assert result["observations_collected"] == 0
        db.close()

    def test_collect_skips_duplicate(self):
        db = TestSession()
        existing = ObservationRecord(
            observation_id="obs_dup",
            local_id="LOCAL-001",
            camera_id="CAM-001",
            captured_at="2026-08-17T12:00:00Z",
            status="received",
        )
        db.add(existing)
        db.commit()

        client = MagicMock()
        client.health.return_value = {"status": "ok"}
        client.list_observations.return_value = {
            "observations": [_make_obs("obs_dup")]
        }

        result = collect_from_local(client=client, db=db)
        assert result["observations_collected"] == 0
        db.close()

    def test_collect_ack_failure(self):
        db = TestSession()
        client = MagicMock()
        client.health.return_value = {"status": "ok"}
        client.list_observations.return_value = {
            "observations": [_make_obs("obs_noack")]
        }
        client.ack_observation.return_value = False

        result = collect_from_local(client=client, db=db)
        assert result["observations_collected"] == 1
        assert result["observations_acked"] == 0

        record = db.query(ObservationRecord).filter_by(observation_id="obs_noack").first()
        assert record.status == "received"
        db.close()

    def test_collect_skips_missing_id(self):
        db = TestSession()
        client = MagicMock()
        client.health.return_value = {"status": "ok"}
        client.list_observations.return_value = {
            "observations": [{"camera_id": "CAM-001"}]
        }

        result = collect_from_local(client=client, db=db)
        assert result["observations_collected"] == 0
        db.close()

    def test_collect_no_ack_if_already_received(self):
        db = TestSession()
        existing = ObservationRecord(
            observation_id="obs_existing",
            local_id="LOCAL-001",
            camera_id="CAM-001",
            captured_at="2026-08-17T12:00:00Z",
            status="acknowledged",
        )
        db.add(existing)
        db.commit()

        client = MagicMock()
        client.health.return_value = {"status": "ok"}
        client.list_observations.return_value = {
            "observations": [_make_obs("obs_existing")]
        }

        result = collect_from_local(client=client, db=db)
        assert result["observations_collected"] == 0
        client.ack_observation.assert_not_called()
        db.close()
