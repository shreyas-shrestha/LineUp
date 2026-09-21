"""HTTP layer: one blueprint per domain, registered by :func:`register_blueprints`.

The consumer launch ships the first group only. The barber side (shop
management, bookings, portfolios and packages, the community feed) is
registered when ``LINEUP_BARBER_SIDE`` is on, so those paths are plain 404s
in the shipped API rather than routes that answer but lead nowhere.
"""

from __future__ import annotations

from typing import Tuple

from flask import Blueprint, Flask

from lineup_backend.config import AppConfig
from lineup_backend.routes.analyze import bp as analyze_bp
from lineup_backend.routes.appointments import bp as appointments_bp
from lineup_backend.routes.auth import bp as auth_bp
from lineup_backend.routes.barber_shop import bp as barber_shop_bp
from lineup_backend.routes.barbers import bp as barbers_bp
from lineup_backend.routes.billing import bp as billing_bp
from lineup_backend.routes.portfolio import bp as portfolio_bp
from lineup_backend.routes.social import bp as social_bp
from lineup_backend.routes.system import bp as system_bp

CONSUMER_BLUEPRINTS: Tuple[Blueprint, ...] = (system_bp, auth_bp, billing_bp, analyze_bp, barbers_bp)
BARBER_SIDE_BLUEPRINTS: Tuple[Blueprint, ...] = (barber_shop_bp, social_bp, appointments_bp, portfolio_bp)

# Kept for callers that want "everything": the two-sided app.
ALL_BLUEPRINTS = CONSUMER_BLUEPRINTS + BARBER_SIDE_BLUEPRINTS


def blueprints_for(config: AppConfig) -> Tuple[Blueprint, ...]:
    return ALL_BLUEPRINTS if config.barber_side else CONSUMER_BLUEPRINTS


def register_blueprints(app: Flask) -> None:
    config: AppConfig = app.config["LINEUP_CONFIG"]
    for blueprint in blueprints_for(config):
        app.register_blueprint(blueprint)
