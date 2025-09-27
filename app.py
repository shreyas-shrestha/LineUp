import random
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from PIL import Image
import cv2
import io
import os

app = Flask(__name__)
CORS(app)

def analyze_image_basic(img_array):
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    if face_cascade.empty():
        return None, "Failed to load face detection model"
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    if len(faces) == 0:
        return None, "No face detected"

    height, width = img_array.shape[:2]
    brightness = np.mean(gray)
    face_width_ratio = faces[0][2] / width if len(faces) > 0 else 0.3

    face_w, face_h = faces[0][2], faces[0][3]
    face_ratio = face_h / face_w
    if face_ratio > 1.3:
        face_shape = "Long"
    elif face_ratio < 0.9:
        face_shape = "Round"
    elif face_width_ratio > 0.4:
        face_shape = "Square"
    else:
        face_shape = "Oval"

    image_hash = hash(str(img_array.flatten()[:100].tolist())) % 1000
    ages = [20,22,25,28,30,32,35,38,40,42]
    genders = ["Male","Female"]
    hair_textures = ["Straight","Wavy","Curly","Coily"]

    return {
        "face_shape": face_shape,
        "estimated_age": ages[image_hash % len(ages)],
        "gender": genders[image_hash % len(genders)],
        "hair_texture": hair_textures[image_hash % len(hair_textures)],
        "faces_detected": len(faces),
        "image_brightness": round(brightness,1)
    }, None

@app.route('/analyze', methods=['POST'])
def analyze_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    try:
        file_bytes = file.read()
        img_array = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            img = np.array(Image.open(io.BytesIO(file_bytes)).convert("RGB"))
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    except:
        return jsonify({'error': 'Could not process the image'}), 400

    analysis_result, error = analyze_image_basic(img)
    if error:
        return jsonify({'error': error}), 400

    recommendations = [
        {"name":"Classic Taper Fade","reason":"Timeless cut."},
        {"name":"Textured Crop Top","reason":"Modern style."},
        {"name":"Side Part","reason":"Classic style."},
        {"name":"Crew Cut","reason":"Low maintenance."}
    ]

    response_data = {
        "analysis": {
            "faceShape": analysis_result["face_shape"],
            "hairTexture": analysis_result["hair_texture"],
            "estimatedAge": analysis_result["estimated_age"],
            "gender": analysis_result["gender"]
        },
        "recommendations": recommendations,
        "debug": {
            "facesDetected": analysis_result["faces_detected"],
            "imageBrightness": analysis_result["image_brightness"]
        }
    }
    return jsonify(response_data)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/health')
def health():
    return jsonify({'status':'healthy', 'opencv_available':True})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))  # Render provides PORT
    app.run(host='0.0.0.0', port=port)
