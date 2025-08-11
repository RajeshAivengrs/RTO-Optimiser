import os
import json
import uuid
import logging
import structlog
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

import pytz
from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError, Field
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
import httpx
from geopy.distance import geodesic

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Environment configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/rto_optimizer")
TIMEZONE = pytz.timezone(os.getenv("TIMEZONE", "Asia/Kolkata"))

# Database setup
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# Database Models
class Brand(Base):
    __tablename__ = "brands"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    webhook_secret = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE), onupdate=lambda: datetime.now(TIMEZONE))

class Address(Base):
    __tablename__ = "addresses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line1 = Column(String(500), nullable=False)
    line2 = Column(String(500), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    pincode = Column(String(20), nullable=False)
    country = Column(String(100), default="India")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    confidence_score = Column(Float, default=0.0)
    normalized_address = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE))
    
    __table_args__ = (
        Index('idx_addresses_pincode', 'pincode'),
        Index('idx_addresses_lat_lng', 'latitude', 'longitude'),
    )

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(String(255), unique=True, nullable=False)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False)
    customer_phone_hash = Column(String(255), nullable=False)  # Hashed for privacy
    customer_email_hash = Column(String(255), nullable=True)   # Hashed for privacy
    delivery_address_id = Column(UUID(as_uuid=True), ForeignKey("addresses.id"), nullable=False)
    order_value = Column(Float, nullable=False)
    payment_mode = Column(String(50), nullable=False)  # COD, PREPAID
    order_date = Column(DateTime(timezone=True), nullable=False)
    promised_delivery_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="PLACED")
    order_metadata = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE), onupdate=lambda: datetime.now(TIMEZONE))
    
    __table_args__ = (
        Index('idx_orders_order_id', 'order_id'),
        Index('idx_orders_brand_id', 'brand_id'),
        Index('idx_orders_status', 'status'),
        Index('idx_orders_payment_mode', 'payment_mode'),
    )

class Item(Base):
    __tablename__ = "items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    sku = Column(String(255), nullable=False)
    name = Column(String(500), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    weight_grams = Column(Integer, nullable=True)
    dimensions = Column(JSONB, nullable=True)  # {length, width, height}
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE))

class Shipment(Base):
    __tablename__ = "shipments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id = Column(String(255), unique=True, nullable=False)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    carrier = Column(String(100), nullable=False)
    awb_number = Column(String(255), nullable=True)
    pickup_date = Column(DateTime(timezone=True), nullable=True)
    expected_delivery_date = Column(DateTime(timezone=True), nullable=True)
    actual_delivery_date = Column(DateTime(timezone=True), nullable=True)
    current_status = Column(String(100), nullable=False)
    rto_initiated = Column(Boolean, default=False)
    rto_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE), onupdate=lambda: datetime.now(TIMEZONE))
    
    __table_args__ = (
        Index('idx_shipments_shipment_id', 'shipment_id'),
        Index('idx_shipments_awb', 'awb_number'),
        Index('idx_shipments_carrier', 'carrier'),
        Index('idx_shipments_status', 'current_status'),
    )

class CourierEvent(Base):
    __tablename__ = "courier_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id = Column(UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=False)
    event_code = Column(String(100), nullable=False)
    event_description = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    ndr_code = Column(String(100), nullable=True)
    ndr_reason = Column(Text, nullable=True)
    proof_required = Column(Boolean, default=False)
    proof_validated = Column(Boolean, default=False)
    gps_latitude = Column(Float, nullable=True)
    gps_longitude = Column(Float, nullable=True)
    call_duration_sec = Column(Integer, nullable=True)
    call_outcome = Column(String(100), nullable=True)
    overturned_flag = Column(Boolean, default=False)
    overturned_within_2h = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE))
    
    __table_args__ = (
        Index('idx_courier_events_shipment', 'shipment_id'),
        Index('idx_courier_events_code', 'event_code'),
        Index('idx_courier_events_ndr', 'ndr_code'),
        Index('idx_courier_events_timestamp', 'timestamp'),
    )

class RiskScore(Base):
    __tablename__ = "risk_scores"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_tier = Column(String(20), nullable=False)  # LOW, MED, HIGH
    features = Column(JSONB, nullable=True)
    model_version = Column(String(50), default="v1.0")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE))

