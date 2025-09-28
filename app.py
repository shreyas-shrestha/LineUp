# Appointments endpoints with rate limiting
@app.route('/appointments', methods=['GET', 'POST', 'OPTIONS'])
def handle_appointments():
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response, 200
    
    if request.method == 'GET':
        # Light rate limit for viewing appointments
        limiter.limit("100 per hour")(lambda: None)()
        
        user_type = request.args.get('type', 'client')
        user_id = request.args.get('user_id', 'current_user')
        
        if user_type == 'client':
            user_appointments = [apt for apt in appointments if apt.get('clientId') == user_id]
        else:  # barber
            user_appointments = [apt for apt in appointments if apt.get('barberId') == user_id]
        
        response = make_response(jsonify({"appointments": user_appointments}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    elif request.method == 'POST':
        # Moderate rate limit for booking appointments
        limiter.limit("30 per hour")(lambda: None)()
        
        try:
            data = request.get_json()
            
            new_appointment = {
                "id": str(uuid.uuid4()),
                "clientName": data.get("clientName", "Anonymous Client"),
                "clientId": data.get("clientId", "current_user"),
                "barberName": data.get("barberName", "Unknown Barber"),
                "barberId": data.get("barberId", "unknown_barber"),
                "date": data.get("date", ""),
                "time": data.get("time", ""),
                "service": data.get("service", ""),
                "price": data.get("price", "$0"),
                "status": "pending",
                "notes": data.get("notes", "No special requests"),
                "timestamp": datetime.now().isoformat()
            }
            
            appointments.append(new_appointment)
            
            response = make_response(jsonify({"success": True, "appointment": new_appointment}), 201)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
            
        except Exception as e:
            logger.error(f"Error creating appointment: {str(e)}")
            response = make_response(jsonify({"error": "Failed to create appointment"}), 400)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response

# Update appointment status with rate limiting
@app.route('/appointments/<appointment_id>/status', methods=['PUT', 'OPTIONS'])
@limiter.limit("50 per hour")
def update_appointment_status(appointment_id):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'PUT, OPTIONS')
        return response, 200
    
    try:
        data = request.get_json()
        new_status = data.get("status", "pending")
        
        appointment = next((apt for apt in appointments if apt["id"] == appointment_id), None)
        if not appointment:
            response = make_response(jsonify({"error": "Appointment not found"}), 404)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        appointment["status"] = new_status
        
        response = make_response(jsonify({"success": True, "appointment": appointment}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        logger.error(f"Error updating appointment: {str(e)}")
        response = make_response(jsonify({"error": "Failed to update appointment"}), 400)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

# Barber discovery endpoint with caching and rate limiting
@app.route('/barbers', methods=['GET', 'OPTIONS'])
@limiter.limit("50 per hour")  # Moderate limit since this might call external APIs
def get_barbers():
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    location = request.args.get('location', 'Atlanta, GA')
    
    # Check cache first
    cache_key = location.lower().strip()
    current_time = time.time()
    
    if cache_key in places_api_cache:
        cached_data = places_api_cache[cache_key]
        if current_time - cached_data['timestamp'] < CACHE_DURATION:
            logger.info(f"Returning cached barber data for {location}")
            response = make_response(jsonify({
                "barbers": cached_data['data'], 
                "location": location,
                "cached": True
            }), 200)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
    
    # Check if we can make Places API call
    if not can_make_places_api_call():
        logger.warning("Places API daily limit reached, using mock data")
        mock_barbers = getMockBarbersForLocation(location)
        response = make_response(jsonify({
            "barbers": mock_barbers, 
            "location": location,
            "mock": True,
            "reason": "API limit reached"
        }), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    # Try to fetch real data (this would require implementing Places API calls on backend)
    # For now, use enhanced mock data and cache it
    mock_barbers = getMockBarbersForLocation(location)
    
    # Cache the results
    places_api_cache[cache_key] = {
        'data': mock_barbers,
        'timestamp': current_time
    }
    
    # Increment API usage (even for mock data to simulate)
    increment_places_api_usage()
    
    response = make_response(jsonify({
        "barbers": mock_barbers, 
        "location": location,
        "mock": True
    }), 200)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

def getMockBarbersForLocation(location):
    """Generate location-specific mock barber data"""
    base_barbers = [
        {
            "id": "barber_1",
            "name": f"Elite Cuts {location.split(',')[0]}",
            "specialties": ["Fade", "Taper", "Modern Cuts"],
            "rating": 4.9,
            "avgCost": 45,
            "address": f"Downtown {location.split(',')[0]}",
            "photo": "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=400&h=300&fit=crop",
            "phone": "(555) 123-4567",
            "hours": "Mon-Sat 9AM-8PM"
        },
        {
            "id": "barber_2", 
            "name": f"The {location.split(',')[0]} Barber",
            "specialties": ["Pompadour", "Buzz Cut", "Beard Trim"],
            "rating": 4.8,
            "avgCost": 55,
            "address": f"Uptown {location.split(',')[0]}",
            "photo": "https://images.unsplash.com/photo-1585747860715-2ba37e788b70?w=400&h=300&fit=crop",
            "phone": "(555) 123-4568",
            "hours": "Tue-Sun 10AM-7PM"
        },
        {
            "id": "barber_3",
            "name": f"{location.split(',')[0]} Style Studio",
            "specialties": ["Modern Fade", "Beard Trim", "Styling"],
            "rating": 4.9,
            "avgCost": 65,
            "address": f"Midtown {location.split(',')[0]}",
            "photo": "https://images.unsplash.com/photo-1605497788044-5a32c7078486?w=400&h=300&fit=crop",
            "phone": "(555) 123-4569",
            "hours": "Mon-Fri 8AM-6PM"
        }
    ]
    return base_barbers

# Portfolio endpoints with rate limiting
@app.route('/portfolio', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/portfolio/<barber_id>', methods=['GET', 'POST', 'OPTIONS'])
def portfolio(barber_id=None):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response, 200
    
    if request.method == 'GET':
        # Light rate limit for viewing portfolios
        limiter.limit("100 per hour")(lambda: None)()
        
        if barber_id:
            portfolio = barber_portfolios.get(barber_id, [])
        else:
            # Return all portfolios
            portfolio = []
            for barber_portfolio in barber_portfolios.values():
                portfolio.extend(barber_portfolio)
        
        response = make_response(jsonify({"portfolio": portfolio}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    elif request.method == 'POST':
        # Moderate rate limit for adding portfolio items
        limiter.limit("25 per hour")(lambda: None)()
        
        try:
            data = request.get_json()
            barber_id = barber_id or data.get("barberId", "default_barber")
            
            new_work = {
                "id": str(uuid.uuid4()),
                "styleName": data.get("styleName", ""),
                "image": data.get("image", ""),
                "description": data.get("description", ""),
                "likes": 0,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "barberId": barber_id,
                "timestamp": datetime.now().isoformat()
            }
            
            if barber_id not in barber_portfolios:
                barber_portfolios[barber_id] = []
            
            barber_portfolios[barber_id].insert(0, new_work)
            
            response = make_response(jsonify({"success": True, "work": new_work}), 201)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
            
        except Exception as e:
            logger.error(f"Error adding portfolio work: {str(e)}")
            response = make_response(jsonify({"error": "Failed to add work"}), 400)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response

# Test endpoint with rate limiting
@app.route('/test', methods=['GET', 'POST'])
@limiter.limit("100 per minute")
def test():
    return jsonify({
        "message": "Test successful",
        "method": request.method,
        "gemini_configured": model is not None,
        "timestamp": datetime.now().isoformat(),
        "rate_limiting": "active",
        "features_active": True
    })

# Rate limit exceeded handler
@app.errorhandler(429)
def rate_limit_exceeded(error):
    response = make_response(jsonify({
        "error": "Rate limit exceeded",
        "message": "Too many requests. Please try again later.",
        "retry_after": getattr(error, 'retry_after', 60)
    }), 429)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

# Handle 404
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Endpoint not found", 
        "available": ["/", "/health", "/analyze", "/social", "/portfolio", "/appointments", "/barbers", "/test"]
    }), 404

# Handle 500
@app.errorhandler(500)
def server_error(e):
    logger.error(f"500 error: {str(e)}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting LineUp Backend v2.0 with Rate Limiting on port {port}")
    logger.info(f"Gemini API configured: {model is not None}")
    logger.info(f"Expected frontend: https://lineupai.onrender.com")
    logger.info("Rate limits: AI Analysis (10/hr), Social Posts (20/hr), General (1000/hr)")
    logger.info("CORS enabled for all origins")
    logger.info("Features: AI Analysis, Social Feed, Barber Portfolios, Appointments")
    app.run(host="0.0.0.0", port=port, debug=False)# app.py - Updated Backend API with Rate Limiting
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import json
import logging
import google.generativeai as genai
import base64
from PIL import Image
from io import BytesIO
from datetime import datetime, timedelta
import uuid
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per hour"],  # Global rate limit
    storage_uri="memory://",  # Use Redis in production: "redis://localhost:6379"
    strategy="moving-window"
)

# Configure CORS
CORS(app, 
     origins=["https://lineupai.onrender.com", "http://localhost:*", "*"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Accept", "Authorization"],
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

# Configure Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-pro')
    logger.info("Gemini API configured successfully")
else:
    model = None
    logger.warning("GEMINI_API_KEY not found - will use mock data")

# In-memory storage (in production, use a proper database)
social_posts = []
barber_portfolios = {}
appointments = []
barber_profiles = {}

# Rate limiting cache for Google Places API
places_api_cache = {}
CACHE_DURATION = 3600  # 1 hour cache for Places API results

# Rate limiting tracker
api_usage_tracker = {
    'places_api_calls': 0,
    'gemini_api_calls': 0,
    'daily_reset': datetime.now().date()
}

def reset_daily_counters():
    """Reset API usage counters daily"""
    global api_usage_tracker
    today = datetime.now().date()
    if api_usage_tracker['daily_reset'] != today:
        api_usage_tracker = {
            'places_api_calls': 0,
            'gemini_api_calls': 0,
            'daily_reset': today
        }
        logger.info("Daily API usage counters reset")

def can_make_places_api_call():
    """Check if we can make a Places API call (limit: 100/day for free tier)"""
    reset_daily_counters()
    return api_usage_tracker['places_api_calls'] < 100

def can_make_gemini_api_call():
    """Check if we can make a Gemini API call (limit: 50/day for free tier)"""
    reset_daily_counters()
    return api_usage_tracker['gemini_api_calls'] < 50

def increment_places_api_usage():
    """Increment Places API usage counter"""
    reset_daily_counters()
    api_usage_tracker['places_api_calls'] += 1

def increment_gemini_api_usage():
    """Increment Gemini API usage counter"""
    reset_daily_counters()
    api_usage_tracker['gemini_api_calls'] += 1

# Initialize with mock data
def initialize_mock_data():
    global social_posts, barber_portfolios, appointments, barber_profiles
    
    # Mock social posts
    social_posts = [
        {
            "id": "1",
            "username": "mike_style",
            "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop&crop=face",
            "image": "https://images.unsplash.com/photo-1622296089863-eb7fc530daa8?w=400&h=400&fit=crop",
            "caption": "Fresh fade from @atlanta_cuts 🔥",
            "likes": 23,
            "timeAgo": "2h",
            "liked": False,
            "timestamp": datetime.now().isoformat()
        },
        {
            "id": "2", 
            "username": "sarah_hair",
            "avatar": "https://images.unsplash.com/photo-1494790108755-2616b612b786?w=100&h=100&fit=crop&crop=face",
            "image": "https://images.unsplash.com/photo-1605497788044-5a32c7078486?w=400&h=400&fit=crop",
            "caption": "New bob cut! Love how it frames my face ✨",
            "likes": 45,
            "timeAgo": "4h",
            "liked": True,
            "timestamp": (datetime.now() - timedelta(hours=4)).isoformat()
        }
    ]
    
    # Mock barber portfolios
    barber_portfolios = {
        "barber_1": [
            {
                "id": "1",
                "styleName": "Modern Fade",
                "image": "https://images.unsplash.com/photo-1622296089863-eb7fc530daa8?w=400&h=400&fit=crop",
                "description": "Clean fade with textured top. Perfect for professionals.",
                "likes": 12,
                "date": "2024-01-15",
                "barberId": "barber_1"
            }
        ]
    }
    
    # Mock appointments
    appointments = [
        {
            "id": str(uuid.uuid4()),
            "clientName": "Alex Johnson",
            "clientId": "client_1", 
            "barberName": "Mike's Cuts",
            "barberId": "barber_1",
            "date": "2024-01-20",
            "time": "14:00",
            "service": "Haircut + Beard",
            "price": "$65",
            "status": "confirmed",
            "notes": "Looking for a modern fade",
            "timestamp": datetime.now().isoformat()
        }
    ]

initialize_mock_data()

# Root endpoint
@app.route('/')
@limiter.limit("100 per minute")
def index():
    return jsonify({
        "service": "LineUp AI Backend",
        "status": "running",
        "version": "2.0",
        "gemini_configured": model is not None,
        "features": ["AI Analysis", "Social Feed", "Barber Portfolios", "Appointments"],
        "rate_limits": {
            "general": "1000 per hour",
            "ai_analysis": "10 per hour per IP",
            "social_posts": "20 per hour per IP",
            "appointments": "30 per hour per IP"
        },
        "endpoints": {
            "health": "/health",
            "analyze": "/analyze (POST)",
            "social": "/social (GET/POST)",
            "portfolio": "/portfolio (GET/POST)",
            "appointments": "/appointments (GET/POST)",
            "barbers": "/barbers (GET)"
        }
    })

# Health check endpoint
@app.route('/health', methods=['GET'])
@limiter.limit("200 per minute")
def health():
    reset_daily_counters()
    return jsonify({
        "status": "healthy",
        "service": "lineup-backend",
        "timestamp": datetime.now().isoformat(),
        "cors_enabled": True,
        "gemini_configured": model is not None,
        "places_api_configured": bool(os.environ.get("GOOGLE_PLACES_API_KEY")),
        "frontend_url": "https://lineupai.onrender.com",
        "api_usage": {
            "places_api_calls_today": api_usage_tracker['places_api_calls'],
            "gemini_api_calls_today": api_usage_tracker['gemini_api_calls'],
            "daily_reset": api_usage_tracker['daily_reset'].isoformat()
        },
        "data_counts": {
            "social_posts": len(social_posts),
            "appointments": len(appointments),
            "barber_portfolios": len(barber_portfolios)
        }
    })

# Configuration endpoint
@app.route('/config', methods=['GET', 'OPTIONS'])
@limiter.limit("100 per minute")
def get_config():
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    response = make_response(jsonify({
        "placesApiKey": os.environ.get("GOOGLE_PLACES_API_KEY", ""),
        "hasPlacesApi": bool(os.environ.get("GOOGLE_PLACES_API_KEY")),
        "backendVersion": "2.0",
        "rateLimits": {
            "places_api_remaining": max(0, 100 - api_usage_tracker['places_api_calls']),
            "gemini_api_remaining": max(0, 50 - api_usage_tracker['gemini_api_calls'])
        }
    }), 200)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

# Mock data fallback for AI analysis
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

# Main analyze endpoint with rate limiting
@app.route('/analyze', methods=['POST', 'OPTIONS'])
@limiter.limit("10 per hour")  # Strict limit for AI analysis
def analyze():
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    logger.info("ANALYZE endpoint called")
    
    # Check if we can make Gemini API call
    if not can_make_gemini_api_call():
        logger.warning("Gemini API daily limit reached, using mock data")
        response = make_response(jsonify(get_mock_data()), 200)
        response.headers['Content-Type'] = 'application/json'
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    try:
        data = request.get_json(force=True)
        
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
                raise ValueError("No image data provided")
            
            image_data = parts[1].get("inlineData", {})
            base64_image = image_data.get("data", "")
            
            if not base64_image:
                raise ValueError("Empty image data")
            
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid request format: {str(e)}")
        
        # Decode base64 image
        try:
            image_bytes = base64.b64decode(base64_image)
            image = Image.open(BytesIO(image_bytes))
        except Exception as e:
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

Provide exactly 5 haircut recommendations that would work best for this person's features."""

        # Call Gemini API
        try:
            increment_gemini_api_usage()  # Track API usage
            response = model.generate_content([prompt, image])
            response_text = response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            response = make_response(jsonify(get_mock_data()), 200)
            response.headers['Content-Type'] = 'application/json'
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        # Clean and parse response
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.rfind("```")
            if end > start:
                response_text = response_text[start:end].strip()
        
        try:
            analysis_data = json.loads(response_text)
        except json.JSONDecodeError:
            response = make_response(jsonify(get_mock_data()), 200)
            response.headers['Content-Type'] = 'application/json'
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        # Validate and return response
        if "analysis" not in analysis_data or "recommendations" not in analysis_data:
            response = make_response(jsonify(get_mock_data()), 200)
            response.headers['Content-Type'] = 'application/json'
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        response = make_response(jsonify(analysis_data), 200)
        response.headers['Content-Type'] = 'application/json'
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        logger.error(f"Error in analyze endpoint: {str(e)}")
        response = make_response(jsonify(get_mock_data()), 200)
        response.headers['Content-Type'] = 'application/json'
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

# Social feed endpoints with rate limiting
@app.route('/social', methods=['GET', 'POST', 'OPTIONS'])
def social():
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response, 200
    
    if request.method == 'GET':
        # Lighter rate limit for GET requests
        limiter.limit("100 per hour")(lambda: None)()
        
        # Return social posts sorted by timestamp
        sorted_posts = sorted(social_posts, key=lambda x: x['timestamp'], reverse=True)
        response = make_response(jsonify({"posts": sorted_posts}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    elif request.method == 'POST':
        # Stricter rate limit for POST requests
        limiter.limit("20 per hour")(lambda: None)()
        
        try:
            data = request.get_json()
            
            new_post = {
                "id": str(uuid.uuid4()),
                "username": data.get("username", "anonymous"),
                "avatar": data.get("avatar", "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&h=100&fit=crop&crop=face"),
                "image": data.get("image", ""),
                "caption": data.get("caption", ""),
                "likes": 0,
                "timeAgo": "now",
                "liked": False,
                "timestamp": datetime.now().isoformat()
            }
            
            social_posts.insert(0, new_post)
            
            response = make_response(jsonify({"success": True, "post": new_post}), 201)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
            
        except Exception as e:
            logger.error(f"Error creating social post: {str(e)}")
            response = make_response(jsonify({"error": "Failed to create post"}), 400)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response

# Like/unlike post with rate limiting
@app.route('/social/<post_id>/like', methods=['POST', 'OPTIONS'])
@limiter.limit("60 per hour")  # Allow frequent likes but prevent spam
def toggle_like(post_id):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    try:
        post = next((p for p in social_posts if p["id"] == post_id), None)
        if not post:
            response = make_response(jsonify({"error": "Post not found"}), 404)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        post["liked"] = not post["liked"]
        post["likes"] += 1 if post["liked"] else -1
        
        response = make_response(jsonify({"success": True, "liked": post["liked"], "likes": post["likes"]}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        logger.error(f"Error toggling like: {str(e)}")
        response = make_response(jsonify({"error": "Failed to toggle like"}), 400)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

# Barber portfolio endpoints
@app.route('/portfolio', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/portfolio/<barber_id>', methods=['GET', 'POST', 'OPTIONS'])
def portfolio(barber_id=None):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response, 200
    
    if request.method == 'GET':
        if barber_id:
            portfolio = barber_portfolios.get(barber_id, [])
        else:
            # Return all portfolios
            portfolio = []
            for barber_portfolio in barber_portfolios.values():
                portfolio.extend(barber_portfolio)
        
        response = make_response(jsonify({"portfolio": portfolio}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            barber_id = barber_id or data.get("barberId", "default_barber")
            
            new_work = {
                "id": str(uuid.uuid4()),
                "styleName": data.get("styleName", ""),
                "image": data.get("image", ""),
                "description": data.get("description", ""),
                "likes": 0,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "barberId": barber_id,
                "timestamp": datetime.now().isoformat()
            }
            
            if barber_id not in barber_portfolios:
                barber_portfolios[barber_id] = []
            
            barber_portfolios[barber_id].insert(0, new_work)
            
            response = make_response(jsonify({"success": True, "work": new_work}), 201)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
            
        except Exception as e:
            logger.error(f"Error adding portfolio work: {str(e)}")
            response = make_response(jsonify({"error": "Failed to add work"}), 400)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response

# Appointments endpoints
@app.route('/appointments', methods=['GET', 'POST', 'OPTIONS'])
def handle_appointments():
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response, 200
    
    if request.method == 'GET':
        user_type = request.args.get('type', 'client')
        user_id = request.args.get('user_id', 'current_user')
        
        if user_type == 'client':
            user_appointments = [apt for apt in appointments if apt.get('clientId') == user_id]
        else:  # barber
            user_appointments = [apt for apt in appointments if apt.get('barberId') == user_id]
        
        response = make_response(jsonify({"appointments": user_appointments}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            
            new_appointment = {
                "id": str(uuid.uuid4()),
                "clientName": data.get("clientName", "Anonymous Client"),
                "clientId": data.get("clientId", "current_user"),
                "barberName": data.get("barberName", "Unknown Barber"),
                "barberId": data.get("barberId", "unknown_barber"),
                "date": data.get("date", ""),
                "time": data.get("time", ""),
                "service": data.get("service", ""),
                "price": data.get("price", "$0"),
                "status": "pending",
                "notes": data.get("notes", "No special requests"),
                "timestamp": datetime.now().isoformat()
            }
            
            appointments.append(new_appointment)
            
            response = make_response(jsonify({"success": True, "appointment": new_appointment}), 201)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
            
        except Exception as e:
            logger.error(f"Error creating appointment: {str(e)}")
            response = make_response(jsonify({"error": "Failed to create appointment"}), 400)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response

# Update appointment status
@app.route('/appointments/<appointment_id>/status', methods=['PUT', 'OPTIONS'])
def update_appointment_status(appointment_id):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'PUT, OPTIONS')
        return response, 200
    
    try:
        data = request.get_json()
        new_status = data.get("status", "pending")
        
        appointment = next((apt for apt in appointments if apt["id"] == appointment_id), None)
        if not appointment:
            response = make_response(jsonify({"error": "Appointment not found"}), 404)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        appointment["status"] = new_status
        
        response = make_response(jsonify({"success": True, "appointment": appointment}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        logger.error(f"Error updating appointment: {str(e)}")
        response = make_response(jsonify({"error": "Failed to update appointment"}), 400)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

# Barber discovery endpoint (mock data)
@app.route('/barbers', methods=['GET', 'OPTIONS'])
def get_barbers():
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    location = request.args.get('location', 'Atlanta, GA')
    
    # Mock barber data
    mock_barbers = [
        {
            "id": "barber_1",
            "name": "Elite Cuts Atlanta",
            "specialties": ["Fade", "Taper", "Modern Cuts"],
            "rating": 4.9,
            "avgCost": 45,
            "address": "Midtown Atlanta",
            "photo": "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=400&h=300&fit=crop",
            "phone": "(404) 555-0123",
            "hours": "Mon-Sat 9AM-8PM"
        },
        {
            "id": "barber_2", 
            "name": "The Buckhead Barber",
            "specialties": ["Pompadour", "Buzz Cut", "Beard Trim"],
            "rating": 4.8,
            "avgCost": 55,
            "address": "Buckhead",
            "photo": "https://images.unsplash.com/photo-1585747860715-2ba37e788b70?w=400&h=300&fit=crop",
            "phone": "(404) 555-0124",
            "hours": "Tue-Sun 10AM-7PM"
        },
        {
            "id": "barber_3",
            "name": "Virginia-Highland Shears",
            "specialties": ["Modern Fade", "Beard Trim", "Styling"],
            "rating": 4.9,
            "avgCost": 65,
            "address": "Virginia-Highland",
            "photo": "https://images.unsplash.com/photo-1605497788044-5a32c7078486?w=400&h=300&fit=crop",
            "phone": "(404) 555-0125",
            "hours": "Mon-Fri 8AM-6PM"
        }
    ]
    
    response = make_response(jsonify({"barbers": mock_barbers, "location": location}), 200)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

# Test endpoint
@app.route('/test', methods=['GET', 'POST'])
def test():
    return jsonify({
        "message": "Test successful",
        "method": request.method,
        "gemini_configured": model is not None,
        "timestamp": datetime.now().isoformat(),
        "features_active": True
    })

# Handle 404
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Endpoint not found", 
        "available": ["/", "/health", "/analyze", "/social", "/portfolio", "/appointments", "/barbers", "/test"]
    }), 404

# Handle 500
@app.errorhandler(500)
def server_error(e):
    logger.error(f"500 error: {str(e)}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting LineUp Backend v2.0 on port {port}")
    logger.info(f"Gemini API configured: {model is not None}")
    logger.info(f"Expected frontend: https://lineupai.onrender.com")
    logger.info("CORS enabled for all origins")
    logger.info("Features: AI Analysis, Social Feed, Barber Portfolios, Appointments")
    app.run(host="0.0.0.0", port=port, debug=False)
