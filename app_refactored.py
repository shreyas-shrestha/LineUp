# app_refactored.py - Refactored Flask Backend
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pydantic import ValidationError
import logging
import os

# Import our modules
from config import Config
from errors import (
    register_error_handlers, validate_request, 
    APIError, NotFoundError, ExternalAPIError
)
from models import (
    init_db,
    AppointmentCreate, AppointmentStatusUpdate,
    SocialPostCreate, PortfolioItemCreate,
    SubscriptionPackageCreate, VirtualTryOnRequest,
    LocationQuery, ImageAnalysisRequest
)
from services import (
    DatabaseService, CacheService, SocialService,
    AppointmentService, PortfolioService, 
    GeminiService, PlacesService
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Configure rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per hour"],
    storage_uri=Config.RATE_LIMIT_STORAGE,
    strategy="moving-window"
)

# Configure CORS
CORS(app, 
     origins=Config.CORS_ORIGINS,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Accept", "Authorization"],
     supports_credentials=False)

# Register error handlers
register_error_handlers(app)

# Initialize database
init_db()

# Validate configuration
config_status = Config.validate()
logger.info(f"Configuration validated: {config_status}")


# ============================================================================
# ROUTES - ROOT & HEALTH
# ============================================================================

@app.route('/')
@limiter.limit("100 per minute")
def index():
    """API information endpoint"""
    return jsonify({
        "service": "LineUp AI Backend",
        "status": "running",
        "version": "2.0-refactored",
        "features": ["AI Analysis", "Social Feed", "Barber Discovery", "Appointments"],
        "configuration": Config.get_status(),
        "endpoints": {
            "health": "/health",
            "analyze": "/analyze (POST)",
            "social": "/social (GET/POST)",
            "portfolio": "/portfolio (GET/POST)",
            "appointments": "/appointments (GET/POST)",
            "barbers": "/barbers (GET)",
            "virtual-tryon": "/virtual-tryon (POST)"
        }
    })


@app.route('/health', methods=['GET'])
@limiter.limit("200 per minute")
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "lineup-backend",
        "timestamp": str(os.times()),
        "configuration": Config.get_status()
    })


@app.route('/config', methods=['GET', 'OPTIONS'])
@limiter.limit("100 per minute")
def get_config():
    """Get frontend configuration"""
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
    return jsonify({
        "placesApiKey": Config.GOOGLE_PLACES_API_KEY if Config.GOOGLE_PLACES_API_KEY else "",
        "hasPlacesApi": bool(Config.GOOGLE_PLACES_API_KEY),
        "hasGemini": bool(Config.GEMINI_API_KEY),
        "hasVirtualTryon": bool(Config.MODAL_HAIRFAST_ENDPOINT or Config.HF_API_KEY),
        "backendVersion": "2.0"
    })


# ============================================================================
# ROUTES - AI ANALYSIS
# ============================================================================

@app.route('/analyze', methods=['POST', 'OPTIONS'])
@limiter.limit("10 per hour")
def analyze():
    """AI face analysis and haircut recommendations"""
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
    logger.info("ANALYZE endpoint called")
    
    try:
        # Validate request
        data = request.get_json(force=True)
        validated = validate_request(ImageAnalysisRequest, data)
        
        # Extract image data
        payload = validated.payload
        parts = payload['contents'][0].get('parts', [])
        
        if len(parts) < 2:
            raise APIError("No image data provided")
        
        image_data = parts[1].get('inlineData', {})
        base64_image = image_data.get('data', '')
        
        if not base64_image:
            raise APIError("Empty image data")
        
        # Analyze with Gemini
        result = GeminiService.analyze_face(base64_image)
        
        return jsonify(result)
        
    except ValidationError as e:
        raise APIError(str(e), status_code=400)
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        # Return mock data on error
        return jsonify(GeminiService._get_mock_analysis())


# ============================================================================
# ROUTES - SOCIAL FEED
# ============================================================================

