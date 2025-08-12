from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
import structlog

# Import the database collections from server.py
from server import collections, get_current_time

router = APIRouter(prefix="/api/seller", tags=["seller"])
logger = structlog.get_logger()

# Seller Models
class SellerOrderAnalytics(BaseModel):
    order_id: str
    status: str
    delivery_attempts: List[Dict[str, Any]]
    ndr_details: Optional[Dict[str, Any]] = None
    proof_validation: Optional[Dict[str, Any]] = None
    carrier_performance: Dict[str, Any]
    cost_impact: Dict[str, Any]

class SellerKPIResponse(BaseModel):
    brand_id: str
    period: str
    total_orders: int
    successful_deliveries: int
    success_rate: float
    verified_ndrs: int
    suspicious_ndrs: int
    rto_prevented: int
    cost_saved: float
    carrier_breakdown: List[Dict[str, Any]]

class NDRChallenge(BaseModel):
    order_id: str
    challenge_reason: str
    evidence_required: List[str]
    seller_comments: Optional[str] = None

# Seller Dashboard Endpoints

@router.get("/dashboard/{brand_id}", response_model=SellerKPIResponse)
async def get_seller_dashboard(
    brand_id: str,
    period: str = Query("week", enum=["day", "week", "month"])
):
    """Get seller-specific dashboard with accountability metrics"""
    try:
        # Calculate date range based on period
        now = datetime.now()
        if period == "day":
            start_date = now - timedelta(days=1)
        elif period == "week":
            start_date = now - timedelta(days=7)
        else:  # month
            start_date = now - timedelta(days=30)
        
        # Get orders for the brand in the period
        orders = await collections["orders"].find({
            "brand_id": brand_id,
            "created_at": {"$gte": start_date}
        }).to_list(length=None)
        
        total_orders = len(orders)
        successful_deliveries = 0
        verified_ndrs = 0
        suspicious_ndrs = 0
        rto_prevented = 0
        
        carrier_stats = {}
        
        for order in orders:
            # Get shipments for each order
            shipments = await collections["shipments"].find({
                "order_id": order["_id"]
            }).to_list(length=None)
            
            for shipment in shipments:
                carrier = shipment.get("carrier", "Unknown")
                if carrier not in carrier_stats:
                    carrier_stats[carrier] = {
                        "total": 0,
                        "delivered": 0,
                        "verified_ndrs": 0,
                        "suspicious_ndrs": 0,
                        "rto_prevented": 0
                    }
                
                carrier_stats[carrier]["total"] += 1
                
                # Check shipment status
                if shipment.get("current_status") == "DELIVERED":
                    successful_deliveries += 1
                    carrier_stats[carrier]["delivered"] += 1
                
                # Get NDR events for this shipment
                ndr_events = await collections["courier_events"].find({
                    "shipment_id": shipment["_id"],
                    "event_code": "NDR"
                }).to_list(length=None)
                
                for ndr_event in ndr_events:
                    if ndr_event.get("proof_validated"):
                        verified_ndrs += 1
                        carrier_stats[carrier]["verified_ndrs"] += 1
                    elif ndr_event.get("proof_required"):
                        suspicious_ndrs += 1
                        carrier_stats[carrier]["suspicious_ndrs"] += 1
                    
                    # Check if RTO was prevented
                    if ndr_event.get("overturned_flag"):
                        rto_prevented += 1
                        carrier_stats[carrier]["rto_prevented"] += 1
        
        # Calculate cost savings (assuming ₹200 per prevented RTO)
        cost_saved = rto_prevented * 200.0
        
        # Format carrier breakdown
        carrier_breakdown = []
        for carrier, stats in carrier_stats.items():
            success_rate = (stats["delivered"] / stats["total"] * 100) if stats["total"] > 0 else 0
            carrier_breakdown.append({
                "carrier": carrier,
                "total_orders": stats["total"],
                "success_rate": round(success_rate, 2),
                "verified_ndrs": stats["verified_ndrs"],
                "suspicious_ndrs": stats["suspicious_ndrs"],
                "rto_prevented": stats["rto_prevented"]
            })
        
        success_rate = (successful_deliveries / total_orders * 100) if total_orders > 0 else 0
        
        return SellerKPIResponse(
            brand_id=brand_id,
            period=period,
            total_orders=total_orders,
            successful_deliveries=successful_deliveries,
            success_rate=round(success_rate, 2),
            verified_ndrs=verified_ndrs,
            suspicious_ndrs=suspicious_ndrs,
            rto_prevented=rto_prevented,
            cost_saved=cost_saved,
            carrier_breakdown=carrier_breakdown
        )
        
    except Exception as e:
        logger.error("Failed to get seller dashboard", error=str(e), brand_id=brand_id)
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard data")

