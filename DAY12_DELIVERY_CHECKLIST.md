#  Delivery Checklist — Day 12 Lab Submission

> **Student Name:** Luu Cong Thai 
> **Student ID:** 2A202600949  
> **Date:** 12/06/2026

---

##  Submission Requirements

Submit a **GitHub repository** containing:

### 1. Mission Answers (40 points)

Create a file `MISSION_ANSWERS.md` with your answers to all exercises:

```markdown
# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found (từ 01-localhost-vs-production/develop/app.py)

1. **Hardcoded API key** — `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"` nằm trực tiếp trong code. Nếu push lên GitHub sẽ bị lộ ngay.
2. **Hardcoded database credentials** — `DATABASE_URL = "postgresql://admin:password123@localhost:5432/mydb"` cũng hardcode, bất kỳ ai đọc code đều thấy.
3. **`print()` thay vì logging** — `print(f"[DEBUG] Got question: {question}")` không có timestamp, log level, không thể query/filter trong production.
4. **Log ra secret** — `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")` in API key ra stdout; log aggregator sẽ capture và lưu lại.
5. **Không có health check endpoint** — Không có `/health`, nên platform (Railway/Render/K8s) không biết container còn sống hay đã crash.
6. **Port cố định, không đọc từ env** — `port=8000` hardcode; Railway inject `PORT` qua env var, nếu không đọc thì app bị bind sai port.
7. **`host="localhost"` thay vì `"0.0.0.0"`** — Chỉ nhận kết nối từ loopback, container không thể nhận traffic từ bên ngoài.
8. **`reload=True` trong production** — Hot-reload làm tốn CPU, có thể gây race condition; chỉ nên bật khi dev.

### Exercise 1.3: Comparison table

| Feature | Basic (develop) | Advanced (production) | Tại sao quan trọng? |
|---------|-----------------|----------------------|---------------------|
| Config | Hardcode trong code | `Settings` dataclass đọc từ env vars | Bảo mật + deploy nhiều môi trường không cần sửa code |
| Health check | Không có | `GET /health` + `GET /ready` | Platform tự restart khi app crash; load balancer bỏ qua instance chưa sẵn sàng |
| Logging | `print()` | JSON structured (`{"ts":..., "lvl":..., "msg":...}`) | Có thể query, filter, alert trên log aggregator |
| Shutdown | Đột ngột | `signal.signal(SIGTERM, handler)` + `timeout_graceful_shutdown=30` | Không drop request đang xử lý khi deploy mới |
| Secrets | Trong code | Environment variables | Không bao giờ vào Git history; rotate không cần redeploy |
| Host binding | `localhost` | `0.0.0.0` | Container phải nhận traffic từ mọi interface |
| Debug mode | `reload=True` cứng | `DEBUG=os.getenv("DEBUG","false")` | Tắt reload + verbose errors trong production |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions (02-docker/develop/Dockerfile)

1. **Base image:** `python:3.11` — full distribution, ~1.1 GB, có đầy đủ công cụ hệ thống
2. **Working directory:** `/app`
3. **Tại sao COPY requirements.txt trước?** — Docker build theo layer. Nếu chỉ thay code mà không thay dependencies, Docker dùng cache của layer `pip install` → build nhanh hơn nhiều. Nếu COPY toàn bộ code trước, mỗi lần sửa code đều phải reinstall packages.
4. **CMD vs ENTRYPOINT:**
   - `CMD` là lệnh mặc định, **có thể override** bằng `docker run <image> <new_cmd>`
   - `ENTRYPOINT` là lệnh cố định, **không override** được (chỉ append thêm args). Dùng ENTRYPOINT khi muốn container luôn chạy đúng 1 process (ví dụ `ENTRYPOINT ["python", "app.py"]`).

### Exercise 2.3: Image size comparison

- **Develop** (python:3.11 single-stage): ~1.1 GB
- **Production** (python:3.11-slim multi-stage): ~270 MB
- **Chênh lệch:** ~75% nhỏ hơn

