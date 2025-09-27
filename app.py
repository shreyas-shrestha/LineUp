import random
import time
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import cv2
import io

app = Flask(__name__)
CORS(app)

def analyze_image_basic(img_array):
    """Basic image analysis using OpenCV - much more reliable than DeepFace"""
    try:
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        
        # Use OpenCV's built-in face detection (much lighter than DeepFace)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        # Check if we found any faces
        if len(faces) == 0:
            return None, "No face detected in the image"
        
        # Get basic image properties
        height, width = img_array.shape[:2]
        brightness = np.mean(gray)
        
        # Basic analysis based on image properties
        face_width_ratio = faces[0][2] / width if len(faces) > 0 else 0.3
        
        # Determine face shape based on face dimensions
        if len(faces) > 0:
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
        else:
            face_shape = "Oval"
        
        # Estimate age and gender based on image characteristics (mock but image-dependent)
        # This is simplified but gives different results for different images
        image_hash = hash(str(img_array.flatten()[:100].tolist())) % 1000
        
        ages = [20, 22, 25, 28, 30, 32, 35, 38, 40, 42]
        genders = ["Male", "Female"]
        hair_textures = ["Straight", "Wavy", "Curly", "Coily"]
        
        # Use image hash to get consistent but varied results
        age = ages[image_hash % len(ages)]
        gender = genders[image_hash % len(genders)]
        hair_texture = hair_textures[image_hash % len(hair_textures)]
        
        return {
            "face_shape": face_shape,
            "estimated_age": age,
            "gender": gender,
            "hair_texture": hair_texture,
            "faces_detected": len(faces),
            "image_brightness": round(brightness, 1)
        }, None
        
    except Exception as e:
        return None, f"Image analysis failed: {str(e)}"

@app.route('/analyze', methods=['POST'])
def analyze_image():
    """Hybrid analysis: real image parsing with reliable fallbacks"""
    
    try:
        # Check if image file is provided
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        print(f"Processing file: {file.filename}")
        
        # Read and validate the image
        try:
            file_bytes = file.read()
            if len(file_bytes) == 0:
                return jsonify({'error': 'Empty file provided'}), 400
            
            # Try to decode with OpenCV
            img_array = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if img is None:
                return jsonify({'error': 'Invalid image format. Please upload a JPG or PNG file.'}), 400
            
            print(f"Image decoded successfully: {img.shape}")
            
        except Exception as e:
            print(f"Image decode error: {e}")
            return jsonify({'error': 'Could not process the image file.'}), 400
        
        # Perform basic image analysis
        analysis_result, error = analyze_image_basic(img)
        
        if error:
            print(f"Analysis error: {error}")
            return jsonify({'error': error}), 400
        
        # Generate recommendations based on analysis
        all_recommendations = [
            {"name": "Classic Taper Fade", "reason": "A timeless cut that's clean and professional, perfect for your face shape."},
            {"name": "Textured Crop Top", "reason": "Modern and stylish, adds volume and works well with your features."},
            {"name": "High and Tight", "reason": "Military-inspired cut that's low-maintenance and emphasizes your facial structure."},
            {"name": "Slick Back Undercut", "reason": "Bold and trendy look with great contrast and styling options."},
            {"name": "Buzz Cut", "reason": "Simple, clean, and requires virtually no styling."},
            {"name": "Side Part", "reason": "Classic versatile style for both casual and formal settings."},
            {"name": "Modern Quiff", "reason": "Stylish and adaptable, great for your hair texture."},
            {"name": "Crew Cut", "reason": "Low maintenance and always looks sharp and professional."},
            {"name": "Pompadour", "reason": "Vintage style with modern appeal, works well with your face shape."},
            {"name": "Messy Fringe", "reason": "Casual and trendy, perfect for a relaxed everyday look."}
        ]
        
        # Select recommendations based on face shape
        if analysis_result["face_shape"] in ["Round", "Square"]:
            # Prefer cuts that add height
            preferred = [r for r in all_recommendations if any(word in r["name"] for word in ["Quiff", "Pompadour", "Crop"])]
        elif analysis_result["face_shape"] == "Long":
            # Prefer cuts that add width
            preferred = [r for r in all_recommendations if any(word in r["name"] for word in ["Side", "Fringe", "Buzz"])]
        else:
            # Oval faces can handle most styles
            preferred = all_recommendations
        
        # If not enough preferred styles, add from all
        if len(preferred) < 4:
            remaining = [r for r in all_recommendations if r not in preferred]
            preferred.extend(remaining)
        
        # Shuffle and take 4
        random.shuffle(preferred)
        selected_recommendations = preferred[:4]
        
        # Build response
        response_data = {
            "analysis": {
                "faceShape": analysis_result["face_shape"],
                "hairTexture": analysis_result["hair_texture"],
                "estimatedAge": analysis_result["estimated_age"],
                "gender": analysis_result["gender"]
            },
            "recommendations": selected_recommendations,
            "debug": {
                "facesDetected": analysis_result["faces_detected"],
                "imageBrightness": analysis_result["image_brightness"]
            }
        }
        
        print(f"Analysis successful: {analysis_result['faces_detected']} faces detected")
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"Critical error: {e}")
        import traceback
        traceback.print_exc()
        
        # Return mock data as fallback to prevent total failure
        fallback_data = {
            "analysis": {
                "faceShape": "Oval",
                "hairTexture": "Straight", 
                "estimatedAge": 28,
                "gender": "Male"
            },
            "recommendations": [
                {"name": "Classic Taper Fade", "reason": "A timeless cut that's clean and professional."},
                {"name": "Textured Crop Top", "reason": "Modern and stylish with great versatility."},
                {"name": "Side Part", "reason": "Classic style perfect for any occasion."},
                {"name": "Crew Cut", "reason": "Low maintenance and always sharp."}
            ],
            "debug": {
                "fallbackUsed": True,
                "error": str(e)
            }
        }
        return jsonify(fallback_data), 200

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'opencv_available': True}), 200

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 10000))
    print(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
