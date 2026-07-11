"""Tests for authentication service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.ai.auth_service import (
    ALGORITHM,
    SECRET_KEY,
    _truncate_password,
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
)


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_get_password_hash_returns_string(self):
        result = get_password_hash("testpassword")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_password_hash_different_each_time(self):
        """Hashing same password should produce different hashes (due to salt)."""
        hash1 = get_password_hash("testpassword")
        hash2 = get_password_hash("testpassword")
        assert hash1 != hash2

    def test_verify_password_correct(self):
        password = "securepassword123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        hashed = get_password_hash("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_empty(self):
        hashed = get_password_hash("password")
        assert verify_password("", hashed) is False

    def test_truncate_password_short(self):
        """Short password should not be truncated."""
        password = "short"
        result = _truncate_password(password)
        assert result == password

    def test_truncate_password_long(self):
        """Password longer than 72 bytes should be truncated."""
        password = "a" * 100
        result = _truncate_password(password)
        assert len(result.encode("utf-8")) <= 72

    def test_truncate_password_unicode(self):
        """Unicode password should be truncated correctly."""
        password = "中" * 50  # Each Chinese char is 3 bytes in UTF-8
        result = _truncate_password(password)
        assert len(result.encode("utf-8")) <= 72


class TestTokenCreation:
    """Test JWT token creation."""

    def test_create_access_token_returns_string(self):
        token = create_access_token({"sub": "testuser"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_contains_data(self):
        token = create_access_token({"sub": "testuser"})
        payload = decode_token(token)
        assert payload["sub"] == "testuser"

    def test_create_access_token_has_expiry(self):
        token = create_access_token({"sub": "testuser"})
        payload = decode_token(token)
        assert "exp" in payload

    def test_create_access_token_custom_expiry(self):
        custom_delta = timedelta(hours=2)
        token = create_access_token({"sub": "testuser"}, expires_delta=custom_delta)
        payload = decode_token(token)
        assert "exp" in payload

    def test_create_access_token_default_expiry(self):
        token = create_access_token({"sub": "testuser"})
        payload = decode_token(token)
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        # Default expiry should be ~24 hours from now
        assert exp_time > now + timedelta(hours=23)
        assert exp_time < now + timedelta(hours=25)


class TestTokenDecoding:
    """Test JWT token decoding."""

    def test_decode_token_valid(self):
        token = create_access_token({"sub": "testuser", "role": "admin"})
        payload = decode_token(token)
        assert payload["sub"] == "testuser"
        assert payload["role"] == "admin"

    def test_decode_token_invalid(self):
        with pytest.raises(Exception):
            decode_token("invalid.token.here")

    def test_decode_token_expired(self):
        # Create a token that expired 1 hour ago
        expired_delta = timedelta(hours=-1)
        token = create_access_token({"sub": "testuser"}, expires_delta=expired_delta)
        with pytest.raises(Exception):
            decode_token(token)
