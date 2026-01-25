"""Repository for barber portfolios."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from lineup_backend.db.repository import BaseRepository
from lineup_backend.db.models import PortfolioModel

logger = logging.getLogger(__name__)


class PortfolioRepository(BaseRepository):
    """Repository for barber portfolios."""
    
    def __init__(self):
        super().__init__("barber_portfolios")
    
    def create_portfolio_item(self, barber_id: str, style_name: str, image: str,
                             description: str = "") -> Optional[Dict]:
        """Create a new portfolio item."""
        portfolio_id = str(uuid.uuid4())
        
        portfolio = PortfolioModel(
            id=portfolio_id,
            barberId=barber_id,
            styleName=style_name,
            image=image,
            description=description,
            likes=0,
            date=datetime.now().strftime("%Y-%m-%d"),
            timestamp=datetime.now()
        )
        
        data = portfolio.model_dump(by_alias=True, exclude={"id"})
        result = self.create(portfolio_id, data)
        
        if result:
            result["id"] = portfolio_id
        return result
    
    def get_portfolio(self, barber_id: Optional[str] = None, limit: Optional[int] = None) -> List[Dict]:
        """Get portfolio items, optionally filtered by barber."""
        if barber_id:
            return self.query([("barberId", "==", barber_id)], limit=limit, order_by="timestamp", direction="desc")
        else:
            return self.get_all(limit=limit, order_by="timestamp", direction="desc")
    
    def get_portfolio_item(self, portfolio_id: str) -> Optional[Dict]:
        """Get a single portfolio item by ID."""
        return self.get_by_id(portfolio_id)
    
    def update_portfolio_item(self, portfolio_id: str, data: Dict) -> Optional[Dict]:
        """Update a portfolio item."""
        return self.update(portfolio_id, data)
    
    def delete_portfolio_item(self, portfolio_id: str, barber_id: str) -> bool:
        """Delete a portfolio item (only if owned by barber)."""
        item = self.get_by_id(portfolio_id)
        if item and item.get("barberId") == barber_id:
            return self.delete(portfolio_id)
        return False
    
    def increment_likes(self, portfolio_id: str) -> Optional[Dict]:
        """Increment likes on a portfolio item."""
        item = self.get_by_id(portfolio_id)
        if item:
            current_likes = item.get("likes", 0)
            return self.update(portfolio_id, {"likes": current_likes + 1})
        return None
