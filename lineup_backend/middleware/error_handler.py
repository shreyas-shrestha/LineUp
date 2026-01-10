"""Standardized error handling for the LineUp backend."""

from __future__ import annotations

import logging
import traceback
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple, Union

from flask import Flask, jsonify, make_response, request

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base exception for API errors with standardized response format."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or f"ERR_{status_code}"
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to response dictionary."""
        response = {
            "success": False,
            "error": {
                "code": self.error_code,
                "message": self.message,
            },
        }
        if self.details:
            response["error"]["details"] = self.details
        return response


class ValidationError(APIError):
    """Raised when request validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class AuthenticationError(APIError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
        )


class AuthorizationError(APIError):
    """Raised when user lacks permission."""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
        )


class NotFoundError(APIError):
    """Raised when a resource is not found."""

    def __init__(self, resource: str = "Resource", resource_id: Optional[str] = None):
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with ID '{resource_id}' not found"
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
        )


class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after},
        )


class ExternalServiceError(APIError):
    """Raised when an external service fails."""

    def __init__(self, service: str, message: Optional[str] = None):
        super().__init__(
            message=message or f"External service '{service}' is unavailable",
            status_code=503,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service},
        )


def create_success_response(
    data: Any = None,
    message: Optional[str] = None,
    status_code: int = 200,
) -> Tuple[Any, int]:
    """Create a standardized success response."""
    response = {"success": True}
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = message
    
    resp = make_response(jsonify(response), status_code)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


def create_error_response(
    error: Union[APIError, Exception],
    status_code: Optional[int] = None,
) -> Tuple[Any, int]:
    """Create a standardized error response."""
    if isinstance(error, APIError):
        response = error.to_dict()
        code = error.status_code
    else:
        response = {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        }
        code = status_code or 500
    
    resp = make_response(jsonify(response), code)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


def handle_errors(func: Callable) -> Callable:
    """Decorator to handle errors in route handlers."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except APIError as e:
            logger.warning(f"API Error in {func.__name__}: {e.message}")
            return create_error_response(e)
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            logger.error(traceback.format_exc())
            return create_error_response(e, 500)

    return wrapper


def register_error_handlers(app: Flask) -> None:
    """Register global error handlers with the Flask app."""

    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        return create_error_response(error)

    @app.errorhandler(400)
    def handle_bad_request(error):
        return create_error_response(
            APIError("Bad request", 400, "BAD_REQUEST")
        )

    @app.errorhandler(404)
    def handle_not_found(error):
        return create_error_response(
            NotFoundError("Endpoint")
        )

    @app.errorhandler(429)
    def handle_rate_limit(error):
        retry_after = getattr(error, "retry_after", 60)
        return create_error_response(RateLimitError(retry_after))

    @app.errorhandler(500)
    def handle_internal_error(error):
        logger.error(f"Internal server error: {str(error)}")
        return create_error_response(
            APIError(
                "Internal server error. Please try again later.",
                500,
                "INTERNAL_ERROR",
            )
        )

    @app.errorhandler(503)
    def handle_service_unavailable(error):
        return create_error_response(
            ExternalServiceError("backend", "Service temporarily unavailable")
        )
