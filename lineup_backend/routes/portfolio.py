"""Barber portfolio and subscription commerce.

Reads are public. A barber can only write their own portfolio/packages; the
7th portfolio photo and packages need Barber Pro (402 ``pro_required``).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from flask import Blueprint, g, jsonify, request

from lineup_backend.context import services
from lineup_backend.extensions import limiter, rate
from lineup_backend.http import clean_text, decode_base64_image, get_json_body, json_response, now_iso, to_int, today_str
from lineup_backend.middleware.auth import assert_owner, require_auth, require_pro, require_role
from lineup_backend.middleware.error_handler import ApiError
from lineup_backend.pricing import FREE_PORTFOLIO_LIMIT
from lineup_backend.services.billing import ProRequired
from lineup_backend.services.users import is_pro

bp = Blueprint("portfolio", __name__)

MAX_IMAGE_URL_LENGTH = 2000


def _portfolio_image(value: Any) -> str:
    """Accept an http(s) URL or a real base64 image; reject anything else so a
    stored value can never be a script URL or arbitrary text rendered as <img src>."""
    if not isinstance(value, str) or not value.strip():
        raise ApiError("image is required", 400)
    text = value.strip()
    if re.match(r"^https?://", text, re.IGNORECASE):
        if len(text) > MAX_IMAGE_URL_LENGTH or any(ch.isspace() for ch in text):
            raise ApiError("image URL is not valid", 400)
        return text
    decode_base64_image(text, field="image")
    return "".join(text.split())


@bp.route("/portfolio", methods=["GET", "POST"], defaults={"barber_id": None})
@bp.route("/portfolio/<barber_id>", methods=["GET", "POST"])
@limiter.limit(rate("read"), methods=["GET"])
@limiter.limit(rate("write"), methods=["POST"])
def portfolio(barber_id):
    collection = services().store.barber_portfolios
    if request.method == "GET":
        items = collection.list(barberId=barber_id) if barber_id else collection.list()
        items.sort(key=lambda w: w.get("timestamp", ""), reverse=True)
        return jsonify({"portfolio": items})

    require_role("barber")(lambda: None)()
    user = g.user
    owner = user["uid"]
    if barber_id and barber_id != owner:
        assert_owner(barber_id, "You can only add to your own portfolio")
    data = get_json_body()
    image = _portfolio_image(data.get("image"))
    existing = len(collection.list(barberId=owner))
    if not is_pro(user) and existing >= FREE_PORTFOLIO_LIMIT:
        raise ProRequired("portfolio")
    work = collection.create(
        {
            "styleName": clean_text(data.get("styleName"), max_length=120),
            "image": image,
            "description": clean_text(data.get("description"), max_length=1000),
            "likes": 0,
            "date": today_str(),
            "barberId": owner,
            "timestamp": now_iso(),
        }
    )
    remaining = None if is_pro(user) else max(0, FREE_PORTFOLIO_LIMIT - existing - 1)
    return json_response({"success": True, "work": work, "count": existing + 1, "remaining_free": remaining}, 201)


@bp.delete("/portfolio/<barber_id>/<work_id>")
@limiter.limit(rate("write"))
@require_role("barber")
def delete_work(barber_id: str, work_id: str):
    assert_owner(barber_id, "You can only edit your own portfolio")
    collection = services().store.barber_portfolios
    work = collection.get(work_id)
    if not work or work.get("barberId") != barber_id:
        raise ApiError("Work not found", 404)
    collection.delete(work_id)
    return jsonify({"success": True})


@bp.route("/subscription-packages", methods=["GET", "POST"])
@limiter.limit(rate("read"), methods=["GET"])
@limiter.limit(rate("write"), methods=["POST"])
def subscription_packages():
    collection = services().store.subscription_packages
    if request.method == "GET":
        barber_id = request.args.get("barber_id")
        items = collection.list(barberId=barber_id) if barber_id else collection.list()
        return jsonify({"packages": items})

    require_role("barber")(lambda: None)()
    user = require_pro("packages")
    data = get_json_body()
    title = clean_text(data.get("title"), max_length=120)
    if not title:
        raise ApiError("title is required", 400)
    profile = services().store.barber_profiles.get(user["uid"]) or {}
    package = collection.create(
        {
            "barberId": user["uid"],
            "barberName": clean_text(data.get("barberName"), default=profile.get("name", user.get("name", "")), max_length=160),
            "title": title,
            "description": clean_text(data.get("description"), max_length=1000),
            "price": clean_text(data.get("price"), max_length=20),
            "numCuts": to_int(data.get("numCuts"), 0, minimum=0),
            "durationMonths": to_int(data.get("durationMonths"), 0, minimum=0),
            "discount": clean_text(data.get("discount"), max_length=40),
            "timestamp": now_iso(),
        }
    )
    return json_response({"success": True, "package": package}, 201)


@bp.delete("/subscription-packages/<package_id>")
@limiter.limit(rate("write"))
@require_role("barber")
def delete_package(package_id: str):
    collection = services().store.subscription_packages
    package = collection.get(package_id)
    if not package or package.get("barberId") != g.user["uid"]:
        raise ApiError("Package not found", 404)
    collection.delete(package_id)
    return jsonify({"success": True})


@bp.route("/client-subscriptions", methods=["GET", "POST"])
@limiter.limit(rate("read"), methods=["GET"])
@limiter.limit(rate("write"), methods=["POST"])
@require_auth
def client_subscriptions():
    svc = services()
    collection = svc.store.client_subscriptions
    user = g.user
    if request.method == "GET":
        return jsonify({"subscriptions": collection.list(clientId=user["uid"])})

    data = get_json_body()
    package_id = clean_text(data.get("packageId"), max_length=120)
    if not package_id:
        raise ApiError("packageId is required", 400)
    package = svc.store.subscription_packages.get(package_id)
    if not package:
        raise ApiError("Package not found", 404)
    num_cuts = to_int(data.get("numCuts", package.get("numCuts")), 0, minimum=0)
    months = to_int(data.get("durationMonths", package.get("durationMonths")), 1, minimum=1)
    now = datetime.now(timezone.utc)
    subscription = collection.create(
        {
            "clientId": user["uid"],
            "clientName": clean_text(user.get("name"), default="Client", max_length=120),
            "packageId": package_id,
            "packageTitle": package.get("title", ""),
            "barberId": package.get("barberId", ""),
            "barberName": package.get("barberName", ""),
            "price": str(package.get("price", "")),
            "numCuts": num_cuts,
            "remainingCuts": num_cuts,
            "purchaseDate": now.isoformat(),
            "expiryDate": (now + timedelta(days=30 * months)).isoformat(),
            "status": "active",
            "timestamp": now.isoformat(),
        }
    )
    return json_response({"success": True, "subscription": subscription}, 201)
