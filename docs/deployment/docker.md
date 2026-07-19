# Docker Deployment

## Quick Start

```bash
docker run -p 8311:8311 \
  -e OPENAI_API_KEY="sk-..." \
  -v $(pwd)/config:/etc/model-canary \
  ghcr.io/model-canary/model-canary:latest
```

## Docker Compose

```bash
docker compose up

# With PostgreSQL:
docker compose --profile postgres up

# Full stack:
docker compose --profile full up
```

## Building Locally

```bash
docker build -t model-canary -f docker/Dockerfile .
```
