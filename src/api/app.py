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
from src.models import db, User, UserStrava, Shoe, Activity, ActivityShoeDistance
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
        "user": {"id": user.id, "email": user.email, "name": user.name, "avatar_url": user.avatar_url},
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
        "user": {"id": user.id, "email": user.email, "name": user.name, "avatar_url": user.avatar_url},
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
    return jsonify({
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "strava_connected": strava_connected,
        },
    })


@app.route("/api/auth/profile", methods=["PUT"])
@require_auth
def update_profile():
    """Update name and/or avatar."""
    user = request.user
    data = request.get_json() or {}
    if "name" in data and data["name"] is not None:
        user.name = str(data["name"]).strip() or user.name
    if "avatar_url" in data and data["avatar_url"] is not None:
        user.avatar_url = str(data["avatar_url"]).strip() or None
    db.session.commit()
    return jsonify({
        "success": True,
        "user": {"id": user.id, "email": user.email, "name": user.name, "avatar_url": user.avatar_url},
    })


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


# --- Shoes ---

def _shoe_to_json(s):
    return {
        "id": s.id,
        "activity_type": s.activity_type,
        "brand": s.brand,
        "model": s.model,
        "nick": s.nick,
        "max_distance_km": s.max_distance_km,
        "distance_covered_km": s.distance_covered_km,
        "is_default": s.is_default,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _recompute_shoe_distance_covered(shoe_id):
    """Set shoe.distance_covered_km to sum of ActivityShoeDistance.distance_km for this shoe."""
    shoe = Shoe.query.get(shoe_id)
    if not shoe:
        return
    total = db.session.query(func.coalesce(func.sum(ActivityShoeDistance.distance_km), 0)).filter_by(
        shoe_id=shoe_id
    ).scalar()
    shoe.distance_covered_km = round(float(total), 2)


@app.route("/api/shoes", methods=["GET"])
@require_auth
def list_shoes():
    """List current user's shoes."""
    shoes = Shoe.query.filter_by(user_id=request.user.id).order_by(Shoe.created_at.desc()).all()
    return jsonify({"success": True, "shoes": [_shoe_to_json(s) for s in shoes]})


@app.route("/api/shoes", methods=["POST"])
@require_auth
def create_shoe():
    """Create a new shoe."""
    data = request.get_json() or {}
    activity_type = (data.get("activity_type") or "").strip() or "running"
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

    shoe = Shoe(
        user_id=request.user.id,
        activity_type=activity_type,
        brand=brand,
        model=model,
        nick=nick,
        max_distance_km=max_distance_km,
        distance_covered_km=0.0,  # Computed from activity_shoe_distance
    )
    db.session.add(shoe)
    db.session.flush()
    if distance_covered_km and distance_covered_km > 0:
        db.session.add(
            ActivityShoeDistance(activity_id=None, shoe_id=shoe.id, distance_km=distance_covered_km)
        )
        db.session.flush()
        _recompute_shoe_distance_covered(shoe.id)
    db.session.commit()
    return jsonify({"success": True, "shoe": _shoe_to_json(shoe)}), 201


@app.route("/api/shoes/<int:shoe_id>", methods=["GET"])
@require_auth
def get_shoe(shoe_id):
    """Get a single shoe."""
    shoe = Shoe.query.filter_by(id=shoe_id, user_id=request.user.id).first()
    if not shoe:
        return jsonify({"success": False, "error": "Shoe not found"}), 404
    return jsonify({"success": True, "shoe": _shoe_to_json(shoe)})


@app.route("/api/shoes/<int:shoe_id>", methods=["PUT"])
@require_auth
def update_shoe(shoe_id):
    """Update a shoe."""
    shoe = Shoe.query.filter_by(id=shoe_id, user_id=request.user.id).first()
    if not shoe:
        return jsonify({"success": False, "error": "Shoe not found"}), 404

    data = request.get_json() or {}
    if "activity_type" in data:
        shoe.activity_type = str(data["activity_type"]).strip() or shoe.activity_type
    if "brand" in data:
        shoe.brand = str(data["brand"]).strip() or shoe.brand
    if "model" in data:
        shoe.model = str(data["model"]).strip() or shoe.model
    if "nick" in data:
        shoe.nick = str(data["nick"]).strip() or None
    if "max_distance_km" in data:
        try:
            shoe.max_distance_km = round(float(data["max_distance_km"]), 2) if data["max_distance_km"] is not None else None
        except (TypeError, ValueError):
            pass
    if "distance_covered_km" in data:
        try:
            val = data["distance_covered_km"]
            new_total = _round_km(val, 0.0)
            activity_linked_total = db.session.query(
                func.coalesce(func.sum(ActivityShoeDistance.distance_km), 0)
            ).filter(
                ActivityShoeDistance.shoe_id == shoe_id,
                ActivityShoeDistance.activity_id.isnot(None),
            ).scalar()
            manual_delta = round(new_total - float(activity_linked_total), 2)
            manual_row = ActivityShoeDistance.query.filter_by(
                shoe_id=shoe_id, activity_id=None
            ).first()
            if manual_row:
                manual_row.distance_km = manual_delta
            else:
                db.session.add(
                    ActivityShoeDistance(activity_id=None, shoe_id=shoe_id, distance_km=manual_delta)
                )
            db.session.flush()
            _recompute_shoe_distance_covered(shoe_id)
        except (TypeError, ValueError):
            pass
    db.session.commit()
    return jsonify({"success": True, "shoe": _shoe_to_json(shoe)})


@app.route("/api/shoes/<int:shoe_id>", methods=["DELETE"])
@require_auth
def delete_shoe(shoe_id):
    """Delete a shoe."""
    shoe = Shoe.query.filter_by(id=shoe_id, user_id=request.user.id).first()
    if not shoe:
        return jsonify({"success": False, "error": "Shoe not found"}), 404
    db.session.delete(shoe)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/shoes/<int:shoe_id>/default", methods=["PUT"])
@require_auth
def set_default_shoe(shoe_id):
    """Mark shoe as default (clear others)."""
    shoe = Shoe.query.filter_by(id=shoe_id, user_id=request.user.id).first()
    if not shoe:
        return jsonify({"success": False, "error": "Shoe not found"}), 404
    for s in Shoe.query.filter_by(user_id=request.user.id).all():
        s.is_default = False
    shoe.is_default = True
    db.session.commit()
    return jsonify({"success": True, "shoe": _shoe_to_json(shoe)})


# --- Activities ---

def _activity_to_json(a, include_shoes=False):
    out = {
        "id": a.id,
        "name": a.name,
        "date": a.date.isoformat() if hasattr(a.date, "isoformat") else str(a.date),
        "total_distance_km": a.total_distance_km,
        "source": a.source,
        "strava_activity_id": a.strava_activity_id,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
    if include_shoes:
        out["shoes"] = [
            {"shoe_id": asd.shoe_id, "distance_km": asd.distance_km}
            for asd in a.activity_shoe_distances
        ]
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
    """Create activity. Optionally auto-add default shoe with full distance."""
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    date_str = data.get("date")
    total_distance_km = data.get("total_distance_km")
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
    total_distance_km = _round_km(total_distance_km, 0.0)

    activity = Activity(
        user_id=request.user.id,
        name=name,
        date=date,
        total_distance_km=total_distance_km,
        source="manual",
    )
    db.session.add(activity)
    db.session.flush()

    if auto_add_default:
        default_shoe = Shoe.query.filter_by(user_id=request.user.id, is_default=True).first()
        if default_shoe:
            db.session.add(
                ActivityShoeDistance(
                    activity_id=activity.id, shoe_id=default_shoe.id, distance_km=total_distance_km
                )
            )
            db.session.flush()
            _recompute_shoe_distance_covered(default_shoe.id)

    db.session.commit()
    return jsonify({"success": True, "activity": _activity_to_json(activity, include_shoes=True)}), 201


@app.route("/api/activities/<int:activity_id>", methods=["GET"])
@require_auth
def get_activity(activity_id):
    """Get activity detail with shoes."""
    activity = Activity.query.filter_by(id=activity_id, user_id=request.user.id).first()
    if not activity:
        return jsonify({"success": False, "error": "Activity not found"}), 404
    return jsonify({"success": True, "activity": _activity_to_json(activity, include_shoes=True)})


@app.route("/api/activities/<int:activity_id>", methods=["PUT"])
@require_auth
def update_activity(activity_id):
    """Update activity name, date, total_distance_km."""
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
    if "total_distance_km" in data and data["total_distance_km"] is not None:
        try:
            activity.total_distance_km = round(float(data["total_distance_km"]), 2)
        except (TypeError, ValueError):
            pass
    db.session.commit()
    return jsonify({"success": True, "activity": _activity_to_json(activity, include_shoes=True)})


@app.route("/api/activities/<int:activity_id>", methods=["DELETE"])
@require_auth
def delete_activity(activity_id):
    """Delete activity."""
    activity = Activity.query.filter_by(id=activity_id, user_id=request.user.id).first()
    if not activity:
        return jsonify({"success": False, "error": "Activity not found"}), 404
    affected_shoe_ids = {asd.shoe_id for asd in activity.activity_shoe_distances}
    db.session.delete(activity)
    db.session.flush()
    for sid in affected_shoe_ids:
        _recompute_shoe_distance_covered(sid)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/activities/<int:activity_id>/shoes", methods=["PUT"])
@require_auth
def update_activity_shoes(activity_id):
    """Add/edit/remove shoes and distances. Body: [{ shoe_id, distance_km }, ...]
    - When 2+ shoes remain: distance_km required for each; sum must equal activity.total_distance_km
    - When 1 shoe remains: distance_km optional; backend auto-sets to full activity distance
    """
    activity = Activity.query.filter_by(id=activity_id, user_id=request.user.id).first()
    if not activity:
        return jsonify({"success": False, "error": "Activity not found"}), 404

    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({"success": False, "error": "Expected array of { shoe_id, distance_km }"}), 400

    # Filter to valid items with shoe_id
    items = [item for item in data if item.get("shoe_id") is not None]
    shoe_ids = [item["shoe_id"] for item in items]
    if shoe_ids:
        count = Shoe.query.filter(Shoe.id.in_(shoe_ids), Shoe.user_id == request.user.id).count()
        if count != len(set(shoe_ids)):
            return jsonify({"success": False, "error": "Invalid shoe_id"}), 400

    # Validation: 2+ shoes -> require distance_km for each, sum == activity.total_distance_km
    # 1 shoe -> auto-set distance_km if omitted
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
        # Auto-set to full activity distance if omitted
        if "distance_km" not in items[0] or items[0]["distance_km"] is None:
            items[0]["distance_km"] = total_activity

    # Shoes affected (before and after)
    old_shoe_ids = {
        asd.shoe_id
        for asd in ActivityShoeDistance.query.filter_by(activity_id=activity_id).all()
    }
    new_shoe_ids = set(shoe_ids)
    affected_shoe_ids = old_shoe_ids | new_shoe_ids

    # Replace activity_shoe_distances for this activity (only activity-linked rows)
    ActivityShoeDistance.query.filter_by(activity_id=activity_id).delete()
    for item in items:
        shoe_id = item["shoe_id"]
        d = _round_km(item.get("distance_km", 0) or 0, 0.0)
        db.session.add(
            ActivityShoeDistance(activity_id=activity_id, shoe_id=shoe_id, distance_km=d)
        )

    db.session.flush()
    for sid in affected_shoe_ids:
        _recompute_shoe_distance_covered(sid)
    db.session.commit()
    activity = Activity.query.get(activity_id)
    return jsonify({"success": True, "activity": _activity_to_json(activity, include_shoes=True)})


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
    print("\nShoes: GET/POST /api/shoes, GET/PUT/DELETE /api/shoes/:id")
    print("       PUT /api/shoes/:id/default")
    print("\nActivities: GET/POST /api/activities, GET/PUT/DELETE /api/activities/:id")
    print("            PUT /api/activities/:id/shoes")
    print("\nWebhook: GET/POST /api/webhooks/strava")
    print("\nServer: http://localhost:8000")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=8000)
