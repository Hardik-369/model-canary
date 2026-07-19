FROM python:3.13-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml .
COPY src/ src/

RUN uv build --wheel

FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONUNBUFFERED=1
ENV MODEL_CANARY_CONFIG=/etc/model-canary/config.yml

VOLUME ["/etc/model-canary", "/var/lib/model-canary"]

EXPOSE 8311

ENTRYPOINT ["/entrypoint.sh"]
CMD ["model-canary", "dashboard"]
