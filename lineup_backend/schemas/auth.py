"""Authentication-related Pydantic schemas."""

from __future__ import annotations

from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, EmailStr
import re


class UserCreate(BaseModel):
    """Schema for user registration."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=100, alias="displayName")
    role: Literal["client", "barber"] = Field(default="client")
    phone: Optional[str] = Field(default=None, max_length=20)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Ensure password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    class Config:
        populate_by_name = True


class UserLogin(BaseModel):
    """Schema for user login."""
    
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    
    access_token: str = Field(alias="accessToken")
    token_type: str = Field(default="Bearer", alias="tokenType")
    expires_in: int = Field(alias="expiresIn")
    user: "UserResponse"

    class Config:
        populate_by_name = True


class UserResponse(BaseModel):
    """Schema for user data in responses."""
    
    id: str
    email: str
    display_name: str = Field(alias="displayName")
    role: str
    phone: Optional[str] = None
    avatar: Optional[str] = None
    created_at: str = Field(alias="createdAt")

    class Config:
        populate_by_name = True


class PasswordReset(BaseModel):
    """Schema for password reset request."""
    
    email: EmailStr


class PasswordChange(BaseModel):
    """Schema for changing password."""
    
    current_password: str = Field(..., min_length=1, alias="currentPassword")
    new_password: str = Field(..., min_length=8, max_length=128, alias="newPassword")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    class Config:
        populate_by_name = True


class ProfileUpdate(BaseModel):
    """Schema for updating user profile."""
    
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=100, alias="displayName")
    phone: Optional[str] = Field(default=None, max_length=20)
    avatar: Optional[str] = None

    class Config:
        populate_by_name = True

