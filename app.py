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
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime, timedelta
import uuid
import time
# Firebase import will be conditional

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

# Gradio Client removed - no longer using HairFastGAN

# Optional: Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, firestore, storage
    logger.info("Firebase Admin SDK loaded successfully")
    FIREBASE_AVAILABLE = True
except ImportError:
    firebase_admin = None
    firestore = None
    storage = None
    FIREBASE_AVAILABLE = False
    logger.warning("Firebase not installed. Will use in-memory storage.")

# Optional: Cloudinary for FREE image storage (25GB free tier)
try:
    import cloudinary
    import cloudinary.uploader
    CLOUDINARY_AVAILABLE = True
    logger.info("Cloudinary SDK loaded successfully")
except ImportError:
    cloudinary = None
    cloudinary_uploader = None
    CLOUDINARY_AVAILABLE = False
    logger.warning("Cloudinary not installed. Will use base64 storage.")

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

# Configure Cloudinary (FREE image storage - 25GB free tier)
cloudinary_config = None
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

if CLOUDINARY_AVAILABLE and CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    try:
        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET
        )
        cloudinary_config = cloudinary.config()
        logger.info(f"Cloudinary configured successfully: {CLOUDINARY_CLOUD_NAME}")
    except Exception as e:
        logger.warning(f"Cloudinary configuration failed: {str(e)}")
        cloudinary_config = None
else:
    if not CLOUDINARY_AVAILABLE:
        logger.info("Cloudinary not installed. Will use base64 storage.")
    elif not CLOUDINARY_CLOUD_NAME:
        logger.info("CLOUDINARY_CLOUD_NAME not set. Will use base64 storage.")
    else:
        logger.info("Cloudinary credentials not set. Will use base64 storage.")

# Configure Firebase/Firestore (for database only, not storage)
db = None
storage_bucket = None
if FIREBASE_AVAILABLE:
    try:
        # Check for Firebase credentials
        FIREBASE_CREDENTIALS = os.environ.get("FIREBASE_CREDENTIALS")
        
        if FIREBASE_CREDENTIALS:
            # Initialize with credentials from environment variable
            cred_dict = json.loads(FIREBASE_CREDENTIALS)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            # Initialize Firebase Storage bucket
            try:
                project_id = cred_dict.get('project_id')
                if project_id:
                    bucket_name = f"{project_id}.appspot.com"
                    storage_bucket = storage.bucket(bucket_name)
                    logger.info(f"Firebase Storage initialized: {bucket_name}")
            except Exception as e:
                logger.warning(f"Firebase Storage initialization failed: {str(e)}")
                storage_bucket = None
            logger.info("Firebase initialized with credentials from environment")
        else:
            logger.warning("FIREBASE_CREDENTIALS not found - will use in-memory storage")
    except Exception as e:
        logger.error(f"Firebase initialization failed: {str(e)}")
        db = None
        storage_bucket = None

# In-memory storage (fallback when database not available)
social_posts = []
barber_portfolios = {}
appointments = []
barber_profiles = {}
subscription_packages = []  # Barber subscription packages
client_subscriptions = []   # Client active subscriptions
barber_reviews = {}  # Reviews for barbers: {barber_id: [reviews]}
post_comments = {}  # Comments on posts: {post_id: [comments]}
user_follows = {}  # Follow relationships: {user_id: [followed_user_ids]}
hair_trends = {}  # AI insights on trending styles

# Rate limiting cache for Google Places API
places_api_cache = {}
CACHE_DURATION = 3600  # 1 hour cache for Places API results
MAX_CACHE_SIZE = 50  # Maximum number of cached entries to prevent memory issues

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

def clean_cache():
    """Clean expired cache entries and limit cache size"""
    global places_api_cache
    current_time = time.time()
    
    # Remove expired entries
    expired_keys = []
    for key, value in places_api_cache.items():
        if current_time - value['timestamp'] >= CACHE_DURATION:
            expired_keys.append(key)
    
    for key in expired_keys:
        del places_api_cache[key]
    
    # Limit cache size - remove oldest entries if cache is too large
    if len(places_api_cache) > MAX_CACHE_SIZE:
        # Sort by timestamp and remove oldest entries
        sorted_cache = sorted(places_api_cache.items(), key=lambda x: x[1]['timestamp'])
        entries_to_remove = len(places_api_cache) - MAX_CACHE_SIZE
        for i in range(entries_to_remove):
            del places_api_cache[sorted_cache[i][0]]
    
    if expired_keys or len(places_api_cache) > MAX_CACHE_SIZE:
        logger.info(f"Cache cleaned: removed {len(expired_keys)} expired entries, cache size: {len(places_api_cache)}")

def clear_all_cache():
    """Clear all cache entries"""
    global places_api_cache
    cache_size = len(places_api_cache)
    places_api_cache.clear()
    logger.info(f"All cache cleared: removed {cache_size} entries")
    return cache_size

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

# ========================================
# IMAGE STORAGE AND CONTENT MODERATION
# ========================================

def upload_image_to_storage(image_bytes, filename=None):
    """
    Upload image to FREE Cloudinary storage and return public URL
    Falls back to base64 if Cloudinary is not configured
    """
    # Try Cloudinary first (FREE - 25GB free tier)
    if cloudinary_config and CLOUDINARY_AVAILABLE:
        try:
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                image_bytes,
                folder="lineup-community",
                resource_type="image",
                format="jpg",
                quality="auto:good"  # Auto optimize quality
            )
            public_url = upload_result.get('secure_url') or upload_result.get('url')
            logger.info(f"Image uploaded to Cloudinary: {public_url}")
            return public_url
        except Exception as e:
            logger.error(f"Error uploading to Cloudinary: {str(e)}")
            # Fall through to return None (will use base64)
    
    # Firebase Storage fallback (optional, costs money after free tier)
    if storage_bucket:
        try:
            if not filename:
                filename = f"community-posts/{uuid.uuid4()}_{int(time.time())}.jpg"
            
            blob = storage_bucket.blob(filename)
            blob.upload_from_string(image_bytes, content_type='image/jpeg')
            blob.make_public()
            public_url = blob.public_url
            logger.info(f"Image uploaded to Firebase Storage: {filename}")
            return public_url
        except Exception as e:
            logger.error(f"Error uploading to Firebase Storage: {str(e)}")
    
    # Return None to use base64 fallback
    return None

