"""API key authentication integration tests."""
import os
import pytest


@pytest.fixture
def client_with_auth(monkeypatch, engine):
    """Client with API_KEY set in environment."""
    monkeypatch.setenv("API_KEY", "test-secret-key-12345")
    # Re-import settings (rebuild)
    from app.core.config import Settings
    monkeypatch.setattr("app.core.config.settings",
                        Settings(API_KEY="test-secret-key-12345",
                                 CORS_ORIGINS="*",
                                 API_KEY_PROTECTED_PATHS="/api/datasources/refresh"))

    from sqlalchemy.orm import sessionmaker
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    from app.models import database as db_mod
    from app.main import app as real_app
    from app.mock_data import init_db as init_mod

    original_engine = db_mod.engine
    original_session = db_mod.SessionLocal
    db_mod.engine = engine
    db_mod.SessionLocal = TestSession
    monkeypatch.setattr(init_mod, "init_database", lambda: None)

    def _override():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    real_app.dependency_overrides[db_mod.get_db] = _override
    from fastapi.testclient import TestClient
    with TestClient(real_app) as c:
        yield c
    real_app.dependency_overrides.clear()
    db_mod.engine = original_engine
    db_mod.SessionLocal = original_session


def test_health_endpoint_no_auth_required(client_with_auth):
    r = client_with_auth.get("/api/health")
    assert r.status_code == 200


def test_protected_endpoint_without_key_returns_401(client_with_auth):
    r = client_with_auth.post("/api/datasources/refresh")
    assert r.status_code == 401
    body = r.json()
    assert body["error_code"] == "AUTH_MISSING_API_KEY"


def test_protected_endpoint_with_wrong_key_returns_403(client_with_auth):
    r = client_with_auth.post(
        "/api/datasources/refresh",
        headers={"X-API-Key": "wrong-key"},
    )
    assert r.status_code == 403
    body = r.json()
    assert body["error_code"] == "AUTH_INVALID_API_KEY"


def test_protected_endpoint_with_correct_key_passes(client_with_auth):
    r = client_with_auth.post(
        "/api/datasources/refresh",
        headers={"X-API-Key": "test-secret-key-12345"},
    )
    # Should NOT be 401 or 403; can be 200/204 or 500 (if external fails)
    assert r.status_code not in (401, 403)
