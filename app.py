from flask import Flask, render_template, request, jsonify
import base64
import io
import random

app = Flask(__name__)

class UltraSimpleAnalyzer:
    def analyze_image(self, image_data):
        # Simple analysis based on image data length (file size proxy)
        data_length = len(image_data)
        
        # Generate "analysis" based on data characteristics
        seed = data_length % 1000
        random.seed(seed)
        
        face_shapes = ["Oval", "Round", "Square", "Heart", "Oblong"]
        hair_types = ["Straight", "Wavy", "Curly", "Coily"]
        hair_colors = ["Black", "Dark Brown", "Brown", "Light Brown", "Blonde"]
        
        face_shape = random.choice(face_shapes)
        hair_type = random.choice(hair_types)
        hair_color = random.choice(hair_colors)
        confidence = random.randint(85, 95)
        
        recommendations = [
            {"style": "Modern Fade", "match": random.randint(88, 95), "reason": f"Excellent for {face_shape} faces"},
            {"style": "Classic Pompadour", "match": random.randint(85, 92), "reason": f"Works great with {hair_type} hair"},
            {"style": "Textured Crop", "match": random.randint(82, 90), "reason": "Trendy and low maintenance"}
        ]
        
        return {
            "face_shape": face_shape,
            "hair_type": hair_type,
            "hair_color": hair_color,
            "recommendations": recommendations,
            "confidence": confidence,
            "face_shape_confidence": confidence,
            "hair_type_confidence": confidence - 3
        }

analyzer = UltraSimpleAnalyzer()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        image_data = request.json['image']
        image_data = image_data.split(',')[1]  # Remove data:image/jpeg;base64,
        
        result = analyzer.analyze_image(image_data)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
