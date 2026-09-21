"""Google Places integration: barbershop search, reviews, photo redirects.

The API key never leaves the server: photo URLs point at our ``/places/photo``
endpoint which redirects to Google's CDN.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests

from lineup_backend.metrics import metrics
from lineup_backend.services.barber_matcher import BarberMatcher, describe_need
from lineup_backend.services.cache import TTLCache
from lineup_backend.services.quota import DailyQuota

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
PHOTO_URL = "https://maps.googleapis.com/maps/api/place/photo"
DETAIL_FIELDS = "name,formatted_address,formatted_phone_number,opening_hours,website,price_level,rating,user_ratings_total,photos,reviews"

HttpGet = Callable[..., Any]


def _redact(text: str, api_key: Optional[str]) -> str:
    """Strip the API key out of anything that may reach a log or a response.

    ``requests`` puts the full request URL in its exception messages, and that
    URL carries ``key=<GOOGLE_PLACES_API_KEY>``.
    """
    if api_key and api_key in text:
        text = text.replace(api_key, "<redacted>")
    return text


# Google's price_level is a 0-4 tier, not a dollar amount.
PRICE_TIERS = {0: "Free", 1: "$", 2: "$$", 3: "$$$", 4: "$$$$"}
# "$30 for a fade", "paid $ 45": a dollar sign then two or three digits.
PRICE_MENTION = re.compile(r"\$\s?(\d{2,3})(?!\d)")
PLAUSIBLE_PRICE = (10, 250)


def price_tier(level: Any) -> Optional[str]:
    """``"$$"`` for Google's price_level 2; None when Google did not report one."""
    try:
        return PRICE_TIERS.get(int(level))
    except (TypeError, ValueError):
        return None