@app.route('/social', methods=['GET', 'POST', 'OPTIONS'])
def social():
    """Social feed endpoints"""
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
    if request.method == 'GET':
        limiter.limit("100 per hour")(lambda: None)()
        posts = SocialService.get_posts()
        return jsonify({"posts": posts})
    
    elif request.method == 'POST':
        limiter.limit("20 per hour")(lambda: None)()
        
        try:
            data = request.get_json()
            validated = validate_request(SocialPostCreate, data)
            
            post = SocialService.create_post(
                username=validated.username,
                avatar=validated.avatar,
                image=validated.image,
                caption=validated.caption
            )
            
            return jsonify({"success": True, "post": post}), 201
            
        except Exception as e:
            logger.error(f"Error creating post: {e}")
            raise APIError("Failed to create post")


@app.route('/social/<post_id>/like', methods=['POST', 'OPTIONS'])
@limiter.limit("60 per hour")
def toggle_like(post_id):
    """Toggle like on a post"""
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
    try:
        result = SocialService.toggle_like(post_id)
        return jsonify(result)
    except NotFoundError:
        raise NotFoundError("Post not found")
    except Exception as e:
        logger.error(f"Error toggling like: {e}")
        raise APIError("Failed to toggle like")


# ============================================================================
# ROUTES - APPOINTMENTS
# ============================================================================

@app.route('/appointments', methods=['GET', 'POST', 'OPTIONS'])
def handle_appointments():
    """Appointment management endpoints"""
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
    if request.method == 'GET':
        limiter.limit("100 per hour")(lambda: None)()
        
        client_id = request.args.get('user_id')
        barber_id = request.args.get('barber_id')
        user_type = request.args.get('type', 'client')
        
        if user_type == 'client' and client_id:
            appointments = AppointmentService.get_appointments(client_id=client_id)
        elif user_type == 'barber' and barber_id:
            appointments = AppointmentService.get_appointments(barber_id=barber_id)
        else:
            appointments = AppointmentService.get_appointments()
        
        return jsonify({"appointments": appointments})
    
    elif request.method == 'POST':
        limiter.limit("30 per hour")(lambda: None)()
        
        try:
            data = request.get_json()
            validated = validate_request(AppointmentCreate, data)
            
            appointment = AppointmentService.create_appointment(validated.dict())
            
            return jsonify({"success": True, "appointment": appointment}), 201
            
        except ValidationError as e:
            raise APIError(str(e), status_code=400)
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            raise APIError("Failed to create appointment")


@app.route('/appointments/<appointment_id>/status', methods=['PUT', 'OPTIONS'])
@limiter.limit("50 per hour")
def update_appointment_status(appointment_id):
    """Update appointment status"""
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
    try:
        data = request.get_json()
        validated = validate_request(AppointmentStatusUpdate, data)
        
        appointment = AppointmentService.update_status(appointment_id, validated.status)
        
        return jsonify({"success": True, "appointment": appointment})
        
    except NotFoundError:
        raise NotFoundError("Appointment not found")
    except Exception as e:
        logger.error(f"Error updating appointment: {e}")
        raise APIError("Failed to update appointment")


# ============================================================================
# ROUTES - BARBER DISCOVERY
# ============================================================================

@app.route('/barbers', methods=['GET', 'OPTIONS'])
@limiter.limit("50 per hour")
def get_barbers():
    """Find barbershops near location"""
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
    location = request.args.get('location', 'Atlanta, GA')
    styles = request.args.get('styles', '').split(',') if request.args.get('styles') else []
    
    try:
        # Validate location
        validated = validate_request(LocationQuery, {'location': location, 'styles': ','.join(styles)})
        
        result = PlacesService.find_barbers(validated.location, styles)
        result['location'] = location
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error finding barbers: {e}")
        # Return mock data on error
        mock_result = PlacesService._get_mock_barbers(location)
        mock_result['location'] = location
        return jsonify(mock_result)


@app.route('/search-barbers', methods=['GET', 'OPTIONS'])
@limiter.limit("50 per hour")
def search_barbers():
    """Search barbershops by name or location"""
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
    query = request.args.get('query', '')
    search_type = request.args.get('type', 'location')  # 'name' or 'location'
    
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400
    
    try:
        if search_type == 'name':
            # Search by business name
            result = PlacesService.search_by_name(query)
        else:
            # Default to location search
            result = PlacesService.find_barbers(query, [])
            
        result['query'] = query
        result['search_type'] = search_type
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error searching barbers: {e}")
        # Return empty result on error
        return jsonify({
            "barbers": [],
            "query": query,
            "search_type": search_type,
            "error": str(e)
        })


