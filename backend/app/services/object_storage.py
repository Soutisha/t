from pathlib import Path
from app.core.config import settings


class StorageError(RuntimeError):
    """Raised when an object cannot be safely stored or retrieved."""


def _validate_key(key: str) -> str:
    normalized = key.replace("\\\\", "/").strip("/")
    parts = Path(normalized).parts
    if not normalized or Path(normalized).is_absolute() or ".." in parts or normalized in (".",):
        raise StorageError("Invalid object key.")
    return normalized


class LocalObjectStorage:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.object_storage_local_dir).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            self.root.chmod(0o700)
        except OSError:
            pass

    def _path(self, key: str) -> Path:
        safe = _validate_key(key)
        target = (self.root / safe).resolve()
        if self.root not in target.parents:
            raise StorageError("Invalid object key.")
        return target

    def put(self, key: str, data: bytes, content_type: str) -> str:
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with target.open("xb") as stream:
                stream.write(data)
            target.chmod(0o600)
        except FileExistsError as exc:
            raise StorageError("Object already exists.") from exc
        except OSError as exc:
            raise StorageError("Object could not be stored.") from exc
        return _validate_key(key)

    def get(self, key: str) -> bytes:
        target = self._path(key)
        try:
            return target.read_bytes()
        except OSError as exc:
            raise StorageError("Object not found.") from exc

    def delete(self, key: str) -> None:
        target = self._path(key)
        try:
            target.unlink(missing_ok=True)
        except OSError as exc:
            raise StorageError("Object could not be deleted.") from exc

    def check(self) -> None:
        if not self.root.is_dir():
            raise StorageError("Local object storage is unavailable.")


class S3ObjectStorage:
    def __init__(self):
        if not settings.s3_bucket:
            raise StorageError("S3_BUCKET is not configured.")
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise StorageError("Install the cloud requirements to use S3.") from exc
        self.client = boto3.client(
            "s3",
            region_name=settings.s3_region or None,
            endpoint_url=settings.s3_endpoint_url or None,
            aws_access_key_id=settings.s3_access_key_id or None,
            aws_secret_access_key=settings.s3_secret_access_key or None,
            config=Config(s3={"addressing_style": "path"}),
        )
        self.bucket = settings.s3_bucket
        self.prefix = settings.s3_prefix.strip("/")

    def _key(self, key: str) -> str:
        clean = _validate_key(key)
        return f"{self.prefix}/{clean}" if self.prefix else clean

    def put(self, key: str, data: bytes, content_type: str) -> str:
        logical_key = _validate_key(key)
        try:
            request = {
                "Bucket": self.bucket,
                "Key": self._key(logical_key),
                "Body": data,
                "ContentType": content_type,
            }
            if settings.s3_server_side_encryption:
                request["ServerSideEncryption"] = settings.s3_server_side_encryption
            self.client.put_object(**request)
        except Exception as exc:
            raise StorageError("Object could not be stored in S3.") from exc
        return logical_key

    def get(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=self._key(key))
            return response["Body"].read()
        except Exception as exc:
            raise StorageError("Object could not be retrieved from S3.") from exc

    def delete(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=self._key(key))
        except Exception as exc:
            raise StorageError("Object could not be deleted from S3.") from exc

    def check(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception as exc:
            raise StorageError("S3 bucket is not reachable with the configured application identity.") from exc


def get_object_storage():
    if settings.object_storage_backend == "s3":
        return S3ObjectStorage()
    return LocalObjectStorage(settings.object_storage_local_dir or settings.trustvision_storage_dir)
