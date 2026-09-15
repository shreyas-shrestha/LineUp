"""CORS configuration. Origins may be exact strings or regular expressions."""

from __future__ import annotations

from typing import List

from flask import Flask
from flask_cors import CORS


def configure_cors(app: Flask, allowed_origins: List[str]) -> None:
    origins: List[str] = ["*"] if "*" in allowed_origins else list(allowed_origins)
    CORS(
        app,
        origins=origins,
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Accept", "Authorization"],
        expose_headers=["Retry-After", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
        supports_credentials=False,
        max_age=86400,
    )
