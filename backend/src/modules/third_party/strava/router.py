"""Strava integration API routes."""
import logging
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests
from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from src.core.auth import CurrentUser, decode_token
from src.core.config import STRAVA_FRONTEND_REDIRECT_URL, STRAVA_WEBHOOK_VERIFY_TOKEN
from src.core.responses import error_json, success_json
from src.modules.third_party.strava.deps import get_strava_service
from src.modules.third_party.strava.service import StravaService
from src.modules.third_party.strava.webhook_handler import (
    process_activity_create,
    process_activity_update,
)

logger = logging.getLogger("coach_app.strava")

router = APIRouter(tags=["strava"])


def _get_redirect_uri(state: str | None, request_redirect_uri: str | None = None) -> str:
    """Resolve redirect_uri from state (user_id|redirect_uri), request args, or env."""
    redirect_uri = None
    if state and "|" in state:
        redirect_uri = state.split("|", 1)[1]
    redirect_uri = redirect_uri or request_redirect_uri or STRAVA_FRONTEND_REDIRECT_URL
    return redirect_uri


def _frontend_redirect_url(
    state: str | None,
    request_redirect_uri: str | None = None,
    *,
    outcome: str,
    reason: str | None = None,
) -> str:
    """Build frontend redirect URL with Strava OAuth outcome query params."""
    base = _get_redirect_uri(state, request_redirect_uri)
    parsed = urlparse(base)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["strava"] = outcome
    if reason:
        query["reason"] = reason
    return urlunparse(parsed._replace(query=urlencode(query)))


@router.get("/api/strava/connect")
def strava_connect(
    user: CurrentUser,
    redirect_uri: str | None = Query(None),
    svc: StravaService = Depends(get_strava_service),
):
    """Return OAuth URL for frontend to open in WebBrowser. Accepts redirect_uri query param."""
    if not svc.oauth.is_configured():
        raise error_json(503, "Strava is not configured.")
    try:
        url = svc.get_authorize_url(user.id, redirect_uri=redirect_uri)
        return success_json({"authorize_url": url})
    except Exception:
        logger.exception("Strava connect URL error")
        raise error_json(500, "Could not build Strava authorization URL.")


@router.get("/api/strava/authorize")
def strava_authorize(
    user: CurrentUser,
    redirect_uri: str | None = Query(None),
    svc: StravaService = Depends(get_strava_service),
):
    """Alias for /api/strava/connect."""
    return strava_connect(user=user, redirect_uri=redirect_uri, svc=svc)


@router.get("/api/strava/callback")
def strava_callback_get(
    request: Request,
    code: str | None = Query(None),
    state: str | None = Query(None),
    redirect_uri: str | None = Query(None),
    error: str | None = Query(None),
    svc: StravaService = Depends(get_strava_service),
):
    """OAuth callback via Strava redirect (GET)."""

    def redirect(outcome: str, reason: str | None = None) -> RedirectResponse:
        url = _frontend_redirect_url(state, redirect_uri, outcome=outcome, reason=reason)
        return RedirectResponse(url=url, status_code=302)

    if not svc.oauth.is_configured():
        return redirect("error", "exchange_failed")

    if error or not code:
        return redirect("error", "denied")

    try:
        us = svc.exchange_code(code, state)
    except requests.RequestException as exc:
        logger.warning("Strava token exchange failed: %s", exc)
        return redirect("error", "exchange_failed")
    except Exception:
        logger.exception("Strava callback error")
        return redirect("error", "exchange_failed")

    if not us:
        return redirect("error", "invalid_state")

    return redirect("connected")


@router.post("/api/strava/callback")
async def strava_callback_post(
    request: Request,
    authorization: str | None = Header(None),
    svc: StravaService = Depends(get_strava_service),
):
    """OAuth callback with JSON body and optional JWT (POST)."""
    if not svc.oauth.is_configured():
        raise error_json(503, "Strava is not configured.")

    payload: dict[str, Any] = {}
    try:
        payload = await request.json()
    except Exception:
        pass
    if not isinstance(payload, dict):
        payload = {}

    code = payload.get("code")
    state = payload.get("state")

    if not code:
        raise error_json(400, "Missing code.")

    if authorization and authorization.startswith("Bearer "):
        user_id = decode_token(authorization[7:])
        if user_id:
            state = str(user_id)

    try:
        us = svc.exchange_code(code, state)
    except requests.RequestException as exc:
        logger.warning("Strava token exchange failed: %s", exc)
        raise error_json(502, "Strava authorization failed. Please try again.")
    except Exception:
        logger.exception("Strava callback error")
        raise error_json(500, "Strava authorization failed. Please try again.")

    if not us:
        raise error_json(400, "Invalid or expired state.")

    return success_json({"athlete": {"id": us.strava_athlete_id}})


@router.post("/api/strava/disconnect")
def strava_disconnect(user: CurrentUser, svc: StravaService = Depends(get_strava_service)):
    """Remove Strava link for current user."""
    svc.disconnect(user.id)
    return success_json({})


@router.get("/api/strava/status")
def strava_status(user: CurrentUser, svc: StravaService = Depends(get_strava_service)):
    """Return per-user Strava connection status. 404 if not connected (401 only for app auth)."""
    connected = svc.has_connection(user.id)
    if not connected:
        raise error_json(404, "Strava not connected")
    athlete = svc.get_connection_info(user.id)
    return success_json(
        {
            "configured": svc.oauth.is_configured(),
            "connected": True,
            "athlete": athlete,
        }
    )


@router.get("/api/webhooks/strava")
def strava_webhook_verify(
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
):
    """Strava subscription verification: respond with hub.challenge."""
    if not STRAVA_WEBHOOK_VERIFY_TOKEN:
        return JSONResponse(status_code=503, content={"error": "Webhook not configured"})
    if hub_verify_token != STRAVA_WEBHOOK_VERIFY_TOKEN:
        logger.info("Strava webhook verify rejected (bad or missing token)")
        return JSONResponse(status_code=403, content={"error": "Invalid verify token"})
    if hub_challenge is None:
        return JSONResponse(status_code=400, content={"error": "Missing hub.challenge"})
    return JSONResponse(status_code=200, content={"hub.challenge": hub_challenge})


@router.post("/api/webhooks/strava")
async def strava_webhook_event(request: Request):
    """Handle Strava webhook events. Respond 200 quickly, process async."""
    data: dict[str, Any] = {}
    try:
        body = await request.json()
        if isinstance(body, dict):
            data = body
    except Exception:
        pass
    if not data:
        form = await request.form()
        data = dict(form)

    if not data:
        logger.info("Received empty Strava webhook payload")
        return JSONResponse(status_code=200, content={"ok": True})

    aspect_type = data.get("aspect_type")
    object_type = data.get("object_type")
    owner_id = data.get("owner_id")
    object_id = data.get("object_id")

    if not aspect_type or not object_type or not owner_id or not object_id:
        logger.warning(
            "Invalid Strava webhook payload: %s",
            {k: data.get(k) for k in ("aspect_type", "object_type", "owner_id", "object_id")},
        )
        return JSONResponse(status_code=200, content={"ok": True})

    if aspect_type == "create" and object_type == "activity":
        try:
            process_activity_create(int(owner_id), int(object_id))
        except (ValueError, TypeError):
            pass

    if aspect_type == "update" and object_type == "activity":
        updates = data.get("updates") or {}
        if "title" in updates:
            try:
                process_activity_update(int(owner_id), int(object_id), updates)
            except (ValueError, TypeError):
                pass

    return JSONResponse(status_code=200, content={"ok": True})
