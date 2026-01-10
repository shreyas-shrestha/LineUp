"""Pydantic schemas for request/response validation."""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import re


class AppointmentCreate(BaseModel):
    """Schema for creating a new appointment."""
    
    client_name: str = Field(..., min_length=1, max_length=100, alias="clientName")
    client_id: str = Field(default="current_user", alias="clientId")
    barber_name: str = Field(..., min_length=1, max_length=100, alias="barberName")
    barber_id: str = Field(..., min_length=1, alias="barberId")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    time: str = Field(..., description="Time in HH:MM format")
    service: str = Field(..., min_length=1, max_length=100)
    price: str = Field(default="$0")
    notes: str = Field(default="No special requests", max_length=500)
    
    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v
    
    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("Time must be in HH:MM format")
        return v

    class Config:
        populate_by_name = True


class AppointmentUpdate(BaseModel):
    """Schema for updating appointment status."""
    
    status: str = Field(..., pattern="^(pending|confirmed|completed|cancelled|rejected|rescheduled)$")
    reason: Optional[str] = Field(default=None, max_length=500)
    new_date: Optional[str] = Field(default=None, alias="date")
    new_time: Optional[str] = Field(default=None, alias="time")

    class Config:
        populate_by_name = True


class SocialPostCreate(BaseModel):
    """Schema for creating a social post."""
    
    username: str = Field(default="anonymous", max_length=50)
    avatar: Optional[str] = Field(default=None)
    image: str = Field(..., min_length=1, description="Base64 encoded image data")
    caption: str = Field(default="", max_length=500)
    hashtags: List[str] = Field(default_factory=list)
    
    @field_validator("hashtags")
    @classmethod
    def validate_hashtags(cls, v: List[str]) -> List[str]:
        # Limit to 10 hashtags, each max 30 chars
        validated = []
        for tag in v[:10]:
            clean_tag = tag.strip().lstrip("#")[:30]
            if clean_tag:
                validated.append(clean_tag)
        return validated


class ReviewCreate(BaseModel):
    """Schema for creating a barber review."""
    
    username: str = Field(default="anonymous", max_length=50)
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5 stars")
    text: str = Field(default="", max_length=1000)


class PortfolioItemCreate(BaseModel):
    """Schema for adding a portfolio item."""
    
    style_name: str = Field(..., min_length=1, max_length=100, alias="styleName")
    image: str = Field(..., min_length=1, description="Base64 encoded image or URL")
    description: str = Field(default="", max_length=500)
    barber_id: str = Field(default="default_barber", alias="barberId")

    class Config:
        populate_by_name = True


class ServiceCreate(BaseModel):
    """Schema for creating a barber service."""
    
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., ge=0, le=10000)
    duration: int = Field(default=30, ge=5, le=480, description="Duration in minutes")
    category: str = Field(default="General", max_length=50)
    description: str = Field(default="", max_length=500)


class SubscriptionPackageCreate(BaseModel):
    """Schema for creating a subscription package."""
    
    barber_id: str = Field(..., min_length=1, alias="barberId")
    barber_name: str = Field(..., min_length=1, max_length=100, alias="barberName")
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    price: str = Field(..., min_length=1)
    num_cuts: int = Field(..., ge=1, le=100, alias="numCuts")
    duration_months: int = Field(..., ge=1, le=24, alias="durationMonths")
    discount: str = Field(default="", max_length=50)

    class Config:
        populate_by_name = True


class AnalyzeRequest(BaseModel):
    """Schema for the AI analysis request."""
    
    payload: dict = Field(..., description="Gemini API payload with image data")


class VirtualTryOnRequest(BaseModel):
    """Schema for virtual try-on request."""
    
    user_photo: str = Field(..., min_length=1, alias="userPhoto", description="Base64 encoded photo")
    style_description: str = Field(..., min_length=1, max_length=200, alias="styleDescription")

    class Config:
        populate_by_name = True


# Response schemas for consistent API responses
class APIResponse(BaseModel):
    """Standard API response wrapper."""
    
    success: bool = True
    data: Optional[dict] = None
    error: Optional[str] = None
    message: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    
    success: bool = True
    data: List[dict] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 20
    has_more: bool = False



