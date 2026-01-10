"""Route blueprints for the LineUp backend API."""

from lineup_backend.routes.health import health_bp
from lineup_backend.routes.analyze import analyze_bp
from lineup_backend.routes.barbers import barbers_bp
from lineup_backend.routes.appointments import appointments_bp
from lineup_backend.routes.social import social_bp
from lineup_backend.routes.portfolio import portfolio_bp

__all__ = [
    "health_bp",
    "analyze_bp",
    "barbers_bp",
    "appointments_bp",
    "social_bp",
    "portfolio_bp",
]
