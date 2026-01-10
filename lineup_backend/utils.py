"""Common utilities for the LineUp backend."""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Dict, Optional, Tuple

from flask import jsonify, make_response, request

logger = logging.getLogger(__name__)


def cors_response(data: Any, status: int = 200) -> Tuple[Any, int]:
    """Create a JSON response with CORS headers."""
    response = make_response(jsonify(data), status)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Content-Type'] = 'application/json'
    return response


def cors_preflight() -> Tuple[Any, int]:
    """Handle OPTIONS preflight request."""
    response = make_response('')
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Accept, Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    return response, 200


def api_response(
    data: Optional[Dict] = None,
    message: Optional[str] = None,
    error: Optional[str] = None,
    status: int = 200
) -> Tuple[Any, int]:
    """
    Standardized API response format.
    
    Success: {"success": true, "data": {...}, "message": "..."}
    Error: {"success": false, "error": "...", "message": "..."}
    """
    response_data = {"success": status < 400}
    
    if data is not None:
        response_data["data"] = data
    
    if message:
        response_data["message"] = message
    
    if error:
        response_data["error"] = error
        response_data["success"] = False
    
    return cors_response(response_data, status)


def handle_options(methods: str = "GET, POST, OPTIONS"):
    """Decorator to handle OPTIONS preflight for a route."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method == 'OPTIONS':
                response = make_response('')
                response.headers.add('Access-Control-Allow-Origin', '*')
                response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Accept, Authorization')
                response.headers.add('Access-Control-Allow-Methods', methods)
                return response, 200
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def safe_get_json() -> Dict:
    """Safely get JSON from request, returning empty dict on failure."""
    try:
        return request.get_json(force=True) or {}
    except Exception:
        return {}


def validate_required_fields(data: Dict, required: list) -> Optional[str]:
    """
    Validate that required fields are present in data.
    Returns error message if validation fails, None if valid.
    """
    missing = [field for field in required if not data.get(field)]
    if missing:
        return f"Missing required fields: {', '.join(missing)}"
    return None


class APIError(Exception):
    """Custom API error with status code."""
    
    def __init__(self, message: str, status_code: int = 400, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}
    
    def to_response(self) -> Tuple[Any, int]:
        """Convert error to API response."""
        response_data = {
            "success": False,
            "error": self.message
        }
        if self.details:
            response_data["details"] = self.details
        return cors_response(response_data, self.status_code)

