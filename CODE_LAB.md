#  Code Lab: Deploy Your AI Agent to Production

> **AICB-P1 · VinUniversity 2026**  
> Thời gian: 3-4 giờ | Độ khó: Intermediate

##  Mục Tiêu

Sau khi hoàn thành lab này, bạn sẽ:
- Hiểu sự khác biệt giữa development và production
- Containerize một AI agent với Docker
- Deploy agent lên cloud platform
- Bảo mật API với authentication và rate limiting
- Thiết kế hệ thống có khả năng scale và reliable

---

##  Yêu Cầu

```bash
 Python 3.11+
 Docker & Docker Compose
 Git
 Text editor (VS Code khuyến nghị)
 Terminal/Command line
```

**Không cần:**
-  OpenAI API key (dùng mock LLM)
-  Credit card
-  Kinh nghiệm DevOps trước đó

---

##  Lộ Trình Lab

| Phần | Thời gian | Nội dung |
|------|-----------|----------|
| **Part 1** | 30 phút | Localhost vs Production |
| **Part 2** | 45 phút | Docker Containerization |
| **Part 3** | 45 phút | Cloud Deployment |
| **Part 4** | 40 phút | API Security |
| **Part 5** | 40 phút | Scaling & Reliability |
| **Part 6** | 60 phút | Final Project |
| **Part 7** | 40 phút | Data Pipeline & Observability (Day 10) |

---

## Part 1: Localhost vs Production (30 phút)

###  Concepts

**Vấn đề:** "It works on my machine" — code chạy tốt trên laptop nhưng fail khi deploy.

**Nguyên nhân:**
- Hardcoded secrets
- Khác biệt về environment (Python version, OS, dependencies)
- Không có health checks
- Config không linh hoạt

**Giải pháp:** 12-Factor App principles

###  Exercise 1.1: Phát hiện anti-patterns

```bash
cd 01-localhost-vs-production/develop
```

**Nhiệm vụ:** Đọc `app.py` và tìm ít nhất 5 vấn đề.

<details>
<summary> Gợi ý</summary>

Tìm:
- API key hardcode
- Port cố định
- Debug mode
- Không có health check
- Không xử lý shutdown

</details>



###  Exercise 1.2: Chạy basic version

```bash
pip install -r requirements.txt
python app.py
```

Test:
```bash
curl -X POST "http://localhost:8000/ask?question=hello"
```

**Quan sát:** Nó chạy! Nhưng có production-ready không?

###  Exercise 1.3: So sánh với advanced version

```bash
cd ../production
cp .env.example .env
pip install -r requirements.txt
python app.py
```

**Nhiệm vụ:** So sánh 2 files `app.py`. Điền vào bảng:

| Feature | Basic | Advanced | Tại sao quan trọng? |
|---------|-------|----------|---------------------|
| Config | Hardcode | Env vars | ... |
| Health check |  |  | ... |
| Logging | print() | JSON | ... |
| Shutdown | Đột ngột | Graceful | ... |

###  Checkpoint 1

- [ ] Hiểu tại sao hardcode secrets là nguy hiểm
- [ ] Biết cách dùng environment variables
- [ ] Hiểu vai trò của health check endpoint
- [ ] Biết graceful shutdown là gì

---

## Part 2: Docker Containerization (45 phút)

###  Concepts

**Vấn đề:** "Works on my machine" part 2 — Python version khác, dependencies conflict.

**Giải pháp:** Docker — đóng gói app + dependencies vào container.

**Benefits:**
- Consistent environment
- Dễ deploy
- Isolation
- Reproducible builds

###  Exercise 2.1: Dockerfile cơ bản

```bash
cd ../../02-docker/develop
```

**Nhiệm vụ:** Đọc `Dockerfile` và trả lời:

1. Base image là gì?
2. Working directory là gì?
3. Tại sao COPY requirements.txt trước?
4. CMD vs ENTRYPOINT khác nhau thế nào?

