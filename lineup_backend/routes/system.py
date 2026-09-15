"""Service info, health, capability flags and operational endpoints."""

from __future__ import annotations

import statistics

import hmac

from flask import Blueprint, jsonify, request

from lineup_backend import __version__
from lineup_backend.context import services
from lineup_backend.extensions import limiter, rate
from lineup_backend.http import now_iso
from lineup_backend.metrics import metrics
from lineup_backend.middleware.error_handler import ApiError

bp = Blueprint("system", __name__)


def require_ops_access() -> None:
    """Operational endpoints (/metrics, /cache-stats, /clear-cache) are for
    whoever runs the server, not for users. Access is granted when the request
    carries ``X-Admin-Token`` (or a bearer token) equal to ``LINEUP_ADMIN_TOKEN``;
    without a configured token they stay open only in dev auth mode. Anything
    else is a 404 so the endpoints are not advertised."""
    svc = services()
    expected = svc.config.admin_token
    if expected:
        supplied = request.headers.get("X-Admin-Token") or ""
        if not supplied:
            parts = request.headers.get("Authorization", "").split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                supplied = parts[1]
        if supplied and hmac.compare_digest(supplied, expected):
            return
    elif svc.auth.dev_login_enabled:
        return
    raise ApiError("Not found", 404, message="The requested resource does not exist")


@bp.get("/")
@limiter.limit(rate("health"))
def index():
    return jsonify(
        {
            "service": "LineUp API",
            "status": "running",
            "version": __version__,
            "endpoints": {
                "health": "/health",
                "config": "/config",
                "auth": "/auth/me, /auth/onboarding (POST), /auth/dev-login (POST, dev only)",
                "billing": "/billing/pricing, /billing/me, /billing/usage, /billing/checkout (POST), /billing/portal (POST), /billing/webhook (POST)",
                "analyze": "/analyze (POST)",
                "virtual_tryon": "/virtual-tryon (POST)",
                "barbers": "/barbers?location=City (GET)",
                "social": "/social (GET/POST)",
                "appointments": "/appointments (GET/POST)",
                "portfolio": "/portfolio (GET/POST)",
                "metrics": "/metrics",
            },
        }
    )


@bp.get("/health")
@limiter.limit(rate("health"))
def health():
    svc = services()
    cfg = svc.config
    svc.places_cache.prune()
    counts = svc.store.counts()
    return jsonify(
        {
            "status": "healthy",
            "service": "lineup-backend",
            "version": __version__,
            "timestamp": now_iso(),
            "environment": cfg.env,
            "storage": svc.store.kind,
            "integrations": {
                "gemini": svc.gemini.available,
                "google_places": svc.places.available,
                "replicate": svc.tryon.available,
                "cloudinary": svc.images.provider == "cloudinary",
                "firebase_storage": svc.images.provider == "firebase",
                "firestore": svc.store.kind == "firestore",
                "firebase_auth": svc.auth.mode == "firebase",
                "stripe": svc.stripe.available,
            },
            "auth_mode": svc.auth.mode,
            "cors_enabled": True,
            "gemini_configured": svc.gemini.available,
            "places_api_configured": svc.places.available,
            "cache_size": len(svc.places_cache),
            "frontend_url": cfg.frontend_url,
            "api_usage": {
                "places_api_calls_today": svc.places_quota.used,
                "gemini_api_calls_today": svc.gemini_quota.used,
                "daily_reset": svc.places_quota.reset_date.isoformat(),
            },
            "data_counts": {
                "social_posts": counts["social_posts"],
                "appointments": counts["appointments"],
                "barber_portfolios": counts["barber_portfolios"],
            },
        }
    )


@bp.get("/config")
@limiter.limit(rate("health"))
def config():
    """Capability flags only. Never exposes keys."""
    svc = services()
    return jsonify(
        {
            "hasPlacesApi": svc.places.available,
            "hasGeminiApi": svc.gemini.available,
            "hasCloudinary": svc.images.provider == "cloudinary",
            "hasFirebase": svc.store.kind == "firestore",
            "hasStripe": svc.stripe.available,
            "backendVersion": __version__,
            "auth": svc.auth.public_config(),
            "billing": {
                "stripe": svc.stripe.available,
                "pricingUrl": "/billing/pricing",
                "chargeForMock": svc.config.charge_for_mock,
                "dailyCaps": svc.config.daily_caps,
            },
            "features": {
                "aiAnalysis": svc.gemini.available,
                "barberSearch": svc.places.available,
                "virtualTryOn": svc.tryon.available,
                "imageStorage": svc.images.configured,
                "contentModeration": svc.gemini.available,
            },
            "rateLimits": {
                "places_api_remaining": svc.places_quota.remaining,
                "gemini_api_remaining": svc.gemini_quota.remaining,
            },
        }
    )


@bp.get("/metrics")
@limiter.limit(rate("ops"))
def get_metrics():
    require_ops_access()
    all_metrics = metrics.get_all_metrics()
    endpoints = all_metrics["endpoints"].values()
    total_requests = sum(m["request_count"] for m in endpoints)
    total_errors = sum(m["error_count"] for m in endpoints)
    summary = {
        "total_requests": total_requests,
        "total_errors": total_errors,
        "overall_success_rate": ((total_requests - total_errors) / total_requests * 100.0) if total_requests else 0.0,
        "avg_response_time_p95": 0.0,
    }
    p95_times = [m["response_time"]["p95"] for m in endpoints if m["response_time"]["p95"] > 0]
    if p95_times:
        summary["avg_response_time_p95"] = statistics.mean(p95_times)
    all_metrics["summary"] = summary
    all_metrics["cache_summary"] = {
        name: {
            "hit_rate": data.get("hit_rate", 0.0),
            "total_time_saved_seconds": data.get("total_time_saved_seconds", 0.0),
            "api_calls_avoided": data.get("api_calls_avoided", 0),
            "speedup_factor": data.get("speedup_factor", 0.0),
        }
        for name, data in all_metrics["cache"].items()
    }
    return jsonify(all_metrics)


@bp.get("/cache-stats")
@limiter.limit(rate("ops"))
def cache_stats():
    require_ops_access()
    svc = services()
    stats = svc.places_cache.stats()
    return jsonify(stats)


@bp.route("/clear-cache", methods=["POST", "GET"])
@limiter.limit(rate("ops"))
def clear_cache():
    require_ops_access()
    svc = services()
    removed = svc.places_cache.clear()
    svc.matcher.clear_cache()
    return jsonify(
        {
            "success": True,
            "message": "Cache cleared",
            "entries_removed": removed,
            "cache_size": 0,
            "timestamp": now_iso(),
        }
    )
