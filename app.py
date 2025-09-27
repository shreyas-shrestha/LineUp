# app.py
from flask import Flask, request, jsonify
import base64
import os
import requests

app = Flask(__name__)

# --- Gemini API Config ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_ENDPOINT = "https://api.generative.ai/v1beta2/models/gemini-2.5-pro:generateMessage"

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

# --- Mock function for barbers (optional, frontend uses mock data) ---
def mock_barbers():
    return [
        {"id": 1, "name": "Cuts by Clay", "specialties": ["Fade", "Taper"], "rating": 4.9, "avgCost": 45, "location": "Midtown"},
        {"id": 2, "name": "The Buckhead Barber", "specialties": ["Pompadour", "Buzz Cut"], "rating": 4.8, "avgCost": 55, "location": "Buckhead"},
        {"id": 3, "name": "Virginia-Highland Shears", "specialties": ["Shag", "Bob"], "rating": 4.9, "avgCost": 75, "location": "Virginia-Highland"},
    ]

# --- Route ---
@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json()
        if not data or "payload" not in data:
            return jsonify({"error": "Invalid request"}), 400

        payload = data["payload"]
        if not payload or not payload.get("contents"):
            return jsonify({"error": "No image provided"}), 400

        # --- Extract image data ---
        inlineData = payload["contents"][0]["parts"][1].get("inlineData")
        if not inlineData or not inlineData.get("data"):
            return jsonify({"error": "Image data missing"}), 400

        image_base64 = inlineData["data"]

        # --- Call Gemini API ---
        headers = {
            "Authorization": f"Bearer {GEMINI_API_KEY}",
            "Content-Type": "application/json"
        }

        prompt = (
            "Analyze this person in the photo and return the following fields in JSON: "
            "faceShape, hairTexture, hairColor, estimatedGender, estimatedAge, "
            "recommendations (array of up to 5 objects with styleName, description, reason). "
            "If the image is not a human face, return an error field."
        )

        gemini_payload = {
            "messages": [
                {"author": "user", "content": [{"type": "text", "text": prompt}, {"type": "image", "imageData": image_base64}]}
            ]
        }

        response = requests.post(GEMINI_ENDPOINT, headers=headers, json=gemini_payload, timeout=60)
        response.raise_for_status()
        gemini_result = response.json()

        # --- Parse Gemini result ---
        # Expecting JSON output inside 'content' field
        content_text = gemini_result.get("candidates", [{}])[0].get("content", "")
        if isinstance(content_text, list):
            content_text = content_text[0].get("text", "{}")
        try:
            analysis_data = eval(content_text) if isinstance(content_text, str) else content_text
        except Exception:
            return jsonify({"error": "Gemini returned invalid JSON"}), 500

        # Limit recommendations to 5
        if "recommendations" in analysis_data:
            analysis_data["recommendations"] = analysis_data["recommendations"][:5]

        return jsonify(analysis_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- Health Check ---
@app.route("/")
def index():
    return "Haircut AI backend running!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
