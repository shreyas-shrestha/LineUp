"""Validation schemas for social/community-related requests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import (
    BaseSchema,
    ValidationError,
    sanitize_string,
    validate_base64_image,
    validate_length,
)


@dataclass
class SocialPostCreate(BaseSchema):
    """Schema for creating a new social post."""

    image: str  # base64 encoded
    caption: str
    username: str
    avatar: str
    hashtags: List[str]

    MAX_CAPTION_LENGTH = 500
    MAX_HASHTAGS = 10
    DEFAULT_AVATAR = "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&h=100&fit=crop&crop=face"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SocialPostCreate":
        """Create and validate social post from request data."""
        errors: Dict[str, str] = {}

        # Required: image
        image = data.get("image", "")
        if not image:
            errors["image"] = "Image is required"
        else:
            try:
                image = validate_base64_image(image)
            except ValidationError as e:
                errors.update(e.errors)

        # Optional: caption with length limit
        caption = sanitize_string(data.get("caption", ""), cls.MAX_CAPTION_LENGTH)

        # Optional: username
        username = sanitize_string(data.get("username", "anonymous"), 50)
        if not username:
            username = "anonymous"

        # Optional: avatar URL
        avatar = data.get("avatar", cls.DEFAULT_AVATAR)
        if not avatar:
            avatar = cls.DEFAULT_AVATAR

        # Extract hashtags from caption if not provided
        hashtags = data.get("hashtags", [])
        if not hashtags and caption:
            # Extract hashtags from caption
            import re
            hashtags = re.findall(r"#(\w+)", caption)
        
        # Limit hashtags
        hashtags = hashtags[:cls.MAX_HASHTAGS] if hashtags else []
        # Sanitize hashtags
        hashtags = [sanitize_string(tag.lower().replace("#", ""), 50) for tag in hashtags]

        if errors:
            raise ValidationError(errors)

        return cls(
            image=image,
            caption=caption,
            username=username,
            avatar=avatar,
            hashtags=hashtags,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "image": self.image,
            "caption": self.caption,
            "username": self.username,
            "avatar": self.avatar,
            "hashtags": self.hashtags,
            "likes": 0,
            "shares": 0,
            "comments": 0,
            "liked": False,
            "timeAgo": "now",
            "timestamp": datetime.now().isoformat(),
        }


@dataclass
class CommentCreate(BaseSchema):
    """Schema for creating a new comment."""

    text: str
    username: str

    MAX_COMMENT_LENGTH = 500

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommentCreate":
        """Create and validate comment from request data."""
        errors: Dict[str, str] = {}

        text = sanitize_string(data.get("text", ""), cls.MAX_COMMENT_LENGTH)
        if not text:
            errors["text"] = "Comment text is required"
        
        if len(text) < 1:
            errors["text"] = "Comment must not be empty"

        username = sanitize_string(data.get("username", "anonymous"), 50)
        if not username:
            username = "anonymous"

        if errors:
            raise ValidationError(errors)

        return cls(text=text, username=username)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "text": self.text,
            "username": self.username,
            "timeAgo": "just now",
            "timestamp": datetime.now().isoformat(),
        }
