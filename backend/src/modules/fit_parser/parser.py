"""Standalone FIT file parser."""

from __future__ import annotations

import io
from datetime import datetime, timedelta
from typing import Any

import fitparse
from fitparse.utils import FitCRCError, FitEOFError, FitHeaderError, FitParseError

from .errors import CorruptedFitFileError, InvalidFitFileError, UnsupportedFormatError
from .models import ActivityMeta, Lap, NormalizedActivity, TrackPoint
from .sport_mapping import map_sport

SEMICIRCLE_TO_DEGREES = 180.0 / (2**31)
MS_TO_KMH = 3.6
NATIVE_POWER_FIELD_NUM = 7


def _first_value(message: fitparse.records.FitMessage, *field_names: str) -> Any:
    for field_name in field_names:
        value = message.get_value(field_name)
        if value is not None:
            return value
    return None


def _semicircles_to_degrees(value: int | float | None) -> float | None:
    if value is None:
        return None
    return float(value) * SEMICIRCLE_TO_DEGREES


def _speed_ms_to_kmh(value: float | None) -> float | None:
    if value is None:
        return None
    return float(value) * MS_TO_KMH


def _pace_from_speed_kmh(speed_kmh: float | None) -> float | None:
    if speed_kmh is None or speed_kmh <= 0:
        return None
    return 60.0 / speed_kmh


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _running_power_from_developer_fields(message: fitparse.records.FitMessage) -> int | None:
    for field_data in message.fields:
        field = field_data.field
        if field is None or getattr(field, "field_type", None) != "devfield":
            continue

        name = (field.name or "").lower()
        units = (getattr(field, "units", None) or field_data.units or "").lower()
        native_field_num = getattr(field, "native_field_num", None)
        is_running_power = "running" in name and "power" in name
        if not is_running_power:
            continue
        if units not in ("", "w", "watts") and native_field_num not in (None, NATIVE_POWER_FIELD_NUM):
            continue

        value = _to_int(field_data.value)
        if value is not None:
            return value
    return None


def _collect_developer_fields(fit_file: fitparse.FitFile) -> dict[str, Any] | None:
    developer_fields: dict[str, Any] = {}
    for message in fit_file.get_messages():
        for field_data in message.fields:
            field = field_data.field
            if field is None or getattr(field, "field_type", None) != "devfield":
                continue

            entry = developer_fields.setdefault(
                field.name,
                {
                    "units": getattr(field, "units", None) or field_data.units,
                    "native_field_num": getattr(field, "native_field_num", None),
                    "message_types": set(),
                },
            )
            entry["message_types"].add(message.name)

    if not developer_fields:
        return None

    return {
        name: {
            "units": entry["units"],
            "native_field_num": entry["native_field_num"],
            "message_types": sorted(entry["message_types"]),
        }
        for name, entry in sorted(developer_fields.items())
    }


def _device_name_from_messages(
    file_id_messages: list[fitparse.records.FitMessage],
    device_info_messages: list[fitparse.records.FitMessage],
) -> str | None:
    for message in file_id_messages + device_info_messages:
        manufacturer = _first_value(message, "manufacturer")
        product = _first_value(message, "product_name", "product")
        parts = [str(part) for part in (manufacturer, product) if part is not None]
        if parts:
            return " ".join(parts)
    return None


def _end_time(start_time: datetime | None, duration_seconds: float | None) -> datetime | None:
    if start_time is None or duration_seconds is None:
        return None
    return start_time + timedelta(seconds=duration_seconds)


def _parse_laps(lap_messages: list[fitparse.records.FitMessage]) -> list[Lap]:
    laps: list[Lap] = []
    for index, message in enumerate(lap_messages, start=1):
        avg_speed_ms = _first_value(message, "enhanced_avg_speed", "avg_speed")
        avg_speed_kmh = _speed_ms_to_kmh(_to_float(avg_speed_ms))
        laps.append(
            Lap(
                lap_number=index,
                duration=_to_float(_first_value(message, "total_elapsed_time", "total_timer_time")),
                distance=_to_float(_first_value(message, "total_distance")),
                avg_hr=_to_int(_first_value(message, "avg_heart_rate")),
                max_hr=_to_int(_first_value(message, "max_heart_rate")),
                avg_power=_to_int(_first_value(message, "avg_power")),
                max_power=_to_int(_first_value(message, "max_power")),
                normalized_power=_to_int(_first_value(message, "normalized_power")),
                avg_motor_power=_to_int(_first_value(message, "avg_lev_motor_power")),
                max_motor_power=_to_int(_first_value(message, "max_lev_motor_power")),
                avg_speed=avg_speed_kmh,
                avg_pace=_pace_from_speed_kmh(avg_speed_kmh),
            )
        )
    return laps