###  Exercise 2.2: Build và run

```bash
# Quay về project root trước khi build
cd ../../

# Build image (build context là project root)
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .

# Run container
docker run -p 8000:8000 my-agent:develop

# Test
curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Docker?"}'
```

**Quan sát:** Image size là bao nhiêu?
```bash
docker images my-agent:develop
```

###  Exercise 2.3: Multi-stage build

```bash
cd 02-docker/production
```

> Windows PowerShell note: nếu đang dùng PowerShell, bạn có thể chạy `cd .\02-docker\production`.

**Nhiệm vụ:** Đọc `Dockerfile` và tìm:
- Stage 1 làm gì?
- Stage 2 làm gì?
- Tại sao image nhỏ hơn?

Build và so sánh (chạy từ project root):
```bash
# Quay về project root nếu chưa ở đó
cd ../../

docker build -f 02-docker/production/Dockerfile -t my-agent:advanced .
# Linux/macOS:
# docker images | grep my-agent
# Windows PowerShell:
# docker images | Select-String my-agent
```

> Windows note: If you are using PowerShell and the `docker images | grep ...` command fails, use `Select-String` instead.

###  Exercise 2.4: Docker Compose stack

**Nhiệm vụ:** Đọc `docker-compose.yml` và vẽ architecture diagram.

```bash
# Chạy từ thư mục 02-docker/production
cd 02-docker/production
docker compose up
```

Services nào được start? Chúng communicate thế nào?

Test:
```bash
# Health check
curl http://localhost/health

# Agent endpoint
curl http://localhost/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain microservices"}'
```

###  Checkpoint 2

- [ ] Hiểu cấu trúc Dockerfile
- [ ] Biết lợi ích của multi-stage builds
- [ ] Hiểu Docker Compose orchestration
- [ ] Biết cách debug container (`docker logs`, `docker exec`)

---

## Part 3: Cloud Deployment (45 phút)

###  Concepts

**Vấn đề:** Laptop không thể chạy 24/7, không có public IP.

**Giải pháp:** Cloud platforms — Railway, Render, GCP Cloud Run.

**So sánh:**

| Platform | Độ khó | Free tier | Best for |
|----------|--------|-----------|----------|
| Railway | ⭐ | $5 credit | Prototypes |
| Render | ⭐⭐ | 750h/month | Side projects |
| Cloud Run | ⭐⭐⭐ | 2M requests | Production |

###  Exercise 3.1: Deploy Railway (15 phút)

```bash
cd ../../03-cloud-deployment/railway
```

**Steps:**

1. Install Railway CLI:
```bash
npm i -g @railway/cli
```

2. Login:
```bash
railway login
```

3. Initialize project:
```bash
railway init
```

4. Set environment variables:
```bash
railway variables set PORT=8000
railway variables set AGENT_API_KEY=my-secret-key
```

5. Deploy:
```bash
railway up
```

6. Get public URL:
```bash
railway domain
```

**Nhiệm vụ:** Test public URL với curl hoặc Postman.

> Windows PowerShell note: `curl` là alias của `Invoke-WebRequest` trên PowerShell. Để dùng GNU curl, install qua `scoop install curl` hoặc dùng `Invoke-WebRequest` trực tiếp.

Test:
```bash
# Health check
curl http://student-agent-domain/health

# Agent endpoint
curl http://student-agent-domain/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": ""}'
```

Windows PowerShell alternative (dùng `Invoke-WebRequest`):
```powershell
# Health check
Invoke-WebRequest -Uri "http://student-agent-domain/health"

# Agent endpoint
Invoke-WebRequest -Uri "http://student-agent-domain/ask" -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"question": ""}'
```

###  Exercise 3.2: Deploy Render (15 phút)

```bash
cd ../render
```

**Steps:**

