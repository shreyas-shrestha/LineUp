"""Flask application factory."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from flask import Flask, g, request
from werkzeug.middleware.proxy_fix import ProxyFix

from lineup_backend import __version__
from lineup_backend.config import AppConfig
from lineup_backend.context import build_services
from lineup_backend.extensions import limiter
from lineup_backend.logging_config import configure_logging
from lineup_backend.middleware.cors import configure_cors
from lineup_backend.middleware.error_handler import register_error_handlers
from lineup_backend.routes import register_blueprints
from lineup_backend.storage import seed_mock_data

logger = logging.getLogger(__name__)


def create_app(config: Optional[AppConfig] = None, **overrides: Any) -> Flask:
    """Build the app. ``overrides`` are AppConfig fields (used by tests)."""
    cfg = config or AppConfig.from_env(**overrides)
    configure_logging(cfg.log_level, cfg.log_format)

    app = Flask("lineup")
    app.config.update(
        ENV=cfg.env,
        TESTING=cfg.is_testing,
        DEBUG=cfg.debug,
        PORT=cfg.port,
        MAX_CONTENT_LENGTH=cfg.max_content_length,
        RATELIMIT_ENABLED=cfg.ratelimit_enabled,
        RATELIMIT_STORAGE_URI=cfg.ratelimit_storage_uri,
        RATELIMIT_DEFAULT=cfg.rate_limits["global"],
        RATELIMIT_STRATEGY="moving-window",
        RATELIMIT_HEADERS_ENABLED=True,
        RATELIMIT_IN_MEMORY_FALLBACK_ENABLED=True,
        LINEUP_RATE_LIMITS=dict(cfg.rate_limits),
        LINEUP_CONFIG=cfg,
    )
    app.json.sort_keys = False
    if cfg.trust_proxy:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)  # type: ignore[method-assign]

    configure_cors(app, cfg.allowed_origins)
    register_error_handlers(app)
    limiter.init_app(app)

    services = build_services(cfg)
    app.extensions["lineup"] = services
    register_blueprints(app)

    if cfg.should_seed and services.store.kind == "memory":
        if seed_mock_data(services.store):
            logger.info("Seeded in-memory store with mock data")

    _register_request_logging(app, cfg)
    logger.info(
        "LineUp backend %s ready (env=%s, storage=%s, gemini=%s, places=%s, replicate=%s, images=%s)",
        __version__,
        cfg.env,
        services.store.kind,
        services.gemini.available,
        services.places.available,
        services.tryon.available,
        services.images.provider or "none",
    )
    return app


def _register_request_logging(app: Flask, cfg: AppConfig) -> None:
    access_log = logging.getLogger("lineup.access")

    @app.before_request
    def _start_timer() -> None:
        g.request_started = time.perf_counter()

    @app.after_request
    def _log_request(response):
        started = getattr(g, "request_started", None)
        if started is not None and not cfg.is_testing:
            duration_ms = (time.perf_counter() - started) * 1000
            access_log.debug("%s %s -> %s (%.1f ms)", request.method, request.path, response.status_code, duration_ms)
        return response
