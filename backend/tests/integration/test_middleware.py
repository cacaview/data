"""Middleware integration tests through HTTP."""


def test_rate_limit_headers_present(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert "X-RateLimit-Limit" in r.headers
    assert "X-RateLimit-Remaining" in r.headers


def test_validation_error_returns_422_with_request_id(client):
    r = client.get("/api/trade/ranking?type=bogus")
    assert r.status_code == 422
    body = r.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "request_id" in body
    assert "details" in body
    # Each detail should have a field+type+message
    for d in body["details"]:
        assert "field" in d
        assert "type" in d
        assert "message" in d


def test_404_returns_error_code(client):
    r = client.get("/api/no-such-endpoint")
    assert r.status_code == 404


def test_cors_headers_on_response(client):
    r = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    # CORS middleware should set allow-origin
    assert r.headers.get("access-control-allow-origin") in ("*", "http://localhost:3000")


def test_options_preflight_cors(client):
    r = client.options(
        "/api/trade/trend",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Preflight should succeed (200/204)
    assert r.status_code in (200, 204)
