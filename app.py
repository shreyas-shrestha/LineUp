# app.py - Backend API for lineup-fjpn.onrender.com
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import os
import json
import logging

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

# Root endpoint
@app.route('/')
def index():
    return jsonify({
        "service": "LineUp AI Backend",
        "status": "running",
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
        "frontend_url": "https://lineupai.onrender.com"
    })

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
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request origin: {request.headers.get('Origin', 'Unknown')}")
    logger.info("=" * 50)
    
    try:
        # Get JSON data (but don't require specific format for now)
        data = request.get_json(force=True)
        logger.info(f"Received data keys: {data.keys() if data else 'None'}")
        
        # Return mock data - always works
        mock_response = {
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
        
        logger.info("Returning mock response successfully")
        
        # Create response with explicit headers
        response = make_response(jsonify(mock_response), 200)
        response.headers['Content-Type'] = 'application/json'
        response.headers['Access-Control-Allow-Origin'] = '*'
        
        return response
        
    except Exception as e:
        logger.error(f"Error in analyze endpoint: {str(e)}")
        error_response = jsonify({"error": f"Server error: {str(e)}"})
        error_response.headers['Access-Control-Allow-Origin'] = '*'
        return error_response, 500

# Test endpoint
@app.route('/test', methods=['GET', 'POST'])
def test():
    return jsonify({
        "message": "Test successful",
        "method": request.method,
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
    logger.info(f"Expected frontend: https://lineupai.onrender.com")
    logger.info("CORS enabled for all origins")
    app.run(host="0.0.0.0", port=port, debug=False)
