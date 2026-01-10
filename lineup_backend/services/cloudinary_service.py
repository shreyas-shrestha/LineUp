"""Cloudinary service for image storage."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .base import BaseService

logger = logging.getLogger(__name__)


class CloudinaryService(BaseService):
    """Service for Cloudinary image storage operations."""

    def __init__(
        self,
        cloud_name: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
    ):
        super().__init__()
        self._cloud_name = cloud_name
        self._api_key = api_key
        self._api_secret = api_secret
        self._configured = False
        self._cloudinary = None
        self._uploader = None

        if cloud_name and api_key and api_secret:
            try:
                import cloudinary
                import cloudinary.uploader

                cloudinary.config(
                    cloud_name=cloud_name,
                    api_key=api_key,
                    api_secret=api_secret,
                )
                self._cloudinary = cloudinary
                self._uploader = cloudinary.uploader
                self._configured = True
                logger.info(f"Cloudinary configured: {cloud_name}")
            except ImportError:
                logger.warning("Cloudinary library not installed")
            except Exception as e:
                logger.error(f"Cloudinary configuration failed: {e}")

    def is_configured(self) -> bool:
        """Check if Cloudinary is properly configured."""
        return self._configured

    def health_check(self) -> Dict[str, Any]:
        """Return health information about Cloudinary service."""
        return {
            "configured": self.is_configured(),
            "cloud_name": self._cloud_name if self.is_configured() else None,
            "uploads_today": self._get_usage("uploads"),
        }

    def upload_image(
        self,
        image_bytes: bytes,
        folder: str = "lineup-community",
        format: str = "jpg",
    ) -> Optional[str]:
        """Upload an image to Cloudinary.
        
        Args:
            image_bytes: Raw image bytes
            folder: Cloudinary folder to upload to
            format: Output format
            
        Returns:
            Public URL of uploaded image, or None if upload failed
        """
        if not self.is_configured():
            logger.warning("Cloudinary not configured, cannot upload")
            return None

        try:
            result = self._uploader.upload(
                image_bytes,
                folder=folder,
                resource_type="image",
                format=format,
                quality="auto:good",
            )
            
            self._increment_usage("uploads")
            url = result.get("secure_url") or result.get("url")
            logger.info(f"Image uploaded to Cloudinary: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Cloudinary upload error: {e}")
            return None

    def delete_image(self, public_id: str) -> bool:
        """Delete an image from Cloudinary.
        
        Args:
            public_id: Cloudinary public ID of the image
            
        Returns:
            True if deleted successfully
        """
        if not self.is_configured():
            return False

        try:
            result = self._uploader.destroy(public_id)
            return result.get("result") == "ok"
        except Exception as e:
            logger.error(f"Cloudinary delete error: {e}")
            return False

    def get_optimized_url(
        self,
        url: str,
        width: int = 400,
        height: int = 400,
        crop: str = "fill",
    ) -> str:
        """Get an optimized/transformed URL for an image.
        
        Args:
            url: Original Cloudinary URL
            width: Target width
            height: Target height
            crop: Crop mode
            
        Returns:
            Transformed URL
        """
        if not self.is_configured() or "/upload/" not in url:
            return url

        # Insert transformation parameters
        transformation = f"w_{width},h_{height},c_{crop},q_auto"
        return url.replace("/upload/", f"/upload/{transformation}/")