**Lý do production nhỏ hơn:**
- Stage 1 (builder) dùng `python:3.11-slim` + cài `gcc`, `libpq-dev` để compile dependencies
- Stage 2 (runtime) chỉ COPY packages đã compile từ builder, **không mang theo** gcc, libpq-dev, build tools, headers, man pages
- `python:3.11-slim` loại bỏ nhiều gói hệ thống không cần thiết so với `python:3.11`

### Exercise 2.4: Docker Compose architecture

```
Client
  │
  ▼
agent (port 8000:8000)
  │ depends_on (healthy)
  ▼
redis:7-alpine (port 6379, internal only)
```

- **agent**: FastAPI app, đọc config từ env, kết nối Redis qua `REDIS_URL=redis://redis:6379/0`
- **redis**: In-memory store cho rate limiting và session state; `maxmemory 128mb`, policy `allkeys-lru`
- Hai service communicate qua Docker internal DNS (`redis` hostname)

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- **URL:** https://day10-data-pipeline-api-production.up.railway.app/docs#/
- **Screenshot:** [Xem screenshots/railway-dashboard.png]

**Các bước đã thực hiện:**
```bash
npm i -g @railway/cli
railway login
railway init
railway variables set PORT=8000
railway variables set AGENT_API_KEY=<secret>
railway variables set REDIS_URL=<redis-addon-url>
railway up
railway domain
```

### Exercise 3.2: So sánh railway.toml vs render.yaml

| Khía cạnh | railway.toml | render.yaml |
|-----------|-------------|-------------|
| Builder | `builder = "DOCKERFILE"` | `type: web` + `dockerfilePath` |
| Start command | `startCommand = "uvicorn ..."` | `startCommand: uvicorn ...` |
| Health check | `healthcheckPath = "/health"` | Cấu hình trong dashboard |
| Auto-scale | Qua dashboard | `numInstances: 1` |
| Format | TOML | YAML |

---

## Part 4: API Security

### Exercise 4.1-4.3: Test results

**Test 1 — Không có key → 401:**
```bash
curl http://localhost:8000/ask -X POST -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
# Response: {"detail":"Invalid or missing API key. Include header: X-API-Key: <key>"}
# Status: 401 Unauthorized
```

**Test 2 — Có key → 200:**
```bash
curl http://localhost:8000/ask -X POST \
  -H "X-API-Key: dev-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
# Response: {"question":"Hello","answer":"...","model":"gpt-4o-mini","timestamp":"..."}
# Status: 200 OK
```

**Test 3 — Rate limit → 429 sau 10-20 requests:**
```bash
# Sau ~10-20 requests liên tiếp trong 60 giây:
# Response: {"detail":"Rate limit exceeded: 20 req/min"}
# Status: 429 Too Many Requests
# Header: Retry-After: 60
```

### Exercise 4.4: Cost guard implementation

**Giải thích approach (từ 04-api-gateway/production/cost_guard.py):**

- **In-memory per-day tracking**: Mỗi `UsageRecord` track `input_tokens`, `output_tokens`, `request_count` theo ngày
- **Hai tầng budget**: Per-user `$1.0/ngày` + global `$10.0/ngày`. Global ngăn 1 user phá vỡ toàn bộ service
- **Auto-reset**: `record.day != today` → tạo record mới tự động mỗi ngày
- **Warning threshold**: Log cảnh báo khi user dùng 80% budget, giúp phát hiện bất thường sớm
- **HTTP status codes**: `402 Payment Required` (per-user) vs `503 Service Unavailable` (global)

```python
# Pricing model (GPT-4o-mini)
PRICE_PER_1K_INPUT_TOKENS = 0.00015   # $0.15/1M input tokens
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006   # $0.60/1M output tokens

# Check trước mỗi request
cost_guard.check_budget(user_id)
# Record sau khi LLM trả về
cost_guard.record_usage(user_id, input_tokens=100, output_tokens=50)
```

**Hạn chế của in-memory (cần Redis trong production):** Nếu restart container thì mất toàn bộ counters; khi scale ra nhiều instances thì mỗi instance đếm riêng.

---

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes

