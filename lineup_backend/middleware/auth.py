"""Authentication middleware for Firebase Auth integration."""

from __future__ import annotations

import logging
from functools import wraps
from typing import Optional, Dict, Any, Callable

from flask import request, g

logger = logging.getLogger(__name__)

# Firebase Admin SDK (optional - graceful degradation)
try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth
    FIREBASE_AUTH_AVAILABLE = True
except ImportError:
    firebase_admin = None
    firebase_auth = None
    FIREBASE_AUTH_AVAILABLE = False
    logger.warning("Firebase Admin SDK not available. Auth will be disabled.")


class User:
    """Represents an authenticated user."""
    
    def __init__(
        self,
        uid: str,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        role: str = "client",
        email_verified: bool = False,
        custom_claims: Optional[Dict[str, Any]] = None
    ):
        self.uid = uid
        self.email = email
        self.display_name = display_name
        self.role = role
        self.email_verified = email_verified
        self.custom_claims = custom_claims or {}
    
    @property
    def is_barber(self) -> bool:
        return self.role == "barber"
    
    @property
    def is_client(self) -> bool:
        return self.role == "client"
    
    @property
    def is_admin(self) -> bool:
        return self.custom_claims.get("admin", False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uid": self.uid,
            "email": self.email,
            "displayName": self.display_name,
            "role": self.role,
            "emailVerified": self.email_verified,
        }
    
    @classmethod
    def from_firebase_token(cls, decoded_token: Dict[str, Any]) -> "User":
        """Create a User from a decoded Firebase token."""
        custom_claims = decoded_token.get("custom_claims", {})
        return cls(
            uid=decoded_token.get("uid", ""),
            email=decoded_token.get("email"),
            display_name=decoded_token.get("name"),
            role=custom_claims.get("role", "client"),
            email_verified=decoded_token.get("email_verified", False),
            custom_claims=custom_claims
        )


def get_current_user() -> Optional[User]:
    """Get the current authenticated user from the request context."""
    return getattr(g, 'current_user', None)


def _extract_token_from_header() -> Optional[str]:
    """Extract the Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header:
        return None
    
    parts = auth_header.split()
    
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1]


def _verify_firebase_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify a Firebase ID token and return the decoded claims."""
    if not FIREBASE_AUTH_AVAILABLE or not firebase_auth:
        logger.warning("Firebase Auth not available, skipping token verification")
        return None
    
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token
    except firebase_auth.InvalidIdTokenError:
        logger.warning("Invalid Firebase ID token")
        return None
    except firebase_auth.ExpiredIdTokenError:
        logger.warning("Expired Firebase ID token")
        return None
    except firebase_auth.RevokedIdTokenError:
        logger.warning("Revoked Firebase ID token")
        return None
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {str(e)}")
        return None


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for an endpoint.
    
    Usage:
        @app.route('/protected')
        @require_auth
        def protected_endpoint():
            user = get_current_user()
            return jsonify({"user": user.to_dict()})
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check if auth is disabled (development mode)
        from lineup_backend.config import AppConfig
        import os
        config = AppConfig.from_env()
        
        if config.flask_env == "development" and os.environ.get("LINEUP_DISABLE_AUTH") == "true":
            # Create a mock user for development
            g.current_user = User(
                uid="dev_user",
                email="dev@lineup.com",
                display_name="Development User",
                role="client"
            )
            return func(*args, **kwargs)
        
        # Extract and verify token
        token = _extract_token_from_header()
        
        if not token:
            from .error_handler import AuthenticationError
            raise AuthenticationError("Missing authentication token")
        
        decoded_token = _verify_firebase_token(token)
        
        if not decoded_token:
            from .error_handler import AuthenticationError
            raise AuthenticationError("Invalid or expired authentication token")
        
        # Set the current user in the request context
        g.current_user = User.from_firebase_token(decoded_token)
        
        return func(*args, **kwargs)
    
    return wrapper


def optional_auth(func: Callable) -> Callable:
    """
    Decorator for optional authentication.
    Sets current_user if a valid token is provided, but doesn't require it.
    
    Usage:
        @app.route('/public')
        @optional_auth
        def public_endpoint():
            user = get_current_user()
            if user:
                return jsonify({"message": f"Hello, {user.display_name}!"})
            return jsonify({"message": "Hello, guest!"})
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = _extract_token_from_header()
        
        if token:
            decoded_token = _verify_firebase_token(token)
            if decoded_token:
                g.current_user = User.from_firebase_token(decoded_token)
        
        return func(*args, **kwargs)
    
    return wrapper


def require_role(role: str) -> Callable:
    """
    Decorator to require a specific role for an endpoint.
    Must be used after @require_auth.
    
    Usage:
        @app.route('/barber-only')
        @require_auth
        @require_role('barber')
        def barber_only_endpoint():
            return jsonify({"message": "Welcome, barber!"})
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            
            if not user:
                from .error_handler import AuthenticationError
                raise AuthenticationError()
            
            if user.role != role and not user.is_admin:
                from .error_handler import AuthorizationError
                raise AuthorizationError(f"This action requires {role} role")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_owner_or_admin(get_owner_id: Callable) -> Callable:
    """
    Decorator to require that the user is the owner of the resource or an admin.
    
    Usage:
        def get_appointment_owner(appointment_id):
            # Logic to get owner ID from appointment
            return "user_123"
        
        @app.route('/appointments/<appointment_id>')
        @require_auth
        @require_owner_or_admin(get_appointment_owner)
        def update_appointment(appointment_id):
            return jsonify({"message": "Updated!"})
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            
            if not user:
                from .error_handler import AuthenticationError
                raise AuthenticationError()
            
            # Admin can do anything
            if user.is_admin:
                return func(*args, **kwargs)
            
            # Check if user is the owner
            owner_id = get_owner_id(*args, **kwargs)
            
            if owner_id and user.uid != owner_id:
                from .error_handler import AuthorizationError
                raise AuthorizationError("You can only modify your own resources")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def set_user_role(uid: str, role: str) -> bool:
    """
    Set a custom role for a user in Firebase.
    
    Args:
        uid: The Firebase user ID
        role: The role to set ('client' or 'barber')
    
    Returns:
        True if successful, False otherwise
    """
    if not FIREBASE_AUTH_AVAILABLE or not firebase_auth:
        logger.warning("Firebase Auth not available, cannot set user role")
        return False
    
    try:
        firebase_auth.set_custom_user_claims(uid, {"role": role})
        logger.info(f"Set role '{role}' for user {uid}")
        return True
    except Exception as e:
        logger.error(f"Error setting user role: {str(e)}")
        return False

