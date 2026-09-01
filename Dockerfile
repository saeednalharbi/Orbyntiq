# syntax=docker/dockerfile:1

# ============================================================
# Build stage
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip wheel \
    --wheel-dir /wheels \
    "setuptools==84.0.0" \
    "wheel==0.48.0" \
    .


# ============================================================
# Runtime stage
# ============================================================
FROM python:3.11-slim AS runtime

ARG APP_UID=10001
ARG APP_GID=10001

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ORBYNTIQ_API_HOST=0.0.0.0 \
    ORBYNTIQ_API_PORT=8000

RUN groupadd --gid "${APP_GID}" orbyntiq \
    && useradd \
        --uid "${APP_UID}" \
        --gid "${APP_GID}" \
        --create-home \
        --shell /usr/sbin/nologin \
        orbyntiq

COPY --from=builder /wheels /wheels

RUN python -m pip install \
        --no-cache-dir \
        --no-index \
        --find-links=/wheels \
        "setuptools==84.0.0" \
        "wheel==0.48.0" \
        orbyntiq \
    && rm -rf /wheels

USER orbyntiq

EXPOSE 8000

HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
    --start-period=20s \
    --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"]

CMD ["uvicorn", "orbyntiq.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