class LaneScore(Base):
    __tablename__ = "lane_scores"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    carrier = Column(String(100), nullable=False)
    dest_pincode = Column(String(20), nullable=False)
    week_start = Column(DateTime(timezone=True), nullable=False)
    total_shipments = Column(Integer, default=0)
    on_time_percentage = Column(Float, default=0.0)
    rto_percentage = Column(Float, default=0.0)
    false_attempt_rate = Column(Float, default=0.0)
    suspect_ndr_rate = Column(Float, default=0.0)
    first_attempt_percentage = Column(Float, default=0.0)
    sla_score = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE))
    
    __table_args__ = (
        Index('idx_lane_scores_carrier_pin', 'carrier', 'dest_pincode'),
        Index('idx_lane_scores_week', 'week_start'),
    )

class MessageEvent(Base):
    __tablename__ = "message_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    channel = Column(String(50), nullable=False)  # WHATSAPP, SMS, IVR, EMAIL
    message_type = Column(String(100), nullable=False)
    content = Column(Text, nullable=True)
    status = Column(String(50), default="PENDING")  # PENDING, SENT, DELIVERED, FAILED
    response = Column(Text, nullable=True)
    external_message_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE), onupdate=lambda: datetime.now(TIMEZONE))

# Pydantic Models for API
class OrderRequest(BaseModel):
    order_id: str
    brand_id: str
    customer_phone: str
    customer_email: Optional[str] = None
    delivery_address: Dict[str, Any]
    items: List[Dict[str, Any]]
    order_value: float
    payment_mode: str
    order_date: str
    promised_delivery_date: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class CourierEventRequest(BaseModel):
    shipment_id: str
    event_code: str
    event_description: Optional[str] = None
    location: Optional[str] = None
    timestamp: str
    ndr_code: Optional[str] = None
    ndr_reason: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    call_duration_sec: Optional[int] = None
    call_outcome: Optional[str] = None

class NDRResolutionRequest(BaseModel):
    order_id: str
    action: str  # RESCHEDULE, CHANGE_ADDRESS, RTO, DISPUTE
    new_address: Optional[Dict[str, Any]] = None
    reschedule_date: Optional[str] = None
    customer_response: Optional[str] = None

# Database dependency
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Utility functions
def hash_pii(value: str) -> str:
    """Hash PII data for privacy"""
    import hashlib
    return hashlib.sha256(value.encode()).hexdigest()

def validate_gps_proximity(lat1: float, lng1: float, lat2: float, lng2: float, max_distance_meters: int = 200) -> bool:
    """Validate GPS coordinates are within specified distance"""
    try:
        distance = geodesic((lat1, lng1), (lat2, lng2)).meters
        return distance <= max_distance_meters
    except Exception as e:
        logger.error("GPS validation error", error=str(e))
        return False

