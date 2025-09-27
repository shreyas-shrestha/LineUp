# app.py - Backend API with Gemini Integration
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import os
import json
import logging
import google.generativeai as genai
import base64
from PIL import Image
from io import BytesIO

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure CORS to allow requests from your frontend
CORS(app, 
     origins=["https://lineupai.onrender.com", "http://localhost:*", "*"],
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Accept"],
     supports_credentials=False)

# Configure Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-pro')
    logger.info("Gemini API configured successfully")
else:
    model = None
    logger.warning("GEMINI_API_KEY not found - will use mock data")

# Root endpoint
@app.route('/')
def index():
    return jsonify({
        "service": "LineUp AI Backend",
        "status": "running",
        "gemini_configured": model is not None,
        "endpoints": {
            "health": "/health",
            "analyze": "/analyze (POST)"
        }
    })

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "lineup-backend",
        "timestamp": "2024",
        "cors_enabled": True,
        "gemini_configured": model is not None,
        "frontend_url": "https://lineupai.onrender.com"
    })

# Mock data fallback
def get_mock_data():
    return {
        "analysis": {
            "faceShape": "oval",
            "hairTexture": "wavy",
            "hairColor": "brown",
            "estimatedGender": "male",
            "estimatedAge": "25-30"
        },
        "recommendations": [
            {
                "styleName": "Modern Fade",
                "description": "A contemporary take on the classic fade with textured top",
                "reason": "Complements oval face shapes perfectly"
            },
            {
                "styleName": "Textured Quiff",
                "description": "Voluminous style swept upward for a bold look",
                "reason": "Works beautifully with wavy hair texture"
            },
            {
                "styleName": "Classic Side Part",
                "description": "Timeless and professional with clean lines",
                "reason": "Enhances facial features and adds sophistication"
            },
            {
                "styleName": "Messy Crop",
                "description": "Effortlessly cool with natural texture",
                "reason": "Low maintenance yet stylish option"
            },
            {
                "styleName": "Short Buzz",
                "description": "Clean, minimal, and masculine",
                "reason": "Highlights facial structure beautifully"
            }
        ]
    }

