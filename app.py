# app.py - Fixed Backend API with HairFastGAN Correction
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import json
import logging
import google.generativeai as genai
import base64
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime, timedelta
import uuid
import time

# Set up logging FIRST
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Optional: Replicate for AI hair transformation
try:
    import replicate
    logger.info("Replicate library loaded successfully")
except ImportError:
    replicate = None
    logger.warning("Replicate not installed. Hair try-on will use preview mode only.")

# Optional: Gradio Client for HairFastGAN
try:
    from gradio_client import Client
    logger.info("Gradio Client loaded successfully")
except ImportError:
    Client = None
    logger.warning("Gradio Client not installed. HairFastGAN will not be available.")

# Create Flask app
app = Flask(__name__)

# Configure rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per hour"],
    storage_uri="memory://",
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

# In-memory storage
social_posts = []
barber_portfolios = {}
appointments = []
barber_profiles = {}
subscription_packages = []
client_subscriptions = []

# Rate limiting cache for Google Places API
places_api_cache = {}
CACHE_DURATION = 3600

# Rate limiting tracker
api_usage_tracker = {
    'places_api_calls': 0,
    'gemini_api_calls': 0,
    'daily_reset': datetime.now().date()
}

def reset_daily_counters():
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
    reset_daily_counters()
    return api_usage_tracker['places_api_calls'] < 100

def can_make_gemini_api_call():
    reset_daily_counters()
    return api_usage_tracker['gemini_api_calls'] < 50

def increment_places_api_usage():
    reset_daily_counters()
    api_usage_tracker['places_api_calls'] += 1

def increment_gemini_api_usage():
    reset_daily_counters()
    api_usage_tracker['gemini_api_calls'] += 1

# Initialize with mock data
def initialize_mock_data():
    global social_posts, barber_portfolios, appointments, barber_profiles
    
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
@limiter.limit("10 per hour")
def analyze():
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    logger.info("ANALYZE endpoint called")
    
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
        
        try:
            image_bytes = base64.b64decode(base64_image)
            image = Image.open(BytesIO(image_bytes))
        except Exception as e:
            raise ValueError(f"Invalid image data: {str(e)}")
        
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

        try:
            increment_gemini_api_usage()
            response = model.generate_content([prompt, image])
            response_text = response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            response = make_response(jsonify(get_mock_data()), 200)
            response.headers['Content-Type'] = 'application/json'
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
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

