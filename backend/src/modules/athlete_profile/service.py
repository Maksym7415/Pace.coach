"""Athlete profile business logic."""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.modules.athlete_profile.models import (
    AthleteBaseline,
    AthleteBodyMetric,
    AthleteSport,
    AthleteSportProfile,
    AthleteZone,
    Sport,
)
from src.modules.athlete_profile.schemas import (
    BaselineUpsertRequest,
    BodyMetricCreateRequest,
    SportProfileUpsertRequest,
    ZoneCreateRequest,
)
from src.modules.identity.models import User

logger = logging.getLogger("coach_app.athlete_profile")


def _sport_to_dict(sport: Sport) -> dict:
    return {"id": sport.id, "code": sport.code, "name": sport.name}


def _athlete_sport_to_dict(athlete_sport: AthleteSport) -> dict:
    return {
        "id": athlete_sport.id,
        "sport": _sport_to_dict(athlete_sport.sport),
        "is_primary": athlete_sport.is_primary,
        "created_at": athlete_sport.created_at.isoformat() if athlete_sport.created_at else None,
    }


def _baseline_to_dict(baseline: AthleteBaseline) -> dict:
    return {
        "id": baseline.id,
        "athlete_id": baseline.athlete_id,
        "hrv_baseline_min": baseline.hrv_baseline_min,
        "hrv_baseline_max": baseline.hrv_baseline_max,
        "resting_hr_baseline": baseline.resting_hr_baseline,
        "created_at": baseline.created_at.isoformat() if baseline.created_at else None,
        "updated_at": baseline.updated_at.isoformat() if baseline.updated_at else None,
    }


def _body_metric_to_dict(metric: AthleteBodyMetric) -> dict:
    return {
        "id": metric.id,
        "athlete_id": metric.athlete_id,
        "weight_kg": metric.weight_kg,
        "height_cm": metric.height_cm,
        "measured_at": metric.measured_at.isoformat(),
        "created_at": metric.created_at.isoformat() if metric.created_at else None,
    }


