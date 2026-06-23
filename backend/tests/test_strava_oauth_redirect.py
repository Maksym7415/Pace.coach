"""Tests for Strava GET callback frontend redirect query params."""
from unittest.mock import MagicMock

import pytest
import requests
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.modules.third_party.strava.deps import get_strava_service

FRONTEND_REDIRECT = "http://localhost:5173/strava/oauth"
STATE = f"42|{FRONTEND_REDIRECT}"


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def _override_strava(client: TestClient, svc: MagicMock):
    app = client.app
    app.dependency_overrides[get_strava_service] = lambda: svc


def _clear_override(client: TestClient):
    client.app.dependency_overrides.pop(get_strava_service, None)


def _mock_svc(*, configured: bool = True) -> MagicMock:
    svc = MagicMock()
    svc.oauth.is_configured.return_value = configured
    return svc


def test_callback_success_redirects_with_connected(client):
    svc = _mock_svc()
    svc.exchange_code.return_value = MagicMock()
    _override_strava(client, svc)
    try:
        response = client.get(
            "/api/strava/callback",
            params={"code": "auth-code", "state": STATE},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == f"{FRONTEND_REDIRECT}?strava=connected"
    finally:
        _clear_override(client)


def test_callback_denied_when_no_code(client):
    svc = _mock_svc()
    _override_strava(client, svc)
    try:
        response = client.get(
            "/api/strava/callback",
            params={"state": STATE},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == f"{FRONTEND_REDIRECT}?strava=error&reason=denied"
    finally:
        _clear_override(client)


def test_callback_denied_when_strava_returns_error(client):
    svc = _mock_svc()
    _override_strava(client, svc)
    try:
        response = client.get(
            "/api/strava/callback",
            params={"state": STATE, "error": "access_denied"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == f"{FRONTEND_REDIRECT}?strava=error&reason=denied"
        svc.exchange_code.assert_not_called()
    finally:
        _clear_override(client)


def test_callback_exchange_failed_on_request_error(client):
    svc = _mock_svc()
    svc.exchange_code.side_effect = requests.RequestException("boom")
    _override_strava(client, svc)
    try:
        response = client.get(
            "/api/strava/callback",
            params={"code": "auth-code", "state": STATE},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert (
            response.headers["location"]
            == f"{FRONTEND_REDIRECT}?strava=error&reason=exchange_failed"
        )
    finally:
        _clear_override(client)


def test_callback_invalid_state_when_exchange_returns_none(client):
    svc = _mock_svc()
    svc.exchange_code.return_value = None
    _override_strava(client, svc)
    try:
        response = client.get(
            "/api/strava/callback",
            params={"code": "auth-code", "state": STATE},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert (
            response.headers["location"]
            == f"{FRONTEND_REDIRECT}?strava=error&reason=invalid_state"
        )
    finally:
        _clear_override(client)


def test_callback_not_configured_redirects_with_exchange_failed(client):
    svc = _mock_svc(configured=False)
    _override_strava(client, svc)
    try:
        response = client.get(
            "/api/strava/callback",
            params={"code": "auth-code", "state": STATE},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert (
            response.headers["location"]
            == f"{FRONTEND_REDIRECT}?strava=error&reason=exchange_failed"
        )
        svc.exchange_code.assert_not_called()
    finally:
        _clear_override(client)