1. Push code lên GitHub (nếu chưa có)
2. Vào [render.com](https://render.com) → Sign up
3. New → Blueprint
4. Connect GitHub repo
5. Render tự động đọc `render.yaml`
6. Set environment variables trong dashboard
7. Deploy!

> Windows note: để push code lên GitHub từ PowerShell, sử dụng Git CLI hoặc `git` command (nếu đã cài Git for Windows). Hoặc dùng GitHub Desktop GUI. Các bước 3–7 đều làm trên browser, nên không khác biệt OS.

**Nhiệm vụ:** So sánh `render.yaml` với `railway.toml`. Khác nhau gì?

###  Exercise 3.3: (Optional) GCP Cloud Run (15 phút)

```bash
cd ../production-cloud-run
```

**Yêu cầu:** GCP account (có free tier).

**Nhiệm vụ:** Đọc `cloudbuild.yaml` và `service.yaml`. Hiểu CI/CD pipeline.

###  Checkpoint 3

- [ ] Deploy thành công lên ít nhất 1 platform
- [ ] Có public URL hoạt động
- [ ] Hiểu cách set environment variables trên cloud
- [ ] Biết cách xem logs

---

## Part 4: API Security (40 phút)

###  Concepts

**Vấn đề:** Public URL = ai cũng gọi được = hết tiền OpenAI.

**Giải pháp:**
1. **Authentication** — Chỉ user hợp lệ mới gọi được
2. **Rate Limiting** — Giới hạn số request/phút
3. **Cost Guard** — Dừng khi vượt budget

###  Exercise 4.1: API Key authentication

```bash
cd ../../04-api-gateway/develop
```

**Nhiệm vụ:** Đọc `app.py` và tìm:
- API key được check ở đâu?
- Điều gì xảy ra nếu sai key?
- Làm sao rotate key?

Test:
```bash
python app.py

#  Không có key
curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'

#  Có key
curl http://localhost:8000/ask -X POST \
  -H "X-API-Key: secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
```

###  Exercise 4.2: JWT authentication (Advanced)

```bash
cd ../production
```

**Nhiệm vụ:** 
1. Đọc `auth.py` — hiểu JWT flow
2. Lấy token:
```bash
python app.py

curl http://localhost:8000/token -X POST \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secret"}'
```

3. Dùng token để gọi API:

**Linux/macOS:**
```bash
TOKEN="<token_từ_bước_2>"
curl http://localhost:8000/ask -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain JWT"}'
```

**Windows PowerShell:**
```powershell
$TOKEN="<token_từ_bước_2>"
Invoke-WebRequest -Uri "http://localhost:8000/ask" -Method POST `
  -Headers @{"Authorization"="Bearer $TOKEN"; "Content-Type"="application/json"} `
  -Body '{"question": "Explain JWT"}'
```

###  Exercise 4.3: Rate limiting

**Nhiệm vụ:** Đọc `rate_limiter.py` và trả lời:
- Algorithm nào được dùng? (Token bucket? Sliding window?)
- Limit là bao nhiêu requests/minute?
- Làm sao bypass limit cho admin?

Test:
```bash
# Linux/macOS:
for i in {1..20}; do
  curl http://localhost:8000/ask -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"question": "Test '$i'"}'
  echo ""
done
```

> **Windows PowerShell alternative:**
> ```powershell
> for ($i=1; $i -le 20; $i++) {
>   Invoke-WebRequest -Uri "http://localhost:8000/ask" -Method POST `
>     -Headers @{"Authorization"="Bearer $TOKEN"; "Content-Type"="application/json"} `
>     -Body "{`"question`": `"Test $i`"}"
>   Write-Host ""
> }
> ```

Quan sát response khi hit limit.

###  Exercise 4.4: Cost guard

**Nhiệm vụ:** Đọc `cost_guard.py` và implement logic:

```python
def check_budget(user_id: str, estimated_cost: float) -> bool:
    """
    Return True nếu còn budget, False nếu vượt.
    
    Logic:
    - Mỗi user có budget $10/tháng
    - Track spending trong Redis
    - Reset đầu tháng
    """
    # TODO: Implement
    pass
