"""Tests for the standalone FIT parser."""

from datetime import datetime
from pathlib import Path

import pytest

from src.modules.fit_parser import (
    FitParser,
    InvalidFitFileError,
    NormalizedActivity,
    UnsupportedFormatError,
)
from src.modules.fit_parser.sport_mapping import map_sport

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_FIT = FIXTURES_DIR / "activity-small-fenix2-run.fit"


@pytest.fixture
def sample_fit_bytes() -> bytes:
    return SAMPLE_FIT.read_bytes()


def test_parse_sample_activity_returns_normalized_activity(sample_fit_bytes: bytes):
    result = FitParser.parse(sample_fit_bytes)

    assert isinstance(result, NormalizedActivity)
    assert result.meta.source == "fit"
    assert result.meta.sport == "running"
    assert result.meta.activity_type == "road_run"
    assert result.meta.distance == pytest.approx(9008.22)
    assert result.meta.duration == pytest.approx(2832.0)
    assert result.meta.moving_time == pytest.approx(2832.0)
    assert result.meta.calories == 516
    assert result.meta.elevation_gain == pytest.approx(64)
    assert result.meta.elevation_loss == pytest.approx(61)
    assert result.meta.avg_cadence == 81
    assert result.meta.device_name == "garmin fenix2"
    assert result.meta.start_time == datetime(2015, 8, 15, 14, 45, 8)
    assert result.meta.end_time == datetime(2015, 8, 15, 15, 32, 20)
    assert len(result.laps) == 4
    assert len(result.track_points) == 2809


def test_missing_optional_fields_are_none(sample_fit_bytes: bytes):
    result = FitParser.parse(sample_fit_bytes)

    assert result.meta.avg_hr is None
    assert result.meta.max_hr is None
    assert result.meta.avg_speed is None
    assert result.meta.avg_pace is None
    assert result.meta.avg_power is None
    assert result.meta.max_power is None
    assert result.meta.normalized_power is None
    assert result.meta.threshold_power is None
    assert result.meta.avg_motor_power is None
    assert result.meta.max_motor_power is None
    assert result.meta.temperature is None
    assert result.developer_fields is None


def test_lap_and_track_point_shape(sample_fit_bytes: bytes):
    result = FitParser.parse(sample_fit_bytes)

    first_lap = result.laps[0]
    assert first_lap.lap_number == 1
    assert first_lap.duration == pytest.approx(270.0)
    assert first_lap.distance == pytest.approx(848.94)
    assert first_lap.avg_hr is None
    assert first_lap.max_power is None
    assert first_lap.normalized_power is None
    assert first_lap.avg_motor_power is None
    assert first_lap.max_motor_power is None

    first_point = result.track_points[0]
    assert first_point.timestamp == datetime(2015, 8, 15, 14, 45, 8)
    assert first_point.latitude == pytest.approx(58.959183, rel=1e-4)
    assert first_point.longitude == pytest.approx(5.728839, rel=1e-4)
    assert first_point.speed == pytest.approx(21.204, rel=1e-3)
    assert first_point.pace == pytest.approx(2.8296, rel=1e-3)
    assert first_point.power is None
    assert first_point.accumulated_power is None
    assert first_point.motor_power is None
    assert first_point.running_power is None


def test_track_point_reads_distinct_native_power_fields():
    from fitparse.records import DevField, FieldData

    class FakeMessage:
        def __init__(self, values: dict[str, object], fields: list[FieldData] | None = None):
            self._values = values
            self.fields = fields or []

        def get_value(self, name: str):
            return self._values.get(name)

    from src.modules.fit_parser.parser import _parse_track_points

    running_power_field = DevField(
        dev_data_index=0,
        def_num=0,
        type=None,
        name="Running Power",
        units="watts",
        native_field_num=7,
        scale=None,
        offset=None,
        components=None,
        subfields=None,
    )
    developer_field = FieldData(
        field_def=None,
        field=running_power_field,
        parent_field=None,
        value=285,
        raw_value=285,
        units="watts",
    )

    points = _parse_track_points(
        [
            FakeMessage(
                {
                    "power": 250,
                    "accumulated_power": 100_000,
                    "motor_power": 50,
                },
                fields=[developer_field],
            )
        ]
    )

    point = points[0]
    assert point.power == 250
    assert point.accumulated_power == 100_000
    assert point.motor_power == 50
    assert point.running_power == 285


def test_invalid_bytes_raise_invalid_fit_file_error():
    with pytest.raises(InvalidFitFileError):
        FitParser.parse(b"not a fit file")


def test_empty_bytes_raise_invalid_fit_file_error():
    with pytest.raises(InvalidFitFileError):
        FitParser.parse(b"")


def test_truncated_fit_file_raises_corrupted_error(sample_fit_bytes: bytes):
    from src.modules.fit_parser.errors import CorruptedFitFileError

    with pytest.raises(CorruptedFitFileError):
        FitParser.parse(sample_fit_bytes[:128])


def test_deterministic_output(sample_fit_bytes: bytes):
    first = FitParser.parse(sample_fit_bytes)
    second = FitParser.parse(sample_fit_bytes)

    assert first.model_dump() == second.model_dump()


def test_unsupported_multi_session_format(monkeypatch):
    class FakeFitFile:
        def get_messages(self, name: str):
            if name == "session":
                return [object(), object()]
            return []

    monkeypatch.setattr(
        "src.modules.fit_parser.parser._load_fit_file",
        lambda _data: FakeFitFile(),
    )

    with pytest.raises(UnsupportedFormatError):
        FitParser.parse(b"ignored")


@pytest.mark.parametrize(
    ("sport", "sub_sport", "expected_sport", "expected_activity_type"),
    [
        (1, 3, "running", "trail_run"),
        (1, 1, "running", "treadmill_run"),
        (2, 7, "cycling", "gravel_ride"),
        (5, 18, "swimming", "open_water_swim"),
        ("running", "trail", "running", "trail_run"),
    ],
)
def test_sport_mapping(sport, sub_sport, expected_sport, expected_activity_type):
    mapped_sport, mapped_activity_type = map_sport(sport, sub_sport)
    assert mapped_sport == expected_sport
    assert mapped_activity_type == expected_activity_type
