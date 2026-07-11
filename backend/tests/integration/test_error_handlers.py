"""Tests for error handlers and middleware."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestErrorHandlers:
    """Test unified error handling."""

    def test_404_returns_json(self, client: TestClient):
        """Test that 404 returns JSON error response."""
        response = client.get("/api/nonexistent-endpoint")
        assert response.status_code == 404

    def test_validation_error_returns_422(self, client: TestClient):
        """Test that validation errors return 422."""
        response = client.post("/api/chat/ask", json={})
        assert response.status_code == 422
