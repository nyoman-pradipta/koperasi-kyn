# ─── Stage 1: Build Frontend ────────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# ─── Stage 2: Python Backend + Frontend dist ─────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Sistem dependensi minimal
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
  && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Salin kode backend
COPY backend/ ./backend/

# Salin hasil build frontend dari stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Folder uploads & database (akan di-mount via volume di production)
RUN mkdir -p /app/uploads /app/data

# Port yang diekspos
EXPOSE 8002

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8002"]
