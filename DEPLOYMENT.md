# Deployment Information

## Public URL

https://day10-data-pipeline-api-production.up.railway.app

## Swagger UI

https://day10-data-pipeline-api-production.up.railway.app/docs

## Platform

Railway — builder: `DOCKERFILE`, branch: `main`

## API Overview

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/` | GET | Service info |
| `/health` | GET | Liveness probe |
| `/ready` | GET | Readiness probe |
| `/pipeline/run` | POST | Execute ETL pipeline |
| `/pipeline/manifests` | GET | List run manifests |
| `/pipeline/manifests/{run_id}` | GET | Get specific manifest |

---

## Test Commands

### Root Info
```bash
curl https://day10-data-pipeline-api-production.up.railway.app/
```
Expected:
```json
{
  "service": "Day 10 Data Pipeline API",
  "version": "1.0.0",
  "uptime_seconds": 1151.7,
  "endpoints": {
    "run pipeline": "POST /pipeline/run",
    "list manifests": "GET /pipeline/manifests",
    "health": "GET /health"
  }
}
```

### Health Check
```bash
curl https://day10-data-pipeline-api-production.up.railway.app/health
```
Expected:
```json
{
  "status": "ok",
  "uptime_seconds": 1129.4,
  "timestamp": "2026-06-12T11:57:36.147018+00:00"
}
```

### Readiness Check
```bash
curl https://day10-data-pipeline-api-production.up.railway.app/ready
```
Expected:
```json
{"ready": true}
```

### Run Pipeline
```bash
curl -X POST https://day10-data-pipeline-api-production.up.railway.app/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{}'
```
Expected:
```json
{
  "run_id": "2026-06-12T...",
  "status": "ok",
  "raw_records": 247,
  "cleaned_records": 45,
  "quarantine_records": 202,
  "duration_ms": ...
}
```

### List Manifests
```bash
curl https://day10-data-pipeline-api-production.up.railway.app/pipeline/manifests
```
Expected:
```json
{"manifests": [...], "total": N}
```

### Get Specific Manifest
```bash
curl https://day10-data-pipeline-api-production.up.railway.app/pipeline/manifests/<run_id>
```

---

## Windows PowerShell

```powershell
$BASE = "https://day10-data-pipeline-api-production.up.railway.app"

# Health check
Invoke-WebRequest -Uri "$BASE/health" | Select-Object -Expand Content

# Readiness
Invoke-WebRequest -Uri "$BASE/ready" | Select-Object -Expand Content

# Run pipeline
Invoke-WebRequest -Uri "$BASE/pipeline/run" -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{}' | Select-Object -Expand Content

# List manifests
Invoke-WebRequest -Uri "$BASE/pipeline/manifests" | Select-Object -Expand Content
```

---

## Environment Variables Set

| Variable | Value |
|----------|-------|
| `PORT` | Injected by Railway |
| `ENVIRONMENT` | production |

---

## Screenshots

- [Railway Dashboard](screenshots/railway-dashboard.png)
