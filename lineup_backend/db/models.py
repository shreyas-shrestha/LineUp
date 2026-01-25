"""Pydantic models for Firestore data entities."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, EmailStr


class UserModel(BaseModel):
    """User profile model."""
    
    id: Optional[str] = None
    email: EmailStr
    display_name: str = Field(..., alias="displayName")
    role: str = "client"  # "client" or "barber"
    avatar: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    email_verified: bool = Field(default=False, alias="emailVerified")
    created_at: datetime = Field(default_factory=datetime.now, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.now, alias="updatedAt")
    
    # Barber-specific fields
    barber_info: Optional[Dict[str, Any]] = Field(default=None, alias="barberInfo")
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SavedAnalysisModel(BaseModel):
    """Saved haircut analysis results model."""
    
    id: Optional[str] = None
    user_id: str = Field(..., alias="userId")
    image_url: Optional[str] = Field(default=None, alias="imageUrl")
    image_base64: Optional[str] = Field(default=None, alias="imageBase64")
    recommendations: List[str] = []
    face_shape: Optional[str] = Field(default=None, alias="faceShape")
    hair_texture: Optional[str] = Field(default=None, alias="hairTexture")
    analysis_data: Dict[str, Any] = Field(default_factory=dict, alias="analysisData")
    created_at: datetime = Field(default_factory=datetime.now, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.now, alias="updatedAt")
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SocialPostModel(BaseModel):
    """Social post model."""
    
    id: Optional[str] = None
    user_id: str = Field(..., alias="userId")
    username: str
    avatar: str
    image: str  # base64 encoded
    caption: str = ""
    hashtags: List[str] = []
    likes: int = 0
    shares: int = 0
    comments: int = 0
    liked: bool = False
    time_ago: str = Field(default="now", alias="timeAgo")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PostCommentModel(BaseModel):
    """Post comment model."""
    
    id: Optional[str] = None
    post_id: str = Field(..., alias="postId")
    user_id: str = Field(..., alias="userId")
    username: str
    text: str
    time_ago: str = Field(default="just now", alias="timeAgo")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PostLikeModel(BaseModel):
    """Post like model."""
    
    id: Optional[str] = None
    post_id: str = Field(..., alias="postId")
    user_id: str = Field(..., alias="userId")
    created_at: datetime = Field(default_factory=datetime.now, alias="createdAt")
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserFollowModel(BaseModel):
    """User follow relationship model."""
    
    id: Optional[str] = None
    follower_id: str = Field(..., alias="followerId")
    following_id: str = Field(..., alias="followingId")
    created_at: datetime = Field(default_factory=datetime.now, alias="createdAt")
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AppointmentModel(BaseModel):
    """Appointment model."""
    
    id: Optional[str] = None
    client_id: str = Field(..., alias="clientId")
    client_name: str = Field(..., alias="clientName")
    barber_id: str = Field(..., alias="barberId")
    barber_name: str = Field(..., alias="barberName")
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    service: str = ""
    price: str = "$0"
    status: str = "pending"  # pending, confirmed, completed, cancelled, rejected, rescheduled
    notes: str = ""
    rejection_reason: Optional[str] = Field(default=None, alias="rejectionReason")
    cancellation_reason: Optional[str] = Field(default=None, alias="cancellationReason")
    reschedule_history: List[Dict[str, Any]] = Field(default_factory=list, alias="rescheduleHistory")
    barber_notes: List[Dict[str, Any]] = Field(default_factory=list, alias="barberNotes")
    status_updated_at: Optional[datetime] = Field(default=None, alias="statusUpdatedAt")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PortfolioModel(BaseModel):
    """Barber portfolio work model."""
    
    id: Optional[str] = None
    barber_id: str = Field(..., alias="barberId")
    style_name: str = Field(..., alias="styleName")
    image: str  # base64 encoded or URL
    description: str = ""
    likes: int = 0
    date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ReviewModel(BaseModel):
    """Barber review model."""
    
    id: Optional[str] = None
    barber_id: str = Field(..., alias="barberId")
    client_id: str = Field(..., alias="clientId")
    client_name: Optional[str] = Field(default=None, alias="clientName")
    rating: int = Field(..., ge=1, le=5)
    text: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BarberMetricModel(BaseModel):
    """Barber metric aggregate model."""
    
    id: Optional[str] = None
    barber_id: str = Field(..., alias="barberId")
    metric_type: str = Field(..., alias="metricType")  # appointment_count, revenue, etc.
    period: str  # daily, weekly, monthly
    date: str  # YYYY-MM-DD or YYYY-MM or YYYY
    value: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.now, alias="updatedAt")
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BarberEventModel(BaseModel):
    """Barber event tracking model."""
    
    id: Optional[str] = None
    barber_id: str = Field(..., alias="barberId")
    event_type: str = Field(..., alias="eventType")  # appointment_created, portfolio_view, etc.
    timestamp: datetime = Field(default_factory=datetime.now)
    data: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = Field(default=None, alias="userId")
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class NotificationModel(BaseModel):
    """Notification model."""
    
    id: Optional[str] = None
    user_id: str = Field(..., alias="userId")
    type: str  # new_follower, post_like, post_comment, appointment_request, etc.
    title: str
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.now, alias="createdAt")
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