def estimate_price_from_reviews(reviews: List[Dict[str, Any]]) -> Optional[int]:
    """The median of the dollar amounts reviewers quote, or None.

    Google rarely reports a price level for barbershops, but people write
    "$30 for a skin fade" in reviews all the time, and that is a price a
    customer actually paid rather than a tier. Amounts outside a plausible
    haircut range (tips, "$100s of dollars") are ignored.
    """
    amounts: List[int] = []
    low, high = PLAUSIBLE_PRICE
    for review in reviews or []:
        for match in PRICE_MENTION.finditer(str(review.get("text") or "")):
            value = int(match.group(1))
            if low <= value <= high:
                amounts.append(value)
    if not amounts:
        return None
    amounts.sort()
    return amounts[len(amounts) // 2]


def mock_barbers(location: str) -> List[Dict[str, Any]]:
    city = location.split(",")[0].strip() or "Downtown"
    maps = "https://www.google.com/maps/search/?api=1&query=33.7490,-84.3880"
    return [
        {
            "id": "barber_1",
            "name": f"Elite Cuts {city}",
            "specialties": ["Fade", "Taper", "Modern Cuts"],
            "rating": 4.9,
            "user_ratings_total": 127,
            "avgCost": 45,
            "price_tier": "$$",
            "price_source": "sample",
            "reviews": [
                {"username": "Marcus T.", "rating": 5, "text": "Cleanest skin fade I've had, $45 and worth every cent.", "date": "2026-08-30"},
                {"username": "Dev P.", "rating": 5, "text": "Asked for a textured crop from a photo and he nailed it.", "date": "2026-08-12"},
            ],
            "address": f"Downtown {city}",
            "photo": "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=400&h=300&fit=crop",
            "phone": "(555) 123-4567",
            "website": "https://elitecuts.example.com",
            "bookingUrl": "https://calendly.com/elitecuts/booking",
            "google_maps_url": maps,
            "hours": "Mon-Sat 9AM-8PM",
        },
        {
            "id": "barber_2",
            "name": f"The {city} Barber",
            "specialties": ["Pompadour", "Buzz Cut", "Beard Trim"],
            "rating": 4.8,
            "user_ratings_total": 89,
            "avgCost": 55,
            "price_tier": "$$",
            "price_source": "sample",
            "reviews": [
                {"username": "Jordan L.", "rating": 5, "text": "Best pompadour in town. $55 with a beard trim.", "date": "2026-09-02"},
            ],
            "address": f"Uptown {city}",
            "photo": "https://images.unsplash.com/photo-1585747860715-2ba37e788b70?w=400&h=300&fit=crop",
            "phone": "(555) 123-4568",
            "website": "",
            "bookingUrl": "https://booksy.com/thebarber",
            "google_maps_url": maps,
            "hours": "Tue-Sun 10AM-7PM",
        },
        {
            "id": "barber_3",
            "name": f"{city} Style Studio",
            "specialties": ["Modern Fade", "Beard Trim", "Styling"],
            "rating": 4.9,
            "user_ratings_total": 156,
            "avgCost": 65,
            "price_tier": "$$$",
            "price_source": "sample",
            "reviews": [
                {"username": "Sam R.", "rating": 5, "text": "Modern fade with a hard part, $65. Booked online, no wait.", "date": "2026-09-10"},
                {"username": "Ali K.", "rating": 4, "text": "Great curly fade, they actually know how to cut curly hair.", "date": "2026-08-21"},
            ],
            "address": f"Midtown {city}",
            "photo": "https://images.unsplash.com/photo-1605497788044-5a32c7078486?w=400&h=300&fit=crop",
            "phone": "(555) 123-4569",
            "website": "https://stylestudio.example.com",
            "bookingUrl": "https://squareup.com/appointments/book/stylestudio",
            "google_maps_url": maps,
            "hours": "Mon-Fri 8AM-6PM",
        },
    ]


def format_google_reviews(raw_reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    formatted = []
    for review in raw_reviews[:10]:
        ts = review.get("time")
        try:
            date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else "Recent"
        except (ValueError, TypeError, OSError, OverflowError):
            date = "Recent"
        formatted.append(
            {
                "id": f"{review.get('author_name', '')}_{ts or 0}",
                "username": review.get("author_name", "Anonymous"),
                "rating": review.get("rating", 5),
                "text": review.get("text", ""),
                "date": date,
                "profile_photo": review.get("profile_photo_url", ""),
                "relative_time": review.get("relative_time_description", ""),
            }
        )
    return formatted


def detect_specialties(name: str, styles: List[str]) -> List[str]:
    name_lower = name.lower()
    specialties: List[str] = []
    if "fade" in name_lower:
        specialties.append("Fade Specialist")
    if "classic" in name_lower or "traditional" in name_lower:
        specialties.append("Classic Cuts")
    if "modern" in name_lower or "style" in name_lower:
        specialties.append("Modern Styles")
    if "beard" in name_lower:
        specialties.append("Beard Trim")
    for style in styles:
        lowered = style.lower()
        if "fade" in lowered:
            specialties.append("Fade Expert")
        elif "classic" in lowered:
            specialties.append("Classic Styles")
        elif "modern" in lowered:
            specialties.append("Contemporary Cuts")
    if not specialties:
        specialties = ["Haircut", "Styling", "Beard Trim"]
    return list(dict.fromkeys(specialties))[:3]


class PlacesService:
    def __init__(
        self,
        api_key: Optional[str],
        quota: DailyQuota,
        cache: TTLCache,
        matcher: BarberMatcher,
        http_get: Optional[HttpGet] = None,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key
        self.quota = quota
        self.cache = cache
        self.matcher = matcher
        self._http_get = http_get
        self.timeout = timeout
        if not api_key:
            logger.warning("GOOGLE_PLACES_API_KEY not set: barber search returns sample data")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _get(self, url: str, params: Dict[str, Any], **kwargs: Any) -> Any:
        getter = self._http_get or requests.get
        kwargs.setdefault("timeout", self.timeout)
        return getter(url, params=params, **kwargs)

    @staticmethod
    def is_google_place_id(value: str) -> bool:
        return len(value) >= 20 and value.startswith(("Ch", "Ei", "Gh"))

    # -- search ------------------------------------------------------------

    def _mock_payload(self, location: str, reason: str, styles: Optional[List[str]] = None, hair: Optional[str] = None) -> Dict[str, Any]:
        # Sample shops go through the same ranker so the cards carry a match
        # and its reasons; no Gemini call, since the reviews are made up.
        ranked = self.matcher.rank_barbers(mock_barbers(location), list(styles or []), use_ai_analysis=False, hair=hair)
        return {
            "barbers": ranked,
            "location": location,
            "mock": True,
            "real_data": False,
            "reason": reason,
            **self._ranked_for(styles or [], hair),
        }

    @staticmethod
    def _ranked_for(styles: List[str], hair: Optional[str]) -> Dict[str, Any]:
        """What the list was ranked for, so the page can say it in one line."""
        ranked = bool(styles or hair)
        return {
            "ranked_by_style": ranked,
            "ranked_for": {"styles": list(styles), "hair": hair, "summary": describe_need(styles, hair)} if ranked else None,
        }

    @staticmethod
    def cache_key(location: str) -> str:
        return location.lower().strip()

    def would_fetch(self, location: str) -> bool:
        """True when a search for ``location`` would hit Google (not cached, key present, budget left)."""
        return self.available and self.cache.get(self.cache_key(location)) is None and self.quota.can_call()

    def search(
        self,
        location: str,
        styles: List[str],
        photo_base_url: Optional[str] = None,
        allow_fetch: bool = True,
        hair: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return the ``/barbers`` payload: real (cached or fresh) or mock data.

        With ``allow_fetch=False`` (anonymous callers) only cached results are
        served; a cache miss returns sample data marked ``reason: sign_in_required``.
        """
        cache_key = self.cache_key(location)
        started = time.time()
        cached = self.cache.get(cache_key)
        if cached is not None:
            metrics.record_cache_hit("places_api", response_time_ms=(time.time() - started) * 1000)
            ranked = self._rank(cached, styles, hair)
            return {
                "barbers": ranked[:10],
                "location": location,
                "cached": True,
                "mock": False,
                "real_data": True,
                "total_found": len(cached),
                **self._ranked_for(styles, hair),
            }
        metrics.record_cache_miss("places_api")

        if not self.available:
            return self._mock_payload(location, "places_not_configured", styles, hair)
        if not allow_fetch:
            return self._mock_payload(location, "sign_in_required", styles, hair)
        if not self.quota.can_call():
            logger.warning("Places daily budget spent; returning sample data")
            return self._mock_payload(location, "daily_quota_reached", styles, hair)

        calls = 0
        try:
            barbers, calls = self._fetch(location, styles, photo_base_url, hair)
        except Exception as exc:  # noqa: BLE001
            detail = _redact(str(exc), self.api_key)
            logger.error("Places search failed for %r: %s", location, detail)
            payload = self._mock_payload(location, "places_error", styles, hair)
            payload["error"] = detail
            return payload
        finally:
            # One search is a geocode + a nearby search + one details call per
            # result, so the budget has to count them all, not the search.
            self.quota.record(max(1, calls))

        metrics.record_api_call_time("places_api", (time.time() - started) * 1000)
        self.cache.set(cache_key, barbers)
        ranked = self._rank(barbers, styles, hair)
        return {
            "barbers": ranked[:10],
            "location": location,
            "cached": False,
            "mock": False,
            "real_data": True,
            "total_found": len(barbers),
            **self._ranked_for(styles, hair),
        }

    def _rank(self, barbers: List[Dict[str, Any]], styles: List[str], hair: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.matcher.rank_barbers(list(barbers), styles, use_ai_analysis=True, hair=hair)

    def _fetch(self, location: str, styles: List[str], photo_base_url: Optional[str], hair: Optional[str] = None) -> Tuple[List[Dict[str, Any]], int]:
        """Return the shops and the number of Google API calls they cost."""
        geo_started = time.time()
        geocode = self._get(GEOCODE_URL, {"address": location, "key": self.api_key}).json()
        metrics.record_api_latency("google_geocode", (time.time() - geo_started) * 1000)
        if geocode.get("status") != "OK" or not geocode.get("results"):
            raise RuntimeError(f"Location not found: {location}")
        center = geocode["results"][0]["geometry"]["location"]

        places_started = time.time()
        nearby = self._get(
            NEARBY_URL,
            {
                "location": f"{center['lat']},{center['lng']}",
                "radius": 10000,
                "type": "hair_care",
                "keyword": self.matcher.build_search_keywords(styles, hair),
                "key": self.api_key,
            },
        ).json()
        metrics.record_api_latency("google_places_search", (time.time() - places_started) * 1000)
        if nearby.get("status") != "OK":
            raise RuntimeError(f"Places API error: {nearby.get('status')}")

        barbers = []
        calls = 2  # geocode + nearby search
        for place in nearby.get("results", [])[:15]:
            barbers.append(self._build_barber(place, styles, photo_base_url))
            calls += 1  # one details call per shop
        return barbers, calls

    def _place_details(self, place_id: str) -> Dict[str, Any]:
        try:
            started = time.time()
            data = self._get(DETAILS_URL, {"place_id": place_id, "fields": DETAIL_FIELDS, "key": self.api_key}).json()
            metrics.record_api_latency("google_places_details", (time.time() - started) * 1000)
            return data.get("result", {}) if data.get("status") == "OK" else {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Place details failed for %s: %s", place_id, _redact(str(exc), self.api_key))
            return {}

    def _build_barber(self, place: Dict[str, Any], styles: List[str], photo_base_url: Optional[str]) -> Dict[str, Any]:
        details = self._place_details(place["place_id"])
        loc = place.get("geometry", {}).get("location", {})
        lat, lng = loc.get("lat"), loc.get("lng")

        photo_url = None
        photos = place.get("photos") or details.get("photos") or []
        if photos and photos[0].get("photo_reference") and photo_base_url:
            photo_url = f"{photo_base_url}/places/photo?ref={quote(photos[0]['photo_reference'])}&maxwidth=400"

        reviews = format_google_reviews(details.get("reviews", []))
        # Never invent a price. Google seldom sets price_level for barbershops;
        # defaulting it produced the same "$55" on every card. Prefer what
        # reviewers actually paid, then Google's tier, otherwise nothing.
        price_level = place.get("price_level", details.get("price_level"))
        tier = price_tier(price_level)
        quoted = estimate_price_from_reviews(reviews)

        return {
            "id": place["place_id"],
            "place_id": place["place_id"],
            "name": place.get("name", "Barbershop"),
            "address": details.get("formatted_address", place.get("vicinity", "Address not available")),
            "rating": place.get("rating", 0),
            "user_ratings_total": place.get("user_ratings_total", 0),
            "price_level": price_level,
            "price_tier": tier,
            "avgCost": quoted,
            "price_source": "reviews" if quoted is not None else ("google" if tier else None),
            "phone": details.get("formatted_phone_number", ""),
            "website": details.get("website", ""),
            "bookingUrl": details.get("website", ""),
            "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={lat},{lng}",
            "hours": details.get("opening_hours", {}).get("weekday_text", []),
            "open_now": place.get("opening_hours", {}).get("open_now"),
            "photo": photo_url,
            "specialties": detect_specialties(place.get("name", ""), styles),
            "location": {"lat": lat, "lng": lng},
            "recommended_for_styles": list(styles),
            "google_reviews": reviews,
            "reviews": reviews,
        }

    # -- reviews / photos --------------------------------------------------

    def fetch_reviews(self, place_id: str) -> Optional[Dict[str, Any]]:
        if not self.available:
            return None
        try:
            data = self._get(DETAILS_URL, {"place_id": place_id, "fields": "name,rating,user_ratings_total,reviews", "key": self.api_key}).json()
        except Exception as exc:  # noqa: BLE001
            logger.error("Google reviews failed for %s: %s", place_id, _redact(str(exc), self.api_key))
            return None
        if data.get("status") != "OK" or "result" not in data:
            logger.warning("Google reviews status for %s: %s", place_id, data.get("status"))
            return None
        result = data["result"]
        return {
            "reviews": format_google_reviews(result.get("reviews", [])),
            "average_rating": result.get("rating", 0),
            "total_reviews": result.get("user_ratings_total", 0),
            "source": "google",
        }

    def photo_redirect_url(self, photo_reference: str, max_width: int = 400) -> Optional[str]:
        """Resolve a photo reference to Google's CDN URL without exposing the key."""
        if not self.available:
            return None
        try:
            response = self._get(
                PHOTO_URL,
                {"photoreference": photo_reference, "maxwidth": max_width, "key": self.api_key},
                allow_redirects=False,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Place photo lookup failed: %s", _redact(str(exc), self.api_key))
            return None
        location = response.headers.get("Location") if hasattr(response, "headers") else None
        return location if response.status_code in (301, 302, 303, 307, 308) and location else None
