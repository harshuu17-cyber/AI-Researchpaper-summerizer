# ==========================================
# STAGE 1: Build React Frontend
# ==========================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci || npm install

COPY frontend/ ./
RUN npm run build

# ==========================================
# STAGE 2: Python Backend & Production Server
# ==========================================
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/ ./backend/

# Copy compiled frontend dist into backend/dist for unified serving
COPY --from=frontend-builder /app/frontend/dist ./backend/dist

# Ensure persistent directories exist
RUN mkdir -p /app/uploads /app/outputs

ENV UPLOAD_DIR=/app/uploads \
    OUTPUTS_DIR=/app/outputs

EXPOSE 8000

WORKDIR /app/backend

# Run FastAPI with dynamic port binding for cloud providers
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