```

<details>
<summary> Solution</summary>

```python
import redis
from datetime import datetime

r = redis.Redis()

def check_budget(user_id: str, estimated_cost: float) -> bool:
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    
    current = float(r.get(key) or 0)
    if current + estimated_cost > 10:
        return False
    
    r.incrbyfloat(key, estimated_cost)
    r.expire(key, 32 * 24 * 3600)  # 32 days
    return True
```

</details>

###  Checkpoint 4

- [ ] Implement API key authentication
- [ ] Hiểu JWT flow
- [ ] Implement rate limiting
- [ ] Implement cost guard với Redis

---

## Part 5: Scaling & Reliability (40 phút)

###  Concepts

**Vấn đề:** 1 instance không đủ khi có nhiều users.

**Giải pháp:**
1. **Stateless design** — Không lưu state trong memory
2. **Health checks** — Platform biết khi nào restart
3. **Graceful shutdown** — Hoàn thành requests trước khi tắt
4. **Load balancing** — Phân tán traffic

###  Exercise 5.1: Health checks

```bash
cd ../../05-scaling-reliability/develop
```

**Nhiệm vụ:** Implement 2 endpoints:

```python
@app.get("/health")
def health():
    """Liveness probe — container còn sống không?"""
    # TODO: Return 200 nếu process OK
    pass

@app.get("/ready")
def ready():
    """Readiness probe — sẵn sàng nhận traffic không?"""
    # TODO: Check database connection, Redis, etc.
    # Return 200 nếu OK, 503 nếu chưa ready
    pass
```

<details>
<summary> Solution</summary>

```python
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    try:
        # Check Redis
        r.ping()
        # Check database
        db.execute("SELECT 1")
        return {"status": "ready"}
    except:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready"}
        )
```

</details>

###  Exercise 5.2: Graceful shutdown

**Nhiệm vụ:** Implement signal handler:

```python
import signal
import sys

def shutdown_handler(signum, frame):
    """Handle SIGTERM from container orchestrator"""
    # TODO:
    # 1. Stop accepting new requests
    # 2. Finish current requests
    # 3. Close connections
    # 4. Exit
    pass

signal.signal(signal.SIGTERM, shutdown_handler)
```

Test:
```bash
# Linux/macOS:
python app.py &
PID=$!

# Gửi request
curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Long task"}' &

# Ngay lập tức kill
kill -TERM $PID

# Quan sát: Request có hoàn thành không?
```

> **Windows PowerShell:**
> ```powershell
> # Start app in background
> $proc = Start-Process -FilePath "python" -ArgumentList "app.py" -PassThru
> Start-Sleep -Seconds 2
> 
> # Send request in background
> $reqJob = Start-Job -ScriptBlock {
>   Invoke-WebRequest -Uri "http://localhost:8000/ask" -Method POST `
>     -Headers @{"Content-Type"="application/json"} `
>     -Body '{"question": "Long task"}'
> }
> 
> # Kill process immediately
> Stop-Process -Id $proc.Id -Force
> 
> # Check if request completed
> Receive-Job -Job $reqJob
> ```

###  Exercise 5.3: Stateless design

```bash
cd ../production
```

**Nhiệm vụ:** Refactor code để stateless.

**Anti-pattern:**
```python
#  State trong memory
conversation_history = {}

@app.post("/ask")
def ask(user_id: str, question: str):
    history = conversation_history.get(user_id, [])
    # ...
```

**Correct:**
```python
#  State trong Redis
@app.post("/ask")
def ask(user_id: str, question: str):
    history = r.lrange(f"history:{user_id}", 0, -1)
    # ...
