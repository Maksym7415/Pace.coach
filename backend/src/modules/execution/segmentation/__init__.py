"""Segmentation strategies."""

from src.modules.execution.segmentation.device_step_index import DeviceStepIndexStrategy
from src.modules.execution.segmentation.lap_structure import LapStructureStrategy
from src.modules.execution.segmentation.manual import ManualStrategy
from src.modules.execution.segmentation.registry import SegmentationRegistry
from src.modules.execution.segmentation.signal import SignalSegmentationStrategy

__all__ = [
    "DeviceStepIndexStrategy",
    "LapStructureStrategy",
    "ManualStrategy",
    "SegmentationRegistry",
    "SignalSegmentationStrategy",
]
