"""LineUp Backend Package - Production-ready modular backend."""

from .config import AppConfig
from .storage import (
    social_posts,
    post_comments,
    user_follows,
    barber_portfolios,
    barber_profiles,
    barber_reviews,
    hair_trends,
    appointments,
    subscription_packages,
    client_subscriptions,
    reset_all,
)

__version__ = "2.0.0"

__all__ = [
    "AppConfig",
    # Storage exports
    "social_posts",
    "post_comments", 
    "user_follows",
    "barber_portfolios",
    "barber_profiles",
    "barber_reviews",
    "hair_trends",
    "appointments",
    "subscription_packages",
    "client_subscriptions",
    "reset_all",
]
