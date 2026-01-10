"""Validation schemas for barber-related requests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import (
    BaseSchema,
    ValidationError,
    sanitize_string,
    validate_length,
    validate_range,
    validate_time,
)


@dataclass
class ServiceCreate(BaseSchema):
    """Schema for creating a new barber service."""

    name: str
    price: float
    duration: int  # minutes
    category: str
    description: str = ""

    VALID_CATEGORIES = {"Hair", "Beard", "Package", "Special", "Add-on", "General"}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceCreate":
        """Create and validate service from request data."""
        errors: Dict[str, str] = {}

        # Required: name
        name = sanitize_string(data.get("name", ""), 100)
        if not name:
            errors["name"] = "Service name is required"

        # Required: price
        try:
            price = float(data.get("price", 0))
            if price < 0:
                errors["price"] = "Price must be non-negative"
            if price > 10000:
                errors["price"] = "Price seems unreasonably high"
        except (TypeError, ValueError):
            errors["price"] = "Invalid price format"
            price = 0

        # Required: duration
        try:
            duration = int(data.get("duration", 30))
            if duration < 5:
                errors["duration"] = "Duration must be at least 5 minutes"
            if duration > 480:
                errors["duration"] = "Duration cannot exceed 8 hours"
        except (TypeError, ValueError):
            errors["duration"] = "Invalid duration format"
            duration = 30

        # Optional: category
        category = sanitize_string(data.get("category", "General"), 50)
        # Don't enforce strict categories, just suggest
        if category not in cls.VALID_CATEGORIES:
            category = "General"

        # Optional: description
        description = sanitize_string(data.get("description", ""), 500)

        if errors:
            raise ValidationError(errors)

        return cls(
            name=name,
            price=price,
            duration=duration,
            category=category,
            description=description,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "name": self.name,
            "price": self.price,
            "duration": self.duration,
            "category": self.category,
            "description": self.description,
            "createdAt": datetime.now().isoformat(),
        }


@dataclass
class DayHours:
    """Working hours for a single day."""
    
    enabled: bool = True
    start: str = "09:00"
    end: str = "18:00"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DayHours":
        """Create day hours from dictionary."""
        enabled = data.get("enabled", True)
        start = data.get("start", "09:00")
        end = data.get("end", "18:00")

        # Validate times if enabled
        if enabled:
            try:
                validate_time(start, "start")
                validate_time(end, "end")
            except ValidationError:
                # Default to standard hours on validation failure
                start = "09:00"
                end = "18:00"

        return cls(enabled=enabled, start=start, end=end)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "start": self.start,
            "end": self.end,
        }


@dataclass
class AvailabilityUpdate(BaseSchema):
    """Schema for updating barber availability."""
    
    working_hours: Dict[str, DayHours]
    break_times: List[Dict[str, str]]
    blocked_dates: List[str]
    service_duration: int  # minutes
    buffer_time: int  # minutes between appointments
    timezone: str

    DAYS_OF_WEEK = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AvailabilityUpdate":
        """Create and validate availability from request data."""
        errors: Dict[str, str] = {}

        # Parse working hours
        working_hours_data = data.get("workingHours", {})
        working_hours: Dict[str, DayHours] = {}
        
        for day in cls.DAYS_OF_WEEK:
            day_data = working_hours_data.get(day, {})
            working_hours[day] = DayHours.from_dict(day_data)

        # Parse break times
        break_times = data.get("breakTimes", [])
        validated_breaks = []
        for break_time in break_times:
            if isinstance(break_time, dict) and "start" in break_time and "end" in break_time:
                try:
                    validate_time(break_time["start"])
                    validate_time(break_time["end"])
                    validated_breaks.append(break_time)
                except ValidationError:
                    pass  # Skip invalid break times

        # Parse blocked dates
        blocked_dates = data.get("blockedDates", [])
        validated_dates = []
        for date_str in blocked_dates:
            if isinstance(date_str, str):
                try:
                    datetime.strptime(date_str, "%Y-%m-%d")
                    validated_dates.append(date_str)
                except ValueError:
                    pass  # Skip invalid dates

        # Service duration
        try:
            service_duration = int(data.get("serviceDuration", 30))
            if service_duration < 5 or service_duration > 480:
                service_duration = 30
        except (TypeError, ValueError):
            service_duration = 30

        # Buffer time
        try:
            buffer_time = int(data.get("bufferTime", 15))
            if buffer_time < 0 or buffer_time > 120:
                buffer_time = 15
        except (TypeError, ValueError):
            buffer_time = 15

        # Timezone
        timezone = sanitize_string(data.get("timezone", "America/New_York"), 50)
        if not timezone:
            timezone = "America/New_York"

        if errors:
            raise ValidationError(errors)

        return cls(
            working_hours=working_hours,
            break_times=validated_breaks,
            blocked_dates=validated_dates,
            service_duration=service_duration,
            buffer_time=buffer_time,
            timezone=timezone,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "workingHours": {day: hours.to_dict() for day, hours in self.working_hours.items()},
            "breakTimes": self.break_times,
            "blockedDates": self.blocked_dates,
            "serviceDuration": self.service_duration,
            "bufferTime": self.buffer_time,
            "timezone": self.timezone,
            "updatedAt": datetime.now().isoformat(),
        }


@dataclass
class PortfolioWorkCreate(BaseSchema):
    """Schema for adding portfolio work."""

    style_name: str
    image: str  # base64 encoded
    description: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PortfolioWorkCreate":
        """Create and validate portfolio work from request data."""
        errors: Dict[str, str] = {}

        style_name = sanitize_string(data.get("styleName", ""), 100)
        if not style_name:
            errors["styleName"] = "Style name is required"

        image = data.get("image", "")
        if not image:
            errors["image"] = "Image is required"

        description = sanitize_string(data.get("description", ""), 500)

        if errors:
            raise ValidationError(errors)

        return cls(
            style_name=style_name,
            image=image,
            description=description,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "styleName": self.style_name,
            "image": self.image,
            "description": self.description,
            "likes": 0,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat(),
        }
