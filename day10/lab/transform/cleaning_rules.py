"""
Cleaning rules — raw export → cleaned rows + quarantine.

Baseline gồm các failure mode mở rộng (allowlist doc_id, parse ngày, HR stale version).
Sinh viên thêm ≥3 rule mới: mỗi rule phải ghi `metric_impact` (xem README — chống trivial).
"""

from __future__ import annotations

import csv
import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from functools import lru_cache
from typing import Any, Dict, List, Tuple

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "data_contract.yaml"


@lru_cache(maxsize=1)
def _load_contract() -> Dict[str, Any]:
    if not CONTRACT_PATH.is_file():
        return {}
    with CONTRACT_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _allowed_doc_ids() -> frozenset[str]:
    contract = _load_contract()
    values = set(contract.get("allowed_doc_ids") or [])
    if not values:
        values.update(
            {
                "policy_refund_v4",
                "sla_p1_2026",
                "it_helpdesk_faq",
                "hr_leave_policy",
                "access_control_sop",
            }
        )
    extra = os.environ.get("EXTRA_ALLOWED_DOC_IDS", "")
    if extra.strip():
        values.update({item.strip() for item in extra.split(",") if item.strip()})
    return frozenset(values)


def _hr_leave_cutoff() -> str:
    env_value = os.environ.get("HR_LEAVE_MIN_EFFECTIVE_DATE", "").strip()
    if env_value:
        return env_value
    contract = _load_contract()
    return (
        contract.get("policy_versioning", {}).get("hr_leave_min_effective_date")
        or "2026-01-01"
    )


def _normalize_exported_at(raw: str) -> str:
    """Rule: canonicalize exported_at để freshness check có timestamp thật."""
    s = (raw or "").strip()
    if not s:
        return ""
    candidate = s.replace("/", "-")
    if candidate.endswith("Z"):
        candidate = candidate.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


ALLOWED_DOC_IDS = _allowed_doc_ids()

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DMY_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _strip_uncertain_prefix(text: str) -> str:
    """Rule: loại bỏ tiền tố mơ hồ để canonical text ổn định hơn."""
    cleaned = re.sub(r"^\s*Nội dung không rõ ràng:\s*", "", (text or "").strip())
    return " ".join(cleaned.split())


def _strip_leading_emphasis(text: str) -> str:
    """Rule: bỏ prefix nhấn mạnh như !!! để tránh tạo vector khác nhau cho cùng nội dung."""
    cleaned = re.sub(r"^\s*[!！]{2,}\s*", "", (text or "").strip())
    return " ".join(cleaned.split())


def _strip_noise_annotations(text: str) -> str:
    """Rule: bỏ annotation nhiễu từ export như Chú ý / Nội dung có thể bị trùng."""
    fixed = re.sub(
        r"\s*Chú ý:\s*effective_date không đồng nhất giữa các nguồn\.?",
        "",
        (text or ""),
        flags=re.IGNORECASE,
    )
    fixed = re.sub(
        r"\s*Nội dung có thể bị trùng do sync lại dữ liệu\.?",
        "",
        fixed,
        flags=re.IGNORECASE,
    )
    return " ".join(fixed.split())


def _collapse_repeated_sentences(text: str) -> str:
    """Rule: collapse các câu bị lặp liên tiếp trong cùng chunk."""
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if p.strip()]
    if not parts:
        return ""
    collapsed: List[str] = []
    for part in parts:
        if not collapsed or part != collapsed[-1]:
            collapsed.append(part)
    return " ".join(collapsed)


def _normalize_hr_leave_version(text: str, eff_norm: str) -> str:
    """
    Rule: đồng bộ bản HR 2026 theo cutoff từ contract/env,
    để chunk cũ 10 ngày không còn làm lệch retrieval.
    """
    cutoff = _hr_leave_cutoff()
    if not eff_norm or eff_norm < cutoff:
        return text

    fixed = text
    fixed = _strip_uncertain_prefix(fixed)
    fixed = _collapse_repeated_sentences(fixed)
    fixed = re.sub(
        r"\b10 ngày(?: làm việc)? phép năm\b",
        "12 ngày phép năm theo chính sách 2026",
        fixed,
        flags=re.IGNORECASE,
    )
    fixed = re.sub(
        r"\bbản HR 2025\b",
        "theo chính sách 2026",
        fixed,
        flags=re.IGNORECASE,
    )
    fixed = re.sub(
        r"\b10 ngày(?: làm việc)?\s*/?\s*năm\b",
        "12 ngày/năm",
        fixed,
        flags=re.IGNORECASE,
    )
    fixed = " ".join(fixed.split())
    return fixed


