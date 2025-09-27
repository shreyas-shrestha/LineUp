import os
import io
import json
import base64
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Image processing libs
import cv2
import numpy as np
from PIL import Image

# Vertex client
from google.cloud.aiplatform.gapic import PredictionServiceClient

# ----- Config -----
PROJECT = os.getenv("VERTEX_PROJECT")            # e.g. "my-gcp-project"
LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")  # model location
ENDPOINT_ID = os.getenv("VERTEX_ENDPOINT_ID")   # deployed model endpoint id
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "*")  # e.g. https://lineupai.onrender.com

# Apply GOOGLE_APPLICATION_CREDENTIALS from env var if provided as JSON string
if os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
    creds_path = "/tmp/gcloud-creds.json"
    with open(creds_path, "w") as f:
        f.write(os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"))
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

# ----- App setup -----
app = Flask(__name__, static_folder="static", template_folder="templates")
# Lock upload size (5 MB)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
# CORS (restrict to your frontend in production)
CORS(app, resources={r"/*": {"origins": [FRONTEND_ORIGIN]}})

# Rate limiting to prevent abuse
limiter = Limiter(key_func=get_remote_address, app=app, default_limits=["200 per hour"])

DATA_DIR = "data"
SOCIAL_FILE = os.path.join(DATA_DIR, "social_posts.json")
os.makedirs(DATA_DIR, exist_ok=True)
if not os.path.exists(SOCIAL_FILE):
    with open(SOCIAL_FILE, "w") as f:
        json.dump([], f)

# Allowed image extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}


# ----- Utility functions -----
def allowed_filename(fname):
    return "." in fname and fname.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def read_image_bytes_from_base64(b64str):
    return base64.b64decode(b64str)

def pil_to_cv2(img: Image.Image):
    rgb = np.array(img)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


# ----- Local heuristics / fallback analyzer -----
def analyze_image_basic_cv(img_bgr):
    """
    Local best-effort analysis:
      - face detection (OpenCV Haar cascade)
      - hair texture/color heuristics (VERY basic)
      - produce recommendations list (map-based)
    This is fallback if Vertex isn't configured or the Vertex call fails.
    """
    try:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)

        if len(faces) == 0:
            return None, "No face detected in the image."

        # Use first face bounding box to crop for hair heuristics
        (x, y, w, h) = faces[0]
        h_pad = int(h * 0.6)
        y0 = max(0, y - h_pad)
        y1 = min(img_bgr.shape[0], y + h + int(h * 0.3))
        x0 = max(0, x - int(w * 0.3))
        x1 = min(img_bgr.shape[1], x + w + int(w * 0.3))
        crop = img_bgr[y0:y1, x0:x1]

        # Hair color heuristic: compute dominant color in crop (k-means or avg)
        crop_lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)
        avg_lab = crop_lab.reshape(-1, 3).mean(axis=0)
        L, A, B = avg_lab
        # Very rough mapping
        if L > 200:
            hair_color = "Blonde"
        elif A > 150:
            hair_color = "Red"
        elif L < 60:
            hair_color = "Black"
        else:
            hair_color = "Brown"

        # Hair texture heuristic: measure edge/curvature density
        gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray_crop, 50, 150)
        edge_density = edges.mean()  # 0..255

        if edge_density < 1.5:
            hair_texture = "Straight"
        elif edge_density < 8:
            hair_texture = "Wavy"
        else:
            hair_texture = "Curly"

        # Very naive face shape based on bbox ratio
        face_ratio = h / w if w > 0 else 1.0
        if face_ratio > 1.3:
            face_shape = "Long"
        elif face_ratio < 0.9:
            face_shape = "Round"
        elif w / img_bgr.shape[1] > 0.4:
            face_shape = "Square"
        else:
            face_shape = "Oval"

        analysis = {
            "faceShape": face_shape,
            "hairTexture": hair_texture,
            "hairColor": hair_color,
            "estimatedAge": "unknown",
            "estimatedGender": "unknown"
        }

        # Build recommendation pool (more than 15)
        recommendations_master = [
            {"styleName":"Classic Taper Fade","description":"Clean, short sides, tapered back.","suitable":["Straight","Wavy"]},
            {"styleName":"Textured Crop","description":"Short textured top with crop fringe.","suitable":["Straight","Wavy","Curly"]},
            {"styleName":"Modern Quiff","description":"Lifted front with volume.","suitable":["Straight","Wavy"]},
            {"styleName":"Pompadour","description":"Retro high-volume top.","suitable":["Straight","Wavy"]},
            {"styleName":"Buzz Cut","description":"Very short uniform cut.","suitable":["Straight","Wavy","Curly","Coily"]},
            {"styleName":"Crew Cut","description":"Short on sides with slightly longer top.","suitable":["Straight","Wavy"]},
            {"styleName":"Slick Back","description":"Long top slicked back.","suitable":["Straight"]},
            {"styleName":"Side Part","description":"Classic parted style.","suitable":["Straight","Wavy"]},
            {"styleName":"Messy Fringe","description":"Casual textured fringe.","suitable":["Wavy","Curly"]},
            {"styleName":"High and Tight","description":"Military-inspired short sides.","suitable":["Straight","Wavy","Curly"]},
            {"styleName":"Curly Top","description":"Short sides with curly top.","suitable":["Curly","Coily"]},
            {"styleName":"Long Layers","description":"Layered long hair for movement.","suitable":["Straight","Wavy","Curly"]},
            {"styleName":"Shag","description":"Tapered layers; natural movement.","suitable":["Wavy","Curly"]},
            {"styleName":"Mullet (Modern)","description":"Short front/long back modern mullet.","suitable":["Wavy","Straight"]},
            {"styleName":"Undercut","description":"Contrasting shaved sides with top volume.","suitable":["Straight","Wavy"]},
            {"styleName":"Curly Fade","description":"Fade sides and preserved curly top.","suitable":["Curly","Coily"]},
            {"styleName":"Layered Bob","description":"Classic bob with layers.","suitable":["Straight","Wavy"]},
            {"styleName":"Pompadour Fade","description":"Pompadour with faded sides.","suitable":["Straight","Wavy"]},
            {"styleName":"Man Bun","description":"Long hair tied back.","suitable":["Straight","Wavy","Curly"]},
            {"styleName":"Side Swept Bangs","description":"Longer fringe swept to the side.","suitable":["Straight","Wavy"]}
        ]

        # Filter recommendations by texture, then hair color heuristic (tint)
        filtered = [r for r in recommendations_master if analysis["hairTexture"] in r["suitable"]]
        # If too few, add more from master
        if len(filtered) < 8:
            filtered = recommendations_master

        # Add a reason tailored with hairColor and face shape
        selected = filtered[:20]  # top N
        for r in selected:
            r["reason"] = f"Good for {analysis['hairTexture'].lower()} hair and {analysis['faceShape'].lower()} faces. ({analysis['hairColor']})"

        return {"analysis": analysis, "recommendations": selected}, None

    except Exception as e:
        return None, f"Local analysis failed: {e}"


