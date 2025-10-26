# app.py - Fixed Backend API with Rate Limiting
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

# Create Flask app FIRST - This was missing!
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
    model = genai.GenerativeModel('gemini-2.0-flash')
    logger.info("Gemini API configured successfully")
else:
    model = None
    logger.warning("GEMINI_API_KEY not found - will use mock data")

# In-memory storage (in production, use a proper database)
social_posts = []
barber_portfolios = {}
appointments = []
barber_profiles = {}
subscription_packages = []  # Barber subscription packages
client_subscriptions = []   # Client active subscriptions

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

Provide exactly 6 haircut recommendations that would work best for this person's features."""

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

# Barber discovery endpoint with REAL Google Places API integration
@app.route('/barbers', methods=['GET', 'OPTIONS'])
@limiter.limit("50 per hour")  # Moderate limit since this calls external APIs
def get_barbers():
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    location = request.args.get('location', 'Atlanta, GA')
    recommended_styles = request.args.get('styles', '').split(',')  # Get recommended styles
    
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
    
    # Get Google Places API key
    GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")
    
    if not GOOGLE_PLACES_API_KEY:
        logger.warning("Google Places API key not configured, using mock data")
        mock_barbers = getMockBarbersForLocation(location)
        response = make_response(jsonify({
            "barbers": mock_barbers, 
            "location": location,
            "mock": True,
            "reason": "API key not configured"
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
    
    try:
        import requests
        
        # First, geocode the location to get coordinates
        geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json"
        geocode_params = {
            'address': location,
            'key': GOOGLE_PLACES_API_KEY
        }
        
        geocode_response = requests.get(geocode_url, params=geocode_params)
        geocode_data = geocode_response.json()
        
        if geocode_data['status'] != 'OK' or not geocode_data['results']:
            raise Exception(f"Location not found: {location}")
        
        lat = geocode_data['results'][0]['geometry']['location']['lat']
        lng = geocode_data['results'][0]['geometry']['location']['lng']
        
        # Search for barbershops using Places API
        places_url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        places_params = {
            'location': f"{lat},{lng}",
            'radius': 10000,  # 10km radius
            'type': 'hair_care',
            'keyword': 'barber barbershop mens haircut',
            'key': GOOGLE_PLACES_API_KEY
        }
        
        places_response = requests.get(places_url, params=places_params)
        places_data = places_response.json()
        
        if places_data['status'] != 'OK':
            raise Exception(f"Places API error: {places_data.get('status')}")
        
        # Process real barbershop data
        real_barbers = []
        for place in places_data['results'][:15]:  # Get top 15 results
            # Get additional details for each place
            details_url = f"https://maps.googleapis.com/maps/api/place/details/json"
            details_params = {
                'place_id': place['place_id'],
                'fields': 'name,formatted_address,formatted_phone_number,opening_hours,website,price_level,rating,user_ratings_total,photos',
                'key': GOOGLE_PLACES_API_KEY
            }
            
            try:
                details_response = requests.get(details_url, params=details_params)
                details_data = details_response.json()
                
                if details_data['status'] == 'OK':
                    details = details_data['result']
                else:
                    details = {}
            except:
                details = {}
            
            # Determine specialties based on name and recommended styles
            specialties = []
            name_lower = place['name'].lower()
            
            # Match specialties based on barbershop name or type
            if 'fade' in name_lower or 'fades' in name_lower:
                specialties.append('Fade Specialist')
            if 'classic' in name_lower or 'traditional' in name_lower:
                specialties.append('Classic Cuts')
            if 'modern' in name_lower or 'style' in name_lower:
                specialties.append('Modern Styles')
            if 'beard' in name_lower:
                specialties.append('Beard Trim')
            
            # Add specialties based on recommended styles
            if recommended_styles:
                for style in recommended_styles:
                    if style and 'fade' in style.lower():
                        specialties.append('Fade Expert')
                    elif style and 'classic' in style.lower():
                        specialties.append('Classic Styles')
                    elif style and 'modern' in style.lower():
                        specialties.append('Contemporary Cuts')
            
            # Default specialties if none detected
            if not specialties:
                specialties = ['Haircut', 'Styling', 'Beard Trim']
            
            # Remove duplicates
            specialties = list(set(specialties))[:3]
            
            # Get photo URL if available
            photo_url = None
            if 'photos' in place and place['photos']:
                photo_ref = place['photos'][0].get('photo_reference')
                if photo_ref:
                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_ref}&key={GOOGLE_PLACES_API_KEY}"
            
            barber_info = {
                'id': place['place_id'],
                'name': place['name'],
                'address': details.get('formatted_address', place.get('vicinity', 'Address not available')),
                'rating': place.get('rating', 0),
                'user_ratings_total': place.get('user_ratings_total', 0),
                'price_level': place.get('price_level', 2),
                'avgCost': 25 + (place.get('price_level', 2) * 15),  # Estimate cost
                'phone': details.get('formatted_phone_number', 'Call for info'),
                'website': details.get('website', ''),
                'hours': details.get('opening_hours', {}).get('weekday_text', []),
                'open_now': place.get('opening_hours', {}).get('open_now', None),
                'photo': photo_url,
                'specialties': specialties,
                'location': {
                    'lat': place['geometry']['location']['lat'],
                    'lng': place['geometry']['location']['lng']
                },
                'recommended_for_styles': recommended_styles if recommended_styles else []
            }
            
            real_barbers.append(barber_info)
        
        # Sort by rating and number of reviews
        real_barbers.sort(key=lambda x: (x['rating'] * (min(x['user_ratings_total'], 100) / 100)), reverse=True)
        
        # Cache the results
        places_api_cache[cache_key] = {
            'data': real_barbers[:10],  # Cache top 10
            'timestamp': current_time
        }
        
        # Increment API usage
        increment_places_api_usage()
        
        logger.info(f"Found {len(real_barbers)} real barbershops in {location}")
        
        response = make_response(jsonify({
            "barbers": real_barbers[:10],  # Return top 10
            "location": location,
            "real_data": True,
            "total_found": len(real_barbers)
        }), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        logger.error(f"Error fetching real barber data: {str(e)}")
        
        # Fallback to mock data on error
        mock_barbers = getMockBarbersForLocation(location)
        response = make_response(jsonify({
            "barbers": mock_barbers, 
            "location": location,
            "mock": True,
            "error": str(e)
        }), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

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

# Subscription Packages endpoints
@app.route('/subscription-packages', methods=['GET', 'POST', 'OPTIONS'])
def handle_subscription_packages():
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response, 200
    
    if request.method == 'GET':
        limiter.limit("100 per hour")(lambda: None)()
        
        barber_id = request.args.get('barber_id', None)
        if barber_id:
            packages = [pkg for pkg in subscription_packages if pkg.get('barberId') == barber_id]
        else:
            packages = subscription_packages
        
        response = make_response(jsonify({"packages": packages}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    elif request.method == 'POST':
        limiter.limit("20 per hour")(lambda: None)()
        
        try:
            data = request.get_json()
            
            new_package = {
                "id": str(uuid.uuid4()),
                "barberId": data.get("barberId", ""),
                "barberName": data.get("barberName", ""),
                "title": data.get("title", ""),
                "description": data.get("description", ""),
                "price": data.get("price", ""),
                "numCuts": data.get("numCuts", 0),
                "durationMonths": data.get("durationMonths", 0),
                "discount": data.get("discount", ""),
                "timestamp": datetime.now().isoformat()
            }
            
            subscription_packages.append(new_package)
            
            response = make_response(jsonify({"success": True, "package": new_package}), 201)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
            
        except Exception as e:
            logger.error(f"Error creating subscription package: {str(e)}")
            response = make_response(jsonify({"error": "Failed to create package"}), 400)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response

# Client Subscriptions endpoints
@app.route('/client-subscriptions', methods=['GET', 'POST', 'OPTIONS'])
def handle_client_subscriptions():
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response, 200
    
    if request.method == 'GET':
        limiter.limit("100 per hour")(lambda: None)()
        
        client_id = request.args.get('client_id', 'current_user')
        user_subscriptions = [sub for sub in client_subscriptions if sub.get('clientId') == client_id]
        
        response = make_response(jsonify({"subscriptions": user_subscriptions}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    elif request.method == 'POST':
        limiter.limit("20 per hour")(lambda: None)()
        
        try:
            data = request.get_json()
            
            new_subscription = {
                "id": str(uuid.uuid4()),
                "clientId": data.get("clientId", "current_user"),
                "clientName": data.get("clientName", "Current User"),
                "packageId": data.get("packageId", ""),
                "packageTitle": data.get("packageTitle", ""),
                "barberId": data.get("barberId", ""),
                "barberName": data.get("barberName", ""),
                "price": data.get("price", ""),
                "numCuts": data.get("numCuts", 0),
                "remainingCuts": data.get("numCuts", 0),
                "purchaseDate": datetime.now().isoformat(),
                "expiryDate": (datetime.now() + timedelta(days=30 * data.get("durationMonths", 1))).isoformat(),
                "status": "active",
                "timestamp": datetime.now().isoformat()
            }
            
            client_subscriptions.append(new_subscription)
            
            response = make_response(jsonify({"success": True, "subscription": new_subscription}), 201)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
            
        except Exception as e:
            logger.error(f"Error creating subscription: {str(e)}")
            response = make_response(jsonify({"error": "Failed to create subscription"}), 400)
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

# Virtual Try-On endpoint using HairFastGAN approach
@app.route('/virtual-tryon', methods=['POST', 'OPTIONS'])
@limiter.limit("5 per hour")  # More restrictive for processing-heavy operations
def virtual_tryon():
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    try:
        data = request.get_json()
        
        # Get user photo (base64 encoded)
        user_photo = data.get('userPhoto', '')
        # Get reference hairstyle image URL or base64
        hairstyle_reference = data.get('hairstyleReference', '')
        style_name = data.get('styleName', '')
        
        if not user_photo:
            return jsonify({"error": "User photo required"}), 400
        
        # NOTE: In production, this would:
        # 1. Download/load the user photo
        # 2. Load or map the hairstyle reference image
        # 3. Use HairFastGAN model to apply hairstyle transfer
        # 4. Return the result image as base64
        
        # For now, return a mock response indicating the flow
        # This demonstrates the architecture without requiring full model setup
        
        response_data = {
            "success": True,
            "message": "Virtual try-on processing initiated",
            "approach": "HairFastGAN-style transfer",
            "note": "In production, this would use HairFastGAN model to transfer the hairstyle from reference to user photo",
            "mock": True
        }
        
        response = make_response(jsonify(response_data), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        logger.error(f"Error in virtual try-on endpoint: {str(e)}")
        response = make_response(jsonify({"error": "Failed to process try-on"}), 400)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

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
    app.run(host="0.0.0.0", port=port, debug=False)
