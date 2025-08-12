import os
import re
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import structlog
import httpx  # Using httpx instead of emergentintegrations for now
from server import collections, get_current_time, hash_pii

logger = structlog.get_logger()

class WhatsAppClient:
    """Mock WhatsApp client for demonstration"""
    
    async def send_message(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Mock send message implementation"""
        # In real implementation, this would use WhatsApp Business API
        logger.info("Mock WhatsApp message sent", phone=phone_number[:8] + "XXX")
        return {
            "success": True,
            "message_id": f"msg_{int(datetime.now().timestamp())}",
            "phone_number": phone_number
        }

class WhatsAppNDRService:
    """WhatsApp service for NDR resolution workflow"""
    
    def __init__(self):
        self.whatsapp = WhatsAppClient()
        self.pending_responses = {}  # Store pending customer responses
    
    async def send_ndr_resolution_options(self, order_id: str, customer_phone: str) -> Dict[str, Any]:
        """Send NDR resolution options to customer via WhatsApp"""
        try:
            # Get order details
            order = await collections["orders"].find_one({"order_id": order_id})
            if not order:
                raise ValueError(f"Order {order_id} not found")
            
            # Get delivery address
            address = await collections["addresses"].find_one({"_id": order["delivery_address_id"]})
            address_text = f"{address.get('line1', '')}, {address.get('city', '')}, {address.get('pincode', '')}" if address else "your address"
            
            # Create resolution options message
            message = f"""🚚 **Delivery Update - Order #{order_id}**

Hi! We attempted to deliver your order to {address_text} but you were unavailable.

**Please choose an option:**

1️⃣ **RESCHEDULE** - Choose new delivery time
2️⃣ **CHANGE ADDRESS** - Update delivery location  
3️⃣ **SELF PICKUP** - Collect from nearby hub
4️⃣ **CANCEL ORDER** - Process return

Reply with the number (1, 2, 3, or 4) or type HELP for assistance.

⏰ Please respond within 2 hours to avoid return shipping charges."""

            # Send message using Emergent WhatsApp integration
            result = await self.whatsapp.send_message(
                phone_number=customer_phone,
                message=message
            )
            
            # Store pending response
            self.pending_responses[customer_phone] = {
                "order_id": order_id,
                "sent_at": get_current_time(),
                "status": "PENDING"
            }
            
            # Create message event record
            await collections["message_events"].insert_one({
                "_id": f"whatsapp_{order_id}_{int(datetime.now().timestamp())}",
                "order_id": order["_id"],
                "channel": "WHATSAPP",
                "message_type": "NDR_RESOLUTION_OPTIONS",
                "content": message,
                "status": "SENT" if result.get("success") else "FAILED",
                "external_message_id": result.get("message_id"),
                "created_at": get_current_time(),
                "updated_at": get_current_time()
            })
            
            logger.info("NDR resolution options sent", 
                       order_id=order_id, 
                       phone=customer_phone[:8] + "XXX",
                       success=result.get("success"))
            
            return {
                "success": True,
                "message_sent": True,
                "order_id": order_id,
                "expires_at": (get_current_time() + timedelta(hours=2)).isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to send NDR resolution options", 
                        error=str(e), order_id=order_id)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def process_customer_response(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Process customer response to NDR resolution"""
        try:
            # Check if we have a pending response for this number
            pending = self.pending_responses.get(phone_number)
            if not pending or pending["status"] != "PENDING":
                return await self.handle_general_message(phone_number, message)
            
            order_id = pending["order_id"]
            message_lower = message.strip().lower()
            
            # Parse response
            response_type = None
            if message_lower in ['1', 'reschedule', 'reschedule delivery']:
                response_type = "RESCHEDULE"
            elif message_lower in ['2', 'change address', 'change location']:
                response_type = "CHANGE_ADDRESS"
            elif message_lower in ['3', 'self pickup', 'pickup', 'collect']:
                response_type = "SELF_PICKUP"
            elif message_lower in ['4', 'cancel', 'cancel order', 'return']:
                response_type = "RTO"
            elif message_lower in ['help', '?']:
                return await self.send_help_message(phone_number, order_id)
            
            if not response_type:
                return await self.send_clarification_message(phone_number)
            
            # Process the response
            result = await self.handle_ndr_resolution(order_id, response_type, phone_number, message)
            
            # Update pending response status
            self.pending_responses[phone_number]["status"] = "COMPLETED"
            
            return result
            
        except Exception as e:
            logger.error("Failed to process customer response", 
                        error=str(e), phone=phone_number[:8] + "XXX")
            await self.send_error_message(phone_number)
            return {"success": False, "error": str(e)}
    
    async def handle_ndr_resolution(self, order_id: str, action: str, phone_number: str, original_message: str) -> Dict[str, Any]:
        """Handle specific NDR resolution action"""
        try:
            if action == "RESCHEDULE":
                return await self.handle_reschedule(order_id, phone_number)
            elif action == "CHANGE_ADDRESS":
                return await self.handle_address_change(order_id, phone_number)
            elif action == "SELF_PICKUP":
                return await self.handle_self_pickup(order_id, phone_number)
            elif action == "RTO":
                return await self.handle_rto_request(order_id, phone_number)
            
        except Exception as e:
            logger.error("Failed to handle NDR resolution", 
                        error=str(e), order_id=order_id, action=action)
            return {"success": False, "error": str(e)}
    
    async def handle_reschedule(self, order_id: str, phone_number: str) -> Dict[str, Any]:
        """Handle delivery reschedule request"""
        try:
            # Send time slot options
            message = f"""⏰ **Reschedule Delivery - Order #{order_id}**

Please choose a convenient time slot:

🌅 **Morning Slots:**
A. 9:00 AM - 12:00 PM
B. 10:00 AM - 1:00 PM

🌞 **Afternoon Slots:**
C. 2:00 PM - 5:00 PM  
D. 3:00 PM - 6:00 PM

🌆 **Evening Slots:**
E. 6:00 PM - 8:00 PM

Reply with the letter (A, B, C, D, or E) for your preferred slot.

📅 Available dates: Today, Tomorrow, Day after tomorrow"""

            await self.whatsapp.send_message(phone_number, message)
            
            # Update order status
            await collections["orders"].update_one(
                {"order_id": order_id},
                {"$set": {
                    "status": "RESCHEDULE_REQUESTED",
                    "updated_at": get_current_time()
                }}
            )
            
            return {"success": True, "action": "reschedule_options_sent"}
            
        except Exception as e:
            logger.error("Failed to handle reschedule", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def handle_address_change(self, order_id: str, phone_number: str) -> Dict[str, Any]:
        """Handle delivery address change request"""
        try:
            message = f"""📍 **Change Delivery Address - Order #{order_id}**

Please provide your new delivery address in this format:

**House/Flat number, Street name**
**Area, City, Pincode**

Example:
123, MG Road
Indiranagar, Bengaluru, 560038

⚠️ Note: Address change may incur additional delivery charges if the new location is outside our delivery zone."""

            await self.whatsapp.send_message(phone_number, message)
            
            # Update order status
            await collections["orders"].update_one(
                {"order_id": order_id},
                {"$set": {
                    "status": "ADDRESS_CHANGE_REQUESTED",
                    "updated_at": get_current_time()
                }}
            )
            
            return {"success": True, "action": "address_change_requested"}
            
        except Exception as e:
            logger.error("Failed to handle address change", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def handle_self_pickup(self, order_id: str, phone_number: str) -> Dict[str, Any]:
        """Handle self pickup request"""
        try:
            # Find nearest pickup location (mock data for now)
            message = f"""📦 **Self Pickup - Order #{order_id}**

Your nearest pickup locations:

🏪 **Pickup Hub 1**
Address: MG Road Metro Station, Bengaluru
Timings: 10:00 AM - 8:00 PM (Mon-Sat)
Distance: 2.5 km

🏪 **Pickup Hub 2**  
Address: Indiranagar 100ft Road, Bengaluru
Timings: 9:00 AM - 9:00 PM (Daily)
Distance: 3.2 km

Your order will be ready for pickup within 4 hours. You'll receive a pickup code via SMS.

Reply **CONFIRM HUB 1** or **CONFIRM HUB 2** to proceed."""

            await self.whatsapp.send_message(phone_number, message)
            
            # Update order status
            await collections["orders"].update_one(
                {"order_id": order_id},
                {"$set": {
                    "status": "SELF_PICKUP_REQUESTED", 
                    "updated_at": get_current_time()
                }}
            )
            
            return {"success": True, "action": "pickup_options_sent"}
            
        except Exception as e:
            logger.error("Failed to handle self pickup", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def handle_rto_request(self, order_id: str, phone_number: str) -> Dict[str, Any]:
        """Handle RTO/cancellation request"""
        try:
            # Get order details for refund calculation
            order = await collections["orders"].find_one({"order_id": order_id})
            order_value = order.get("order_value", 0)
            payment_mode = order.get("payment_mode", "COD")
            
            if payment_mode == "PREPAID":
                refund_amount = order_value - 50  # Deduct processing fee
                refund_text = f"Refund of ₹{refund_amount} will be processed within 5-7 business days."
            else:
                refund_text = "No payment collected. Order will be cancelled without charges."
            
            message = f"""❌ **Order Cancellation - #{order_id}**

We understand you'd like to cancel this order.

**Cancellation Details:**
• Order Value: ₹{order_value}
• Payment Mode: {payment_mode}
• {refund_text}

**Are you sure you want to cancel?**

Reply **YES CANCEL** to confirm cancellation
Reply **NO KEEP** to keep the order and explore other options

⚠️ Once cancelled, this action cannot be undone."""

            await self.whatsapp.send_message(phone_number, message)
            
            return {"success": True, "action": "cancellation_confirmation_sent"}
            
        except Exception as e:
            logger.error("Failed to handle RTO request", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def send_help_message(self, phone_number: str, order_id: str) -> Dict[str, Any]:
        """Send help message with options"""
        message = f"""❓ **Help - Order #{order_id}**

**Available Options:**

1️⃣ **RESCHEDULE** - Choose new delivery time
2️⃣ **CHANGE ADDRESS** - Update delivery location
3️⃣ **SELF PICKUP** - Collect from nearby hub  
4️⃣ **CANCEL ORDER** - Process return

**Simply reply with:**
- Number (1, 2, 3, or 4)
- Or type the option name (e.g., "reschedule")

Need more help? Call our support: 1800-123-4567"""

        await self.whatsapp.send_message(phone_number, message)
        return {"success": True, "action": "help_sent"}
    
    async def send_clarification_message(self, phone_number: str) -> Dict[str, Any]:
        """Send message asking for clarification"""
        message = """🤔 I didn't understand your response.

Please reply with:
1️⃣ for Reschedule
2️⃣ for Change Address  
3️⃣ for Self Pickup
4️⃣ for Cancel Order

Or type HELP for more options."""

        await self.whatsapp.send_message(phone_number, message)
        return {"success": True, "action": "clarification_sent"}
    
    async def send_error_message(self, phone_number: str) -> Dict[str, Any]:
        """Send error message"""
        message = """⚠️ We're experiencing technical difficulties.

Please try again in a few minutes or call our support team at 1800-123-4567.

We apologize for the inconvenience."""

        await self.whatsapp.send_message(phone_number, message)
        return {"success": True, "action": "error_message_sent"}
    
    async def handle_general_message(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Handle general messages not related to NDR resolution"""
        response = """👋 Hello! 

I'm your delivery assistant. I help with order delivery issues and rescheduling.

If you have a delivery-related question, please share your order number and I'll assist you.

For other inquiries, please contact our support team at 1800-123-4567."""

        await self.whatsapp.send_message(phone_number, response)
        return {"success": True, "action": "general_response_sent"}

# Global WhatsApp service instance
whatsapp_service = WhatsAppNDRService()