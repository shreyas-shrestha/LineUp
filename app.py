from flask import Flask, render_template, request, jsonify
import base64
import io
import cv2
import numpy as np
import mediapipe as mp
import joblib
from werkzeug.exceptions import BadRequest

app = Flask(__name__)

# ----------------- Database Placeholder -----------------
# In a real app, this would be a database connection.
db_posts = []
db_barbers = [
    {
        "name": "Atlanta Fade Masters",
        "specialties": ["Modern Fade", "Textured Crop"],
        "location": "Downtown Atlanta",
        "contact": "555-0101",
        "image": "https://i.ibb.co/C07Bf5t/barber-shop-1.jpg"
    },
    {
        "name": "Midtown Curls & Co.",
        "specialties": ["Curly", "Coily", "Classic Pompadour"],
        "location": "Midtown Atlanta",
        "contact": "555-0102",
        "image": "https://i.ibb.co/Vq7Yw7p/barber-shop-2.jpg"
    },
    {
        "name": "Buckhead Barbershop",
        "specialties": ["Clean Shaves", "Short Styles", "Wavy Hair"],
        "location": "Buckhead, Atlanta",
        "contact": "555-0103",
        "image": "https://i.ibb.co/n65Y0y3/barber-shop-3.jpg"
    }
]

# ----------------- AI Analyzer -----------------
class Analyzer:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils

    def analyze_image(self, image_data):
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Could not decode image. Please upload a valid image file.")

        # Face detection using MediaPipe
        with self.mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1) as face_mesh:
            results = face_mesh.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            if not results.multi_face_landmarks:
                return {"error": "No face detected in the image. Please upload a clear photo with a visible face."}

        # Placeholder for specific analysis
        face_shape = "Oval"  # This would be derived from landmark analysis
        hair_type = "Wavy" # This would be from a trained model
        hair_color = "Brown"

        # Generate dynamic recommendations based on analysis
        recommendations = []
        if face_shape == "Oval":
            recommendations.append({"style": "Modern Fade", "match": 95, "reason": "Excellent for Oval faces, accentuating your features."})
            recommendations.append({"style": "Classic Pompadour", "match": 88, "reason": "A timeless look that complements your face shape."})
        elif face_shape == "Square":
            recommendations.append({"style": "Textured Crop", "match": 92, "reason": "Softens the strong lines of a Square face."})

        if hair_type == "Wavy":
            recommendations.append({"style": "Wavy Undercut", "match": 90, "reason": "Embraces your natural texture for a stylish look."})
        elif hair_type == "Curly":
            recommendations.append({"style": "Curly Fade", "match": 94, "reason": "Keeps the sides clean while highlighting your natural curls."})

        return {
            "face_shape": face_shape,
            "hair_type": hair_type,
            "hair_color": hair_color,
            "recommendations": recommendations,
            "confidence": 92,
            "face_shape_confidence": 95,
            "hair_type_confidence": 88
        }

analyzer = Analyzer()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        image_data = request.json['image']
        image_data = image_data.split(',')[1]
        
        result = analyzer.analyze_image(image_data)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
        
    except BadRequest as e:
        return jsonify({"error": "Invalid JSON or missing 'image' field."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/feed')
def feed():
    return render_template('feed.html', posts=db_posts)

@app.route('/post', methods=['POST'])
def new_post():
    try:
        image_data = request.json['image']
        caption = request.json.get('caption', '')
        new_post = {
            "id": len(db_posts) + 1,
            "image": image_data,
            "caption": caption,
            "likes": 0,
            "user": "You"
        }
        db_posts.append(new_post)
        return jsonify({"success": True, "post": new_post})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/post/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    post = next((p for p in db_posts if p['id'] == post_id), None)
    if post:
        post['likes'] += 1
        return jsonify({"success": True, "likes": post['likes']})
    return jsonify({"error": "Post not found"}), 404

@app.route('/barbers')
def get_barbers():
    # In a real app, you would filter based on location and recommended style
    return jsonify({"barbers": db_barbers})

if __name__ == '__main__':
    app.run(debug=True)
