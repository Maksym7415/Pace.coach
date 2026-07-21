"""Local filesystem storage provider for dev FIT uploads."""

from __future__ import annotations

import hashlib
from pathlib import Path

from src.modules.activity_import.storage import StorageProvider, StoredFileMetadata

PROVIDER_NAME = "local"
BUCKET_NAME = "local"


class LocalFilesystemStorage(StorageProvider):
    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def upload(self, data: bytes, filename: str, content_type: str) -> StoredFileMetadata:
        checksum = hashlib.sha256(data).hexdigest()
        object_key = f"fit-uploads/{checksum}.fit"
        path = self._root / object_key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return StoredFileMetadata(
            provider=PROVIDER_NAME,
            bucket=BUCKET_NAME,
            object_key=object_key,
            checksum=checksum,
            file_size=len(data),
        )

    def download(self, object_key: str) -> bytes:
        path = self._root / object_key
        if not path.is_file():
            raise FileNotFoundError(f"Stored object not found: {object_key}")
        return path.read_bytes()
