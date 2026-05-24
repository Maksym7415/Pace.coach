"""API contract smoke tests for React Native backward compatibility."""
import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app

client = TestClient(create_app())


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"success": True, "status": "ok"}


def test_register_validation():
    response = client.post("/api/auth/register", json={"email": "", "password": "", "name": ""})
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert "required" in body["error"]


def test_login_validation():
    response = client.post("/api/auth/login", json={"email": "", "password": ""})
    assert response.status_code == 400
    assert response.json()["success"] is False


def test_me_requires_auth():
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["success"] is False


def test_not_found_envelope():
    response = client.get("/api/nonexistent")
    assert response.status_code == 404
    assert response.json() == {"success": False, "error": "Endpoint not found"}


def test_strava_status_requires_auth():
    response = client.get("/api/strava/status")
    assert response.status_code == 401


def test_gear_list_requires_auth():
    response = client.get("/api/gear")
    assert response.status_code == 401
