# backend/app.py
from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Gemini 2.5 Pro API key (store securely in environment variable)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")  # do NOT hardcode

GEMINI_API_URL = "https://api.openai.com/v1/responses"  # Gemini endpoint

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        # Ensure payload exists
        data = request.json
        if not data or "payload" not in data:
            return jsonify({"error": "No payload provided"}), 400

        payload = data["payload"]

        # Call Gemini API
        headers = {
            "Authorization": f"Bearer {GEMINI_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(GEMINI_API_URL, json=payload, headers=headers, timeout=60)

        # Raise for HTTP errors
        response.raise_for_status()

        # Gemini may return JSON or text inside JSON
        try:
            result = response.json()
        except ValueError:
            # fallback if response is not JSON
            return jsonify({"error": "Invalid response from Gemini API"}), 500

        # You can also parse Gemini's candidates if needed:
        # example: return JSON inside first candidate part
        try:
            text_content = result.get("candidates", [])[0]["content"]["parts"][0]["text"]
            return jsonify(eval(text_content))  # Be careful: ideally JSON parse, not eval
        except Exception:
            # fallback: return raw Gemini JSON
            return jsonify(result)

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"API request failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "LineUp backend running"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
