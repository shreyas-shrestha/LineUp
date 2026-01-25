"""Repository for notifications."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from lineup_backend.db.repository import BaseRepository
from lineup_backend.db.models import NotificationModel

logger = logging.getLogger(__name__)


class NotificationRepository(BaseRepository):
    """Repository for user notifications."""
    
    def __init__(self):
        super().__init__("notifications")
    
    def create_notification(self, user_id: str, notification_type: str, title: str,
                           message: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Create a new notification."""
        notification_id = str(uuid.uuid4())
        
        notification = NotificationModel(
            id=notification_id,
            userId=user_id,
            type=notification_type,
            title=title,
            message=message,
            data=data or {},
            read=False,
            createdAt=datetime.now()
        )
        
        notification_data = notification.model_dump(by_alias=True, exclude={"id"})
        result = self.create(notification_id, notification_data)
        
        if result:
            result["id"] = notification_id
        return result
    
    def get_user_notifications(self, user_id: str, unread_only: bool = False,
                              limit: Optional[int] = None) -> List[Dict]:
        """Get notifications for a user."""
        filters = [("userId", "==", user_id)]
        if unread_only:
            filters.append(("read", "==", False))
        
        return self.query(filters, limit=limit, order_by="createdAt", direction="desc")
    
    def mark_as_read(self, notification_id: str, user_id: str) -> Optional[Dict]:
        """Mark a notification as read."""
        notification = self.get_by_id(notification_id)
        if notification and notification.get("userId") == user_id:
            return self.update(notification_id, {"read": True})
        return None
    
    def mark_all_as_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user."""
        notifications = self.get_user_notifications(user_id, unread_only=True)
        count = 0
        
        for notification in notifications:
            if self.update(notification["id"], {"read": True}):
                count += 1
        
        return count
    
    def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications for a user."""
        return self.count([("userId", "==", user_id), ("read", "==", False)])
    
    def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Delete a notification (only if owned by user)."""
        notification = self.get_by_id(notification_id)
        if notification and notification.get("userId") == user_id:
            return self.delete(notification_id)
        return False
