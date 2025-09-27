import base64
import io
import random
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
from deepface import DeepFace
import cv2
import os
import traceback

app = Flask(__name__)
CORS(app)

# Pre-load a dummy image to initialize the model on startup
# This helps avoid a long delay on the first user request.
# NOTE: This function is causing an Out of Memory error on Render's 512MB RAM instances.
# We are commenting it out to allow the server to start.
# The trade-off is that the first API call will be much slower as the model loads on-demand.
# def preload_model():
#     try:
#         print("Pre-loading model...")
#         # Use a real image-like array
#         dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)
#         # It is important to call analyze on a backend that supports it, like 'opencv'
#         DeepFace.analyze(dummy_image, actions=['age', 'gender'], enforce_detection=False, detector_backend='opencv')
#         print("Model pre-loaded successfully.")
#     except Exception as e:
#         print(f"Error pre-loading model: {e}")
#         traceback.print_exc()

# # Call this function when the app starts
# preload_model()

@app.route('/analyze', methods=['POST'])
def analyze_image():
    print("Received request at /analyze endpoint.") # LOG 1

    if 'image' not in request.files:
        print("Error: No image file found in request.")
        return jsonify({'error': 'No image file provided'}), 400

    file = request.files['image']
    print(f"Received file: {file.filename}") # LOG 2
    
    try:
        in_memory_file = io.BytesIO()
        file.save(in_memory_file)
        in_memory_file.seek(0)
        
        print("Image saved to in-memory buffer.") # LOG 3

        image_np = np.frombuffer(in_memory_file.read(), np.uint8)
        img = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

        if img is None:
            print("Error: cv2.imdecode failed. The file might be corrupt or in an unsupported format.")
            return jsonify({'error': 'Could not decode the image. Please upload a valid image file (e.g., JPG, PNG).'}), 400

        print("Image decoded successfully. Calling DeepFace.analyze...") # LOG 4

        # Use DeepFace to verify there is a face and get basic attributes
        # Specifying a faster backend like 'opencv' can prevent timeouts
        analysis = DeepFace.analyze(
            img_path=img,
            actions=['age', 'gender'],
            enforce_detection=True,
            detector_backend='opencv' 
        )
        
        print("DeepFace analysis successful.") # LOG 5
        
        if not analysis or not isinstance(analysis, list) or len(analysis) == 0:
             print("DeepFace returned an empty or invalid result.")
             return jsonify({'error': 'No face detected in the image.'}), 400

        detected_face = analysis[0]
        print(f"Detected face data: {detected_face}") # LOG 6

        # --- Simulate Complex Analysis ---
        face_shapes = ["Oval", "Round", "Square", "Heart", "Diamond", "Long"]
        hair_textures = ["Straight", "Wavy", "Curly", "Coily"]
        
        recommendations = [
            {"name": "Classic Taper Fade", "reason": "A timeless cut that's clean and professional, suitable for most face shapes."},
            {"name": "Textured Crop Top", "reason": "Modern and stylish, this cut adds volume and works well with a strong jawline."},
            {"name": "High and Tight", "reason": "A military-inspired cut that's low-maintenance and emphasizes facial features."},
            {"name": "Slick Back Undercut", "reason": "A bold and trendy look that provides a lot of contrast and styling options."},
            {"name": "Buzz Cut", "reason": "Simple, masculine, and requires virtually no styling."},
            {"name": "Side Part", "reason": "A classic, versatile style that can be adapted for both casual and formal settings."}
        ]
        
        random.shuffle(recommendations)
        print("Generated recommendations.") # LOG 7

        # Build the successful response
        response_data = {
            "analysis": {
                "faceShape": random.choice(face_shapes),
                "hairTexture": random.choice(hair_textures),
                "estimatedAge": detected_face.get('age', 'N/A'),
                "gender": detected_face.get('dominant_gender', 'N/A').capitalize()
            },
            "recommendations": recommendations[:4]
        }
        
        print("Successfully prepared JSON response. Sending...") # LOG 8
        return jsonify(response_data)

    except ValueError as ve:
        if "Face could not be detected" in str(ve):
             print(f"DeepFace ValueError: {ve}")
             return jsonify({'error': 'No face detected in the image.'}), 400
        else:
             print(f"An unexpected ValueError occurred: {ve}")
             traceback.print_exc()
             return jsonify({'error': 'Error analyzing image.'}), 500
    except Exception as e:
        # This is the most important log for debugging
        print(f"CRITICAL ERROR in /analyze: {e}")
        traceback.print_exc()
        return jsonify({'error': 'An internal server error occurred.'}), 500

if __name__ == '__main__':
    # Use os.environ.get('PORT', 10000) for Render compatibility
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

