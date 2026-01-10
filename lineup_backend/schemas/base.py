"""Base validation utilities using dataclasses (no external dependencies)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar

T = TypeVar("T")


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(self, errors: Dict[str, str]):
        self.errors = errors
        super().__init__(f"Validation failed: {errors}")


def validate_required(value: Any, field_name: str) -> None:
    """Validate that a field is not None or empty."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError({field_name: f"{field_name} is required"})


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_date(date_str: str, field_name: str = "date") -> datetime:
    """Validate and parse date string (YYYY-MM-DD format)."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValidationError(
            {field_name: f"Invalid date format. Expected YYYY-MM-DD, got '{date_str}'"}
        )


def validate_time(time_str: str, field_name: str = "time") -> str:
    """Validate time string (HH:MM format)."""
    pattern = r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$"
    if not re.match(pattern, time_str):
        raise ValidationError(
            {field_name: f"Invalid time format. Expected HH:MM, got '{time_str}'"}
        )
    return time_str


def validate_length(
    value: str,
    field_name: str,
    min_length: int = 0,
    max_length: int = 10000,
) -> None:
    """Validate string length."""
    if len(value) < min_length:
        raise ValidationError(
            {field_name: f"{field_name} must be at least {min_length} characters"}
        )
    if len(value) > max_length:
        raise ValidationError(
            {field_name: f"{field_name} must be at most {max_length} characters"}
        )


def validate_range(
    value: int | float,
    field_name: str,
    min_value: Optional[int | float] = None,
    max_value: Optional[int | float] = None,
) -> None:
    """Validate numeric range."""
    if min_value is not None and value < min_value:
        raise ValidationError(
            {field_name: f"{field_name} must be at least {min_value}"}
        )
    if max_value is not None and value > max_value:
        raise ValidationError(
            {field_name: f"{field_name} must be at most {max_value}"}
        )


def sanitize_string(value: str, max_length: int = 10000) -> str:
    """Sanitize a string by stripping whitespace and limiting length."""
    if not value:
        return ""
    return value.strip()[:max_length]


def validate_base64_image(data: str, field_name: str = "image") -> str:
    """Validate and extract base64 image data."""
    if not data:
        raise ValidationError({field_name: "Image data is required"})
    
    # Remove data URI prefix if present
    if "," in data:
        parts = data.split(",")
        if len(parts) == 2:
            header, base64_data = parts
            if not header.startswith("data:image"):
                raise ValidationError({field_name: "Invalid image data format"})
            return base64_data
    
    # Assume it's raw base64
    return data


@dataclass
class BaseSchema:
    """Base class for validation schemas."""

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create schema instance from dictionary, validating fields."""
        raise NotImplementedError("Subclasses must implement from_dict")

    def to_dict(self) -> Dict[str, Any]:
        """Convert schema to dictionary."""
        raise NotImplementedError("Subclasses must implement to_dict")