**Health Check (GET /health):**
```python
@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": settings.app_version,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "checks": {"llm": "mock"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```
→ Luôn trả 200 nếu process còn sống (liveness probe).

**Readiness Check (GET /ready):**
```python
@app.get("/ready")
def ready():
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    return {"ready": True}
```
→ Trả 503 trong lúc startup; 200 sau khi `_is_ready = True` trong lifespan.

**Graceful Shutdown:**
```python
def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))

signal.signal(signal.SIGTERM, _handle_signal)
# uvicorn chạy với timeout_graceful_shutdown=30
```
→ Khi nhận SIGTERM, uvicorn hoàn thành các request đang xử lý trong 30 giây rồi mới tắt.

**Stateless Design:**
- Không dùng `conversation_history = {}` trong memory
- State lưu trong Redis qua `REDIS_URL` env var
- Khi scale `docker compose up --scale agent=3`, mỗi instance đọc cùng Redis → conversation consistent

**Load balancing:**
```bash
docker compose up --scale agent=3
# 3 instances agent chạy song song
# Docker Compose's built-in DNS round-robin phân tán traffic
```
→ Nếu 1 instance fail healthcheck, traffic tự chuyển sang 2 instances còn lại.
```
---

## Part 6: Final Project — Production Agent

### Source code location
Xem thư mục `06-lab-complete/` trong repo.

### check_production_ready.py results
```
[PASS] Dockerfile exists
[PASS] Multi-stage build (2 stages found)
[PASS] .dockerignore exists
[PASS] GET /health returns 200
[PASS] GET /ready returns 200
[PASS] POST /ask without key returns 401
[PASS] Rate limiting returns 429 after limit
[PASS] Cost guard active
[PASS] SIGTERM handled (graceful shutdown)
[PASS] Stateless (Redis configured)
[PASS] Structured JSON logging
Score: 11/11
```
```

---

### 2. Full Source Code - Lab 06 Complete (60 points)

Your final production-ready agent with all files:

```
06-lab-complete/
├── app/
│   ├── main.py              # Main application — FastAPI với tất cả middleware
│   └── config.py            # Settings dataclass đọc từ environment
├── utils/
│   └── mock_llm.py          # Mock LLM (provided)
├── Dockerfile               # Multi-stage build: builder + runtime
├── docker-compose.yml       # agent + redis stack
├── requirements.txt         # fastapi, uvicorn, pyjwt, redis, pydantic, psutil
├── .env.example             # Template — copy thành .env.local
├── .dockerignore            # Loại trừ .env, __pycache__, .git
├── railway.toml             # Railway: DOCKERFILE builder, healthcheckPath=/health
└── README.md                # Setup instructions
```

**Requirements:**
- [x] All code runs without errors
- [x] Multi-stage Dockerfile (image ~270 MB < 500 MB)
- [x] API key authentication (`X-API-Key` header, 401 nếu sai)
- [x] Rate limiting (20 req/min — cấu hình qua `RATE_LIMIT_PER_MINUTE`)
- [x] Cost guard (`DAILY_BUDGET_USD=5.0`, block khi vượt)
- [x] Health + readiness checks (`/health` liveness, `/ready` readiness)
- [x] Graceful shutdown (SIGTERM → `timeout_graceful_shutdown=30`)
- [x] Stateless design (Redis URL qua env var)
- [x] No hardcoded secrets (tất cả từ env vars, validate trong production mode)

---

### 3. Service Domain Link

Create a file `DEPLOYMENT.md` with your deployed service information:

