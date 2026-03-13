#!/usr/bin/env python3
"""
Flask REST API for Shoe Tracker
"""
from datetime import datetime, timedelta, timezone
import os
import secrets
import sys
from pathlib import Path

import bcrypt
import requests
from flask import Flask, jsonify, request, redirect
from sqlalchemy import func
from flask_cors import CORS

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.config import DATABASE_URL, STRAVA_FRONTEND_REDIRECT_URL
from src.models import (
    db,
    User,
    UserStrava,
    Shoe,
    Activity,
    ActivityShoeDistance,
    Gear,
    GearInstallation,
    GearService,
    GearServiceLog,
    ActivityGearUsage,
)
from src.auth import create_token, require_auth
from src.services.strava_service import StravaService
from src.services.webhook_handler import process_activity_create, process_activity_update
from src.config import STRAVA_WEBHOOK_VERIFY_TOKEN

# Create Flask app
app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["STRAVA_FRONTEND_REDIRECT"] = STRAVA_FRONTEND_REDIRECT_URL

db.init_app(app)


def _round_km(value, default=0.0):
    """Round distance to 2 decimal places for DB storage. Returns default for None or invalid."""
    if value is None:
        return default
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return default


def _user_to_json(user, strava_connected=None):
    """JSON for user. strava_connected passed separately to avoid extra query when known."""
    out = {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "preferred_distance_unit": getattr(user, "preferred_distance_unit", None) or "km",
    }
    if strava_connected is not None:
        out["strava_connected"] = strava_connected
    return out


# --- Health ---

@app.route("/api/health", methods=["GET"])
def health():
    """Health check."""
    return jsonify({"success": True, "status": "ok"})


# --- Auth ---

