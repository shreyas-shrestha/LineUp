"""Repository for barber metrics and analytics."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from lineup_backend.db.repository import BaseRepository
from lineup_backend.db.models import BarberMetricModel, BarberEventModel

logger = logging.getLogger(__name__)


class MetricsRepository(BaseRepository):
    """Repository for barber metrics aggregates."""
    
    def __init__(self):
        super().__init__("barber_metrics")
    
    def create_metric(self, barber_id: str, metric_type: str, period: str, date: str,
                     value: float, metadata: Optional[Dict] = None) -> Optional[Dict]:
        """Create or update a metric."""
        metric_id = f"{barber_id}_{metric_type}_{period}_{date}"
        
        metric = BarberMetricModel(
            id=metric_id,
            barberId=barber_id,
            metricType=metric_type,
            period=period,
            date=date,
            value=value,
            metadata=metadata or {},
            createdAt=datetime.now(),
            updatedAt=datetime.now()
        )
        
        data = metric.model_dump(by_alias=True, exclude={"id"})
        result = self.create(metric_id, data)
        
        if result:
            result["id"] = metric_id
        return result
    
    def update_metric(self, barber_id: str, metric_type: str, period: str, date: str,
                     value: float, metadata: Optional[Dict] = None) -> Optional[Dict]:
        """Update an existing metric."""
        metric_id = f"{barber_id}_{metric_type}_{period}_{date}"
        return self.update(metric_id, {
            "value": value,
            "metadata": metadata or {},
            "updatedAt": datetime.now()
        })
    
    def get_metrics(self, barber_id: str, metric_type: Optional[str] = None,
                   period: Optional[str] = None, start_date: Optional[str] = None,
                   end_date: Optional[str] = None, limit: Optional[int] = None) -> List[Dict]:
        """Get metrics with filters."""
        filters = [("barberId", "==", barber_id)]
        
        if metric_type:
            filters.append(("metricType", "==", metric_type))
        
        if period:
            filters.append(("period", "==", period))
        
        if start_date:
            filters.append(("date", ">=", start_date))
        
        if end_date:
            filters.append(("date", "<=", end_date))
        
        return self.query(filters, limit=limit, order_by="date", direction="desc")
    
    def get_metric(self, barber_id: str, metric_type: str, period: str, date: str) -> Optional[Dict]:
        """Get a specific metric."""
        metric_id = f"{barber_id}_{metric_type}_{period}_{date}"
        return self.get_by_id(metric_id)


class EventRepository(BaseRepository):
    """Repository for barber events (for detailed analytics)."""
    
    def __init__(self):
        super().__init__("barber_events")
    
    def create_event(self, barber_id: str, event_type: str, data: Optional[Dict] = None,
                    user_id: Optional[str] = None) -> Optional[Dict]:
        """Create an event record."""
        event_id = str(uuid.uuid4())
        
        event = BarberEventModel(
            id=event_id,
            barberId=barber_id,
            eventType=event_type,
            timestamp=datetime.now(),
            data=data or {},
            userId=user_id
        )
        
        event_data = event.model_dump(by_alias=True, exclude={"id"})
        result = self.create(event_id, event_data)
        
        if result:
            result["id"] = event_id
        return result
    
    def get_events(self, barber_id: str, event_type: Optional[str] = None,
                  start_time: Optional[datetime] = None, end_time: Optional[datetime] = None,
                  limit: Optional[int] = None) -> List[Dict]:
        """Get events with filters."""
        filters = [("barberId", "==", barber_id)]
        
        if event_type:
            filters.append(("eventType", "==", event_type))
        
        if start_time:
            filters.append(("timestamp", ">=", start_time))
        
        if end_time:
            filters.append(("timestamp", "<=", end_time))
        
        return self.query(filters, limit=limit, order_by="timestamp", direction="desc")
    
    def count_events(self, barber_id: str, event_type: Optional[str] = None,
                    start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> int:
        """Count events matching filters."""
        filters = [("barberId", "==", barber_id)]
        
        if event_type:
            filters.append(("eventType", "==", event_type))
        
        if start_time:
            filters.append(("timestamp", ">=", start_time))
        
        if end_time:
            filters.append(("timestamp", "<=", end_time))
        
        return self.count(filters)
