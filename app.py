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
import statistics
from lineup_backend.metrics import metrics, track_performance
from lineup_backend.services.barber_matcher import BarberMatcher
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

# Configure CORS - SECURITY: Tightened origins for production
# Get allowed origins from environment or use defaults
ALLOWED_ORIGINS = os.environ.get("LINEUP_ALLOWED_ORIGINS", "").split(",")
if not ALLOWED_ORIGINS or ALLOWED_ORIGINS == [""]:
    # Default allowed origins
    ALLOWED_ORIGINS = [
        "https://lineupai.onrender.com",
        "https://lineup-fjpn.onrender.com",
        "http://localhost:5000",
        "http://localhost:3000",
        "http://127.0.0.1:5000",
        "http://127.0.0.1:3000"
    ]
    # In development, allow all origins
    if os.environ.get("FLASK_ENV") == "development":
        ALLOWED_ORIGINS = ["*"]

CORS(app, 
     origins=ALLOWED_ORIGINS,
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
appointments = []
user_reviews = {}  # barber_id -> list of user-submitted reviews

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

# Root endpoint
@app.route('/')
@limiter.limit("100 per minute")
def index():
    return jsonify({
        "service": "LineUp AI Backend",
        "status": "running",
        "version": "2.0",
        "gemini_configured": model is not None,
        "features": ["AI Analysis", "Barber Search", "Appointments"],
        "rate_limits": {
            "general": "1000 per hour",
            "ai_analysis": "10 per hour per IP",
            "appointments": "30 per hour per IP"
        },
        "endpoints": {
            "health": "/health",
            "analyze": "/analyze (POST)",
            "appointments": "/appointments (GET/POST)",
            "barbers": "/barbers (GET)",
            "virtual-tryon": "/virtual-tryon (POST)"
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

@app.route('/metrics', methods=['GET', 'OPTIONS'])
@limiter.limit("10 per hour")  # Limit access to metrics
def get_metrics():
    """Get real-time performance metrics."""
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    all_metrics = metrics.get_all_metrics()
    
    # Add summary stats
    total_requests = sum(m["request_count"] for m in all_metrics["endpoints"].values())
    total_errors = sum(m["error_count"] for m in all_metrics["endpoints"].values())
    
    summary = {
        "total_requests": total_requests,
        "total_errors": total_errors,
        "overall_success_rate": 0.0,
        "avg_response_time_p95": 0.0,
    }
    
    # Cache savings summary
    cache_summary = {}
    for cache_name, cache_data in all_metrics["cache"].items():
        cache_summary[cache_name] = {
            "hit_rate": cache_data.get("hit_rate", 0.0),
            "total_time_saved_seconds": cache_data.get("total_time_saved_seconds", 0.0),
            "api_calls_avoided": cache_data.get("api_calls_avoided", 0),
            "speedup_factor": cache_data.get("speedup_factor", 0.0)
        }
    
    if total_requests > 0:
        summary["overall_success_rate"] = ((total_requests - total_errors) / total_requests) * 100.0
        
        # Average p95 across all endpoints
        p95_times = [m["response_time"]["p95"] for m in all_metrics["endpoints"].values() if m["response_time"]["p95"] > 0]
        if p95_times:
            summary["avg_response_time_p95"] = statistics.mean(p95_times)
    
    all_metrics["summary"] = summary
    all_metrics["cache_summary"] = cache_summary
    
    response = make_response(jsonify(all_metrics), 200)
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
            "appointments": len(appointments)
        }
    })

# Configuration endpoint - SECURITY: Never expose API keys to frontend
@app.route('/config', methods=['GET', 'OPTIONS'])
@limiter.limit("100 per minute")
def get_config():
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    # SECURITY: Only expose capability flags, NEVER expose actual API keys
    response = make_response(jsonify({
        "hasPlacesApi": bool(os.environ.get("GOOGLE_PLACES_API_KEY")),
        "hasGeminiApi": model is not None,
        "hasCloudinary": cloudinary_config is not None,
        "hasFirebase": db is not None,
        "backendVersion": "2.0",
        "features": {
            "aiAnalysis": model is not None,
            "barberSearch": bool(os.environ.get("GOOGLE_PLACES_API_KEY")),
            "virtualTryOn": bool(os.environ.get("REPLICATE_API_TOKEN")),
            "imageStorage": cloudinary_config is not None or storage_bucket is not None,
            "contentModeration": model is not None
        },
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
        logger.warning("Gemini API daily limit reached")
        response = make_response(jsonify({"error": "AI analysis limit reached", "message": "Please try again later"}), 503)
        response.headers['Content-Type'] = 'application/json'
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    try:
        data = request.get_json(force=True)
        
        if not model:
            logger.info("Gemini not configured")
            response = make_response(jsonify({"error": "AI analysis unavailable", "message": "Service not configured"}), 503)
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
        
        # Create Gemini prompt - constrain styleName to ALLOWED_HAIRCUTS for FLUX compatibility
        prompt = """You are an expert hairstylist and facial analysis AI. Analyze this person's face and hair in the photo and provide personalized haircut recommendations.

IMPORTANT: Return ONLY a valid JSON response with NO additional text, NO markdown formatting, NO code blocks.

CRITICAL RULE: The "styleName" field MUST be chosen from this EXACT list (copy the name exactly):
Straight, Wavy, Curly, Bob, Pixie Cut, Layered, Undercut, Mohawk, Crew Cut, Faux Hawk,
Slicked Back, Side-Parted, Center-Parted, Blunt Bangs, Side-Swept Bangs, Shag, Lob,
Angled Bob, A-Line Bob, Asymmetrical Bob, Layered Shag, Choppy Layers, Soft Waves,
Tousled, Feathered, Cornrows, Box Braids, Dreadlocks, Perm, Top Knot, French Braid,
High Ponytail, Mohawk Fade, Space Buns, Messy Bun, Braided Ponytail

DO NOT invent style names. DO NOT use names like "Modern Fade", "Textured Quiff", "Short Buzz", "Classic Taper" -- these are NOT in the allowed list. Pick the closest match from the list above.

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
            "styleName": "[MUST be from the allowed list above]",
            "description": "[2-3 sentence description of the haircut style and how it would look on this person]",
            "reason": "[1-2 sentences explaining why this suits their face shape, hair texture, and features]"
        }
    ]
}

Provide exactly 6 diverse haircut recommendations. Choose styles that genuinely suit this person's face shape and hair texture. Each recommendation should be a different style from the allowed list."""

        # Call Gemini API
        try:
            increment_gemini_api_usage()  # Track API usage
            response = model.generate_content([prompt, image])
            response_text = response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            response = make_response(jsonify({"error": "AI analysis failed", "message": str(e)}), 503)
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
            response = make_response(jsonify({"error": "Invalid AI response", "message": "Could not parse analysis results"}), 503)
            response.headers['Content-Type'] = 'application/json'
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        # Validate and return response
        if "analysis" not in analysis_data or "recommendations" not in analysis_data:
            response = make_response(jsonify({"error": "Invalid analysis", "message": "Missing required fields"}), 503)
            response.headers['Content-Type'] = 'application/json'
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        response = make_response(jsonify(analysis_data), 200)
        response.headers['Content-Type'] = 'application/json'
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        logger.error(f"Error in analyze endpoint: {str(e)}")
        response = make_response(jsonify({"error": "Analysis failed", "message": str(e)}), 503)
        response.headers['Content-Type'] = 'application/json'
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
        
        # Try to get from database first
        appointment = None
        if db:
            appointment = db_get_doc('appointments', appointment_id)
        
        # Fallback to in-memory
        if not appointment:
            appointment = next((apt for apt in appointments if apt.get("id") == appointment_id), None)
        
        if not appointment:
            response = make_response(jsonify({"error": "Appointment not found"}), 404)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        appointment["status"] = new_status
        appointment["statusUpdatedAt"] = datetime.now().isoformat()
        
        # Save to database
        if db:
            db_update_doc('appointments', appointment_id, {
                "status": new_status,
                "statusUpdatedAt": appointment["statusUpdatedAt"]
            })
        
        response = make_response(jsonify({"success": True, "appointment": appointment}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        logger.error(f"Error updating appointment: {str(e)}")
        response = make_response(jsonify({"error": "Failed to update appointment"}), 400)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

# ========================================
# PHASE 1: PRODUCTION-GRADE BARBER FEATURES
# ========================================

# Appointment Management - Accept/Reject/Reschedule/Cancel
@app.route('/appointments/<appointment_id>/accept', methods=['POST', 'OPTIONS'])
@limiter.limit("50 per hour")
def accept_appointment(appointment_id):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    try:
        # Get appointment
        appointment = None
        if db:
            appointment = db_get_doc('appointments', appointment_id)
        if not appointment:
            appointment = next((apt for apt in appointments if apt.get("id") == appointment_id), None)
        
        if not appointment:
            response = make_response(jsonify({"error": "Appointment not found"}), 404)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        appointment["status"] = "confirmed"
        appointment["statusUpdatedAt"] = datetime.now().isoformat()
        
        if db:
            db_update_doc('appointments', appointment_id, {
                "status": "confirmed",
                "statusUpdatedAt": appointment["statusUpdatedAt"]
            })
        
        response = make_response(jsonify({"success": True, "appointment": appointment}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error accepting appointment: {str(e)}")
        response = make_response(jsonify({"error": "Failed to accept appointment"}), 400)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

@app.route('/appointments/<appointment_id>/reject', methods=['POST', 'OPTIONS'])
@limiter.limit("50 per hour")
def reject_appointment(appointment_id):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    try:
        data = request.get_json() or {}
        reason = data.get("reason", "No reason provided")
        
        appointment = None
        if db:
            appointment = db_get_doc('appointments', appointment_id)
        if not appointment:
            appointment = next((apt for apt in appointments if apt.get("id") == appointment_id), None)
        
        if not appointment:
            response = make_response(jsonify({"error": "Appointment not found"}), 404)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        appointment["status"] = "rejected"
        appointment["rejectionReason"] = reason
        appointment["statusUpdatedAt"] = datetime.now().isoformat()
        
        if db:
            db_update_doc('appointments', appointment_id, {
                "status": "rejected",
                "rejectionReason": reason,
                "statusUpdatedAt": appointment["statusUpdatedAt"]
            })
        
        response = make_response(jsonify({"success": True, "appointment": appointment}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error rejecting appointment: {str(e)}")
        response = make_response(jsonify({"error": "Failed to reject appointment"}), 400)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

@app.route('/appointments/<appointment_id>/reschedule', methods=['POST', 'OPTIONS'])
@limiter.limit("50 per hour")
def reschedule_appointment(appointment_id):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    try:
        data = request.get_json()
        new_date = data.get("date")
        new_time = data.get("time")
        reason = data.get("reason", "Rescheduled by barber")
        
        if not new_date or not new_time:
            response = make_response(jsonify({"error": "Date and time required"}), 400)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        appointment = None
        if db:
            appointment = db_get_doc('appointments', appointment_id)
        if not appointment:
            appointment = next((apt for apt in appointments if apt.get("id") == appointment_id), None)
        
        if not appointment:
            response = make_response(jsonify({"error": "Appointment not found"}), 404)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        # Store old date/time for history
        if "rescheduleHistory" not in appointment:
            appointment["rescheduleHistory"] = []
        appointment["rescheduleHistory"].append({
            "oldDate": appointment.get("date"),
            "oldTime": appointment.get("time"),
            "newDate": new_date,
            "newTime": new_time,
            "reason": reason,
            "rescheduledAt": datetime.now().isoformat()
        })
        
        appointment["date"] = new_date
        appointment["time"] = new_time
        appointment["status"] = "rescheduled"
        appointment["statusUpdatedAt"] = datetime.now().isoformat()
        
        if db:
            db_update_doc('appointments', appointment_id, {
                "date": new_date,
                "time": new_time,
                "status": "rescheduled",
                "rescheduleHistory": appointment["rescheduleHistory"],
                "statusUpdatedAt": appointment["statusUpdatedAt"]
            })
        
        response = make_response(jsonify({"success": True, "appointment": appointment}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error rescheduling appointment: {str(e)}")
        response = make_response(jsonify({"error": "Failed to reschedule appointment"}), 400)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

@app.route('/appointments/<appointment_id>/cancel', methods=['POST', 'OPTIONS'])
@limiter.limit("50 per hour")
def cancel_appointment(appointment_id):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    try:
        data = request.get_json() or {}
        reason = data.get("reason", "Cancelled by barber")
        
        appointment = None
        if db:
            appointment = db_get_doc('appointments', appointment_id)
        if not appointment:
            appointment = next((apt for apt in appointments if apt.get("id") == appointment_id), None)
        
        if not appointment:
            response = make_response(jsonify({"error": "Appointment not found"}), 404)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        appointment["status"] = "cancelled"
        appointment["cancellationReason"] = reason
        appointment["statusUpdatedAt"] = datetime.now().isoformat()
        
        if db:
            db_update_doc('appointments', appointment_id, {
                "status": "cancelled",
                "cancellationReason": reason,
                "statusUpdatedAt": appointment["statusUpdatedAt"]
            })
        
        response = make_response(jsonify({"success": True, "appointment": appointment}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error cancelling appointment: {str(e)}")
        response = make_response(jsonify({"error": "Failed to cancel appointment"}), 400)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

# Add notes to appointment
@app.route('/appointments/<appointment_id>/notes', methods=['POST', 'PUT', 'OPTIONS'])
@limiter.limit("50 per hour")
def add_appointment_notes(appointment_id):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, PUT, OPTIONS')
        return response, 200
    
    try:
        data = request.get_json()
        note = data.get("note", "")
        note_type = data.get("type", "general")  # general, client_preference, service_notes, etc.
        
        appointment = None
        if db:
            appointment = db_get_doc('appointments', appointment_id)
        if not appointment:
            appointment = next((apt for apt in appointments if apt.get("id") == appointment_id), None)
        
        if not appointment:
            response = make_response(jsonify({"error": "Appointment not found"}), 404)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        if "barberNotes" not in appointment:
            appointment["barberNotes"] = []
        
        appointment["barberNotes"].append({
            "note": note,
            "type": note_type,
            "createdAt": datetime.now().isoformat()
        })
        
        if db:
            db_update_doc('appointments', appointment_id, {
                "barberNotes": appointment["barberNotes"]
            })
        
        response = make_response(jsonify({"success": True, "appointment": appointment}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error adding notes: {str(e)}")
        response = make_response(jsonify({"error": "Failed to add notes"}), 400)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

# Barber discovery endpoint with REAL Google Places API integration
@app.route('/barbers', methods=['GET', 'OPTIONS'])
@limiter.limit("50 per hour")  # Moderate limit since this calls external APIs
@track_performance("barbers")
def get_barbers():
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    location = request.args.get('location', 'Atlanta, GA')
    styles_param = request.args.get('styles', '')
    recommended_styles = [s.strip() for s in styles_param.split(',') if s.strip()] if styles_param else []
    
    logger.info(f"Barber search: location={location}, styles={recommended_styles}")
    
    # Initialize barber matcher
    matcher = BarberMatcher(gemini_model=model)
    
    # Clean cache before checking
    clean_cache()
    
    # Check cache first
    cache_key = location.lower().strip()
    current_time = time.time()
    
    if cache_key in places_api_cache:
        cached_data = places_api_cache[cache_key]
        if current_time - cached_data['timestamp'] < CACHE_DURATION:
            # Track cache hit with response time
            cache_hit_start = time.time()
            logger.info(f"Returning cached barber data for {location}")
            response = make_response(jsonify({
                "barbers": cached_data['data'], 
                "location": location,
                "cached": True
            }), 200)
            cache_hit_time_ms = (time.time() - cache_hit_start) * 1000
            metrics.record_cache_hit("places_api", response_time_ms=cache_hit_time_ms)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
    
    # If we get here, it's a cache miss
    metrics.record_cache_miss("places_api")
    
    # Track API call time for cache savings calculation
    api_call_start = time.time()
    
    # Get Google Places API key
    GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")
    
    if not GOOGLE_PLACES_API_KEY:
        logger.warning("Google Places API key not configured")
        response = make_response(jsonify({
            "error": "Barber search unavailable",
            "message": "Location search is not configured"
        }), 503)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    # Check if we can make Places API call
    if not can_make_places_api_call():
        logger.warning("Places API daily limit reached")
        response = make_response(jsonify({
            "error": "Search limit reached",
            "message": "Please try again later"
        }), 503)
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
        
        geocode_start = time.time()
        geocode_response = requests.get(geocode_url, params=geocode_params)
        geocode_latency = (time.time() - geocode_start) * 1000
        metrics.record_api_latency("google_geocode", geocode_latency)
        
        geocode_data = geocode_response.json()
        
        if geocode_data['status'] != 'OK' or not geocode_data['results']:
            raise Exception(f"Location not found: {location}")
        
        lat = geocode_data['results'][0]['geometry']['location']['lat']
        lng = geocode_data['results'][0]['geometry']['location']['lng']
        
        # Search for barbershops - use Text Search for style-specific queries
        if recommended_styles:
            # Text Search: better for finding specialists (e.g., "best fade barber near 30308")
            places_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json"
            style_terms = ' '.join(recommended_styles[:2])  # Use first 2 styles
            search_query = f"barber {style_terms} near {location}"
            logger.info(f"Text Search query: {search_query}")
            
            places_params = {
                'query': search_query,
                'location': f"{lat},{lng}",
                'radius': 8000,  # 8km radius
                'type': 'hair_care',
                'key': GOOGLE_PLACES_API_KEY
            }
        else:
            # Nearby Search: good for general barber discovery
            places_url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            search_keywords = matcher.build_search_keywords(recommended_styles)
            logger.info(f"Nearby Search keywords: {search_keywords}")
            
            places_params = {
                'location': f"{lat},{lng}",
                'radius': 10000,  # 10km radius
                'type': 'hair_care',
                'keyword': search_keywords,
                'key': GOOGLE_PLACES_API_KEY
            }
        
        places_start = time.time()
        places_response = requests.get(places_url, params=places_params)
        places_latency = (time.time() - places_start) * 1000
        metrics.record_api_latency("google_places_search", places_latency)
        
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
                'fields': 'name,formatted_address,formatted_phone_number,opening_hours,website,price_level,rating,user_ratings_total,photos,reviews',
                'key': GOOGLE_PLACES_API_KEY
            }
            
            try:
                details_start = time.time()
                details_response = requests.get(details_url, params=details_params)
                details_latency = (time.time() - details_start) * 1000
                metrics.record_api_latency("google_places_details", details_latency)
                
                details_data = details_response.json()
                
                if details_data['status'] == 'OK':
                    details = details_data['result']
                else:
                    details = {}
            except Exception as e:
                logger.warning(f"Failed to fetch place details: {e}")
                details = {}
            
            # Specialties will be set after AI review analysis (see rank_barbers)
            # For now, set basic defaults based on what we know
            specialties = ['Haircut', 'Styling']
            name_lower = place['name'].lower()
            if 'beard' in name_lower:
                specialties.append('Beard Trim')
            if 'barber' in name_lower:
                specialties = ['Haircut', 'Styling', 'Beard Trim']
            
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
            
            # Get booking URL from website or generate Calendly-style URL
            booking_url = details.get('website', '')
            # If website exists, try to create booking URL (common patterns)
            if booking_url:
                # Common booking platforms
                if 'calendly.com' in booking_url.lower():
                    booking_url = booking_url
                elif 'booksy.com' in booking_url.lower():
                    booking_url = booking_url
                elif 'squareup.com' in booking_url.lower() or 'square.site' in booking_url.lower():
                    booking_url = booking_url
                else:
                    # Default: use website as booking URL
                    booking_url = booking_url
            
            # Get reviews from Google Places
            reviews = details.get('reviews', [])
            google_reviews = []
            if reviews:
                for review in reviews[:10]:  # Limit to 10 reviews
                    google_reviews.append({
                        'id': review.get('author_name', '') + '_' + str(review.get('time', 0)),
                        'username': review.get('author_name', 'Anonymous'),
                        'rating': review.get('rating', 5),
                        'text': review.get('text', ''),
                        'date': datetime.fromtimestamp(review.get('time', 0)).strftime('%Y-%m-%d') if review.get('time') else 'Recent',
                        'profile_photo': review.get('profile_photo_url', ''),
                        'relative_time': review.get('relative_time_description', '')
                    })
            
            barber_info = {
                'id': place['place_id'],
                'name': place['name'],
                'address': details.get('formatted_address', place.get('vicinity', 'Address not available')),
                'rating': place.get('rating', 0),
                'user_ratings_total': place.get('user_ratings_total', 0),
                'price_level': place.get('price_level', None),
                'priceTier': '$' * place.get('price_level', 2) if place.get('price_level') else None,
                'phone': details.get('formatted_phone_number', 'Call for info'),
                'website': details.get('website', ''),
                'bookingUrl': booking_url,  # External booking URL
                'google_maps_url': google_maps_url,
                'hours': details.get('opening_hours', {}).get('weekday_text', []),
                'open_now': place.get('opening_hours', {}).get('open_now', None),
                'photo': photo_url,
                'specialties': specialties,
                'location': {
                    'lat': lat,
                    'lng': lng
                },
                'recommended_for_styles': recommended_styles if recommended_styles else [],
                'place_id': place['place_id'],  # Store place_id for reviews
                'google_reviews': google_reviews,  # Include reviews in barber data
                'reviews': google_reviews  # Also store as 'reviews' for matcher
            }
            
            real_barbers.append(barber_info)
        
        # Use AI-powered matching to rank barbers by style relevance
        if recommended_styles:
            logger.info(f"Ranking {len(real_barbers)} barbers for styles: {recommended_styles}")
            real_barbers = matcher.rank_barbers(
                real_barbers, 
                recommended_styles,
                use_ai_analysis=True  # Enable AI review analysis
            )
        else:
            # No specific styles - just sort by rating
            real_barbers.sort(key=lambda x: (x['rating'] * (min(x['user_ratings_total'], 100) / 100)), reverse=True)
        
        # Track API call duration for cache savings calculation
        api_call_duration_ms = (time.time() - api_call_start) * 1000
        metrics.record_api_call_time("places_api", api_call_duration_ms)
        
        # Cache the results (top 10)
        top_barbers = real_barbers[:10]
        places_api_cache[cache_key] = {
            'data': top_barbers,
            'timestamp': current_time
        }
        
        # Increment API usage
        increment_places_api_usage()
        
        logger.info(f"Found {len(real_barbers)} real barbershops in {location}, returning top {len(top_barbers)}")
        
        response = make_response(jsonify({
            "barbers": top_barbers,
            "location": location,
            "real_data": True,
            "total_found": len(real_barbers),
            "ranked_by_style": bool(recommended_styles)
        }), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        logger.error(f"Error fetching real barber data: {str(e)}")
        response = make_response(jsonify({
            "error": "Failed to load barbershops",
            "message": str(e)
        }), 503)
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

# Virtual Try-On endpoint - uses centralized ReplicateService
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
        
        logger.info(f"Starting hair transformation: {style_description}")
        
        # Use centralized ReplicateService for transformation
        from lineup_backend.services.replicate_service import ReplicateService
        from lineup_backend.services.gemini_service import GeminiService
        
        REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
        replicate_service = ReplicateService(api_token=REPLICATE_API_TOKEN)
        
        # Create GeminiService wrapper if Gemini model is available
        gemini_service = None
        if model:
            gemini_service = GeminiService(model=model)
        
        result = replicate_service.transform_hair(
            user_photo_base64=user_photo_base64,
            style_description=style_description,
            gemini_service=gemini_service
        )
        
        if result.get("success"):
            response = make_response(jsonify(result), 200)
        else:
            response = make_response(jsonify(result), 400)
        
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
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
        # Check if barber_id is a Google place_id (Google place_ids are typically 27 characters)
        # Try to fetch Google Reviews first
        # Google place_ids are typically 27+ characters and start with 'Ch' or other patterns
        is_google_place_id = len(barber_id) >= 20 and (barber_id.startswith('Ch') or barber_id.startswith('Ei') or barber_id.startswith('Gh'))
        places_key = os.environ.get("GOOGLE_PLACES_API_KEY")
        
        if places_key and is_google_place_id:
            try:
                # Import requests if not already imported
                try:
                    import requests
                except ImportError:
                    requests = None
                
                if not requests:
                    logger.error("requests module not available for fetching Google Reviews")
                    raise Exception("requests module not available")
                
                details_url = f"https://maps.googleapis.com/maps/api/place/details/json"
                details_params = {
                    'place_id': barber_id,
                    'fields': 'name,rating,user_ratings_total,reviews',
                    'key': places_key
                }
                
                logger.info(f"Fetching Google Reviews for place_id: {barber_id}")
                details_response = requests.get(details_url, params=details_params, timeout=10)
                details_data = details_response.json()
                
                logger.info(f"Google Reviews API response status: {details_data.get('status')}")
                
                if details_data.get('status') == 'OK' and 'result' in details_data:
                    result = details_data['result']
                    reviews = result.get('reviews', [])
                    
                    logger.info(f"Found {len(reviews)} reviews from Google")
                    
                    google_reviews = []
                    for review in reviews[:10]:  # Limit to 10 reviews
                        try:
                            review_date = 'Recent'
                            if review.get('time'):
                                try:
                                    review_date = datetime.fromtimestamp(review.get('time')).strftime('%Y-%m-%d')
                                except (ValueError, TypeError, OSError):
                                    review_date = 'Recent'
                            
                            google_reviews.append({
                                'id': review.get('author_name', '') + '_' + str(review.get('time', 0)),
                                'username': review.get('author_name', 'Anonymous'),
                                'rating': review.get('rating', 5),
                                'text': review.get('text', ''),
                                'date': review_date,
                                'profile_photo': review.get('profile_photo_url', ''),
                                'relative_time': review.get('relative_time_description', '')
                            })
                        except Exception as review_error:
                            logger.error(f"Error processing review: {str(review_error)}")
                            continue
                    
                    avg_rating = result.get('rating', 0)
                    total_reviews = result.get('user_ratings_total', 0)
                    
                    logger.info(f"Returning {len(google_reviews)} Google reviews")
                    response = make_response(jsonify({
                        'reviews': google_reviews,
                        'average_rating': avg_rating,
                        'total_reviews': total_reviews,
                        'source': 'google'
                    }), 200)
                    response.headers['Access-Control-Allow-Origin'] = '*'
                    return response
                else:
                    logger.warning(f"Google Reviews API returned status: {details_data.get('status')}, error: {details_data.get('error_message', 'Unknown error')}")
            except Exception as e:
                logger.error(f"Error fetching Google Reviews: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                # Fall through to mock reviews
        
        # Fallback when Google reviews unavailable
        reviews = []
        avg_rating = 0
        total_reviews = len(reviews)
        
        if reviews:
            avg_rating = sum(r.get('rating', 0) for r in reviews) / len(reviews)
        
        response = make_response(jsonify({
            'reviews': reviews,
            'average_rating': avg_rating,
            'total_reviews': total_reviews,
            'source': 'none'
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
            if db:
                reviews_doc = db_get_doc('barber_reviews', barber_id) or {'reviews': []}
                reviews_doc['reviews'] = reviews_doc.get('reviews', []) + [new_review]
                db_add_doc('barber_reviews', reviews_doc, doc_id=barber_id)
            else:
                if barber_id not in user_reviews:
                    user_reviews[barber_id] = []
                user_reviews[barber_id].append(new_review)
            response = make_response(jsonify({"success": True, "review": new_review}), 201)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            logger.error(f"Error creating review: {str(e)}")
            response = make_response(jsonify({"error": "Failed to create review"}), 400)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response

# ========================================
# Availability & Working Hours Management
# ========================================

@app.route('/barbers/<barber_id>/availability', methods=['GET', 'PUT', 'OPTIONS'])
@limiter.limit("50 per hour")
def manage_availability(barber_id):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, PUT, OPTIONS')
        return response, 200
    
    if request.method == 'GET':
        try:
            availability = None
            if db:
                availability = db_get_doc('barber_availability', barber_id)
            
            if not availability:
                # Default availability
                availability = {
                    "barberId": barber_id,
                    "workingHours": {
                        "monday": {"enabled": True, "start": "09:00", "end": "18:00"},
                        "tuesday": {"enabled": True, "start": "09:00", "end": "18:00"},
                        "wednesday": {"enabled": True, "start": "09:00", "end": "18:00"},
                        "thursday": {"enabled": True, "start": "09:00", "end": "18:00"},
                        "friday": {"enabled": True, "start": "09:00", "end": "18:00"},
                        "saturday": {"enabled": True, "start": "09:00", "end": "17:00"},
                        "sunday": {"enabled": False, "start": "09:00", "end": "17:00"}
                    },
                    "breakTimes": [],
                    "blockedDates": [],
                    "serviceDuration": 30,  # Default 30 minutes
                    "bufferTime": 15,  # 15 minutes between appointments
                    "timezone": "America/New_York"
                }
            
            response = make_response(jsonify({"availability": availability}), 200)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            logger.error(f"Error getting availability: {str(e)}")
            response = make_response(jsonify({"error": "Failed to get availability"}), 400)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
    
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            
            availability_data = {
                "barberId": barber_id,
                "workingHours": data.get("workingHours", {}),
                "breakTimes": data.get("breakTimes", []),
                "blockedDates": data.get("blockedDates", []),
                "serviceDuration": data.get("serviceDuration", 30),
                "bufferTime": data.get("bufferTime", 15),
                "timezone": data.get("timezone", "America/New_York"),
                "updatedAt": datetime.now().isoformat()
            }
            
            if db:
                db_add_doc('barber_availability', availability_data, doc_id=barber_id)
            
            response = make_response(jsonify({"success": True, "availability": availability_data}), 200)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            logger.error(f"Error updating availability: {str(e)}")
            response = make_response(jsonify({"error": "Failed to update availability"}), 400)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response

@app.route('/barbers/<barber_id>/available-slots', methods=['GET', 'OPTIONS'])
@limiter.limit("100 per hour")
def get_available_slots(barber_id):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    try:
        date = request.args.get('date')
        if not date:
            response = make_response(jsonify({"error": "Date parameter required"}), 400)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        # Get availability
        availability = None
        if db:
            availability = db_get_doc('barber_availability', barber_id)
        
        if not availability:
            response = make_response(jsonify({"error": "Availability not configured"}), 404)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        # Get existing appointments for that date
        appointments_today = []
        if db:
            appointments_today = db_query('appointments', 'barberId', '==', barber_id)
            appointments_today = [apt for apt in appointments_today if apt.get('date') == date and apt.get('status') not in ['cancelled', 'rejected']]
        else:
            appointments_today = [apt for apt in appointments if apt.get('barberId') == barber_id and apt.get('date') == date and apt.get('status') not in ['cancelled', 'rejected']]
        
        # Calculate available slots (simplified - can be enhanced)
        from datetime import datetime as dt
        day_name = dt.strptime(date, "%Y-%m-%d").strftime("%A").lower()
        day_hours = availability.get("workingHours", {}).get(day_name, {})
        
        if not day_hours.get("enabled", False):
            response = make_response(jsonify({"slots": []}), 200)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        start_time = day_hours.get("start", "09:00")
        end_time = day_hours.get("end", "18:00")
        duration = availability.get("serviceDuration", 30)
        buffer = availability.get("bufferTime", 15)
        
        # Generate time slots
        slots = []
        # Simplified slot generation - in production, parse times properly
        response = make_response(jsonify({
            "slots": slots,
            "date": date,
            "workingHours": day_hours
        }), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error getting available slots: {str(e)}")
        response = make_response(jsonify({"error": "Failed to get available slots"}), 400)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

# ========================================
# Service & Pricing Management
# ========================================

@app.route('/barbers/<barber_id>/services', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
@limiter.limit("50 per hour")
def manage_services(barber_id):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        return response, 200
    
    if request.method == 'GET':
        try:
            services = []
            if db:
                services = db_query('barber_services', 'barberId', '==', barber_id)
            
            if not services:
                # Default services
                services = [
                    {"id": "1", "name": "Haircut", "price": 30, "duration": 30, "category": "Hair"},
                    {"id": "2", "name": "Beard Trim", "price": 15, "duration": 15, "category": "Beard"},
                    {"id": "3", "name": "Haircut + Beard", "price": 40, "duration": 45, "category": "Package"}
                ]
            
            response = make_response(jsonify({"services": services}), 200)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            logger.error(f"Error getting services: {str(e)}")
            response = make_response(jsonify({"error": "Failed to get services"}), 400)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            service_id = str(uuid.uuid4())
            
            new_service = {
                "id": service_id,
                "barberId": barber_id,
                "name": data.get("name", ""),
                "price": data.get("price", 0),
                "duration": data.get("duration", 30),
                "category": data.get("category", "General"),
                "description": data.get("description", ""),
                "createdAt": datetime.now().isoformat()
            }
            
            if db:
                db_add_doc('barber_services', new_service, doc_id=service_id)
            
            response = make_response(jsonify({"success": True, "service": new_service}), 201)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            logger.error(f"Error creating service: {str(e)}")
            response = make_response(jsonify({"error": "Failed to create service"}), 400)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
    
    elif request.method == 'PUT':
        try:
            service_id = request.args.get('service_id')
            if not service_id:
                response = make_response(jsonify({"error": "service_id required"}), 400)
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response
            
            data = request.get_json()
            
            if db:
                db_update_doc('barber_services', service_id, data)
            
            response = make_response(jsonify({"success": True}), 200)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            logger.error(f"Error updating service: {str(e)}")
            response = make_response(jsonify({"error": "Failed to update service"}), 400)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
    
    elif request.method == 'DELETE':
        try:
            service_id = request.args.get('service_id')
            if not service_id:
                response = make_response(jsonify({"error": "service_id required"}), 400)
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response
            
            if db:
                db_delete_doc('barber_services', service_id)
            
            response = make_response(jsonify({"success": True}), 200)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            logger.error(f"Error deleting service: {str(e)}")
            response = make_response(jsonify({"error": "Failed to delete service"}), 400)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response

# ========================================
# Client History & Notes
# ========================================

@app.route('/barbers/<barber_id>/clients', methods=['GET', 'OPTIONS'])
@limiter.limit("100 per hour")
def get_clients(barber_id):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    try:
        # Get all appointments for this barber to extract clients
        appointments_list = []
        if db:
            appointments_list = db_query('appointments', 'barberId', '==', barber_id)
        else:
            appointments_list = [apt for apt in appointments if apt.get('barberId') == barber_id]
        
        # Group by client
        clients_dict = {}
        for apt in appointments_list:
            client_id = apt.get('clientId')
            if not client_id:
                continue
            
            if client_id not in clients_dict:
                clients_dict[client_id] = {
                    "clientId": client_id,
                    "clientName": apt.get('clientName', 'Unknown'),
                    "totalVisits": 0,
                    "lastVisit": None,
                    "totalSpent": 0,
                    "appointments": []
                }
            
            clients_dict[client_id]["totalVisits"] += 1
            clients_dict[client_id]["appointments"].append(apt)
            
            # Calculate total spent (simplified)
            price_str = apt.get('price', '$0').replace('$', '').replace(',', '')
            try:
                price = float(price_str)
                clients_dict[client_id]["totalSpent"] += price
            except (ValueError, TypeError):
                pass
        
        # Sort by last visit
        clients = list(clients_dict.values())
        for client in clients:
            if client["appointments"]:
                client["appointments"].sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                client["lastVisit"] = client["appointments"][0].get('date')
        
        clients.sort(key=lambda x: x.get('lastVisit') or '', reverse=True)
        
        response = make_response(jsonify({"clients": clients}), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error getting clients: {str(e)}")
        response = make_response(jsonify({"error": "Failed to get clients"}), 400)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

@app.route('/barbers/<barber_id>/clients/<client_id>/history', methods=['GET', 'OPTIONS'])
@limiter.limit("100 per hour")
def get_client_history(barber_id, client_id):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response, 200
    
    try:
        appointments_list = []
        if db:
            appointments_list = db_query('appointments', 'barberId', '==', barber_id)
            appointments_list = [apt for apt in appointments_list if apt.get('clientId') == client_id]
        else:
            appointments_list = [apt for apt in appointments if apt.get('barberId') == barber_id and apt.get('clientId') == client_id]
        
        # Sort by date
        appointments_list.sort(key=lambda x: x.get('date', '') + ' ' + x.get('time', ''), reverse=True)
        
        response = make_response(jsonify({
            "clientId": client_id,
            "appointments": appointments_list,
            "totalVisits": len(appointments_list)
        }), 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error getting client history: {str(e)}")
        response = make_response(jsonify({"error": "Failed to get client history"}), 400)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

@app.route('/barbers/<barber_id>/clients/<client_id>/notes', methods=['GET', 'POST', 'PUT', 'OPTIONS'])
@limiter.limit("50 per hour")
def manage_client_notes(barber_id, client_id):
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS')
        return response, 200
    
    if request.method == 'GET':
        try:
            notes_doc = None
            if db:
                notes_doc = db_get_doc('client_notes', f"{barber_id}_{client_id}")
            
            notes = notes_doc.get("notes", []) if notes_doc else []
            
            response = make_response(jsonify({"notes": notes}), 200)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            logger.error(f"Error getting client notes: {str(e)}")
            response = make_response(jsonify({"error": "Failed to get client notes"}), 400)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            note_text = data.get("note", "")
            note_type = data.get("type", "general")
            
            notes_doc = None
            if db:
                notes_doc = db_get_doc('client_notes', f"{barber_id}_{client_id}")
            
            notes = notes_doc.get("notes", []) if notes_doc else []
            
            new_note = {
                "id": str(uuid.uuid4()),
                "note": note_text,
                "type": note_type,
                "createdAt": datetime.now().isoformat()
            }
            notes.append(new_note)
            
            if db:
                db_add_doc('client_notes', {
                    "barberId": barber_id,
                    "clientId": client_id,
                    "notes": notes
                }, doc_id=f"{barber_id}_{client_id}")
            
            response = make_response(jsonify({"success": True, "note": new_note}), 201)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            logger.error(f"Error adding client note: {str(e)}")
            response = make_response(jsonify({"error": "Failed to add client note"}), 400)
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
    logger.info(f"🚀 Starting LineUp API server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)  # debug=False for production