# Main analyze endpoint
@app.route('/analyze', methods=['POST', 'OPTIONS'])
def analyze():
    # Handle preflight
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    logger.info("=" * 50)
    logger.info("ANALYZE endpoint called")
    logger.info(f"Gemini configured: {model is not None}")
    logger.info("=" * 50)
    
    try:
        # Get JSON data
        data = request.get_json(force=True)
        
        # If Gemini is not configured, return mock data
        if not model:
            logger.info("Using mock data (Gemini not configured)")
            response = make_response(jsonify(get_mock_data()), 200)
            response.headers['Content-Type'] = 'application/json'
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        # Extract image data from request
        try:
            payload = data.get("payload", {})
            contents = payload.get("contents", [{}])[0]
            parts = contents.get("parts", [])
            
            if len(parts) < 2:
                logger.error("Missing image data in request")
                raise ValueError("No image data provided")
            
            image_data = parts[1].get("inlineData", {})
            base64_image = image_data.get("data", "")
            
            if not base64_image:
                logger.error("Empty image data")
                raise ValueError("Empty image data")
            
            logger.info(f"Received image data: {len(base64_image)} characters")
            
        except (KeyError, IndexError) as e:
            logger.error(f"Error extracting image data: {e}")
            raise ValueError(f"Invalid request format: {str(e)}")
        
        # Decode base64 image
        try:
            image_bytes = base64.b64decode(base64_image)
            image = Image.open(BytesIO(image_bytes))
            logger.info(f"Image decoded successfully: {image.size}")
        except Exception as e:
            logger.error(f"Error decoding image: {e}")
            raise ValueError(f"Invalid image data: {str(e)}")
        
        # Create Gemini prompt
        prompt = """You are an expert hairstylist and facial analysis AI. Analyze this person's face and hair in the photo and provide personalized haircut recommendations.

IMPORTANT: Return ONLY a valid JSON response with NO additional text, NO markdown formatting, NO code blocks.

Return this EXACT JSON structure:
{
    "analysis": {
        "faceShape": "[one of: oval, round, square, heart, oblong, diamond, triangle]",
        "hairTexture": "[one of: straight, wavy, curly, coily, kinky]",
        "hairColor": "[one of: black, dark-brown, brown, light-brown, blonde, red, gray, white, other]",
        "estimatedGender": "[one of: male, female, non-binary]",
        "estimatedAge": "[one of: under-20, 20-25, 25-30, 30-35, 35-40, 40-45, 45-50, 50-55, 55-60, over-60]"
    },
    "recommendations": [
        {
            "styleName": "[Specific haircut name]",
            "description": "[2-3 sentence description of the haircut style and how it's achieved]",
            "reason": "[1-2 sentences explaining why this works for their specific face shape, hair texture, and features]"
        }
    ]
}

Provide exactly 5 haircut recommendations that would work best for this person's features.
Consider their face shape, hair texture, age, and overall appearance.
Make recommendations realistic and achievable with their current hair.

If you cannot detect a clear human face in the image, return:
{"error": "No clear face detected in the image. Please upload a front-facing photo."}

Remember: Return ONLY the JSON, no other text."""

        # Call Gemini API
        logger.info("Calling Gemini API...")
        try:
            response = model.generate_content([prompt, image])
            response_text = response.text.strip()
            logger.info(f"Gemini response received: {len(response_text)} characters")
            
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            # Fall back to mock data if Gemini fails
            logger.info("Falling back to mock data due to Gemini error")
            response = make_response(jsonify(get_mock_data()), 200)
            response.headers['Content-Type'] = 'application/json'
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        # Clean the response (remove markdown if present)
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.rfind("```")
            if end > start:
                response_text = response_text[start:end].strip()
        elif "```" in response_text:
            response_text = response_text.replace("```", "").strip()
        
        # Remove any leading/trailing whitespace or newlines
        response_text = response_text.strip()
        
        # Try to parse JSON
        try:
            analysis_data = json.loads(response_text)
            logger.info("JSON parsed successfully")
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Response was: {response_text[:500]}...")
            
            # Try to extract JSON if it's embedded in text
            try:
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    analysis_data = json.loads(json_match.group())
                    logger.info("Extracted and parsed JSON from response")
                else:
                    raise ValueError("No JSON found in response")
            except Exception as e2:
                logger.error(f"Failed to extract JSON: {e2}")
                # Fall back to mock data
                logger.info("Using mock data due to parse error")
                response = make_response(jsonify(get_mock_data()), 200)
                response.headers['Content-Type'] = 'application/json'
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response
        
        # Check for error response from Gemini
        if "error" in analysis_data:
            logger.info(f"Gemini returned error: {analysis_data['error']}")
            response = make_response(jsonify(analysis_data), 400)
            response.headers['Content-Type'] = 'application/json'
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        # Validate response structure
        if "analysis" not in analysis_data or "recommendations" not in analysis_data:
            logger.error(f"Invalid response structure: {analysis_data.keys()}")
            # Fall back to mock data
            logger.info("Using mock data due to invalid structure")
            response = make_response(jsonify(get_mock_data()), 200)
            response.headers['Content-Type'] = 'application/json'
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        # Ensure we have exactly 5 recommendations
        if len(analysis_data.get("recommendations", [])) < 5:
            # Pad with some generic recommendations
            while len(analysis_data["recommendations"]) < 5:
                analysis_data["recommendations"].append({
                    "styleName": f"Style Option {len(analysis_data['recommendations']) + 1}",
                    "description": "A versatile haircut that suits many face shapes",
                    "reason": "Would complement your features well"
                })
        else:
            analysis_data["recommendations"] = analysis_data["recommendations"][:5]
        
        logger.info("Returning Gemini analysis successfully")
        
        # Create response with explicit headers
        response = make_response(jsonify(analysis_data), 200)
        response.headers['Content-Type'] = 'application/json'
        response.headers['Access-Control-Allow-Origin'] = '*'
        
        return response
        
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        error_response = jsonify({"error": str(ve)})
        error_response.headers['Access-Control-Allow-Origin'] = '*'
        return error_response, 400
        
    except Exception as e:
        logger.error(f"Unexpected error in analyze endpoint: {str(e)}")
        # Fall back to mock data for any unexpected error
        logger.info("Using mock data due to unexpected error")
        response = make_response(jsonify(get_mock_data()), 200)
        response.headers['Content-Type'] = 'application/json'
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

# Test endpoint
@app.route('/test', methods=['GET', 'POST'])
def test():
    return jsonify({
        "message": "Test successful",
        "method": request.method,
        "gemini_configured": model is not None,
        "timestamp": "2024"
    })

# Handle 404
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found", "available": ["/", "/health", "/analyze", "/test"]}), 404

# Handle 500
@app.errorhandler(500)
def server_error(e):
    logger.error(f"500 error: {str(e)}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting LineUp Backend on port {port}")
    logger.info(f"Gemini API configured: {model is not None}")
    logger.info(f"Expected frontend: https://lineupai.onrender.com")
    logger.info("CORS enabled for all origins")
    app.run(host="0.0.0.0", port=port, debug=False)
