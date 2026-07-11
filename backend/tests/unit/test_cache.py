"""Tests for cache module."""

from __future__ import annotations

from app.data.cache import clear_all, get_cache_stats, get_cached, invalidate_source, set_cached


class TestCache:
    def test_set_and_get(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        # Reload to pick up new DATA_DIR
        import app.data.cache as cache_mod

        monkeypatch.setattr(cache_mod, "CACHE_DB_PATH", str(tmp_path / "api_cache.db"))

        set_cached("test_key", "test_source", {"data": 123}, ttl_hours=1)
        result = get_cached("test_key")
        assert result == {"data": 123}

    def test_get_missing_key(self, tmp_path, monkeypatch):
        import app.data.cache as cache_mod

        monkeypatch.setattr(cache_mod, "CACHE_DB_PATH", str(tmp_path / "api_cache.db"))

        result = get_cached("nonexistent_key_xyz")
        assert result is None

    def test_clear_all(self, tmp_path, monkeypatch):
        import app.data.cache as cache_mod

        monkeypatch.setattr(cache_mod, "CACHE_DB_PATH", str(tmp_path / "api_cache.db"))

        set_cached("key1", "src", "value1", ttl_hours=1)
        set_cached("key2", "src", "value2", ttl_hours=1)
        clear_all()
        assert get_cached("key1") is None
        assert get_cached("key2") is None

    def test_set_with_short_ttl(self, tmp_path, monkeypatch):
        import app.data.cache as cache_mod

        monkeypatch.setattr(cache_mod, "CACHE_DB_PATH", str(tmp_path / "api_cache.db"))

        set_cached("short_ttl", "src", "data", ttl_hours=0.0001)  # very short TTL
        get_cached("short_ttl")
        # might or might not be expired depending on timing

    def test_invalidate_source(self, tmp_path, monkeypatch):
        import app.data.cache as cache_mod

        monkeypatch.setattr(cache_mod, "CACHE_DB_PATH", str(tmp_path / "api_cache.db"))

        set_cached("k1", "source_a", "v1", ttl_hours=1)
        set_cached("k2", "source_b", "v2", ttl_hours=1)
        invalidate_source("source_a")
        assert get_cached("k1") is None
        assert get_cached("k2") == "v2"

    def test_get_cache_stats(self, tmp_path, monkeypatch):
        import app.data.cache as cache_mod

        monkeypatch.setattr(cache_mod, "CACHE_DB_PATH", str(tmp_path / "api_cache.db"))

        set_cached("k1", "src1", "v1", ttl_hours=1)
        set_cached("k2", "src1", "v2", ttl_hours=1)
        set_cached("k3", "src2", "v3", ttl_hours=1)
        stats = get_cache_stats()
        assert stats["total_entries"] == 3
        assert stats["by_source"]["src1"] == 2
        assert stats["by_source"]["src2"] == 1
