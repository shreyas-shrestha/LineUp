"""Endpoints for saving and retrieving haircut analysis results."""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional

from flask import Blueprint, request

from lineup_backend.middleware.auth import require_auth, get_current_user
from lineup_backend.middleware.error_handler import AuthenticationError
from lineup_backend.utils import cors_response, handle_options, api_response, safe_get_json
from lineup_backend.db.repositories import SavedAnalysisRepository

logger = logging.getLogger(__name__)

analyze_bp = Blueprint('analyze', __name__)
analysis_repo = SavedAnalysisRepository()


@analyze_bp.route('/analyze/save', methods=['POST', 'OPTIONS'])
@handle_options("POST, OPTIONS")
@require_auth
def save_analysis():
    """
    Save haircut analysis results.
    Requires authentication.
    """
    try:
        user = get_current_user()
        if not user:
            raise AuthenticationError("Authentication required to save analysis")
        
        data = safe_get_json()
        
        # Validate required fields
        if not data.get("recommendations") and not data.get("analysisData"):
            return api_response(
                error="Analysis data or recommendations required",
                status=400
            )
        
        # Save analysis
        saved_analysis = analysis_repo.save_analysis(
            user_id=user.uid,
            image_url=data.get("imageUrl"),
            image_base64=data.get("imageBase64"),
            recommendations=data.get("recommendations", []),
            face_shape=data.get("faceShape"),
            hair_texture=data.get("hairTexture"),
            analysis_data=data.get("analysisData", {})
        )
        
        if not saved_analysis:
            return api_response(error="Failed to save analysis", status=500)
        
        logger.info(f"Analysis saved: {saved_analysis.get('id')} for user {user.uid}")
        
        return api_response(
            data={"analysis": saved_analysis},
            message="Analysis saved successfully",
            status=201
        )
        
    except AuthenticationError as e:
        return api_response(error=str(e), status=401)
    except Exception as e:
        logger.error(f"Error saving analysis: {str(e)}")
        return api_response(error="Failed to save analysis", status=500)


@analyze_bp.route('/analyze/history', methods=['GET', 'OPTIONS'])
@handle_options("GET, OPTIONS")
@require_auth
def get_analysis_history():
    """
    Get saved analysis history for current user.
    Requires authentication.
    """
    try:
        user = get_current_user()
        if not user:
            raise AuthenticationError("Authentication required")
        
        limit = request.args.get('limit', type=int)
        if limit and limit > 100:
            limit = 100
        
        analyses = analysis_repo.get_user_analyses(user.uid, limit=limit)
        
        return api_response(data={"analyses": analyses})
        
    except AuthenticationError as e:
        return api_response(error=str(e), status=401)
    except Exception as e:
        logger.error(f"Error getting analysis history: {str(e)}")
        return api_response(error="Failed to get analysis history", status=500)


@analyze_bp.route('/analyze/<analysis_id>', methods=['GET', 'OPTIONS'])
@handle_options("GET, OPTIONS")
@require_auth
def get_analysis(analysis_id: str):
    """
    Get a specific saved analysis.
    Requires authentication and ownership.
    """
    try:
        user = get_current_user()
        if not user:
            raise AuthenticationError("Authentication required")
        
        analysis = analysis_repo.get_analysis(analysis_id)
        
        if not analysis:
            return api_response(error="Analysis not found", status=404)
        
        # Check ownership
        if analysis.get("userId") != user.uid:
            from lineup_backend.middleware.error_handler import AuthorizationError
            raise AuthorizationError("You can only access your own analyses")
        
        return api_response(data={"analysis": analysis})
        
    except AuthenticationError as e:
        return api_response(error=str(e), status=401)
    except Exception as e:
        logger.error(f"Error getting analysis: {str(e)}")
        return api_response(error="Failed to get analysis", status=500)


@analyze_bp.route('/analyze/<analysis_id>', methods=['DELETE', 'OPTIONS'])
@handle_options("DELETE, OPTIONS")
@require_auth
def delete_analysis(analysis_id: str):
    """
    Delete a saved analysis.
    Requires authentication and ownership.
    """
    try:
        user = get_current_user()
        if not user:
            raise AuthenticationError("Authentication required")
        
        success = analysis_repo.delete_analysis(analysis_id, user.uid)
        
        if not success:
            return api_response(error="Analysis not found or unauthorized", status=404)
        
        logger.info(f"Analysis deleted: {analysis_id} by user {user.uid}")
        
        return api_response(message="Analysis deleted successfully")
        
    except AuthenticationError as e:
        return api_response(error=str(e), status=401)
    except Exception as e:
        logger.error(f"Error deleting analysis: {str(e)}")
        return api_response(error="Failed to delete analysis", status=500)