# ----- Vertex call -----
def analyze_with_vertex(image_bytes: bytes):
    """
    Send image bytes to Vertex AI prediction endpoint.
    Expects you deployed an image classification/vision model that accepts base64 in "content".
    The exact request format depends on your model signature — this example works for AutoML-style endpoints
    where instances are [{'content': '<base64string>'}]
    """
    if not PROJECT or not LOCATION or not ENDPOINT_ID:
        raise RuntimeError("Vertex endpoint not configured (VERTEX_PROJECT, VERTEX_LOCATION, VERTEX_ENDPOINT_ID).")

    client = PredictionServiceClient(client_options={"api_endpoint": f"{LOCATION}-aiplatform.googleapis.com"})

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    instances = [{"content": b64}]  # AutoML Vision-like instance format

    endpoint = f"projects/{PROJECT}/locations/{LOCATION}/endpoints/{ENDPOINT_ID}"
    response = client.predict(endpoint=endpoint, instances=instances)

    # Response.predictions content depends on your model. Commonly: [{'labels': [...], 'scores': [...]}]
    # We'll attempt to parse a common output; adjust according to your model
    preds = []
    for p in response.predictions:
        preds.append(dict(p))

    return preds


# ----- Routes -----
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
@limiter.limit("30/minute")
def analyze_route():
    """
    Accepts JSON payload from frontend. Expected structure (simplest):
    {
      "payload": [
        {
          "parts": [
             { "inlineData": { "mimeType": "image/jpeg", "data": "<base64-data>" } }
          ]
        }
      ]
    }
    Returns JSON with analysis + recommendations.
    """
    try:
        req = request.get_json(force=True)
        payload = req.get("payload") if isinstance(req, dict) else None
        if not payload or not isinstance(payload, list):
            return jsonify({"error": "Invalid payload"}), 400

        # Find inlineData
        parts = payload[0].get("parts", []) if payload else []
        inline = None
        for p in parts:
            if isinstance(p, dict) and "inlineData" in p:
                inline = p["inlineData"]
                break
        if not inline or "data" not in inline:
            return jsonify({"error": "No image inlineData found"}), 400

        b64data = inline["data"]
        image_bytes = read_image_bytes_from_base64(b64data)

        # First, quick local face detection to reject non-faces
        try:
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_cv = pil_to_cv2(pil_img)
        except Exception as e:
            return jsonify({"error": f"Could not decode image: {e}"}), 400

        # local quick face detect (Haar)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        if len(faces) == 0:
            return jsonify({"error": "No face detected in the image. Please upload a clear front-facing photo."}), 400

        # If Vertex is configured, call it; otherwise fallback to local analyzer
        try:
            if PROJECT and LOCATION and ENDPOINT_ID:
                preds = analyze_with_vertex(image_bytes)
                # NOTE: model must return structured JSON matching your label schema
                # We wrap preds in a consistent response for the frontend to consume.
                # If your Vertex model returns attributes such as hair_texture/hair_color/face_shape -> use them.
                # Otherwise, fall back to converting labels into attributes.
                # Here we attempt to parse an AutoML-like prediction
                parsed = {
                    "analysis": {},
                    "recommendations": []
                }
                # Example parse (adjust to your model outputs):
                first = preds[0] if preds else {}
                # Try to extract labels
                labels = first.get("displayNames") or first.get("labels") or first.get("classes") or first.get("labels", None)
                # If model returned structured attributes
                parsed["analysis"]["hairColor"] = first.get("hair_color") or first.get("hairColor") or "Unknown"
                parsed["analysis"]["hairTexture"] = first.get("hair_texture") or first.get("hairTexture") or "Unknown"
                parsed["analysis"]["faceShape"] = first.get("face_shape") or first.get("faceShape") or "Unknown"
                parsed["analysis"]["estimatedAge"] = first.get("age") or "unknown"
                parsed["analysis"]["estimatedGender"] = first.get("gender") or "unknown"

                # If your model provides recommended_styles, include them; otherwise fallback later.
                if "recommended_styles" in first:
                    parsed["recommendations"] = first["recommended_styles"]
                else:
                    # Fallback: run local recommender to get styles tailored
                    local_result, err = analyze_image_basic_cv(img_cv)
                    if local_result:
                        parsed = local_result
                return jsonify(parsed), 200

            else:
                # Vertex not configured -> fallback to local
                local_result, err = analyze_image_basic_cv(img_cv)
                if err:
                    return jsonify({"error": err}), 400
                return jsonify(local_result), 200

        except Exception as e:
            # On Vertex errors, fallback to local analyzer
            local_result, err = analyze_image_basic_cv(img_cv)
            if local_result:
                local_result["debug"] = {"vertex_error": str(e)}
                return jsonify(local_result), 200
            return jsonify({"error": f"Analysis failed: {e}"}), 500

    except Exception as e:
        return jsonify({"error": f"Server error: {e}"}), 500