def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    h = hashlib.sha256(f"{doc_id}|{chunk_text}|{seq}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{seq}_{h}"


def _normalize_effective_date(raw: str) -> Tuple[str, str]:
    """
    Trả về (iso_date, error_reason).
    iso_date rỗng nếu không parse được.
    """
    s = (raw or "").strip()
    if not s:
        return "", "empty_effective_date"
    if _ISO_DATE.match(s):
        return s, ""
    m = _DMY_SLASH.match(s)
    if m:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        return f"{yyyy}-{mm}-{dd}", ""
    return "", "invalid_effective_date_format"


def load_raw_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k: (v or "").strip() for k, v in r.items()})
    return rows


def clean_rows(
    rows: List[Dict[str, str]],
    *,
    apply_refund_window_fix: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Trả về (cleaned, quarantine).

    Baseline (mở rộng theo narrative Day 10):
    1) Quarantine: doc_id không thuộc allowlist (export lạ / catalog sai).
    2) Chuẩn hoá effective_date sang YYYY-MM-DD; quarantine nếu không parse được.
    3) Quarantine: chunk hr_leave_policy có effective_date < 2026-01-01 (bản HR cũ / conflict version).
    4) Quarantine: chunk_text rỗng hoặc effective_date rỗng sau chuẩn hoá.
    5) Loại trùng nội dung chunk_text (giữ bản đầu).
    6) Fix stale refund: policy_refund_v4 chứa '14 ngày làm việc' → 7 ngày.
    7) Canonicalize HR 2026 text dựa trên cutoff từ contract/env để loại bản 10 ngày còn sót.
    8) Strip prefix "Nội dung không rõ ràng:" và collapse câu lặp liên tiếp để vector index ổn định.
    9) Strip prefix nhấn mạnh "!!!" và annotation nhiễu từ raw export.
    """
    quarantine: List[Dict[str, Any]] = []
    seen_text: set[str] = set()
    cleaned: List[Dict[str, Any]] = []
    seq = 0

    for raw in rows:
        doc_id = raw.get("doc_id", "")
        text = raw.get("chunk_text", "")
        eff_raw = raw.get("effective_date", "")
        exported_at = _normalize_exported_at(raw.get("exported_at", ""))

        if doc_id not in ALLOWED_DOC_IDS:
            quarantine.append({**raw, "reason": "unknown_doc_id"})
            continue

        eff_norm, eff_err = _normalize_effective_date(eff_raw)
        if eff_err == "empty_effective_date":
            quarantine.append({**raw, "reason": "missing_effective_date"})
            continue
        if eff_err == "invalid_effective_date_format":
            quarantine.append({**raw, "reason": eff_err, "effective_date_raw": eff_raw})
            continue

        if not exported_at:
            quarantine.append({**raw, "reason": "invalid_exported_at_format"})
            continue

        if doc_id == "hr_leave_policy" and eff_norm < "2026-01-01":
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_hr_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue

        if not text:
            quarantine.append({**raw, "reason": "missing_chunk_text"})
            continue

        key = _norm_text(text)
        if key in seen_text:
            quarantine.append({**raw, "reason": "duplicate_chunk_text"})
            continue
        seen_text.add(key)

        fixed_text = text
        if apply_refund_window_fix and doc_id == "policy_refund_v4":
            if "14 ngày làm việc" in fixed_text:
                fixed_text = fixed_text.replace(
                    "14 ngày làm việc",
                    "7 ngày làm việc",
                )
                fixed_text += " [cleaned: stale_refund_window]"
        if doc_id == "hr_leave_policy":
            fixed_text = _normalize_hr_leave_version(fixed_text, eff_norm)

        fixed_text = _strip_uncertain_prefix(fixed_text)
        fixed_text = _strip_leading_emphasis(fixed_text)
        fixed_text = _strip_noise_annotations(fixed_text)
        fixed_text = _collapse_repeated_sentences(fixed_text)
        if len(fixed_text.strip()) < 8:
            quarantine.append({**raw, "reason": "short_chunk_text_after_clean"})
            continue

        seq += 1
        cleaned.append(
            {
                "chunk_id": _stable_chunk_id(doc_id, fixed_text, seq),
                "doc_id": doc_id,
                "chunk_text": fixed_text,
                "effective_date": eff_norm,
                "exported_at": exported_at or "",
            }
        )

    return cleaned, quarantine


def write_cleaned_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at\n", encoding="utf-8")
        return
    fieldnames = ["chunk_id", "doc_id", "chunk_text", "effective_date", "exported_at"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def write_quarantine_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at,reason\n", encoding="utf-8")
        return
    keys: List[str] = []
    seen_k: set[str] = set()
    for r in rows:
        for k in r.keys():
            if k not in seen_k:
                seen_k.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", restval="")
        w.writeheader()
        for r in rows:
            w.writerow(r)