```

Tại sao? Vì khi scale ra nhiều instances, mỗi instance có memory riêng.

###  Exercise 5.4: Load balancing

**Nhiệm vụ:** Chạy stack với Nginx load balancer:

```bash
docker compose up --scale agent=3
```

Quan sát:
- 3 agent instances được start
- Nginx phân tán requests
- Nếu 1 instance die, traffic chuyển sang instances khác

Test:
```bash
# Linux/macOS:
# Gọi 10 requests
for i in {1..10}; do
  curl http://localhost/ask -X POST \
    -H "Content-Type: application/json" \
    -d '{"question": "Request '$i'"}'
done

# Check logs — requests được phân tán
docker compose logs agent
```

> **Windows PowerShell:**
> ```powershell
> # Call 10 requests
> for ($i=1; $i -le 10; $i++) {
>   Invoke-WebRequest -Uri "http://localhost/ask" -Method POST `
>     -Headers @{"Content-Type"="application/json"} `
>     -Body "{`"question`": `"Request $i`"}"
> }
> 
> # Check logs
> docker compose logs agent | Select-String "Request"
> ```

###  Exercise 5.5: Test stateless

```bash
python test_stateless.py
```

Script này:
1. Gọi API để tạo conversation
2. Kill random instance
3. Gọi tiếp — conversation vẫn còn không?

###  Checkpoint 5

- [ ] Implement health và readiness checks
- [ ] Implement graceful shutdown
- [ ] Refactor code thành stateless
- [ ] Hiểu load balancing với Nginx
- [ ] Test stateless design

---

## Part 6: Final Project (60 phút)

###  Objective

Build một production-ready AI agent từ đầu, kết hợp TẤT CẢ concepts đã học.

###  Requirements

**Functional:**
- [ ] Agent trả lời câu hỏi qua REST API
- [ ] Support conversation history
- [ ] Streaming responses (optional)

**Non-functional:**
- [ ] Dockerized với multi-stage build
- [ ] Config từ environment variables
- [ ] API key authentication
- [ ] Rate limiting (10 req/min per user)
- [ ] Cost guard ($10/month per user)
- [ ] Health check endpoint
- [ ] Readiness check endpoint
- [ ] Graceful shutdown
- [ ] Stateless design (state trong Redis)
- [ ] Structured JSON logging
- [ ] Deploy lên Railway hoặc Render
- [ ] Public URL hoạt động

### 🏗 Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Nginx (LB)     │
└──────┬──────────┘
       │
       ├─────────┬─────────┐
       ▼         ▼         ▼
   ┌──────┐  ┌──────┐  ┌──────┐
   │Agent1│  │Agent2│  │Agent3│
   └───┬──┘  └───┬──┘  └───┬──┘
       │         │         │
       └─────────┴─────────┘
                 │
                 ▼
           ┌──────────┐
           │  Redis   │
           └──────────┘
```

###  Step-by-step

#### Step 1: Project setup (5 phút)

```bash
mkdir my-production-agent
cd my-production-agent

# Tạo structure
mkdir -p app
touch app/__init__.py
touch app/main.py
touch app/config.py
touch app/auth.py
touch app/rate_limiter.py
touch app/cost_guard.py
touch Dockerfile
touch docker-compose.yml
touch requirements.txt
touch .env.example
touch .dockerignore
```

#### Step 2: Config management (10 phút)

**File:** `app/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # TODO: Define all config
    # - PORT
    # - REDIS_URL
    # - AGENT_API_KEY
    # - LOG_LEVEL
    # - RATE_LIMIT_PER_MINUTE
    # - MONTHLY_BUDGET_USD
    pass

settings = Settings()
```

#### Step 3: Main application (15 phút)

**File:** `app/main.py`

