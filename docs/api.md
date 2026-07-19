# API Reference

Model Canary provides a full REST API built with FastAPI.

## Base URL

```
http://localhost:8311
```

## Endpoints

### Health Check

```
GET /health
```

Response:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "service": "model-canary"
}
```

### Runs

```
GET /api/v1/runs
GET /api/v1/runs/{run_id}
POST /api/v1/run
POST /api/v1/run/prompt
```

### Drift Reports

```
GET /api/v1/drifts
GET /api/v1/drifts/{drift_id}
```

Query parameters: `prompt_name`, `model`, `provider`, `severity`, `limit`, `offset`

### Fingerprints

```
GET /api/v1/fingerprints?prompt_name=...
```

### Benchmark

```
POST /api/v1/benchmark
```

### Compare

```
GET /api/v1/compare?prompt_name=...&provider_a=...&provider_b=...
```

### Stats

```
GET /api/v1/stats
```

### Providers

```
GET /api/v1/providers
```

### Prompts

```
GET /api/v1/prompts
```

### Interactive Docs

```
GET /docs
GET /redoc
GET /openapi.json
```
