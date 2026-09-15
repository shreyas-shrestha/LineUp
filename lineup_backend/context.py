"""Per-application service container. Routes call :func:`services`."""

from __future__ import annotations

from dataclasses import dataclass

from flask import current_app

from lineup_backend.config import AppConfig
from lineup_backend.services.auth import AuthService
from lineup_backend.services.barber_matcher import BarberMatcher
from lineup_backend.services.billing import Ledger
from lineup_backend.services.cache import TTLCache
from lineup_backend.services.gemini import GeminiService
from lineup_backend.services.image_storage import ImageStorageService
from lineup_backend.services.places import PlacesService
from lineup_backend.services.quota import DailyQuota
from lineup_backend.services.stripe_gateway import StripeGateway
from lineup_backend.services.tryon import TryOnService
from lineup_backend.storage import Store, create_store


@dataclass
class Services:
    config: AppConfig
    store: Store
    gemini: GeminiService
    places: PlacesService
    tryon: TryOnService
    images: ImageStorageService
    matcher: BarberMatcher
    gemini_quota: DailyQuota
    places_quota: DailyQuota
    places_cache: TTLCache
    ledger: Ledger
    auth: AuthService
    stripe: StripeGateway


def build_services(config: AppConfig) -> Services:
    store = create_store(config)
    gemini_quota = DailyQuota(config.gemini_daily_limit, "gemini")
    places_quota = DailyQuota(config.places_daily_limit, "places")
    gemini = GeminiService(config.gemini_api_key, config.gemini_model, gemini_quota)
    matcher = BarberMatcher(generate_text=gemini.generate_text)
    places_cache = TTLCache(config.places_cache_ttl, config.places_cache_max)
    places = PlacesService(config.google_places_api_key, places_quota, places_cache, matcher)
    tryon = TryOnService(config.replicate_api_token, gemini)
    images = ImageStorageService(
        config.cloudinary_cloud_name,
        config.cloudinary_api_key,
        config.cloudinary_api_secret,
        firebase_bucket=getattr(store, "bucket", None),
    )
    ledger = Ledger(store, config)
    auth = AuthService(config, store, ledger)
    stripe = StripeGateway(config.stripe_secret_key, config.stripe_webhook_secret, config.stripe_price_ids())
    return Services(
        config=config,
        store=store,
        gemini=gemini,
        places=places,
        tryon=tryon,
        images=images,
        matcher=matcher,
        gemini_quota=gemini_quota,
        places_quota=places_quota,
        places_cache=places_cache,
        ledger=ledger,
        auth=auth,
        stripe=stripe,
    )


def services() -> Services:
    return current_app.extensions["lineup"]
