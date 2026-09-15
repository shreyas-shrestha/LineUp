"""Mock data for local development and tests (never loaded in production
unless LINEUP_SEED_MOCK_DATA=true)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict

from lineup_backend.services.availability import DEFAULT_SERVICES, default_availability
from lineup_backend.services.users import new_user_doc
from lineup_backend.storage.base import Store

UNSPLASH = "https://images.unsplash.com"

# Development accounts (dev-login with these emails to get these identities).
DEV_CLIENT = {"uid": "client_1", "email": "client@lineup.dev", "name": "Alex Johnson", "role": "client"}
DEV_BARBER = {"uid": "barber_1", "email": "barber@lineup.dev", "name": "Mike Rivera", "role": "barber", "shopName": "Mike's Cuts"}


def _iso(hours_ago: float = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


def _date(days_ahead: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days_ahead)).strftime("%Y-%m-%d")


def seed_mock_data(store: Store) -> bool:
    """Populate the store with demo content. Idempotent: skips if posts exist."""
    if store.social_posts.count() > 0:
        return False

    store.social_posts.create(
        {
            "username": "mike_style",
            "avatar": f"{UNSPLASH}/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop&crop=face",
            "image": f"{UNSPLASH}/photo-1622296089863-eb7fc530daa8?w=400&h=400&fit=crop",
            "caption": "Fresh fade from @atlanta_cuts #fade #haircut",
            "authorUid": "user_mike_style",
            "likes": 23,
            "likedBy": [],
            "shares": 5,
            "comments": 2,
            "timeAgo": "2h",
            "timestamp": _iso(2),
            "hashtags": ["fade", "haircut", "barberlife"],
        },
        doc_id="1",
    )
    store.social_posts.create(
        {
            "username": "sarah_hair",
            "avatar": f"{UNSPLASH}/photo-1494790108755-2616b612b786?w=100&h=100&fit=crop&crop=face",
            "image": f"{UNSPLASH}/photo-1605497788044-5a32c7078486?w=400&h=400&fit=crop",
            "caption": "New bob cut. Love how it frames my face #bob #hairstyle",
            "authorUid": "user_sarah_hair",
            "likes": 45,
            "likedBy": [DEV_CLIENT["uid"]],
            "shares": 12,
            "comments": 1,
            "timeAgo": "4h",
            "timestamp": _iso(4),
            "hashtags": ["bob", "hairstyle", "freshcut", "fade"],
        },
        doc_id="2",
    )

    store.post_comments.upsert(
        "1",
        {
            "comments": [
                {"id": "c1", "username": "alex_taylor", "text": "Looking sharp.", "timeAgo": "1h", "timestamp": _iso(1)},
                {"id": "c2", "username": "john_doe", "text": "What's the fade number?", "timeAgo": "30m", "timestamp": _iso(0.5)},
            ]
        },
    )
    store.post_comments.upsert(
        "2",
        {"comments": [{"id": "c3", "username": "mike_style", "text": "Beautiful cut.", "timeAgo": "3h", "timestamp": _iso(3)}]},
    )

    store.user_follows.upsert(DEV_CLIENT["uid"], {"following": ["mike_style", "sarah_hair"]})
    store.user_follows.upsert("user_mike_style", {"following": ["sarah_hair", "jason_cuts"]})

    seed_dev_users(store)

    reviews: Dict[str, list] = {
        "barber_1": [
            ("r1", "john_doe", 5, "Best fade I've ever had. Mike is a true artist.", "2024-01-18"),
            ("r2", "jane_smith", 5, "Professional service, clean cuts every time.", "2024-01-15"),
            ("r3", "alex_taylor", 4, "Great barber, just sometimes a bit crowded on weekends.", "2024-01-10"),
        ],
        "barber_2": [("r4", "sam_jones", 4, "Good quality work, friendly staff.", "2024-01-17")],
    }
    for barber_id, items in reviews.items():
        for review_id, username, rating, text, date in items:
            store.barber_reviews.create(
                {"barberId": barber_id, "username": username, "rating": rating, "text": text, "date": date, "timestamp": _iso(48)},
                doc_id=review_id,
            )

    store.barber_portfolios.create(
        {
            "styleName": "Modern Fade",
            "image": f"{UNSPLASH}/photo-1622296089863-eb7fc530daa8?w=400&h=400&fit=crop",
            "description": "Clean fade with textured top. Works well for professionals.",
            "likes": 12,
            "date": "2024-01-15",
            "barberId": "barber_1",
            "timestamp": _iso(72),
        },
        doc_id="1",
    )

    store.appointments.create(
        {
            "clientName": DEV_CLIENT["name"],
            "clientId": DEV_CLIENT["uid"],
            "barberName": DEV_BARBER["shopName"],
            "barberId": DEV_BARBER["uid"],
            "date": _date(1),
            "time": "14:00",
            "service": "Haircut + Beard",
            "price": "$65",
            "status": "confirmed",
            "notes": "Looking for a modern fade",
            "timestamp": _iso(6),
        },
        doc_id="apt_seed_1",
    )

    store.hair_trends.upsert(
        "global",
        {
            "trending_styles": ["textured crop", "modern fade", "curtain bangs", "buzz cut", "pompadour"],
            "trending_hashtags": ["#fade", "#haircut", "#barberlife", "#freshcut", "#hairstyle"],
            "popular_colors": ["natural", "blonde highlights", "dark brown", "black"],
            "seasonal_tips": "Textured crops and fades are trending this season. Consider volume on top with short sides.",
        },
    )
    return True


def _seed_user(store: Store, account: Dict[str, str]) -> None:
    if store.users.get(account["uid"]) is not None:
        return
    user = store.users.create(
        new_user_doc(account["uid"], account["email"], account["name"], role=account["role"], provider="dev"),
        doc_id=account["uid"],
    )
    credits = int(user.get("credits", 0) or 0)
    if credits > 0:  # same ledger row a real signup writes (see Ledger.record_signup)
        store.usage_events.create(
            {
                "uid": account["uid"],
                "kind": "grant",
                "action": "grant",
                "credits": credits,
                "delta": credits,
                "balance_after": credits,
                "provider_cost_estimate": 0.0,
                "ok": True,
                "ts": user["createdAt"],
                "meta": {},
                "reason": "signup_bonus",
            }
        )


def seed_dev_users(store: Store) -> None:
    """The two developer accounts plus the barber's shop profile, hours and services."""
    _seed_user(store, DEV_CLIENT)
    _seed_user(store, DEV_BARBER)
    if store.barber_profiles.get(DEV_BARBER["uid"]) is None:
        store.barber_profiles.create(
            {
                "ownerUid": DEV_BARBER["uid"],
                "name": DEV_BARBER["shopName"],
                "phone": "(404) 555-0142",
                "address": "Downtown Atlanta",
                "bio": "Fades, tapers and beard work since 2015.",
                "createdAt": _iso(24 * 30),
                "updatedAt": _iso(24 * 30),
            },
            doc_id=DEV_BARBER["uid"],
        )
    if not store.barber_services.list(barberId=DEV_BARBER["uid"]):
        for index, service in enumerate(DEFAULT_SERVICES):
            store.barber_services.create({**service, "barberId": DEV_BARBER["uid"], "createdAt": _iso(24 * 30 - index), "default": True})
    if store.barber_availability.get(DEV_BARBER["uid"]) is None:
        store.barber_availability.upsert(DEV_BARBER["uid"], {**default_availability(DEV_BARBER["uid"]), "updatedAt": _iso(24 * 30)})