# ============================================================================
# ROUTES - PORTFOLIO
# ============================================================================

@app.route('/portfolio', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/portfolio/<barber_id>', methods=['GET', 'POST', 'OPTIONS'])
def portfolio(barber_id=None):
    """Portfolio management endpoints"""
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
    if request.method == 'GET':
        limiter.limit("100 per hour")(lambda: None)()
        portfolio_items = PortfolioService.get_portfolio(barber_id)
        return jsonify({"portfolio": portfolio_items})
    
    elif request.method == 'POST':
        limiter.limit("25 per hour")(lambda: None)()
        
        try:
            data = request.get_json()
            validated = validate_request(PortfolioItemCreate, data)
            
            item = PortfolioService.add_item(
                barber_id=validated.barber_id,
                style_name=validated.style_name,
                image=validated.image,
                description=validated.description
            )
            
            return jsonify({"success": True, "work": item}), 201
            
        except Exception as e:
            logger.error(f"Error adding portfolio item: {e}")
            raise APIError("Failed to add work")


# ============================================================================
# ROUTES - VIRTUAL TRY-ON
# ============================================================================

@app.route('/virtual-tryon', methods=['POST', 'OPTIONS'])
@limiter.limit("20 per hour")
def virtual_tryon():
    """Virtual hair try-on using HairFastGAN"""
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
    try:
        data = request.get_json()
        validated = validate_request(VirtualTryOnRequest, data)
        
        logger.info(f"🎨 Virtual try-on requested: {validated.styleDescription}")
        
        # Check if Modal endpoint is configured
        if not Config.MODAL_HAIRFAST_ENDPOINT:
            raise ExternalAPIError(
                'HairFastGAN',
                'Virtual try-on not configured. Please set MODAL_HAIRFAST_ENDPOINT.'
            )
        
        # Call Modal endpoint
        import requests
        response = requests.post(
            Config.MODAL_HAIRFAST_ENDPOINT,
            json={
                "face_image": validated.userPhoto,
                "style_description": validated.styleDescription
            },
            timeout=60
        )
        
        if response.status_code != 200:
            raise ExternalAPIError('HairFastGAN', f'Service error: {response.status_code}')
        
        result = response.json()
        
        if not result.get('success'):
            raise APIError(result.get('error', 'Transformation failed'))
        
        return jsonify(result)
        
    except ValidationError as e:
        raise APIError(str(e), status_code=400)
    except Exception as e:
        logger.error(f"Virtual try-on error: {e}")
        raise APIError(f"Virtual try-on failed: {str(e)}")


# ============================================================================
# ROUTES - SUBSCRIPTION PACKAGES
# ============================================================================

@app.route('/subscription-packages', methods=['GET', 'POST', 'OPTIONS'])
def handle_subscription_packages():
    """Subscription package management"""
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
    if request.method == 'GET':
        limiter.limit("100 per hour")(lambda: None)()
        barber_id = request.args.get('barber_id')
        packages = DatabaseService.get_all(models.DBSubscriptionPackage)
        if barber_id:
            packages = [p for p in packages if p.get('barber_id') == barber_id]
        return jsonify({"packages": packages})
    
    elif request.method == 'POST':
        limiter.limit("20 per hour")(lambda: None)()
        
        try:
            data = request.get_json()
            validated = validate_request(SubscriptionPackageCreate, data)
            
            from models import DBSubscriptionPackage
            import uuid
            from datetime import datetime
            
            package = DBSubscriptionPackage(
                id=str(uuid.uuid4()),
                barber_id=validated.barber_id,
                barber_name=validated.barber_name,
                title=validated.title,
                description=validated.description,
                price=validated.price,
                num_cuts=validated.num_cuts,
                duration_months=validated.duration_months,
                discount=validated.discount,
                timestamp=datetime.utcnow()
            )
            
            result = DatabaseService.save(package)
            return jsonify({"success": True, "package": result}), 201
            
        except Exception as e:
            logger.error(f"Error creating package: {e}")
            raise APIError("Failed to create package")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    port = Config.PORT
    logger.info(f"🚀 Starting LineUp API (Refactored) on port {port}")
    logger.info(f"📊 Configuration: {Config.get_status()}")
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)

