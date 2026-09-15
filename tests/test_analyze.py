import base64
import json
from io import BytesIO

from PIL import Image

from tests.helpers import GEMINI_ANALYSIS, FakeGeminiModel, FakeResponse, analyze_payload, tiny_image_b64, tiny_image_bytes


def test_analyze_requires_sign_in(client):
    response = client.post("/analyze", json=analyze_payload())
    assert response.status_code == 401
    assert response.get_json()["error"] == "Sign in to continue"


def test_analyze_returns_mock_without_gemini(as_client):
    response = as_client.post("/analyze", json=analyze_payload())
    assert response.status_code == 200
    data = response.get_json()
    assert data["mock"] is True
    assert data["reason"] == "gemini_not_configured"
    assert set(data["analysis"]) == {"faceShape", "hairTexture", "hairColor", "estimatedGender", "estimatedAge"}
    assert len(data["recommendations"]) == 6
    assert {"styleName", "description", "reason"} <= set(data["recommendations"][0])
    # Charged locally (LINEUP_METER_MOCK defaults to true outside production) so the credit flow is demoable.
    assert data["billing"]["charged"] == 1 and data["billing"]["credits"] == 2


def test_analyze_accepts_plain_image_field(as_client):
    response = as_client.post("/analyze", json={"image": tiny_image_b64("JPEG")})
    assert response.status_code == 200
    assert response.get_json()["mock"] is True


def test_analyze_rejects_non_json_body(as_client):
    response = as_client.post("/analyze", data="not json", content_type="text/plain")
    assert response.status_code == 400
    assert "JSON" in response.get_json()["error"]


def test_analyze_rejects_missing_image(as_client):
    response = as_client.post("/analyze", json={"payload": {"contents": [{"parts": [{"text": "hi"}]}]}})
    assert response.status_code == 400
    assert response.get_json()["error"] == "No image data provided"


def test_analyze_rejects_invalid_base64_and_non_image(as_client, svc):
    response = as_client.post("/analyze", json={"image": "@@not-base64@@"})
    assert response.status_code == 400
    assert "base64" in response.get_json()["error"]
    response = as_client.post("/analyze", json={"image": base64.b64encode(b"hello world").decode()})
    assert response.status_code == 400
    assert "not a valid image" in response.get_json()["error"]
    # Validation failures are refunded.
    assert svc.ledger.balance(as_client.uid) == 3


def test_analyze_uses_gemini_when_available(as_client, svc):
    model = FakeGeminiModel(text="```json\n" + json.dumps(GEMINI_ANALYSIS) + "\n```")
    svc.gemini.model = model
    response = as_client.post("/analyze", json=analyze_payload())
    assert response.status_code == 200
    data = response.get_json()
    assert data["mock"] is False
    assert data["source"] == "gemini"
    assert data["analysis"]["faceShape"] == "square"
    assert data["recommendations"][0]["styleName"] == "Textured Crop"
    assert len(model.calls) == 1
    assert svc.gemini_quota.used == 1
    assert data["billing"] == {"action": "analysis", "charged": 1, "credits": 2, "event_id": data["billing"]["event_id"]}


def test_analyze_falls_back_when_gemini_fails(as_client, svc):
    svc.gemini.model = FakeGeminiModel(error=RuntimeError("upstream down"))
    data = as_client.post("/analyze", json=analyze_payload()).get_json()
    assert data["mock"] is True and data["reason"] == "gemini_error"


def test_analyze_falls_back_when_gemini_returns_garbage(as_client, svc):
    svc.gemini.model = FakeGeminiModel(text="I cannot help with that")
    data = as_client.post("/analyze", json=analyze_payload()).get_json()
    assert data["mock"] is True and data["reason"] == "gemini_error"


def test_analyze_falls_back_when_daily_quota_spent(as_client, svc):
    svc.gemini.model = FakeGeminiModel(text=json.dumps(GEMINI_ANALYSIS))
    svc.gemini_quota.used = svc.gemini_quota.limit
    data = as_client.post("/analyze", json=analyze_payload()).get_json()
    assert data["mock"] is True and data["reason"] == "daily_quota_reached"


def test_tryon_requires_sign_in(client):
    assert client.post("/virtual-tryon", json={"userPhoto": tiny_image_b64(), "styleDescription": "x"}).status_code == 401


def test_tryon_preview_mode(as_client):
    response = as_client.post("/virtual-tryon", json={"userPhoto": tiny_image_b64(), "styleDescription": "Modern Fade"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["mode"] == "preview" and data["mock"] is True and data["reason"] == "replicate_not_configured"
    assert data["haircut"] == "Mohawk Fade" and data["haircutMatchedBy"] == "keyword"
    assert data["originalImage"] == tiny_image_b64()
    result = Image.open(BytesIO(base64.b64decode(data["resultImage"])))
    assert result.format == "JPEG"
    assert data["billing"]["charged"] == 3 and data["billing"]["credits"] == 0


def test_tryon_uses_replicate_when_available(as_client, svc):
    svc.tryon._run = lambda ref, input: ["https://cdn.example/result.png"]
    svc.tryon._http_get = lambda url, **kw: FakeResponse(status=200, content=tiny_image_bytes("PNG", (64, 64)))
    data = as_client.post("/virtual-tryon", json={"userPhoto": "data:image/png;base64," + tiny_image_b64(), "styleDescription": "buzz cut"}).get_json()
    assert data["mode"] == "replicate" and data["mock"] is False
    assert data["haircut"] == "Crew Cut"
    assert base64.b64decode(data["resultImage"]) == tiny_image_bytes("PNG", (64, 64))


def test_tryon_falls_back_to_preview_on_replicate_error(as_client, svc):
    def failing_run(ref, input):
        raise RuntimeError("model busy")

    svc.tryon._run = failing_run
    data = as_client.post("/virtual-tryon", json={"userPhoto": tiny_image_b64(), "styleDescription": "bob"}).get_json()
    assert data["success"] is True and data["mode"] == "preview" and data["reason"] == "replicate_error"
    # Provider failure: the 3 credits come back.
    assert data["billing"]["charged"] == 0 and data["billing"]["refunded"] == "provider_error" and data["billing"]["credits"] == 3


def test_tryon_validation(as_client, svc):
    assert as_client.post("/virtual-tryon", json={"styleDescription": "x"}).get_json()["error"] == "User photo required"
    assert as_client.post("/virtual-tryon", json={"userPhoto": tiny_image_b64()}).get_json()["error"] == "Style description required"
    response = as_client.post("/virtual-tryon", json={"userPhoto": "zzz", "styleDescription": "x"})
    assert response.status_code == 400
    assert svc.ledger.balance(as_client.uid) == 3


def test_ai_insights_is_public(client):
    data = client.get("/ai-insights?styles=Modern%20Fade,Quiff").get_json()
    assert data["trending_styles"][:2] == ["textured crop", "modern fade"]
    assert data["trending_hashtags"] == ["#fade"]  # only tag shared by both seeded posts
    assert len(data["personalized_recommendations"]) == 3
    assert "Modern Fade" in data["personalized_recommendations"][0]
    assert client.get("/ai-insights").get_json()["personalized_recommendations"] == []


def test_installed_gemini_sdk_accepts_the_timeout_we_pass():
    """Regression: google-generativeai < 0.4 rejected ``request_options`` with a
    ValueError that the service swallowed, so every real call silently failed."""
    import inspect

    from google.generativeai.generative_models import GenerativeModel

    assert "request_options" in inspect.signature(GenerativeModel.generate_content).parameters
