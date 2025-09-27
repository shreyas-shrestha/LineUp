from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")  # Set this in Render or local env
GEMINI_ENDPOINT = "https://api.gemini.com/v1/analyze"  # Replace with actual Gemini API URL

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.json
        base64_image = data.get("payload", {}).get("contents", [{}])[0].get("parts", [{}])[1].get("inlineData", {}).get("data")
        if not base64_image:
            return jsonify({"error": "No image provided"}), 400

        # Gemini request payload
        gemini_payload = {
            "model": "gemini-2.5-pro",
            "instructions": (
                "Analyze this image. Detect if it contains a human face. "
                "If yes, identify hair texture, hair color, face shape, gender, and approximate age. "
                "Provide the top 3 haircut recommendations personalized for this person. "
                "If it's not a face, return an error message."
            ),
            "input_image_base64": base64_image
        }

        headers = {"Authorization": f"Bearer {GEMINI_API_KEY}"}
        response = requests.post(GEMINI_ENDPOINT, json=gemini_payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()

        # The frontend expects:
        # {
        #   "analysis": {faceShape, hairTexture, hairColor, estimatedGender, estimatedAge},
        #   "recommendations": [{styleName, description, reason}, ...]
        # }
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
