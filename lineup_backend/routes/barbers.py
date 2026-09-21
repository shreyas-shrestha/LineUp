"""Barber discovery: Google Places search, the photo proxy and public reviews.

This is the consumer-facing half of the old ``barbers`` blueprint and is
always registered. Shop management (profile, hours, services, clients) lives
in :mod:`lineup_backend.routes.barber_shop` and only exists when the barber
side is switched on.
"""

from __future__ import annotations

from flask import Blueprint, g, jsonify, redirect, request

from lineup_backend.context import services
from lineup_backend.extensions import limiter, rate
from lineup_backend.http import clean_text, query_list, to_int, to_number
from lineup_backend.metrics import track_performance
from lineup_backend.middleware.auth import optional_auth
from lineup_backend.middleware.error_handler import ApiError
from lineup_backend.services.billing import metered
from lineup_backend.services.places import PlacesService

bp = Blueprint("barbers", __name__)


def _public_base_url() -> str:
    cfg = services().config
    if cfg.public_url:
        return cfg.public_url.rstrip("/")
    scheme = request.headers.get("X-Forwarded-Proto", request.scheme).split(",")[0].strip()
    return f"{scheme}://{request.host}"


def _search_location() -> str:
    return clean_text(request.args.get("location"), default="Atlanta, GA", max_length=200)


def _search_is_free() -> bool:
    return not services().places.would_fetch(_search_location())


@bp.get("/barbers")
@limiter.limit(rate("places"))
@track_performance("barbers")
@optional_auth
@metered("barber_search", free_when=_search_is_free)
def search_barbers():
    """Signed-in users can trigger a (metered) Google Places search; anonymous
    callers get cached results or sample data."""
    location = _search_location()
    styles = query_list("styles")
    payload = services().places.search(location, styles, photo_base_url=_public_base_url(), allow_fetch=g.user is not None)
    return jsonify(payload)


@bp.get("/places/photo")
@limiter.limit(rate("read"))
def place_photo():
    """Redirect to a Google Places photo without exposing the API key."""
    ref = clean_text(request.args.get("ref"), max_length=1000)
    if not ref:
        raise ApiError("ref is required", 400)
    max_width = min(to_int(request.args.get("maxwidth"), 400, minimum=1), 1600)
    svc = services()
    if not svc.places.available:
        raise ApiError("Photos are not available", 404)
    url = svc.places.photo_redirect_url(ref, max_width)
    if not url:
        raise ApiError("Photo not found", 404)
    response = redirect(url, code=302)
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response


@bp.get("/barbers/<barber_id>/reviews")
@limiter.limit(rate("read"))
def reviews(barber_id: str):
    """Google reviews for a Places id, otherwise reviews left on LineUp."""
    svc = services()
    if svc.places.available and PlacesService.is_google_place_id(barber_id):
        google = svc.places.fetch_reviews(barber_id)
        if google:
            return jsonify(google)

    items = svc.store.barber_reviews.list(barberId=barber_id)
    items.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    average = round(sum(to_number(r.get("rating")) for r in items) / len(items), 1) if items else 0
    return jsonify({"reviews": items, "average_rating": average, "total_reviews": len(items), "source": "local"})
