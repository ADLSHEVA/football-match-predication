# syntax=docker/dockerfile:1
# ─── Stage 1: build the React (Vite) frontend ─────────────
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build          # → /app/frontend/dist

# ─── Stage 2: FastAPI backend serving API + built frontend ─
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app/backend

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
# main.py serves the static build from <project>/frontend/dist
# (BASE_DIR = /app/backend → BASE_DIR.parent/frontend/dist = /app/frontend/dist)
COPY --from=frontend /app/frontend/dist /app/frontend/dist

EXPOSE 8000
# Render and most PaaS inject $PORT; default to 8000 for local `docker run`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
