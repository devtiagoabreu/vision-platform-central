from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from src.config.settings import settings

router = APIRouter()


class CentralStatusResponse(BaseModel):
    central_id: str
    central_name: str
    version: str


def verify_token(x_api_token: str = Header(...)):
    if x_api_token != settings.central_api_token:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/health")
async def health():
    return {"status": "ok", "service": "vision-platform-central", "version": "0.1.0"}


@router.get("/api/v1/status", response_model=CentralStatusResponse)
async def status():
    return CentralStatusResponse(
        central_id=settings.central_id,
        central_name=settings.central_name,
        version="0.1.0",
    )


@router.get("/api/v1/locals")
async def list_locals():
    # TODO: query database for registered locals
    return {"locals": []}


@router.get("/api/v1/observations")
async def list_observations():
    # TODO: implement with database query
    return {"observations": []}
