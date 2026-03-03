"""Pytest fixtures. Set test env before importing app so config and DB use in-memory SQLite."""
import os
import sys

import pytest

# File-based test DB so all connections/threads share the same DB (unlike :memory:)
_test_db = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_poordad.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db}"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["SQL_ECHO"] = "false"

# Import app after env is set
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import create_db_and_tables, engine
from main import app
from sqlmodel import Session


@pytest.fixture
def db_schema():
    """Create a fresh DB per test to avoid stale pooled connections."""
    engine.dispose()
    if os.path.exists(_test_db):
        os.remove(_test_db)
    create_db_and_tables()
    yield
    engine.dispose()
    if os.path.exists(_test_db):
        os.remove(_test_db)


@pytest.fixture
def client(db_schema):
    """TestClient with app; DB tables exist."""
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c


@pytest.fixture
def session(db_schema):
    """Database session for inserting test data."""
    with Session(engine) as session:
        yield session
