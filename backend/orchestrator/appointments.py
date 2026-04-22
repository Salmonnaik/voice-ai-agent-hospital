"""
appointments.py

Appointment management service for the Voice AI Platform.
Handles appointment CRUD operations, status management, and notifications.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Appointment(BaseModel):
    id: str
    name: str
    mobile: str
    status: str  # 'pending', 'accepted', 'rejected', 'completed'
    createdAt: str
    scheduledTime: Optional[str] = None
    notes: Optional[str] = None
    department: Optional[str] = None

class AppointmentManager:
    def __init__(self):
        # In-memory storage (in production, use database)
        self.appointments: Dict[str, Appointment] = {}
        self.lock = asyncio.Lock()
    
    async def create_appointment(self, appointment_data: Dict) -> Appointment:
        """Create a new appointment"""
        async with self.lock:
            appointment = Appointment(
                id=appointment_data.get('id', str(datetime.now().timestamp())),
                name=appointment_data['name'],
                mobile=appointment_data['mobile'],
                status='pending',
                createdAt=appointment_data.get('createdAt', datetime.now().isoformat()),
                scheduledTime=appointment_data.get('scheduledTime'),
                notes=appointment_data.get('notes'),
                department=appointment_data.get('department')
            )
            
            self.appointments[appointment.id] = appointment
            logger.info(f"Created appointment: {appointment.id} for {appointment.name}")
            
            # Trigger notification/processing
            await self._process_new_appointment(appointment)
            
            return appointment
    
    async def get_appointment(self, appointment_id: str) -> Optional[Appointment]:
        """Get appointment by ID"""
        async with self.lock:
            return self.appointments.get(appointment_id)
    
    async def get_all_appointments(self) -> List[Appointment]:
        """Get all appointments"""
        async with self.lock:
            return list(self.appointments.values())
    
    async def get_appointments_by_status(self, status: str) -> List[Appointment]:
        """Get appointments filtered by status"""
        async with self.lock:
            return [apt for apt in self.appointments.values() if apt.status == status]
    
    async def update_appointment_status(self, appointment_id: str, status: str, 
                                      scheduled_time: Optional[str] = None) -> Optional[Appointment]:
        """Update appointment status"""
        async with self.lock:
            if appointment_id in self.appointments:
                appointment = self.appointments[appointment_id]
                appointment.status = status
                if scheduled_time:
                    appointment.scheduledTime = scheduled_time
                
                logger.info(f"Updated appointment {appointment_id} status to {status}")
                
                # Trigger status update notifications
                await self._process_status_update(appointment)
                
                return appointment
            return None
    
    async def get_user_appointments(self, mobile: str) -> List[Appointment]:
        """Get all appointments for a specific user (by mobile)"""
        async with self.lock:
            return [apt for apt in self.appointments.values() if apt.mobile == mobile]
    
    async def _process_new_appointment(self, appointment: Appointment):
        """Process new appointment - send notifications, etc."""
        # In a real system, this would:
        # - Send SMS confirmation
        # - Notify hospital staff
        # - Check for conflicts
        # - Schedule in hospital system
        
        logger.info(f"Processing new appointment: {appointment.id}")
        
        # Simulate processing delay
        await asyncio.sleep(0.1)
        
        # Could trigger webhook or notification service here
        notification_data = {
            "type": "new_appointment",
            "appointment": appointment.dict(),
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to notification queue (in real implementation)
        logger.info(f"Would send notification: {notification_data}")
    
    async def _process_status_update(self, appointment: Appointment):
        """Process appointment status update"""
        # In a real system, this would:
        # - Send SMS update
        # - Update calendar
        # - Notify relevant parties
        
        logger.info(f"Processing status update for appointment: {appointment.id}")
        
        notification_data = {
            "type": "status_update",
            "appointment": appointment.dict(),
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to notification queue (in real implementation)
        logger.info(f"Would send status notification: {notification_data}")

# Global instance
appointment_manager = AppointmentManager()

# API handlers
async def handle_appointment_request(data: Dict) -> Dict:
    """Handle appointment creation request"""
    try:
        appointment = await appointment_manager.create_appointment(data)
        return {
            "success": True,
            "appointment": appointment.dict(),
            "message": "Appointment created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating appointment: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to create appointment"
        }

async def handle_appointment_list_request(data: Dict) -> Dict:
    """Handle appointment list request"""
    try:
        mobile = data.get('mobile')
        status = data.get('status')
        
        if mobile:
            appointments = await appointment_manager.get_user_appointments(mobile)
        elif status:
            appointments = await appointment_manager.get_appointments_by_status(status)
        else:
            appointments = await appointment_manager.get_all_appointments()
        
        return {
            "success": True,
            "appointments": [apt.dict() for apt in appointments],
            "count": len(appointments)
        }
    except Exception as e:
        logger.error(f"Error listing appointments: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to list appointments"
        }

async def handle_appointment_update_request(data: Dict) -> Dict:
    """Handle appointment status update request"""
    try:
        appointment_id = data.get('appointment_id')
        status = data.get('status')
        scheduled_time = data.get('scheduled_time')
        
        if not appointment_id or not status:
            return {
                "success": False,
                "error": "appointment_id and status are required",
                "message": "Missing required fields"
            }
        
        appointment = await appointment_manager.update_appointment_status(
            appointment_id, status, scheduled_time
        )
        
        if appointment:
            return {
                "success": True,
                "appointment": appointment.dict(),
                "message": f"Appointment status updated to {status}"
            }
        else:
            return {
                "success": False,
                "error": "Appointment not found",
                "message": "Appointment not found"
            }
    except Exception as e:
        logger.error(f"Error updating appointment: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to update appointment"
        }
