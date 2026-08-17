"""Factory for the activity file storage provider."""

from __future__ import annotations

from src.core.config import (
    ACTIVITY_STORAGE_BUCKET,
    ACTIVITY_STORAGE_ROOT,
    IS_PRODUCTION,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_URL,
)
from src.modules.activity_import.local_storage import LocalFilesystemStorage
from src.modules.activity_import.storage import StorageProvider
from src.modules.activity_import.supabase_storage import SupabaseStorage


def build_storage_provider() -> StorageProvider:
    """Return the storage backend for the current environment.

    Production uses Supabase Storage and fails fast when credentials are missing.
    Development uses the local filesystem.
    """
    if not IS_PRODUCTION:
        return LocalFilesystemStorage(ACTIVITY_STORAGE_ROOT)

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in production"
        )
    return SupabaseStorage(
        url=SUPABASE_URL,
        service_role_key=SUPABASE_SERVICE_ROLE_KEY,
        bucket=ACTIVITY_STORAGE_BUCKET,
    )
