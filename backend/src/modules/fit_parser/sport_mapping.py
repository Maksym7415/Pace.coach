"""Map FIT sport and sub-sport values to internal sport and activity type codes."""

from __future__ import annotations

_FIT_SPORT_TO_CODE: dict[int | str, str] = {
    0: "generic",
    1: "running",
    2: "cycling",
    3: "transition",
    4: "fitness_equipment",
    5: "swimming",
    6: "basketball",
    7: "soccer",
    8: "tennis",
    9: "american_football",
    10: "training",
    11: "walking",
    12: "cross_country_skiing",
    13: "alpine_skiing",
    14: "snowboarding",
    15: "rowing",
    16: "mountaineering",
    17: "hiking",
    18: "multisport",
    19: "paddling",
    20: "flying",
    21: "e_biking",
    22: "motorcycling",
    23: "boating",
    24: "driving",
    25: "golf",
    26: "hang_gliding",
    27: "horseback_riding",
    28: "hunting",
    29: "fishing",
    30: "play",
    31: "snow_shoeing",
    32: "snowmobiling",
    33: "stand_up_paddleboarding",
    34: "surfing",
    35: "wakeboarding",
    36: "water_skiing",
    37: "kayaking",
    38: "rafting",
    39: "windsurfing",
    40: "kitesurfing",
    41: "tactical",
    42: "jumpmaster",
    43: "boxing",
    44: "floor_climbing",
    45: "baseball",
    46: "diving",
    47: "hiit",
    48: "racket",
    49: "wheelchair_push_walk",
    50: "wheelchair_push_run",
    51: "meditation",
    52: "disc_golf",
    53: "cricket",
    54: "rugby",
    55: "hockey",
    56: "lacrosse",
    57: "volleyball",
    58: "water_tubing",
    59: "wakesurfing",
    60: "mixed_martial_arts",
    61: "snorkeling",
    62: "dance",
    63: "trail_running",
    64: "ultra_running",
    65: "gravel_cycling",
    66: "e_bike_mountain",
    67: "commuting",
    68: "hand_cycling",
    69: "indoor_climbing",
    70: "bouldering",
    71: "mountain_biking",
    "generic": "generic",
    "running": "running",
    "cycling": "cycling",
    "transition": "transition",
    "fitness_equipment": "fitness_equipment",
    "swimming": "swimming",
    "training": "training",
    "walking": "walking",
    "hiking": "hiking",
    "multisport": "multisport",
    "e_biking": "e_biking",
    "trail_running": "running",
    "gravel_cycling": "cycling",
    "mountain_biking": "cycling",
}

_RUNNING_ACTIVITY_TYPE: dict[int | str, str] = {
    0: "road_run",
    1: "treadmill_run",
    2: "road_run",
    3: "trail_run",
    4: "track_run",
    58: "road_run",
    "generic": "road_run",
    "treadmill": "treadmill_run",
    "street": "road_run",
    "trail": "trail_run",
    "track": "track_run",
    "virtual_activity": "road_run",
}

_CYCLING_ACTIVITY_TYPE: dict[int | str, str] = {
    0: "road_ride",
    1: "indoor_ride",
    2: "road_ride",
    3: "mtb_ride",
    4: "road_ride",
    5: "indoor_ride",
    6: "indoor_ride",
    7: "gravel_ride",
    8: "road_ride",
    9: "road_ride",
    10: "mtb_ride",
    11: "road_ride",
    12: "indoor_ride",
    13: "road_ride",
    14: "road_ride",
    15: "road_ride",
    16: "road_ride",
    17: "road_ride",
    18: "road_ride",
    19: "road_ride",
    20: "road_ride",
    21: "road_ride",
    22: "road_ride",
    23: "road_ride",
    24: "road_ride",
    25: "road_ride",
    26: "road_ride",
    27: "road_ride",
    28: "road_ride",
    29: "road_ride",
    30: "road_ride",
    31: "road_ride",
    32: "road_ride",
    33: "road_ride",
    34: "road_ride",
    35: "road_ride",
    36: "road_ride",
    37: "road_ride",
    38: "road_ride",
    39: "road_ride",
    40: "road_ride",
    41: "road_ride",
    42: "road_ride",
    43: "road_ride",
    44: "road_ride",
    45: "road_ride",
    46: "road_ride",
    47: "road_ride",
    48: "road_ride",
    49: "road_ride",
    50: "road_ride",
    51: "road_ride",
    52: "road_ride",
    53: "road_ride",
    54: "road_ride",
    55: "road_ride",
    "generic": "road_ride",
    "treadmill": "indoor_ride",
    "street": "road_ride",
    "trail": "mtb_ride",
    "track": "road_ride",
    "spin": "indoor_ride",
    "indoor_cycling": "indoor_ride",
    "gravel_cycling": "gravel_ride",
    "mountain": "mtb_ride",
    "virtual_activity": "indoor_ride",
}

_SWIMMING_ACTIVITY_TYPE: dict[int | str, str] = {
    0: "pool_swim",
    1: "pool_swim",
    2: "pool_swim",
    3: "pool_swim",
    4: "pool_swim",
    5: "pool_swim",
    17: "open_water_swim",
    18: "open_water_swim",
    "generic": "pool_swim",
    "lap_swimming": "pool_swim",
    "open_water": "open_water_swim",
}

_STRENGTH_ACTIVITY_TYPE: dict[int | str, str] = {
    0: "strength",
    "generic": "strength",
    "strength_training": "strength",
}


def _normalize_fit_enum(value: int | str | None) -> int | str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip().lower().replace(" ", "_")
    return value


def map_sport(sport: int | str | None, sub_sport: int | str | None = None) -> tuple[str | None, str | None]:
    """Return internal sport code and activity type code for FIT sport values."""
    sport_key = _normalize_fit_enum(sport)
    sub_sport_key = _normalize_fit_enum(sub_sport)

    sport_code = _FIT_SPORT_TO_CODE.get(sport_key) if sport_key is not None else None
    if sport_code is None:
        return None, None

    activity_type: str | None = None
    if sport_code == "running":
        activity_type = _RUNNING_ACTIVITY_TYPE.get(sub_sport_key or 0, "road_run")
    elif sport_code == "cycling":
        activity_type = _CYCLING_ACTIVITY_TYPE.get(sub_sport_key or 0, "road_ride")
    elif sport_code == "swimming":
        activity_type = _SWIMMING_ACTIVITY_TYPE.get(sub_sport_key or 0, "pool_swim")
    elif sport_code in {"training", "fitness_equipment"}:
        activity_type = _STRENGTH_ACTIVITY_TYPE.get(sub_sport_key or 0, "strength")

    return sport_code, activity_type
