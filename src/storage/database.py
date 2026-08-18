from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.config.settings import settings

engine = create_engine(settings.central_db_url, echo=False)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
