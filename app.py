from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
from PIL import Image
import base64
import io
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import mediapipe as mp
import os

app = Flask(__name__)

class HairAnalyzer:
    def __init__(self):
        # Initialize MediaPipe Face Detection
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_drawing = mp.solutions.drawing_utils
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=0, min_detection_confidence=0.5)
        
        # Train simple ML models
        self.face_shape_model = self._train_face_shape_model()
        self.hair_type_model = self._train_hair_type_model()
        
    def _train_face_shape_model(self):
        """Train a simple face shape classifier"""
        # Generate synthetic training data for face shape classification
        # In production, this would be real labeled data
        np.random.seed(42)
        
        # Features: [face_width_ratio, face_height_ratio, jaw_width_ratio, forehead_width_ratio]
        # Labels: 0=oval, 1=round, 2=square, 3=heart, 4=oblong
        
        # Oval faces (balanced proportions)
        oval_data = np.random.normal([0.85, 1.2, 0.8, 0.85], [0.05, 0.1, 0.05, 0.05], (100, 4))
        oval_labels = np.zeros(100)
        
        # Round faces (wider, shorter)
        round_data = np.random.normal([0.95, 1.0, 0.9, 0.9], [0.05, 0.08, 0.05, 0.05], (100, 4))
        round_labels = np.ones(100)
        
        # Square faces (angular, similar width/height)
        square_data = np.random.normal([0.9, 1.1, 0.9, 0.85], [0.05, 0.08, 0.05, 0.05], (100, 4))
        square_labels = np.full(100, 2)
        
        # Heart faces (wide forehead, narrow jaw)
        heart_data = np.random.normal([0.8, 1.15, 0.7, 0.95], [0.05, 0.08, 0.05, 0.05], (100, 4))
        heart_labels = np.full(100, 3)
        
        # Oblong faces (narrow, long)
        oblong_data = np.random.normal([0.75, 1.4, 0.75, 0.8], [0.05, 0.1, 0.05, 0.05], (100, 4))
        oblong_labels = np.full(100, 4)
        
        # Combine all data
        X = np.vstack([oval_data, round_data, square_data, heart_data, oblong_data])
        y = np.hstack([oval_labels, round_labels, square_labels, heart_labels, oblong_labels])
        
        # Train model
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        return model
    
    def _train_hair_type_model(self):
        """Train a simple hair type classifier"""
        np.random.seed(42)
        
        # Features: [texture_variance, curl_factor, thickness_metric, color_uniformity]
        # Labels: 0=straight, 1=wavy, 2=curly, 3=coily
        
        straight_data = np.random.normal([0.2, 0.1, 0.6, 0.8], [0.1, 0.05, 0.1, 0.1], (100, 4))
        straight_labels = np.zeros(100)
        
        wavy_data = np.random.normal([0.4, 0.3, 0.7, 0.7], [0.1, 0.1, 0.1, 0.1], (100, 4))
        wavy_labels = np.ones(100)
        
        curly_data = np.random.normal([0.6, 0.6, 0.8, 0.6], [0.1, 0.1, 0.1, 0.1], (100, 4))
        curly_labels = np.full(100, 2)
        
        coily_data = np.random.normal([0.8, 0.8, 0.9, 0.5], [0.1, 0.1, 0.1, 0.1], (100, 4))
        coily_labels = np.full(100, 3)
        
        X = np.vstack([straight_data, wavy_data, curly_data, coily_data])
        y = np.hstack([straight_labels, wavy_labels, curly_labels, coily_labels])
        
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        return model
    
    def extract_face_features(self, image):
        """Extract facial features using MediaPipe"""
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.face_detection.process(image_rgb)
        
        if not results.detections:
            return None
            
        detection = results.detections[0]
        bbox = detection.location_data.relative_bounding_box
        
        # Calculate face proportions
        face_width = bbox.width
        face_height = bbox.height
        face_ratio = face_width / face_height if face_height > 0 else 1
        
        # Extract more features from the bounding box
        # These are simplified - in production you'd use more sophisticated landmark detection
        features = [
            face_ratio,  # width to height ratio
            face_height,  # relative face height
            face_width * 0.8,  # estimated jaw width
            face_width * 0.9   # estimated forehead width
        ]
        
        return np.array(features).reshape(1, -1)
    
    def extract_hair_features(self, image, face_bbox=None):
        """Extract hair texture features"""
        # Convert to grayscale for texture analysis
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Focus on hair region (upper portion of image)
        h, w = gray.shape
        hair_region = gray[:h//3, :]  # Top third of image
        
        # Calculate texture features
        # Variance (measure of texture)
        texture_variance = np.var(hair_region) / 10000  # Normalize
        
        # Edge density (measure of curl/wave)
        edges = cv2.Canny(hair_region, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        # Local binary pattern for thickness
        thickness_metric = np.std(hair_region) / 100  # Simplified thickness measure
        
        # Color uniformity
        color_std = np.std(hair_region) / 100
        color_uniformity = 1 / (1 + color_std)  # Inverse of standard deviation
        
        features = [
            min(texture_variance, 1.0),
            min(edge_density, 1.0), 
            min(thickness_metric, 1.0),
            min(color_uniformity, 1.0)
        ]
        
        return np.array(features).reshape(1, -1)
    
    def get_hair_color(self, image):
        """Determine dominant hair color"""
        # Focus on hair region
        h, w = image.shape[:2]
        hair_region = image[:h//3, :]
        
        # Calculate average color
        avg_color = np.mean(hair_region.reshape(-1, 3), axis=0)
        b, g, r = avg_color
        
        # Simple color classification
        brightness = (r + g + b) / 3
        
        if brightness < 50:
            return "Black"
        elif brightness < 80:
            return "Dark Brown"
        elif brightness < 120:
            return "Brown"
        elif brightness < 160:
            return "Light Brown"
        elif r > g and r > b and r > 140:
            return "Auburn/Red"
        else:
            return "Blonde"
    
    def analyze_image(self, image):
        """Main analysis function"""
        # Extract features
        face_features = self.extract_face_features(image)
        
        if face_features is None:
            return {
                "error": "No face detected in image",
                "confidence": 0
            }
        
        hair_features = self.extract_hair_features(image)
        hair_color = self.get_hair_color(image)
        
        # Predict face shape
        face_shape_pred = self.face_shape_model.predict(face_features)[0]
        face_shape_prob = self.face_shape_model.predict_proba(face_features)[0]
        face_shapes = ["Oval", "Round", "Square", "Heart", "Oblong"]
        face_shape = face_shapes[int(face_shape_pred)]
        
        # Predict hair type
        hair_type_pred = self.hair_type_model.predict(hair_features)[0]
        hair_type_prob = self.hair_type_model.predict_proba(hair_features)[0]
        hair_types = ["Straight", "Wavy", "Curly", "Coily"]
        hair_type = hair_types[int(hair_type_pred)]
        
        # Generate recommendations
        recommendations = self.get_recommendations(face_shape, hair_type, hair_color)
        
        # Calculate confidence
        confidence = int((np.max(face_shape_prob) + np.max(hair_type_prob)) / 2 * 100)
        
        return {
            "face_shape": face_shape,
            "hair_type": hair_type,
            "hair_color": hair_color,
            "recommendations": recommendations,
            "confidence": confidence,
            "face_shape_confidence": int(np.max(face_shape_prob) * 100),
            "hair_type_confidence": int(np.max(hair_type_prob) * 100)
        }
    
    def get_recommendations(self, face_shape, hair_type, hair_color):
        """Get haircut recommendations based on analysis"""
        recommendations_db = {
            ("Oval", "Straight"): [
                {"style": "Classic Pompadour", "match": 95, "reason": "Perfect for oval faces with straight hair"},
                {"style": "Side Part", "match": 90, "reason": "Professional and versatile"},
                {"style": "Textured Crop", "match": 85, "reason": "Modern and easy to style"}
            ],
            ("Oval", "Wavy"): [
                {"style": "Textured Quiff", "match": 92, "reason": "Natural waves add texture"},
                {"style": "Surfer Cut", "match": 88, "reason": "Enhances natural wave pattern"},
                {"style": "Medium Length Layers", "match": 85, "reason": "Works with natural texture"}
            ],
            ("Round", "Straight"): [
                {"style": "High Fade", "match": 90, "reason": "Creates height and angles"},
                {"style": "Undercut", "match": 87, "reason": "Adds definition to round features"},
                {"style": "Angular Fringe", "match": 83, "reason": "Sharp lines complement face shape"}
            ],
            ("Round", "Curly"): [
                {"style": "High Top Fade", "match": 88, "reason": "Volume on top elongates face"},
                {"style": "Curly Undercut", "match": 85, "reason": "Controlled sides, natural top"},
                {"style": "Textured Crop", "match": 82, "reason": "Manages curl while adding height"}
            ],
            ("Square", "Straight"): [
                {"style": "Soft Layers", "match": 89, "reason": "Softens angular jawline"},
                {"style": "Long Fringe", "match": 86, "reason": "Balances strong jaw"},
                {"style": "Wavy Texture", "match": 83, "reason": "Adds movement to straight hair"}
            ]
        }
        
        # Get specific recommendations or fall back to general ones
        key = (face_shape, hair_type)
        if key in recommendations_db:
            return recommendations_db[key]
        else:
            # Default recommendations based on face shape
            defaults = {
                "Oval": [
                    {"style": "Versatile Cut", "match": 85, "reason": "Oval faces suit most styles"},
                    {"style": "Classic Style", "match": 80, "reason": "Timeless choice for oval faces"}
                ],
                "Round": [
                    {"style": "High Volume Cut", "match": 83, "reason": "Adds height to round faces"},
                    {"style": "Angular Style", "match": 79, "reason": "Creates definition"}
                ],
                "Square": [
                    {"style": "Soft Texture", "match": 81, "reason": "Softens angular features"},
                    {"style": "Layered Cut", "match": 77, "reason": "Adds movement"}
                ],
                "Heart": [
                    {"style": "Fuller Bottom", "match": 82, "reason": "Balances narrow chin"},
                    {"style": "Side Swept", "match": 78, "reason": "Softens wide forehead"}
                ],
                "Oblong": [
                    {"style": "Width-Adding Cut", "match": 80, "reason": "Adds width to long faces"},
                    {"style": "Horizontal Layers", "match": 76, "reason": "Creates width illusion"}
                ]
            }
            return defaults.get(face_shape, defaults["Oval"])

# Initialize analyzer
analyzer = HairAnalyzer()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Get image data from request
        image_data = request.json['image']
        
        # Decode base64 image
        image_data = image_data.split(',')[1]  # Remove data:image/jpeg;base64,
        image_bytes = base64.b64decode(image_data)
        
        # Convert to OpenCV format
        image = Image.open(io.BytesIO(image_bytes))
        image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Analyze image
        result = analyzer.analyze_image(image_cv)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
