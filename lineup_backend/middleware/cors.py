"""CORS configuration for the LineUp backend."""

from __future__ import annotations

from typing import List

from flask import Flask
from flask_cors import CORS


def configure_cors(app: Flask, allowed_origins: List[str]) -> None:
    """Configure CORS for the Flask application.
    
    Args:
        app: The Flask application instance
        allowed_origins: List of allowed origins (use ["*"] for development only)
    """
    # Filter out wildcard in production-like environments
    # Keep specific origins for better security
    is_production = app.config.get("ENV") == "production"
    
    if is_production and "*" in allowed_origins:
        # Remove wildcard in production, keep only specific origins
        allowed_origins = [o for o in allowed_origins if o != "*"]
        if not allowed_origins:
            # Fallback to a safe default
            allowed_origins = ["https://lineupai.onrender.com"]
    
    CORS(
        app,
        origins=allowed_origins,
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Accept", "Authorization"],
        supports_credentials=False,
        max_age=86400,  # Cache preflight for 24 hours
    )

