from flask import Flask, render_template, request, jsonify
import base64
import io
import cv2
import numpy as np
import mediapipe as mp
import joblib  # For loading a pre-trained model

# ----------------- Database Placeholder -----------------
# In a real application, you would connect to a database like PostgreSQL or MongoDB.
# This is a simple in-memory list to simulate a database for posts and barbers.
db_posts = []
db_barbers = [
    {
        "name": "The Modern Man Barbershop",
        "specialties": ["Modern Fade", "Textured Crop"],
        "location": "123 Main St, Anytown",
        "contact": "555-1234"
    },
    {
        "name": "Classic Cuts",
        "specialties": ["Classic Pompadour"],
        "location": "456 Elm St, Anytown",
        "contact": "555-5678"
    }
]

# ----------------- AI Analyzer -----------------
class Analyzer:
    def __init__(self):
        # Placeholder for pre-trained models.
        # You would need to train and save these models yourself.
        # e.g., self.hair_type_model = joblib.load('hair_type_model.pkl')
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils

    def analyze_image(self, image_data):
        # Decode the base64 image data
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Could not decode image.")

        # Face Shape Analysis with MediaPipe
        face_shape = "Unknown"
        with self.mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1) as face_mesh:
            results = face_mesh.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            if results.multi_face_landmarks:
                # Placeholder for logic to determine face shape from landmarks
                # This would involve calculating distances between key points.
                face_shape = "Oval"  # Example placeholder

        # Hair Type Analysis (conceptual)
        hair_type = "Wavy" # Example placeholder
        # In a real app, you would use your trained Random Forest model here:
        # hair_type = self.hair_type_model.predict(features)[0]

        # Hair Color Analysis (conceptual)
        hair_color = "Brown"  # Example placeholder

        # Placeholder for haircut recommendations
        recommendations = [
            {"style": "Modern Fade", "match": 90, "reason": f"Excellent for {face_shape} faces."},
            {"style": "Classic Pompadour", "match": 85, "reason": f"Works great with {hair_type} hair."},
            {"style": "Textured Crop", "match": 82, "reason": "Trendy and low maintenance."}
        ]

        return {
            "face_shape": face_shape,
            "hair_type": hair_type,
            "hair_color": hair_color,
            "recommendations": recommendations,
            "confidence": 92,
            "face_shape_confidence": 95,
            "hair_type_confidence": 88
        }

# ----------------- Flask App -----------------
app = Flask(__name__)
analyzer = Analyzer()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        image_data = request.json['image']
        image_data = image_data.split(',')[1]  # Remove data URI prefix
        
        result = analyzer.analyze_image(image_data)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------- New Social Endpoints -----------------
@app.route('/feed')
def feed():
    return render_template('feed.html', posts=db_posts)

@app.route('/post', methods=['POST'])
def new_post():
    try:
        image_data = request.json['image']
        caption = request.json.get('caption', '')
        # In a real app, save image to storage and store post info in a database
        new_post = {
            "id": len(db_posts) + 1,
            "image": image_data, # For this example, we keep base64
            "caption": caption,
            "likes": 0,
            "user": "You" # Placeholder for logged-in user
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

# ----------------- New Barber Endpoint -----------------
@app.route('/barbers')
def get_barbers():
    # In a real app, you'd filter barbers based on location and recommendations
    return jsonify({"barbers": db_barbers})

if __name__ == '__main__':
    app.run(debug=True)
