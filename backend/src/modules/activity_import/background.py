"""Background task queue abstraction."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from fastapi import BackgroundTasks


class BackgroundTaskQueue(ABC):
    @abstractmethod
    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """Schedule a callable to run asynchronously."""


class FastAPIBackgroundTaskQueue(BackgroundTaskQueue):
    def __init__(self, background_tasks: BackgroundTasks) -> None:
        self._background_tasks = background_tasks

    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        self._background_tasks.add_task(func, *args, **kwargs)
