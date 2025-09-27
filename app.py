import os
import base64
import random
import cv2
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from deepface import DeepFace

app = Flask(__name__)
# Allow requests from any origin, which is fine for this proxy setup
CORS(app)

# --- Simulated Data for Analysis ---
# We simulate these because reliable open-source models for these specific
# traits are difficult to implement and host in a lightweight app.
SIMULATED_FACE_SHAPES = ["Oval", "Round", "Square", "Heart", "Diamond", "Long"]
SIMULATED_HAIR_TEXTURES = ["Straight", "Wavy", "Curly", "Coily"]

# A pool of recommendations to choose from
RECOMMENDATIONS_POOL = {
    "masculine": [
        {"styleName": "Classic Taper", "description": "A timeless cut that's short on the sides and gradually longer on top.", "reason": "Its versatility complements almost any face shape by adding balance."},
        {"styleName": "Textured Crop", "description": "A modern, short haircut with a lot of texture on top for a stylish, messy look.", "reason": "The texture on top adds volume and can help elongate a rounder face shape."},
        {"styleName": "Side Part", "description": "A clean and professional look where the hair is parted neatly to one side.", "reason": "Creates a sophisticated, asymmetrical look that can sharpen softer facial features."},
        {"styleName": "Undercut", "description": "Features a sharp contrast between long hair on top and very short sides.", "reason": "This bold style draws attention upwards, highlighting the eyes and cheekbones."},
        {"styleName": "Buzz Cut", "description": "A very short, uniform cut that's easy to maintain and always looks sharp.", "reason": "It emphasizes strong facial features and bone structure, offering a clean, masculine profile."},
        {"styleName": "Modern Mullet", "description": "Business in the front, party in the back, but with modern textured styling.", "reason": "A trendy, edgy choice that works well with wavy or curly textures."},
        {"styleName": "Quiff", "description": "Similar to a pompadour but often messier and more voluminous.", "reason": "Adds significant height, which can make a face appear longer and more balanced."},
    ],
    "feminine": [
        {"styleName": "Long Layers", "description": "Soft, cascading layers that add movement and volume to long hair.", "reason": "This classic style can soften angular face shapes and is incredibly versatile."},
        {"styleName": "Wavy Bob", "description": "A chic, chin-length cut with soft waves for a relaxed and modern feel.", "reason": "It can add width to a narrow face and highlights the jawline beautifully."},
        {"styleName": "Pixie Cut", "description": "A very short, stylish cut that can be either soft and feminine or edgy and bold.", "reason": "Opens up the face and highlights beautiful eyes and cheekbones."},
        {"styleName": "Shag", "description": "A heavily layered cut with a rock-and-roll vibe, featuring lots of texture and a feathered finish.", "reason": "The layers create volume and can balance a long face shape or soften a square jaw."},
        {"styleName": "Blunt Cut", "description": "A haircut with a sharp, straight-across edge, often seen on bobs or long hair.", "reason": "Creates a look of thickness and health, providing a strong, geometric frame for the face."},
        {"styleName": "Curtain Bangs", "description": "Longer bangs parted in the middle that frame the face on both sides.", "reason": "They soften the face and draw attention to the eyes, complementing many face shapes."},
        {"styleName": "Asymmetrical Bob", "description": "A bob that is cut shorter in the back and longer in the front.", "reason": "Creates a dynamic, angular line that can add definition to a rounder face."},
    ]
}

def decode_image(base64_string):
    """Decodes a base64 string into an OpenCV-readable image."""
    # Add padding if missing
    padding_needed = len(base64_string) % 4
    if padding_needed:
        base64_string += '=' * (4 - padding_needed)

    try:
        # Decode the image data
        img_data = base64.b64decode(base64_string)
        # Convert to numpy array
        nparr = np.frombuffer(img_data, np.uint8)
        # Decode image to OpenCV format (BGR)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        app.logger.error(f"Base64 decoding failed: {e}")
        return None

@app.route('/analyze', methods=['POST'])
def analyze_image():
    data = request.get_json()
    if 'payload' not in data or 'contents' not in data['payload']:
        return jsonify({"error": "Invalid request payload structure."}), 400

    # The actual image data is nested within the payload structure
    try:
        base64_image_data = data['payload']['contents'][0]['parts'][1]['inlineData']['data']
    except (KeyError, IndexError):
        return jsonify({"error": "Could not find image data in request."}), 400

    img = decode_image(base64_image_data)
    if img is None:
        return jsonify({"error": "Failed to decode image. The image data might be corrupt."}), 400

    try:
        # --- Real AI Analysis using deepface ---
        # We use deepface to verify a face exists and get basic attributes.
        # This will throw an exception if no face is found.
        analysis_result = DeepFace.analyze(
            img_path=img,
            actions=['age', 'gender'],
            enforce_detection=True, # This ensures it fails if no face is detected
            detector_backend='ssd' # Using a faster detector
        )
        
        # The result is a list of dicts, one for each face. We take the first one.
        main_face = analysis_result[0]

        # --- Simulated Analysis & Recommendations ---
        dominant_gender = main_face['dominant_gender']
        estimated_age = main_face['age']

        # Choose a recommendation pool based on gender
        if dominant_gender.lower() == 'man':
            recommendation_pool = RECOMMENDATIONS_POOL['masculine']
            gender_label = "Masculine"
        else:
            recommendation_pool = RECOMMENDATIONS_POOL['feminine']
            gender_label = "Feminine"

        # Construct the final JSON response in the format the frontend expects
        response_data = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "analysis": {
                                "faceShape": random.choice(SIMULATED_FACE_SHAPES),
                                "hairTexture": random.choice(SIMULATED_HAIR_TEXTURES),
                                "estimatedAge": f"{estimated_age - 5}-{estimated_age + 5}",
                                "estimatedGender": gender_label
                            },
                            "recommendations": random.sample(recommendation_pool, 4)
                        })
                    }]
                }
            }]
        }
        return jsonify(response_data)

    except ValueError as e:
        # This exception is often thrown by deepface if no face is detected
        app.logger.warning(f"DeepFace analysis failed: {e}")
        return jsonify({"error": "This doesn't look like a photo of a person's face. Please upload a different image."}), 400
    except Exception as e:
        app.logger.error(f"An unexpected error occurred during analysis: {e}")
        return jsonify({"error": "An internal server error occurred during analysis."}), 500

if __name__ == '__main__':
    # Use the PORT environment variable if available, otherwise default to 3000
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
