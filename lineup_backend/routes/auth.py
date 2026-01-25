"""Authentication endpoints for user registration, login, and profile management."""

from __future__ import annotations

import logging
from typing import Dict, Any

from flask import Blueprint, request

from lineup_backend.middleware.auth import require_auth, get_current_user, set_user_role
from lineup_backend.middleware.error_handler import AuthenticationError, ValidationError as APIValidationError
from lineup_backend.utils import cors_response, handle_options, api_response, safe_get_json
from lineup_backend.db.repositories import UserRepository
from lineup_backend.schemas.auth import (
    UserCreate,
    UserLogin,
    ProfileUpdate,
)

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)
user_repo = UserRepository()


@auth_bp.route('/auth/register', methods=['POST', 'OPTIONS'])
@handle_options("POST, OPTIONS")
def register():
    """
    Register a new user.
    
    Note: This endpoint creates a user profile in Firestore.
    Actual Firebase Auth user creation should be done on the frontend using Firebase Auth SDK.
    This endpoint assumes the user is already created in Firebase Auth and provides the ID token.
    """
    try:
        data = safe_get_json()
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header or not auth_header.startswith("Bearer "):
            return api_response(
                error="Missing or invalid Authorization header. Use Firebase Auth SDK to create user first.",
                status=400
            )
        
        token = auth_header.split("Bearer ")[1]
        
        # Verify token and get user info
        from lineup_backend.middleware.auth import _verify_firebase_token
        decoded_token = _verify_firebase_token(token)
        
        if not decoded_token:
            return api_response(error="Invalid or expired token", status=401)
        
        uid = decoded_token.get("uid")
        email = decoded_token.get("email", data.get("email", ""))
        display_name = data.get("displayName", decoded_token.get("name", "User"))
        role = data.get("role", "client")
        
        # Validate role
        if role not in ["client", "barber"]:
            role = "client"
        
        # Check if user already exists
        existing_user = user_repo.get_user(uid)
        if existing_user:
            return api_response(
                error="User already exists",
                status=400
            )
        
        # Create user profile
        user_data = user_repo.create_user(
            user_id=uid,
            email=email,
            display_name=display_name,
            role=role,
            avatar=data.get("avatar"),
            bio=data.get("bio")
        )
        
        if not user_data:
            return api_response(error="Failed to create user profile", status=500)
        
        # Set role in Firebase Auth custom claims
        if role == "barber":
            set_user_role(uid, "barber")
        
        logger.info(f"User registered: {uid} ({role})")
        
        return api_response(
            data={"user": user_data},
            message="User registered successfully",
            status=201
        )
        
    except Exception as e:
        logger.error(f"Error in register: {str(e)}")
        return api_response(error="Registration failed", status=400)


@auth_bp.route('/auth/me', methods=['GET', 'OPTIONS'])
@handle_options("GET, OPTIONS")
@require_auth
def get_current_user_profile():
    """Get current authenticated user's profile."""
    try:
        user = get_current_user()
        if not user:
            raise AuthenticationError("User not found")
        
        # Get full profile from database
        user_profile = user_repo.get_user(user.uid)
        
        if not user_profile:
            # Create profile if it doesn't exist
            user_profile = user_repo.create_user(
                user_id=user.uid,
                email=user.email or "",
                display_name=user.display_name or "User",
                role=user.role
            )
        
        return api_response(data={"user": user_profile})
        
    except AuthenticationError as e:
        return api_response(error=str(e), status=401)
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        return api_response(error="Failed to get user profile", status=500)


@auth_bp.route('/auth/me', methods=['PUT', 'OPTIONS'])
@handle_options("PUT, OPTIONS")
@require_auth
def update_current_user_profile():
    """Update current authenticated user's profile."""
    try:
        user = get_current_user()
        if not user:
            raise AuthenticationError("User not found")
        
        data = safe_get_json()
        
        # Validate update data
        try:
            update_schema = ProfileUpdate(**data)
            update_data = update_schema.model_dump(exclude_unset=True, by_alias=True)
        except Exception as e:
            return api_response(error=f"Validation error: {str(e)}", status=400)
        
        # Update user profile
        updated_user = user_repo.update_user(user.uid, update_data)
        
        if not updated_user:
            return api_response(error="Failed to update profile", status=500)
        
        logger.info(f"User profile updated: {user.uid}")
        
        return api_response(
            data={"user": updated_user},
            message="Profile updated successfully"
        )
        
    except AuthenticationError as e:
        return api_response(error=str(e), status=401)
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        return api_response(error="Failed to update profile", status=500)


@auth_bp.route('/auth/role', methods=['POST', 'OPTIONS'])
@handle_options("POST, OPTIONS")
@require_auth
def set_role():
    """
    Set user role (admin only, or user setting their own role initially).
    """
    try:
        user = get_current_user()
        if not user:
            raise AuthenticationError("User not found")
        
        data = safe_get_json()
        target_user_id = data.get("userId", user.uid)
        new_role = data.get("role")
        
        if new_role not in ["client", "barber"]:
            return api_response(error="Invalid role. Must be 'client' or 'barber'", status=400)
        
        # Check permissions: admin can set anyone's role, users can only set their own initially
        if target_user_id != user.uid and not user.is_admin:
            from lineup_backend.middleware.error_handler import AuthorizationError
            raise AuthorizationError("Only admins can set other users' roles")
        
        # Update role in database
        updated_user = user_repo.set_role(target_user_id, new_role)
        
        if not updated_user:
            return api_response(error="Failed to update role", status=500)
        
        # Update Firebase Auth custom claims
        set_user_role(target_user_id, new_role)
        
        logger.info(f"Role updated: {target_user_id} -> {new_role}")
        
        return api_response(
            data={"user": updated_user},
            message="Role updated successfully"
        )
        
    except AuthenticationError as e:
        return api_response(error=str(e), status=401)
    except Exception as e:
        logger.error(f"Error setting role: {str(e)}")
        return api_response(error="Failed to set role", status=500)
