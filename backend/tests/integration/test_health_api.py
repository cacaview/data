"""Health endpoints integration tests."""
import pytest


def test_health_endpoint_returns_200(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_health_includes_request_id_header(client):
    r = client.get("/api/health")
    assert "X-Request-ID" in r.headers
    assert len(r.headers["X-Request-ID"]) > 0


def test_health_request_id_echoed_when_provided(client):
    r = client.get("/api/health", headers={"X-Request-ID": "my-custom-id-123"})
    assert r.headers["X-Request-ID"] == "my-custom-id-123"


def test_readiness_checks_database(client):
    r = client.get("/api/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert "checks" in body
    assert "database" in body["checks"]


def test_metrics_endpoint_returns_prometheus_text(client):
    """Calling /metrics after some traffic should return Prometheus format."""
    # Generate some traffic
    client.get("/api/health")
    client.get("/api/health")

    r = client.get("/api/metrics")
    assert r.status_code == 200
    text = r.text
    assert "actap_uptime_seconds" in text
    assert "actap_http_requests_total" in text
    # /health is in there
    assert 'path="/api/health"' in text


def test_response_includes_timing_header(client):
    r = client.get("/api/health")
    assert "X-Response-Time-Ms" in r.headers
    ms = float(r.headers["X-Response-Time-Ms"])
    assert ms >= 0
