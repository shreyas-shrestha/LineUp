"""Repository for barber reviews."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from lineup_backend.db.repository import BaseRepository
from lineup_backend.db.models import ReviewModel

logger = logging.getLogger(__name__)


class ReviewRepository(BaseRepository):
    """Repository for barber reviews."""
    
    def __init__(self):
        super().__init__("barber_reviews")
    
    def create_review(self, barber_id: str, client_id: str, rating: int, text: str = "",
                     client_name: Optional[str] = None) -> Optional[Dict]:
        """Create a new review."""
        review_id = str(uuid.uuid4())
        
        review = ReviewModel(
            id=review_id,
            barberId=barber_id,
            clientId=client_id,
            clientName=client_name,
            rating=rating,
            text=text,
            timestamp=datetime.now()
        )
        
        data = review.model_dump(by_alias=True, exclude={"id"})
        result = self.create(review_id, data)
        
        if result:
            result["id"] = review_id
        return result
    
    def get_reviews(self, barber_id: str, limit: Optional[int] = None) -> List[Dict]:
        """Get reviews for a barber."""
        return self.query([("barberId", "==", barber_id)], limit=limit, order_by="timestamp", direction="desc")
    
    def get_review(self, review_id: str) -> Optional[Dict]:
        """Get a review by ID."""
        return self.get_by_id(review_id)
    
    def get_barber_rating_stats(self, barber_id: str) -> Dict[str, float]:
        """Get rating statistics for a barber."""
        reviews = self.get_reviews(barber_id)
        
        if not reviews:
            return {
                "average": 0.0,
                "total": 0,
                "distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }
        
        ratings = [r.get("rating", 0) for r in reviews]
        total = len(ratings)
        average = sum(ratings) / total if total > 0 else 0.0
        
        distribution = {i: 0 for i in range(1, 6)}
        for rating in ratings:
            if 1 <= rating <= 5:
                distribution[rating] = distribution.get(rating, 0) + 1
        
        return {
            "average": round(average, 2),
            "total": total,
            "distribution": distribution
        }
