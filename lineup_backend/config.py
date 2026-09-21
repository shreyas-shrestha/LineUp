"""Application configuration loaded from environment variables.

Every setting the backend reads lives here so ``.env.example`` and the docs can
be kept in sync with one file. Secrets are never logged: use :meth:`AppConfig.redacted`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

DEFAULT_ALLOWED_ORIGINS: List[str] = [
    "https://lineupai.onrender.com",
    "https://lineupai-api.onrender.com",
    r"^http://localhost(:\d+)?$",
    r"^http://127\.0\.0\.1(:\d+)?$",
]

# Rate-limit groups. Each can be overridden with LINEUP_RATE_<GROUP> (Flask-Limiter syntax).
DEFAULT_RATE_LIMITS: Dict[str, str] = {
    "global": "1000 per hour",      # default for every route
    "health": "200 per minute",     # /, /health, /config
    "read": "200 per hour",         # list/get endpoints
    "write": "60 per hour",         # create/update endpoints
    "engagement": "100 per hour",   # likes, comments, shares, follows
    "social_write": "20 per hour",  # creating feed posts (image upload + moderation)
    "ai": "10 per hour",            # /analyze (Gemini)
    "tryon": "20 per hour",         # /virtual-tryon (Replicate)
    "places": "50 per hour",        # /barbers search (Google Places)
    "ops": "10 per hour",           # /metrics, /cache-stats, /clear-cache
    "auth": "30 per hour",          # /auth/dev-login, /auth/onboarding
    "billing": "60 per hour",       # /billing/* (checkout, portal, dev grants)
    "webhook": "600 per hour",      # /billing/webhook (Stripe -> us)
}

SECRET_FIELDS = {
    "gemini_api_key",
    "google_places_api_key",
    "replicate_api_token",
    "cloudinary_api_key",
    "cloudinary_api_secret",
    "firebase_credentials",
    "firebase_web_config",
    "dev_secret",
    "stripe_secret_key",
    "stripe_webhook_secret",
    "admin_token",
}

_TRUE_VALUES = {"1", "true", "yes", "on"}


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def _env_bool(name: str, default: bool) -> bool:
    value = _env(name)
    if value is None:
        return default
    return value.lower() in _TRUE_VALUES


def _env_optional_bool(name: str) -> Optional[bool]:
    value = _env(name)
    if value is None:
        return None
    return value.lower() in _TRUE_VALUES


def _env_int(name: str, default: int) -> int:
    value = _env(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_list(name: str) -> List[str]:
    value = _env(name)
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


@dataclass
class AppConfig:
    """Runtime settings. Build with :meth:`from_env`; override fields for tests."""

    # Runtime
    env: str = "production"
    # Consumer launch: barber accounts, bookings, portfolios, packages and the
    # community feed stay off until LINEUP_BARBER_SIDE=true.
    barber_side: bool = False
    # Production refuses to boot on the in-memory store (a restart would wipe
    # every purchase). Set only for throwaway demo deploys.
    allow_memory_store: bool = False
    port: int = 5000
    log_level: str = "INFO"
    log_format: str = "text"
    trust_proxy: bool = False
    public_url: Optional[str] = None
    frontend_url: str = "https://lineupai.onrender.com"
    allowed_origins: List[str] = field(default_factory=lambda: list(DEFAULT_ALLOWED_ORIGINS))
    max_content_length: int = 12 * 1024 * 1024
    admin_token: Optional[str] = None  # gates /metrics, /cache-stats, /clear-cache outside development

    # Rate limiting
    ratelimit_enabled: bool = True
    ratelimit_storage_uri: str = "memory://"
    rate_limits: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_RATE_LIMITS))

    # Gemini (analysis, moderation, haircut matching)
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash"
    gemini_daily_limit: int = 50

    # Google Places (barber search, reviews, photos)
    google_places_api_key: Optional[str] = None
    places_daily_limit: int = 1700
    places_cache_ttl: int = 3600
    places_cache_max: int = 50

    # Replicate (virtual try-on)
    replicate_api_token: Optional[str] = None

    # Image storage
    cloudinary_cloud_name: Optional[str] = None
    cloudinary_api_key: Optional[str] = None
    cloudinary_api_secret: Optional[str] = None

    # Persistence
    firebase_credentials: Optional[str] = None  # service-account JSON as a string
    seed_mock_data: Optional[bool] = None  # None = auto (dev without Firestore)

    # Auth (Firebase ID tokens in production; signed dev JWTs locally)
    firebase_web_config: Optional[str] = None  # public web-app config JSON, handed to the browser via /config
    dev_secret: Optional[str] = None  # HS256 secret for dev-login JWTs (random per process when unset)
    dev_token_ttl: int = 7 * 24 * 3600  # seconds a dev-login token stays valid

    # Billing (Stripe) and metering
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_price_starter: Optional[str] = None
    stripe_price_plus: Optional[str] = None
    stripe_price_studio: Optional[str] = None
    stripe_price_barber_pro: Optional[str] = None
    max_analysis_per_day_per_user: int = 20
    max_tryon_per_day_per_user: int = 10
    max_barber_search_per_day_per_user: int = 40
    meter_mock: Optional[bool] = None  # charge credits for mock/preview responses? None = only outside production

    @classmethod
    def from_env(cls, **overrides: Any) -> "AppConfig":
        rate_limits = dict(DEFAULT_RATE_LIMITS)
        for key in rate_limits:
            rate_limits[key] = _env(f"LINEUP_RATE_{key.upper()}", rate_limits[key]) or rate_limits[key]

        values: Dict[str, Any] = dict(
            env=(_env("FLASK_ENV") or _env("ENV") or "production").lower(),
            barber_side=_env_bool("LINEUP_BARBER_SIDE", False),
            allow_memory_store=_env_bool("LINEUP_ALLOW_MEMORY_STORE", False),
            port=_env_int("PORT", 5000),
            log_level=(_env("LOG_LEVEL") or "INFO").upper(),
            log_format=(_env("LOG_FORMAT") or "text").lower(),
            trust_proxy=_env_bool("LINEUP_TRUST_PROXY", False),
            public_url=_env("LINEUP_PUBLIC_URL"),
            frontend_url=_env("LINEUP_FRONTEND_URL", "https://lineupai.onrender.com"),
            allowed_origins=_env_list("LINEUP_ALLOWED_ORIGINS") or list(DEFAULT_ALLOWED_ORIGINS),
            max_content_length=_env_int("MAX_CONTENT_LENGTH", 12 * 1024 * 1024),
            admin_token=_env("LINEUP_ADMIN_TOKEN"),
            ratelimit_enabled=_env_bool("RATELIMIT_ENABLED", True),
            ratelimit_storage_uri=_env("RATELIMIT_STORAGE_URI", "memory://"),
            rate_limits=rate_limits,
            gemini_api_key=_env("GEMINI_API_KEY"),
            gemini_model=_env("GEMINI_MODEL", "gemini-2.0-flash"),
            gemini_daily_limit=_env_int("LINEUP_GEMINI_DAILY_LIMIT", 50),
            google_places_api_key=_env("GOOGLE_PLACES_API_KEY"),
            places_daily_limit=_env_int("LINEUP_PLACES_DAILY_LIMIT", 1700),
            places_cache_ttl=_env_int("LINEUP_PLACES_CACHE_TTL", 3600),
            places_cache_max=_env_int("LINEUP_PLACES_CACHE_MAX", 50),
            replicate_api_token=_env("REPLICATE_API_TOKEN"),
            cloudinary_cloud_name=_env("CLOUDINARY_CLOUD_NAME"),
            cloudinary_api_key=_env("CLOUDINARY_API_KEY"),
            cloudinary_api_secret=_env("CLOUDINARY_API_SECRET"),
            firebase_credentials=_env("FIREBASE_CREDENTIALS"),
            seed_mock_data=_env_optional_bool("LINEUP_SEED_MOCK_DATA"),
            firebase_web_config=_env("FIREBASE_WEB_CONFIG"),
            dev_secret=_env("LINEUP_DEV_SECRET"),
            dev_token_ttl=_env_int("LINEUP_DEV_TOKEN_TTL", 7 * 24 * 3600),
            stripe_secret_key=_env("STRIPE_SECRET_KEY"),
            stripe_webhook_secret=_env("STRIPE_WEBHOOK_SECRET"),
            stripe_price_starter=_env("STRIPE_PRICE_STARTER"),
            stripe_price_plus=_env("STRIPE_PRICE_PLUS"),
            stripe_price_studio=_env("STRIPE_PRICE_STUDIO"),
            stripe_price_barber_pro=_env("STRIPE_PRICE_BARBER_PRO"),
            max_analysis_per_day_per_user=_env_int("MAX_ANALYSIS_PER_DAY_PER_USER", 20),
            max_tryon_per_day_per_user=_env_int("MAX_TRYON_PER_DAY_PER_USER", 10),
            max_barber_search_per_day_per_user=_env_int("MAX_BARBER_SEARCH_PER_DAY_PER_USER", 40),
            meter_mock=_env_optional_bool("LINEUP_METER_MOCK"),
        )
        unknown = set(overrides) - set(values)
        if unknown:
            raise TypeError(f"Unknown config overrides: {sorted(unknown)}")
        values.update(overrides)
        return cls(**values)

    # -- derived flags -----------------------------------------------------

    @property
    def is_development(self) -> bool:
        return self.env == "development"

    @property
    def is_testing(self) -> bool:
        return self.env == "testing"

    @property
    def is_production(self) -> bool:
        return not (self.is_development or self.is_testing)

    @property
    def debug(self) -> bool:
        return self.is_development

    @property
    def has_cloudinary(self) -> bool:
        return bool(self.cloudinary_cloud_name and self.cloudinary_api_key and self.cloudinary_api_secret)

    @property
    def consumer_only(self) -> bool:
        return not self.barber_side

    @property
    def has_firestore(self) -> bool:
        return bool(self.firebase_credentials)

    @property
    def require_persistent_store(self) -> bool:
        """Production must not run on memory: credits bought through Stripe would vanish on restart."""
        return self.is_production and not self.allow_memory_store

    @property
    def should_seed(self) -> bool:
        """Seed mock data when asked to, or in development without Firestore."""
        if self.seed_mock_data is not None:
            return self.seed_mock_data
        return self.is_development and not self.has_firestore

    @property
    def has_stripe(self) -> bool:
        return bool(self.stripe_secret_key)

    @property
    def dev_login_enabled(self) -> bool:
        """Dev login exists only outside production and only without Firebase Auth."""
        return not self.is_production and not self.has_firestore

    @property
    def charge_for_mock(self) -> bool:
        """Whether mock/preview responses cost credits (lets local demos exercise the 402 path)."""
        if self.meter_mock is not None:
            return self.meter_mock
        return not self.is_production

    @property
    def daily_caps(self) -> Dict[str, int]:
        return {
            "analysis": self.max_analysis_per_day_per_user,
            "tryon": self.max_tryon_per_day_per_user,
            "barber_search": self.max_barber_search_per_day_per_user,
        }

    def stripe_price_ids(self) -> Dict[str, Optional[str]]:
        return {
            "starter": self.stripe_price_starter,
            "plus": self.stripe_price_plus,
            "studio": self.stripe_price_studio,
            "barber_pro": self.stripe_price_barber_pro,
        }

    def firebase_web(self) -> Optional[Dict[str, Any]]:
        """Parsed FIREBASE_WEB_CONFIG (public keys only), or None."""
        if not self.firebase_web_config:
            return None
        try:
            data = json.loads(self.firebase_web_config)
        except ValueError:
            return None
        if not isinstance(data, dict):
            return None
        allowed = ("apiKey", "authDomain", "projectId", "appId", "storageBucket", "messagingSenderId", "measurementId")
        return {key: data[key] for key in allowed if isinstance(data.get(key), str)}

    def configured_integrations(self) -> Dict[str, bool]:
        """Which integrations have credentials (not whether they initialised)."""
        return {
            "gemini": bool(self.gemini_api_key),
            "google_places": bool(self.google_places_api_key),
            "replicate": bool(self.replicate_api_token),
            "cloudinary": self.has_cloudinary,
            "firestore": self.has_firestore,
            "firebase_auth": self.has_firestore,
            "stripe": self.has_stripe,
        }

    def redacted(self) -> Dict[str, Any]:
        """Config as a dict with secrets masked, safe for logs."""
        out: Dict[str, Any] = {}
        for key, value in self.__dict__.items():
            if key in SECRET_FIELDS:
                out[key] = "***" if value else None
            else:
                out[key] = value
        return out