def moderate_image_content(image_bytes):
    """
    Moderate image content using Gemini Vision API
    Returns: (is_approved, reason) tuple
    - is_approved: True if content passes moderation
    - reason: Error message if rejected, None if approved
    """
    if not model:
        logger.warning("Gemini model not available, skipping moderation (permissive mode)")
        return (True, None)
    
    try:
        # Decode image from bytes
        image = Image.open(BytesIO(image_bytes))
        
        # Moderation prompt - check for explicit content and hair-related content
        moderation_prompt = """Analyze this image and determine:
1. Is there any explicit, adult, violent, or inappropriate content? (yes/no)
2. Is this image related to hair, haircuts, hairstyles, or barber/stylist work? (yes/no)

Respond with ONLY a JSON object in this exact format (no markdown, no explanation):
{
    "explicit_content": true/false,
    "hair_related": true/false,
    "confidence": "high" | "medium" | "low"
}

If explicit_content is true, the image must be rejected.
If hair_related is false, the image must be rejected as it's not relevant to a hair/barber community."""

        increment_gemini_api_usage()
        response = model.generate_content([moderation_prompt, image])
        response_text = response.text.strip()
        
        # Parse response
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.rfind("```")
            if end > start:
                response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.rfind("```")
            if end > start:
                response_text = response_text[start:end].strip()
        
        try:
            moderation_result = json.loads(response_text)
        except json.JSONDecodeError:
            # If parsing fails, try to extract JSON from response
            import re
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                moderation_result = json.loads(json_match.group())
            else:
                logger.error(f"Failed to parse moderation response: {response_text}")
                # Permissive fallback - approve if we can't parse
                return (True, None)
        
        explicit_content = moderation_result.get("explicit_content", False)
        hair_related = moderation_result.get("hair_related", False)
        
        # Check for explicit content
        if explicit_content:
            logger.warning("Content moderation: Rejected - Explicit/inappropriate content detected")
            return (False, "Your image contains inappropriate or explicit content and cannot be posted.")
        
        # Check if hair-related
        if not hair_related:
            logger.warning("Content moderation: Rejected - Image is not hair-related")
            return (False, "Your image must be related to hair, haircuts, or hairstyles. Please post hair-related content only.")
        
        logger.info("Content moderation: Approved")
        return (True, None)
        
    except Exception as e:
        logger.error(f"Error in content moderation: {str(e)}")
        # Permissive fallback - approve if moderation fails
        return (True, None)

# ========================================
# FIREBASE/FIRESTORE DATABASE FUNCTIONS
# ========================================

def get_collection(collection_name):
    """Get Firestore collection or None if not available"""
    if db:
        return db.collection(collection_name)
    return None

def db_get_all(collection_name):
    """Get all documents from a collection"""
    if not db:
        return None
    try:
        docs = get_collection(collection_name).stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]
    except Exception as e:
        logger.error(f"Error getting all from {collection_name}: {str(e)}")
        return None

def db_get_doc(collection_name, doc_id):
    """Get a single document by ID"""
    if not db:
        return None
    try:
        doc = get_collection(collection_name).document(doc_id).get()
        if doc.exists:
            return {**doc.to_dict(), 'id': doc.id}
        return None
    except Exception as e:
        logger.error(f"Error getting doc from {collection_name}: {str(e)}")
        return None

def db_add_doc(collection_name, data, doc_id=None):
    """Add a document to a collection"""
    if not db:
        return None
    try:
        if doc_id:
            get_collection(collection_name).document(doc_id).set(data)
            return {**data, 'id': doc_id}
        else:
            doc_ref = get_collection(collection_name).add(data)[1]
            return {**data, 'id': doc_ref.id}
    except Exception as e:
        logger.error(f"Error adding doc to {collection_name}: {str(e)}")
        return None

def db_update_doc(collection_name, doc_id, data):
    """Update a document"""
    if not db:
        return False
    try:
        get_collection(collection_name).document(doc_id).update(data)
        return True
    except Exception as e:
        logger.error(f"Error updating doc in {collection_name}: {str(e)}")
        return False

def db_delete_doc(collection_name, doc_id):
    """Delete a document"""
    if not db:
        return False
    try:
        get_collection(collection_name).document(doc_id).delete()
        return True
    except Exception as e:
        logger.error(f"Error deleting doc from {collection_name}: {str(e)}")
        return False

def db_query(collection_name, field, operator, value):
    """Query a collection"""
    if not db:
        return []
    try:
        docs = get_collection(collection_name).where(field, operator, value).stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]
    except Exception as e:
        logger.error(f"Error querying {collection_name}: {str(e)}")
        return []

# ========================================
# END DATABASE FUNCTIONS
# ========================================

