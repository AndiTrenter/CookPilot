# --- Stage 1: build React frontend ---
FROM node:20-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/yarn.lock* ./
RUN yarn install --frozen-lockfile || yarn install
COPY frontend/ .
# The built image serves the SPA at the container root, so the frontend must
# call the backend relatively.
ENV REACT_APP_BACKEND_URL=""
RUN yarn build

# --- Stage 2: backend runtime ---
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    COOKPILOT_FRONTEND_DIR=/app/frontend_dist

# OCR + PDF tooling (prepared for receipt module).
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng \
        poppler-utils libjpeg62-turbo zlib1g \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/backend/
COPY --from=frontend /frontend/build/ /app/frontend_dist/

# Persistent data dir for uploads
RUN mkdir -p /data/uploads
ENV COOKPILOT_UPLOADS=/data/uploads

EXPOSE 8001
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