# NDR Proof Validation Service
class NDRProofValidator:
    @staticmethod
    async def validate_proof_of_attempt(
        event: CourierEvent,
        delivery_address: Address,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Validate NDR proof of attempt according to business rules"""
        validation_result = {
            "is_valid": False,
            "gps_valid": False,
            "call_valid": False,
            "violations": []
        }
        
        # Check if this is a CUSTOMER_UNAVAILABLE NDR
        if event.event_code != "NDR" or event.ndr_code != "CUSTOMER_UNAVAILABLE":
            validation_result["is_valid"] = True
            return validation_result
        
        # Validate GPS proximity (within 200 meters)
        if (event.gps_latitude and event.gps_longitude and 
            delivery_address.latitude and delivery_address.longitude):
            gps_valid = validate_gps_proximity(
                event.gps_latitude, event.gps_longitude,
                delivery_address.latitude, delivery_address.longitude
            )
            validation_result["gps_valid"] = gps_valid
            if not gps_valid:
                validation_result["violations"].append("GPS location not within 200m of delivery address")
        else:
            validation_result["violations"].append("Missing GPS coordinates")
        
        # Validate call log (minimum 10 seconds duration)
        if event.call_duration_sec and event.call_duration_sec >= 10:
            validation_result["call_valid"] = True
        else:
            validation_result["violations"].append("Call duration less than 10 seconds or missing")
        
        validation_result["is_valid"] = validation_result["gps_valid"] and validation_result["call_valid"]
        
        return validation_result

# FastAPI app setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting RTO Optimizer API")
    try:
        # Create database tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down RTO Optimizer API")
    await engine.dispose()

app = FastAPI(
    title="RTO Optimizer API",
    description="Last-mile & RTO Optimization Platform for Bengaluru PoC",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    start_time = datetime.now()
    
    with structlog.contextvars.bind_contextvars(request_id=request_id):
        logger.info(
            "Request started",
            method=request.method,
            url=str(request.url),
            client=request.client.host if request.client else None
        )
        
        response = await call_next(request)
        
        process_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(
            "Request completed",
            status_code=response.status_code,
            process_time=process_time
        )
        
        return response

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(select(1))
        return {
            "status": "healthy",
            "timestamp": datetime.now(TIMEZONE).isoformat(),
            "service": "RTO Optimizer API",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unhealthy")

# Core API Endpoints

@app.post("/api/webhooks/order")
async def webhook_order(
    request: OrderRequest,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """Process incoming order webhook"""
    try:
        # Create or get brand
        brand_query = select(Brand).where(Brand.id == request.brand_id)
        result = await db.execute(brand_query)
        brand = result.scalar_one_or_none()
        
        if not brand:
            raise HTTPException(status_code=400, detail="Invalid brand_id")
        
        # Create address
        address_data = request.delivery_address
        address = Address(
            line1=address_data.get("line1", ""),
            line2=address_data.get("line2"),
            city=address_data.get("city", ""),
            state=address_data.get("state", ""),
            pincode=address_data.get("pincode", ""),
            country=address_data.get("country", "India")
        )
        db.add(address)
        await db.flush()
        
        # Create order with hashed PII
        order_date = datetime.fromisoformat(request.order_date.replace('Z', '+00:00'))
        promised_date = None
        if request.promised_delivery_date:
            promised_date = datetime.fromisoformat(request.promised_delivery_date.replace('Z', '+00:00'))
        
        order = Order(
            order_id=request.order_id,
            brand_id=brand.id,
            customer_phone_hash=hash_pii(request.customer_phone),
            customer_email_hash=hash_pii(request.customer_email) if request.customer_email else None,
            delivery_address_id=address.id,
            order_value=request.order_value,
            payment_mode=request.payment_mode,
            order_date=order_date,
            promised_delivery_date=promised_date,
            metadata=request.metadata
        )
        db.add(order)
        await db.flush()
        
        # Create items
        for item_data in request.items:
            item = Item(
                order_id=order.id,
                sku=item_data.get("sku", ""),
                name=item_data.get("name", ""),
                quantity=item_data.get("quantity", 1),
                unit_price=item_data.get("unit_price", 0.0),
                weight_grams=item_data.get("weight_grams"),
                dimensions=item_data.get("dimensions")
            )
            db.add(item)
        
        await db.commit()
        
        logger.info("Order created successfully", order_id=request.order_id)
        
        return {
            "status": "success",
            "order_id": request.order_id,
            "message": "Order processed successfully"
        }
        
    except ValidationError as e:
        logger.error("Validation error", error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except SQLAlchemyError as e:
        logger.error("Database error", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/webhooks/courier_event")
async def webhook_courier_event(
    request: CourierEventRequest,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """Process incoming courier event webhook with proof validation"""
    try:
        # Get shipment
        shipment_query = select(Shipment).where(Shipment.shipment_id == request.shipment_id)
        result = await db.execute(shipment_query)
        shipment = result.scalar_one_or_none()
        
        if not shipment:
            raise HTTPException(status_code=400, detail="Invalid shipment_id")
        
        # Parse timestamp
        event_timestamp = datetime.fromisoformat(request.timestamp.replace('Z', '+00:00'))
        
        # Create courier event
        courier_event = CourierEvent(
            shipment_id=shipment.id,
            event_code=request.event_code,
            event_description=request.event_description,
            location=request.location,
            timestamp=event_timestamp,
            ndr_code=request.ndr_code,
            ndr_reason=request.ndr_reason,
            gps_latitude=request.gps_latitude,
            gps_longitude=request.gps_longitude,
            call_duration_sec=request.call_duration_sec,
            call_outcome=request.call_outcome
        )
        
        # Check if proof validation is required
        if request.event_code == "NDR" and request.ndr_code == "CUSTOMER_UNAVAILABLE":
            courier_event.proof_required = True
            
            # Get delivery address for validation
            order_query = select(Order, Address).join(Address).where(Order.id == shipment.order_id)
            result = await db.execute(order_query)
            order_address = result.first()
            
            if order_address:
                order, address = order_address
                
                # Validate proof of attempt
                validator = NDRProofValidator()
                validation_result = await validator.validate_proof_of_attempt(
                    courier_event, address, db
                )
                
                courier_event.proof_validated = validation_result["is_valid"]
                
                if not validation_result["is_valid"]:
                    logger.warning(
                        "NDR proof validation failed",
                        shipment_id=request.shipment_id,
                        violations=validation_result["violations"]
                    )
                    
                    # Block RTO and trigger escalation
                    # TODO: Implement auto-escalation and priority reattempt logic
                    
        db.add(courier_event)
        await db.commit()
        
        logger.info(
            "Courier event processed",
            shipment_id=request.shipment_id,
            event_code=request.event_code,
            proof_required=courier_event.proof_required,
            proof_validated=courier_event.proof_validated
        )
        
        return {
            "status": "success",
            "event_id": str(courier_event.id),
            "proof_required": courier_event.proof_required,
            "proof_validated": courier_event.proof_validated,
            "message": "Courier event processed successfully"
        }
        
    except ValidationError as e:
        logger.error("Validation error", error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except SQLAlchemyError as e:
        logger.error("Database error", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/ndr/resolution")
async def ndr_resolution(
    request: NDRResolutionRequest,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """Handle NDR resolution based on customer response"""
    try:
        # Get order
        order_query = select(Order).where(Order.order_id == request.order_id)
        result = await db.execute(order_query)
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=400, detail="Invalid order_id")
        
        # Process resolution based on action
        resolution_data = {
            "order_id": request.order_id,
            "action": request.action,
            "timestamp": datetime.now(TIMEZONE).isoformat(),
            "status": "processed"
        }
        
        if request.action == "RESCHEDULE":
            if request.reschedule_date:
                new_date = datetime.fromisoformat(request.reschedule_date.replace('Z', '+00:00'))
                # Update order promised delivery date
                order.promised_delivery_date = new_date
                resolution_data["new_delivery_date"] = new_date.isoformat()
                
        elif request.action == "CHANGE_ADDRESS":
            if request.new_address:
                # Create new address
                new_address = Address(
                    line1=request.new_address.get("line1", ""),
                    line2=request.new_address.get("line2"),
                    city=request.new_address.get("city", ""),
                    state=request.new_address.get("state", ""),
                    pincode=request.new_address.get("pincode", ""),
                    country=request.new_address.get("country", "India")
                )
                db.add(new_address)
                await db.flush()
                
                # Update order delivery address
                order.delivery_address_id = new_address.id
                resolution_data["new_address_id"] = str(new_address.id)
                
        elif request.action == "DISPUTE":
            # Mark as disputed and trigger priority reattempt
            # Find the latest NDR event
            shipment_query = select(Shipment).where(Shipment.order_id == order.id)
            result = await db.execute(shipment_query)
            shipment = result.scalar_one_or_none()
            
            if shipment:
                # Check if dispute is within 2 hours
                ndr_event_query = select(CourierEvent).where(
                    CourierEvent.shipment_id == shipment.id,
                    CourierEvent.event_code == "NDR"
                ).order_by(CourierEvent.timestamp.desc())
                result = await db.execute(ndr_event_query)
                latest_ndr = result.first()
                
                if latest_ndr:
                    time_diff = datetime.now(TIMEZONE) - latest_ndr[0].timestamp.replace(tzinfo=TIMEZONE)
                    if time_diff <= timedelta(hours=2):
                        latest_ndr[0].overturned_within_2h = True
                        logger.info("NDR disputed within 2h window", order_id=request.order_id)
                
        elif request.action == "RTO":
            # Initiate RTO process
            shipment_query = select(Shipment).where(Shipment.order_id == order.id)
            result = await db.execute(shipment_query)
            shipment = result.scalar_one_or_none()
            
            if shipment:
                shipment.rto_initiated = True
                order.status = "RTO_INITIATED"
        
        # Update order metadata with resolution
        if not order.metadata:
            order.metadata = {}
        order.metadata["ndr_resolution"] = resolution_data
        
        await db.commit()
        
        logger.info(
            "NDR resolution processed",
            order_id=request.order_id,
            action=request.action
        )
        
        return {
            "status": "success",
            "order_id": request.order_id,
            "action": request.action,
            "message": "NDR resolution processed successfully"
        }
        
    except ValidationError as e:
        logger.error("Validation error", error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except SQLAlchemyError as e:
        logger.error("Database error", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)