"""Tests for Supabase storage provider and the storage factory."""
from __future__ import annotations

import hashlib
from unittest.mock import MagicMock

import pytest

from src.modules.activity_import.local_storage import LocalFilesystemStorage
from src.modules.activity_import.supabase_storage import SupabaseStorage


def test_supabase_upload_posts_content_addressed_object(monkeypatch):
    posted = {}

    def fake_post(url, data=None, headers=None, timeout=None):
        posted["url"] = url
        posted["data"] = data
        posted["headers"] = headers
        response = MagicMock()
        response.status_code = 200
        response.text = ""
        return response

    monkeypatch.setattr("src.modules.activity_import.supabase_storage.requests.post", fake_post)

    storage = SupabaseStorage(
        url="https://example.supabase.co",
        service_role_key="service-role",
        bucket="activity-files",
    )
    data = b"fit-bytes"
    checksum = hashlib.sha256(data).hexdigest()
    metadata = storage.upload(data, filename="run.fit", content_type="application/vnd.ant.fit")

    assert metadata.provider == "supabase"
    assert metadata.bucket == "activity-files"
    assert metadata.object_key == f"fit-uploads/{checksum}.fit"
    assert metadata.checksum == checksum
    assert metadata.file_size == len(data)
    assert posted["url"] == (
        f"https://example.supabase.co/storage/v1/object/activity-files/fit-uploads/{checksum}.fit"
    )
    assert posted["data"] == data
    assert posted["headers"]["Authorization"] == "Bearer service-role"
    assert posted["headers"]["Content-Type"] == "application/vnd.ant.fit"
    assert posted["headers"]["x-upsert"] == "true"


def test_supabase_download_returns_bytes(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        response = MagicMock()
        response.status_code = 200
        response.content = b"stored-fit"
        return response

    monkeypatch.setattr("src.modules.activity_import.supabase_storage.requests.get", fake_get)
    storage = SupabaseStorage("https://example.supabase.co", "key", "activity-files")
    assert storage.download("fit-uploads/abc.fit") == b"stored-fit"


def test_supabase_download_404_raises_file_not_found(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        response = MagicMock()
        response.status_code = 404
        response.text = "not found"
        return response

    monkeypatch.setattr("src.modules.activity_import.supabase_storage.requests.get", fake_get)
    storage = SupabaseStorage("https://example.supabase.co", "key", "activity-files")
    with pytest.raises(FileNotFoundError, match="abc.fit"):
        storage.download("fit-uploads/abc.fit")


def test_build_storage_provider_dev_is_local(monkeypatch, tmp_path):
    monkeypatch.setattr("src.modules.activity_import.factory.IS_PRODUCTION", False)
    monkeypatch.setattr("src.modules.activity_import.factory.ACTIVITY_STORAGE_ROOT", tmp_path)
    from src.modules.activity_import.factory import build_storage_provider

    provider = build_storage_provider()
    assert isinstance(provider, LocalFilesystemStorage)


def test_build_storage_provider_production_requires_config(monkeypatch):
    monkeypatch.setattr("src.modules.activity_import.factory.IS_PRODUCTION", True)
    monkeypatch.setattr("src.modules.activity_import.factory.SUPABASE_URL", "")
    monkeypatch.setattr("src.modules.activity_import.factory.SUPABASE_SERVICE_ROLE_KEY", "")
    from src.modules.activity_import.factory import build_storage_provider

    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        build_storage_provider()


def test_build_storage_provider_production_uses_supabase(monkeypatch):
    monkeypatch.setattr("src.modules.activity_import.factory.IS_PRODUCTION", True)
    monkeypatch.setattr("src.modules.activity_import.factory.SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr("src.modules.activity_import.factory.SUPABASE_SERVICE_ROLE_KEY", "role-key")
    monkeypatch.setattr("src.modules.activity_import.factory.ACTIVITY_STORAGE_BUCKET", "fits")
    from src.modules.activity_import.factory import build_storage_provider

    provider = build_storage_provider()
    assert isinstance(provider, SupabaseStorage)
    assert provider._bucket == "fits"
