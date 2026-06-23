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
    response = client.post(
        "/api/auth/register",
        json={"username": "", "email": "", "password": "", "name": ""},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert "required" in body["error"]


def test_register_requires_username():
    response = client.post(
        "/api/auth/register",
        json={"email": "x@example.com", "password": "password123", "name": "X"},
    )
    assert response.status_code == 400


def test_register_invalid_username_format():
    response = client.post(
        "/api/auth/register",
        json={
            "username": "bad user",
            "email": "x@example.com",
            "password": "password123",
            "name": "X",
        },
    )
    assert response.status_code == 400


def test_register_reserved_username():
    response = client.post(
        "/api/auth/register",
        json={
            "username": "admin",
            "email": "x@example.com",
            "password": "password123",
            "name": "X",
        },
    )
    assert response.status_code == 400


def test_login_validation():
    response = client.post("/api/auth/login", json={"identifier": "", "password": ""})
    assert response.status_code == 400
    assert response.json()["success"] is False


def test_login_with_username():
    client.post(
        "/api/auth/register",
        json={
            "username": "logintest1",
            "email": "lt1@example.com",
            "password": "password1234",
            "name": "LT",
        },
    )
    response = client.post(
        "/api/auth/login",
        json={"identifier": "logintest1", "password": "password1234"},
    )
    assert response.status_code == 200
    assert "token" in response.json()


def test_login_with_email():
    client.post(
        "/api/auth/register",
        json={
            "username": "logintest2",
            "email": "lt2@example.com",
            "password": "password1234",
            "name": "LT2",
        },
    )
    response = client.post(
        "/api/auth/login",
        json={"identifier": "lt2@example.com", "password": "password1234"},
    )
    assert response.status_code == 200
    assert "token" in response.json()


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


def test_activities_list_requires_auth():
    response = client.get("/api/activities")
    assert response.status_code == 401


def test_activities_list_invalid_date_range():
    client.post(
        "/api/auth/register",
        json={
            "username": "actlist1",
            "email": "actlist1@example.com",
            "password": "password1234",
            "name": "Act",
        },
    )
    login = client.post(
        "/api/auth/login",
        json={"identifier": "actlist1", "password": "password1234"},
    )
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/activities?start_date=2026-06-30&end_date=2026-06-01",
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["success"] is False
    assert "start_date" in response.json()["error"]

    response = client.get(
        "/api/activities?start_date=2024-01-01&end_date=2026-01-01",
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["success"] is False
    assert "365" in response.json()["error"]
