"""Helpers shared by route modules: JSON bodies, ids, timestamps, image decoding."""

from __future__ import annotations

import base64
import binascii
import re
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional

from flask import Response, jsonify, request
from PIL import Image, UnidentifiedImageError

from lineup_backend.middleware.error_handler import ApiError

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def new_id() -> str:
    return str(uuid.uuid4())


def json_response(payload: Any, status: int = 200) -> Response:
    response = jsonify(payload)
    response.status_code = status
    return response


def get_json_body(required: bool = True) -> Dict[str, Any]:
    """Return the JSON object body or raise a 400 ApiError."""
    data = request.get_json(silent=True)
    if data is None:
        if required:
            raise ApiError("Request body must be a JSON object", 400)
        return {}
    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object", 400)
    return data


def clean_text(value: Any, default: str = "", max_length: int = 2000) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text[:max_length] if text else default


def to_int(value: Any, default: int, minimum: Optional[int] = None) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return default
    if minimum is not None and result < minimum:
        return default
    return result


def to_number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def query_list(name: str) -> List[str]:
    raw = request.args.get(name, "")
    return [part.strip() for part in raw.split(",") if part.strip()]


def is_valid_date(value: Any) -> bool:
    if not isinstance(value, str) or not DATE_RE.match(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def is_valid_time(value: Any) -> bool:
    return isinstance(value, str) and bool(TIME_RE.match(value))


def strip_data_url(data: str) -> str:
    return data.split(",", 1)[1] if "," in data else data


def decode_base64_image(data: Any, field: str = "image") -> bytes:
    """Decode a base64 (optionally data-URL) image and verify it is a real image."""
    if not isinstance(data, str) or not data.strip():
        raise ApiError(f"{field} is required", 400)
    raw = "".join(strip_data_url(data.strip()).split())
    try:
        image_bytes = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        raise ApiError(f"{field} must be base64-encoded image data", 400) from None
    if not image_bytes:
        raise ApiError(f"{field} must be base64-encoded image data", 400)
    try:
        with Image.open(BytesIO(image_bytes)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise ApiError(f"{field} is not a valid image", 400) from None
    return image_bytes


def open_image(image_bytes: bytes) -> Image.Image:
    image = Image.open(BytesIO(image_bytes))
    image.load()
    return image
