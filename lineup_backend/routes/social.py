"""Community feed: posts, likes, comments, shares, follows.

Reads are public (personalised with ``liked`` when a token is sent); every
write needs a signed-in user, whose uid/name become the author.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from flask import Blueprint, g, jsonify, request

from lineup_backend.context import services
from lineup_backend.extensions import limiter, rate
from lineup_backend.http import clean_text, decode_base64_image, get_json_body, json_response, new_id, now_iso, open_image, strip_data_url
from lineup_backend.middleware.auth import optional_auth, require_auth
from lineup_backend.middleware.error_handler import ApiError

bp = Blueprint("social", __name__)

DEFAULT_AVATAR = ""  # avatars are rendered from initials; never a stock photo


def _post_or_404(post_id: str):
    post = services().store.social_posts.get(post_id)
    if not post:
        raise ApiError("Post not found", 404)
    return post


def _viewer_uid() -> Optional[str]:
    user = getattr(g, "user", None)
    return user["uid"] if user else None


def _public_post(post: Dict[str, Any], viewer_uid: Optional[str]) -> Dict[str, Any]:
    liked_by = post.get("likedBy") if isinstance(post.get("likedBy"), list) else []
    public = {key: value for key, value in post.items() if key != "likedBy"}
    public["liked"] = bool(viewer_uid and viewer_uid in liked_by)
    public["likes"] = int(post.get("likes", 0) or 0)
    public["mine"] = bool(viewer_uid and post.get("authorUid") == viewer_uid)
    return public


@bp.route("/social", methods=["GET", "POST"])
@limiter.limit(rate("read"), methods=["GET"])
@limiter.limit(rate("social_write"), methods=["POST"])
@optional_auth
def social():
    svc = services()
    if request.method == "GET":
        viewer = _viewer_uid()
        posts = [_public_post(p, viewer) for p in svc.store.social_posts.list()]
        posts.sort(key=lambda p: p.get("timestamp", ""), reverse=True)
        return jsonify({"posts": posts})

    user = require_auth(lambda: g.user)()
    data = get_json_body()
    image_field = data.get("image")
    if not isinstance(image_field, str) or not image_field.strip():
        raise ApiError("Image is required", 400, success=False)
    try:
        image_bytes = decode_base64_image(image_field, field="image")
    except ApiError as exc:
        raise ApiError("Invalid image format. Please upload a valid image.", 400, success=False) from exc

    if svc.gemini.available:
        approved, reason = svc.gemini.moderate_image(open_image(image_bytes))
        if not approved:
            raise ApiError("Content rejected", 403, success=False, reason=reason)

    stored_url = svc.images.upload(image_bytes)
    raw_b64 = "".join(strip_data_url(image_field.strip()).split())
    hashtags = data.get("hashtags") if isinstance(data.get("hashtags"), list) else []
    post = svc.store.social_posts.create(
        {
            "username": clean_text(user.get("name"), default="anonymous", max_length=80),
            "authorUid": user["uid"],
            "avatar": clean_text(user.get("photoUrl"), default=DEFAULT_AVATAR, max_length=500),
            "image": stored_url or raw_b64,
            "caption": clean_text(data.get("caption"), max_length=2000),
            "likes": 0,
            "likedBy": [],
            "shares": 0,
            "comments": 0,
            "timeAgo": "now",
            "timestamp": now_iso(),
            "hashtags": [clean_text(tag, max_length=50).lstrip("#") for tag in hashtags if clean_text(tag)],
            "stored_in_storage": bool(stored_url),
        }
    )
    return json_response({"success": True, "post": _public_post(post, user["uid"])}, 201)


@bp.post("/social/<post_id>/like")
@limiter.limit(rate("engagement"))
@require_auth
def toggle_like(post_id: str):
    _post_or_404(post_id)
    uid = g.user["uid"]
    outcome: Dict[str, Any] = {}

    def mutate(current: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if current is None:
            return None
        liked_by = [u for u in (current.get("likedBy") or []) if isinstance(u, str)]
        likes = int(current.get("likes", 0) or 0)
        if uid in liked_by:
            liked_by.remove(uid)
            likes = max(0, likes - 1)
            outcome["liked"] = False
        else:
            liked_by.append(uid)
            likes += 1
            outcome["liked"] = True
        outcome["likes"] = likes
        return {"likedBy": liked_by, "likes": likes}

    services().store.social_posts.modify(post_id, mutate)
    return jsonify({"success": True, "liked": outcome.get("liked", False), "likes": outcome.get("likes", 0)})


@bp.route("/social/<post_id>/comments", methods=["GET", "POST"])
@limiter.limit(rate("read"), methods=["GET"])
@limiter.limit(rate("engagement"), methods=["POST"])
def comments(post_id: str):
    svc = services()
    doc = svc.store.post_comments.get(post_id) or {}
    items = list(doc.get("comments", []))
    if request.method == "GET":
        return jsonify({"comments": items})

    user = require_auth(lambda: g.user)()
    data = get_json_body()
    text = clean_text(data.get("text"), max_length=1000)
    if not text:
        raise ApiError("Comment text is required", 400)
    comment = {
        "id": new_id(),
        "username": clean_text(user.get("name"), default="anonymous", max_length=80),
        "uid": user["uid"],
        "text": text,
        "timeAgo": "just now",
        "timestamp": now_iso(),
    }
    # Append and bump the counter atomically: a read-modify-write here drops
    # comments (and drifts the count) when two people comment at once.
    def append(current: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        existing = list((current or {}).get("comments") or [])
        existing.append(comment)
        return {"comments": existing}

    stored = svc.store.post_comments.modify(post_id, append)
    total = len((stored or {}).get("comments") or [])
    svc.store.social_posts.modify(post_id, lambda cur: None if cur is None else {"comments": total})
    return json_response({"success": True, "comment": comment}, 201)


@bp.post("/social/<post_id>/share")
@limiter.limit(rate("engagement"))
@require_auth
def share(post_id: str):
    updated = services().store.social_posts.modify(post_id, lambda cur: None if cur is None else {"shares": int(cur.get("shares", 0) or 0) + 1})
    if not updated:
        raise ApiError("Post not found", 404)
    return jsonify({"success": True, "shares": int(updated.get("shares", 0) or 0)})


@bp.post("/users/<user_id>/follow")
@bp.post("/users/<user_id>/unfollow")
@limiter.limit(rate("engagement"))
@require_auth
def follow(user_id: str):
    follower_id = g.user["uid"]
    collection = services().store.user_follows
    doc = collection.get(follower_id) or {}
    following = [u for u in doc.get("following", []) if u != user_id]
    is_follow = request.path.endswith("/follow")
    if is_follow:
        following.append(user_id)
    collection.upsert(follower_id, {"following": following})
    return jsonify({"success": True, "following": is_follow, "followingCount": len(following)})


@bp.get("/users/me/following")
@limiter.limit(rate("read"))
@require_auth
def my_following():
    doc = services().store.user_follows.get(g.user["uid"]) or {}
    return jsonify({"following": list(doc.get("following", []))})
