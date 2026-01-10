"""In-memory fallback storage for the LineUp backend.

This module centralizes the mutable global state that was previously declared
inside `app.py`. Moving these collections into a dedicated module makes it
easier to swap the implementation later (e.g., replace with a database layer)
and prevents accidental shadowing when multiple modules need access to the same
data structures.
"""

from __future__ import annotations

from typing import Dict, List

# Social feed / community
social_posts: List[dict] = []
post_comments: Dict[str, List[dict]] = {}
user_follows: Dict[str, List[str]] = {}

# Barber + client data
barber_portfolios: Dict[str, List[dict]] = {}
barber_profiles: Dict[str, dict] = {}
barber_reviews: Dict[str, List[dict]] = {}
hair_trends: Dict[str, dict] = {}

# Commerce
appointments: List[dict] = []
subscription_packages: List[dict] = []
client_subscriptions: List[dict] = []


def reset_all() -> None:
    """Reset in-memory collections (mainly for local development/tests)."""
    social_posts.clear()
    post_comments.clear()
    user_follows.clear()
    barber_portfolios.clear()
    barber_profiles.clear()
    barber_reviews.clear()
    hair_trends.clear()
    appointments.clear()
    subscription_packages.clear()
    client_subscriptions.clear()



