"""Repository for social posts, comments, likes, and follows."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from lineup_backend.db.repository import BaseRepository
from lineup_backend.db.models import (
    SocialPostModel,
    PostCommentModel,
    PostLikeModel,
    UserFollowModel,
)

logger = logging.getLogger(__name__)


class SocialRepository(BaseRepository):
    """Repository for social posts."""
    
    def __init__(self):
        super().__init__("social_posts")
    
    def create_post(self, user_id: str, username: str, avatar: str, image: str,
                   caption: str = "", hashtags: Optional[List[str]] = None) -> Optional[Dict]:
        """Create a new social post."""
        post_id = str(uuid.uuid4())
        post_data = SocialPostModel(
            id=post_id,
            userId=user_id,
            username=username,
            avatar=avatar,
            image=image,
            caption=caption,
            hashtags=hashtags or [],
            likes=0,
            shares=0,
            comments=0,
            liked=False,
            timeAgo="now",
            timestamp=datetime.now()
        )
        
        data = post_data.model_dump(by_alias=True, exclude={"id"})
        result = self.create(post_id, data)
        
        if result:
            result["id"] = post_id
        return result
    
    def get_posts(self, limit: Optional[int] = None, user_id: Optional[str] = None) -> List[Dict]:
        """Get posts, optionally filtered by user."""
        if user_id:
            posts = self.query([("userId", "==", user_id)], limit=limit, order_by="timestamp", direction="desc")
        else:
            posts = self.get_all(limit=limit, order_by="timestamp", direction="desc")
        return posts
    
    def get_post(self, post_id: str) -> Optional[Dict]:
        """Get a single post by ID."""
        return self.get_by_id(post_id)
    
    def update_post(self, post_id: str, data: Dict) -> Optional[Dict]:
        """Update a post."""
        return self.update(post_id, data)
    
    def delete_post(self, post_id: str) -> bool:
        """Delete a post."""
        return self.delete(post_id)
    
    def increment_likes(self, post_id: str) -> Optional[Dict]:
        """Increment likes count on a post."""
        post = self.get_by_id(post_id)
        if post:
            current_likes = post.get("likes", 0)
            return self.update(post_id, {"likes": current_likes + 1})
        return None
    
    def decrement_likes(self, post_id: str) -> Optional[Dict]:
        """Decrement likes count on a post."""
        post = self.get_by_id(post_id)
        if post:
            current_likes = post.get("likes", 0)
            return self.update(post_id, {"likes": max(0, current_likes - 1)})
        return None
    
    def increment_shares(self, post_id: str) -> Optional[Dict]:
        """Increment shares count on a post."""
        post = self.get_by_id(post_id)
        if post:
            current_shares = post.get("shares", 0)
            return self.update(post_id, {"shares": current_shares + 1})
        return None
    
    def increment_comments(self, post_id: str) -> Optional[Dict]:
        """Increment comments count on a post."""
        post = self.get_by_id(post_id)
        if post:
            current_comments = post.get("comments", 0)
            return self.update(post_id, {"comments": current_comments + 1})
        return None


class CommentRepository(BaseRepository):
    """Repository for post comments."""
    
    def __init__(self):
        super().__init__("post_comments")
    
    def create_comment(self, post_id: str, user_id: str, username: str, text: str) -> Optional[Dict]:
        """Create a new comment."""
        comment_id = str(uuid.uuid4())
        comment_data = PostCommentModel(
            id=comment_id,
            postId=post_id,
            userId=user_id,
            username=username,
            text=text,
            timeAgo="just now",
            timestamp=datetime.now()
        )
        
        data = comment_data.model_dump(by_alias=True, exclude={"id"})
        result = self.create(comment_id, data)
        
        if result:
            result["id"] = comment_id
        return result
    
    def get_comments(self, post_id: str, limit: Optional[int] = None) -> List[Dict]:
        """Get comments for a post."""
        return self.query([("postId", "==", post_id)], limit=limit, order_by="timestamp", direction="desc")
    
    def delete_comment(self, comment_id: str) -> bool:
        """Delete a comment."""
        return self.delete(comment_id)


class LikeRepository(BaseRepository):
    """Repository for post likes."""
    
    def __init__(self):
        super().__init__("post_likes")
    
    def create_like(self, post_id: str, user_id: str) -> Optional[Dict]:
        """Create a like record."""
        like_id = f"{post_id}_{user_id}"  # Composite key
        like_data = PostLikeModel(
            id=like_id,
            postId=post_id,
            userId=user_id,
            createdAt=datetime.now()
        )
        
        data = like_data.model_dump(by_alias=True, exclude={"id"})
        result = self.create(like_id, data)
        
        if result:
            result["id"] = like_id
        return result
    
    def delete_like(self, post_id: str, user_id: str) -> bool:
        """Delete a like record."""
        like_id = f"{post_id}_{user_id}"
        return self.delete(like_id)
    
    def has_liked(self, post_id: str, user_id: str) -> bool:
        """Check if user has liked a post."""
        like_id = f"{post_id}_{user_id}"
        like = self.get_by_id(like_id)
        return like is not None
    
    def get_likes(self, post_id: str) -> List[Dict]:
        """Get all likes for a post."""
        return self.query([("postId", "==", post_id)])


class FollowRepository(BaseRepository):
    """Repository for user follow relationships."""
    
    def __init__(self):
        super().__init__("user_follows")
    
    def create_follow(self, follower_id: str, following_id: str) -> Optional[Dict]:
        """Create a follow relationship."""
        follow_id = f"{follower_id}_{following_id}"  # Composite key
        
        # Check if already following
        if self.get_by_id(follow_id):
            return None
        
        follow_data = UserFollowModel(
            id=follow_id,
            followerId=follower_id,
            followingId=following_id,
            createdAt=datetime.now()
        )
        
        data = follow_data.model_dump(by_alias=True, exclude={"id"})
        result = self.create(follow_id, data)
        
        if result:
            result["id"] = follow_id
        return result
    
    def delete_follow(self, follower_id: str, following_id: str) -> bool:
        """Delete a follow relationship."""
        follow_id = f"{follower_id}_{following_id}"
        return self.delete(follow_id)
    
    def is_following(self, follower_id: str, following_id: str) -> bool:
        """Check if follower is following following."""
        follow_id = f"{follower_id}_{following_id}"
        follow = self.get_by_id(follow_id)
        return follow is not None
    
    def get_followers(self, user_id: str) -> List[Dict]:
        """Get all followers of a user."""
        return self.query([("followingId", "==", user_id)])
    
    def get_following(self, user_id: str) -> List[Dict]:
        """Get all users that a user is following."""
        return self.query([("followerId", "==", user_id)])
