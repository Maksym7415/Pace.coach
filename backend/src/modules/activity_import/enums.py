"""Enums for the activity import pipeline."""

from enum import Enum


class ImportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ImportSource(str, Enum):
    FIT_UPLOAD = "fit_upload"
    GARMIN = "garmin"
    STRAVA = "strava"
    TRAINING_PEAKS = "training_peaks"
    COROS = "coros"
    WAHOO = "wahoo"