```python
from fastapi import FastAPI, Depends, HTTPException
from .config import settings
from .auth import verify_api_key
from .rate_limiter import check_rate_limit
from .cost_guard import check_budget

app = FastAPI()

@app.get("/health")
def health():
    # TODO
    pass

@app.get("/ready")
def ready():
    # TODO: Check Redis connection
    pass

@app.post("/ask")
def ask(
    question: str,
    user_id: str = Depends(verify_api_key),
    _rate_limit: None = Depends(check_rate_limit),
    _budget: None = Depends(check_budget)
):
    # TODO: 
    # 1. Get conversation history from Redis
    # 2. Call LLM
    # 3. Save to Redis
    # 4. Return response
    pass
```

#### Step 4: Authentication (5 phút)

**File:** `app/auth.py`

```python
from fastapi import Header, HTTPException

def verify_api_key(x_api_key: str = Header(...)):
    # TODO: Verify against settings.AGENT_API_KEY
    # Return user_id if valid
    # Raise HTTPException(401) if invalid
    pass
```

#### Step 5: Rate limiting (10 phút)

**File:** `app/rate_limiter.py`

```python
import redis
from fastapi import HTTPException

r = redis.from_url(settings.REDIS_URL)

def check_rate_limit(user_id: str):
    # TODO: Implement sliding window
    # Raise HTTPException(429) if exceeded
    pass
```

#### Step 6: Cost guard (10 phút)

**File:** `app/cost_guard.py`

```python
def check_budget(user_id: str):
    # TODO: Check monthly spending
    # Raise HTTPException(402) if exceeded
    pass
```

#### Step 7: Dockerfile (5 phút)

```dockerfile
# TODO: Multi-stage build
# Stage 1: Builder
# Stage 2: Runtime
```

#### Step 8: Docker Compose (5 phút)

```yaml
# TODO: Define services
# - agent (scale to 3)
# - redis
# - nginx (load balancer)
```

#### Step 9: Test locally (5 phút)

```bash
docker compose up --scale agent=3

# Test all endpoints
curl http://localhost/health
curl http://localhost/ready
curl -H "X-API-Key: secret" http://localhost/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello", "user_id": "user1"}'
```

#### Step 10: Deploy (10 phút)

```bash
# Railway
railway init
railway variables set REDIS_URL=...
railway variables set AGENT_API_KEY=...
railway up

# Hoặc Render
# Push lên GitHub → Connect Render → Deploy
```

###  Validation

Chạy script kiểm tra:

```bash
cd 06-lab-complete
python check_production_ready.py
```

Script sẽ kiểm tra:
-  Dockerfile exists và valid
-  Multi-stage build
-  .dockerignore exists
-  Health endpoint returns 200
-  Readiness endpoint returns 200
-  Auth required (401 without key)
-  Rate limiting works (429 after limit)
-  Cost guard works (402 when exceeded)
-  Graceful shutdown (SIGTERM handled)
-  Stateless (state trong Redis, không trong memory)
-  Structured logging (JSON format)

###  Grading Rubric

| Criteria | Points | Description |
|----------|--------|-------------|
| **Functionality** | 20 | Agent hoạt động đúng |
| **Docker** | 15 | Multi-stage, optimized |
| **Security** | 20 | Auth + rate limit + cost guard |
| **Reliability** | 20 | Health checks + graceful shutdown |
| **Scalability** | 15 | Stateless + load balanced |
| **Deployment** | 10 | Public URL hoạt động |
| **Total** | 100 | |

---

## Part 7: Day 10 — Data Pipeline & Observability (40 phút)

###  Objective

Kết nối project Day 10 vào khóa học: sửa pipeline, clean data, triển khai expectation suite, và tạo bằng chứng before/after để đảm bảo agent Day 09/Final Project có dữ liệu đúng.

###  Why it matters

Day 09 multi-agent và Final Project chỉ có giá trị nếu dữ liệu nền sạch và observable. Day 10 giúp bạn:
- Phát hiện data bug trước khi embed
- Thiết kế quality gate và quarantine  
- Đưa `run_id` / bằng chứng before-after vào quy trình
- Giữ continuity với case CS + IT Helpdesk từ Day 08/09

