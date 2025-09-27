from flask import Flask, render_template, request, jsonify
import numpy as np
from PIL import Image
import base64
import io

app = Flask(__name__)

class SimpleAnalyzer:
    def analyze_image(self, image):
        try:
            # Convert to numpy array for basic analysis
            img_array = np.array(image)
            h, w = img_array.shape[:2]
            
            # Simple aspect ratio analysis
            aspect_ratio = w / h
            
            # Basic brightness analysis
            brightness = np.mean(img_array)
            
            # Determine face shape based on aspect ratio
            if aspect_ratio < 0.85:
                face_shape = "Oblong"
                confidence = 87
            elif aspect_ratio < 0.95:
                face_shape = "Oval" 
                confidence = 92
            else:
                face_shape = "Round"
                confidence = 89
            
            # Hair analysis based on brightness
            if brightness < 100:
                hair_color = "Dark Brown"
                hair_type = "Curly"
            elif brightness < 150:
                hair_color = "Brown"
                hair_type = "Wavy"
            else:
                hair_color = "Light Brown"
                hair_type = "Straight"
            
            recommendations = [
                {"style": "Modern Fade", "match": 90, "reason": f"Great for {face_shape} faces"},
                {"style": "Classic Cut", "match": 85, "reason": f"Works well with {hair_type} hair"},
                {"style": "Textured Style", "match": 88, "reason": "Trendy and versatile"}
            ]
            
            return {
                "face_shape": face_shape,
                "hair_type": hair_type, 
                "hair_color": hair_color,
                "recommendations": recommendations,
                "confidence": confidence,
                "face_shape_confidence": confidence,
                "hair_type_confidence": confidence - 5
            }
            
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}

analyzer = SimpleAnalyzer()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        image_data = request.json['image']
        image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        image = Image.open(io.BytesIO(image_bytes))
        result = analyzer.analyze_image(image)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
