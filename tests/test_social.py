from lineup_backend.services.gemini import REJECT_EXPLICIT
from tests.helpers import FakeGeminiModel, tiny_image_b64


def test_list_posts_newest_first_and_public(client):
    posts = client.get("/social").get_json()["posts"]
    assert [p["id"] for p in posts] == ["1", "2"]
    assert posts[0]["username"] == "mike_style"
    assert all(p["liked"] is False for p in posts)  # anonymous viewer
    assert all("likedBy" not in p for p in posts)


def test_liked_is_per_viewer(as_client, as_barber):
    posts = {p["id"]: p for p in as_client.get("/social").get_json()["posts"]}
    assert posts["2"]["liked"] is True and posts["1"]["liked"] is False  # seeded: client_1 liked post 2
    posts = {p["id"]: p for p in as_barber.get("/social").get_json()["posts"]}
    assert posts["2"]["liked"] is False


def test_create_post_requires_sign_in(client):
    response = client.post("/social", json={"image": tiny_image_b64()})
    assert response.status_code == 401


def test_create_post_requires_image(as_client):
    response = as_client.post("/social", json={"caption": "no image"})
    assert response.status_code == 400
    assert response.get_json() == {"error": "Image is required", "success": False}


def test_create_post_rejects_invalid_image(as_client):
    response = as_client.post("/social", json={"image": "bm90IGFuIGltYWdl"})
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False and "Invalid image" in data["error"]


def test_create_post_success(as_client, client):
    response = as_client.post(
        "/social",
        json={"username": "spoofed", "image": "data:image/png;base64," + tiny_image_b64(), "caption": "Fresh", "hashtags": ["#fade", "cut"]},
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    post = data["post"]
    assert post["image"] == tiny_image_b64()
    assert post["stored_in_storage"] is False
    assert post["username"] == "Alex Johnson" and post["authorUid"] == "client_1" and post["mine"] is True
    assert post["likes"] == 0 and post["comments"] == 0 and post["hashtags"] == ["fade", "cut"]
    assert post["liked"] is False and "likedBy" not in post
    listed = client.get("/social").get_json()["posts"][0]
    assert listed["id"] == post["id"] and listed["mine"] is False


def test_create_post_moderation_rejects(as_client, svc):
    svc.gemini.model = FakeGeminiModel(text='{"explicit_content": true, "hair_related": true}')
    response = as_client.post("/social", json={"image": tiny_image_b64()})
    assert response.status_code == 403
    assert response.get_json() == {"error": "Content rejected", "success": False, "reason": REJECT_EXPLICIT}


def test_create_post_moderation_permissive_on_bad_model_output(as_client, svc):
    svc.gemini.model = FakeGeminiModel(text="not json")
    assert as_client.post("/social", json={"image": tiny_image_b64()}).status_code == 201


def test_like_toggle_is_per_user(client, as_client, as_barber):
    assert client.post("/social/1/like").status_code == 401
    assert as_client.post("/social/1/like").get_json() == {"success": True, "liked": True, "likes": 24}
    # Another user liking does not toggle the first user's like off.
    assert as_barber.post("/social/1/like").get_json() == {"success": True, "liked": True, "likes": 25}
    assert as_client.post("/social/1/like").get_json() == {"success": True, "liked": False, "likes": 24}
    posts = {p["id"]: p for p in as_barber.get("/social").get_json()["posts"]}
    assert posts["1"]["liked"] is True and posts["1"]["likes"] == 24
    posts = {p["id"]: p for p in as_client.get("/social").get_json()["posts"]}
    assert posts["1"]["liked"] is False


def test_like_missing_post(as_client):
    response = as_client.post("/social/999/like")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Post not found"


def test_comments_get_and_post(client, as_client):
    comments = client.get("/social/1/comments").get_json()["comments"]
    assert len(comments) == 2 and comments[0]["username"] == "alex_taylor"

    assert client.post("/social/1/comments", json={"text": "x"}).status_code == 401
    response = as_client.post("/social/1/comments", json={"username": "spoofed", "text": "Clean."})
    assert response.status_code == 201
    comment = response.get_json()["comment"]
    assert comment["text"] == "Clean." and comment["timeAgo"] == "just now"
    assert comment["username"] == "Alex Johnson" and comment["uid"] == "client_1"
    assert len(client.get("/social/1/comments").get_json()["comments"]) == 3
    assert client.get("/social").get_json()["posts"][0]["comments"] == 3
    assert as_client.post("/social/1/comments", json={"text": "  "}).status_code == 400
    assert client.get("/social/unknown/comments").get_json() == {"comments": []}


def test_share(client, as_client):
    assert client.post("/social/2/share").status_code == 401
    assert as_client.post("/social/2/share").get_json() == {"success": True, "shares": 13}
    assert as_client.post("/social/nope/share").status_code == 404


def test_follow_and_unfollow(client, as_client, svc):
    assert client.post("/users/jason_cuts/follow").status_code == 401
    data = as_client.post("/users/jason_cuts/follow", json={"follower_id": "spoofed"}).get_json()
    assert data["success"] is True and data["following"] is True and data["followingCount"] == 3
    assert "jason_cuts" in svc.store.user_follows.get("client_1")["following"]
    assert svc.store.user_follows.get("spoofed") is None
    data = as_client.post("/users/jason_cuts/unfollow").get_json()
    assert data["following"] is False and data["followingCount"] == 2
    assert as_client.get("/users/me/following").get_json() == {"following": ["mike_style", "sarah_hair"]}


def test_concurrent_comments_are_not_lost(as_client, other_client, svc):
    """The comment list is appended atomically, so the count tracks the list."""
    post = as_client.post("/social", json={"caption": "fresh fade", "image": tiny_image_b64()}).get_json()["post"]
    post_id = post["id"]
    for i in range(3):
        assert as_client.post(f"/social/{post_id}/comments", json={"text": f"nice {i}"}).status_code == 201
    assert other_client.post(f"/social/{post_id}/comments", json={"text": "clean"}).status_code == 201
    stored = svc.store.post_comments.get(post_id)["comments"]
    assert len(stored) == 4
    assert svc.store.social_posts.get(post_id)["comments"] == 4
    listed = as_client.get(f"/social/{post_id}/comments").get_json()["comments"]
    assert [c["text"] for c in listed] == ["nice 0", "nice 1", "nice 2", "clean"]
