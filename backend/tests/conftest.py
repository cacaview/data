"""Shared pytest fixtures.

Provides:
- in-memory SQLite test DB with schema creation
- FastAPI TestClient bound to the test DB
- per-test app instance (avoids cross-test state)
- sample data fixtures for trade records, countries, etc.
"""

from __future__ import annotations

import os
import warnings
from collections.abc import Iterator

# Suppress multipart PendingDeprecationWarning before FastAPI import
warnings.filterwarnings("ignore", category=PendingDeprecationWarning, module="multipart")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

# Force test DB before any app imports
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DATA_DIR", "/tmp/actap-test")
os.environ.setdefault("API_KEY", "")
os.environ.setdefault("CORS_ORIGINS", "*")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "10000")
os.environ.setdefault("RATE_LIMIT_STRICT_PER_MINUTE", "10000")

import contextlib  # noqa: E402

from app.models import database as _database  # noqa: E402
from app.models.schemas_db import (  # noqa: E402
    Base,
    Country,
    TradeRecord,
)


@pytest.fixture(scope="function")
def engine(monkeypatch):
    """Per-test in-memory SQLite engine.

    Uses URI form `sqlite:///:memory:` (per-test fresh in-memory DB) so
    test isolation is guaranteed. Patches both `app.models.database.engine`
    AND `SessionLocal` so the module-level `get_db` dependency used by
    routes binds to the same in-memory DB the fixtures write to.
    """
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Share a single connection so all queries see the same in-memory DB
    )
    test_session_local = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=test_engine)
    monkeypatch.setattr(_database, "engine", test_engine)
    monkeypatch.setattr(_database, "SessionLocal", test_session_local)
    try:
        yield test_engine
    finally:
        Base.metadata.drop_all(bind=test_engine)
        # StaticPool holds a single raw sqlite3.Connection; dispose() alone
        # does not close it, leading to a ResourceWarning under Python 3.13.
        test_engine.pool.dispose()
        # Eagerly close the underlying DBAPI connection.
        try:
            conn = test_engine.pool._creator()
        except Exception:
            conn = None
        if conn is not None:
            with contextlib.suppress(Exception):
                conn.close()
        test_engine.dispose()


@pytest.fixture(scope="function")
def session(engine) -> Iterator:
    """Yield a SQLAlchemy session bound to the test engine."""
    Session = sessionmaker(bind=engine)
    s = Session()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture(scope="function")
def sample_countries(session) -> list[Country]:
    """Insert 3 sample countries and return them."""
    countries = [
        Country(
            code="VNM",
            name_cn="越南",
            name_en="Vietnam",
            asean_member=1,
            rcep_member=1,
            gdp_billion_usd=400.0,
            population_million=98.0,
            latitude=14.0,
            longitude=108.0,
        ),
        Country(
            code="THA",
            name_cn="泰国",
            name_en="Thailand",
            asean_member=1,
            rcep_member=1,
            gdp_billion_usd=500.0,
            population_million=70.0,
            latitude=15.0,
            longitude=100.0,
        ),
        Country(
            code="IDN",
            name_cn="印度尼西亚",
            name_en="Indonesia",
            asean_member=1,
            rcep_member=1,
            gdp_billion_usd=1300.0,
            population_million=275.0,
            latitude=-5.0,
            longitude=120.0,
        ),
    ]
    for c in countries:
        session.add(c)
    session.commit()
    return countries


@pytest.fixture(scope="function")
def sample_trade_records(session, sample_countries) -> list[TradeRecord]:
    """Insert 24 months of trade data across 3 partners."""
    records = []
    for year in (2023, 2024):
        for month in range(1, 13):
            for idx, c in enumerate(sample_countries):
                base = 1_000_000 * (idx + 1)
                seasonal = 1.1 if month in (3, 6, 9) else 1.0
                records.append(
                    TradeRecord(
                        year=year,
                        month=month,
                        reporter="CHN",
                        partner=c.code,
                        hs_code="854232",
                        hs_chapter=85,
                        hs_section="XVI",
                        trade_value_usd=base * seasonal,
                        quantity=base / 100,
                        unit="kg",
                        trade_flow="export",
                        source="test",
                    )
                )
    for r in records:
        session.add(r)
    session.commit()
    return records


@pytest.fixture(scope="function")
def sample_tariff_rules(session, sample_countries) -> list:
    """Insert sample tariff rules for testing cost optimizer."""
    from app.models.schemas_db import TariffRule

    rules = []
    for c in sample_countries:
        rules.append(
            TariffRule(
                hs_code="854232",
                partner_country=c.code,
                mfn_rate=10.0,
                rcep_rate=5.0,
                fta_rate=3.0,
                rule_of_origin="WO",
            )
        )
    for r in rules:
        session.add(r)
    session.commit()
    return rules


@pytest.fixture(scope="function")
def client(engine, monkeypatch) -> Iterator[TestClient]:
    """FastAPI TestClient with the test DB injected via monkeypatch.

    The `engine` fixture patches `app.models.database.engine` and
    `SessionLocal` so the module-level `get_db` dependency used by
    routes binds to the same in-memory DB the fixtures write to.
    """
    from app.main import app as real_app
    from app.models import database as db_mod

    # Build a session factory bound to the (possibly monkeypatched) engine.
    TestSession = sessionmaker(bind=db_mod.engine, autocommit=False, autoflush=False)

    def _override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    # Avoid running init_database() on startup (lifespan calls
    # `app.mock_data.init_db.init_database`); we don't want a fresh mock
    # dataset to wipe the test fixtures' rows. The lazy import inside
    # `app.main` resolves the attribute on the module at call time, so
    # patching `init_db.init_database` is enough.
    from app.mock_data import init_db as init_mod

    monkeypatch.setattr(init_mod, "init_database", lambda: None)

    real_app.dependency_overrides[db_mod.get_db] = _override_get_db

    with TestClient(real_app) as c:
        yield c

    real_app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _reset_structlog_context():
    """Clear structlog contextvars between tests to avoid leakage."""
    import structlog

    structlog.contextvars.clear_contextvars()
    yield
    structlog.contextvars.clear_contextvars()


@pytest.fixture(scope="session", autouse=True)
def _close_global_engine():
    """Dispose the module-level engine that `app.models.database` creates
    on import. Without this, pytest's interpreter shutdown raises a
    ResourceWarning about an unclosed sqlite3.Connection."""
    yield
    try:
        from app.models import database as _db

        _db.engine.pool.dispose()
        # NullPool/StaticPool still hold the raw DBAPI connection.
        try:
            conn = _db.engine.pool._creator()
            if conn is not None:
                conn.close()
        except Exception:
            pass
        _db.engine.dispose()
    except Exception:
        pass