@app.route("/api/auth/register", methods=["POST"])
def register():
    """Register a new user."""
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    name = (data.get("name") or "").strip()

    if not email or not password or not name:
        return jsonify({"success": False, "error": "email, password, and name are required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "error": "Email already registered"}), 409

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(email=email, password_hash=password_hash, name=name)
    db.session.add(user)
    db.session.commit()

    token = create_token(user.id)
    return jsonify({
        "success": True,
        "token": token,
        "user": _user_to_json(user),
    }), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    """Login and return JWT."""
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or not password:
        return jsonify({"success": False, "error": "email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
        return jsonify({"success": False, "error": "Invalid email or password"}), 401

    token = create_token(user.id)
    return jsonify({
        "success": True,
        "token": token,
        "user": _user_to_json(user),
    })


@app.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():
    """Request password reset. Stores token in DB (email sending optional)."""
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"success": False, "error": "email is required"}), 400

    user = User.query.filter_by(email=email).first()
    if user:
        user.password_reset_token = secrets.token_urlsafe(32)
        user.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        db.session.commit()
        # TODO: Send email with reset link (e.g. /reset?token=...)

    return jsonify({"success": True, "message": "If the email exists, a reset link was sent"})


@app.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    """Reset password with token."""
    data = request.get_json() or {}
    token = (data.get("token") or "").strip()
    new_password = data.get("new_password")

    if not token or not new_password:
        return jsonify({"success": False, "error": "token and new_password are required"}), 400

    user = User.query.filter_by(password_reset_token=token).first()
    if not user:
        return jsonify({"success": False, "error": "Invalid or expired reset token"}), 400
    if user.password_reset_expires_at and user.password_reset_expires_at < datetime.now(timezone.utc):
        return jsonify({"success": False, "error": "Reset token has expired"}), 400

    user.password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user.password_reset_token = None
    user.password_reset_expires_at = None
    db.session.commit()

    return jsonify({"success": True, "message": "Password reset successfully"})


@app.route("/api/auth/me", methods=["GET"])
@require_auth
def me():
    """Return current user."""
    user = request.user
    strava_connected = UserStrava.query.filter_by(user_id=user.id).first() is not None
    u = _user_to_json(user, strava_connected=strava_connected)
    return jsonify({"success": True, "user": u})


@app.route("/api/auth/profile", methods=["PUT"])
@require_auth
def update_profile():
    """Update name, avatar, and/or preferred_distance_unit (km|miles)."""
    user = request.user
    data = request.get_json() or {}
    if "name" in data and data["name"] is not None:
        user.name = str(data["name"]).strip() or user.name
    if "avatar_url" in data and data["avatar_url"] is not None:
        user.avatar_url = str(data["avatar_url"]).strip() or None
    if "preferred_distance_unit" in data and data["preferred_distance_unit"] is not None:
        unit = str(data["preferred_distance_unit"]).strip().lower()
        if unit in ("km", "miles"):
            user.preferred_distance_unit = unit
    db.session.commit()
    return jsonify({"success": True, "user": _user_to_json(user)})


# --- Strava ---

def _strava_service():
    return StravaService(db.session)


@app.route("/api/strava/connect", methods=["GET"])
@require_auth
def strava_connect():
    """Return OAuth URL for frontend to open in WebBrowser. Accepts redirect_uri query param."""
    svc = _strava_service()
    if not svc.oauth.is_configured():
        return jsonify({"success": False, "error": "Strava is not configured."}), 503
    redirect_uri = request.args.get("redirect_uri")
    try:
        url = svc.get_authorize_url(request.user.id, redirect_uri=redirect_uri)
        return jsonify({"success": True, "authorize_url": url})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/strava/authorize", methods=["GET"])
@require_auth
def strava_authorize():
    """Alias for /api/strava/connect."""
    return strava_connect()


def _get_redirect_uri(state: str | None) -> str:
    """Resolve redirect_uri from state (user_id|redirect_uri), request args, or env."""
    redirect_uri = None
    if state and "|" in state:
        redirect_uri = state.split("|", 1)[1]
    redirect_uri = redirect_uri or request.args.get("redirect_uri") or app.config["STRAVA_FRONTEND_REDIRECT"]
    return redirect_uri


@app.route("/api/strava/callback", methods=["GET", "POST"])
def strava_callback():
    """OAuth callback: exchange code, store tokens. GET: state=user_id from Strava redirect. POST: code + JWT."""
    svc = _strava_service()
    if not svc.oauth.is_configured():
        if request.method == "GET":
            return redirect(_get_redirect_uri(None))
        return jsonify({"success": False, "error": "Strava is not configured."}), 503

    payload = request.get_json(silent=True) or {}
    code = payload.get("code") or request.args.get("code")
    state = payload.get("state") or request.args.get("state")

    if not code:
        if request.method == "GET":
            return redirect(_get_redirect_uri(state))
        return jsonify({"success": False, "error": "Missing code."}), 400

    # POST with JWT: user from auth header
    if request.method == "POST":
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            from src.auth import decode_token
            user_id = decode_token(auth_header[7:])
            if user_id:
                state = str(user_id)

    try:
        us = svc.exchange_code(code, state)
    except requests.RequestException as exc:
        if request.method == "GET":
            return redirect(_get_redirect_uri(state))
        return jsonify({"success": False, "error": str(exc)}), 502
    except Exception as exc:
        if request.method == "GET":
            return redirect(_get_redirect_uri(state))
        return jsonify({"success": False, "error": str(exc)}), 500

    if not us:
        if request.method == "GET":
            return redirect(_get_redirect_uri(state))
        return jsonify({"success": False, "error": "Invalid or expired state."}), 400

    if request.method == "GET":
        return redirect(_get_redirect_uri(state))

    return jsonify({
        "success": True,
        "athlete": {"id": us.strava_athlete_id},
    })


@app.route("/api/strava/disconnect", methods=["POST"])
@require_auth
def strava_disconnect():
    """Remove Strava link for current user."""
    svc = _strava_service()
    svc.disconnect(request.user.id)
    return jsonify({"success": True})


@app.route("/api/strava/status", methods=["GET"])
@require_auth
def strava_status():
    """Return per-user Strava connection status. 404 if not connected (401 only for app auth)."""
    svc = _strava_service()
    connected = svc.has_connection(request.user.id)
    if not connected:
        return jsonify({"success": False, "error": "Strava not connected"}), 404
    athlete = svc.get_connection_info(request.user.id)
    return jsonify({
        "success": True,
        "configured": svc.oauth.is_configured(),
        "connected": True,
        "athlete": athlete,
    })


# --- Gear helpers ---

def _gear_to_json(g, components_count=None):
    """JSON for gear (any type). components_count: optional, number of installed components (for list)."""
    out = {
        "id": g.id,
        "activity_type": g.activity_type,
        "gear_type": g.gear_type,
        "brand": g.brand,
        "model": g.model,
        "nick": g.nick,
        "metric_type": g.metric_type,
        "max_value": g.max_value,
        "value_covered": g.value_covered,
        "is_default": g.is_default,
        "status": g.status,
        "created_at": g.created_at.isoformat() if g.created_at else None,
    }
    if components_count is not None:
        out["components_count"] = components_count
    return out


def _gear_to_shoe_json(g):
    """JSON for gear as shoe (backward compat for /api/shoes)."""
    return {
        "id": g.id,
        "activity_type": g.activity_type,
        "brand": g.brand,
        "model": g.model,
        "nick": g.nick,
        "max_distance_km": g.max_value,
        "distance_covered_km": g.value_covered,
        "is_default": g.is_default,
        "created_at": g.created_at.isoformat() if g.created_at else None,
    }


def _recompute_gear_value_covered(gear_id):
    """Set gear.value_covered to sum of ActivityGearUsage.value for this gear."""
    gear = Gear.query.get(gear_id)
    if not gear:
        return
    total = db.session.query(func.coalesce(func.sum(ActivityGearUsage.value), 0)).filter_by(
        gear_id=gear_id
    ).scalar()
    gear.value_covered = round(float(total), 2)


def _recompute_shoe_distance_covered(shoe_id):
    """Legacy: Set shoe.distance_covered_km. Prefer _recompute_gear_value_covered for gear."""
    shoe = Shoe.query.get(shoe_id)
    if not shoe:
        return
    total = db.session.query(func.coalesce(func.sum(ActivityShoeDistance.distance_km), 0)).filter_by(
        shoe_id=shoe_id
    ).scalar()
    shoe.distance_covered_km = round(float(total), 2)


# --- Shoes (legacy API: delegates to gear with gear_type='shoe') ---

def _get_shoes_query():
    return Gear.query.filter_by(user_id=request.user.id, gear_type="shoe").order_by(Gear.created_at.desc())


@app.route("/api/shoes", methods=["GET"])
@require_auth
def list_shoes():
    """List current user's shoes (gear with gear_type='shoe')."""
    shoes = _get_shoes_query().all()
    return jsonify({"success": True, "shoes": [_gear_to_shoe_json(s) for s in shoes]})


@app.route("/api/shoes", methods=["POST"])
@require_auth
def create_shoe():
    """Create a new shoe (gear with gear_type='shoe')."""
    data = request.get_json() or {}
    activity_type_raw = (data.get("activity_type") or "").strip() or "running"
    activity_type = "run" if activity_type_raw.lower() in ("run", "running") else activity_type_raw.lower() or "run"
    brand = (data.get("brand") or "").strip()
    model = (data.get("model") or "").strip()
    nick = (data.get("nick") or "").strip() or None
    max_distance_km = data.get("max_distance_km")
    if max_distance_km is not None:
        try:
            max_distance_km = round(float(max_distance_km), 2)
        except (TypeError, ValueError):
            max_distance_km = None
    distance_covered_km = _round_km(data.get("distance_covered_km"), 0.0)

    if not brand or not model:
        return jsonify({"success": False, "error": "brand and model are required"}), 400

    gear = Gear(
        user_id=request.user.id,
        activity_type=activity_type,
        gear_type="shoe",
        brand=brand,
        model=model,
        nick=nick,
        metric_type="distance",
        max_value=max_distance_km,
        value_covered=0.0,
        is_default=False,
        status="active",
    )
    db.session.add(gear)
    db.session.flush()
    if distance_covered_km and distance_covered_km > 0:
        db.session.add(
            ActivityGearUsage(activity_id=None, gear_id=gear.id, value=distance_covered_km)
        )
        db.session.flush()
        _recompute_gear_value_covered(gear.id)
    db.session.commit()
    return jsonify({"success": True, "shoe": _gear_to_shoe_json(gear)}), 201


@app.route("/api/shoes/<int:shoe_id>", methods=["GET"])
@require_auth
def get_shoe(shoe_id):
    """Get a single shoe (gear with gear_type='shoe')."""
    shoe = Gear.query.filter_by(id=shoe_id, user_id=request.user.id, gear_type="shoe").first()
    if not shoe:
        return jsonify({"success": False, "error": "Shoe not found"}), 404
    return jsonify({"success": True, "shoe": _gear_to_shoe_json(shoe)})


@app.route("/api/shoes/<int:shoe_id>", methods=["PUT"])
@require_auth
def update_shoe(shoe_id):
    """Update a shoe (gear with gear_type='shoe')."""
    shoe = Gear.query.filter_by(id=shoe_id, user_id=request.user.id, gear_type="shoe").first()
    if not shoe:
        return jsonify({"success": False, "error": "Shoe not found"}), 404

    data = request.get_json() or {}
    if "activity_type" in data:
        at = str(data["activity_type"]).strip() or "run"
        shoe.activity_type = "run" if at.lower() in ("run", "running") else at.lower()
    if "brand" in data:
        shoe.brand = str(data["brand"]).strip() or shoe.brand
    if "model" in data:
        shoe.model = str(data["model"]).strip() or shoe.model
    if "nick" in data:
        shoe.nick = str(data["nick"]).strip() or None
    if "max_distance_km" in data:
        try:
            shoe.max_value = round(float(data["max_distance_km"]), 2) if data["max_distance_km"] is not None else None
        except (TypeError, ValueError):
            pass
    if "distance_covered_km" in data:
        try:
            new_total = _round_km(data["distance_covered_km"], 0.0)
            activity_linked_total = db.session.query(
                func.coalesce(func.sum(ActivityGearUsage.value), 0)
            ).filter(
                ActivityGearUsage.gear_id == shoe_id,
                ActivityGearUsage.activity_id.isnot(None),
            ).scalar()
            manual_delta = round(new_total - float(activity_linked_total), 2)
            manual_row = ActivityGearUsage.query.filter_by(gear_id=shoe_id, activity_id=None).first()
            if manual_row:
                manual_row.value = manual_delta
            else:
                db.session.add(
                    ActivityGearUsage(activity_id=None, gear_id=shoe_id, value=manual_delta)
                )
            db.session.flush()
            _recompute_gear_value_covered(shoe_id)
        except (TypeError, ValueError):
            pass
    db.session.commit()
    return jsonify({"success": True, "shoe": _gear_to_shoe_json(shoe)})


@app.route("/api/shoes/<int:shoe_id>", methods=["DELETE"])
@require_auth
def delete_shoe(shoe_id):
    """Delete a shoe (gear with gear_type='shoe')."""
    shoe = Gear.query.filter_by(id=shoe_id, user_id=request.user.id, gear_type="shoe").first()
    if not shoe:
        return jsonify({"success": False, "error": "Shoe not found"}), 404
    db.session.delete(shoe)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/shoes/<int:shoe_id>/default", methods=["PUT"])
@require_auth
def set_default_shoe(shoe_id):
    """Mark shoe as default for running (clear other running shoes)."""
    shoe = Gear.query.filter_by(id=shoe_id, user_id=request.user.id, gear_type="shoe").first()
    if not shoe:
        return jsonify({"success": False, "error": "Shoe not found"}), 404
    for g in Gear.query.filter_by(user_id=request.user.id, gear_type="shoe").all():
        g.is_default = False
    shoe.is_default = True
    db.session.commit()
    return jsonify({"success": True, "shoe": _gear_to_shoe_json(shoe)})


# --- Activities ---

def _activity_to_json(a, include_shoes=False, include_gear=False):
    out = {
        "id": a.id,
        "name": a.name,
        "date": a.date.isoformat() if hasattr(a.date, "isoformat") else str(a.date),
        "total_distance_km": a.total_distance_km,
        "total_hours": a.total_hours,
        "total_sessions": a.total_sessions,
        "activity_type": a.activity_type,
        "source": a.source,
        "strava_activity_id": a.strava_activity_id,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
    if include_shoes:
        # Shoes from activity_gear_usage where gear is shoe-type
        shoe_usages = [
            u for u in a.activity_gear_usages
            if u.gear and u.gear.gear_type == "shoe"
        ]
        out["shoes"] = [
            {"shoe_id": u.gear_id, "distance_km": u.value}
            for u in shoe_usages
        ]
    if include_gear:
        usage_gear_ids = {u.gear_id for u in a.activity_gear_usages}
        gear_list = []
        for u in a.activity_gear_usages:
            item = {"gear_id": u.gear_id, "value": u.value}
            gear = u.gear
            if gear and gear.gear_type != "component":
                installed = [i.child_gear_id for i in gear.as_parent_installations if i.removed_at is None]
                active = [cid for cid in installed if cid in usage_gear_ids]
                excluded = [cid for cid in installed if cid not in usage_gear_ids]
                item["active_component_ids"] = active
                item["excluded_component_ids"] = excluded
            gear_list.append(item)
        out["gear"] = gear_list
    return out


@app.route("/api/activities", methods=["GET"])
@require_auth
def list_activities():
    """List current user's activities."""
    activities = Activity.query.filter_by(user_id=request.user.id).order_by(Activity.date.desc()).all()
    return jsonify({"success": True, "activities": [_activity_to_json(a) for a in activities]})


@app.route("/api/activities", methods=["POST"])
@require_auth
def create_activity():
    """Create activity. Supports run, bike, swim, other. Optionally auto-add default gear."""
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    date_str = data.get("date")
    activity_type = (data.get("activity_type") or "run").strip().lower()
    if activity_type not in ("run", "bike", "swim", "other"):
        activity_type = "run"
    total_distance_km = _round_km(data.get("total_distance_km"), 0.0)
    total_hours = data.get("total_hours")
    if total_hours is not None:
        try:
            total_hours = round(float(total_hours), 2)
        except (TypeError, ValueError):
            total_hours = None
    total_sessions = data.get("total_sessions")
    if total_sessions is not None:
        try:
            total_sessions = round(float(total_sessions), 2)
        except (TypeError, ValueError):
            total_sessions = None
    auto_add_default = data.get("auto_add_default_shoe", True)

    if not name:
        return jsonify({"success": False, "error": "name is required"}), 400
    if not date_str:
        return jsonify({"success": False, "error": "date is required"}), 400
    try:
        from datetime import datetime
        date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Invalid date format"}), 400

    activity = Activity(
        user_id=request.user.id,
        name=name,
        date=date,
        total_distance_km=total_distance_km,
        total_hours=total_hours,
        total_sessions=total_sessions,
        activity_type=activity_type,
        source="manual",
    )
    db.session.add(activity)
    db.session.flush()

    if auto_add_default:
        default_gear = Gear.query.filter_by(
            user_id=request.user.id,
            activity_type=activity_type,
            is_default=True,
            status="active",
        ).first()
        if default_gear:
            value = total_distance_km if activity_type == "run" else (total_hours or total_distance_km)
            if value and value > 0:
                db.session.add(
                    ActivityGearUsage(
                        activity_id=activity.id, gear_id=default_gear.id, value=value
                    )
                )
                db.session.flush()
                _recompute_gear_value_covered(default_gear.id)

    db.session.commit()
    return jsonify({
        "success": True,
        "activity": _activity_to_json(activity, include_shoes=True, include_gear=True)
    }), 201


@app.route("/api/activities/<int:activity_id>", methods=["GET"])
@require_auth
def get_activity(activity_id):
    """Get activity detail with shoes and gear (including component active/inactive)."""
    activity = Activity.query.filter_by(id=activity_id, user_id=request.user.id).first()
    if not activity:
        return jsonify({"success": False, "error": "Activity not found"}), 404
    return jsonify({
        "success": True,
        "activity": _activity_to_json(activity, include_shoes=True, include_gear=True)
    })


@app.route("/api/activities/<int:activity_id>", methods=["PUT"])
@require_auth
def update_activity(activity_id):
    """Update activity name, date, total_distance_km, total_hours, total_sessions, activity_type."""
    activity = Activity.query.filter_by(id=activity_id, user_id=request.user.id).first()
    if not activity:
        return jsonify({"success": False, "error": "Activity not found"}), 404

    data = request.get_json() or {}
    if "name" in data and data["name"] is not None:
        activity.name = str(data["name"]).strip() or activity.name
    if "date" in data and data["date"]:
        try:
            from datetime import datetime
            activity.date = datetime.fromisoformat(str(data["date"]).replace("Z", "+00:00")).date()
        except (ValueError, TypeError):
            pass
    if "activity_type" in data and data["activity_type"]:
        at = str(data["activity_type"]).strip().lower()
        if at in ("run", "bike", "swim", "other"):
            activity.activity_type = at
    if "total_distance_km" in data and data["total_distance_km"] is not None:
        try:
            activity.total_distance_km = round(float(data["total_distance_km"]), 2)
        except (TypeError, ValueError):
            pass
    if "total_hours" in data and data["total_hours"] is not None:
        try:
            activity.total_hours = round(float(data["total_hours"]), 2)
        except (TypeError, ValueError):
            pass
    if "total_sessions" in data and data["total_sessions"] is not None:
        try:
            activity.total_sessions = round(float(data["total_sessions"]), 2)
        except (TypeError, ValueError):
            pass
    db.session.commit()
    return jsonify({
        "success": True,
        "activity": _activity_to_json(activity, include_shoes=True, include_gear=True)
    })


@app.route("/api/activities/<int:activity_id>", methods=["DELETE"])
@require_auth
def delete_activity(activity_id):
    """Delete activity."""
    activity = Activity.query.filter_by(id=activity_id, user_id=request.user.id).first()
    if not activity:
        return jsonify({"success": False, "error": "Activity not found"}), 404
    affected_gear_ids = {u.gear_id for u in activity.activity_gear_usages}
    db.session.delete(activity)
    db.session.flush()
    for gid in affected_gear_ids:
        _recompute_gear_value_covered(gid)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/activities/<int:activity_id>/shoes", methods=["PUT"])
@require_auth
def update_activity_shoes(activity_id):
    """Add/edit/remove shoes and distances. Body: [{ shoe_id, distance_km }, ...]
    - shoe_id = gear_id for gear with gear_type='shoe'
    - When 2+ shoes: distance_km required for each; sum must equal activity.total_distance_km
    - When 1 shoe: distance_km optional; backend auto-sets to full activity distance
    """
    activity = Activity.query.filter_by(id=activity_id, user_id=request.user.id).first()
    if not activity:
        return jsonify({"success": False, "error": "Activity not found"}), 404

    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({"success": False, "error": "Expected array of { shoe_id, distance_km }"}), 400

    items = [item for item in data if item.get("shoe_id") is not None]
    shoe_ids = [item["shoe_id"] for item in items]
    if shoe_ids:
        count = Gear.query.filter(
            Gear.id.in_(shoe_ids), Gear.user_id == request.user.id, Gear.gear_type == "shoe"
        ).count()
        if count != len(set(shoe_ids)):
            return jsonify({"success": False, "error": "Invalid shoe_id"}), 400

    total_activity = activity.total_distance_km
    if len(items) >= 2:
        for item in items:
            if "distance_km" not in item or item["distance_km"] is None:
                return jsonify(
                    {"success": False, "error": "distance_km required for each shoe when 2+ shoes remain"}
                ), 400
        try:
            provided_sum = sum(float(item["distance_km"]) for item in items)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Invalid distance_km"}), 400
        if abs(provided_sum - total_activity) > 1e-6:
            return jsonify(
                {"success": False, "error": f"Sum of distances must equal activity total ({total_activity} km)"}
            ), 400
    elif len(items) == 1:
        if "distance_km" not in items[0] or items[0]["distance_km"] is None:
            items[0]["distance_km"] = total_activity

    old_gear_ids = {u.gear_id for u in ActivityGearUsage.query.filter_by(activity_id=activity_id).all()}
    new_gear_ids = set(shoe_ids)
    affected_gear_ids = old_gear_ids | new_gear_ids

    ActivityGearUsage.query.filter_by(activity_id=activity_id).delete()
    for item in items:
        gear_id = item["shoe_id"]
        val = _round_km(item.get("distance_km", 0) or 0, 0.0)
        db.session.add(
            ActivityGearUsage(activity_id=activity_id, gear_id=gear_id, value=val)
        )

    db.session.flush()
    for gid in affected_gear_ids:
        _recompute_gear_value_covered(gid)
    db.session.commit()
    activity = Activity.query.get(activity_id)
    return jsonify({"success": True, "activity": _activity_to_json(activity, include_shoes=True)})


# --- Gear ---

@app.route("/api/gear", methods=["GET"])
@require_auth
def list_gear():
    """List current user's gear. Optional query: activity_type, gear_type. Includes components_count."""
    q = Gear.query.filter_by(user_id=request.user.id).order_by(Gear.created_at.desc())
    if request.args.get("activity_type"):
        q = q.filter_by(activity_type=request.args.get("activity_type"))
    if request.args.get("gear_type"):
        q = q.filter_by(gear_type=request.args.get("gear_type"))
    gear_list = q.all()
    gear_ids = [g.id for g in gear_list]
    count_map = {}
    if gear_ids:
        count_rows = (
            db.session.query(GearInstallation.parent_gear_id, func.count(GearInstallation.id).label("cnt"))
            .filter(
                GearInstallation.parent_gear_id.in_(gear_ids),
                GearInstallation.removed_at.is_(None),
            )
            .group_by(GearInstallation.parent_gear_id)
            .all()
        )
        count_map = {row.parent_gear_id: row.cnt for row in count_rows}
    return jsonify({
        "success": True,
        "gear": [_gear_to_json(g, components_count=count_map.get(g.id, 0)) for g in gear_list]
    })


@app.route("/api/gear", methods=["POST"])
@require_auth
def create_gear():
    """Create new gear."""
    data = request.get_json() or {}
    activity_type = (data.get("activity_type") or "run").strip().lower()
    gear_type = (data.get("gear_type") or "shoe").strip().lower()
    brand = (data.get("brand") or "").strip()
    model = (data.get("model") or "").strip()
    nick = (data.get("nick") or "").strip() or None
    metric_type = (data.get("metric_type") or "distance").strip().lower()
    max_value = data.get("max_value")
    if max_value is not None:
        try:
            max_value = round(float(max_value), 2)
        except (TypeError, ValueError):
            max_value = None
    value_covered = _round_km(data.get("value_covered"), 0.0)

    if not brand or not model:
        return jsonify({"success": False, "error": "brand and model are required"}), 400

    gear = Gear(
        user_id=request.user.id,
        activity_type=activity_type,
        gear_type=gear_type,
        brand=brand,
        model=model,
        nick=nick,
        metric_type=metric_type,
        max_value=max_value,
        value_covered=0.0,
        is_default=False,
        status="active",
    )
    db.session.add(gear)
    db.session.flush()
    if value_covered and value_covered > 0:
        db.session.add(ActivityGearUsage(activity_id=None, gear_id=gear.id, value=value_covered))
        db.session.flush()
        _recompute_gear_value_covered(gear.id)

    parent_gear_id = data.get("parent_gear_id")
    if gear_type == "component" and parent_gear_id is not None:
        parent = Gear.query.filter_by(id=parent_gear_id, user_id=request.user.id).first()
        if not parent:
            db.session.rollback()
            return jsonify({"success": False, "error": "Parent gear not found"}), 400
        if parent.id == gear.id:
            db.session.rollback()
            return jsonify({"success": False, "error": "Gear cannot be its own parent"}), 400
        if parent.gear_type == "component":
            db.session.rollback()
            return jsonify({"success": False, "error": "Parent must not be a component (only 1 level hierarchy)"}), 400
        db.session.add(GearInstallation(child_gear_id=gear.id, parent_gear_id=parent_gear_id))
        db.session.flush()

    db.session.commit()
    return jsonify({"success": True, "gear": _gear_to_json(gear)}), 201


@app.route("/api/gear/<int:gear_id>", methods=["GET"])
@require_auth
def get_gear(gear_id):
    """Get single gear with installations and services."""
    gear = Gear.query.filter_by(id=gear_id, user_id=request.user.id).first()
    if not gear:
        return jsonify({"success": False, "error": "Gear not found"}), 404
    out = _gear_to_json(gear)
    out["installations"] = [
        {
            "id": i.id,
            "parent_gear_id": i.parent_gear_id,
            "installed_at": i.installed_at.isoformat() if i.installed_at else None,
            "removed_at": i.removed_at.isoformat() if i.removed_at else None,
        }
        for i in gear.as_child_installations
    ]
    out["services"] = [
        {
            "id": s.id,
            "name": s.name,
            "interval_value": s.interval_value,
            "interval_unit": s.interval_unit,
            "early_warning_ratio": s.early_warning_ratio,
            "last_performed_value": s.last_performed_value,
        }
        for s in gear.gear_services
    ]
    return jsonify({"success": True, "gear": out})


@app.route("/api/gear/<int:gear_id>", methods=["PUT"])
@require_auth
def update_gear(gear_id):
    """Update gear."""
    gear = Gear.query.filter_by(id=gear_id, user_id=request.user.id).first()
    if not gear:
        return jsonify({"success": False, "error": "Gear not found"}), 404

    data = request.get_json() or {}
    if "activity_type" in data:
        gear.activity_type = str(data["activity_type"]).strip().lower() or gear.activity_type
    if "gear_type" in data:
        gear.gear_type = str(data["gear_type"]).strip().lower() or gear.gear_type
    if "brand" in data:
        gear.brand = str(data["brand"]).strip() or gear.brand
    if "model" in data:
        gear.model = str(data["model"]).strip() or gear.model
    if "nick" in data:
        gear.nick = str(data["nick"]).strip() or None
    if "metric_type" in data:
        gear.metric_type = str(data["metric_type"]).strip().lower() or gear.metric_type
    if "max_value" in data:
        try:
            gear.max_value = round(float(data["max_value"]), 2) if data["max_value"] is not None else None
        except (TypeError, ValueError):
            pass
    if "value_covered" in data:
        try:
            new_total = _round_km(data["value_covered"], 0.0)
            activity_linked = db.session.query(
                func.coalesce(func.sum(ActivityGearUsage.value), 0)
            ).filter(
                ActivityGearUsage.gear_id == gear_id,
                ActivityGearUsage.activity_id.isnot(None),
            ).scalar()
            manual_delta = round(new_total - float(activity_linked), 2)
            manual_row = ActivityGearUsage.query.filter_by(gear_id=gear_id, activity_id=None).first()
            if manual_row:
                manual_row.value = manual_delta
            else:
                db.session.add(ActivityGearUsage(activity_id=None, gear_id=gear_id, value=manual_delta))
            db.session.flush()
            _recompute_gear_value_covered(gear_id)
        except (TypeError, ValueError):
            pass

    if "parent_gear_id" in data and gear.gear_type == "component":
        parent_gear_id = data["parent_gear_id"]
        for inst in GearInstallation.query.filter_by(child_gear_id=gear_id, removed_at=None).all():
            inst.removed_at = datetime.now(timezone.utc)
        if parent_gear_id is not None:
            parent = Gear.query.filter_by(id=parent_gear_id, user_id=request.user.id).first()
            if not parent:
                return jsonify({"success": False, "error": "Parent gear not found"}), 400
            if parent.id == gear_id:
                return jsonify({"success": False, "error": "Gear cannot be its own parent"}), 400
            if parent.gear_type == "component":
                return jsonify({"success": False, "error": "Parent must not be a component (only 1 level hierarchy)"}), 400
            db.session.add(GearInstallation(child_gear_id=gear_id, parent_gear_id=parent_gear_id))
        db.session.flush()

    db.session.commit()
    return jsonify({"success": True, "gear": _gear_to_json(gear)})


@app.route("/api/gear/<int:gear_id>", methods=["DELETE"])
@require_auth
def delete_gear(gear_id):
    """Delete gear."""
    gear = Gear.query.filter_by(id=gear_id, user_id=request.user.id).first()
    if not gear:
        return jsonify({"success": False, "error": "Gear not found"}), 404
    db.session.delete(gear)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/gear/<int:gear_id>/default", methods=["PUT"])
@require_auth
def set_default_gear(gear_id):
    """Mark gear as default for its activity_type."""
    gear = Gear.query.filter_by(id=gear_id, user_id=request.user.id).first()
    if not gear:
        return jsonify({"success": False, "error": "Gear not found"}), 404
    for g in Gear.query.filter_by(
        user_id=request.user.id, activity_type=gear.activity_type
    ).all():
        g.is_default = False
    gear.is_default = True
    db.session.commit()
    return jsonify({"success": True, "gear": _gear_to_json(gear)})


@app.route("/api/gear/<int:gear_id>/components", methods=["GET"])
@require_auth
def get_gear_components(gear_id):
    """List components currently installed on this parent gear. Only for parent gear (shoe/bike)."""
    gear = Gear.query.filter_by(id=gear_id, user_id=request.user.id).first()
    if not gear:
        return jsonify({"success": False, "error": "Gear not found"}), 404
    if gear.gear_type == "component":
        return jsonify({"success": False, "error": "Components cannot have child components (only 1 level)"}), 400
    installations = [i for i in gear.as_parent_installations if i.removed_at is None]
    components = []
    for inst in installations:
        child = inst.child_gear
        item = _gear_to_json(child)
        item["installation_id"] = inst.id
        item["installed_at"] = inst.installed_at.isoformat() if inst.installed_at else None
        components.append(item)
    return jsonify({"success": True, "components": components})


@app.route("/api/gear/<int:gear_id>/installations", methods=["POST"])
@require_auth
def create_gear_installation(gear_id):
    """Attach component (gear_id) to parent. Body: { parent_gear_id }. gear_id = component (child)."""
    child = Gear.query.filter_by(id=gear_id, user_id=request.user.id).first()
    if not child:
        return jsonify({"success": False, "error": "Gear not found"}), 404
    data = request.get_json() or {}
    parent_id = data.get("parent_gear_id")
    if not parent_id:
        return jsonify({"success": False, "error": "parent_gear_id required"}), 400
    parent = Gear.query.filter_by(id=parent_id, user_id=request.user.id).first()
    if not parent:
        return jsonify({"success": False, "error": "Parent gear not found"}), 404
    # End current installation if any (component can only be on one parent at a time)
    for inst in GearInstallation.query.filter_by(child_gear_id=gear_id, removed_at=None).all():
        inst.removed_at = datetime.now(timezone.utc)
    inst = GearInstallation(child_gear_id=gear_id, parent_gear_id=parent_id)
    db.session.add(inst)
    db.session.commit()
    return jsonify({"success": True, "installation": {"id": inst.id, "parent_gear_id": inst.parent_gear_id}}), 201


@app.route("/api/gear/<int:gear_id>/installations/<int:installation_id>", methods=["DELETE"])
@require_auth
def remove_gear_installation(gear_id, installation_id):
    """Detach component (set removed_at)."""
    inst = GearInstallation.query.filter_by(id=installation_id).first()
    if not inst or inst.child_gear_id != gear_id:
        return jsonify({"success": False, "error": "Installation not found"}), 404
    child = Gear.query.filter_by(id=inst.child_gear_id, user_id=request.user.id).first()
    if not child:
        return jsonify({"success": False, "error": "Gear not found"}), 404
    inst.removed_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/gear/<int:gear_id>/services", methods=["GET"])
@require_auth
def list_gear_services(gear_id):
    """List services for gear."""
    gear = Gear.query.filter_by(id=gear_id, user_id=request.user.id).first()
    if not gear:
        return jsonify({"success": False, "error": "Gear not found"}), 404
    return jsonify({
        "success": True,
        "services": [
            {
                "id": s.id,
                "name": s.name,
                "interval_value": s.interval_value,
                "interval_unit": s.interval_unit,
                "early_warning_ratio": s.early_warning_ratio,
                "last_performed_value": s.last_performed_value,
            }
            for s in gear.gear_services
        ],
    })


@app.route("/api/gear/<int:gear_id>/services", methods=["POST"])
@require_auth
def create_gear_service(gear_id):
    """Create service schedule. Body: { name, interval_value, interval_unit, early_warning_ratio? }."""
    gear = Gear.query.filter_by(id=gear_id, user_id=request.user.id).first()
    if not gear:
        return jsonify({"success": False, "error": "Gear not found"}), 404
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    interval_value = data.get("interval_value")
    interval_unit = (data.get("interval_unit") or "km").strip().lower()
    early_warning_ratio = data.get("early_warning_ratio")
    if not name:
        return jsonify({"success": False, "error": "name required"}), 400
    try:
        interval_value = float(interval_value)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "interval_value required and numeric"}), 400
    if early_warning_ratio is not None:
        try:
            early_warning_ratio = float(early_warning_ratio)
        except (TypeError, ValueError):
            early_warning_ratio = None
    svc = GearService(
        gear_id=gear_id,
        name=name,
        interval_value=interval_value,
        interval_unit=interval_unit,
        early_warning_ratio=early_warning_ratio,
    )
    db.session.add(svc)
    db.session.commit()
    return jsonify({
        "success": True,
        "service": {
            "id": svc.id,
            "name": svc.name,
            "interval_value": svc.interval_value,
            "interval_unit": svc.interval_unit,
            "early_warning_ratio": svc.early_warning_ratio,
            "last_performed_value": svc.last_performed_value,
        },
    }), 201


@app.route("/api/gear/<int:gear_id>/services/<int:service_id>", methods=["PUT"])
@require_auth
def update_gear_service(gear_id, service_id):
    """Update service schedule. Body: { name?, interval_value?, interval_unit?, early_warning_ratio? }."""
    gear = Gear.query.filter_by(id=gear_id, user_id=request.user.id).first()
    if not gear:
        return jsonify({"success": False, "error": "Gear not found"}), 404
    svc = GearService.query.filter_by(id=service_id, gear_id=gear_id).first()
    if not svc:
        return jsonify({"success": False, "error": "Service not found"}), 404
    data = request.get_json() or {}
    if "name" in data and data["name"] is not None:
        svc.name = str(data["name"]).strip() or svc.name
    if "interval_value" in data and data["interval_value"] is not None:
        try:
            svc.interval_value = float(data["interval_value"])
        except (TypeError, ValueError):
            pass
    if "interval_unit" in data and data["interval_unit"] is not None:
        svc.interval_unit = str(data["interval_unit"]).strip().lower() or svc.interval_unit
    if "early_warning_ratio" in data:
        if data["early_warning_ratio"] is None:
            svc.early_warning_ratio = None
        else:
            try:
                svc.early_warning_ratio = float(data["early_warning_ratio"])
            except (TypeError, ValueError):
                pass
    db.session.commit()
    return jsonify({
        "success": True,
        "service": {
            "id": svc.id,
            "name": svc.name,
            "interval_value": svc.interval_value,
            "interval_unit": svc.interval_unit,
            "early_warning_ratio": svc.early_warning_ratio,
            "last_performed_value": svc.last_performed_value,
        },
    })


@app.route("/api/gear/<int:gear_id>/services/<int:service_id>", methods=["DELETE"])
@require_auth
def delete_gear_service(gear_id, service_id):
    """Delete a service schedule."""
    gear = Gear.query.filter_by(id=gear_id, user_id=request.user.id).first()
    if not gear:
        return jsonify({"success": False, "error": "Gear not found"}), 404
    svc = GearService.query.filter_by(id=service_id, gear_id=gear_id).first()
    if not svc:
        return jsonify({"success": False, "error": "Service not found"}), 404
    db.session.delete(svc)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/gear/<int:gear_id>/services/<int:service_id>/logs", methods=["POST"])
@require_auth
def log_gear_service(gear_id, service_id):
    """Mark service as performed. Sets last_performed_value = gear.value_covered."""
    gear = Gear.query.filter_by(id=gear_id, user_id=request.user.id).first()
    if not gear:
        return jsonify({"success": False, "error": "Gear not found"}), 404
    svc = GearService.query.filter_by(id=service_id, gear_id=gear_id).first()
    if not svc:
        return jsonify({"success": False, "error": "Service not found"}), 404
    value_at = gear.value_covered
    svc.last_performed_value = value_at
    log_entry = GearServiceLog(gear_service_id=service_id, performed_at=datetime.now(timezone.utc), value_at_perform=value_at)
    db.session.add(log_entry)
    db.session.commit()
    return jsonify({
        "success": True,
        "log": {"id": log_entry.id, "performed_at": log_entry.performed_at.isoformat(), "value_at_perform": value_at},
    }), 201


@app.route("/api/gear/<int:gear_id>/retire", methods=["PUT"])
@require_auth
def retire_gear(gear_id):
    """Retire gear (status=retired)."""
    gear = Gear.query.filter_by(id=gear_id, user_id=request.user.id).first()
    if not gear:
        return jsonify({"success": False, "error": "Gear not found"}), 404
    gear.status = "retired"
    db.session.commit()
    return jsonify({"success": True, "gear": _gear_to_json(gear)})


@app.route("/api/gear/alerts", methods=["GET"])
@require_auth
def list_gear_alerts():
    """List gear with max_value or service due/overdue alerts."""
    gear_list = Gear.query.filter_by(user_id=request.user.id, status="active").all()
    alerts = []
    for g in gear_list:
        if g.max_value is not None and g.value_covered >= g.max_value:
            alerts.append({"gear_id": g.id, "type": "max_value", "message": f"Gear reached max value ({g.value_covered} >= {g.max_value})"})
        for s in g.gear_services:
            last = s.last_performed_value if s.last_performed_value is not None else 0
            since = g.value_covered - last
            if since >= s.interval_value:
                alerts.append({"gear_id": g.id, "service_id": s.id, "type": "service_overdue", "message": f"Service '{s.name}' overdue"})
            elif s.early_warning_ratio and since >= s.interval_value * s.early_warning_ratio:
                alerts.append({"gear_id": g.id, "service_id": s.id, "type": "service_warning", "message": f"Service '{s.name}' due soon"})
    return jsonify({"success": True, "alerts": alerts})


@app.route("/api/activities/<int:activity_id>/gear", methods=["PUT"])
@require_auth
def update_activity_gear(activity_id):
    """Assign gear to activity. Body: [{ gear_id, value }, ...] or [{ gear_id, component_ids: [id,...] }].
    For shoes/distance: value is distance_km. For components, auto-select installed by default; component_ids to deselect.
    """
    activity = Activity.query.filter_by(id=activity_id, user_id=request.user.id).first()
    if not activity:
        return jsonify({"success": False, "error": "Activity not found"}), 404

    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({"success": False, "error": "Expected array of { gear_id, value? }"}), 400

    total_val = activity.total_distance_km or activity.total_hours or activity.total_sessions or 0
    items = []
    for item in data:
        gid = item.get("gear_id")
        if gid is None:
            continue
        gear = Gear.query.filter_by(id=gid, user_id=request.user.id).first()
        if not gear:
            return jsonify({"success": False, "error": f"Invalid gear_id {gid}"}), 400
        val = item.get("value")
        if val is not None:
            val = _round_km(val, 0.0)
        else:
            val = total_val
        excluded_component_ids = set(item.get("excluded_component_ids") or [])
        items.append({"gear_id": gid, "value": val, "excluded_component_ids": excluded_component_ids})

    if len(items) >= 2:
        try:
            provided_sum = sum(item["value"] for item in items)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Invalid value"}), 400
        if abs(provided_sum - total_val) > 1e-6:
            return jsonify({"success": False, "error": f"Sum of values must equal activity total"}), 400

    old_gear_ids = {u.gear_id for u in activity.activity_gear_usages}
    new_gear_ids = set()
    ActivityGearUsage.query.filter_by(activity_id=activity_id).delete()
    for item in items:
        gid = item["gear_id"]
        val = item["value"]
        db.session.add(ActivityGearUsage(activity_id=activity_id, gear_id=gid, value=val))
        new_gear_ids.add(gid)
        gear = Gear.query.get(gid)
        if gear and gear.gear_type != "component":
            installed = [i for i in gear.as_parent_installations if i.removed_at is None]
            for inst in installed:
                cid = inst.child_gear_id
                if cid not in item.get("excluded_component_ids", set()):
                    db.session.add(ActivityGearUsage(activity_id=activity_id, gear_id=cid, value=val))
                    new_gear_ids.add(cid)
    affected = old_gear_ids | new_gear_ids
    db.session.flush()
    for gid in affected:
        _recompute_gear_value_covered(gid)
    db.session.commit()
    activity = Activity.query.get(activity_id)
    return jsonify({"success": True, "activity": _activity_to_json(activity, include_shoes=True, include_gear=True)})


# --- Strava Webhook ---

@app.route("/api/webhooks/strava", methods=["GET"])
def strava_webhook_verify():
    """Strava subscription verification: respond with hub.challenge."""
    challenge = request.args.get("hub.challenge")
    verify_token = request.args.get("hub.verify_token")
    if not STRAVA_WEBHOOK_VERIFY_TOKEN:
        return jsonify({"error": "Webhook not configured"}), 503
    if verify_token != STRAVA_WEBHOOK_VERIFY_TOKEN:
        return jsonify({"error": "Invalid verify token"}), 403
    return jsonify({"hub.challenge": challenge})


@app.route("/api/webhooks/strava", methods=["POST"])
def strava_webhook_event():
    """Handle Strava webhook events. Respond 200 quickly, process async."""
    # Strava sends form-urlencoded or JSON
    data = request.get_json(silent=True) or request.form.to_dict()
    if not data:
        return jsonify({"ok": True}), 200

    aspect_type = data.get("aspect_type")
    object_type = data.get("object_type")
    owner_id = data.get("owner_id")
    object_id = data.get("object_id")

    if aspect_type == "create" and object_type == "activity" and owner_id and object_id:
        try:
            process_activity_create(int(owner_id), int(object_id), app)
        except (ValueError, TypeError):
            pass

    if aspect_type == "update" and object_type == "activity" and owner_id and object_id:
        updates = data.get("updates") or {}
        if "title" in updates:
            try:
                process_activity_update(int(owner_id), int(object_id), updates, app)
            except (ValueError, TypeError):
                pass

    return jsonify({"ok": True}), 200


# --- Error handlers ---

@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "Internal server error"}), 500


