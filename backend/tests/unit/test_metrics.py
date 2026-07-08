"""Metrics registry unit tests."""
from app.core.metrics import MetricsRegistry


def test_records_request_increments():
    r = MetricsRegistry()
    r.record_request("GET", "/x", 200, 10.0)
    r.record_request("GET", "/x", 200, 20.0)
    r.record_request("GET", "/x", 500, 5.0)

    text = r.render()
    assert 'actap_http_requests_total{path="/x",method="GET",status="200"} 2' in text
    assert 'actap_http_requests_total{path="/x",method="GET",status="500"} 1' in text
    assert 'actap_http_errors_total{status="500"} 1' in text
    assert 'actap_http_request_duration_ms_sum{path="/x",method="GET"} 35.0' in text


def test_renders_uptime_gauge():
    r = MetricsRegistry()
    text = r.render()
    assert "actap_uptime_seconds" in text
    assert "actap_uptime_seconds " in text
