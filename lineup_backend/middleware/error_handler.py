"""JSON error responses for every failure path.

Route code raises :class:`ApiError` for expected client errors. Framework
errors (404, 405, 413, 429, ...) and unexpected exceptions are converted to the
same ``{"error": ..., "message": ...}`` shape so the frontend never sees HTML.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """An expected error with an HTTP status and a JSON body."""

    def __init__(self, error: str, status: int = 400, **extra: Any) -> None:
        super().__init__(error)
        self.message = error  # the ``error`` field; a human ``message`` may be passed via extra
        self.status = status
        self.extra = extra

    def payload(self) -> Dict[str, Any]:
        body: Dict[str, Any] = {"error": self.message}
        body.update(self.extra)
        return body


def _json(payload: Dict[str, Any], status: int) -> Response:
    response = jsonify(payload)
    response.status_code = status
    return response


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError) -> Response:
        return _json(error.payload(), error.status)

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException) -> Response:
        status = error.code or 500
        if status == 404:
            body = {"error": "Not found", "message": "The requested resource does not exist"}
        elif status == 405:
            allowed = sorted(getattr(error, "valid_methods", None) or [])
            body = {
                "error": "Method not allowed",
                "message": f"{request.method} is not allowed for {request.path}",
                "allowed": allowed,
            }
        elif status == 413:
            body = {
                "error": "Payload too large",
                "message": "The request body exceeds the maximum allowed size",
                "max_bytes": app.config.get("MAX_CONTENT_LENGTH"),
            }
        elif status == 429:
            retry_after = getattr(error, "retry_after", None) or 60
            body = {
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
                "retry_after": retry_after,
                "limit": str(error.description or ""),
            }
        elif status == 400:
            body = {"error": "Bad request", "message": str(error.description or "Invalid request")}
        else:
            body = {"error": error.name, "message": str(error.description or "")}
        response = _json(body, status)
        if status == 429:
            response.headers.setdefault("Retry-After", str(body["retry_after"]))
        return response

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception) -> Response:
        logger.exception("Unhandled error on %s %s", request.method, request.path)
        return _json(
            {"error": "Internal server error", "message": "Something went wrong on our end. Please try again later."},
            500,
        )