if __name__ == "__main__":
    print("=" * 60)
    print("Shoe Tracker REST API")
    print("=" * 60)
    print("\n  GET  /api/health                  - Health check")
    print("\nAuth:")
    print("  POST /api/auth/register           - Register")
    print("  POST /api/auth/login              - Login")
    print("  POST /api/auth/forgot-password    - Request reset")
    print("  POST /api/auth/reset-password     - Reset with token")
    print("  GET  /api/auth/me                 - Current user")
    print("  PUT  /api/auth/profile            - Update name, avatar")
    print("\nStrava:")
    print("  GET  /api/strava/connect          - OAuth URL")
    print("  GET  /api/strava/callback          - OAuth callback")
    print("  POST /api/strava/disconnect        - Disconnect")
    print("  GET  /api/strava/status            - Connection status")
    print("\nShoes (legacy): GET/POST /api/shoes, GET/PUT/DELETE /api/shoes/:id")
    print("               PUT /api/shoes/:id/default")
    print("\nGear: GET/POST /api/gear, GET/PUT/DELETE /api/gear/:id")
    print("      PUT /api/gear/:id/default, PUT /api/gear/:id/retire")
    print("      POST/DELETE /api/gear/:id/installations")
    print("      GET/POST /api/gear/:id/services, GET/PUT/DELETE /api/gear/:id/services/:sid, POST .../sid/logs")
    print("      GET /api/gear/alerts")
    print("\nActivities: GET/POST /api/activities, GET/PUT/DELETE /api/activities/:id")
    print("            PUT /api/activities/:id/shoes, PUT /api/activities/:id/gear")
    print("\nWebhook: GET/POST /api/webhooks/strava")
    print("\nServer: http://localhost:8000")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=8000)
