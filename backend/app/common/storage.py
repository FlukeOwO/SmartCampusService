"""
Storage Abstraction Layer - Cloud-Ready File Storage
ใช้ Adapter Pattern เพื่อสลับระหว่าง Local Storage และ Google Cloud Storage

Architecture:
- StorageProvider (Abstract Interface)
- LocalStorageProvider (สำหรับ Development)
- GCSStorageProvider (สำหรับ Production บน GCP)
"""

import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

import aiofiles
from fastapi import UploadFile

from app.core.config import settings


# ============================================================================
# Storage Provider Interface (Abstract Base Class)
# ============================================================================


class StorageProvider(ABC):
    """
    Abstract Interface สำหรับ Storage Provider
    ทุก Provider ต้อง implement methods เหล่านี้
    """

    @abstractmethod
    async def upload_file(
        self,
        file: UploadFile,
        folder: str,
        filename: str | None = None,
    ) -> dict[str, str]:
        """
        Upload file และคืนค่า metadata
        
        Args:
            file: UploadFile object จาก FastAPI
            folder: โฟลเดอร์ปลายทาง (เช่น 'requests', 'avatars')
            filename: ชื่อไฟล์ (ถ้าไม่ระบุจะสร้างแบบ random)
        
        Returns:
            Dictionary ที่มี 'url', 'path', 'filename', 'size'
        """
        pass

    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """
        ลบไฟล์
        
        Args:
            file_path: Path ของไฟล์ที่ต้องการลบ
        
        Returns:
            True ถ้าลบสำเร็จ
        """
        pass

    @abstractmethod
    async def get_file_url(self, file_path: str) -> str:
        """
        สร้าง URL สำหรับเข้าถึงไฟล์
        
        Args:
            file_path: Path ของไฟล์
        
        Returns:
            Public URL
        """
        pass

    @abstractmethod
    async def file_exists(self, file_path: str) -> bool:
        """
        ตรวจสอบว่าไฟล์มีอยู่หรือไม่
        
        Args:
            file_path: Path ของไฟล์
        
        Returns:
            True ถ้าไฟล์มีอยู่
        """
        pass


# ============================================================================
# Local Storage Provider (สำหรับ Development)
# ============================================================================


class LocalStorageProvider(StorageProvider):
    """
    Local File System Storage Provider
    เก็บไฟล์ใน Local Volume (Docker Volume หรือ Local Directory)
    """

    def __init__(self, base_path: str):
        """
        Initialize Local Storage Provider
        
        Args:
            base_path: Base directory สำหรับเก็บไฟล์ (เช่น '/app/storage')
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, original_filename: str) -> str:
        """
        สร้างชื่อไฟล์แบบ unique
        Format: {timestamp}_{uuid}_{original_name}
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        # เก็บเฉพาะ extension
        ext = Path(original_filename).suffix
        safe_name = f"{timestamp}_{unique_id}{ext}"
        return safe_name

    async def upload_file(
        self,
        file: UploadFile,
        folder: str,
        filename: str | None = None,
    ) -> dict[str, str]:
        """Upload file ไปยัง Local Storage"""
        # สร้างชื่อไฟล์
        if filename is None:
            filename = self._generate_filename(file.filename or "unnamed")

        # สร้างโฟลเดอร์ปลายทาง
        target_folder = self.base_path / folder
        target_folder.mkdir(parents=True, exist_ok=True)

        # Path เต็มของไฟล์
        file_path = target_folder / filename
        relative_path = f"{folder}/{filename}"

        # เขียนไฟล์
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        # คำนวณขนาดไฟล์
        file_size = len(content)

        return {
            "url": f"/storage/{relative_path}",  # URL สำหรับเข้าถึง (ต้องมี Static Files route)
            "path": relative_path,
            "filename": filename,
            "size": file_size,
            "folder": folder,
        }

    async def delete_file(self, file_path: str) -> bool:
        """ลบไฟล์จาก Local Storage"""
        try:
            full_path = self.base_path / file_path
            if full_path.exists():
                full_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
            return False

    async def get_file_url(self, file_path: str) -> str:
        """สร้าง URL สำหรับเข้าถึงไฟล์"""
        return f"/storage/{file_path}"

    async def file_exists(self, file_path: str) -> bool:
        """ตรวจสอบว่าไฟล์มีอยู่หรือไม่"""
        full_path = self.base_path / file_path
        return full_path.exists()


# ============================================================================
# Google Cloud Storage Provider (สำหรับ Production)
# ============================================================================


