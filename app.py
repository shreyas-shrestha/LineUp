# app.py - MINIMAL WORKING VERSION
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import os
import json

app = Flask(__name__)
# Enable CORS for all routes with all origins
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type"]}})

# Basic route
@app.route('/')
def index():
    return "LineUp AI Backend is running!"

# Health check
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": "2024",
        "message": "Server is running"
    })

# Main analyze endpoint - ALWAYS returns mock data for now
@app.route('/analyze', methods=['GET', 'POST', 'OPTIONS'])
def analyze():
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "*")
        response.headers.add('Access-Control-Allow-Methods', "*")
        return response
    
    # For GET requests (browser test)
    if request.method == 'GET':
        return jsonify({"message": "This endpoint accepts POST requests with image data"})
    
    # For POST requests - always return mock data
    print("=" * 50)
    print("ANALYZE ENDPOINT - POST REQUEST RECEIVED")
    print("=" * 50)
    
    # Don't even try to parse the request - just return mock data
    mock_data = {
        "analysis": {
            "faceShape": "oval",
            "hairTexture": "wavy",
            "hairColor": "brown",
            "estimatedGender": "male",
            "estimatedAge": "25-30"
        },
        "recommendations": [
            {
                "styleName": "Classic Fade",
                "description": "Short on sides, gradual blend to longer on top",
                "reason": "Works great with oval face shape"
            },
            {
                "styleName": "Textured Quiff",
                "description": "Modern style with volume and texture",
                "reason": "Complements wavy hair texture"
            },
            {
                "styleName": "Side Part",
                "description": "Timeless professional look",
                "reason": "Enhances facial symmetry"
            },
            {
                "styleName": "Messy Crop",
                "description": "Casual textured style",
                "reason": "Low maintenance and stylish"
            },
            {
                "styleName": "Buzz Cut",
                "description": "Very short all over",
                "reason": "Clean and minimal maintenance"
            }
        ]
    }
    
    print("Returning mock data...")
    print(json.dumps(mock_data, indent=2))
    
    # Create response with explicit headers
    response = make_response(jsonify(mock_data))
    response.headers['Content-Type'] = 'application/json'
    response.headers['Access-Control-Allow-Origin'] = '*'
    
    return response

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed", "allowed": ["POST", "OPTIONS"]}), 405

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting server on port {port}")
    print("This is the MINIMAL version - always returns mock data")
    app.run(host="0.0.0.0", port=port, debug=False)  # Turn off debug mode for production
