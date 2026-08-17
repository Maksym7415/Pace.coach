"""Supabase Storage provider for production FIT uploads."""

from __future__ import annotations

import hashlib

import requests

from src.modules.activity_import.storage import StorageProvider, StoredFileMetadata

PROVIDER_NAME = "supabase"


class SupabaseStorage(StorageProvider):
    def __init__(self, url: str, service_role_key: str, bucket: str) -> None:
        self._url = url.rstrip("/")
        self._service_role_key = service_role_key
        self._bucket = bucket

    def upload(self, data: bytes, filename: str, content_type: str) -> StoredFileMetadata:
        checksum = hashlib.sha256(data).hexdigest()
        object_key = f"fit-uploads/{checksum}.fit"
        response = requests.post(
            self._object_url(object_key),
            data=data,
            headers=self._headers(content_type=content_type, upsert=True),
            timeout=60,
        )
        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"Supabase storage upload failed ({response.status_code}): {response.text}"
            )
        return StoredFileMetadata(
            provider=PROVIDER_NAME,
            bucket=self._bucket,
            object_key=object_key,
            checksum=checksum,
            file_size=len(data),
        )

    def download(self, object_key: str) -> bytes:
        response = requests.get(
            self._object_url(object_key),
            headers=self._headers(),
            timeout=60,
        )
        if response.status_code == 404:
            raise FileNotFoundError(f"Stored object not found: {object_key}")
        if response.status_code != 200:
            raise RuntimeError(
                f"Supabase storage download failed ({response.status_code}): {response.text}"
            )
        return response.content

    def _object_url(self, object_key: str) -> str:
        return f"{self._url}/storage/v1/object/{self._bucket}/{object_key}"

    def _headers(self, *, content_type: str | None = None, upsert: bool = False) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._service_role_key}",
            "apikey": self._service_role_key,
        }
        if content_type:
            headers["Content-Type"] = content_type
        if upsert:
            headers["x-upsert"] = "true"
        return headers