class GCSStorageProvider(StorageProvider):
    """
    Google Cloud Storage Provider
    เก็บไฟล์บน GCS Bucket (Cloud-Ready)
    """

    def __init__(self, bucket_name: str, project_id: str | None = None):
        """
        Initialize GCS Storage Provider
        
        Args:
            bucket_name: GCS Bucket name
            project_id: GCP Project ID (optional)
        """
        from google.cloud import storage

        self.bucket_name = bucket_name
        self.client = storage.Client(project=project_id)
        self.bucket = self.client.bucket(bucket_name)

    def _generate_filename(self, original_filename: str) -> str:
        """สร้างชื่อไฟล์แบบ unique"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        ext = Path(original_filename).suffix
        safe_name = f"{timestamp}_{unique_id}{ext}"
        return safe_name

    async def upload_file(
        self,
        file: UploadFile,
        folder: str,
        filename: str | None = None,
    ) -> dict[str, str]:
        """Upload file ไปยัง GCS"""
        # สร้างชื่อไฟล์
        if filename is None:
            filename = self._generate_filename(file.filename or "unnamed")

        # Path ใน GCS (blob name)
        blob_name = f"{folder}/{filename}"
        blob = self.bucket.blob(blob_name)

        # อ่านข้อมูลไฟล์
        content = await file.read()

        # Upload ไป GCS (sync operation - ใน production อาจใช้ async library)
        blob.upload_from_string(
            content,
            content_type=file.content_type or "application/octet-stream",
        )

        # ทำให้ไฟล์เป็น public (ถ้าต้องการ)
        # blob.make_public()

        # คำนวณขนาดไฟล์
        file_size = len(content)

        return {
            "url": blob.public_url,  # Public URL
            "path": blob_name,
            "filename": filename,
            "size": file_size,
            "folder": folder,
            "bucket": self.bucket_name,
        }

    async def delete_file(self, file_path: str) -> bool:
        """ลบไฟล์จาก GCS"""
        try:
            blob = self.bucket.blob(file_path)
            blob.delete()
            return True
        except Exception as e:
            print(f"Error deleting file {file_path} from GCS: {e}")
            return False

    async def get_file_url(self, file_path: str) -> str:
        """สร้าง URL สำหรับเข้าถึงไฟล์"""
        blob = self.bucket.blob(file_path)
        return blob.public_url

    async def file_exists(self, file_path: str) -> bool:
        """ตรวจสอบว่าไฟล์มีอยู่ใน GCS หรือไม่"""
        blob = self.bucket.blob(file_path)
        return blob.exists()


# ============================================================================
# Storage Service (Factory Pattern)
# ============================================================================


class StorageService:
    """
    Storage Service - จัดการการเลือกใช้ Provider ตาม Configuration
    ใช้ Factory Pattern เพื่อสร้าง Provider ที่เหมาะสม
    """

    def __init__(self, provider: StorageProvider):
        self.provider = provider

    async def upload(
        self,
        file: UploadFile,
        folder: str = "uploads",
        filename: str | None = None,
        max_size_mb: int | None = None,
    ) -> dict[str, str]:
        """
        Upload file พร้อมตรวจสอบขนาด
        
        Args:
            file: UploadFile object
            folder: โฟลเดอร์ปลายทาง
            filename: ชื่อไฟล์ (optional)
            max_size_mb: ขนาดไฟล์สูงสุด (MB)
        
        Returns:
            File metadata dictionary
        
        Raises:
            ValueError: ถ้าไฟล์ใหญ่เกินกำหนด
        """
        # ตรวจสอบขนาดไฟล์
        if max_size_mb:
            content = await file.read()
            file_size_mb = len(content) / (1024 * 1024)
            
            if file_size_mb > max_size_mb:
                raise ValueError(
                    f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb} MB)"
                )
            
            # Reset file pointer
            await file.seek(0)

        return await self.provider.upload_file(file, folder, filename)

    async def delete(self, file_path: str) -> bool:
        """ลบไฟล์"""
        return await self.provider.delete_file(file_path)

    async def get_url(self, file_path: str) -> str:
        """ดึง URL ของไฟล์"""
        return await self.provider.get_file_url(file_path)

    async def exists(self, file_path: str) -> bool:
        """ตรวจสอบว่าไฟล์มีอยู่หรือไม่"""
        return await self.provider.file_exists(file_path)


# ============================================================================
# Storage Service Factory
# ============================================================================


def get_storage_service() -> StorageService:
    """
    Factory Function สำหรับสร้าง StorageService ตาม Configuration
    อ่านค่าจาก settings.STORAGE_PROVIDER
    
    Returns:
        StorageService instance with appropriate provider
    """
    if settings.STORAGE_PROVIDER == "gcs":
        # Google Cloud Storage (Production)
        if not settings.GCS_BUCKET_NAME:
            raise ValueError("GCS_BUCKET_NAME must be set when using GCS storage provider")
        
        provider = GCSStorageProvider(
            bucket_name=settings.GCS_BUCKET_NAME,
            project_id=settings.GCS_PROJECT_ID or None,
        )
    else:
        # Local Storage (Development)
        provider = LocalStorageProvider(base_path=settings.LOCAL_STORAGE_PATH)

    return StorageService(provider=provider)


# ============================================================================
# Utility Functions
# ============================================================================


def validate_file_type(filename: str, allowed_extensions: list[str]) -> bool:
    """
    ตรวจสอบ file extension
    
    Args:
        filename: ชื่อไฟล์
        allowed_extensions: List ของ extensions ที่อนุญาต (เช่น ['.jpg', '.png'])
    
    Returns:
        True ถ้า extension ถูกต้อง
    """
    ext = Path(filename).suffix.lower()
    return ext in allowed_extensions


def get_file_extension(filename: str) -> str:
    """ดึง file extension"""
    return Path(filename).suffix.lower()


# ตัวอย่างการใช้งาน:
# 
# from app.common.storage import get_storage_service
# 
# storage = get_storage_service()
# result = await storage.upload(
#     file=uploaded_file,
#     folder="requests",
#     max_size_mb=10
# )
# print(result['url'])  # URL สำหรับเข้าถึงไฟล์
