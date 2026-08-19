from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.main import app
from src.storage.database import Base, get_db

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine)


@pytest.fixture(autouse=True)
def _setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def _override_get_db():
    def _get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _patch_sessions():
    with patch("src.main.SessionLocal", TestSession), \
         patch("src.main.create_tables"), \
         patch("src.auth.router.SessionLocal", TestSession), \
         patch("src.auth.dependencies.SessionLocal", TestSession), \
         patch("src.auth.router.settings") as mock_auth_settings, \
         patch("src.auth.dependencies.settings") as mock_dep_settings:
        for s in (mock_auth_settings, mock_dep_settings):
            s.jwt_secret_key = "test-secret-key"
            s.jwt_expire_hours = 24
            s.admin_username = "admin"
            s.admin_password = "admin"
        yield


@pytest.fixture
def client():
    return TestClient(app)
