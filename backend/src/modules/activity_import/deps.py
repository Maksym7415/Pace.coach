"""FastAPI dependencies for activity import module."""

from collections.abc import Callable

from fastapi import BackgroundTasks, Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.modules.activity_import.background import BackgroundTaskQueue, FastAPIBackgroundTaskQueue
from src.modules.activity_import.service import ActivityIngestionService
from src.modules.activity_import.storage import StorageProvider

_storage_provider: StorageProvider | None = None


def configure_storage_provider(provider: StorageProvider) -> None:
    """Register the concrete storage provider at application startup."""
    global _storage_provider
    _storage_provider = provider


def get_storage_provider() -> StorageProvider:
    if _storage_provider is None:
        raise RuntimeError(
            "StorageProvider is not configured. Call configure_storage_provider() at startup."
        )
    return _storage_provider


def get_background_task_queue(
    background_tasks: BackgroundTasks,
) -> BackgroundTaskQueue:
    return FastAPIBackgroundTaskQueue(background_tasks)


def get_ingestion_service(
    db: Session = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    queue: BackgroundTaskQueue = Depends(get_background_task_queue),
) -> ActivityIngestionService:
    return ActivityIngestionService(db=db, storage=storage, queue=queue)


class _NoOpBackgroundTaskQueue(BackgroundTaskQueue):
    def enqueue(self, func, *args, **kwargs) -> None:
        pass


def get_import_processor() -> Callable[[int], None]:
    """Return a callable that processes an import job outside the request lifecycle."""
    storage = get_storage_provider()
    service = ActivityIngestionService(
        db=None,  # type: ignore[arg-type]
        storage=storage,
        queue=_NoOpBackgroundTaskQueue(),
    )
    return service._process_import
