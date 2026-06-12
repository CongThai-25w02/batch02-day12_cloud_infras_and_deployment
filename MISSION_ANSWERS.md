# Day 12 Lab - Mission Answers

> **Student:** Luu Cong Thai — 2A202600949

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found (từ `01-localhost-vs-production/develop/app.py`)

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

### Exercise 2.1: Dockerfile questions (từ `02-docker/develop/Dockerfile`)

1. **Base image:** `python:3.11` — full distribution, ~1.1 GB, có đầy đủ công cụ hệ thống.
2. **Working directory:** `/app`
3. **Tại sao COPY requirements.txt trước?** — Docker build theo layer. Nếu chỉ thay code mà không thay dependencies, Docker dùng cache của layer `pip install` → build nhanh hơn. Nếu COPY toàn bộ code trước, mỗi lần sửa code đều phải reinstall packages từ đầu.
4. **CMD vs ENTRYPOINT:**
   - `CMD` là lệnh mặc định, **có thể override** khi chạy `docker run <image> <lệnh_khác>`
   - `ENTRYPOINT` là lệnh cố định, **không override** được (chỉ append thêm args). Dùng ENTRYPOINT khi muốn container luôn chạy đúng 1 process cố định.

### Exercise 2.3: Image size comparison

| | Develop | Production |
|--|---------|------------|
| Base image | `python:3.11` (full, single-stage) | `python:3.11-slim` (multi-stage) |
| Size | ~1.1 GB | ~270 MB |
| Chênh lệch | — | **~75% nhỏ hơn** |

**Lý do production nhỏ hơn:**
- Stage 1 (builder): cài `gcc`, `libpq-dev` để compile dependencies → xong việc thì bỏ
- Stage 2 (runtime): chỉ COPY packages đã compiled, **không mang theo** build tools, headers, man pages
- `python:3.11-slim` loại bỏ nhiều gói hệ thống không cần cho runtime

### Exercise 2.4: Docker Compose architecture

```
Client
  │
  ▼
agent (port 8000:8000)
  │ depends_on: redis (healthy)
  ▼
redis:7-alpine (port 6379, internal only)
```

- **agent**: FastAPI app, đọc config từ env, kết nối Redis qua `REDIS_URL=redis://redis:6379/0`
- **redis**: In-memory store cho rate limiting và session state; `maxmemory 128mb`, policy `allkeys-lru`
- Hai service giao tiếp qua Docker internal DNS (`redis` hostname)

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- **Public URL:** https://day10-data-pipeline-api-production.up.railway.app
- **Swagger UI:** https://day10-data-pipeline-api-production.up.railway.app/docs
- **Screenshot:** [screenshots/railway-dashboard.png](screenshots/railway-dashboard.png)

**Các bước thực hiện:**
```bash
npm i -g @railway/cli
railway login
railway init
railway variables set PORT=8000
railway up
railway domain
```

### Exercise 3.2: So sánh `railway.toml` vs `render.yaml`

| Khía cạnh | `railway.toml` | `render.yaml` |
|-----------|---------------|--------------|
| Format | TOML | YAML |
| Builder | `builder = "DOCKERFILE"` | `type: web` + `dockerfilePath` |
| Start command | `startCommand = "uvicorn ..."` | `startCommand: uvicorn ...` |
| Health check | `healthcheckPath = "/health"` | Cấu hình trong dashboard |
| Restart policy | `restartPolicyType = "ON_FAILURE"` | Tự động |
| Auto-scale | Qua Railway dashboard | `numInstances: 1` trong file |

---

## Part 4: API Security

### Exercise 4.1-4.3: Test results

**Test 1 — Không có key → 401:**
```bash
curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
# Response: {"detail":"Invalid or missing API key. Include header: X-API-Key: <key>"}
# Status: 401 Unauthorized
```

**Test 2 — Có key hợp lệ → 200:**
```bash
curl http://localhost:8000/ask -X POST \
  -H "X-API-Key: dev-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
# Response: {"question":"Hello","answer":"...","model":"gpt-4o-mini","timestamp":"..."}
# Status: 200 OK
```

**Test 3 — Rate limit → 429 sau 20+ requests trong 60 giây:**
```bash
# Response: {"detail":"Rate limit exceeded: 20 req/min"}
# Status: 429 Too Many Requests
# Header: Retry-After: 60
```

### Exercise 4.4: Cost guard implementation

**Approach** (từ `04-api-gateway/production/cost_guard.py`):

- **In-memory per-day tracking**: Mỗi `UsageRecord` track `input_tokens`, `output_tokens`, `request_count` theo ngày (`YYYY-MM-DD`)
- **Hai tầng budget**: Per-user `$1.0/ngày` + global `$10.0/ngày`. Tầng global ngăn 1 user phá budget toàn service
- **Auto-reset**: So sánh `record.day != today` → tạo record mới tự động đầu mỗi ngày
- **Warning threshold**: Log cảnh báo khi user dùng ≥80% budget
- **HTTP status codes**: `402 Payment Required` (per-user vượt limit) vs `503 Service Unavailable` (global budget cạn)

```python
# Pricing model (GPT-4o-mini)
PRICE_PER_1K_INPUT_TOKENS  = 0.00015   # $0.15/1M input tokens
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006    # $0.60/1M output tokens

cost_guard.check_budget(user_id)                                          # kiểm tra trước LLM
cost_guard.record_usage(user_id, input_tokens=100, output_tokens=50)      # ghi sau LLM trả về
```

**Hạn chế in-memory:** restart container mất counters; scale nhiều instances thì mỗi instance đếm riêng → trong production thực tế cần dùng Redis.

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks

**Liveness probe — `GET /health`** (luôn trả 200 nếu process còn sống):
```python
@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": settings.app_version,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

**Readiness probe — `GET /ready`** (503 trong lúc startup, 200 sau khi sẵn sàng):
```python
@app.get("/ready")
def ready():
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    return {"ready": True}
```

### Exercise 5.2: Graceful shutdown

```python
def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))

signal.signal(signal.SIGTERM, _handle_signal)
# uvicorn: timeout_graceful_shutdown=30 giây
```

Khi SIGTERM đến: uvicorn ngừng nhận request mới → đợi requests hiện tại hoàn thành (tối đa 30s) → exit clean, không drop request nào.

### Exercise 5.3: Stateless design

**Anti-pattern:**
```python
conversation_history = {}   # mỗi instance có memory riêng → mất khi scale ra
```

**Correct:**
```python
# State lưu trong Redis, shared giữa tất cả instances
history = r.lrange(f"history:{user_id}", 0, -1)
r.rpush(f"history:{user_id}", new_message)
```

### Exercise 5.4: Load balancing

```bash
docker compose up --scale agent=3
# 3 instances chạy song song, Docker Compose DNS round-robin phân tán requests
# 1 instance fail → traffic tự chuyển sang 2 instances còn lại
```

### Exercise 5.5: Test stateless

Khi scale 3 instances và kill 1 instance ngẫu nhiên, conversation history vẫn còn vì được lưu trong Redis — không phải in-memory của instance bị kill.
