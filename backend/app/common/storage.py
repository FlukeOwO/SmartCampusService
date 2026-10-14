"""
Storage adapter - สลับ Local (dev) <-> Google Cloud Storage (cloud) ด้วย STORAGE_PROVIDER

- bucket บน cloud เป็น private: ไม่มี public URL, เปิดไฟล์ผ่าน V4 Signed URL อายุสั้นเท่านั้น
- บน Cloud Run ไม่มี private key ของ service account จึงเซ็นผ่าน IAM signBlob
  (service account ต้องมี roles/iam.serviceAccountTokenCreator บนตัวเอง)
- google-cloud-storage เป็น client แบบ blocking จึงเรียกผ่าน run_in_threadpool
"""

import logging
import threading
from abc import ABC, abstractmethod
from datetime import timedelta
from functools import lru_cache
from pathlib import Path, PurePosixPath

import aiofiles
from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.common.constants import ALLOWED_UPLOADS
from app.common.exceptions import PayloadTooLargeException, StorageException, ValidationException
from app.core.config import settings

logger = logging.getLogger(__name__)

_CHUNK = 64 * 1024


class StorageProvider(ABC):
    @abstractmethod
    async def save(self, key: str, data: bytes, content_type: str) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def signed_url(self, key: str, filename: str) -> str: ...


class LocalStorageProvider(StorageProvider):
    """เก็บไฟล์ใน volume ของเครื่อง dev และเสิร์ฟผ่าน /storage"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.base_path / key).resolve()
        if not path.is_relative_to(self.base_path):
            raise ValidationException("Invalid storage key")
        return path

    async def save(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)

    async def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    async def signed_url(self, key: str, filename: str) -> str:
        return f"/storage/{key}"


class GCSStorageProvider(StorageProvider):
    def __init__(self, bucket_name: str, project_id: str | None):
        import google.auth
        from google.cloud import storage

        self._credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        self._client = storage.Client(project=project_id, credentials=self._credentials)
        self._bucket = self._client.bucket(bucket_name)
        self._lock = threading.Lock()

    def _signing_kwargs(self) -> dict:
        from google.auth.credentials import Signing
        from google.auth.transport.requests import Request

        # มี private key (เช่น key file ตอน dev) -> เซ็นในเครื่องได้เลย
        if isinstance(self._credentials, Signing):
            return {}
        # Cloud Run (metadata server credentials) -> เซ็นผ่าน IAM signBlob
        with self._lock:
            if not self._credentials.valid:
                self._credentials.refresh(Request())
            return {
                "service_account_email": self._credentials.service_account_email,
                "access_token": self._credentials.token,
            }

    def _save(self, key: str, data: bytes, content_type: str) -> None:
        self._bucket.blob(key).upload_from_string(data, content_type=content_type)

    def _delete(self, key: str) -> None:
        from google.api_core.exceptions import NotFound

        try:
            self._bucket.blob(key).delete()
        except NotFound:
            pass

    def _signed_url(self, key: str, filename: str) -> str:
        return self._bucket.blob(key).generate_signed_url(
            version="v4",
            method="GET",
            expiration=timedelta(minutes=settings.SIGNED_URL_EXPIRE_MINUTES),
            response_disposition=f'inline; filename="{filename}"',
            **self._signing_kwargs(),
        )

    async def save(self, key: str, data: bytes, content_type: str) -> None:
        try:
            await run_in_threadpool(self._save, key, data, content_type)
        except Exception as exc:
            logger.exception("GCS upload failed for %s", key)
            raise StorageException() from exc

    async def delete(self, key: str) -> None:
        try:
            await run_in_threadpool(self._delete, key)
        except Exception:
            logger.exception("GCS delete failed for %s", key)

    async def signed_url(self, key: str, filename: str) -> str:
        try:
            return await run_in_threadpool(self._signed_url, key, filename)
        except Exception as exc:
            logger.exception("Signed URL generation failed for %s", key)
            raise StorageException("Could not create file URL") from exc


@lru_cache
def get_storage() -> StorageProvider:
    if settings.STORAGE_PROVIDER == "gcs":
        if not settings.GCS_BUCKET_NAME:
            raise RuntimeError("GCS_BUCKET_NAME must be set when STORAGE_PROVIDER=gcs")
        return GCSStorageProvider(settings.GCS_BUCKET_NAME, settings.GCS_PROJECT_ID or None)
    return LocalStorageProvider(settings.LOCAL_STORAGE_PATH)


async def read_validated_upload(file: UploadFile) -> tuple[bytes, str, str]:
    """
    อ่านไฟล์ทีละ chunk (หยุดทันทีเมื่อเกินขนาด) แล้วตรวจนามสกุล + magic bytes

    Returns: (data, extension, content_type)
    """
    original = PurePosixPath(file.filename or "")
    ext = original.suffix.lower()
    if ext not in ALLOWED_UPLOADS:
        raise ValidationException(
            f"File type '{ext or 'unknown'}' is not allowed",
            details={"allowed": sorted(ALLOWED_UPLOADS)},
        )

    limit = settings.max_upload_size_bytes
    buf = bytearray()
    while chunk := await file.read(_CHUNK):
        buf.extend(chunk)
        if len(buf) > limit:
            raise PayloadTooLargeException(
                f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit"
            )
    if not buf:
        raise ValidationException("File is empty")

    content_type, signatures = ALLOWED_UPLOADS[ext]
    if not any(bytes(buf).startswith(sig) for sig in signatures):
        raise ValidationException("File content does not match its extension")
    if ext == ".webp" and buf[8:12] != b"WEBP":
        raise ValidationException("File content does not match its extension")
    return bytes(buf), ext, content_type
