from pathlib import Path

import psutil
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.auth.dependencies import get_current_user
from src.config.settings import settings
from src.storage.database import (
    DEVICE_TYPES,
    TASK_TYPES,
    DeviceRecord,
    LocalRecord,
    ObservationRecord,
    get_db,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _tmpl():
    from fastapi.templating import Jinja2Templates
    return Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")


def _require(request: Request):
    user = get_current_user(request)
    if user is None:
        return None, RedirectResponse(url="/login", status_code=302)
    return user, None


@router.get("", response_class=HTMLResponse)
async def dashboard_home(request: Request, db: Session = Depends(get_db)):
    user, redirect = _require(request)
    if redirect:
        return redirect

    total_cameras = db.query(
        ObservationRecord.camera_id
    ).distinct().count()

    total_obs = db.query(ObservationRecord).count()
    received = db.query(ObservationRecord).filter(
        ObservationRecord.status == "received"
    ).count()
    processed = db.query(ObservationRecord).filter(
        ObservationRecord.status == "processed"
    ).count()

    locals_active = db.query(LocalRecord).filter(
        LocalRecord.status == "active"
    ).count()
    locals_total = db.query(LocalRecord).count()

    latest = (
        db.query(ObservationRecord)
        .order_by(ObservationRecord.created_at.desc())
        .first()
    )

    return _tmpl().TemplateResponse(request, "dashboard.html", {
        "user": user,
        "page": "home",
        "central_id": settings.central_id,
        "central_name": settings.central_name,
        "total_cameras": total_cameras,
        "total_obs": total_obs,
        "received": received,
        "processed": processed,
        "locals_active": locals_active,
        "locals_total": locals_total,
        "latest": latest,
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
    })


@router.get("/locals", response_class=HTMLResponse)
async def locals_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = _require(request)
    if redirect:
        return redirect

    locals_list = db.query(LocalRecord).order_by(LocalRecord.created_at.desc()).all()
    return _tmpl().TemplateResponse(request, "locals.html", {
        "user": user,
        "page": "locals",
        "locals_list": locals_list,
    })


@router.post("/locals")
async def register_local_web(
    request: Request,
    local_id: str = Form(...),
    local_name: str = Form(...),
    api_url: str = Form(...),
    api_token: str = Form(...),
    db: Session = Depends(get_db),
):
    user, redirect = _require(request)
    if redirect:
        return redirect

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
    return RedirectResponse(url="/dashboard/locals", status_code=302)


@router.post("/locals/{local_id}/delete")
async def delete_local_web(
    request: Request,
    local_id: str,
    db: Session = Depends(get_db),
):
    user, redirect = _require(request)
    if redirect:
        return redirect

    record = db.query(LocalRecord).filter(LocalRecord.local_id == local_id).first()
    if record:
        db.delete(record)
        db.commit()
    return RedirectResponse(url="/dashboard/locals", status_code=302)


@router.get("/cameras", response_class=HTMLResponse)
async def cameras_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = _require(request)
    if redirect:
        return redirect

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

    return _tmpl().TemplateResponse(request, "cameras.html", {
        "user": user,
        "page": "cameras",
        "cameras": cameras,
    })


@router.get("/devices", response_class=HTMLResponse)
async def devices_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = _require(request)
    if redirect:
        return redirect

    devices = db.query(DeviceRecord).order_by(DeviceRecord.created_at.desc()).all()
    return _tmpl().TemplateResponse(request, "devices.html", {
        "user": user,
        "page": "devices",
        "devices": devices,
        "device_types": DEVICE_TYPES,
        "task_types": TASK_TYPES,
    })


@router.get("/observations", response_class=HTMLResponse)
async def observations_page(
    request: Request,
    status: str | None = None,
    local_id: str | None = None,
    db: Session = Depends(get_db),
):
    user, redirect = _require(request)
    if redirect:
        return redirect

    query = db.query(ObservationRecord)
    if status:
        query = query.filter(ObservationRecord.status == status)
    if local_id:
        query = query.filter(ObservationRecord.local_id == local_id)

    observations = (
        query.order_by(ObservationRecord.created_at.desc())
        .limit(100)
        .all()
    )

    locals_list = db.query(LocalRecord).all()

    return _tmpl().TemplateResponse(request, "observations.html", {
        "user": user,
        "page": "observations",
        "observations": observations,
        "current_status": status,
        "current_local_id": local_id,
        "locals_list": locals_list,
    })


@router.get("/observations/{observation_id}", response_class=HTMLResponse)
async def observation_detail(
    request: Request,
    observation_id: str,
    db: Session = Depends(get_db),
):
    user, redirect = _require(request)
    if redirect:
        return redirect

    obs = db.query(ObservationRecord).filter(
        ObservationRecord.observation_id == observation_id
    ).first()
    if obs is None:
        return RedirectResponse(url="/dashboard/observations", status_code=302)

    return _tmpl().TemplateResponse(request, "observation_detail.html", {
        "user": user,
        "page": "observations",
        "obs": obs,
    })


@router.get("/collector", response_class=HTMLResponse)
async def collector_page(request: Request):
    user, redirect = _require(request)
    if redirect:
        return redirect

    return _tmpl().TemplateResponse(request, "collector.html", {
        "user": user,
        "page": "collector",
        "collector_interval_ms": settings.collector_interval_ms,
    })


@router.post("/collector/poll")
async def collector_poll_web(request: Request, db: Session = Depends(get_db)):
    user, redirect = _require(request)
    if redirect:
        return redirect

    from src.collector.local_client import LocalClient
    from src.collector.sync import collect_from_local
    client = LocalClient()
    collect_from_local(client=client, db=db)
    return RedirectResponse(url="/dashboard/collector", status_code=302)


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    user, redirect = _require(request)
    if redirect:
        return redirect

    return _tmpl().TemplateResponse(request, "settings.html", {
        "user": user,
        "page": "settings",
        "central_id": settings.central_id,
        "central_name": settings.central_name,
        "central_api_token": settings.central_api_token,
        "collector_interval_ms": settings.collector_interval_ms,
    })


@router.get("/api/stats")
async def api_stats(db: Session = Depends(get_db)):
    total_obs = db.query(ObservationRecord).count()
    received = db.query(ObservationRecord).filter(
        ObservationRecord.status == "received"
    ).count()
    processed = db.query(ObservationRecord).filter(
        ObservationRecord.status == "processed"
    ).count()
    locals_active = db.query(LocalRecord).filter(
        LocalRecord.status == "active"
    ).count()
    return {
        "total_obs": total_obs,
        "received": received,
        "processed": processed,
        "locals_active": locals_active,
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
    }


@router.get("/api/locals-status")
async def api_locals_status(db: Session = Depends(get_db)):
    locals_list = db.query(LocalRecord).filter(LocalRecord.status == "active").all()
    return {
        "locals": [
            {
                "local_id": loc.local_id,
                "local_name": loc.local_name,
                "last_seen_at": loc.last_seen_at.isoformat() if loc.last_seen_at else None,
            }
            for loc in locals_list
        ]
    }
