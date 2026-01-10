"""Health and status endpoints."""

from datetime import datetime
from flask import Blueprint, jsonify, request

from lineup_backend.utils import cors_response, handle_options

health_bp = Blueprint('health', __name__)


@health_bp.route('/')
def index():
    """Root endpoint with API information."""
    return cors_response({
        "service": "LineUp AI Backend",
        "status": "running",
        "version": "2.1",
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


@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    from lineup_backend import storage as memory_store
    
    # Import here to avoid circular imports
    import os
    
    return cors_response({
        "status": "healthy",
        "service": "lineup-backend",
        "timestamp": datetime.now().isoformat(),
        "cors_enabled": True,
        "gemini_configured": bool(os.environ.get("GEMINI_API_KEY")),
        "places_api_configured": bool(os.environ.get("GOOGLE_PLACES_API_KEY")),
        "frontend_url": "https://lineupai.onrender.com",
        "data_counts": {
            "social_posts": len(memory_store.social_posts),
            "appointments": len(memory_store.appointments),
            "barber_portfolios": len(memory_store.barber_portfolios)
        }
    })


@health_bp.route('/config', methods=['GET', 'OPTIONS'])
@handle_options("GET, OPTIONS")
def get_config():
    """
    Public configuration endpoint.
    NOTE: Never expose API keys here - only feature flags and public info.
    """
    import os
    
    return cors_response({
        "hasPlacesApi": bool(os.environ.get("GOOGLE_PLACES_API_KEY")),
        "backendVersion": "2.1",
        "features": {
            "virtualTryOn": bool(os.environ.get("REPLICATE_API_TOKEN")),
            "aiAnalysis": bool(os.environ.get("GEMINI_API_KEY")),
            "cloudinaryStorage": bool(os.environ.get("CLOUDINARY_CLOUD_NAME")),
        }
    })

