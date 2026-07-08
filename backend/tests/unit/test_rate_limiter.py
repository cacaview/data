"""Rate limiter unit tests."""

from app.middleware.rate_limit import IPRateLimiter


def test_allows_under_limit():
    lim = IPRateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        assert lim.is_allowed("1.2.3.4")[0] is True


def test_blocks_over_limit():
    lim = IPRateLimiter(max_requests=2, window_seconds=60)
    lim.is_allowed("1.2.3.4")
    lim.is_allowed("1.2.3.4")
    allowed, remaining = lim.is_allowed("1.2.3.4")
    assert allowed is False
    assert remaining == 0


def test_independent_per_ip():
    lim = IPRateLimiter(max_requests=1, window_seconds=60)
    assert lim.is_allowed("a")[0] is True
    assert lim.is_allowed("a")[0] is False
    # b is unaffected
    assert lim.is_allowed("b")[0] is True


def test_window_expires():
    lim = IPRateLimiter(max_requests=1, window_seconds=0)
    # With 0-second window, every call should be allowed (entry expires immediately)
    import time

    lim.is_allowed("x")
    time.sleep(0.01)
    # Window=0 means cutoff = now - 0 = now; entry is at < now so dropped
    assert lim.is_allowed("x")[0] is True