###  Setup Day 10 project

```bash
cd day10/lab
python -m venv .venv
```

> **Windows PowerShell activation:**
> ```powershell
> & .venv\Scripts\Activate.ps1
> ```
> Or use traditional: `.venv\Scripts\activate`

```bash
pip install -r requirements.txt
```

> Windows note: `cp .env.example .env` không hoạt động. Dùng:
> ```powershell
> Copy-Item .env.example .env
> ```

###  Key steps

**Step 1: Run baseline pipeline**
```bash
python etl_pipeline.py run
```

**Expected output (Windows PowerShell):**
```
PIPELINE_OK
run_id=2026-06-10T09-29Z
raw_records=247
cleaned_records=45
quarantine_records=202
cleaned_csv=artifacts\cleaned\cleaned_2026-06-10T09-29Z.csv
pydantic_validation=PASS
expectation[min_one_row] OK (halt)
expectation[no_empty_doc_id] OK (halt)
expectation[refund_no_stale_14d_window] OK (halt)
expectation[hr_leave_no_stale_10d_annual] OK (halt)
embed_upsert count=45 collection=day10_kb
manifest_written=artifacts\manifests\manifest_2026-06-10T09-29Z.json
```

**Step 2: Modify & extend (2-3 expectations)**

Mở và chỉnh sửa:
- `transform/cleaning_rules.py` — thêm allowlist rules
- `quality/expectations.py` — thêm ít nhất 2 new expectations

Example new expectation:
```python
# quality/expectations.py
@expectation("access_control_role_valid")
def access_control_role_valid(df: DataFrame) -> ExpectationResult:
    """Valid roles: admin, manager, user"""
    valid_roles = {"admin", "manager", "user"}
    invalid = df[~df['role'].isin(valid_roles)]
    return ExpectationResult(
        passed=len(invalid) == 0,
        details={"invalid_roles_count": len(invalid)}
    )
```

**Step 3: Run retrieval evaluation**
```bash
python eval_retrieval.py --out artifacts/eval/eval_after_fix.csv
```

**Step 4: Run grading**
```bash
python grading_run.py --out artifacts/eval/grading_run.jsonl
```

###  Windows-specific: Check artifact files

```powershell
# List cleaned records
Get-ChildItem -Path artifacts/cleaned/ | ForEach-Object { Write-Host $_.Name }

# View manifest
$manifest = Get-ChildItem -Path artifacts/manifests/ -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-Content $manifest.FullName | ConvertFrom-Json | Format-List

# Check quarantine
(Import-Csv artifacts/quarantine/*.csv | Measure-Object).Count
```

###  What to deliver

- [ ] Pipeline chạy thành công (exit 0)
- [ ] Thêm ít nhất 2 expectation mới vào `quality/expectations.py`
- [ ] Có `run_id` và manifest trong `artifacts/manifests/`
- [ ] Báo cáo before/after trong `reports/group_report.md`:
  - Raw records: 247 → Cleaned: 45 (18% quality pass rate)
  - Top violations: [list 5 top reasons in quarantine]
  - Retrieval quality delta: [show eval before/after]

###  Checkpoint 7

- [ ] Chạy Day 10 từ project root: `cd day10\lab` (Windows) hoặc `cd day10/lab` (Mac/Linux)
- [ ] Venv activated: `& .venv\Scripts\Activate.ps1` (Windows)
- [ ] Pipeline OK: `python etl_pipeline.py run` → exit 0
- [ ] Manifest exists: `artifacts/manifests/manifest_*.json`
- [ ] 45+ documents embedded: `chroma_db/day10_kb`
- [ ] Sửa ≥2 expectations, run lại, capture before/after metrics

---

##  Hoàn Thành!

