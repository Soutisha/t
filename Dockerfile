# Single-origin deployment: React UI and FastAPI API behind Nginx.
FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json ./package.json
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 tesseract-ocr nginx supervisor && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./requirements.txt
COPY backend/requirements-cloud.txt ./requirements-cloud.txt
RUN pip install --no-cache-dir -r requirements.txt -r requirements-cloud.txt
COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./alembic.ini
COPY --from=frontend-build /frontend/dist /usr/share/nginx/html
COPY deploy/nginx.conf /etc/nginx/sites-available/default
COPY deploy/supervisord.conf /etc/supervisor/conf.d/pitstop.conf
RUN useradd --create-home --uid 10001 appuser && mkdir -p /app/var/trustvision /app/var/objects && chown -R appuser:appuser /app/var
EXPOSE 10000
CMD ["sh", "-c", "alembic -c alembic.ini upgrade head && exec supervisord -n -c /etc/supervisor/supervisord.conf"]
