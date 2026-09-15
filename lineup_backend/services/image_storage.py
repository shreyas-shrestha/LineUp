"""Uploads community images to Cloudinary or Firebase Storage. Returns None
when nothing is configured so callers keep the base64 payload instead."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ImageStorageService:
    def __init__(
        self,
        cloud_name: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        firebase_bucket: Any = None,
    ) -> None:
        self._cloudinary = None
        self.bucket = firebase_bucket
        if cloud_name and api_key and api_secret:
            try:
                import cloudinary
                import cloudinary.uploader  # noqa: F401

                cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)
                self._cloudinary = cloudinary
                logger.info("Cloudinary configured (cloud=%s)", cloud_name)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Cloudinary unavailable: %s", type(exc).__name__)

    @property
    def provider(self) -> Optional[str]:
        if self._cloudinary is not None:
            return "cloudinary"
        if self.bucket is not None:
            return "firebase"
        return None

    @property
    def configured(self) -> bool:
        return self.provider is not None

    def upload(self, image_bytes: bytes, folder: str = "lineup-community") -> Optional[str]:
        if self._cloudinary is not None:
            try:
                result = self._cloudinary.uploader.upload(
                    image_bytes, folder=folder, resource_type="image", format="jpg", quality="auto:good"
                )
                return result.get("secure_url") or result.get("url")
            except Exception as exc:  # noqa: BLE001
                logger.error("Cloudinary upload failed: %s", exc)
        if self.bucket is not None:
            try:
                blob = self.bucket.blob(f"community-posts/{uuid.uuid4()}_{int(time.time())}.jpg")
                blob.upload_from_string(image_bytes, content_type="image/jpeg")
                blob.make_public()
                return blob.public_url
            except Exception as exc:  # noqa: BLE001
                logger.error("Firebase Storage upload failed: %s", exc)
        return None
