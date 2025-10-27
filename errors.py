# errors.py - Centralized Error Handling
from flask import jsonify
import logging

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base API exception with structured error responses"""
    
    def __init__(self, message: str, status_code: int = 400, payload: dict = None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}
    
    def to_dict(self):
        """Convert error to JSON-serializable dict"""
        rv = dict(self.payload)
        rv['error'] = self.message
        rv['status'] = self.status_code
        return rv


class ValidationError(APIError):
    """Input validation failed"""
    def __init__(self, message: str, errors: list = None):
        super().__init__(message, status_code=400, payload={'validation_errors': errors or []})


class NotFoundError(APIError):
    """Resource not found"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class UnauthorizedError(APIError):
    """Authentication required"""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)


class RateLimitError(APIError):
    """Rate limit exceeded"""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(message, status_code=429, payload={'retry_after': retry_after})


class ExternalAPIError(APIError):
    """External API call failed"""
    def __init__(self, service: str, message: str = "External service unavailable"):
        super().__init__(
            message, 
            status_code=503,
            payload={'service': service, 'fallback': 'Using cached or mock data'}
        )


def register_error_handlers(app):
    """Register all error handlers with Flask app"""
    
    @app.errorhandler(APIError)
    def handle_api_error(error):
        """Handle custom API errors"""
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        response.headers['Access-Control-Allow-Origin'] = '*'
        logger.warning(f"API Error: {error.message} (Status: {error.status_code})")
        return response
    
    @app.errorhandler(404)
    def handle_404(error):
        """Handle 404 Not Found"""
        response = jsonify({
            'error': 'Resource not found',
            'status': 404,
            'message': 'The requested endpoint does not exist'
        })
        response.status_code = 404
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    @app.errorhandler(500)
    def handle_500(error):
        """Handle 500 Internal Server Error"""
        logger.error(f"Internal server error: {str(error)}")
        response = jsonify({
            'error': 'Internal server error',
            'status': 500,
            'message': 'Something went wrong. Please try again later.'
        })
        response.status_code = 500
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    @app.errorhandler(429)
    def handle_rate_limit(error):
        """Handle rate limit exceeded"""
        response = jsonify({
            'error': 'Rate limit exceeded',
            'status': 429,
            'message': 'Too many requests. Please slow down.',
            'retry_after': getattr(error, 'description', 60)
        })
        response.status_code = 429
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Catch-all for unexpected errors"""
        logger.error(f"Unexpected error: {str(error)}", exc_info=True)
        response = jsonify({
            'error': 'Unexpected error occurred',
            'status': 500,
            'message': 'An unexpected error occurred. Please try again.'
        })
        response.status_code = 500
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response


def validate_request(model_class, data: dict):
    """
    Validate request data against Pydantic model
    
    Args:
        model_class: Pydantic model class
        data: Request data dictionary
    
    Returns:
        Validated model instance
    
    Raises:
        ValidationError: If validation fails
    """
    try:
        return model_class(**data)
    except Exception as e:
        # Extract validation errors from Pydantic
        if hasattr(e, 'errors'):
            error_messages = []
            for error in e.errors():
                field = '.'.join(str(x) for x in error['loc'])
                message = error['msg']
                error_messages.append(f"{field}: {message}")
            raise ValidationError(
                "Validation failed",
                errors=error_messages
            )
        raise ValidationError(str(e))

