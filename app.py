import os
import io
import cv2
import numpy as np
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables (Render will handle these)
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://lineupai.onrender.com"]}})

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# --- Helper: Face detection with OpenCV ---
def detect_face(img_array):
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    return faces

# --- API route ---
@app.route("/analyze", methods=["POST"])
def analyze_image():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    file_bytes = file.read()

    # Decode with OpenCV
    img_array = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if img is None:
        return jsonify({"error": "Invalid image file"}), 400

    faces = detect_face(img)
    if len(faces) == 0:
        return jsonify({"error": "No face detected. Please upload a clear face photo."}), 400

    # --- Prompt Gemini ---
    prompt = """
    You are a professional hairstylist assistant.
    Analyze this face image and return JSON only with the following structure:
    {
      "hairTexture": "...",
      "hairColor": "...",
      "faceShape": "...",
      "recommendations": [
        {"name": "...", "reason": "..."},
        {"name": "...", "reason": "..."},
        {"name": "...", "reason": "..."}
      ]
    }

    The recommendations should be the **top 3 haircuts** suited for this person.
    """

    model = genai.GenerativeModel("gemini-2.5-pro")
    response = model.generate_content(
        [prompt, {"mime_type": "image/jpeg", "data": file_bytes}]
    )

    # Send structured JSON back to frontend
    try:
        import json
        analysis = json.loads(response.text)
        return jsonify(analysis)
    except Exception:
        return jsonify({"error": "AI response could not be parsed."}), 500

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