def _parse_track_points(record_messages: list[fitparse.records.FitMessage]) -> list[TrackPoint]:
    track_points: list[TrackPoint] = []
    for message in record_messages:
        speed_ms = _first_value(message, "enhanced_speed", "speed")
        speed_kmh = _speed_ms_to_kmh(_to_float(speed_ms))
        track_points.append(
            TrackPoint(
                timestamp=_first_value(message, "timestamp"),
                latitude=_semicircles_to_degrees(_first_value(message, "position_lat")),
                longitude=_semicircles_to_degrees(_first_value(message, "position_long")),
                altitude=_to_float(_first_value(message, "enhanced_altitude", "altitude")),
                distance=_to_float(_first_value(message, "distance")),
                speed=speed_kmh,
                pace=_pace_from_speed_kmh(speed_kmh),
                heart_rate=_to_int(_first_value(message, "heart_rate")),
                cadence=_to_int(_first_value(message, "cadence")),
                power=_to_int(_first_value(message, "power")),
                accumulated_power=_to_int(_first_value(message, "accumulated_power")),
                motor_power=_to_int(_first_value(message, "motor_power")),
                temperature=_to_float(_first_value(message, "temperature")),
                running_power=_running_power_from_developer_fields(message),
                stride_length=_to_float(_first_value(message, "step_length")),
                vertical_oscillation=_to_float(_first_value(message, "vertical_oscillation")),
                ground_contact_time=_to_float(_first_value(message, "stance_time")),
                left_right_balance=_to_float(_first_value(message, "stance_time_balance")),
            )
        )
    return track_points


def _parse_activity_meta(
    session_message: fitparse.records.FitMessage,
    device_name: str | None,
) -> ActivityMeta:
    sport, activity_type = map_sport(
        _first_value(session_message, "sport"),
        _first_value(session_message, "sub_sport"),
    )
    start_time = _first_value(session_message, "start_time", "timestamp")
    duration = _to_float(_first_value(session_message, "total_elapsed_time"))
    avg_speed_ms = _first_value(session_message, "enhanced_avg_speed", "avg_speed")
    avg_speed_kmh = _speed_ms_to_kmh(_to_float(avg_speed_ms))

    return ActivityMeta(
        start_time=start_time,
        end_time=_end_time(start_time, duration),
        duration=duration,
        moving_time=_to_float(_first_value(session_message, "total_timer_time")),
        distance=_to_float(_first_value(session_message, "total_distance")),
        sport=sport,
        activity_type=activity_type,
        calories=_to_int(_first_value(session_message, "total_calories")),
        elevation_gain=_to_float(_first_value(session_message, "total_ascent")),
        elevation_loss=_to_float(_first_value(session_message, "total_descent")),
        avg_hr=_to_int(_first_value(session_message, "avg_heart_rate")),
        max_hr=_to_int(_first_value(session_message, "max_heart_rate")),
        avg_cadence=_to_int(_first_value(session_message, "avg_cadence")),
        avg_speed=avg_speed_kmh,
        avg_pace=_pace_from_speed_kmh(avg_speed_kmh),
        avg_power=_to_int(_first_value(session_message, "avg_power")),
        max_power=_to_int(_first_value(session_message, "max_power")),
        normalized_power=_to_int(_first_value(session_message, "normalized_power")),
        threshold_power=_to_int(_first_value(session_message, "threshold_power")),
        avg_motor_power=_to_int(_first_value(session_message, "avg_lev_motor_power")),
        max_motor_power=_to_int(_first_value(session_message, "max_lev_motor_power")),
        temperature=_to_float(_first_value(session_message, "avg_temperature")),
        device_name=device_name,
        source="fit",
    )


def _empty_activity_meta(device_name: str | None) -> ActivityMeta:
    return ActivityMeta(device_name=device_name, source="fit")


def _load_fit_file(data: bytes) -> fitparse.FitFile:
    if not data:
        raise InvalidFitFileError("FIT input is empty")

    try:
        return fitparse.FitFile(io.BytesIO(data))
    except FitHeaderError as exc:
        raise InvalidFitFileError(str(exc)) from exc
    except (FitEOFError, FitCRCError, FitParseError) as exc:
        raise CorruptedFitFileError(str(exc)) from exc


class FitParser:
    @staticmethod
    def parse(data: bytes) -> NormalizedActivity:
        fit_file = _load_fit_file(data)

        try:
            file_id_messages = list(fit_file.get_messages("file_id"))
            device_info_messages = list(fit_file.get_messages("device_info"))
            session_messages = list(fit_file.get_messages("session"))
            lap_messages = list(fit_file.get_messages("lap"))
            record_messages = list(fit_file.get_messages("record"))
        except (FitEOFError, FitCRCError, FitParseError) as exc:
            raise CorruptedFitFileError(str(exc)) from exc

        if len(session_messages) > 1:
            raise UnsupportedFormatError("Multiple session messages are not supported")

        device_name = _device_name_from_messages(file_id_messages, device_info_messages)
        meta = (
            _parse_activity_meta(session_messages[0], device_name)
            if session_messages
            else _empty_activity_meta(device_name)
        )

        return NormalizedActivity(
            meta=meta,
            laps=_parse_laps(lap_messages),
            track_points=_parse_track_points(record_messages),
            developer_fields=_collect_developer_fields(fit_file),
        )
