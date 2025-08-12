#!/bin/bash

# RTO Optimizer Production Startup Script
echo "Starting RTO Optimizer (Bengaluru PoC)..."

# Set environment variables for production
export ENV=production
export LOG_LEVEL=INFO
export TIMEZONE=Asia/Kolkata

# Start the FastAPI server
cd /app/backend
python -m uvicorn server:app --host 0.0.0.0 --port 8001 --workers 1