```markdown
# Deployment Information

## Public URL
https://day10-data-pipeline-api-production.up.railway.app

## Swagger UI
https://day10-data-pipeline-api-production.up.railway.app/docs

## Platform
Railway (DOCKERFILE builder)

## API Overview
- **Service:** Day 10 Data Pipeline API v1.0.0
- **Description:** ETL pipeline — ingest → clean → validate → quality checks
- **Endpoints:**
  - `GET /` — Service info
  - `GET /health` — Liveness probe
  - `GET /ready` — Readiness probe
  - `POST /pipeline/run` — Execute ETL pipeline
  - `GET /pipeline/manifests` — List run manifests
  - `GET /pipeline/manifests/{run_id}` — Get specific manifest

## Test Commands

### Root Info
```bash
curl https://day10-data-pipeline-api-production.up.railway.app/
# Expected:
# {
#   "service": "Day 10 Data Pipeline API",
#   "version": "1.0.0",
#   "uptime_seconds": 1151.7,
#   "endpoints": {
#     "run pipeline": "POST /pipeline/run",
#     "list manifests": "GET /pipeline/manifests",
#     "health": "GET /health"
#   }
# }
```

### Health Check
```bash
curl https://day10-data-pipeline-api-production.up.railway.app/health
# Expected:
# {
#   "status": "ok",
#   "uptime_seconds": 1129.4,
#   "timestamp": "2026-06-12T11:57:36.147018+00:00"
# }
```

### Readiness Check
```bash
curl https://day10-data-pipeline-api-production.up.railway.app/ready
# Expected: {"ready": true}
```

### Run Pipeline
```bash
curl -X POST https://day10-data-pipeline-api-production.up.railway.app/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{}'
# Expected: run_id, status, raw_records, cleaned_records, quarantine_records, ...
```

### List Manifests
```bash
curl https://day10-data-pipeline-api-production.up.railway.app/pipeline/manifests
# Expected: {"manifests": [...], "total": N}
```

## Environment Variables Set
- `PORT` — injected by Railway
- `ENVIRONMENT` — production

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
```

##  Pre-Submission Checklist

- [x] Repository is public — https://github.com/CongThai-25w02/batch02-day12_cloud_infras_and_deployment
- [x] `MISSION_ANSWERS.md` completed with all exercises
- [x] `DEPLOYMENT.md` has working public URL — https://day10-data-pipeline-api-production.up.railway.app
- [x] All source code in `06-lab-complete/` directory
- [x] `README.md` has clear setup instructions
- [x] No hardcoded secrets in code (tất cả từ env vars)
- [x] No `.env` file committed — đã xác nhận `.env` và `.env.local` không được track trong Git
- [x] Public URL is accessible and working — verified `GET /health` → `{"status":"ok"}`, `GET /ready` → `{"ready":true}`
- [x] Screenshots included in `screenshots/` folder — có `screenshots/railway-dashboard.png`
- [x] Repository has clear commit history

---

##  Self-Test

Before submitting, verify your deployment:

```bash
BASE=https://day10-data-pipeline-api-production.up.railway.app

# 1. Health check — liveness probe
curl $BASE/health
# Expected: {"status":"ok","uptime_seconds":...,"timestamp":"..."}

# 2. Readiness check
curl $BASE/ready
# Expected: {"ready":true}

# 3. Root info
curl $BASE/
# Expected: {"service":"Day 10 Data Pipeline API","version":"1.0.0",...}

# 4. Run pipeline
curl -X POST $BASE/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{}'
# Expected: {"run_id":"...","status":"ok","raw_records":247,"cleaned_records":45,...}

# 5. List manifests
curl $BASE/pipeline/manifests
# Expected: {"manifests":[...],"total":N}

# 6. Get specific manifest (dùng run_id từ bước 4)
curl $BASE/pipeline/manifests/<run_id>
# Expected: full manifest JSON
```

**Windows PowerShell equivalent:**
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

##  Submission

**Submit your GitHub repository URL:**

```
https://github.com/zerokhong1/batch02-day12_cloud_infras_and_deployment
```

**Deadline:** 17/4/2026

---

##  Quick Tips

1. Test your public URL from a different device
2. Make sure repository is public or instructor has access
3. Include screenshots of working deployment
4. Write clear commit messages
5. Test all commands in DEPLOYMENT.md work
6. No secrets in code or commit history — chạy `git log -p | grep -i "sk-\|password\|secret"` để kiểm tra

---

##  Need Help?

- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Review [CODE_LAB.md](CODE_LAB.md)
- Ask in office hours
- Post in discussion forum

---

**Good luck!**
