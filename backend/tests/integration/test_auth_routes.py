"""Integration tests for authentication routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.models.schemas_db import User


class TestAuthRegister:
    """Test user registration endpoint."""

    def test_register_success(self, client: TestClient):
        """Test successful user registration."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "securepass123",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert data["full_name"] == "New User"
        assert data["role"] == "user"
        assert "hashed_password" not in data

    def test_register_duplicate_username(self, client: TestClient):
        """Test registration with duplicate username."""
        # Register first user
        client.post(
            "/api/auth/register",
            json={
                "username": "duplicate",
                "email": "first@example.com",
                "password": "pass123",
            },
        )

        # Try to register with same username
        response = client.post(
            "/api/auth/register",
            json={
                "username": "duplicate",
                "email": "second@example.com",
                "password": "pass456",
            },
        )
        assert response.status_code == 400
        assert "Username already registered" in response.json()["message"]

    def test_register_duplicate_email(self, client: TestClient):
        """Test registration with duplicate email."""
        # Register first user
        client.post(
            "/api/auth/register",
            json={
                "username": "user1",
                "email": "same@example.com",
                "password": "pass123",
            },
        )

        # Try to register with same email
        response = client.post(
            "/api/auth/register",
            json={
                "username": "user2",
                "email": "same@example.com",
                "password": "pass456",
            },
        )
        assert response.status_code == 400
        assert "Email already registered" in response.json()["message"]

    def test_register_missing_fields(self, client: TestClient):
        """Test registration with missing required fields."""
        response = client.post(
            "/api/auth/register",
            json={"username": "incomplete"},
        )
        assert response.status_code == 422  # Validation error


class TestAuthLogin:
    """Test user login endpoint."""

    def test_login_success(self, client: TestClient):
        """Test successful login."""
        # Register user first
        client.post(
            "/api/auth/register",
            json={
                "username": "loginuser",
                "email": "login@example.com",
                "password": "correctpass",
            },
        )

        # Login
        response = client.post(
            "/api/auth/login",
            json={
                "username": "loginuser",
                "password": "correctpass",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient):
        """Test login with wrong password."""
        # Register user first
        client.post(
            "/api/auth/register",
            json={
                "username": "wrongpass",
                "email": "wrong@example.com",
                "password": "correctpass",
            },
        )

        # Login with wrong password
        response = client.post(
            "/api/auth/login",
            json={
                "username": "wrongpass",
                "password": "wrongpass",
            },
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["message"]

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with nonexistent user."""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "nonexistent",
                "password": "anypass",
            },
        )
        assert response.status_code == 401


class TestAuthMe:
    """Test user profile endpoints."""

    def test_get_me_authenticated(self, client: TestClient):
        """Test getting user profile with valid token."""
        # Register and login
        client.post(
            "/api/auth/register",
            json={
                "username": "profileuser",
                "email": "profile@example.com",
                "password": "pass123",
                "full_name": "Profile User",
            },
        )
        login_resp = client.post(
            "/api/auth/login",
            json={
                "username": "profileuser",
                "password": "pass123",
            },
        )
        token = login_resp.json()["access_token"]

        # Get profile
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "profileuser"
        assert data["full_name"] == "Profile User"

    def test_get_me_unauthenticated(self, client: TestClient):
        """Test getting user profile without token."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client: TestClient):
        """Test getting user profile with invalid token."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_update_me_full_name(self, client: TestClient):
        """Test updating user's full name."""
        # Register and login
        client.post(
            "/api/auth/register",
            json={
                "username": "updateuser",
                "email": "update@example.com",
                "password": "pass123",
                "full_name": "Old Name",
            },
        )
        login_resp = client.post(
            "/api/auth/login",
            json={
                "username": "updateuser",
                "password": "pass123",
            },
        )
        token = login_resp.json()["access_token"]

        # Update profile
        response = client.put(
            "/api/auth/me?full_name=New Name",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "New Name"

    def test_update_me_email(self, client: TestClient):
        """Test updating user's email."""
        # Register and login
        client.post(
            "/api/auth/register",
            json={
                "username": "emailuser",
                "email": "old@example.com",
                "password": "pass123",
            },
        )
        login_resp = client.post(
            "/api/auth/login",
            json={
                "username": "emailuser",
                "password": "pass123",
            },
        )
        token = login_resp.json()["access_token"]

        # Update email
        response = client.put(
            "/api/auth/me?email=new@example.com",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "new@example.com"

    def test_update_me_duplicate_email(self, client: TestClient):
        """Test updating email to one that's already taken."""
        # Register two users
        client.post(
            "/api/auth/register",
            json={
                "username": "user1",
                "email": "user1@example.com",
                "password": "pass123",
            },
        )
        client.post(
            "/api/auth/register",
            json={
                "username": "user2",
                "email": "user2@example.com",
                "password": "pass123",
            },
        )
        login_resp = client.post(
            "/api/auth/login",
            json={
                "username": "user1",
                "password": "pass123",
            },
        )
        token = login_resp.json()["access_token"]

        # Try to update to user2's email
        response = client.put(
            "/api/auth/me?email=user2@example.com",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "Email already registered" in response.json()["message"]
