"""Pydantic validation for cleaned Day 10 rows."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TZ_AWARE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2}|Z)$")


class CleanedRowModel(BaseModel):
    """Schema for cleaned rows persisted to CSV and vector index."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    chunk_text: str = Field(min_length=8)
    effective_date: str = Field(min_length=10, max_length=10)
    exported_at: str = Field(min_length=20)

    @field_validator("effective_date")
    @classmethod
    def _validate_effective_date(cls, value: str) -> str:
        if not _ISO_DATE.match(value or ""):
            raise ValueError("effective_date must be YYYY-MM-DD")
        return value

    @field_validator("exported_at")
    @classmethod
    def _validate_exported_at(cls, value: str) -> str:
        if not _TZ_AWARE_ISO.match(value or ""):
            raise ValueError("exported_at must be timezone-aware ISO-8601")
        return value


def validate_cleaned_rows(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Validate cleaned rows with a real pydantic model."""
    valid_rows: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    for idx, row in enumerate(rows):
        try:
            model = CleanedRowModel.model_validate(row)
            valid_rows.append(model.model_dump())
        except ValidationError as exc:
            errors.append({"row_index": idx, "errors": exc.errors()})

    summary = {
        "row_count": len(rows),
        "valid_count": len(valid_rows),
        "invalid_count": len(errors),
        "passed": len(errors) == 0,
        "errors": errors[:10],
    }
    return valid_rows, summary