@router.get("/orders/{brand_id}/{order_id}")
async def get_order_transparency(
    brand_id: str,
    order_id: str,
    db = Depends(get_database)
):
    """Get detailed transparency view for a specific order"""
    try:
        # Get order details
        order = await collections["orders"].find_one({
            "order_id": order_id,
            "brand_id": brand_id
        })
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Get delivery address
        address = await collections["addresses"].find_one({
            "_id": order["delivery_address_id"]
        })
        
        # Get shipments
        shipments = await collections["shipments"].find({
            "order_id": order["_id"]
        }).to_list(length=None)
        
        delivery_attempts = []
        ndr_details = None
        proof_validation = None
        
        for shipment in shipments:
            # Get courier events for this shipment
            events = await collections["courier_events"].find({
                "shipment_id": shipment["_id"]
            }).sort("timestamp", 1).to_list(length=None)
            
            for event in events:
                attempt = {
                    "event_id": str(event["_id"]),
                    "timestamp": event["timestamp"].isoformat(),
                    "event_code": event["event_code"],
                    "location": event.get("location"),
                    "description": event.get("event_description")
                }
                
                # Add NDR specific details
                if event["event_code"] == "NDR":
                    ndr_details = {
                        "ndr_code": event.get("ndr_code"),
                        "ndr_reason": event.get("ndr_reason"),
                        "proof_required": event.get("proof_required", False),
                        "proof_validated": event.get("proof_validated", False)
                    }
                    
                    # Add proof validation details
                    if event.get("proof_required"):
                        proof_validation = {
                            "gps_coordinates": {
                                "provided": [event.get("gps_latitude"), event.get("gps_longitude")],
                                "required": [address.get("latitude"), address.get("longitude")] if address else None
                            },
                            "call_log": {
                                "duration_sec": event.get("call_duration_sec"),
                                "outcome": event.get("call_outcome"),
                                "valid": event.get("call_duration_sec", 0) >= 10
                            },
                            "violations": []
                        }
                        
                        # Calculate GPS distance if coordinates are available
                        if (event.get("gps_latitude") and event.get("gps_longitude") and 
                            address and address.get("latitude") and address.get("longitude")):
                            from geopy.distance import geodesic
                            distance = geodesic(
                                (event["gps_latitude"], event["gps_longitude"]),
                                (address["latitude"], address["longitude"])
                            ).meters
                            
                            proof_validation["gps_distance_meters"] = round(distance, 2)
                            proof_validation["gps_valid"] = distance <= 200
                            
                            if distance > 200:
                                proof_validation["violations"].append(f"GPS location {distance:.0f}m from delivery address (max: 200m)")
                        
                        if event.get("call_duration_sec", 0) < 10:
                            proof_validation["violations"].append(f"Call duration {event.get('call_duration_sec', 0)}s (min: 10s)")
                
                delivery_attempts.append(attempt)
        
        # Get carrier performance for this order's carrier
        carrier_performance = {"carrier": "Unknown", "recent_performance": {}}
        if shipments:
            carrier = shipments[0].get("carrier")
            if carrier:
                # Calculate recent performance for this carrier
                recent_shipments = await collections["shipments"].find({
                    "carrier": carrier
                }).limit(100).to_list(length=None)
                
                total_recent = len(recent_shipments)
                delivered = sum(1 for s in recent_shipments if s.get("current_status") == "DELIVERED")
                
                carrier_performance = {
                    "carrier": carrier,
                    "recent_performance": {
                        "total_shipments": total_recent,
                        "delivery_rate": round((delivered / total_recent * 100), 2) if total_recent > 0 else 0,
                        "avg_delivery_time": "2.3 days"  # Mock data - could calculate from actual data
                    }
                }
        
        # Calculate cost impact
        cost_impact = {
            "order_value": order.get("order_value", 0),
            "delivery_cost": 50.0,  # Mock delivery cost
            "potential_rto_cost": 200.0 if ndr_details else 0,
            "total_risk": order.get("order_value", 0) + 200.0 if ndr_details else 50.0
        }
        
        return {
            "order_id": order_id,
            "status": order.get("status"),
            "customer_phone_hash": order.get("customer_phone_hash"),
            "delivery_address": address,
            "delivery_attempts": delivery_attempts,
            "ndr_details": ndr_details,
            "proof_validation": proof_validation,
            "carrier_performance": carrier_performance,
            "cost_impact": cost_impact,
            "last_updated": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get order transparency", error=str(e), order_id=order_id)
        raise HTTPException(status_code=500, detail="Failed to fetch order details")

@router.post("/challenge-ndr")
async def challenge_ndr(
    challenge: NDRChallenge,
    db = Depends(get_database)
):
    """Allow sellers to challenge suspicious NDRs"""
    try:
        # Get the order
        order = await collections["orders"].find_one({"order_id": challenge.order_id})
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Find the latest NDR event for this order
        shipments = await collections["shipments"].find({"order_id": order["_id"]}).to_list(length=None)
        
        ndr_event = None
        for shipment in shipments:
            events = await collections["courier_events"].find({
                "shipment_id": shipment["_id"],
                "event_code": "NDR"
            }).sort("timestamp", -1).limit(1).to_list(length=None)
            
            if events:
                ndr_event = events[0]
                break
        
        if not ndr_event:
            raise HTTPException(status_code=404, detail="No NDR event found for this order")
        
        # Create challenge record
        challenge_record = {
            "_id": str(uuid.uuid4()),
            "order_id": challenge.order_id,
            "ndr_event_id": str(ndr_event["_id"]),
            "challenge_reason": challenge.challenge_reason,
            "evidence_required": challenge.evidence_required,
            "seller_comments": challenge.seller_comments,
            "status": "UNDER_REVIEW",
            "created_at": datetime.now(),
            "resolved_at": None,
            "resolution": None
        }
        
        await collections["ndr_challenges"].insert_one(challenge_record)
        
        # Mark the NDR as challenged
        await collections["courier_events"].update_one(
            {"_id": ndr_event["_id"]},
            {"$set": {"challenged": True, "challenge_id": challenge_record["_id"]}}
        )
        
        # Update order status
        await collections["orders"].update_one(
            {"_id": order["_id"]},
            {"$set": {"status": "NDR_CHALLENGED", "updated_at": datetime.now()}}
        )
        
        logger.info("NDR challenge created", order_id=challenge.order_id, challenge_id=challenge_record["_id"])
        
        return {
            "status": "success",
            "challenge_id": challenge_record["_id"],
            "message": "NDR challenge submitted successfully. Investigation will begin within 2 hours.",
            "expected_resolution": (datetime.now() + timedelta(hours=24)).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create NDR challenge", error=str(e), order_id=challenge.order_id)
        raise HTTPException(status_code=500, detail="Failed to submit challenge")

@router.get("/alerts/{brand_id}")
async def get_seller_alerts(
    brand_id: str,
    db = Depends(get_database)
):
    """Get real-time alerts for seller"""
    try:
        alerts = []
        
        # Check for high RTO rate alerts
        recent_orders = await collections["orders"].find({
            "brand_id": brand_id,
            "created_at": {"$gte": datetime.now() - timedelta(days=7)}
        }).to_list(length=None)
        
        if recent_orders:
            rto_orders = [o for o in recent_orders if o.get("status") in ["RTO_INITIATED", "RTO_COMPLETED"]]
            rto_rate = len(rto_orders) / len(recent_orders) * 100
            
            if rto_rate > 15:
                alerts.append({
                    "type": "HIGH_RTO_RATE",
                    "severity": "high",
                    "title": "High RTO Rate Alert",
                    "message": f"Your RTO rate is {rto_rate:.1f}% this week (threshold: 15%)",
                    "action_required": True,
                    "suggestions": [
                        "Review delivery addresses for accuracy",
                        "Check carrier performance",
                        "Consider alternative delivery options"
                    ]
                })
        
        # Check for suspicious NDR patterns
        suspicious_ndrs = await collections["courier_events"].count_documents({
            "event_code": "NDR",
            "proof_required": True,
            "proof_validated": False,
            "created_at": {"$gte": datetime.now() - timedelta(days=7)}
        })
        
        if suspicious_ndrs > 5:
            alerts.append({
                "type": "SUSPICIOUS_NDR_PATTERN",
                "severity": "medium",
                "title": "Suspicious NDR Activity",
                "message": f"{suspicious_ndrs} suspicious NDRs detected this week",
                "action_required": True,
                "suggestions": [
                    "Review NDR events for proof validation failures",
                    "Consider challenging invalid NDRs",
                    "Escalate to carrier management"
                ]
            })
        
        # Positive alerts for cost savings
        prevented_rtos = await collections["courier_events"].count_documents({
            "overturned_flag": True,
            "created_at": {"$gte": datetime.now() - timedelta(days=7)}
        })
        
        if prevented_rtos > 0:
            cost_saved = prevented_rtos * 200
            alerts.append({
                "type": "COST_SAVINGS",
                "severity": "info",
                "title": "RTO Prevention Success",
                "message": f"₹{cost_saved} saved by preventing {prevented_rtos} RTOs this week",
                "action_required": False,
                "suggestions": []
            })
        
        return {
            "brand_id": brand_id,
            "alerts": alerts,
            "total_count": len(alerts),
            "high_priority_count": len([a for a in alerts if a["severity"] == "high"]),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get seller alerts", error=str(e), brand_id=brand_id)
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")

# Helper function to get database (to be imported from main server.py)
async def get_database():
    from server import db
    return db