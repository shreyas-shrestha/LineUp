# app.py - Serves your existing HTML/JS files AND provides the API
from flask import Flask, request, jsonify, make_response, render_template, send_from_directory
from flask_cors import CORS
import os
import json

# Initialize Flask with correct folders
app = Flask(__name__, 
            static_folder='static',      # Your JS files go here
            template_folder='templates')  # Your HTML files go here

CORS(app, resources={r"/*": {"origins": "*"}})

# Serve the main page (your existing index.html)
@app.route('/')
def index():
    return render_template('index.html')

# Serve JavaScript files from static folder
@app.route('/scripts.js')
def serve_scripts():
    return send_from_directory('static', 'scripts.js')

# Serve any other static files
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "message": "Server is running",
        "frontend": "Serving from templates/index.html",
        "backend": "API endpoints active"
    })

# Main analyze endpoint - returns mock data for now
@app.route('/analyze', methods=['POST', 'OPTIONS'])
def analyze():
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "*")
        response.headers.add('Access-Control-Allow-Methods', "*")
        return response
    
    print("=" * 50)
    print("ANALYZE ENDPOINT HIT - Processing request")
    print("=" * 50)
    
    # For now, always return mock data (you can add Gemini later)
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
                "description": "Short on sides with a gradual blend to longer hair on top",
                "reason": "Perfect for oval face shapes and professional settings"
            },
            {
                "styleName": "Textured Quiff",
                "description": "Modern style with volume and texture swept upward",
                "reason": "Takes advantage of your natural wavy texture"
            },
            {
                "styleName": "Side Part",
                "description": "Timeless professional look with a defined part",
                "reason": "Enhances facial symmetry and looks sophisticated"
            },
            {
                "styleName": "Messy Crop",
                "description": "Short, textured cut with a deliberately tousled look",
                "reason": "Low maintenance while still looking stylish"
            },
            {
                "styleName": "Buzz Cut",
                "description": "Very short all over for ultimate simplicity",
                "reason": "Clean look that highlights facial features"
            }
        ]
    }
    
    response = jsonify(mock_data)
    response.headers['Content-Type'] = 'application/json'
    return response

# Error handlers
@app.errorhandler(404)
def not_found(e):
    # If it's an API call, return JSON
    if request.path.startswith('/api/') or request.path == '/analyze':
        return jsonify({"error": "Endpoint not found"}), 404
    # Otherwise, serve the main page (for client-side routing)
    return render_template('index.html')

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Flask server on port {port}")
    print("Serving frontend from: /templates/index.html")
    print("Serving JavaScript from: /static/scripts.js")
    print("API endpoint at: /analyze")
    app.run(host="0.0.0.0", port=port, debug=False)
