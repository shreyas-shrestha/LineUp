"""Cross-cutting request/response concerns: CORS, error handling, optional auth."""

from lineup_backend.middleware.cors import configure_cors
from lineup_backend.middleware.error_handler import ApiError, register_error_handlers

__all__ = ["configure_cors", "ApiError", "register_error_handlers"]
