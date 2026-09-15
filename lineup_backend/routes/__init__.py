"""HTTP layer: one blueprint per domain, registered by :func:`register_blueprints`."""

from __future__ import annotations

from flask import Flask

from lineup_backend.routes.analyze import bp as analyze_bp
from lineup_backend.routes.appointments import bp as appointments_bp
from lineup_backend.routes.auth import bp as auth_bp
from lineup_backend.routes.barbers import bp as barbers_bp
from lineup_backend.routes.billing import bp as billing_bp
from lineup_backend.routes.portfolio import bp as portfolio_bp
from lineup_backend.routes.social import bp as social_bp
from lineup_backend.routes.system import bp as system_bp

ALL_BLUEPRINTS = (system_bp, auth_bp, billing_bp, analyze_bp, barbers_bp, social_bp, appointments_bp, portfolio_bp)


def register_blueprints(app: Flask) -> None:
    for blueprint in ALL_BLUEPRINTS:
        app.register_blueprint(blueprint)
