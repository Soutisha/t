from io import BytesIO
import sys
import types
import pytest

from app.core.config import settings
from app.services.object_storage import LocalObjectStorage, S3ObjectStorage, StorageError


def test_local_storage_round_trip_and_delete(tmp_path):
    storage = LocalObjectStorage(str(tmp_path / "private"))
    key = storage.put("evidence/item.png", b"image-bytes", "image/png")
    assert key == "evidence/item.png"
    assert storage.get(key) == b"image-bytes"
    storage.delete(key)
    with pytest.raises(StorageError):
        storage.get(key)


def test_local_storage_rejects_traversal(tmp_path):
    storage = LocalObjectStorage(str(tmp_path / "private"))
    with pytest.raises(StorageError):
        storage.put("../escape.txt", b"x", "text/plain")


def test_s3_storage_uses_prefix_and_round_trips(monkeypatch):
    calls = {"client": {}}
    objects = {}

    class FakeS3:
        def put_object(self, **kwargs):
            calls["put"] = kwargs
            objects[kwargs["Key"]] = kwargs["Body"]
        def get_object(self, **kwargs):
            calls["get"] = kwargs
            return {"Body": BytesIO(objects[kwargs["Key"]])}
        def delete_object(self, **kwargs):
            calls["delete"] = kwargs
            objects.pop(kwargs["Key"], None)
        def head_bucket(self, **kwargs):
            calls["head_bucket"] = kwargs

    def fake_client(*args, **kwargs):
        calls["client"] = kwargs
        return FakeS3()
    fake_boto3 = types.SimpleNamespace(client=fake_client)
    fake_botocore = types.ModuleType("botocore")
    fake_botocore_config = types.ModuleType("botocore.config")
    fake_botocore_config.Config = lambda **kwargs: kwargs
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setitem(sys.modules, "botocore", fake_botocore)
    monkeypatch.setitem(sys.modules, "botocore.config", fake_botocore_config)
    monkeypatch.setattr(settings, "s3_bucket", "pitstop-private")
    monkeypatch.setattr(settings, "s3_prefix", "pitstop")
    monkeypatch.setattr(settings, "s3_region", "us-east-1")
    monkeypatch.setattr(settings, "s3_endpoint_url", "http://minio:9000")
    monkeypatch.setattr(settings, "s3_server_side_encryption", "AES256")
    monkeypatch.setattr(settings, "s3_access_key_id", "pitstop-api")
    monkeypatch.setattr(settings, "s3_secret_access_key", "application-secret")
    storage = S3ObjectStorage()
    storage.check()
    assert calls["head_bucket"]["Bucket"] == "pitstop-private"
    assert calls["client"]["aws_access_key_id"] == "pitstop-api"
    assert calls["client"]["aws_secret_access_key"] == "application-secret"

    key = storage.put("evidence/abc.png", b"secure-image", "image/png")
    assert key == "evidence/abc.png"
    assert calls["put"]["Bucket"] == "pitstop-private"
    assert calls["put"]["Key"] == "pitstop/evidence/abc.png"
    assert calls["put"]["ServerSideEncryption"] == "AES256"
    assert storage.get(key) == b"secure-image"
    storage.delete(key)
    assert "pitstop/evidence/abc.png" not in objects


def test_s3_readiness_fails_closed_when_bucket_is_unavailable(monkeypatch):
    class UnavailableS3:
        def head_bucket(self, **kwargs):
            raise RuntimeError("private bucket unavailable")
    fake_boto3 = types.SimpleNamespace(client=lambda *args, **kwargs: UnavailableS3())
    fake_botocore = types.ModuleType("botocore")
    fake_botocore_config = types.ModuleType("botocore.config")
    fake_botocore_config.Config = lambda **kwargs: kwargs
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setitem(sys.modules, "botocore", fake_botocore)
    monkeypatch.setitem(sys.modules, "botocore.config", fake_botocore_config)
    monkeypatch.setattr(settings, "s3_bucket", "pitstop-private")
    monkeypatch.setattr(settings, "s3_access_key_id", "pitstop-api")
    monkeypatch.setattr(settings, "s3_secret_access_key", "application-secret")
    with pytest.raises(StorageError):
        S3ObjectStorage().check()
