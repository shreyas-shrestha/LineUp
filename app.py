# app.py
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import os
import json
import base64
from io import BytesIO
from PIL import Image
import google.generativeai as genai

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app, origins='*')  # Allow all origins for debugging

# --- Gemini API Config ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# For local testing, you can hardcode the key temporarily
# GEMINI_API_KEY = "YOUR_API_KEY_HERE"  # Remove this line in production!

if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY environment variable not set")
    GEMINI_API_KEY = "dummy_key_for_testing"  # This will cause Gemini calls to fail but won't crash the app

# Configure Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("Gemini configured successfully")
except Exception as e:
    print(f"Error configuring Gemini: {e}")
    model = None

# --- Serve Static Files ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scripts.js')
def serve_scripts():
    return send_from_directory('static', 'scripts.js')

# --- Health Check ---
@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "gemini_configured": model is not None,
        "api_key_present": bool(GEMINI_API_KEY and GEMINI_API_KEY != "dummy_key_for_testing")
    })

# --- Main Analysis Route ---
@app.route("/analyze", methods=["POST", "OPTIONS"])
def analyze():
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return "", 204
    
    print("Received analyze request")
    
    try:
        # Get JSON data
        data = request.get_json()
        print(f"Received data keys: {data.keys() if data else 'No data'}")
        
        if not data or "payload" not in data:
            return jsonify({"error": "Invalid request - no payload"}), 400

        payload = data["payload"]
        if not payload or not payload.get("contents"):
            return jsonify({"error": "No contents in payload"}), 400

        # Extract image data
        try:
            contents = payload["contents"][0]["parts"]
            if len(contents) < 2:
                return jsonify({"error": "Image data missing from parts"}), 400
                
            inline_data = contents[1].get("inlineData")
            if not inline_data or not inline_data.get("data"):
                return jsonify({"error": "No image data found"}), 400

            image_base64 = inline_data["data"]
            mime_type = inline_data.get("mimeType", "image/jpeg")
            
            print(f"Image data received, length: {len(image_base64)}, mime: {mime_type}")
            
        except (KeyError, IndexError) as e:
            print(f"Error extracting image: {e}")
            return jsonify({"error": f"Error extracting image data: {str(e)}"}), 400
        
        # Check if model is configured
        if model is None:
            print("Gemini model not configured, returning mock data")
            # Return mock data if Gemini isn't configured
            mock_response = {
                "analysis": {
                    "faceShape": "oval",
                    "hairTexture": "straight",
                    "hairColor": "brown",
                    "estimatedGender": "male",
                    "estimatedAge": "25-30"
                },
                "recommendations": [
                    {
                        "styleName": "Classic Fade",
                        "description": "A timeless cut with short sides that gradually blend into longer hair on top",
                        "reason": "Works well with oval face shapes and straight hair"
                    },
                    {
                        "styleName": "Textured Quiff",
                        "description": "Modern style with volume at the front, swept upward and back",
                        "reason": "Adds dimension and height, perfect for your face shape"
                    },
                    {
                        "styleName": "Side Part",
                        "description": "Clean and professional with a defined part on one side",
                        "reason": "Classic look that complements straight hair texture"
                    },
                    {
                        "styleName": "Buzz Cut",
                        "description": "Very short all over, low maintenance and clean",
                        "reason": "Simple and masculine, shows off facial features"
                    },
                    {
                        "styleName": "Crew Cut",
                        "description": "Short on sides and back with slightly longer hair on top",
                        "reason": "Versatile and easy to style for any occasion"
                    }
                ]
            }
            return jsonify(mock_response)
        
        # Decode base64 to image
        try:
            image_bytes = base64.b64decode(image_base64)
            image = Image.open(BytesIO(image_bytes))
            print(f"Image decoded successfully, size: {image.size}")
        except Exception as e:
            print(f"Error decoding image: {e}")
            return jsonify({"error": f"Invalid image data: {str(e)}"}), 400
        
        # Create prompt
        prompt = """Analyze this person's face and hair in the photo.

IMPORTANT: Return ONLY valid JSON, no markdown, no extra text.

Return this exact JSON structure:
{
    "analysis": {
        "faceShape": "choose: oval, round, square, heart, oblong, or diamond",
        "hairTexture": "choose: straight, wavy, curly, or coily",
        "hairColor": "choose: black, brown, blonde, red, gray, or other",
        "estimatedGender": "choose: male, female, or non-binary",
        "estimatedAge": "choose: under-20, 20-25, 25-30, 30-35, 35-40, 40-45, 45-50, or over-50"
    },
    "recommendations": [
        {
            "styleName": "Name of hairstyle 1",
            "description": "Brief description of the style",
            "reason": "Why this works for their features"
        },
        {
            "styleName": "Name of hairstyle 2",
            "description": "Brief description of the style",
            "reason": "Why this works for their features"
        },
        {
            "styleName": "Name of hairstyle 3",
            "description": "Brief description of the style",
            "reason": "Why this works for their features"
        },
        {
            "styleName": "Name of hairstyle 4",
            "description": "Brief description of the style",
            "reason": "Why this works for their features"
        },
        {
            "styleName": "Name of hairstyle 5",
            "description": "Brief description of the style",
            "reason": "Why this works for their features"
        }
    ]
}

If no face is visible, return: {"error": "No clear face detected"}

ONLY return the JSON object, nothing else."""

        # Call Gemini API
        print("Calling Gemini API...")
        try:
            response = model.generate_content([prompt, image])
            response_text = response.text.strip()
            print(f"Gemini response received, length: {len(response_text)}")
            
        except Exception as e:
            print(f"Gemini API error: {e}")
            return jsonify({"error": f"AI service error: {str(e)}"}), 500
        
        # Clean response
        response_text = response_text.strip()
        
        # Remove markdown formatting if present
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.rfind("```")
            if end > start:
                response_text = response_text[start:end].strip()
        elif "```" in response_text:
            response_text = response_text.replace("```", "").strip()
        
        # Try to parse JSON
        try:
            analysis_data = json.loads(response_text)
            print("JSON parsed successfully")
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Response text: {response_text[:500]}...")  # Print first 500 chars
            
            # Try to extract JSON from the response
            try:
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = response_text[start:end]
                    analysis_data = json.loads(json_str)
                    print("JSON extracted and parsed successfully")
                else:
                    raise ValueError("No JSON object found")
            except Exception as e2:
                print(f"Failed to extract JSON: {e2}")
                return jsonify({"error": "AI returned invalid format"}), 500

        # Validate response structure
        if "error" in analysis_data:
            return jsonify(analysis_data), 400
            
        if "analysis" not in analysis_data or "recommendations" not in analysis_data:
            print(f"Invalid structure. Keys found: {analysis_data.keys()}")
            return jsonify({"error": "Invalid response structure from AI"}), 500
        
        # Ensure exactly 5 recommendations
        if len(analysis_data["recommendations"]) < 5:
            # Pad with generic recommendations
            while len(analysis_data["recommendations"]) < 5:
                analysis_data["recommendations"].append({
                    "styleName": f"Style Option {len(analysis_data['recommendations']) + 1}",
                    "description": "A versatile haircut option",
                    "reason": "Could work well with your features"
                })
        else:
            analysis_data["recommendations"] = analysis_data["recommendations"][:5]
        
        print("Returning successful response")
        return jsonify(analysis_data)

    except Exception as e:
        print(f"Unexpected error in /analyze: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500


# --- Error handlers ---
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting server on port {port}")
    print(f"API Key present: {bool(GEMINI_API_KEY and GEMINI_API_KEY != 'dummy_key_for_testing')}")
    app.run(host="0.0.0.0", port=port, debug=True)