# Initialize with mock data
def initialize_mock_data():
    global social_posts, barber_portfolios, appointments, barber_profiles, barber_reviews, post_comments, user_follows, hair_trends
    
    # Mock social posts with hashtags and engagement metrics
    social_posts = [
        {
            "id": "1",
            "username": "mike_style",
            "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop&crop=face",
            "image": "https://images.unsplash.com/photo-1622296089863-eb7fc530daa8?w=400&h=400&fit=crop",
            "caption": "Fresh fade from @atlanta_cuts 🔥 #fade #haircut",
            "likes": 23,
            "shares": 5,
            "comments": 8,
            "timeAgo": "2h",
            "liked": False,
            "timestamp": datetime.now().isoformat(),
            "hashtags": ["fade", "haircut", "barberlife"]
        },
        {
            "id": "2", 
            "username": "sarah_hair",
            "avatar": "https://images.unsplash.com/photo-1494790108755-2616b612b786?w=100&h=100&fit=crop&crop=face",
            "image": "https://images.unsplash.com/photo-1605497788044-5a32c7078486?w=400&h=400&fit=crop",
            "caption": "New bob cut! Love how it frames my face ✨ #bob #hairstyle",
            "likes": 45,
            "shares": 12,
            "comments": 15,
            "timeAgo": "4h",
            "liked": True,
            "timestamp": (datetime.now() - timedelta(hours=4)).isoformat(),
            "hashtags": ["bob", "hairstyle", "freshcut"]
        }
    ]
    
    # Mock reviews for barbers
    barber_reviews = {
        "barber_1": [
            {"id": "r1", "username": "john_doe", "rating": 5, "text": "Best fade I've ever had! Mike is a true artist.", "date": "2024-01-18"},
            {"id": "r2", "username": "jane_smith", "rating": 5, "text": "Professional service, clean cuts every time.", "date": "2024-01-15"},
            {"id": "r3", "username": "alex_taylor", "rating": 4, "text": "Great barber, just sometimes a bit crowded on weekends.", "date": "2024-01-10"}
        ],
        "barber_2": [
            {"id": "r4", "username": "sam_jones", "rating": 4, "text": "Good quality work, friendly staff.", "date": "2024-01-17"}
        ]
    }
    
    # Mock comments on posts
    post_comments = {
        "1": [
            {"id": "c1", "username": "alex_taylor", "text": "Looking sharp! 🔥", "timeAgo": "1h"},
            {"id": "c2", "username": "john_doe", "text": "What's the fade number?", "timeAgo": "30m"}
        ],
        "2": [
            {"id": "c3", "username": "mike_style", "text": "Beautiful cut!", "timeAgo": "3h"}
        ]
    }
    
    # Mock follow relationships
    user_follows = {
        "current_user": ["mike_style", "sarah_hair"],
        "mike_style": ["sarah_hair", "jason_cuts"]
    }
    
    # Mock hair trends/insights
    hair_trends = {
        "trending_styles": ["textured crop", "modern fade", "curtain bangs", "buzz cut", "pompadour"],
        "trending_hashtags": ["#fade", "#haircut", "#barberlife", "#freshcut", "#hairstyle"],
        "popular_colors": ["natural", "blonde highlights", "dark brown", "black"],
        "seasonal_tips": "This winter, textured crops and fades are trending. Consider volume on top with short sides for a modern look."
    }
    
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
            "user_ratings_total": 127,
            "avgCost": 45,
            "address": f"Downtown {location.split(',')[0]}",
            "photo": "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=400&h=300&fit=crop",
            "phone": "(555) 123-4567",
            "website": "https://elitecuts.example.com",
            "google_maps_url": "https://www.google.com/maps/search/?api=1&query=33.7490,-84.3880",
            "hours": "Mon-Sat 9AM-8PM"
        },
        {
            "id": "barber_2", 
            "name": f"The {location.split(',')[0]} Barber",
            "specialties": ["Pompadour", "Buzz Cut", "Beard Trim"],
            "rating": 4.8,
            "user_ratings_total": 89,
            "avgCost": 55,
            "address": f"Uptown {location.split(',')[0]}",
            "photo": "https://images.unsplash.com/photo-1585747860715-2ba37e788b70?w=400&h=300&fit=crop",
            "phone": "(555) 123-4568",
            "website": "",
            "google_maps_url": "https://www.google.com/maps/search/?api=1&query=33.7490,-84.3880",
            "hours": "Tue-Sun 10AM-7PM"
        },
        {
            "id": "barber_3",
            "name": f"{location.split(',')[0]} Style Studio",
            "specialties": ["Modern Fade", "Beard Trim", "Styling"],
            "rating": 4.9,
            "user_ratings_total": 156,
            "avgCost": 65,
            "address": f"Midtown {location.split(',')[0]}",
            "photo": "https://images.unsplash.com/photo-1605497788044-5a32c7078486?w=400&h=300&fit=crop",
            "phone": "(555) 123-4569",
            "website": "https://stylestudio.example.com",
            "google_maps_url": "https://www.google.com/maps/search/?api=1&query=33.7490,-84.3880",
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
@app.route('/clear-cache', methods=['POST', 'GET', 'OPTIONS'])
@limiter.limit("10 per hour")  # Limit cache clearing to prevent abuse
def clear_cache():
    """Clear all cache entries to free memory"""
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response, 200
    
    try:
        cleared_count = clear_all_cache()
        response = make_response(jsonify({
            "success": True,
            "message": f"Cache cleared successfully",
            "entries_removed": cleared_count,
            "cache_size": len(places_api_cache),
            "timestamp": datetime.now().isoformat()
        }), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        response = make_response(jsonify({
            "success": False,
            "error": str(e)
        }), 500)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

@app.route('/cache-stats', methods=['GET', 'OPTIONS'])
@limiter.limit("50 per hour")
def cache_stats():
    """Get cache statistics"""
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    # Clean cache first
    clean_cache()
    
    current_time = time.time()
    expired_count = sum(1 for v in places_api_cache.values() if current_time - v['timestamp'] >= CACHE_DURATION)
    
    response = make_response(jsonify({
        "cache_size": len(places_api_cache),
        "max_cache_size": MAX_CACHE_SIZE,
        "cache_duration_seconds": CACHE_DURATION,
        "expired_entries": expired_count,
        "memory_usage_estimate_kb": len(places_api_cache) * 10  # Rough estimate
    }), 200)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

@app.route('/health', methods=['GET'])
@limiter.limit("200 per minute")
def health():
    reset_daily_counters()
    # Clean cache on health check
    clean_cache()
    return jsonify({
        "status": "healthy",
        "service": "lineup-backend",
        "timestamp": datetime.now().isoformat(),
        "cors_enabled": True,
        "gemini_configured": model is not None,
        "places_api_configured": bool(os.environ.get("GOOGLE_PLACES_API_KEY")),
        "cache_size": len(places_api_cache),
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
        
        # Try to get from database, fallback to in-memory
        if db:
            posts = db_get_all('social_posts') or []
        else:
            posts = social_posts
        
        # Return social posts sorted by timestamp
        sorted_posts = sorted(posts, key=lambda x: x['timestamp'], reverse=True)
        response = make_response(jsonify({"posts": sorted_posts}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    elif request.method == 'POST':
        # Stricter rate limit for POST requests
        limiter.limit("20 per hour")(lambda: None)()
        
        try:
            data = request.get_json()
            image_base64 = data.get("image", "")
            
            if not image_base64:
                response = make_response(jsonify({
                    "success": False,
                    "error": "Image is required"
                }), 400)
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response
            
            # Decode base64 image
            try:
                # Remove data URL prefix if present
                if ',' in image_base64:
                    image_base64 = image_base64.split(',')[1]
                
                image_bytes = base64.b64decode(image_base64)
                
                # Validate image
                try:
                    img = Image.open(BytesIO(image_bytes))
                    img.verify()
                except Exception as e:
                    logger.error(f"Invalid image format: {str(e)}")
                    response = make_response(jsonify({
                        "success": False,
                        "error": "Invalid image format. Please upload a valid image."
                    }), 400)
                    response.headers['Access-Control-Allow-Origin'] = '*'
                    return response
                
                # Re-open image after verification (verify() closes it)
                image_bytes = base64.b64decode(image_base64.split(',')[-1] if ',' in image_base64 else image_base64)
                
            except Exception as e:
                logger.error(f"Error decoding image: {str(e)}")
                response = make_response(jsonify({
                    "success": False,
                    "error": "Failed to process image. Please try again."
                }), 400)
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response
            
            # Content moderation - check for explicit and non-hair-related content
            is_approved, rejection_reason = moderate_image_content(image_bytes)
            
            if not is_approved:
                response = make_response(jsonify({
                    "success": False,
                    "error": "Content rejected",
                    "reason": rejection_reason
                }), 403)
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response
            
            # Upload image to Cloudinary (FREE) or Firebase Storage, or keep base64
            image_url = upload_image_to_storage(image_bytes)
            
            # Use storage URL if available, otherwise use base64
            final_image = image_url if image_url else image_base64
            
            new_post = {
                "username": data.get("username", "anonymous"),
                "avatar": data.get("avatar", "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&h=100&fit=crop&crop=face"),
                "image": final_image,
                "caption": data.get("caption", ""),
                "likes": 0,
                "timeAgo": "now",
                "liked": False,
                "timestamp": datetime.now().isoformat(),
                "shares": 0,
                "comments": 0,
                "hashtags": data.get("hashtags", []),
                "stored_in_storage": bool(image_url)  # Track if using storage
            }
            
            # Try to save to database, fallback to in-memory
            if db:
                result = db_add_doc('social_posts', new_post)
                new_post['id'] = result['id'] if result else str(uuid.uuid4())
            else:
                new_post['id'] = str(uuid.uuid4())
            social_posts.insert(0, new_post)
            
            logger.info(f"Social post created successfully: {new_post['id']}")
            response = make_response(jsonify({"success": True, "post": new_post}), 201)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
            
        except Exception as e:
            logger.error(f"Error creating social post: {str(e)}")
            response = make_response(jsonify({
                "success": False,
                "error": "Failed to create post",
                "details": str(e) if logger.level == logging.DEBUG else None
            }), 400)
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
        # Try to get post from database first, then fallback to in-memory
        post = None
        if db:
            post_doc = db_get_doc('social_posts', post_id)
            if post_doc:
                post = post_doc
        
        # Fallback to in-memory if not in database
        if not post:
            post = next((p for p in social_posts if str(p.get("id")) == str(post_id)), None)
        
        if not post:
            response = make_response(jsonify({"error": "Post not found"}), 404)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        # Toggle like
        current_liked = post.get("liked", False)
        new_liked = not current_liked
        current_likes = post.get("likes", 0)
        new_likes = current_likes + (1 if new_liked else -1)
        
        # Update post
        post["liked"] = new_liked
        post["likes"] = max(0, new_likes)  # Ensure likes don't go negative
        
        # Save to database if using database
        if db:
            db_update_doc('social_posts', post_id, {
                "liked": new_liked,
                "likes": post["likes"]
            })
        
        response = make_response(jsonify({
            "success": True, 
            "liked": new_liked, 
            "likes": post["likes"]
        }), 200)
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
    
    # Clean cache before checking
    clean_cache()
    
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
            
            # Generate Google Maps URL from coordinates
            lat = place['geometry']['location']['lat']
            lng = place['geometry']['location']['lng']
            google_maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
            
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
                'google_maps_url': google_maps_url,
                'hours': details.get('opening_hours', {}).get('weekday_text', []),
                'open_now': place.get('opening_hours', {}).get('open_now', None),
                'photo': photo_url,
                'specialties': specialties,
                'location': {
                    'lat': lat,
                    'lng': lng
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

# Virtual Try-On endpoint using Replicate (FREE tier available!)
@app.route('/virtual-tryon', methods=['POST', 'OPTIONS'])
@limiter.limit("20 per hour")  # Reasonable limit for GPU processing
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
        user_photo_base64 = data.get('userPhoto', '')
        # Text description of desired hairstyle
        style_description = data.get('styleDescription', '')
        
        if not user_photo_base64:
            return jsonify({"error": "User photo required"}), 400
        
        if not style_description:
            return jsonify({"error": "Style description required"}), 400
        
        logger.info(f"🎨 Starting hair transformation: {style_description}")
        
        # Try Replicate first, then fallback to preview mode
        REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
        
        # Option 1: Replicate (Paid but better quality)
        # Using flux-kontext-apps/change-haircut - FLUX.1 Kontext model for hair transformations
        if REPLICATE_API_TOKEN and replicate:
            logger.info("Using Replicate API for REAL hair style transformation")
            
            # Set the API token for replicate
            os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN
            
            try:
                # Convert base64 to data URI for Replicate
                img_data_raw = user_photo_base64.split(',')[1] if ',' in user_photo_base64 else user_photo_base64
                face_data_uri = f"data:image/jpeg;base64,{img_data_raw}"
                
                logger.info(f"Starting hair style transformation: {style_description}")
                
                # List of ALL allowed haircut values from the Replicate model
                ALLOWED_HAIRCUTS = [
                    "No change", "Random", "Straight", "Wavy", "Curly", "Bob", "Pixie Cut",
                    "Layered", "Messy Bun", "High Ponytail", "Low Ponytail", "Braided Ponytail",
                    "French Braid", "Dutch Braid", "Fishtail Braid", "Space Buns", "Top Knot",
                    "Undercut", "Mohawk", "Crew Cut", "Faux Hawk", "Slicked Back", "Side-Parted",
                    "Center-Parted", "Blunt Bangs", "Side-Swept Bangs", "Shag", "Lob",
                    "Angled Bob", "A-Line Bob", "Asymmetrical Bob", "Graduated Bob", "Inverted Bob",
                    "Layered Shag", "Choppy Layers", "Razor Cut", "Perm", "Ombré", "Straightened",
                    "Soft Waves", "Glamorous Waves", "Hollywood Waves", "Finger Waves", "Tousled",
                    "Feathered", "Pageboy", "Pigtails", "Pin Curls", "Rollerset", "Twist Out",
                    "Bantu Knots", "Dreadlocks", "Cornrows", "Box Braids", "Crochet Braids",
                    "Double Dutch Braids", "French Fishtail Braid", "Waterfall Braid", "Rope Braid",
                    "Heart Braid", "Halo Braid", "Crown Braid", "Braided Crown", "Bubble Braid",
                    "Bubble Ponytail", "Ballerina Braids", "Milkmaid Braids", "Bohemian Braids",
                    "Flat Twist", "Crown Twist", "Twisted Bun", "Twisted Half-Updo", "Twist and Pin Updo",
                    "Chignon", "Simple Chignon", "Messy Chignon", "French Twist", "French Twist Updo",
                    "French Roll", "Updo", "Messy Updo", "Knotted Updo", "Ballerina Bun",
                    "Banana Clip Updo", "Beehive", "Bouffant", "Hair Bow", "Half-Up Top Knot",
                    "Half-Up, Half-Down", "Messy Bun with a Headband", "Messy Bun with a Scarf",
                    "Messy Fishtail Braid", "Sideswept Pixie", "Mohawk Fade", "Zig-Zag Part", "Victory Rolls"
                ]
                
                # Try to use Gemini to find the best match
                haircut_name = None
                if model:
                    try:
                        logger.info("Using Gemini to find best matching haircut...")
                        
                        # Create a more structured prompt with context
                        prompt = f"""You are a professional hairstylist matching haircut descriptions to specific style names.

TASK: Match this haircut description to the BEST option from the allowed list below.

HAIRCUT DESCRIPTION: "{style_description}"

ALLOWED STYLES (choose ONE exact match):
{', '.join(ALLOWED_HAIRCUTS)}

MATCHING RULES:
1. **Fade styles** → "Mohawk Fade" (for any fade: classic fade, modern fade, taper fade, etc.)
2. **Parted styles** → "Side-Parted" (for side part, side part with volume, side-swept, etc.) OR "Center-Parted" (for center part, middle part)
3. **Slicked/Quiff/Pompadour** → "Slicked Back" (for quiff, pompadour, slick back, swept back, etc.)
4. **Short/Buzz** → "Crew Cut" (for buzz cut, crew cut, short cut, military cut)
5. **Undercut** → "Undercut" (for undercut, disconnected undercut)
6. **Mohawk** → "Mohawk" (for mohawk, faux hawk) OR "Mohawk Fade" (if it mentions fade)
7. **Long hair** → "Half-Up, Half-Down" (for long hair, shoulder length, etc.)
8. **Curly/Afro** → "Curly" (for curly, afro, natural curls)
9. **Wavy** → "Wavy" (for wavy, soft waves) OR "Soft Waves" (if specifically soft)
10. **Straight** → "Straight" (for straight, straightened)
11. **Textured/Messy** → "Tousled" (for textured, messy, tousled, messy crop)
12. **Bob styles** → "Bob" (for bob, classic bob) OR "Lob" (for long bob)
13. **Pixie** → "Pixie Cut" (for pixie, pixie cut, bowl cut)
14. **Bun/Top Knot** → "Top Knot" (for man bun, top knot, bun) OR "Messy Bun" (if messy)
15. **Layered** → "Layered" (for layered, layers, layered cut)
16. **Dreadlocks** → "Dreadlocks" (for dreadlocks, dreads)

EXAMPLES:
- "Side Part with Volume" → "Side-Parted"
- "Classic Fade" → "Mohawk Fade"
- "Textured Quiff" → "Slicked Back"
- "Modern Fade" → "Mohawk Fade"
- "Messy Crop" → "Tousled"
- "Buzz Cut" → "Crew Cut"
- "Undercut" → "Undercut"

CRITICAL: Return ONLY the exact name from the list above. No explanations, no quotes, just the exact name."""
                        
                        gemini_response = model.generate_content(prompt)
                        gemini_match = gemini_response.text.strip().strip('"').strip("'").strip('`')
                        
                        # Clean up common Gemini response patterns
                        gemini_match = gemini_match.split('\n')[0].strip()  # Take first line only
                        gemini_match = gemini_match.replace('**', '').replace('*', '')  # Remove markdown
                        
                        # Verify it's in the allowed list
                        if gemini_match in ALLOWED_HAIRCUTS:
                            haircut_name = gemini_match
                            logger.info(f"Gemini matched '{style_description}' to '{haircut_name}'")
                        else:
                            # Try fuzzy matching - check if any allowed style contains the match or vice versa
                            gemini_lower = gemini_match.lower()
                            for allowed in ALLOWED_HAIRCUTS:
                                if gemini_lower == allowed.lower() or gemini_lower in allowed.lower() or allowed.lower() in gemini_lower:
                                    haircut_name = allowed
                                    logger.info(f"Gemini fuzzy matched '{style_description}' to '{haircut_name}' (via '{gemini_match}')")
                                    break
                            
                            if not haircut_name:
                                logger.warning(f"Gemini returned '{gemini_match}' which is not in allowed list, using fallback")
                    except Exception as gemini_error:
                        logger.warning(f"Gemini matching failed: {str(gemini_error)}, using fallback mapping")
                
                # Fallback: Use keyword-based mapping if Gemini not available or failed
                if not haircut_name:
                    logger.info("Using keyword-based fallback mapping...")
                    style_map = {
                    # Fade styles
                    "fade": "Mohawk Fade",
                    "modern fade": "Mohawk Fade",
                    "fade with": "Mohawk Fade",
                    
                    # Short styles
                    "buzz": "Crew Cut",
                    "buzz cut": "Crew Cut",
                    "crew cut": "Crew Cut",
                    "crewcut": "Crew Cut",
                    "short": "Crew Cut",
                    
                    # Slicked/Quiff/Pompadour
                    "quiff": "Slicked Back",
                    "pompadour": "Slicked Back",
                    "slick back": "Slicked Back",
                    "slicked back": "Slicked Back",
                    "slickback": "Slicked Back",
                    
                    # Parted styles - MUST be "Side-Parted" with hyphen
                    "side part": "Side-Parted",
                    "side-part": "Side-Parted",
                    "sidepart": "Side-Parted",
                    "side parted": "Side-Parted",
                    "parted": "Side-Parted",
                    "volume": "Side-Parted",  # For "Side Part with Volume"
                    "with volume": "Side-Parted",
                    
                    # Undercut
                    "undercut": "Undercut",
                    
                    # Mohawk
                    "mohawk": "Mohawk",
                    
                    # Long styles
                    "long": "Half-Up, Half-Down",
                    "long hair": "Half-Up, Half-Down",
                    
                    # Texture/Curly
                    "curly": "Curly",
                    "textured": "Tousled",
                    "messy": "Tousled",
                    "tousled": "Tousled",
                    "afro": "Curly",
                    
                    # Wavy/Straight
                    "wavy": "Wavy",
                    "waves": "Wavy",
                    "soft waves": "Soft Waves",
                    "straight": "Straight",
                    "straightened": "Straightened",
                    
                    # Bob styles
                    "bob": "Bob",
                    "lob": "Lob",
                    "a-line bob": "A-Line Bob",
                    
                    # Pixie
                    "pixie": "Pixie Cut",
                    "pixie cut": "Pixie Cut",
                    "bowl cut": "Pixie Cut",
                    
                    # Bun/Top Knot
                    "man bun": "Top Knot",
                    "bun": "Top Knot",
                    "top knot": "Top Knot",
                    "messy bun": "Messy Bun",
                    
                    # Layered
                    "layered": "Layered",
                    "layers": "Layered",
                    
                    # Dreadlocks
                    "dreadlocks": "Dreadlocks",
                    "dreads": "Dreadlocks",
                    
                    # Center part
                    "center part": "Center-Parted",
                    "center-part": "Center-Parted",
                    "centerpart": "Center-Parted"
                    }
                    
                    # Get the best matching haircut name from the model's allowed list
                    style_lower = style_description.lower().strip()
                    if not haircut_name:
                        haircut_name = "Random"  # Default fallback - model accepts this
                    
                    # Check for exact keyword matches first (longest matches first)
                    # Sort by key length descending to match longer phrases first
                    sorted_keys = sorted(style_map.keys(), key=len, reverse=True)
                    for key in sorted_keys:
                        if key in style_lower:
                            haircut_name = style_map[key]
                            break
                    
                    logger.info(f"Fallback mapping matched '{style_description}' to '{haircut_name}'")
                
                logger.info(f"Using haircut style: {haircut_name} (from description: {style_description})")
                
                # Use flux-kontext-apps/change-haircut model
                # This model uses FLUX.1 Kontext for text-guided hair editing
                # Version: 48f03523665cabe9a2e832ea9cc2d7c30ad5079cb5f1c1f07890d40596fe1f87
                # Use replicate.run() - it handles polling internally
                # Note: If it takes >30 seconds, the Gunicorn worker will timeout
                # In that case, it will fall back to preview mode automatically
                logger.info("Calling Replicate API (this may take 10-30 seconds)...")
                output = replicate.run(
                    "flux-kontext-apps/change-haircut:48f03523665cabe9a2e832ea9cc2d7c30ad5079cb5f1c1f07890d40596fe1f87",
                    input={
                        "input_image": face_data_uri,
                        "haircut": haircut_name,
                        "aspect_ratio": "match_input_image",
                        "output_format": "png",
                        "safety_tolerance": 2
                    }
                )
                
                logger.info(f"Replicate API call completed")
                logger.info(f"Output type: {type(output)}")
                
                # Handle different output types from Replicate prediction
                result_url = None
                
                if output:
                    # Try multiple ways to extract the URL
                    if isinstance(output, str):
                        result_url = output
                        logger.info(f"Output is string URL: {result_url}")
                    elif isinstance(output, list) and len(output) > 0:
                        result_url = output[0]  # First element in list
                        logger.info(f"Output is list, first item: {result_url}")
                    elif hasattr(output, '__iter__') and not isinstance(output, str):
                        try:
                            output_list = list(output)
                            if output_list and len(output_list) > 0:
                                result_url = output_list[0]
                                logger.info(f"Output is iterator, first item: {result_url}")
                        except Exception as iter_error:
                            logger.error(f"Error iterating output: {str(iter_error)}")
                    else:
                        result_url = str(output)
                        logger.info(f"Output converted to string: {result_url}")
                
                if not result_url:
                    logger.error(f"No result URL found in output. Output type: {type(output)}, Output: {output}")
                    raise Exception("Model produced no output URL")
                
                # Download and verify the result
                logger.info(f"Downloading result from: {result_url}")
                import requests as req
                
                try:
                    result_response = req.get(result_url, timeout=60)  # Longer timeout for large images
                    logger.info(f"Download response status: {result_response.status_code}")
                    
                    if result_response.status_code == 200:
                        # Verify it's an image
                        content_type = result_response.headers.get('content-type', '')
                        logger.info(f"Content type: {content_type}")
                        
                        if 'image' not in content_type.lower() and len(result_response.content) < 1000:
                            logger.error(f"Downloaded content doesn't appear to be an image: {result_response.content[:200]}")
                            raise Exception("Invalid image data from model")
                        
                        result_base64 = base64.b64encode(result_response.content).decode('utf-8')
                        logger.info(f"Image converted to base64: {len(result_base64)} chars")
                        
                        # Also include original image for before/after comparison
                        original_base64 = user_photo_base64.split(',')[1] if ',' in user_photo_base64 else user_photo_base64
                        
                        response_data = {
                            "success": True,
                            "message": f"✨ Real AI hair transformation complete: {style_description}",
                            "originalImage": original_base64,
                            "resultImage": result_base64,
                            "styleApplied": style_description,
                            "poweredBy": "Replicate FLUX.1 Kontext (Change-Haircut AI)",
                            "note": "This is a real AI transformation!"
                        }
                        
                        response = make_response(jsonify(response_data), 200)
                        response.headers['Access-Control-Allow-Origin'] = '*'
                        logger.info("✅ AI hair transformation successful!")
                        return response
                    else:
                        logger.error(f"Failed to download result: HTTP {result_response.status_code}")
                        logger.error(f"Response: {result_response.text[:500]}")
                        raise Exception(f"Failed to download result: {result_response.status_code}")
                
                except req.exceptions.Timeout:
                    logger.error("Download timeout after 60 seconds")
                    raise Exception("Result download timed out")
                except Exception as download_error:
                    logger.error(f"Download error: {str(download_error)}")
                    raise
                    
            except Exception as e:
                logger.error(f"Replicate hair style transfer error: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                # Continue to fallback preview mode
        
        # PREVIEW MODE: Return user photo with text overlay
        logger.info("Using preview mode - user photo with text overlay - GUARANTEED TO WORK")
        
        try:
            # Decode image - handle both formats
            try:
                # Remove data URI prefix if present
                if ',' in user_photo_base64:
                    img_data = base64.b64decode(user_photo_base64.split(',')[1])
                else:
                    img_data = base64.b64decode(user_photo_base64)
                
                logger.info(f"Decoded {len(img_data)} bytes of image data")
            except Exception as decode_error:
                logger.error(f"Base64 decode error: {str(decode_error)}")
                raise Exception(f"Invalid image data: {str(decode_error)}")
            
            # Open image
            try:
                img = Image.open(BytesIO(img_data))
                logger.info(f"Image opened: {img.size}, mode: {img.mode}")
                
                # Convert to RGB if needed
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                    logger.info(f"Converted image to RGB")
                    
            except Exception as img_error:
                logger.error(f"Image open error: {str(img_error)}")
                raise Exception(f"Cannot process image: {str(img_error)}")
            
            # Add overlay with text
            try:
                # Convert to RGBA for overlay
                if img.mode == 'RGB':
                    img = img.convert('RGBA')
                
                # Create overlay
                overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
                overlay_draw = ImageDraw.Draw(overlay)
                
                # Draw semi-transparent rectangle at bottom
                height = img.size[1]
                width = img.size[0]
                overlay_draw.rectangle([(0, height-70), (width, height)], fill=(0, 0, 0, 200))
                
                # Composite overlay onto image
                img = Image.alpha_composite(img, overlay)
                
                # Convert back to RGB for JPEG
                img = img.convert('RGB')
                
                logger.info("Overlay added successfully")
                
            except Exception as overlay_error:
                logger.error(f"Overlay error: {str(overlay_error)}")
                # Continue without overlay
                if img.mode != 'RGB':
                    img = img.convert('RGB')
            
            # Add text
            try:
                draw = ImageDraw.Draw(img)
                text = f"Preview: {style_description}"
                
                # Try multiple font paths
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
                    # Use default font as last resort
                    font = ImageFont.load_default()
                    logger.info("Using default font")
                
                # Calculate text position (centered)
                try:
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                except:
                    # Fallback if textbbox not available
                    text_width = len(text) * 15
                
                text_x = max(10, (img.size[0] - text_width) // 2)
                text_y = max(10, height - 50)
                
                # Add text with shadow for better visibility
                draw.text((text_x+2, text_y+2), text, fill=(0, 0, 0), font=font)  # Shadow
                draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)  # Text
                
                logger.info(f"Text added at position ({text_x}, {text_y})")
                
            except Exception as text_error:
                logger.error(f"Text error: {str(text_error)}")
                # Continue without text - image is still valid
            
            # Convert to base64
            try:
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=90, optimize=True)
                result_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                logger.info(f"Image converted to base64: {len(result_base64)} chars")
                
            except Exception as save_error:
                logger.error(f"Save error: {str(save_error)}")
                raise Exception(f"Cannot save image: {str(save_error)}")
            
            # Also include original image for before/after comparison
            original_base64 = user_photo_base64.split(',')[1] if ',' in user_photo_base64 else user_photo_base64
            
            # Return success response
            response_data = {
                "success": True,
                "message": f"✨ Style preview created: {style_description}",
                "originalImage": original_base64,
                "resultImage": result_base64,
                "styleApplied": style_description,
                "poweredBy": "LineUp Preview Mode",
                "note": "This is a preview mode. Works immediately with no setup!"
                }
                
                response = make_response(jsonify(response_data), 200)
                response.headers['Access-Control-Allow-Origin'] = '*'
            logger.info("✅ Preview mode response sent successfully")
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

# ============================================================
# NEW FEATURES: Reviews, Comments, Follows, AI Insights
# ============================================================

# Review endpoints for barbers
@app.route('/barbers/<barber_id>/reviews', methods=['GET', 'POST', 'OPTIONS'])
@limiter.limit("50 per hour")
def handle_reviews(barber_id):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response, 200
    
    if request.method == 'GET':
        reviews = barber_reviews.get(barber_id, [])
        avg_rating = sum(r['rating'] for r in reviews) / len(reviews) if reviews else 0
        response = make_response(jsonify({
            "reviews": reviews,
            "total_reviews": len(reviews),
            "average_rating": round(avg_rating, 1)
        }), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            new_review = {
                "id": str(uuid.uuid4()),
                "username": data.get("username", "anonymous"),
                "rating": data.get("rating", 5),
                "text": data.get("text", ""),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "timestamp": datetime.now().isoformat()
            }
            
            if barber_id not in barber_reviews:
                barber_reviews[barber_id] = []
            barber_reviews[barber_id].append(new_review)
            
            response = make_response(jsonify({"success": True, "review": new_review}), 201)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            logger.error(f"Error creating review: {str(e)}")
            response = make_response(jsonify({"error": "Failed to create review"}), 400)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response

# Comment endpoints for social posts
@app.route('/social/<post_id>/comments', methods=['GET', 'POST', 'OPTIONS'])
@limiter.limit("60 per hour")
def handle_comments(post_id):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response, 200
    
    if request.method == 'GET':
        # Try to get comments from database first
        comments = []
        if db:
            comments_doc = db_get_doc('post_comments', post_id)
            if comments_doc and 'comments' in comments_doc:
                comments = comments_doc['comments']
        
        # Fallback to in-memory
        if not comments:
            comments = post_comments.get(post_id, [])
        
        response = make_response(jsonify({"comments": comments}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            new_comment = {
                "id": str(uuid.uuid4()),
                "username": data.get("username", "anonymous"),
                "text": data.get("text", ""),
                "timeAgo": "just now",
                "timestamp": datetime.now().isoformat()
            }
            
            # Get existing comments
            comments = []
            if db:
                comments_doc = db_get_doc('post_comments', post_id)
                if comments_doc and 'comments' in comments_doc:
                    comments = comments_doc['comments']
            
            if not comments:
                comments = post_comments.get(post_id, [])
            
            # Add new comment
            comments.append(new_comment)
            
            # Save to database if using database
            if db:
                db_add_doc('post_comments', {"comments": comments}, doc_id=post_id)
            else:
                post_comments[post_id] = comments
            
            # Update comment count on post
            post = None
            if db:
                post = db_get_doc('social_posts', post_id)
            
            if not post:
                post = next((p for p in social_posts if str(p.get("id")) == str(post_id)), None)
            
            if post:
                current_comments = post.get("comments", 0)
                post["comments"] = current_comments + 1
                
                # Update in database
                if db:
                    db_update_doc('social_posts', post_id, {
                        "comments": post["comments"]
                    })
            
            response = make_response(jsonify({"success": True, "comment": new_comment}), 201)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            logger.error(f"Error creating comment: {str(e)}")
            response = make_response(jsonify({"error": "Failed to create comment"}), 400)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response

# Follow/unfollow endpoints
@app.route('/users/<user_id>/follow', methods=['POST', 'OPTIONS'])
@app.route('/users/<user_id>/unfollow', methods=['POST', 'OPTIONS'])
@limiter.limit("100 per hour")
def toggle_follow(user_id):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    try:
        data = request.get_json()
        follower_id = data.get("follower_id", "current_user")
        
        if request.path.endswith('/follow'):
            if follower_id not in user_follows:
                user_follows[follower_id] = []
            if user_id not in user_follows[follower_id]:
                user_follows[follower_id].append(user_id)
        else:  # unfollow
            if follower_id in user_follows:
                user_follows[follower_id] = [uid for uid in user_follows[follower_id] if uid != user_id]
        
        response = make_response(jsonify({"success": True}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error toggling follow: {str(e)}")
        response = make_response(jsonify({"error": "Failed to toggle follow"}), 400)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

# Share post endpoint
@app.route('/social/<post_id>/share', methods=['POST', 'OPTIONS'])
@limiter.limit("100 per hour")
def share_post(post_id):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    try:
        # Try to get post from database first, then fallback to in-memory
        post = None
        if db:
            post_doc = db_get_doc('social_posts', post_id)
            if post_doc:
                post = post_doc
        
        # Fallback to in-memory if not in database
        if not post:
            post = next((p for p in social_posts if str(p.get("id")) == str(post_id)), None)
        
        if not post:
            response = make_response(jsonify({"error": "Post not found"}), 404)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        current_shares = post.get("shares", 0)
        post["shares"] = current_shares + 1
        
        # Save to database if using database
        if db:
            db_update_doc('social_posts', post_id, {
                "shares": post["shares"]
            })
        
        response = make_response(jsonify({"success": True, "shares": post["shares"]}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error sharing post: {str(e)}")
        response = make_response(jsonify({"error": "Failed to share post"}), 400)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

# AI Insights endpoint - trending styles, tips, recommendations
@app.route('/ai-insights', methods=['GET', 'OPTIONS'])
@limiter.limit("50 per hour")
def get_ai_insights():
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    try:
        # Get user's preferred styles from recommendations if available
        recommended_styles = request.args.get('styles', '').split(',') if request.args.get('styles') else []
        
        # Analyze trends from social posts
        all_hashtags = []
        for post in social_posts:
            all_hashtags.extend(post.get('hashtags', []))
        
        trending_hashtags = list(set([tag for tag in all_hashtags if all_hashtags.count(tag) > 1]))[:5]
        
        # Combine with pre-loaded trends
        insights = {
            "trending_styles": hair_trends.get("trending_styles", [])[:5],
            "trending_hashtags": trending_hashtags if trending_hashtags else hair_trends.get("trending_hashtags", []),
            "popular_colors": hair_trends.get("popular_colors", [])[:4],
            "seasonal_tips": hair_trends.get("seasonal_tips", ""),
            "personalized_recommendations": []
        }
        
        # Add personalized recommendations based on user's styles
        if recommended_styles:
            first_style = recommended_styles[0] if recommended_styles else "this style"
            insights["personalized_recommendations"] = [
                f"Since you like {first_style}, try these complementary looks:",
                f"Professional tip: {first_style} works best for your face shape when paired with...",
                f"Try {first_style} with a slight variation for a fresh look"
            ][:3]
        
        response = make_response(jsonify(insights), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error getting AI insights: {str(e)}")
        response = make_response(jsonify({"error": "Failed to get insights"}), 400)
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
    # Initialize mock data on startup
    initialize_mock_data()
    logger.info(f"🚀 Starting LineUp API server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)  # debug=False for production