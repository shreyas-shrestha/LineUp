"""Portfolio management endpoints for barbers."""

import logging
import uuid
from datetime import datetime

from flask import Blueprint, request

from lineup_backend.utils import cors_response, handle_options, api_response, safe_get_json
from lineup_backend import storage as memory_store

logger = logging.getLogger(__name__)

portfolio_bp = Blueprint('portfolio', __name__)


@portfolio_bp.route('/portfolio', methods=['GET', 'POST', 'OPTIONS'])
@portfolio_bp.route('/portfolio/<barber_id>', methods=['GET', 'POST', 'OPTIONS'])
@handle_options("GET, POST, OPTIONS")
def portfolio(barber_id=None):
    """
    Handle portfolio viewing and creation.
    
    GET: Retrieve portfolio items (optionally filtered by barber_id)
    POST: Add new portfolio item
    """
    if request.method == 'GET':
        return get_portfolio(barber_id)
    elif request.method == 'POST':
        return create_portfolio_item(barber_id)


def get_portfolio(barber_id: str = None):
    """Get portfolio items for a barber or all portfolios."""
    try:
        if barber_id:
            portfolio = memory_store.barber_portfolios.get(barber_id, [])
        else:
            # Return all portfolios flattened
            portfolio = []
            for barber_portfolio in memory_store.barber_portfolios.values():
                portfolio.extend(barber_portfolio)
        
        return api_response(data={"portfolio": portfolio})
    except Exception as e:
        logger.error(f"Error getting portfolio: {str(e)}")
        return api_response(error="Failed to get portfolio", status=500)


def create_portfolio_item(barber_id: str = None):
    """Create a new portfolio item."""
    try:
        data = safe_get_json()
        
        # Get barber_id from URL or request body
        bid = barber_id or data.get("barberId", "default_barber")
        
        # Validate required fields
        if not data.get("styleName"):
            return api_response(error="Style name is required", status=400)
        
        if not data.get("image"):
            return api_response(error="Image is required", status=400)
        
        new_work = {
            "id": str(uuid.uuid4()),
            "styleName": data.get("styleName", ""),
            "image": data.get("image", ""),
            "description": data.get("description", ""),
            "likes": 0,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "barberId": bid,
            "timestamp": datetime.now().isoformat()
        }
        
        # Initialize barber portfolio if doesn't exist
        if bid not in memory_store.barber_portfolios:
            memory_store.barber_portfolios[bid] = []
        
        # Add to beginning of list (most recent first)
        memory_store.barber_portfolios[bid].insert(0, new_work)
        
        logger.info(f"Portfolio item created: {new_work['id']} for barber {bid}")
        return api_response(
            data={"work": new_work},
            message="Portfolio item added successfully",
            status=201
        )
        
    except Exception as e:
        logger.error(f"Error adding portfolio work: {str(e)}")
        return api_response(error="Failed to add portfolio item", status=500)


@portfolio_bp.route('/portfolio/<barber_id>/<work_id>', methods=['DELETE', 'OPTIONS'])
@handle_options("DELETE, OPTIONS")
def delete_portfolio_item(barber_id: str, work_id: str):
    """Delete a portfolio item."""
    try:
        if barber_id not in memory_store.barber_portfolios:
            return api_response(error="Barber portfolio not found", status=404)
        
        portfolio = memory_store.barber_portfolios[barber_id]
        original_length = len(portfolio)
        
        memory_store.barber_portfolios[barber_id] = [
            item for item in portfolio if item.get("id") != work_id
        ]
        
        if len(memory_store.barber_portfolios[barber_id]) == original_length:
            return api_response(error="Portfolio item not found", status=404)
        
        logger.info(f"Portfolio item deleted: {work_id}")
        return api_response(message="Portfolio item deleted successfully")
        
    except Exception as e:
        logger.error(f"Error deleting portfolio item: {str(e)}")
        return api_response(error="Failed to delete portfolio item", status=500)


@portfolio_bp.route('/portfolio/<barber_id>/<work_id>/like', methods=['POST', 'OPTIONS'])
@handle_options("POST, OPTIONS")
def like_portfolio_item(barber_id: str, work_id: str):
    """Like a portfolio item."""
    try:
        if barber_id not in memory_store.barber_portfolios:
            return api_response(error="Barber portfolio not found", status=404)
        
        for item in memory_store.barber_portfolios[barber_id]:
            if item.get("id") == work_id:
                item["likes"] = item.get("likes", 0) + 1
                return api_response(
                    data={"likes": item["likes"]},
                    message="Portfolio item liked"
                )
        
        return api_response(error="Portfolio item not found", status=404)
        
    except Exception as e:
        logger.error(f"Error liking portfolio item: {str(e)}")
        return api_response(error="Failed to like portfolio item", status=500)

