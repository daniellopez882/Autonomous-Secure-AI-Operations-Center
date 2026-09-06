# syntax=docker/dockerfile:1
#
# A-SOC backend image.
#
# Fixes over the previous revision:
#   * CMD was `python main.py`. main.py is the one-shot CLI demo: it prints a
#     scripted cycle and calls sys.exit. The container therefore started,
#     printed, and died -- it never served the API that docker-compose maps
#     port 8000 to. It now runs uvicorn.
#   * ran as root; now UID 1001
#   * no HEALTHCHECK; now probes /health
#   * single stage carrying gcc and build headers into the runtime image;
#     now multi-stage, so the compiler is not shipped

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    ENVIRONMENT=production \
    BIND_HOST=0.0.0.0 \
    PORT=8000 \
    LOG_LEVEL=INFO \
    JSON_LOGS=true

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 asoc \
    && useradd --system --uid 1001 --gid asoc --create-home asoc

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=asoc:asoc . .

RUN mkdir -p /app/data && chown -R asoc:asoc /app/data

USER asoc

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:8000/health || exit 1

# exec form so uvicorn is PID 1 and receives SIGTERM directly.
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", \
     "--timeout-graceful-shutdown", "20", "--no-server-header"]
