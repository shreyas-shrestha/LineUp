"""Repository for appointments."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from lineup_backend.db.repository import BaseRepository
from lineup_backend.db.models import AppointmentModel

logger = logging.getLogger(__name__)


class AppointmentRepository(BaseRepository):
    """Repository for appointments."""
    
    def __init__(self):
        super().__init__("appointments")
    
    def create_appointment(self, client_id: str, client_name: str, barber_id: str,
                          barber_name: str, date: str, time: str, service: str = "",
                          price: str = "$0", notes: str = "") -> Optional[Dict]:
        """Create a new appointment."""
        appointment_id = str(uuid.uuid4())
        
        appointment = AppointmentModel(
            id=appointment_id,
            clientId=client_id,
            clientName=client_name,
            barberId=barber_id,
            barberName=barber_name,
            date=date,
            time=time,
            service=service,
            price=price,
            status="pending",
            notes=notes,
            timestamp=datetime.now()
        )
        
        data = appointment.model_dump(by_alias=True, exclude={"id"})
        result = self.create(appointment_id, data)
        
        if result:
            result["id"] = appointment_id
        return result
    
    def get_appointment(self, appointment_id: str) -> Optional[Dict]:
        """Get appointment by ID."""
        return self.get_by_id(appointment_id)
    
    def update_appointment(self, appointment_id: str, data: Dict) -> Optional[Dict]:
        """Update appointment."""
        data["statusUpdatedAt"] = datetime.now()
        return self.update(appointment_id, data)
    
    def get_client_appointments(self, client_id: str, status: Optional[str] = None,
                                limit: Optional[int] = None) -> List[Dict]:
        """Get appointments for a client."""
        filters = [("clientId", "==", client_id)]
        if status:
            filters.append(("status", "==", status))
        return self.query(filters, limit=limit, order_by="timestamp", direction="desc")
    
    def get_barber_appointments(self, barber_id: str, status: Optional[str] = None,
                               limit: Optional[int] = None) -> List[Dict]:
        """Get appointments for a barber."""
        filters = [("barberId", "==", barber_id)]
        if status:
            filters.append(("status", "==", status))
        return self.query(filters, limit=limit, order_by="timestamp", direction="desc")
    
    def get_appointments_by_date(self, barber_id: str, date: str) -> List[Dict]:
        """Get appointments for a barber on a specific date."""
        return self.query([
            ("barberId", "==", barber_id),
            ("date", "==", date)
        ], order_by="time", direction="asc")
    
    def update_status(self, appointment_id: str, status: str, 
                     reason: Optional[str] = None) -> Optional[Dict]:
        """Update appointment status."""
        update_data = {
            "status": status,
            "statusUpdatedAt": datetime.now()
        }
        
        if status == "rejected" and reason:
            update_data["rejectionReason"] = reason
        elif status == "cancelled" and reason:
            update_data["cancellationReason"] = reason
        
        return self.update(appointment_id, update_data)
    
    def reschedule_appointment(self, appointment_id: str, new_date: str, new_time: str,
                              reason: str = "Rescheduled") -> Optional[Dict]:
        """Reschedule an appointment."""
        appointment = self.get_by_id(appointment_id)
        if not appointment:
            return None
        
        # Store reschedule history
        reschedule_history = appointment.get("rescheduleHistory", [])
        reschedule_history.append({
            "oldDate": appointment.get("date"),
            "oldTime": appointment.get("time"),
            "newDate": new_date,
            "newTime": new_time,
            "reason": reason,
            "rescheduledAt": datetime.now().isoformat()
        })
        
        return self.update(appointment_id, {
            "date": new_date,
            "time": new_time,
            "status": "rescheduled",
            "rescheduleHistory": reschedule_history,
            "statusUpdatedAt": datetime.now()
        })
    
    def add_barber_note(self, appointment_id: str, note: str, note_type: str = "general") -> Optional[Dict]:
        """Add a note to an appointment."""
        appointment = self.get_by_id(appointment_id)
        if not appointment:
            return None
        
        barber_notes = appointment.get("barberNotes", [])
        barber_notes.append({
            "note": note,
            "type": note_type,
            "createdAt": datetime.now().isoformat()
        })
        
        return self.update(appointment_id, {"barberNotes": barber_notes})