def _sport_profile_to_dict(profile: AthleteSportProfile) -> dict:
    return {
        "id": profile.id,
        "athlete_id": profile.athlete_id,
        "sport": _sport_to_dict(profile.sport),
        "threshold_pace_sec_per_km": profile.threshold_pace_sec_per_km,
        "threshold_hr": profile.threshold_hr,
        "ftp_watts": profile.ftp_watts,
        "css_pace_sec_per_100m": profile.css_pace_sec_per_100m,
        "zone_source": profile.zone_source,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


def _zone_to_dict(zone: AthleteZone) -> dict:
    return {
        "id": zone.id,
        "athlete_sport_profile_id": zone.athlete_sport_profile_id,
        "zone_category": zone.zone_category,
        "zone_name": zone.zone_name,
        "min_value": zone.min_value,
        "max_value": zone.max_value,
        "created_at": zone.created_at.isoformat() if zone.created_at else None,
    }


class AthleteProfileService:
    def __init__(self, db: Session):
        self.db = db

    def list_sports(self) -> dict:
        sports = self.db.scalars(
            select(Sport).where(Sport.is_active.is_(True)).order_by(Sport.name)
        ).all()
        return {"sports": [_sport_to_dict(s) for s in sports], "count": len(sports)}

    def get_athlete_sports(self, athlete_id: int) -> dict:
        rows = self.db.scalars(
            select(AthleteSport)
            .options(joinedload(AthleteSport.sport))
            .where(AthleteSport.athlete_id == athlete_id)
            .order_by(AthleteSport.is_primary.desc(), AthleteSport.id)
        ).all()
        return {
            "sports": [_athlete_sport_to_dict(r) for r in rows],
            "count": len(rows),
        }

    def _get_sport(self, sport_id: int) -> Sport | None:
        return self.db.scalar(
            select(Sport).where(Sport.id == sport_id, Sport.is_active.is_(True))
        )

    def add_athlete_sport(
        self, athlete_id: int, sport_id: int, is_primary: bool = False
    ) -> tuple[dict | None, str | None, int]:
        sport = self._get_sport(sport_id)
        if not sport:
            return None, "Sport not found", 404

        existing = self.db.scalar(
            select(AthleteSport).where(
                AthleteSport.athlete_id == athlete_id,
                AthleteSport.sport_id == sport_id,
            )
        )
        if existing:
            return None, "Athlete already has this sport", 409

        if is_primary:
            self._clear_primary_sport(athlete_id)

        row = AthleteSport(
            athlete_id=athlete_id,
            sport_id=sport_id,
            is_primary=is_primary,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        row = self.db.scalar(
            select(AthleteSport)
            .options(joinedload(AthleteSport.sport))
            .where(AthleteSport.id == row.id)
        )
        return {"sport": _athlete_sport_to_dict(row)}, None, 201

    def _clear_primary_sport(self, athlete_id: int) -> None:
        primaries = self.db.scalars(
            select(AthleteSport).where(
                AthleteSport.athlete_id == athlete_id,
                AthleteSport.is_primary.is_(True),
            )
        ).all()
        for row in primaries:
            row.is_primary = False

    def remove_athlete_sport(
        self, athlete_id: int, sport_id: int
    ) -> tuple[dict | None, str | None, int]:
        row = self.db.scalar(
            select(AthleteSport)
            .options(joinedload(AthleteSport.sport))
            .where(
                AthleteSport.athlete_id == athlete_id,
                AthleteSport.sport_id == sport_id,
            )
        )
        if not row:
            return None, "Sport not found for athlete", 404

        was_primary = row.is_primary
        self.db.delete(row)
        self.db.flush()

        if was_primary:
            remaining = self.db.scalar(
                select(AthleteSport)
                .where(AthleteSport.athlete_id == athlete_id)
                .order_by(AthleteSport.id)
            )
            if remaining:
                remaining.is_primary = True

        profile = self.db.scalar(
            select(AthleteSportProfile).where(
                AthleteSportProfile.athlete_id == athlete_id,
                AthleteSportProfile.sport_id == sport_id,
            )
        )
        if profile:
            self.db.delete(profile)

        self.db.commit()
        return {"removed": True}, None, 200

    def set_primary_sport(
        self, athlete_id: int, sport_id: int
    ) -> tuple[dict | None, str | None, int]:
        row = self.db.scalar(
            select(AthleteSport)
            .options(joinedload(AthleteSport.sport))
            .where(
                AthleteSport.athlete_id == athlete_id,
                AthleteSport.sport_id == sport_id,
            )
        )
        if not row:
            return None, "Sport not found for athlete", 404

        self._clear_primary_sport(athlete_id)
        row.is_primary = True
        self.db.commit()
        self.db.refresh(row)
        return {"sport": _athlete_sport_to_dict(row)}, None, 200

    def get_baseline(self, athlete_id: int) -> tuple[dict | None, str | None, int]:
        baseline = self.db.scalar(
            select(AthleteBaseline).where(AthleteBaseline.athlete_id == athlete_id)
        )
        if not baseline:
            return None, "Baselines not configured", 404
        return {"baseline": _baseline_to_dict(baseline)}, None, 200

    def upsert_baseline(
        self, athlete_id: int, data: BaselineUpsertRequest
    ) -> tuple[dict | None, str | None, int]:
        if (
            data.hrv_baseline_min is not None
            and data.hrv_baseline_max is not None
            and data.hrv_baseline_min > data.hrv_baseline_max
        ):
            return None, "hrv_baseline_min cannot exceed hrv_baseline_max", 400

        baseline = self.db.scalar(
            select(AthleteBaseline).where(AthleteBaseline.athlete_id == athlete_id)
        )
        if baseline:
            baseline.hrv_baseline_min = data.hrv_baseline_min
            baseline.hrv_baseline_max = data.hrv_baseline_max
            baseline.resting_hr_baseline = data.resting_hr_baseline
            self.db.commit()
            self.db.refresh(baseline)
            return {"baseline": _baseline_to_dict(baseline)}, None, 200

        baseline = AthleteBaseline(
            athlete_id=athlete_id,
            hrv_baseline_min=data.hrv_baseline_min,
            hrv_baseline_max=data.hrv_baseline_max,
            resting_hr_baseline=data.resting_hr_baseline,
        )
        self.db.add(baseline)
        self.db.commit()
        self.db.refresh(baseline)
        return {"baseline": _baseline_to_dict(baseline)}, None, 201

    def add_body_metric(
        self, athlete_id: int, data: BodyMetricCreateRequest
    ) -> tuple[dict | None, str | None, int]:
        if data.weight_kg is None and data.height_cm is None:
            return None, "At least one of weight_kg or height_cm is required", 400

        metric = AthleteBodyMetric(
            athlete_id=athlete_id,
            weight_kg=data.weight_kg,
            height_cm=data.height_cm,
            measured_at=data.measured_at,
        )
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        return {"metric": _body_metric_to_dict(metric)}, None, 201

    def list_body_metrics(
        self, athlete_id: int, limit: int = 20
    ) -> tuple[dict | None, str | None, int]:
        limit = min(limit, 100)
        metrics = self.db.scalars(
            select(AthleteBodyMetric)
            .where(AthleteBodyMetric.athlete_id == athlete_id)
            .order_by(AthleteBodyMetric.measured_at.desc(), AthleteBodyMetric.id.desc())
            .limit(limit)
        ).all()
        result = [_body_metric_to_dict(m) for m in metrics]
        return {"metrics": result, "count": len(result)}, None, 200

    def _get_or_create_sport_profile(
        self, athlete_id: int, sport_id: int
    ) -> AthleteSportProfile | None:
        sport = self._get_sport(sport_id)
        if not sport:
            return None

        profile = self.db.scalar(
            select(AthleteSportProfile)
            .options(joinedload(AthleteSportProfile.sport))
            .where(
                AthleteSportProfile.athlete_id == athlete_id,
                AthleteSportProfile.sport_id == sport_id,
            )
        )
        if profile:
            return profile

        enrolled = self.db.scalar(
            select(AthleteSport).where(
                AthleteSport.athlete_id == athlete_id,
                AthleteSport.sport_id == sport_id,
            )
        )
        if not enrolled:
            return None

        profile = AthleteSportProfile(athlete_id=athlete_id, sport_id=sport_id)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return self.db.scalar(
            select(AthleteSportProfile)
            .options(joinedload(AthleteSportProfile.sport))
            .where(AthleteSportProfile.id == profile.id)
        )

    def get_sport_profile(
        self, athlete_id: int, sport_id: int
    ) -> tuple[dict | None, str | None, int]:
        profile = self.db.scalar(
            select(AthleteSportProfile)
            .options(joinedload(AthleteSportProfile.sport))
            .where(
                AthleteSportProfile.athlete_id == athlete_id,
                AthleteSportProfile.sport_id == sport_id,
            )
        )
        if not profile:
            return None, "Sport profile not found", 404
        return {"profile": _sport_profile_to_dict(profile)}, None, 200

    def upsert_sport_profile(
        self, athlete_id: int, sport_id: int, data: SportProfileUpsertRequest
    ) -> tuple[dict | None, str | None, int]:
        profile = self._get_or_create_sport_profile(athlete_id, sport_id)
        if not profile:
            return None, "Athlete must be enrolled in this sport first", 404

        if data.threshold_pace_sec_per_km is not None:
            profile.threshold_pace_sec_per_km = data.threshold_pace_sec_per_km
        if data.threshold_hr is not None:
            profile.threshold_hr = data.threshold_hr
        if data.ftp_watts is not None:
            profile.ftp_watts = data.ftp_watts
        if data.css_pace_sec_per_100m is not None:
            profile.css_pace_sec_per_100m = data.css_pace_sec_per_100m
        if data.zone_source is not None:
            profile.zone_source = data.zone_source.value

        self.db.commit()
        self.db.refresh(profile)
        profile = self.db.scalar(
            select(AthleteSportProfile)
            .options(joinedload(AthleteSportProfile.sport))
            .where(AthleteSportProfile.id == profile.id)
        )
        return {"profile": _sport_profile_to_dict(profile)}, None, 200

    def list_zones(
        self, athlete_id: int, sport_id: int
    ) -> tuple[dict | None, str | None, int]:
        profile = self.db.scalar(
            select(AthleteSportProfile).where(
                AthleteSportProfile.athlete_id == athlete_id,
                AthleteSportProfile.sport_id == sport_id,
            )
        )
        if not profile:
            return None, "Sport profile not found", 404

        zones = self.db.scalars(
            select(AthleteZone)
            .where(AthleteZone.athlete_sport_profile_id == profile.id)
            .order_by(AthleteZone.zone_category, AthleteZone.min_value)
        ).all()
        result = [_zone_to_dict(z) for z in zones]
        return {"zones": result, "count": len(result)}, None, 200

    def create_zone(
        self, athlete_id: int, sport_id: int, data: ZoneCreateRequest
    ) -> tuple[dict | None, str | None, int]:
        if data.min_value > data.max_value:
            return None, "min_value cannot exceed max_value", 400

        profile = self._get_or_create_sport_profile(athlete_id, sport_id)
        if not profile:
            return None, "Athlete must be enrolled in this sport first", 404

        zone = AthleteZone(
            athlete_sport_profile_id=profile.id,
            zone_category=data.zone_category.value,
            zone_name=data.zone_name.strip(),
            min_value=data.min_value,
            max_value=data.max_value,
        )
        self.db.add(zone)
        self.db.commit()
        self.db.refresh(zone)
        return {"zone": _zone_to_dict(zone)}, None, 201

    def delete_zone(
        self, athlete_id: int, zone_id: int
    ) -> tuple[dict | None, str | None, int]:
        zone = self.db.scalar(
            select(AthleteZone)
            .join(AthleteSportProfile)
            .where(
                AthleteZone.id == zone_id,
                AthleteSportProfile.athlete_id == athlete_id,
            )
        )
        if not zone:
            return None, "Zone not found", 404
        self.db.delete(zone)
        self.db.commit()
        return {"removed": True}, None, 200
