"""Storage abstraction for uploaded activity files."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class StoredFileMetadata:
    provider: str
    bucket: str
    object_key: str
    checksum: str
    file_size: int


class StorageProvider(ABC):
    @abstractmethod
    def upload(self, data: bytes, filename: str, content_type: str) -> StoredFileMetadata:
        """Store file bytes and return metadata describing the stored object."""

    @abstractmethod
    def download(self, object_key: str) -> bytes:
        """Retrieve file bytes for the given object key."""
