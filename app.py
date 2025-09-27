from flask import Flask, request, jsonify
import requests
import os
import base64

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")  # Put your key in environment variables

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.json
        base64_image = data.get("image")
        if not base64_image:
            return jsonify({"error": "No image provided"}), 400

        # Prepare Gemini request
        payload = {
            "model": "gemini-2.5-pro",
            "instructions": "Analyze the person's face and hair. Validate if it's a face. Recommend 3 haircuts based on hair texture, color, and face shape.",
            "input_image_base64": base64_image
        }

        headers = {"Authorization": f"Bearer {GEMINI_API_KEY}"}

        # Replace with Gemini endpoint URL
        GEMINI_ENDPOINT = "https://api.gemini.example.com/v1/analyze"  # placeholder
        response = requests.post(GEMINI_ENDPOINT, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

