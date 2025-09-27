# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import google.generativeai as genai
import json
import base64
from PIL import Image
import io

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# --- Gemini API Config ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

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
        contents = payload["contents"][0]["parts"]
        if len(contents) < 2:
            return jsonify({"error": "Image data missing"}), 400
            
        inlineData = contents[1].get("inlineData")
        if not inlineData or not inlineData.get("data"):
            return jsonify({"error": "Image data missing"}), 400

        image_base64 = inlineData["data"]
        
        # Convert base64 to PIL Image
        image_bytes = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_bytes))

        # --- Create prompt for Gemini ---
        prompt = """Analyze this person's face and hair in the photo and provide recommendations.
        
        Return ONLY a valid JSON object with this exact structure:
        {
            "analysis": {
                "faceShape": "oval/round/square/heart/oblong/diamond",
                "hairTexture": "straight/wavy/curly/coily",
                "hairColor": "black/brown/blonde/red/gray/other",
                "estimatedGender": "male/female/non-binary",
                "estimatedAge": "20-25/25-30/30-35/etc"
            },
            "recommendations": [
                {
                    "styleName": "Style Name",
                    "description": "Brief description of the haircut style",
                    "reason": "Why this style works for their face shape and features"
                },
                {
                    "styleName": "Another Style",
                    "description": "Brief description",
                    "reason": "Why it works"
                }
            ]
        }
        
        Provide exactly 5 recommendations. If the image doesn't show a clear human face, return:
        {"error": "No clear face detected in image"}
        
        Return ONLY the JSON, no other text."""

        # --- Call Gemini API ---
        response = model.generate_content([prompt, image])
        
        # Parse the response
        response_text = response.text.strip()
        
        # Clean up the response - remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        try:
            analysis_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {response_text}")
            return jsonify({"error": "Failed to parse AI response"}), 500

        # Check for error in response
        if "error" in analysis_data:
            return jsonify(analysis_data), 400

        # Ensure we have the expected structure
        if "analysis" not in analysis_data or "recommendations" not in analysis_data:
            return jsonify({"error": "Invalid response structure from AI"}), 500

        # Limit recommendations to 5
        analysis_data["recommendations"] = analysis_data["recommendations"][:5]

        return jsonify(analysis_data)

    except Exception as e:
        print(f"Error in /analyze: {str(e)}")
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


# --- Health Check ---
@app.route("/")
def index():
    return "Haircut AI backend running!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
