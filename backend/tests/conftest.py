import os

# Inject dummy key for tests
os.environ["ENCRYPTION_KEY"] = "Trq2q8y5W7u7Q0p4R1v9S3x6Y8z2A4b6C8d0E2f4G6h="

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.common.database import Base, get_db
from backend.api.main import app

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Creates a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """Override the get_db dependency and patch the engine to use our test database."""
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    
    # Patch the engine so lifespan uses the test engine
    from unittest.mock import patch
    with patch("backend.common.database.engine", engine):
        with TestClient(app) as c:
            yield c
            
    app.dependency_overrides.clear()

from unittest.mock import patch

@pytest.fixture
def mock_playwright():
    with patch("backend.bot.common.base.sync_playwright") as mock:
        yield mock

@pytest.fixture
def mock_redis():
    with patch("backend.bot.common.base.redis.from_url") as mock:
        yield mock
