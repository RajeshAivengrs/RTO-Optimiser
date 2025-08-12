# RTO Optimizer Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY backend/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ /app/backend/
COPY frontend/build/ /app/frontend/build/

# Set environment variables
ENV ENV=production
ENV LOG_LEVEL=INFO
ENV TIMEZONE=Asia/Kolkata

# Expose port
EXPOSE 8001

# Start command
CMD ["python", "-m", "uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8001"]