Bạn đã:
-  Hiểu sự khác biệt dev vs production
-  Containerize app với Docker
-  Deploy lên cloud platform
-  Bảo mật API
-  Thiết kế hệ thống scalable và reliable
-  Integrate data pipeline observability (Day 10)

###  Cross-Day Continuity

**Data Flow:**
```
Day 10: ETL Pipeline (clean data)
         ↓
     Chroma DB (vector store)
         ↓
Day 09: Multi-Agent (retrieves cleaned docs)
         ↓
Final Project: Stateless agent (uses clean vectors)
```

**Shared Context (CS + IT Helpdesk):**
- Day 08: Build initial RAG pipeline
- Day 09: Multi-agent supervisor-worker retrieval
- Day 10: Data quality gates & observability ← **YOU ARE HERE**
- Day 12 (Final): Production-ready deployment

**Why Day 10 matters for Final Project:**
- Without clean data → retrieval quality bad
- Without expectations → can't detect regressions
- Without `run_id` → can't trace which data version caused issue
- Without freshness checks → serving stale answers

###  Next Steps

1. **Monitoring:** Thêm Prometheus + Grafana
2. **CI/CD:** GitHub Actions auto-deploy
3. **Advanced scaling:** Kubernetes
4. **Observability:** Distributed tracing với OpenTelemetry
5. **Cost optimization:** Spot instances, auto-scaling

###  Troubleshooting: Windows PowerShell Cheat Sheet

| Task | Command |
|------|---------|
| Change directory | `cd .\path\to\dir` (use `\` backslashes) |
| List files | `Get-ChildItem` or `ls` |
| Filter grep | `Select-String "pattern"` |
| Run venv | `. .venv\Scripts\activate` or `& .venv\Scripts\Activate.ps1` |
| Copy file | `Copy-Item source dest` |
| Make request | `Invoke-WebRequest -Uri ... -Method POST` |
| Check port | `Get-NetTCPConnection -LocalPort 8000` |
| Kill process | `Stop-Process -Name python` |
| Background job | `Start-Job -ScriptBlock { ... }` |
| Loop 1-N | `for ($i=1; $i -le N; $i++) { ... }` |

###  Resources

- [12-Factor App](https://12factor.net/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Railway Docs](https://docs.railway.app/)
- [Render Docs](https://render.com/docs)
- [Great Expectations](https://greatexpectations.io/)
- [Chroma Vector DB](https://docs.trychroma.com/)

---

##  Q&A

**Q: Tôi không có credit card, có thể deploy không?**  
A: Có! Railway cho $5 credit, Render có 750h free tier.

**Q: Mock LLM khác gì với OpenAI thật?**  
A: Mock trả về canned responses, không gọi API. Để dùng OpenAI thật, set `OPENAI_API_KEY` trong env.

**Q: Làm sao debug khi container fail?**  
A: `docker logs <container_id>` hoặc `docker exec -it <container_id> /bin/sh`

**Q: Redis data mất khi restart?**  
A: Dùng volume: `volumes: - redis-data:/data` trong docker-compose.

**Q: Làm sao scale trên Railway/Render?**  
A: Railway: `railway scale <replicas>`. Render: Dashboard → Settings → Instances.

**Q: Day 10 pipeline không chạy, lỗi gì?**  
A: Kiểm tra:
1. Virtual env activated: `& .venv\Scripts\Activate.ps1`
2. Requirements installed: `pip list | Select-String "chromadb"`
3. .env file exists: `Test-Path .env`
4. Log file: `Get-Content artifacts/logs/run_*.log -Tail 50`

**Q: Làm sao xem quarantine records?**  
A: `Import-Csv artifacts/quarantine/*.csv | Format-Table -AutoSize`

**Q: Chạy Part 1-6 rồi, giờ làm gì?**  
A: Tiếp tục Part 7 (Day 10) để ensure data quality, sau đó combine tất cả vào Final Project trên cloud.

---

**Happy Deploying! 🚀**
