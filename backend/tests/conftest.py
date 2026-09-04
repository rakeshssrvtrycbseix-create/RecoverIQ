from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 (ensure models registered)
from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
from app.main import app

TEST_WEBHOOK_SECRET = "test_razorpay_secret_key_998877"


@pytest.fixture(scope="function")
def test_db_engine():
    """Create isolated in-memory SQLite engine with StaticPool."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign key support in SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_db_engine) -> Generator[Session, None, None]:
    """Provide a transactional SQLAlchemy session for testing."""
    session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_db_engine,
    )
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def test_settings() -> Settings:
    """Provide application settings with test webhook secret."""
    return Settings(
        database_url="sqlite:///:memory:",
        razorpay_webhook_secret=TEST_WEBHOOK_SECRET,
        finops_data_mode="demo",
    )


@pytest.fixture(scope="function")
def client(
    db_session: Session, test_settings: Settings
) -> Generator[TestClient, None, None]:
    """Provide a TestClient with database and settings dependencies overridden."""

    def override_get_db():
        yield db_session

    def override_get_settings():
        return test_settings

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = override_get_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
