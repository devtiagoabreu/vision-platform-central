from datetime import datetime

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
    observation_id = Column(String, unique=True, nullable=False, index=True)
    local_id = Column(String, nullable=False)
    camera_id = Column(String, nullable=False)
    captured_at = Column(String, nullable=False)
    image_uri = Column(String, nullable=True)
    sha256 = Column(String, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    quality_score = Column(Float, nullable=True)
    algorithm_version = Column(String, nullable=True)
    status = Column(String, nullable=False, default="received")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
