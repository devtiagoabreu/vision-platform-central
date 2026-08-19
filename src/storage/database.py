from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.config.settings import settings

engine = create_engine(settings.central_db_url, echo=False)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


DEVICE_TYPES = ["camera", "sensor", "other"]
TASK_TYPES = ["fissure", "ppe", "fabric_quality", "structural"]


class ObservationRecord(Base):
    __tablename__ = "image_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    observation_id = Column(String(128), unique=True, nullable=False, index=True)
    local_id = Column(String(64), nullable=False, index=True)
    camera_id = Column(String(64), nullable=False, index=True)
    captured_at = Column(String, nullable=False)
    image_uri = Column(String, nullable=True)
    sha256 = Column(String(64), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    quality_score = Column(Float, nullable=True)
    algorithm_version = Column(String(32), nullable=True)
    status = Column(String(32), nullable=False, default="received", index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    processed_at = Column(DateTime, nullable=True)


class LocalRecord(Base):
    __tablename__ = "locals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    local_id = Column(String(64), unique=True, nullable=False, index=True)
    local_name = Column(String(128), nullable=False)
    api_url = Column(String(256), nullable=False)
    api_token = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False, default="active")
    last_seen_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))


class DeviceRecord(Base):
    __tablename__ = "device_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), nullable=False, index=True)
    local_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    device_type = Column(String(32), nullable=False, default="camera")
    task_type = Column(String(32), nullable=False, default="fissure")
    is_active = Column(Boolean, nullable=False, default=True)
    last_seen_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC),
                        onupdate=lambda: datetime.now(UTC))


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(32), nullable=False, default="admin")
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
