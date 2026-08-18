import logging

from sqlalchemy.orm import Session

from src.collector.local_client import LocalClient
from src.storage.database import ObservationRecord

logger = logging.getLogger(__name__)


def collect_from_local(client: LocalClient | None = None, db: Session | None = None) -> dict:
    client = client or LocalClient()
    health = client.health()
    if health is None:
        return {"status": "error", "message": "Local unreachable"}

    data = client.list_observations()
    observations = data.get("observations", [])
    collected = 0
    acked = 0

    for obs in observations:
        observation_id = obs.get("observation_id")
        if not observation_id:
            continue

        existing = db.query(ObservationRecord).filter(
            ObservationRecord.observation_id == observation_id
        ).first()
        if existing:
            continue

        record = ObservationRecord(
            observation_id=observation_id,
            local_id=obs.get("local_id", ""),
            camera_id=obs.get("camera_id", ""),
            captured_at=obs.get("captured_at", ""),
            image_uri=obs.get("file_path", ""),
            sha256=obs.get("sha256", ""),
            width=obs.get("width", 0),
            height=obs.get("height", 0),
            quality_score=obs.get("quality_score", 0),
            algorithm_version=obs.get("algorithm_version", ""),
            status="received",
        )
        db.add(record)
        collected += 1

        if client.ack_observation(observation_id):
            record.status = "acknowledged"
            acked += 1

    db.commit()

    return {
        "status": "ok",
        "observations_collected": collected,
        "observations_acked": acked,
    }
