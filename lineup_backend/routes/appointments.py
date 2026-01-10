"""Appointment management endpoints."""

import logging
import uuid
from datetime import datetime

from flask import Blueprint, request

from lineup_backend.utils import cors_response, handle_options, api_response, safe_get_json
from lineup_backend import storage as memory_store

logger = logging.getLogger(__name__)

appointments_bp = Blueprint('appointments', __name__)


@appointments_bp.route('/appointments', methods=['GET', 'POST', 'OPTIONS'])
@handle_options("GET, POST, OPTIONS")
def handle_appointments():
    """Get all appointments or create a new one."""
    
    if request.method == 'GET':
        user_type = request.args.get('type', 'client')
        user_id = request.args.get('user_id', 'current_user')
        
        if user_type == 'client':
            user_appointments = [apt for apt in memory_store.appointments if apt.get('clientId') == user_id]
        else:  # barber
            user_appointments = [apt for apt in memory_store.appointments if apt.get('barberId') == user_id]
        
        return cors_response({"appointments": user_appointments})
    
    elif request.method == 'POST':
        try:
            data = safe_get_json()
            
            new_appointment = {
                "id": str(uuid.uuid4()),
                "clientName": data.get("clientName", "Anonymous Client"),
                "clientId": data.get("clientId", "current_user"),
                "barberName": data.get("barberName", "Unknown Barber"),
                "barberId": data.get("barberId", "unknown_barber"),
                "date": data.get("date", ""),
                "time": data.get("time", ""),
                "service": data.get("service", ""),
                "price": data.get("price", "$0"),
                "status": "pending",
                "notes": data.get("notes", "No special requests"),
                "timestamp": datetime.now().isoformat()
            }
            
            memory_store.appointments.append(new_appointment)
            logger.info(f"Appointment created: {new_appointment['id']}")
            
            return api_response(data={"appointment": new_appointment}, message="Appointment created", status=201)
            
        except Exception as e:
            logger.error(f"Error creating appointment: {str(e)}")
            return api_response(error="Failed to create appointment", status=400)


@appointments_bp.route('/appointments/<appointment_id>/status', methods=['PUT', 'OPTIONS'])
@handle_options("PUT, OPTIONS")
def update_appointment_status(appointment_id):
    """Update appointment status."""
    try:
        data = safe_get_json()
        new_status = data.get("status", "pending")
        
        appointment = next((apt for apt in memory_store.appointments if apt.get("id") == appointment_id), None)
        
        if not appointment:
            return api_response(error="Appointment not found", status=404)
        
        appointment["status"] = new_status
        appointment["statusUpdatedAt"] = datetime.now().isoformat()
        
        return cors_response({"success": True, "appointment": appointment})
        
    except Exception as e:
        logger.error(f"Error updating appointment: {str(e)}")
        return api_response(error="Failed to update appointment", status=400)


@appointments_bp.route('/appointments/<appointment_id>/accept', methods=['POST', 'OPTIONS'])
@handle_options("POST, OPTIONS")
def accept_appointment(appointment_id):
    """Accept (confirm) an appointment."""
    try:
        appointment = next((apt for apt in memory_store.appointments if apt.get("id") == appointment_id), None)
        
        if not appointment:
            return api_response(error="Appointment not found", status=404)
        
        appointment["status"] = "confirmed"
        appointment["statusUpdatedAt"] = datetime.now().isoformat()
        
        return cors_response({"success": True, "appointment": appointment})
        
    except Exception as e:
        logger.error(f"Error accepting appointment: {str(e)}")
        return api_response(error="Failed to accept appointment", status=400)


@appointments_bp.route('/appointments/<appointment_id>/reject', methods=['POST', 'OPTIONS'])
@handle_options("POST, OPTIONS")
def reject_appointment(appointment_id):
    """Reject an appointment."""
    try:
        data = safe_get_json()
        reason = data.get("reason", "No reason provided")
        
        appointment = next((apt for apt in memory_store.appointments if apt.get("id") == appointment_id), None)
        
        if not appointment:
            return api_response(error="Appointment not found", status=404)
        
        appointment["status"] = "rejected"
        appointment["rejectionReason"] = reason
        appointment["statusUpdatedAt"] = datetime.now().isoformat()
        
        return cors_response({"success": True, "appointment": appointment})
        
    except Exception as e:
        logger.error(f"Error rejecting appointment: {str(e)}")
        return api_response(error="Failed to reject appointment", status=400)


@appointments_bp.route('/appointments/<appointment_id>/reschedule', methods=['POST', 'OPTIONS'])
@handle_options("POST, OPTIONS")
def reschedule_appointment(appointment_id):
    """Reschedule an appointment."""
    try:
        data = safe_get_json()
        new_date = data.get("date")
        new_time = data.get("time")
        reason = data.get("reason", "Rescheduled")
        
        if not new_date or not new_time:
            return api_response(error="Date and time required", status=400)
        
        appointment = next((apt for apt in memory_store.appointments if apt.get("id") == appointment_id), None)
        
        if not appointment:
            return api_response(error="Appointment not found", status=404)
        
        # Store reschedule history
        if "rescheduleHistory" not in appointment:
            appointment["rescheduleHistory"] = []
        
        appointment["rescheduleHistory"].append({
            "oldDate": appointment.get("date"),
            "oldTime": appointment.get("time"),
            "newDate": new_date,
            "newTime": new_time,
            "reason": reason,
            "rescheduledAt": datetime.now().isoformat()
        })
        
        appointment["date"] = new_date
        appointment["time"] = new_time
        appointment["status"] = "rescheduled"
        appointment["statusUpdatedAt"] = datetime.now().isoformat()
        
        return cors_response({"success": True, "appointment": appointment})
        
    except Exception as e:
        logger.error(f"Error rescheduling appointment: {str(e)}")
        return api_response(error="Failed to reschedule appointment", status=400)


@appointments_bp.route('/appointments/<appointment_id>/cancel', methods=['POST', 'OPTIONS'])
@handle_options("POST, OPTIONS")
def cancel_appointment(appointment_id):
    """Cancel an appointment."""
    try:
        data = safe_get_json()
        reason = data.get("reason", "Cancelled")
        
        appointment = next((apt for apt in memory_store.appointments if apt.get("id") == appointment_id), None)
        
        if not appointment:
            return api_response(error="Appointment not found", status=404)
        
        appointment["status"] = "cancelled"
        appointment["cancellationReason"] = reason
        appointment["statusUpdatedAt"] = datetime.now().isoformat()
        
        return cors_response({"success": True, "appointment": appointment})
        
    except Exception as e:
        logger.error(f"Error cancelling appointment: {str(e)}")
        return api_response(error="Failed to cancel appointment", status=400)


@appointments_bp.route('/appointments/<appointment_id>/notes', methods=['POST', 'PUT', 'OPTIONS'])
@handle_options("POST, PUT, OPTIONS")
def add_appointment_notes(appointment_id):
    """Add notes to an appointment."""
    try:
        data = safe_get_json()
        note = data.get("note", "")
        note_type = data.get("type", "general")
        
        appointment = next((apt for apt in memory_store.appointments if apt.get("id") == appointment_id), None)
        
        if not appointment:
            return api_response(error="Appointment not found", status=404)
        
        if "barberNotes" not in appointment:
            appointment["barberNotes"] = []
        
        appointment["barberNotes"].append({
            "note": note,
            "type": note_type,
            "createdAt": datetime.now().isoformat()
        })
        
        return cors_response({"success": True, "appointment": appointment})
        
    except Exception as e:
        logger.error(f"Error adding notes: {str(e)}")
        return api_response(error="Failed to add notes", status=400)