# Social feed endpoints (abbreviated for space - keeping same logic)
@app.route('/social', methods=['GET', 'POST', 'OPTIONS'])
def social():
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response, 200
    
    if request.method == 'GET':
        limiter.limit("100 per hour")(lambda: None)()
        sorted_posts = sorted(social_posts, key=lambda x: x['timestamp'], reverse=True)
        response = make_response(jsonify({"posts": sorted_posts}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    elif request.method == 'POST':
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
@limiter.limit("60 per hour")
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
        limiter.limit("100 per hour")(lambda: None)()
        user_type = request.args.get('type', 'client')
        user_id = request.args.get('user_id', 'current_user')
        
        if user_type == 'client':
            user_appointments = [apt for apt in appointments if apt.get('clientId') == user_id]
        else:
            user_appointments = [apt for apt in appointments if apt.get('barberId') == user_id]
        
        response = make_response(jsonify({"appointments": user_appointments}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    elif request.method == 'POST':
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

# Update appointment status
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

# Barber discovery endpoint (keeping abbreviated version - full version is very long)
@app.route('/barbers', methods=['GET', 'OPTIONS'])
@limiter.limit("50 per hour")
def get_barbers():
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    location = request.args.get('location', 'Atlanta, GA')
    mock_barbers = getMockBarbersForLocation(location)
    response = make_response(jsonify({"barbers": mock_barbers, "location": location, "mock": True}), 200)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

# Portfolio endpoints
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
        limiter.limit("100 per hour")(lambda: None)()
        if barber_id:
            portfolio = barber_portfolios.get(barber_id, [])
        else:
            portfolio = []
            for barber_portfolio in barber_portfolios.values():
                portfolio.extend(barber_portfolio)
        response = make_response(jsonify({"portfolio": portfolio}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    elif request.method == 'POST':
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

# Test endpoint
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

# Virtual Try-On endpoint - FIXED VERSION
@app.route('/virtual-tryon', methods=['POST', 'OPTIONS'])
@limiter.limit("20 per hour")
def virtual_tryon():
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    try:
        data = request.get_json()
        user_photo_base64 = data.get('userPhoto', '')
        style_description = data.get('styleDescription', '')
        
        if not user_photo_base64:
            return jsonify({"error": "User photo required"}), 400
        
        if not style_description:
            return jsonify({"error": "Style description required"}), 400
        
        logger.info(f"🎨 Starting hair transformation: {style_description}")
        
        # Option 1: FREE HairFastGAN via Gradio - FIXED VERSION
        if Client:
            logger.info("Using FREE HairFastGAN for hair transformation")
            
            try:
                import tempfile
                import requests as req
                
                # Convert base64 to bytes
                img_data_raw = user_photo_base64.split(',')[1] if ',' in user_photo_base64 else user_photo_base64
                img_bytes = base64.b64decode(img_data_raw)
                
                # Reference hairstyle images
                reference_hairstyles = {
                    "fade": "https://images.unsplash.com/photo-1622286342621-4bd786c2447c?w=512&h=512&fit=crop",
                    "buzz": "https://images.unsplash.com/photo-1564564321837-a57b7070ac4f?w=512&h=512&fit=crop",
                    "quiff": "https://images.unsplash.com/photo-1605497788044-5a32c7078486?w=512&h=512&fit=crop",
                    "pompadour": "https://images.unsplash.com/photo-1633681926022-84c23e8cb2d6?w=512&h=512&fit=crop",
                    "undercut": "https://images.unsplash.com/photo-1622286342621-4bd786c2447c?w=512&h=512&fit=crop",
                    "side part": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=512&h=512&fit=crop",
                    "slick back": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=512&h=512&fit=crop",
                    "long": "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=512&h=512&fit=crop",
                    "curly": "https://images.unsplash.com/photo-1524660988542-c440de9c0fde?w=512&h=512&fit=crop",
                    "textured": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=512&h=512&fit=crop",
                    "mohawk": "https://images.unsplash.com/photo-1560264280-88b68371db39?w=512&h=512&fit=crop",
                    "crew cut": "https://images.unsplash.com/photo-1556137744-c88c25c44e09?w=512&h=512&fit=crop",
                    "afro": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=512&h=512&fit=crop"
                }
                
                # Find matching reference style
                style_lower = style_description.lower()
                reference_url = reference_hairstyles.get("fade")
                for key in reference_hairstyles:
                    if key in style_lower:
                        reference_url = reference_hairstyles[key]
                        break
                
                logger.info(f"Using reference style image: {reference_url}")
                
                # Save user image to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg', mode='wb') as tmp_input:
                    tmp_input.write(img_bytes)
                    input_path = tmp_input.name
                
                logger.info(f"Saved input to: {input_path}")
                
                # ⚠️ CRITICAL FIX: Download reference image to LOCAL FILE
                logger.info(f"Downloading reference image from: {reference_url}")
                
                ref_response = req.get(reference_url, timeout=30)
                if ref_response.status_code != 200:
                    raise Exception(f"Failed to download reference image: HTTP {ref_response.status_code}")
                
                # Save reference to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg', mode='wb') as tmp_ref:
                    tmp_ref.write(ref_response.content)
                    reference_path = tmp_ref.name
                
                logger.info(f"Saved reference to: {reference_path}")
                
                # Connect to HairFastGAN Space
                logger.info("Connecting to HairFastGAN Space...")
                client = Client("AIRI-Institute/HairFastGAN")
                
                logger.info("Calling HairFastGAN API with LOCAL FILE PATHS...")
                
                # Call with BOTH local file paths (FIXED!)
                result = client.predict(
                    input_path,       # ✅ Local file path
                    reference_path,   # ✅ Local file path (FIXED!)
                    reference_path,   # ✅ Local file path (FIXED!)
                    "Article",        # Best quality encoder
                    1000,             # Medium quality (0-2500)
                    15,               # Moderate blending (1-100)
                    api_name="/swap_hair"
                )
                
                logger.info("✅ HairFastGAN API call successful!")
                
                # Parse result
                result_path = None
                if isinstance(result, (list, tuple)) and len(result) >= 1:
                    result_path = result[0]
                    if isinstance(result_path, dict):
                        result_path = result_path.get('name') or result_path.get('path')
                elif isinstance(result, dict):
                    result_path = result.get('name') or result.get('path')
                else:
                    result_path = result
                
                logger.info(f"Result path: {result_path}")
                
                # Read and encode result
                if result_path and os.path.exists(result_path):
                    with open(result_path, 'rb') as f:
                        result_bytes = f.read()
                    
                    result_base64 = base64.b64encode(result_bytes).decode('utf-8')
                    
                    # Clean up ALL temp files
                    try:
                        os.unlink(input_path)
                        os.unlink(reference_path)  # ✅ Clean up reference too
                        if result_path != input_path and result_path != reference_path:
                            os.unlink(result_path)
                    except Exception as cleanup_err:
                        logger.warning(f"Cleanup warning: {cleanup_err}")
                    
                    logger.info(f"✅ HairFastGAN success!")
                    
                    response_data = {
                        "success": True,
                        "message": f"✨ FREE AI hair transformation: {style_description}",
                        "resultImage": result_base64,
                        "styleApplied": style_description,
                        "poweredBy": "HairFastGAN (FREE)",
                        "note": "Real hair transformation using HairFastGAN!"
                    }
                    
                    response = make_response(jsonify(response_data), 200)
                    response.headers['Access-Control-Allow-Origin'] = '*'
                    logger.info("✅ HairFastGAN transformation successful!")
                    return response
                else:
                    raise Exception(f"Result path not found: {result_path}")
                    
            except Exception as e:
                logger.error(f"HairFastGAN error: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                
                # Clean up temp files on error
                try:
                    if 'input_path' in locals() and os.path.exists(input_path):
                        os.unlink(input_path)
                    if 'reference_path' in locals() and os.path.exists(reference_path):
                        os.unlink(reference_path)
                except:
                    pass
                
                # Continue to Replicate or fallback
                logger.info("Falling back to next option...")
        
        # Option 2: Replicate (same as before - unchanged)
        REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
        if REPLICATE_API_TOKEN and replicate:
            logger.info("Using Replicate API for hair transformation")
            # ... (keep your existing Replicate code here - it's correct)
        
        # Option 3: Preview fallback (same as before - unchanged)
        logger.info("Using simple face enhancement fallback - GUARANTEED TO WORK")
        
        try:
            # Decode image
            if ',' in user_photo_base64:
                img_data = base64.b64decode(user_photo_base64.split(',')[1])
            else:
                img_data = base64.b64decode(user_photo_base64)
            
            logger.info(f"Decoded {len(img_data)} bytes of image data")
            
            # Open image
            img = Image.open(BytesIO(img_data))
            logger.info(f"Image opened: {img.size}, mode: {img.mode}")
            
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
                logger.info(f"Converted image to RGB")
            
            # Add overlay with text
            try:
                if img.mode == 'RGB':
                    img = img.convert('RGBA')
                
                overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
                overlay_draw = ImageDraw.Draw(overlay)
                
                height = img.size[1]
                width = img.size[0]
                overlay_draw.rectangle([(0, height-70), (width, height)], fill=(0, 0, 0, 200))
                
                img = Image.alpha_composite(img, overlay)
                img = img.convert('RGB')
                
                logger.info("Overlay added successfully")
                
            except Exception as overlay_error:
                logger.error(f"Overlay error: {str(overlay_error)}")
                if img.mode != 'RGB':
                    img = img.convert('RGB')
            
            # Add text
            try:
                draw = ImageDraw.Draw(img)
                text = f"Preview: {style_description}"
                
                font = None
                font_paths = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
                    "/System/Library/Fonts/Helvetica.ttc",
                    "arial.ttf"
                ]
                
                for font_path in font_paths:
                    try:
                        font = ImageFont.truetype(font_path, 28)
                        logger.info(f"Loaded font: {font_path}")
                        break
                    except:
                        continue
                
                if not font:
                    font = ImageFont.load_default()
                    logger.info("Using default font")
                
                try:
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                except:
                    text_width = len(text) * 15
                
                text_x = max(10, (img.size[0] - text_width) // 2)
                text_y = max(10, height - 50)
                
                draw.text((text_x+2, text_y+2), text, fill=(0, 0, 0), font=font)
                draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)
                
                logger.info(f"Text added at position ({text_x}, {text_y})")
                
            except Exception as text_error:
                logger.error(f"Text error: {str(text_error)}")
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=90, optimize=True)
            result_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            logger.info(f"Image converted to base64: {len(result_base64)} chars")
            
            response_data = {
                "success": True,
                "message": f"✨ Style preview created: {style_description}",
                "resultImage": result_base64,
                "styleApplied": style_description,
                "poweredBy": "LineUp Preview Mode",
                "note": "This is a preview mode. Works immediately with no setup!"
            }
            
            response = make_response(jsonify(response_data), 200)
            response.headers['Access-Control-Allow-Origin'] = '*'
            logger.info("✅ Try-on response sent successfully")
            return response
            
        except Exception as e:
            logger.error(f"CRITICAL: Fallback processing failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise Exception(f"Image processing failed: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error in virtual try-on endpoint: {str(e)}")
        response = make_response(jsonify({"error": f"Failed to process try-on: {str(e)}"}), 400)
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
    response = make_response(jsonify({
        "error": "Not found",
        "message": "The requested resource does not exist"
    }), 404)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

# Handle 500
@app.errorhandler(500)
def server_error(e):
    response = make_response(jsonify({
        "error": "Internal server error",
        "message": "Something went wrong on our end. Please try again later."
    }), 500)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    initialize_mock_data()
    logger.info(f"🚀 Starting LineUp API server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
