# syntax=docker/dockerfile:1
FROM node:24-alpine AS web
WORKDIR /web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web/ ./
RUN npm run build

FROM python:3.12-slim AS base
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/docs/data
RUN pip install --no-cache-dir uv
WORKDIR /app/apps/api
COPY apps/api/pyproject.toml apps/api/uv.lock ./

FROM base AS dev
RUN uv sync --frozen --no-install-project
COPY apps/api/ ./
COPY docs/data /app/docs/data

FROM base AS runtime
RUN uv sync --frozen --no-install-project --no-dev
COPY apps/api/ ./
COPY docs/data /app/docs/data
COPY --from=web /web/dist /app/static
ENV STATIC_DIR=/app/static
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
