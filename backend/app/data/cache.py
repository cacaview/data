"""SQLite-based cache for API responses.

Avoids redundant API calls and provides offline fallback.
Each data source has its own cache table with TTL support.
"""
import json
import sqlite3
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Any

logger = logging.getLogger(__name__)

CACHE_DB_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "api_cache.db"))
DEFAULT_TTL_HOURS = 24  # Cache entries valid for 24 hours by default


def _get_conn() -> sqlite3.Connection:
    """Get a connection to the cache database."""
    cache_dir = os.path.dirname(CACHE_DB_PATH)
    os.makedirs(cache_dir, exist_ok=True)
    conn = sqlite3.connect(CACHE_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_cache (
            cache_key TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            metadata TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_cache_source ON api_cache(source)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_cache_expires ON api_cache(expires_at)
    """)
    conn.commit()
    return conn


def get_cached(cache_key: str) -> Optional[dict]:
    """Retrieve cached data if it exists and hasn't expired.

    Args:
        cache_key: Unique key for this cache entry

    Returns:
        Cached data as dict, or None if missing/expired
    """
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT data, expires_at FROM api_cache WHERE cache_key = ?",
            (cache_key,)
        ).fetchone()
        if row is None:
            return None

        expires_at = datetime.fromisoformat(row[1])
        if datetime.utcnow() > expires_at:
            # Expired — delete and return None
            conn.execute("DELETE FROM api_cache WHERE cache_key = ?", (cache_key,))
            conn.commit()
            logger.debug("Cache expired for key: %s", cache_key)
            return None

        logger.debug("Cache hit for key: %s", cache_key)
        return json.loads(row[0])
    finally:
        conn.close()


def set_cached(cache_key: str, source: str, data: Any, ttl_hours: float = DEFAULT_TTL_HOURS, metadata: Optional[dict] = None):
    """Store data in the cache.

    Args:
        cache_key: Unique key for this cache entry
        source: Data source identifier (e.g., 'comtrade', 'worldbank')
        data: Data to cache (will be JSON-serialized)
        ttl_hours: Time-to-live in hours
        metadata: Optional metadata about the cached data
    """
    conn = _get_conn()
    try:
        now = datetime.utcnow()
        expires = now + timedelta(hours=ttl_hours)
        conn.execute(
            """INSERT OR REPLACE INTO api_cache
               (cache_key, source, data, created_at, expires_at, metadata)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                cache_key,
                source,
                json.dumps(data, ensure_ascii=False, default=str),
                now.isoformat(),
                expires.isoformat(),
                json.dumps(metadata, ensure_ascii=False) if metadata else None,
            )
        )
        conn.commit()
        logger.debug("Cached %s bytes for key: %s", len(json.dumps(data)), cache_key)
    finally:
        conn.close()


def invalidate_source(source: str):
    """Invalidate all cached data from a specific source.

    Args:
        source: Data source identifier to invalidate
    """
    conn = _get_conn()
    try:
        count = conn.execute("DELETE FROM api_cache WHERE source = ?", (source,)).rowcount
        conn.commit()
        logger.info("Invalidated %d cache entries for source: %s", count, source)
    finally:
        conn.close()


def clear_all():
    """Clear the entire cache database."""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM api_cache")
        conn.commit()
        logger.info("Cache cleared completely")
    finally:
        conn.close()


def get_cache_stats() -> dict:
    """Get cache statistics."""
    conn = _get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM api_cache").fetchone()[0]
        sources = conn.execute(
            "SELECT source, COUNT(*) FROM api_cache GROUP BY source"
        ).fetchall()
        return {
            "total_entries": total,
            "by_source": {s[0]: s[1] for s in sources},
        }
    finally:
        conn.close()
