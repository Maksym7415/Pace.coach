"""Gear track business logic: gear, activities, shoes, alerts, and maintenance."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from src.modules.gear_track.models import (
    Activity,
    ActivityGearUsage,
    Gear,
    GearInstallation,
    GearService,
    GearServiceLog,
)


def _round_km(value, default=0.0):
    """Round distance to 2 decimal places for DB storage. Returns default for None or invalid."""
    if value is None:
        return default
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return default


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


def _recompute_gear_value_covered(db: Session, gear_id: int) -> None:
    """Set gear.value_covered to sum of ActivityGearUsage.value for this gear."""
    gear = db.get(Gear, gear_id)
    if not gear:
        return
    total = db.scalar(
        select(func.coalesce(func.sum(ActivityGearUsage.value), 0)).where(
            ActivityGearUsage.gear_id == gear_id
        )
    )
    gear.value_covered = round(float(total), 2)


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


def _service_to_json(s: GearService) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "interval_value": s.interval_value,
        "interval_unit": s.interval_unit,
        "early_warning_ratio": s.early_warning_ratio,
        "last_performed_value": s.last_performed_value,
    }


class GearTrackService:
    def __init__(self, db: Session):
        self.db = db

    # --- Shoes (legacy API: gear with gear_type='shoe') ---

    def list_shoes(self, user_id: int) -> dict:
        shoes = self.db.scalars(
            select(Gear)
            .where(Gear.user_id == user_id, Gear.gear_type == "shoe")
            .order_by(Gear.created_at.desc())
        ).all()
        return {"success": True, "shoes": [_gear_to_shoe_json(s) for s in shoes]}

    def create_shoe(self, user_id: int, data: dict) -> tuple[dict | None, str | None, int]:
        data = data or {}
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
            return None, "brand and model are required", 400

        gear = Gear(
            user_id=user_id,
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
        self.db.add(gear)
        self.db.flush()
        if distance_covered_km and distance_covered_km > 0:
            self.db.add(
                ActivityGearUsage(activity_id=None, gear_id=gear.id, value=distance_covered_km)
            )
            self.db.flush()
            _recompute_gear_value_covered(self.db, gear.id)
        self.db.commit()
        self.db.refresh(gear)
        return {"success": True, "shoe": _gear_to_shoe_json(gear)}, None, 201

    def get_shoe(self, user_id: int, shoe_id: int) -> tuple[dict | None, str | None, int]:
        shoe = self.db.scalar(
            select(Gear).where(
                Gear.id == shoe_id,
                Gear.user_id == user_id,
                Gear.gear_type == "shoe",
            )
        )
        if not shoe:
            return None, "Shoe not found", 404
        return {"success": True, "shoe": _gear_to_shoe_json(shoe)}, None, 200

    def update_shoe(self, user_id: int, shoe_id: int, data: dict) -> tuple[dict | None, str | None, int]:
        shoe = self.db.scalar(
            select(Gear).where(
                Gear.id == shoe_id,
                Gear.user_id == user_id,
                Gear.gear_type == "shoe",
            )
        )
        if not shoe:
            return None, "Shoe not found", 404

        data = data or {}
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
                activity_linked_total = self.db.scalar(
                    select(func.coalesce(func.sum(ActivityGearUsage.value), 0)).where(
                        ActivityGearUsage.gear_id == shoe_id,
                        ActivityGearUsage.activity_id.isnot(None),
                    )
                )
                manual_delta = round(new_total - float(activity_linked_total), 2)
                manual_row = self.db.scalar(
                    select(ActivityGearUsage).where(
                        ActivityGearUsage.gear_id == shoe_id,
                        ActivityGearUsage.activity_id.is_(None),
                    )
                )
                if manual_row:
                    manual_row.value = manual_delta
                else:
                    self.db.add(
                        ActivityGearUsage(activity_id=None, gear_id=shoe_id, value=manual_delta)
                    )
                self.db.flush()
                _recompute_gear_value_covered(self.db, shoe_id)
            except (TypeError, ValueError):
                pass
        self.db.commit()
        self.db.refresh(shoe)
        return {"success": True, "shoe": _gear_to_shoe_json(shoe)}, None, 200

    def delete_shoe(self, user_id: int, shoe_id: int) -> tuple[dict | None, str | None, int]:
        shoe = self.db.scalar(
            select(Gear).where(
                Gear.id == shoe_id,
                Gear.user_id == user_id,
                Gear.gear_type == "shoe",
            )
        )
        if not shoe:
            return None, "Shoe not found", 404
        self.db.delete(shoe)
        self.db.commit()
        return {"success": True}, None, 200

    def set_default_shoe(self, user_id: int, shoe_id: int) -> tuple[dict | None, str | None, int]:
        shoe = self.db.scalar(
            select(Gear).where(
                Gear.id == shoe_id,
                Gear.user_id == user_id,
                Gear.gear_type == "shoe",
            )
        )
        if not shoe:
            return None, "Shoe not found", 404
        for g in self.db.scalars(
            select(Gear).where(Gear.user_id == user_id, Gear.gear_type == "shoe")
        ).all():
            g.is_default = False
        shoe.is_default = True
        self.db.commit()
        self.db.refresh(shoe)
        return {"success": True, "shoe": _gear_to_shoe_json(shoe)}, None, 200

    # --- Activities ---

    def list_activities(self, user_id: int) -> dict:
        activities = self.db.scalars(
            select(Activity)
            .where(Activity.user_id == user_id)
            .order_by(Activity.date.desc())
        ).all()
        return {"success": True, "activities": [_activity_to_json(a) for a in activities]}

    def create_activity(self, user_id: int, data: dict) -> tuple[dict | None, str | None, int]:
        data = data or {}
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
            return None, "name is required", 400
        if not date_str:
            return None, "date is required", 400
        try:
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
        except (ValueError, TypeError):
            return None, "Invalid date format", 400

        activity = Activity(
            user_id=user_id,
            name=name,
            date=date,
            total_distance_km=total_distance_km,
            total_hours=total_hours,
            total_sessions=total_sessions,
            activity_type=activity_type,
            source="manual",
        )
        self.db.add(activity)
        self.db.flush()

        if auto_add_default:
            default_gear = self.db.scalar(
                select(Gear).where(
                    Gear.user_id == user_id,
                    Gear.activity_type == activity_type,
                    Gear.is_default.is_(True),
                    Gear.status == "active",
                )
            )
            if default_gear:
                value = total_distance_km if activity_type == "run" else (total_hours or total_distance_km)
                if value and value > 0:
                    self.db.add(
                        ActivityGearUsage(
                            activity_id=activity.id, gear_id=default_gear.id, value=value
                        )
                    )
                    self.db.flush()
                    _recompute_gear_value_covered(self.db, default_gear.id)

        self.db.commit()
        self.db.refresh(activity)
        return {
            "success": True,
            "activity": _activity_to_json(activity, include_shoes=True, include_gear=True),
        }, None, 201

    def get_activity(self, user_id: int, activity_id: int) -> tuple[dict | None, str | None, int]:
        activity = self.db.scalar(
            select(Activity).where(Activity.id == activity_id, Activity.user_id == user_id)
        )
        if not activity:
            return None, "Activity not found", 404
        return {
            "success": True,
            "activity": _activity_to_json(activity, include_shoes=True, include_gear=True),
        }, None, 200

    def update_activity(
        self, user_id: int, activity_id: int, data: dict
    ) -> tuple[dict | None, str | None, int]:
        activity = self.db.scalar(
            select(Activity).where(Activity.id == activity_id, Activity.user_id == user_id)
        )
        if not activity:
            return None, "Activity not found", 404

        data = data or {}
        if "name" in data and data["name"] is not None:
            activity.name = str(data["name"]).strip() or activity.name
        if "date" in data and data["date"]:
            try:
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
        self.db.commit()
        self.db.refresh(activity)
        return {
            "success": True,
            "activity": _activity_to_json(activity, include_shoes=True, include_gear=True),
        }, None, 200

    def delete_activity(self, user_id: int, activity_id: int) -> tuple[dict | None, str | None, int]:
        activity = self.db.scalar(
            select(Activity).where(Activity.id == activity_id, Activity.user_id == user_id)
        )
        if not activity:
            return None, "Activity not found", 404
        affected_gear_ids = {u.gear_id for u in activity.activity_gear_usages}
        self.db.delete(activity)
        self.db.flush()
        for gid in affected_gear_ids:
            _recompute_gear_value_covered(self.db, gid)
        self.db.commit()
        return {"success": True}, None, 200

    def update_activity_shoes(
        self, user_id: int, activity_id: int, data: list
    ) -> tuple[dict | None, str | None, int]:
        activity = self.db.scalar(
            select(Activity).where(Activity.id == activity_id, Activity.user_id == user_id)
        )
        if not activity:
            return None, "Activity not found", 404

        if not isinstance(data, list):
            return None, "Expected array of { shoe_id, distance_km }", 400

        items = [item for item in data if item.get("shoe_id") is not None]
        shoe_ids = [item["shoe_id"] for item in items]
        if shoe_ids:
            count = self.db.scalar(
                select(func.count())
                .select_from(Gear)
                .where(
                    Gear.id.in_(shoe_ids),
                    Gear.user_id == user_id,
                    Gear.gear_type == "shoe",
                )
            )
            if count != len(set(shoe_ids)):
                return None, "Invalid shoe_id", 400

        total_activity = activity.total_distance_km
        if len(items) >= 2:
            for item in items:
                if "distance_km" not in item or item["distance_km"] is None:
                    return None, "distance_km required for each shoe when 2+ shoes remain", 400
            try:
                provided_sum = sum(float(item["distance_km"]) for item in items)
            except (TypeError, ValueError):
                return None, "Invalid distance_km", 400
            if abs(provided_sum - total_activity) > 1e-6:
                return None, f"Sum of distances must equal activity total ({total_activity} km)", 400
        elif len(items) == 1:
            if "distance_km" not in items[0] or items[0]["distance_km"] is None:
                items[0]["distance_km"] = total_activity

        old_gear_ids = {
            u.gear_id
            for u in self.db.scalars(
                select(ActivityGearUsage).where(ActivityGearUsage.activity_id == activity_id)
            ).all()
        }
        new_gear_ids = set(shoe_ids)
        affected_gear_ids = old_gear_ids | new_gear_ids

        self.db.execute(
            delete(ActivityGearUsage).where(ActivityGearUsage.activity_id == activity_id)
        )
        for item in items:
            gear_id = item["shoe_id"]
            val = _round_km(item.get("distance_km", 0) or 0, 0.0)
            self.db.add(
                ActivityGearUsage(activity_id=activity_id, gear_id=gear_id, value=val)
            )

        self.db.flush()
        for gid in affected_gear_ids:
            _recompute_gear_value_covered(self.db, gid)
        self.db.commit()
        activity = self.db.get(Activity, activity_id)
        return {
            "success": True,
            "activity": _activity_to_json(activity, include_shoes=True),
        }, None, 200

    # --- Gear ---

    def list_gear(
        self, user_id: int, activity_type: str | None = None, gear_type: str | None = None
    ) -> dict:
        stmt = (
            select(Gear)
            .where(Gear.user_id == user_id)
            .order_by(Gear.created_at.desc())
        )
        if activity_type:
            stmt = stmt.where(Gear.activity_type == activity_type)
        if gear_type:
            stmt = stmt.where(Gear.gear_type == gear_type)
        gear_list = self.db.scalars(stmt).all()
        gear_ids = [g.id for g in gear_list]
        count_map = {}
        if gear_ids:
            count_rows = self.db.execute(
                select(GearInstallation.parent_gear_id, func.count(GearInstallation.id).label("cnt"))
                .where(
                    GearInstallation.parent_gear_id.in_(gear_ids),
                    GearInstallation.removed_at.is_(None),
                )
                .group_by(GearInstallation.parent_gear_id)
            ).all()
            count_map = {row.parent_gear_id: row.cnt for row in count_rows}
        return {
            "success": True,
            "gear": [_gear_to_json(g, components_count=count_map.get(g.id, 0)) for g in gear_list],
        }

    def create_gear(self, user_id: int, data: dict) -> tuple[dict | None, str | None, int]:
        data = data or {}
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
            return None, "brand and model are required", 400

        gear = Gear(
            user_id=user_id,
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
        self.db.add(gear)
        self.db.flush()
        if value_covered and value_covered > 0:
            self.db.add(ActivityGearUsage(activity_id=None, gear_id=gear.id, value=value_covered))
            self.db.flush()
            _recompute_gear_value_covered(self.db, gear.id)

        parent_gear_id = data.get("parent_gear_id")
        if gear_type == "component" and parent_gear_id is not None:
            parent = self.db.scalar(
                select(Gear).where(Gear.id == parent_gear_id, Gear.user_id == user_id)
            )
            if not parent:
                self.db.rollback()
                return None, "Parent gear not found", 400
            if parent.id == gear.id:
                self.db.rollback()
                return None, "Gear cannot be its own parent", 400
            if parent.gear_type == "component":
                self.db.rollback()
                return None, "Parent must not be a component (only 1 level hierarchy)", 400
            self.db.add(GearInstallation(child_gear_id=gear.id, parent_gear_id=parent_gear_id))
            self.db.flush()

        self.db.commit()
        self.db.refresh(gear)
        return {"success": True, "gear": _gear_to_json(gear)}, None, 201

    def get_gear(self, user_id: int, gear_id: int) -> tuple[dict | None, str | None, int]:
        gear = self.db.scalar(
            select(Gear).where(Gear.id == gear_id, Gear.user_id == user_id)
        )
        if not gear:
            return None, "Gear not found", 404
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
        out["services"] = [_service_to_json(s) for s in gear.gear_services]
        return {"success": True, "gear": out}, None, 200

    def update_gear(
        self, user_id: int, gear_id: int, data: dict
    ) -> tuple[dict | None, str | None, int]:
        gear = self.db.scalar(
            select(Gear).where(Gear.id == gear_id, Gear.user_id == user_id)
        )
        if not gear:
            return None, "Gear not found", 404

        data = data or {}
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
                activity_linked = self.db.scalar(
                    select(func.coalesce(func.sum(ActivityGearUsage.value), 0)).where(
                        ActivityGearUsage.gear_id == gear_id,
                        ActivityGearUsage.activity_id.isnot(None),
                    )
                )
                manual_delta = round(new_total - float(activity_linked), 2)
                manual_row = self.db.scalar(
                    select(ActivityGearUsage).where(
                        ActivityGearUsage.gear_id == gear_id,
                        ActivityGearUsage.activity_id.is_(None),
                    )
                )
                if manual_row:
                    manual_row.value = manual_delta
                else:
                    self.db.add(ActivityGearUsage(activity_id=None, gear_id=gear_id, value=manual_delta))
                self.db.flush()
                _recompute_gear_value_covered(self.db, gear_id)
            except (TypeError, ValueError):
                pass

        if "parent_gear_id" in data and gear.gear_type == "component":
            parent_gear_id = data["parent_gear_id"]
            for inst in self.db.scalars(
                select(GearInstallation).where(
                    GearInstallation.child_gear_id == gear_id,
                    GearInstallation.removed_at.is_(None),
                )
            ).all():
                inst.removed_at = datetime.now(timezone.utc)
            if parent_gear_id is not None:
                parent = self.db.scalar(
                    select(Gear).where(Gear.id == parent_gear_id, Gear.user_id == user_id)
                )
                if not parent:
                    return None, "Parent gear not found", 400
                if parent.id == gear_id:
                    return None, "Gear cannot be its own parent", 400
                if parent.gear_type == "component":
                    return None, "Parent must not be a component (only 1 level hierarchy)", 400
                self.db.add(GearInstallation(child_gear_id=gear_id, parent_gear_id=parent_gear_id))
            self.db.flush()

        self.db.commit()
        self.db.refresh(gear)
        return {"success": True, "gear": _gear_to_json(gear)}, None, 200

    def delete_gear(self, user_id: int, gear_id: int) -> tuple[dict | None, str | None, int]:
        gear = self.db.scalar(
            select(Gear).where(Gear.id == gear_id, Gear.user_id == user_id)
        )
        if not gear:
            return None, "Gear not found", 404
        self.db.delete(gear)
        self.db.commit()
        return {"success": True}, None, 200

    def set_default_gear(self, user_id: int, gear_id: int) -> tuple[dict | None, str | None, int]:
        gear = self.db.scalar(
            select(Gear).where(Gear.id == gear_id, Gear.user_id == user_id)
        )
        if not gear:
            return None, "Gear not found", 404
        for g in self.db.scalars(
            select(Gear).where(Gear.user_id == user_id, Gear.activity_type == gear.activity_type)
        ).all():
            g.is_default = False
        gear.is_default = True
        self.db.commit()
        self.db.refresh(gear)
        return {"success": True, "gear": _gear_to_json(gear)}, None, 200

    def unset_default_gear(self, user_id: int, gear_id: int) -> tuple[dict | None, str | None, int]:
        gear = self.db.scalar(
            select(Gear).where(Gear.id == gear_id, Gear.user_id == user_id)
        )
        if not gear:
            return None, "Gear not found", 404
        if gear.is_default:
            gear.is_default = False
            self.db.commit()
        self.db.refresh(gear)
        return {"success": True, "gear": _gear_to_json(gear)}, None, 200

    def get_gear_components(self, user_id: int, gear_id: int) -> tuple[dict | None, str | None, int]:
        gear = self.db.scalar(
            select(Gear).where(Gear.id == gear_id, Gear.user_id == user_id)
        )
        if not gear:
            return None, "Gear not found", 404
        if gear.gear_type == "component":
            return None, "Components cannot have child components (only 1 level)", 400
        installations = [i for i in gear.as_parent_installations if i.removed_at is None]
        components = []
        for inst in installations:
            child = inst.child_gear
            item = _gear_to_json(child)
            item["installation_id"] = inst.id
            item["installed_at"] = inst.installed_at.isoformat() if inst.installed_at else None
            components.append(item)
        return {"success": True, "components": components}, None, 200

    def create_gear_installation(
        self, user_id: int, gear_id: int, data: dict
    ) -> tuple[dict | None, str | None, int]:
        child = self.db.scalar(
            select(Gear).where(Gear.id == gear_id, Gear.user_id == user_id)
        )
        if not child:
            return None, "Gear not found", 404
        data = data or {}
        parent_id = data.get("parent_gear_id")
        if not parent_id:
            return None, "parent_gear_id required", 400
        parent = self.db.scalar(
            select(Gear).where(Gear.id == parent_id, Gear.user_id == user_id)
        )
        if not parent:
            return None, "Parent gear not found", 404
        for inst in self.db.scalars(
            select(GearInstallation).where(
                GearInstallation.child_gear_id == gear_id,
                GearInstallation.removed_at.is_(None),
            )
        ).all():
            inst.removed_at = datetime.now(timezone.utc)
        inst = GearInstallation(child_gear_id=gear_id, parent_gear_id=parent_id)
        self.db.add(inst)
        self.db.commit()
        self.db.refresh(inst)
        return {
            "success": True,
            "installation": {"id": inst.id, "parent_gear_id": inst.parent_gear_id},
        }, None, 201

    def remove_gear_installation(
        self, user_id: int, gear_id: int, installation_id: int
    ) -> tuple[dict | None, str | None, int]:
        inst = self.db.scalar(
            select(GearInstallation).where(GearInstallation.id == installation_id)
        )
        if not inst or inst.child_gear_id != gear_id:
            return None, "Installation not found", 404
        child = self.db.scalar(
            select(Gear).where(Gear.id == inst.child_gear_id, Gear.user_id == user_id)
        )
        if not child:
            return None, "Gear not found", 404
        inst.removed_at = datetime.now(timezone.utc)
        self.db.commit()
        return {"success": True}, None, 200

    def list_gear_services(self, user_id: int, gear_id: int) -> tuple[dict | None, str | None, int]:
        gear = self.db.scalar(
            select(Gear).where(Gear.id == gear_id, Gear.user_id == user_id)
        )
        if not gear:
            return None, "Gear not found", 404
        return {
            "success": True,
            "services": [_service_to_json(s) for s in gear.gear_services],
        }, None, 200

    def create_gear_service(
        self, user_id: int, gear_id: int, data: dict
    ) -> tuple[dict | None, str | None, int]:
        gear = self.db.scalar(
            select(Gear).where(Gear.id == gear_id, Gear.user_id == user_id)
        )
        if not gear:
            return None, "Gear not found", 404
        data = data or {}
        name = (data.get("name") or "").strip()
        interval_value = data.get("interval_value")
        interval_unit = (data.get("interval_unit") or "km").strip().lower()
        early_warning_ratio = data.get("early_warning_ratio")
        if not name:
            return None, "name required", 400
        try:
            interval_value = float(interval_value)
        except (TypeError, ValueError):
            return None, "interval_value required and numeric", 400
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
        self.db.add(svc)
        self.db.commit()
        self.db.refresh(svc)
        return {"success": True, "service": _service_to_json(svc)}, None, 201

    def update_gear_service(
        self, user_id: int, gear_id: int, service_id: int, data: dict
    ) -> tuple[dict | None, str | None, int]:
        gear = self.db.scalar(
            select(Gear).where(Gear.id == gear_id, Gear.user_id == user_id)
        )
        if not gear:
            return None, "Gear not found", 404
        svc = self.db.scalar(
            select(GearService).where(GearService.id == service_id, GearService.gear_id == gear_id)
        )
        if not svc:
            return None, "Service not found", 404
        data = data or {}
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
        self.db.commit()
        self.db.refresh(svc)
        return {"success": True, "service": _service_to_json(svc)}, None, 200

    def delete_gear_service(
        self, user_id: int, gear_id: int, service_id: int
    ) -> tuple[dict | None, str | None, int]:
        gear = self.db.scalar(
            select(Gear).where(Gear.id == gear_id, Gear.user_id == user_id)
        )
        if not gear:
            return None, "Gear not found", 404
        svc = self.db.scalar(
            select(GearService).where(GearService.id == service_id, GearService.gear_id == gear_id)
        )
        if not svc:
            return None, "Service not found", 404
        self.db.delete(svc)
        self.db.commit()
        return {"success": True}, None, 200

    def log_gear_service(
        self, user_id: int, gear_id: int, service_id: int
    ) -> tuple[dict | None, str | None, int]:
        gear = self.db.scalar(
            select(Gear).where(Gear.id == gear_id, Gear.user_id == user_id)
        )
        if not gear:
            return None, "Gear not found", 404
        svc = self.db.scalar(
            select(GearService).where(GearService.id == service_id, GearService.gear_id == gear_id)
        )
        if not svc:
            return None, "Service not found", 404
        value_at = gear.value_covered
        svc.last_performed_value = value_at
        log_entry = GearServiceLog(
            gear_service_id=service_id,
            performed_at=datetime.now(timezone.utc),
            value_at_perform=value_at,
        )
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        return {
            "success": True,
            "log": {
                "id": log_entry.id,
                "performed_at": log_entry.performed_at.isoformat(),
                "value_at_perform": value_at,
            },
        }, None, 201

    def retire_gear(self, user_id: int, gear_id: int) -> tuple[dict | None, str | None, int]:
        gear = self.db.scalar(
            select(Gear).where(Gear.id == gear_id, Gear.user_id == user_id)
        )
        if not gear:
            return None, "Gear not found", 404
        gear.status = "retired"
        self.db.commit()
        self.db.refresh(gear)
        return {"success": True, "gear": _gear_to_json(gear)}, None, 200

    def list_gear_alerts(self, user_id: int) -> dict:
        gear_list = self.db.scalars(
            select(Gear).where(Gear.user_id == user_id, Gear.status == "active")
        ).all()
        alerts = []
        for g in gear_list:
            if g.max_value is not None and g.value_covered >= g.max_value:
                alerts.append({
                    "gear_id": g.id,
                    "type": "max_value",
                    "message": f"Gear reached max value ({g.value_covered} >= {g.max_value})",
                })
            for s in g.gear_services:
                last = s.last_performed_value if s.last_performed_value is not None else 0
                since = g.value_covered - last
                if since >= s.interval_value:
                    alerts.append({
                        "gear_id": g.id,
                        "service_id": s.id,
                        "type": "service_overdue",
                        "message": f"Service '{s.name}' overdue",
                    })
                elif s.early_warning_ratio and since >= s.interval_value * s.early_warning_ratio:
                    alerts.append({
                        "gear_id": g.id,
                        "service_id": s.id,
                        "type": "service_warning",
                        "message": f"Service '{s.name}' due soon",
                    })
        return {"success": True, "alerts": alerts}

    def update_activity_gear(
        self, user_id: int, activity_id: int, data: list
    ) -> tuple[dict | None, str | None, int]:
        activity = self.db.scalar(
            select(Activity).where(Activity.id == activity_id, Activity.user_id == user_id)
        )
        if not activity:
            return None, "Activity not found", 404

        if not isinstance(data, list):
            return None, "Expected array of { gear_id, value? }", 400

        total_val = activity.total_distance_km or activity.total_hours or activity.total_sessions or 0
        items = []
        for item in data:
            gid = item.get("gear_id")
            if gid is None:
                continue
            gear = self.db.scalar(
                select(Gear).where(Gear.id == gid, Gear.user_id == user_id)
            )
            if not gear:
                return None, f"Invalid gear_id {gid}", 400
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
                return None, "Invalid value", 400
            if abs(provided_sum - total_val) > 1e-6:
                return None, "Sum of values must equal activity total", 400

        old_gear_ids = {u.gear_id for u in activity.activity_gear_usages}
        new_gear_ids = set()
        self.db.execute(
            delete(ActivityGearUsage).where(ActivityGearUsage.activity_id == activity_id)
        )
        for item in items:
            gid = item["gear_id"]
            val = item["value"]
            self.db.add(ActivityGearUsage(activity_id=activity_id, gear_id=gid, value=val))
            new_gear_ids.add(gid)
            gear = self.db.get(Gear, gid)
            if gear and gear.gear_type != "component":
                installed = [i for i in gear.as_parent_installations if i.removed_at is None]
                for inst in installed:
                    cid = inst.child_gear_id
                    if cid not in item.get("excluded_component_ids", set()):
                        self.db.add(ActivityGearUsage(activity_id=activity_id, gear_id=cid, value=val))
                        new_gear_ids.add(cid)
        affected = old_gear_ids | new_gear_ids
        self.db.flush()
        for gid in affected:
            _recompute_gear_value_covered(self.db, gid)
        self.db.commit()
        activity = self.db.get(Activity, activity_id)
        return {
            "success": True,
            "activity": _activity_to_json(activity, include_shoes=True, include_gear=True),
        }, None, 200
