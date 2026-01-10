"""Centralized configuration helpers for the LineUp backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
import os


def _split_env_list(value: Optional[str]) -> List[str]:
    """Split a comma separated env var into a list, ignoring blanks."""
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


@dataclass
class AppConfig:
    """Application settings loaded from environment variables."""

    # External APIs
    gemini_api_key: Optional[str] = None
    google_places_api_key: Optional[str] = None
    replicate_api_token: Optional[str] = None
    huggingface_token: Optional[str] = None

    # Image/storage providers
    cloudinary_cloud_name: Optional[str] = None
    cloudinary_api_key: Optional[str] = None
    cloudinary_api_secret: Optional[str] = None
    firebase_credentials_json: Optional[str] = None

    # Runtime
    flask_env: str = "production"
    port: int = 5000
    allowed_origins: List[str] = field(
        default_factory=lambda: ["https://lineupai.onrender.com", "http://localhost:*"]
    )

    # Rate limiting defaults (strings to match Flask-Limiter syntax)
    global_rate_limit: str = "1000 per hour"
    appointment_rate_limit: str = "30 per hour"
    appointment_status_rate_limit: str = "50 per hour"
    appointments_list_rate_limit: str = "100 per hour"
    places_api_rate_limit: str = "50 per hour"
    ai_analysis_rate_limit: str = "10 per hour"
    virtual_tryon_rate_limit: str = "20 per hour"
    social_rate_limit: str = "20 per hour"
    social_read_rate_limit: str = "100 per hour"

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Build a config object from process environment variables."""
        allowed_origins = _split_env_list(os.environ.get("LINEUP_ALLOWED_ORIGINS"))
        if not allowed_origins:
            allowed_origins = ["https://lineupai.onrender.com", "http://localhost:*"]

        return cls(
            gemini_api_key=os.environ.get("GEMINI_API_KEY"),
            google_places_api_key=os.environ.get("GOOGLE_PLACES_API_KEY"),
            replicate_api_token=os.environ.get("REPLICATE_API_TOKEN"),
            huggingface_token=os.environ.get("HF_TOKEN"),
            cloudinary_cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
            cloudinary_api_key=os.environ.get("CLOUDINARY_API_KEY"),
            cloudinary_api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
            firebase_credentials_json=os.environ.get("FIREBASE_CREDENTIALS"),
            flask_env=os.environ.get("FLASK_ENV", os.environ.get("ENV", "production")),
            port=int(os.environ.get("PORT", 5000)),
            allowed_origins=allowed_origins,
            global_rate_limit=os.environ.get("LINEUP_GLOBAL_RATE", "1000 per hour"),
            appointment_rate_limit=os.environ.get("LINEUP_APPOINTMENT_RATE", "30 per hour"),
            appointment_status_rate_limit=os.environ.get(
                "LINEUP_APPOINTMENT_STATUS_RATE", "50 per hour"
            ),
            appointments_list_rate_limit=os.environ.get(
                "LINEUP_APPOINTMENTS_LIST_RATE", "100 per hour"
            ),
            places_api_rate_limit=os.environ.get("LINEUP_PLACES_RATE", "50 per hour"),
            ai_analysis_rate_limit=os.environ.get("LINEUP_AI_RATE", "10 per hour"),
            virtual_tryon_rate_limit=os.environ.get("LINEUP_TRYON_RATE", "20 per hour"),
            social_rate_limit=os.environ.get("LINEUP_SOCIAL_RATE", "20 per hour"),
            social_read_rate_limit=os.environ.get("LINEUP_SOCIAL_READ_RATE", "100 per hour"),
        )

    @property
    def cors_origins(self) -> List[str]:
        """Expose origins list for CORS setup."""
        if "*" in self.allowed_origins:
            return ["*"]
        return self.allowed_origins


