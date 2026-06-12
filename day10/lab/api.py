"""
Day 10 Data Pipeline API — FastAPI wrapper for the ETL pipeline.

Endpoints:
  GET  /                        - service info
  GET  /health                  - liveness probe
  GET  /ready                   - readiness probe
  POST /pipeline/run            - trigger a pipeline run (no embed)
  GET  /pipeline/manifests      - list recent manifests
  GET  /pipeline/manifests/{id} - get a specific manifest
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from transform.cleaning_rules import clean_rows, load_raw_csv, write_cleaned_csv, write_quarantine_csv
from quality.expectations import run_expectations
from quality.validation import validate_cleaned_rows
from monitoring.freshness_check import check_rows_freshness, check_manifest_freshness

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent
RAW_DEFAULT = ROOT / "data" / "raw" / "policy_export_dirty.csv"
ART = ROOT / "artifacts"
LOG_DIR = ART / "logs"
MAN_DIR = ART / "manifests"
QUAR_DIR = ART / "quarantine"
CLEAN_DIR = ART / "cleaned"

for _p in (LOG_DIR, MAN_DIR, QUAR_DIR, CLEAN_DIR):
    _p.mkdir(parents=True, exist_ok=True)

START_TIME = time.time()
_is_ready = True


app = FastAPI(
    title="Day 10 Data Pipeline API",
    version="1.0.0",
    description="ETL pipeline: ingest → clean → validate → quality checks",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ─── Models ───────────────────────────────────────────────────────────────────

class PipelineRunRequest(BaseModel):
    run_id: str | None = None
    apply_refund_fix: bool = True
    skip_validate: bool = False


class PipelineRunResponse(BaseModel):
    run_id: str
    status: str
    raw_records: int
    cleaned_records: int
    quarantine_records: int
    validation_passed: bool
    expectations_passed: int
    expectations_failed: int
    manifest_path: str
    duration_ms: float


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
def root():
    return {
        "service": "Day 10 Data Pipeline API",
        "version": "1.0.0",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "endpoints": {
            "run pipeline": "POST /pipeline/run",
            "list manifests": "GET /pipeline/manifests",
            "health": "GET /health",
        },
    }


@app.get("/health", tags=["Operations"])
def health():
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    return {"ready": True}


@app.post("/pipeline/run", response_model=PipelineRunResponse, tags=["Pipeline"])
def run_pipeline(req: PipelineRunRequest):
    t0 = time.time()
    run_id = req.run_id or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%MZ")

    if not RAW_DEFAULT.is_file():
        raise HTTPException(404, f"Raw file not found: {RAW_DEFAULT}")

    rows = load_raw_csv(RAW_DEFAULT)
    raw_count = len(rows)

    cleaned, quarantine = clean_rows(rows, apply_refund_window_fix=req.apply_refund_fix)

    rid_safe = run_id.replace(":", "-")
    cleaned_path = CLEAN_DIR / f"cleaned_{rid_safe}.csv"
    quar_path = QUAR_DIR / f"quarantine_{rid_safe}.csv"
    write_cleaned_csv(cleaned_path, cleaned)
    write_quarantine_csv(quar_path, quarantine)

    validated_cleaned, val_detail = validate_cleaned_rows(cleaned)
    val_passed = val_detail["passed"]

    if not val_passed and not req.skip_validate:
        raise HTTPException(422, f"Pydantic validation failed: {val_detail}")

    cleaned = validated_cleaned
    exp_results, halt = run_expectations(cleaned)
    exp_passed = sum(1 for r in exp_results if r.passed)
    exp_failed = sum(1 for r in exp_results if not r.passed)

    if halt and not req.skip_validate:
        raise HTTPException(422, f"Expectation suite failed: {[r.detail for r in exp_results if not r.passed]}")

    latest_exported = max((r.get("exported_at") or "" for r in cleaned), default="")
    manifest = {
        "run_id": run_id,
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_records": raw_count,
        "cleaned_records": len(cleaned),
        "quarantine_records": len(quarantine),
        "latest_exported_at": latest_exported,
        "validation_passed": val_passed,
        "expectations_passed": exp_passed,
        "expectations_failed": exp_failed,
        "cleaned_csv": str(cleaned_path.relative_to(ROOT)),
    }
    man_path = MAN_DIR / f"manifest_{rid_safe}.json"
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return PipelineRunResponse(
        run_id=run_id,
        status="ok",
        raw_records=raw_count,
        cleaned_records=len(cleaned),
        quarantine_records=len(quarantine),
        validation_passed=val_passed,
        expectations_passed=exp_passed,
        expectations_failed=exp_failed,
        manifest_path=str(man_path.relative_to(ROOT)),
        duration_ms=round((time.time() - t0) * 1000, 1),
    )


@app.get("/pipeline/manifests", tags=["Pipeline"])
def list_manifests(limit: int = 10):
    files = sorted(MAN_DIR.glob("manifest_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    results = []
    for f in files[:limit]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            results.append(data)
        except Exception:
            continue
    return {"manifests": results, "total": len(results)}


@app.get("/pipeline/manifests/{run_id}", tags=["Pipeline"])
def get_manifest(run_id: str):
    rid_safe = run_id.replace(":", "-")
    man_path = MAN_DIR / f"manifest_{rid_safe}.json"
    if not man_path.is_file():
        raise HTTPException(404, f"Manifest not found: {run_id}")
    return json.loads(man_path.read_text(encoding="utf-8"))
