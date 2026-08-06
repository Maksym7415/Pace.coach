#!/usr/bin/env python3
"""
Dump ALL FIT messages/fields for workout-execution research.

Usage (from backend/):
  python -m scripts.dump_fit_all /path/to/activity.fit
  python -m scripts.dump_fit_all /path/to/activity.fit --out /tmp/fit_dump

Does not use or modify src.modules.fit_parser.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from typing import Any

import fitparse

FOCUS = {"workout", "workout_step", "event", "lap", "record"}


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Enum):
        return {"name": value.name, "value": value.value}
    if isinstance(value, bytes):
        return {"hex": value.hex(), "len": len(value)}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    # fitparse MessageType / FieldType / named values
    name = getattr(value, "name", None)
    raw = getattr(value, "value", None)
    if name is not None or raw is not None:
        if name is not None and raw is not None and raw is not value:
            return {"name": str(name), "value": _jsonable(raw)}
        if name is not None:
            return str(name)
        if raw is not value:
            return _jsonable(raw)
    return str(value)


def _field_entry(field_data: Any) -> dict[str, Any]:
    field = field_data.field
    field_type = getattr(field, "field_type", None) if field is not None else None
    is_dev = field_type == "devfield"
    entry: dict[str, Any] = {
        "name": field_data.name,
        "value": _jsonable(field_data.value),
        "raw_value": _jsonable(getattr(field_data, "raw_value", None)),
        "units": field_data.units or (getattr(field, "units", None) if field else None),
        "def_num": getattr(field_data, "def_num", None) or getattr(field, "def_num", None),
        "field_type": field_type,
        "is_developer_field": is_dev,
    }
    if is_dev and field is not None:
        entry["developer"] = {
            "units": getattr(field, "units", None),
            "native_field_num": getattr(field, "native_field_num", None),
            "app_id": _jsonable(getattr(field, "app_id", None)),
            "developer_data_index": getattr(field, "developer_data_index", None),
        }
    if field_data.name in (None, "") or str(field_data.name).startswith("unknown"):
        entry["unknown_or_unnamed"] = True
    return entry


def _message_dict(message: fitparse.records.FitMessage, index: int) -> dict[str, Any]:
    fields = [_field_entry(fd) for fd in message.fields]
    flat = {f["name"]: f["value"] for f in fields if f["name"] is not None}
    return {
        "index": index,
        "name": message.name,
        "mesg_num": _jsonable(
            getattr(message, "mesg_num", None) or getattr(message, "mesg_type", None)
        ),
        "fields": fields,
        "flat": flat,
        "field_names": [f["name"] for f in fields],
        "developer_field_names": [f["name"] for f in fields if f["is_developer_field"]],
    }


def _event_name(flat: dict[str, Any]) -> str:
    event = flat.get("event")
    if isinstance(event, dict):
        return str(event.get("name") or event.get("value") or "")
    return str(event or "")


def dump_fit(path: Path) -> dict[str, Any]:
    fit = fitparse.FitFile(str(path))

    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    type_counts: Counter[str] = Counter()
    field_universe: dict[str, set[str]] = defaultdict(set)
    unknown_field_hits: list[dict[str, Any]] = []

    for i, message in enumerate(fit.get_messages()):
        msg = _message_dict(message, i)
        name = message.name or f"unknown_mesg_{getattr(message, 'mesg_num', 'NA')}"
        type_counts[name] += 1
        by_type[name].append(msg)
        for f in msg["fields"]:
            field_universe[name].add(str(f["name"]))
            if f.get("unknown_or_unnamed"):
                unknown_field_hits.append(
                    {"message_type": name, "message_index": i, "field": f}
                )

    records = by_type.get("record", [])
    record_section = {
        "count": len(records),
        "field_names": sorted(field_universe.get("record", set())),
        "first_5": records[:5],
        "last_5": records[-5:] if len(records) > 5 else records,
        "omitted_middle_count": max(0, len(records) - 10) if len(records) > 10 else 0,
    }

    messages_out: dict[str, Any] = {}
    for name, msgs in sorted(by_type.items()):
        if name == "record":
            messages_out[name] = record_section
        else:
            messages_out[name] = {
                "count": len(msgs),
                "field_names": sorted(field_universe.get(name, set())),
                "messages": msgs,
            }

    events = by_type.get("event", [])
    laps = by_type.get("lap", [])
    workouts = by_type.get("workout", [])
    steps = by_type.get("workout_step", [])

    workout_related_events = [
        e
        for e in events
        if _event_name(e["flat"]).lower() in {"workout_step", "workout"}
    ]

    lap_triggers = Counter(str(lap["flat"].get("lap_trigger")) for lap in laps)
    wkt_step_indexes = [
        lap["flat"].get("wkt_step_index", lap["flat"].get("workout_step_index"))
        for lap in laps
    ]

    research_hints = {
        "has_workout_definition": len(workouts) > 0,
        "workout_step_definition_count": len(steps),
        "event_count": len(events),
        "workout_related_event_count": len(workout_related_events),
        "lap_count": len(laps),
        "lap_trigger_value_counts": dict(lap_triggers),
        "wkt_step_index_sequence": wkt_step_indexes,
        "laps_with_wkt_step_index": sum(1 for v in wkt_step_indexes if v is not None),
        "questions": {
            "stores_workout_step_transitions": (
                "LIKELY YES if event.event == workout_step (or workout) appears with timestamps; "
                "definition-only if only workout/workout_step exist without matching events"
            ),
            "step_boundaries_from_fit": (
                "Use lap.wkt_step_index (Garmin FIT field name; not workout_step_index). "
                "Index identifies authored step, not occurrence — repeats cycle the same index. "
                "Fallback is Event(workout_step) timestamps if present."
            ),
            "auto_vs_manual_laps": (
                "lap_trigger alone cannot separate Auto Lap from workout step boundaries when "
                "duration_type is distance/time (trigger reports why the lap closed). "
                "Prefer wkt_step_index continuity."
            ),
            "native_execution_data_available": (
                "Strong if wkt_step_index is present on laps; weaker if only prescribed "
                "WorkoutStep msgs; Event(workout_step) is rare on modern Garmin devices"
            ),
        },
    }

    return {
        "source_file": str(path.resolve()),
        "message_type_counts": dict(sorted(type_counts.items())),
        "message_types": sorted(type_counts.keys()),
        "focus_types_present": sorted(FOCUS & set(type_counts)),
        "focus_types_missing": sorted(FOCUS - set(type_counts)),
        "unknown_or_unnamed_fields": unknown_field_hits,
        "research_hints": research_hints,
        "messages": messages_out,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Dump all FIT fields for research")
    parser.add_argument("fit_file", type=Path)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory (default: /tmp/<fit_stem>_fit_dump)",
    )
    args = parser.parse_args()

    fit_path: Path = args.fit_file
    if not fit_path.exists():
        raise SystemExit(f"FIT not found: {fit_path}")

    out_dir = args.out or Path("/tmp") / f"{fit_path.stem}_fit_dump"
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = dump_fit(fit_path)

    full_path = out_dir / "fit_dump_full.json"
    full_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=_jsonable),
        encoding="utf-8",
    )

    for key in ("workout", "workout_step", "event", "lap", "record"):
        section = payload["messages"].get(key)
        if section is not None:
            (out_dir / f"{key}.json").write_text(
                json.dumps(section, indent=2, ensure_ascii=False, default=_jsonable),
                encoding="utf-8",
            )

    summary = {
        "source_file": payload["source_file"],
        "message_type_counts": payload["message_type_counts"],
        "focus_types_present": payload["focus_types_present"],
        "focus_types_missing": payload["focus_types_missing"],
        "research_hints": payload["research_hints"],
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=_jsonable),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2, default=_jsonable))
    print(f"\nWrote: {full_path}")
    print(f"Also: {out_dir}/{{workout,workout_step,event,lap,record,summary}}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
