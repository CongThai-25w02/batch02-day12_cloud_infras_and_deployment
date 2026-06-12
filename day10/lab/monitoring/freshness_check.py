"""
Kiểm tra freshness từ manifest pipeline (SLA đơn giản theo giờ).

Sinh viên mở rộng: đọc watermark DB, so sánh với clock batch, v.v.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple


def parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        # Cho phép "2026-04-10T08:00:00" không có timezone và một số timestamp raw có dấu "/".
        ts = ts.replace("/", "-")
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _evaluate_freshness(
    *,
    ts_raw: Any,
    sla_hours: float,
    now: datetime,
    boundary: str,
) -> Tuple[str, Dict[str, Any]]:
    dt = parse_iso(str(ts_raw)) if ts_raw else None
    if dt is None:
        return "WARN", {"reason": f"no_timestamp_in_{boundary}", boundary: boundary}

    age_hours = (now - dt).total_seconds() / 3600.0
    detail = {
        boundary: ts_raw,
        "age_hours": round(age_hours, 3),
        "sla_hours": sla_hours,
        "boundary": boundary,
    }
    if age_hours <= sla_hours:
        return "PASS", detail
    return "FAIL", {**detail, "reason": "freshness_sla_exceeded"}


def check_rows_freshness(
    rows: list[dict],
    *,
    sla_hours: float = 24.0,
    now: datetime | None = None,
    boundary: str = "ingest",
) -> Tuple[str, Dict[str, Any]]:
    """Check freshness directly from row timestamps at the ingest boundary."""
    now = now or datetime.now(timezone.utc)
    if not rows:
        return "WARN", {"reason": f"no_rows_for_{boundary}", "boundary": boundary}

    ts_values = [r.get("exported_at") for r in rows if r.get("exported_at")]
    if not ts_values:
        return "WARN", {"reason": f"no_exported_at_for_{boundary}", "boundary": boundary}

    latest_ts = max(ts_values)
    status, detail = _evaluate_freshness(ts_raw=latest_ts, sla_hours=sla_hours, now=now, boundary=boundary)
    detail["latest_exported_at"] = latest_ts
    return status, detail


def check_manifest_freshness(
    manifest_path: Path,
    *,
    sla_hours: float = 24.0,
    now: datetime | None = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Trả về ("PASS" | "WARN" | "FAIL", detail dict).

    Đọc trường `latest_exported_at` hoặc max exported_at trong cleaned summary.
    """
    now = now or datetime.now(timezone.utc)
    if not manifest_path.is_file():
        return "FAIL", {"reason": "manifest_missing", "path": str(manifest_path)}

    data: Dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    ts_raw = data.get("latest_exported_at") or data.get("run_timestamp")
    status, detail = _evaluate_freshness(ts_raw=ts_raw, sla_hours=sla_hours, now=now, boundary="publish")
    if status == "WARN":
        return "WARN", {"reason": "no_timestamp_in_manifest", "manifest": data}
    detail["latest_exported_at"] = ts_raw
    return status, detail
