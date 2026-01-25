"""Repository for user profiles and saved analyses."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

from lineup_backend.db.repository import BaseRepository
from lineup_backend.db.models import UserModel, SavedAnalysisModel

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """Repository for user profiles."""
    
    def __init__(self):
        super().__init__("users")
    
    def create_user(self, user_id: str, email: str, display_name: str, role: str = "client",
                   avatar: Optional[str] = None, bio: Optional[str] = None) -> Optional[Dict]:
        """Create a new user profile."""
        user_data = UserModel(
            id=user_id,
            email=email,
            displayName=display_name,
            role=role,
            avatar=avatar,
            bio=bio,
            emailVerified=False,
            createdAt=datetime.now(),
            updatedAt=datetime.now()
        )
        
        data = user_data.model_dump(by_alias=True, exclude={"id"})
        result = self.create(user_id, data)
        
        if result:
            result["id"] = user_id
        return result
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user profile by ID."""
        return self.get_by_id(user_id)
    
    def update_user(self, user_id: str, data: Dict) -> Optional[Dict]:
        """Update user profile."""
        # Always update updatedAt
        data["updatedAt"] = datetime.now()
        return self.update(user_id, data)
    
    def set_role(self, user_id: str, role: str) -> Optional[Dict]:
        """Set user role."""
        return self.update(user_id, {"role": role, "updatedAt": datetime.now()})
    
    def get_users_by_role(self, role: str, limit: Optional[int] = None) -> List[Dict]:
        """Get all users with a specific role."""
        return self.query([("role", "==", role)], limit=limit)


class SavedAnalysisRepository(BaseRepository):
    """Repository for saved haircut analyses."""
    
    def __init__(self):
        super().__init__("saved_analyses")
    
    def save_analysis(self, user_id: str, image_url: Optional[str] = None,
                     image_base64: Optional[str] = None, recommendations: Optional[List[str]] = None,
                     face_shape: Optional[str] = None, hair_texture: Optional[str] = None,
                     analysis_data: Optional[Dict] = None) -> Optional[Dict]:
        """Save an analysis result."""
        import uuid
        analysis_id = str(uuid.uuid4())
        
        analysis = SavedAnalysisModel(
            id=analysis_id,
            userId=user_id,
            imageUrl=image_url,
            imageBase64=image_base64,
            recommendations=recommendations or [],
            faceShape=face_shape,
            hairTexture=hair_texture,
            analysisData=analysis_data or {},
            createdAt=datetime.now(),
            updatedAt=datetime.now()
        )
        
        data = analysis.model_dump(by_alias=True, exclude={"id"})
        result = self.create(analysis_id, data)
        
        if result:
            result["id"] = analysis_id
        return result
    
    def get_user_analyses(self, user_id: str, limit: Optional[int] = None) -> List[Dict]:
        """Get all saved analyses for a user."""
        return self.query([("userId", "==", user_id)], limit=limit, order_by="createdAt", direction="desc")
    
    def get_analysis(self, analysis_id: str) -> Optional[Dict]:
        """Get a saved analysis by ID."""
        return self.get_by_id(analysis_id)
    
    def delete_analysis(self, analysis_id: str, user_id: str) -> bool:
        """Delete a saved analysis (only if owned by user)."""
        analysis = self.get_by_id(analysis_id)
        if analysis and analysis.get("userId") == user_id:
            return self.delete(analysis_id)
        return False
