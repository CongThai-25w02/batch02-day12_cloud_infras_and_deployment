# ============================================================
# Day 10 Data Pipeline API — Multi-stage, non-root
# ============================================================

FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-api.txt .
RUN pip install --no-cache-dir --user -r requirements-api.txt


FROM python:3.11-slim AS runtime

RUN groupadd -r pipeline && useradd -r -g pipeline -d /app pipeline

WORKDIR /app

COPY --from=builder /root/.local /home/pipeline/.local

COPY api.py .
COPY start.py .
COPY transform/ ./transform/
COPY quality/ ./quality/
COPY monitoring/ ./monitoring/
COPY contracts/ ./contracts/
COPY data/ ./data/
COPY .env.example ./.env.example

RUN mkdir -p artifacts/cleaned artifacts/quarantine artifacts/manifests artifacts/logs \
    && chown -R pipeline:pipeline /app

USER pipeline

ENV PATH=/home/pipeline/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUSERBASE=/home/pipeline/.local
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "start.py"]
