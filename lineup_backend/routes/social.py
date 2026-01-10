"""Social feed and community endpoints."""

import base64
import logging
import uuid
from datetime import datetime
from io import BytesIO

from flask import Blueprint, request
from PIL import Image

from lineup_backend.utils import cors_response, handle_options, api_response, safe_get_json
from lineup_backend import storage as memory_store

logger = logging.getLogger(__name__)

social_bp = Blueprint('social', __name__)


@social_bp.route('/social', methods=['GET', 'POST', 'OPTIONS'])
@handle_options("GET, POST, OPTIONS")
def social():
    """Get all posts or create a new post."""
    
    if request.method == 'GET':
        posts = memory_store.social_posts
        sorted_posts = sorted(posts, key=lambda x: x.get('timestamp', ''), reverse=True)
        return cors_response({"posts": sorted_posts})
    
    elif request.method == 'POST':
        try:
            data = safe_get_json()
            image_base64 = data.get("image", "")
            
            if not image_base64:
                return api_response(error="Image is required", status=400)
            
            # Validate image
            try:
                if ',' in image_base64:
                    image_base64_clean = image_base64.split(',')[1]
                else:
                    image_base64_clean = image_base64
                
                image_bytes = base64.b64decode(image_base64_clean)
                img = Image.open(BytesIO(image_bytes))
                img.verify()
            except Exception as e:
                logger.error(f"Invalid image: {str(e)}")
                return api_response(error="Invalid image format", status=400)
            
            # Create new post
            new_post = {
                "id": str(uuid.uuid4()),
                "username": data.get("username", "anonymous"),
                "avatar": data.get("avatar", "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&h=100&fit=crop&crop=face"),
                "image": image_base64,
                "caption": data.get("caption", ""),
                "likes": 0,
                "timeAgo": "now",
                "liked": False,
                "timestamp": datetime.now().isoformat(),
                "shares": 0,
                "comments": 0,
                "hashtags": data.get("hashtags", [])
            }
            
            memory_store.social_posts.insert(0, new_post)
            logger.info(f"Social post created: {new_post['id']}")
            
            return api_response(data={"post": new_post}, message="Post created successfully", status=201)
            
        except Exception as e:
            logger.error(f"Error creating post: {str(e)}")
            return api_response(error="Failed to create post", status=400)


@social_bp.route('/social/<post_id>/like', methods=['POST', 'OPTIONS'])
@handle_options("POST, OPTIONS")
def toggle_like(post_id):
    """Toggle like on a post."""
    try:
        post = next((p for p in memory_store.social_posts if str(p.get("id")) == str(post_id)), None)
        
        if not post:
            return api_response(error="Post not found", status=404)
        
        current_liked = post.get("liked", False)
        new_liked = not current_liked
        current_likes = post.get("likes", 0)
        new_likes = max(0, current_likes + (1 if new_liked else -1))
        
        post["liked"] = new_liked
        post["likes"] = new_likes
        
        return cors_response({
            "success": True,
            "liked": new_liked,
            "likes": new_likes
        })
        
    except Exception as e:
        logger.error(f"Error toggling like: {str(e)}")
        return api_response(error="Failed to toggle like", status=400)


@social_bp.route('/social/<post_id>/share', methods=['POST', 'OPTIONS'])
@handle_options("POST, OPTIONS")
def share_post(post_id):
    """Increment share count on a post."""
    try:
        post = next((p for p in memory_store.social_posts if str(p.get("id")) == str(post_id)), None)
        
        if not post:
            return api_response(error="Post not found", status=404)
        
        post["shares"] = post.get("shares", 0) + 1
        
        return cors_response({
            "success": True,
            "shares": post["shares"]
        })
        
    except Exception as e:
        logger.error(f"Error sharing post: {str(e)}")
        return api_response(error="Failed to share post", status=400)


@social_bp.route('/social/<post_id>/comments', methods=['GET', 'POST', 'OPTIONS'])
@handle_options("GET, POST, OPTIONS")
def handle_comments(post_id):
    """Get or add comments on a post."""
    
    if request.method == 'GET':
        comments = memory_store.post_comments.get(post_id, [])
        return cors_response({"comments": comments})
    
    elif request.method == 'POST':
        try:
            data = safe_get_json()
            
            new_comment = {
                "id": str(uuid.uuid4()),
                "username": data.get("username", "anonymous"),
                "text": data.get("text", ""),
                "timeAgo": "just now",
                "timestamp": datetime.now().isoformat()
            }
            
            if post_id not in memory_store.post_comments:
                memory_store.post_comments[post_id] = []
            
            memory_store.post_comments[post_id].append(new_comment)
            
            # Update comment count on post
            post = next((p for p in memory_store.social_posts if str(p.get("id")) == str(post_id)), None)
            if post:
                post["comments"] = post.get("comments", 0) + 1
            
            return api_response(data={"comment": new_comment}, message="Comment added", status=201)
            
        except Exception as e:
            logger.error(f"Error adding comment: {str(e)}")
            return api_response(error="Failed to add comment", status=400)


@social_bp.route('/users/<user_id>/follow', methods=['POST', 'OPTIONS'])
@social_bp.route('/users/<user_id>/unfollow', methods=['POST', 'OPTIONS'])
@handle_options("POST, OPTIONS")
def toggle_follow(user_id):
    """Follow or unfollow a user."""
    try:
        data = safe_get_json()
        follower_id = data.get("follower_id", "current_user")
        
        if request.path.endswith('/follow'):
            if follower_id not in memory_store.user_follows:
                memory_store.user_follows[follower_id] = []
            if user_id not in memory_store.user_follows[follower_id]:
                memory_store.user_follows[follower_id].append(user_id)
        else:  # unfollow
            if follower_id in memory_store.user_follows:
                memory_store.user_follows[follower_id] = [
                    uid for uid in memory_store.user_follows[follower_id] if uid != user_id
                ]
        
        return cors_response({"success": True})
        
    except Exception as e:
        logger.error(f"Error toggling follow: {str(e)}")
        return api_response(error="Failed to toggle follow", status=400)

