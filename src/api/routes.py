import shutil

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.collector.local_client import LocalClient
from src.collector.sync import collect_from_local
from src.config.settings import settings
from src.storage.database import LocalRecord, ObservationRecord, get_db

router = APIRouter()


class CentralStatusResponse(BaseModel):
    central_id: str
    central_name: str
    version: str


def verify_token(x_api_token: str = Header(...)):
    if x_api_token != settings.central_api_token:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/health")
async def health(db: Session = Depends(get_db)):
    try:
        disk = shutil.disk_usage("/")
        free_bytes, total_bytes = disk.free, disk.total
    except Exception:
        free_bytes, total_bytes = 0, 0

    queue_pending = db.query(ObservationRecord).filter(
        ObservationRecord.status == "received"
    ).count()

    locals_count = db.query(LocalRecord).filter(
        LocalRecord.status == "active"
    ).count()

    return {
        "status": "ok",
        "service": "vision-platform-central",
        "version": "0.1.0",
        "storage": {
            "free_bytes": free_bytes,
            "total_bytes": total_bytes,
            "queue_pending": queue_pending,
        },
        "locals_count": locals_count,
    }


@router.get("/api/v1/status", response_model=CentralStatusResponse)
async def status():
    return CentralStatusResponse(
        central_id=settings.central_id,
        central_name=settings.central_name,
        version="0.1.0",
    )


@router.get("/api/v1/locals")
async def list_locals(db: Session = Depends(get_db)):
    locals_records = db.query(LocalRecord).filter(LocalRecord.status == "active").all()
    return {
        "locals": [
            {
                "local_id": loc.local_id,
                "local_name": loc.local_name,
                "api_url": loc.api_url,
                "status": loc.status,
                "last_seen_at": loc.last_seen_at.isoformat() if loc.last_seen_at else None,
            }
            for loc in locals_records
        ]
    }


@router.post("/api/v1/locals")
async def register_local(
    local_id: str = Query(...),
    local_name: str = Query(...),
    api_url: str = Query(...),
    api_token: str = Query(...),
    token: str = Depends(verify_token),
    db: Session = Depends(get_db),
):
    existing = db.query(LocalRecord).filter(LocalRecord.local_id == local_id).first()
    if existing:
        existing.local_name = local_name
        existing.api_url = api_url
        existing.api_token = api_token
    else:
        record = LocalRecord(
            local_id=local_id,
            local_name=local_name,
            api_url=api_url,
            api_token=api_token,
        )
        db.add(record)
    db.commit()
    return {"local_id": local_id, "status": "registered"}


@router.post("/api/v1/observations")
async def receive_observation(payload: dict, token: str = Depends(verify_token), db: Session = Depends(get_db)):
    observation_id = payload.get("observation_id")
    if not observation_id:
        raise HTTPException(status_code=400, detail="observation_id is required")

    existing = db.query(ObservationRecord).filter(
        ObservationRecord.observation_id == observation_id
    ).first()
    if existing:
        return {"observation_id": observation_id, "status": "already_received"}

    record = ObservationRecord(
        observation_id=observation_id,
        local_id=payload.get("local_id", ""),
        camera_id=payload.get("camera_id", ""),
        captured_at=payload.get("captured_at", ""),
        sha256=payload.get("sha256", ""),
        width=payload.get("width"),
        height=payload.get("height"),
        quality_score=payload.get("quality_score"),
        algorithm_version=payload.get("algorithm_version", ""),
        status="received",
    )
    db.add(record)
    db.commit()
    return {"observation_id": observation_id, "status": "received"}


@router.get("/api/v1/observations")
async def list_observations(
    status_filter: str | None = Query(None, alias="status"),
    local_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(ObservationRecord)

    if status_filter:
        query = query.filter(ObservationRecord.status == status_filter)
    if local_id:
        query = query.filter(ObservationRecord.local_id == local_id)

    observations = (
        query.order_by(ObservationRecord.created_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "observations": [
            {
                "observation_id": obs.observation_id,
                "local_id": obs.local_id,
                "camera_id": obs.camera_id,
                "captured_at": obs.captured_at,
                "sha256": obs.sha256,
                "width": obs.width,
                "height": obs.height,
                "quality_score": obs.quality_score,
                "algorithm_version": obs.algorithm_version,
                "status": obs.status,
                "created_at": obs.created_at.isoformat(),
            }
            for obs in observations
        ]
    }


@router.post("/api/v1/collector/poll")
async def poll_local(token: str = Depends(verify_token), db: Session = Depends(get_db)):
    client = LocalClient()
    result = collect_from_local(client=client, db=db)
    return result


@router.get("/api/v1/cameras")
async def list_cameras(db: Session = Depends(get_db)):
    rows = (
        db.query(
            ObservationRecord.camera_id,
            ObservationRecord.local_id,
        )
        .distinct()
        .all()
    )

    cameras = []
    for camera_id, local_id in rows:
        count = db.query(ObservationRecord).filter(
            ObservationRecord.camera_id == camera_id
        ).count()
        cameras.append({
            "camera_id": camera_id,
            "local_id": local_id,
            "observation_count": count,
        })

    return {"cameras": cameras}