# ----- Social endpoints -----
@app.route("/social", methods=["GET", "POST"])
@limiter.limit("60/minute")
def social_posts():
    if request.method == "GET":
        with open(SOCIAL_FILE, "r") as f:
            posts = json.load(f)
        return jsonify(posts)

    payload = request.get_json(force=True)
    image = payload.get("image")
    caption = payload.get("caption", "")

    if not image or not caption:
        return jsonify({"error": "Missing image or caption"}), 400

    with open(SOCIAL_FILE, "r") as f:
        posts = json.load(f)

    post = {
        "id": (posts[0]["id"] + 1) if posts else 1,
        "image": image,
        "caption": caption,
        "likes": 0,
        "timestamp": datetime.utcnow().isoformat()
    }

    posts.insert(0, post)
    with open(SOCIAL_FILE, "w") as f:
        json.dump(posts, f, indent=2)

    return jsonify(post), 201


@app.route("/social/like/<int:post_id>", methods=["POST"])
@limiter.limit("120/minute")
def like_post(post_id):
    with open(SOCIAL_FILE, "r") as f:
        posts = json.load(f)
    for p in posts:
        if p["id"] == post_id:
            p["likes"] += 1
            break
    with open(SOCIAL_FILE, "w") as f:
        json.dump(posts, f, indent=2)
    return jsonify({"success": True})


# Health check
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "vertex_configured": bool(PROJECT and LOCATION and ENDPOINT_ID)})


if __name__ == "__main__":
    # For local dev only. On Render, Gunicorn serves via Procfile.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
