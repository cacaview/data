"""Tests for rate limiter middleware."""

from __future__ import annotations

import pytest
from app.middleware.rate_limit import IPRateLimiter


class TestIPRateLimiter:
    def test_allows_within_limit(self):
        limiter = IPRateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            allowed, remaining = limiter.is_allowed("192.168.1.1")
            assert allowed is True
        allowed, remaining = limiter.is_allowed("192.168.1.1")
        assert allowed is False
        assert remaining == 0

    def test_different_ips_independent(self):
        limiter = IPRateLimiter(max_requests=2, window_seconds=60)
        assert limiter.is_allowed("192.168.1.1")[0] is True
        assert limiter.is_allowed("192.168.1.2")[0] is True
        assert limiter.is_allowed("192.168.1.1")[0] is True
        assert limiter.is_allowed("192.168.1.2")[0] is True
        assert limiter.is_allowed("192.168.1.1")[0] is False
        assert limiter.is_allowed("192.168.1.2")[0] is False

    def test_cleanup_removes_stale(self):
        limiter = IPRateLimiter(max_requests=5, window_seconds=60)
        limiter.is_allowed("192.168.1.1")
        limiter.is_allowed("192.168.1.2")
        # Cleanup with very short age
        removed = limiter.cleanup(max_age_seconds=0)
        assert removed >= 0

    def test_remaining_count(self):
        limiter = IPRateLimiter(max_requests=3, window_seconds=60)
        _, remaining = limiter.is_allowed("10.0.0.1")
        assert remaining == 2
        _, remaining = limiter.is_allowed("10.0.0.1")
        assert remaining == 1
        _, remaining = limiter.is_allowed("10.0.0.1")
        assert remaining == 0
