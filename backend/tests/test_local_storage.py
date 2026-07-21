"""Tests for local filesystem storage provider."""

import hashlib

import pytest

from src.modules.activity_import.local_storage import LocalFilesystemStorage


@pytest.fixture
def storage(tmp_path):
    return LocalFilesystemStorage(tmp_path)


def test_upload_writes_file_and_returns_metadata(storage, tmp_path):
    data = b"fit-file-bytes"
    checksum = hashlib.sha256(data).hexdigest()

    metadata = storage.upload(data, filename="run.fit", content_type="application/vnd.ant.fit")

    assert metadata.provider == "local"
    assert metadata.bucket == "local"
    assert metadata.object_key == f"fit-uploads/{checksum}.fit"
    assert metadata.checksum == checksum
    assert metadata.file_size == len(data)
    assert (tmp_path / metadata.object_key).read_bytes() == data


def test_download_round_trips_bytes(storage):
    data = b"another-fit-file"
    metadata = storage.upload(data, filename="ride.fit", content_type="application/vnd.ant.fit")

    assert storage.download(metadata.object_key) == data


def test_same_checksum_produces_same_object_key(storage):
    data = b"same-content"
    checksum = hashlib.sha256(data).hexdigest()

    first = storage.upload(data, filename="a.fit", content_type="application/vnd.ant.fit")
    second = storage.upload(data, filename="b.fit", content_type="application/vnd.ant.fit")

    assert first.object_key == second.object_key == f"fit-uploads/{checksum}.fit"


def test_download_missing_key_raises_file_not_found(storage):
    with pytest.raises(FileNotFoundError, match="missing.fit"):
        storage.download("fit-uploads/missing.fit")
