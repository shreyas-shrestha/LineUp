"""Photo analysis, virtual try-on and style insights. Analysis and try-on are
signed-in, metered actions (see ``pricing.py``)."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict

from flask import Blueprint, jsonify

from lineup_backend.context import services
from lineup_backend.extensions import limiter, rate
from lineup_backend.http import clean_text, decode_base64_image, get_json_body, open_image, query_list, strip_data_url
from lineup_backend.metrics import track_performance
from lineup_backend.middleware.auth import require_auth
from lineup_backend.middleware.error_handler import ApiError
from lineup_backend.services.billing import metered
from lineup_backend.services.gemini import mock_analysis

bp = Blueprint("analyze", __name__)


def _extract_image_field(data: Dict[str, Any]) -> str:
    """Accept ``{"image": b64}`` or the Gemini-style ``payload.contents[0].parts[].inlineData.data``."""
    if isinstance(data.get("image"), str) and data["image"].strip():
        return data["image"]
    payload = data.get("payload")
    if not isinstance(payload, dict):
        raise ApiError("Missing image: send {image: <base64>} or payload.contents[0].parts[].inlineData.data", 400)
    contents = payload.get("contents")
    if not isinstance(contents, list) or not contents or not isinstance(contents[0], dict):
        raise ApiError("payload.contents must be a non-empty list", 400)
    parts = contents[0].get("parts")
    if not isinstance(parts, list):
        raise ApiError("payload.contents[0].parts must be a list", 400)
    for part in parts:
        if not isinstance(part, dict):
            continue
        inline = part.get("inlineData") or part.get("inline_data")
        if isinstance(inline, dict) and isinstance(inline.get("data"), str) and inline["data"].strip():
            return inline["data"]
    raise ApiError("No image data provided", 400)


def _analysis_is_free() -> bool:
    """Mock analysis is free in production; locally it is charged so the credit flow can be demoed."""
    svc = services()
    return svc.gemini.status() != "ready" and not svc.config.charge_for_mock


def _tryon_is_free() -> bool:
    svc = services()
    return not svc.tryon.available and not svc.config.charge_for_mock


@bp.post("/analyze")
@limiter.limit(rate("ai"))
@track_performance("analyze")
@require_auth
@metered("analysis", free_when=_analysis_is_free)
def analyze():
    data = get_json_body()
    image_bytes = decode_base64_image(_extract_image_field(data), field="image")

    svc = services()
    status = svc.gemini.status()
    if status != "ready":
        return jsonify(mock_analysis("gemini_not_configured" if status == "not_configured" else "daily_quota_reached"))

    result = svc.gemini.analyze_face(open_image(image_bytes))
    if result is None:
        return jsonify(mock_analysis("gemini_error"))
    result.update({"mock": False, "source": "gemini"})
    return jsonify(result)


@bp.post("/virtual-tryon")
@limiter.limit(rate("tryon"))
@track_performance("virtual_tryon")
@require_auth
@metered("tryon", free_when=_tryon_is_free)
def virtual_tryon():
    data = get_json_body()
    photo = data.get("userPhoto")
    description = clean_text(data.get("styleDescription"), max_length=200)
    if not isinstance(photo, str) or not photo.strip():
        raise ApiError("User photo required", 400)
    if not description:
        raise ApiError("Style description required", 400)

    image_bytes = decode_base64_image(photo, field="userPhoto")
    original_b64 = "".join(strip_data_url(photo.strip()).split())
    svc = services()
    return jsonify(svc.tryon.transform(image_bytes, original_b64, description))


@bp.get("/ai-insights")
@limiter.limit(rate("read"))
def ai_insights():
    svc = services()
    styles = query_list("styles")
    trends = svc.store.hair_trends.get("global") or {}

    tag_counts: Counter = Counter()
    for post in svc.store.social_posts.list():
        tag_counts.update(tag for tag in post.get("hashtags", []) if isinstance(tag, str))
    trending_hashtags = [f"#{tag}" for tag, count in tag_counts.most_common(5) if count > 1]

    insights = {
        "trending_styles": (trends.get("trending_styles") or [])[:5],
        "trending_hashtags": trending_hashtags or (trends.get("trending_hashtags") or [])[:5],
        "popular_colors": (trends.get("popular_colors") or [])[:4],
        "seasonal_tips": trends.get("seasonal_tips", ""),
        "personalized_recommendations": [],
    }
    if styles:
        first = styles[0]
        insights["personalized_recommendations"] = [
            f"Since you like {first}, ask your barber about complementary variations.",
            f"{first} holds its shape best with a trim every 3-4 weeks.",
            f"Bring a reference photo of {first} to your appointment.",
        ]
    return jsonify(insights)
