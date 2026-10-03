FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN VITE_FREE_HOSTING_MODE=true npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CV_ENABLED=false
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libglib2.0-0 libgl1 nginx supervisor && rm -rf /var/lib/apt/lists/*
COPY backend/requirements*.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY deploy/render/ ./deploy/
COPY --from=frontend /build/dist /usr/share/nginx/html
RUN useradd -m -u 10001 appuser && mkdir -p /data && chown appuser:appuser /data && rm -f /etc/nginx/sites-enabled/default
EXPOSE 10000
CMD ["python", "/app/deploy/start.py"]
