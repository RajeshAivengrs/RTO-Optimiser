from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import structlog
from whatsapp_service import whatsapp_service
from server import collections, get_current_time

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])
logger = structlog.get_logger()

# Pydantic Models
class WhatsAppWebhook(BaseModel):
    phone_number: str
    message: str
    message_id: str
    timestamp: str
    sender_name: Optional[str] = None

class NDRTriggerRequest(BaseModel):
    order_id: str
    customer_phone: str
    ndr_reason: str
    trigger_whatsapp: bool = True

class WhatsAppResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

# WhatsApp Webhook Endpoints

@router.post("/webhook", response_model=WhatsAppResponse)
async def whatsapp_webhook(
    webhook_data: WhatsAppWebhook,
    background_tasks: BackgroundTasks
):
    """Handle incoming WhatsApp messages"""
    try:
        logger.info("Received WhatsApp message", 
                   phone=webhook_data.phone_number[:8] + "XXX",
                   message_id=webhook_data.message_id)
        
        # Process message in background to avoid blocking
        background_tasks.add_task(
            process_whatsapp_message,
            webhook_data.phone_number,
            webhook_data.message
        )
        
        return WhatsAppResponse(
            success=True,
            message="Message received and being processed"
        )
        
    except Exception as e:
        logger.error("WhatsApp webhook error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process webhook")

async def process_whatsapp_message(phone_number: str, message: str):
    """Background task to process WhatsApp messages"""
    try:
        # Import here to avoid circular import
        from whatsapp_service import WhatsAppNDRService
        whatsapp_service = WhatsAppNDRService()
        
        result = await whatsapp_service.process_customer_response(phone_number, message)
        
        logger.info("WhatsApp message processed", 
                   phone=phone_number[:8] + "XXX",
                   success=result.get("success"),
                   action=result.get("action"))
        
    except Exception as e:
        logger.error("Failed to process WhatsApp message", 
                    error=str(e), phone=phone_number[:8] + "XXX")

@router.post("/trigger-ndr", response_model=WhatsAppResponse)
async def trigger_ndr_resolution(request: NDRTriggerRequest):
    """Trigger NDR resolution workflow for an order"""
    try:
        if not request.trigger_whatsapp:
            return WhatsAppResponse(
                success=True,
                message="WhatsApp notification disabled for this order"
            )
        
        # Import here to avoid circular import
        from whatsapp_service import WhatsAppNDRService
        whatsapp_service = WhatsAppNDRService()
        
        # Send NDR resolution options to customer
        result = await whatsapp_service.send_ndr_resolution_options(
            order_id=request.order_id,
            customer_phone=request.customer_phone
        )
        
        if result["success"]:
            return WhatsAppResponse(
                success=True,
                message="NDR resolution options sent to customer",
                data={
                    "order_id": request.order_id,
                    "phone_number": request.customer_phone[:8] + "XXX",
                    "expires_at": result.get("expires_at")
                }
            )
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
        
    except Exception as e:
        logger.error("Failed to trigger NDR resolution", 
                    error=str(e), order_id=request.order_id)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send-message")
async def send_whatsapp_message(
    phone_number: str,
    message: str
):
    """Send a custom WhatsApp message"""
    try:
        # Import here to avoid circular import
        from whatsapp_service import WhatsAppNDRService
        whatsapp_service = WhatsAppNDRService()
        
        result = await whatsapp_service.whatsapp.send_message(
            phone_number=phone_number,
            message=message
        )
        
        return WhatsAppResponse(
            success=result.get("success", False),
            message="Message sent successfully" if result.get("success") else "Failed to send message",
            data=result
        )
        
    except Exception as e:
        logger.error("Failed to send WhatsApp message", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_whatsapp_status():
    """Get WhatsApp service status"""
    try:
        # Check if WhatsApp service can be initialized
        from whatsapp_service import WhatsAppNDRService
        whatsapp_service = WhatsAppNDRService()
        status = "connected" if whatsapp_service.whatsapp else "disconnected"
        
        return {
            "status": status,
            "service": "WhatsApp NDR Resolution",
            "version": "1.0.0",
            "last_checked": get_current_time().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to check WhatsApp status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pending-responses")
async def get_pending_responses():
    """Get list of pending customer responses"""
    try:
        pending = whatsapp_service.pending_responses
        
        # Filter out expired responses (older than 2 hours)
        from datetime import timedelta
        cutoff_time = get_current_time() - timedelta(hours=2)
        
        active_pending = {}
        for phone, data in pending.items():
            if data.get("sent_at", cutoff_time) > cutoff_time and data.get("status") == "PENDING":
                active_pending[phone[:8] + "XXX"] = {
                    "order_id": data["order_id"],
                    "sent_at": data["sent_at"].isoformat(),
                    "expires_at": (data["sent_at"] + timedelta(hours=2)).isoformat()
                }
        
        return {
            "pending_count": len(active_pending),
            "pending_responses": active_pending,
            "last_updated": get_current_time().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get pending responses", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Analytics endpoint for WhatsApp performance
@router.get("/analytics")
async def get_whatsapp_analytics():
    """Get WhatsApp NDR resolution analytics"""
    try:
        from datetime import timedelta
        
        # Get message events from last 7 days
        week_ago = get_current_time() - timedelta(days=7)
        
        total_messages = await collections["message_events"].count_documents({
            "channel": "WHATSAPP",
            "created_at": {"$gte": week_ago}
        })
        
        successful_messages = await collections["message_events"].count_documents({
            "channel": "WHATSAPP",
            "status": "SENT",
            "created_at": {"$gte": week_ago}
        })
        
        ndr_resolutions = await collections["message_events"].count_documents({
            "channel": "WHATSAPP", 
            "message_type": "NDR_RESOLUTION_OPTIONS",
            "created_at": {"$gte": week_ago}
        })
        
        # Calculate resolution rate
        resolution_rate = 0
        if ndr_resolutions > 0:
            # Count orders that were resolved after WhatsApp interaction
            resolved_orders = await collections["orders"].count_documents({
                "status": {"$in": ["RESCHEDULE_REQUESTED", "ADDRESS_CHANGE_REQUESTED", "SELF_PICKUP_REQUESTED"]},
                "updated_at": {"$gte": week_ago}
            })
            resolution_rate = (resolved_orders / ndr_resolutions * 100) if ndr_resolutions > 0 else 0
        
        return {
            "period": "last_7_days",
            "total_messages_sent": total_messages,
            "successful_deliveries": successful_messages,
            "delivery_rate": (successful_messages / total_messages * 100) if total_messages > 0 else 0,
            "ndr_notifications_sent": ndr_resolutions,
            "customer_response_rate": resolution_rate,
            "cost_savings_estimate": resolved_orders * 200 if 'resolved_orders' in locals() else 0,  # ₹200 per prevented RTO
            "last_updated": get_current_time().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get WhatsApp analytics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))