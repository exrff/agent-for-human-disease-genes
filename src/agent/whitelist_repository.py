#!/usr/bin/env python3
"""Unified access to the dataset whitelist."""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


LOGGER = logging.getLogger(__name__)
WHITELIST_PATH = Path(__file__).resolve().parents[2] / "data" / "geo_whitelist.csv"
FAILED_ARCHIVE_PATH = Path(__file__).resolve().parents[2] / "data" / "failed_whitelist_datasets.csv"


def _normalize_expected_systems(raw_value: str) -> List[str]:
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(";") if item.strip()]


def load_whitelist_datasets() -> Dict[str, Dict[str, Any]]:
    """Load all datasets from the single whitelist source."""
    datasets: Dict[str, Dict[str, Any]] = {}

    if not WHITELIST_PATH.exists():
        LOGGER.warning("Whitelist file not found: %s", WHITELIST_PATH)
        return datasets

    try:
        with open(WHITELIST_PATH, "r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                dataset_id = (row.get("dataset_id") or "").strip()
                if not dataset_id:
                    continue

                datasets[dataset_id] = {
                    "dataset_id": dataset_id,
                    "name": (row.get("name") or dataset_id).strip(),
                    "chinese_name": (row.get("chinese_name") or dataset_id).strip(),
                    "disease_type": (row.get("disease_type") or "unknown").strip(),
                    "expected_strategy": (row.get("expected_strategy") or "").strip(),
                    "expected_systems": _normalize_expected_systems(
                        row.get("expected_systems", "")
                    ),
                    "description": (row.get("description") or "").strip(),
                    "platform": (row.get("platform") or "").strip(),
                    "n_samples": int((row.get("n_samples") or "0").strip() or 0),
                    "pub_date": (row.get("pub_date") or "").strip(),
                    "gdstype": (row.get("gdstype") or "").strip(),
                }
    except Exception as exc:
        LOGGER.warning("Failed reading whitelist file %s: %s", WHITELIST_PATH, exc)
        return {}

    return datasets


def get_dataset_info(dataset_id: str) -> Optional[Dict[str, Any]]:
    """Return whitelist metadata for a single dataset."""
    return load_whitelist_datasets().get(dataset_id)


def remove_dataset_from_whitelist(dataset_id: str, reason: str = "") -> bool:
    """Remove one dataset from whitelist and archive the removed row."""
    if not WHITELIST_PATH.exists():
        LOGGER.warning("Whitelist file not found when removing dataset: %s", WHITELIST_PATH)
        return False

    with open(WHITELIST_PATH, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    removed_row: Optional[Dict[str, str]] = None
    kept_rows: List[Dict[str, str]] = []
    for row in rows:
        current_id = (row.get("dataset_id") or "").strip()
        if current_id == dataset_id and removed_row is None:
            removed_row = dict(row)
            continue
        kept_rows.append(row)

    if removed_row is None:
        LOGGER.info("Dataset not found in whitelist, nothing removed: %s", dataset_id)
        return False

    with open(WHITELIST_PATH, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept_rows)

    archive_exists = FAILED_ARCHIVE_PATH.exists()
    archive_fields = fieldnames + ["removed_at", "remove_reason"]
    archive_row = {k: removed_row.get(k, "") for k in fieldnames}
    archive_row["removed_at"] = datetime.now().isoformat(timespec="seconds")
    archive_row["remove_reason"] = reason

    with open(FAILED_ARCHIVE_PATH, "a", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=archive_fields)
        if not archive_exists:
            writer.writeheader()
        writer.writerow(archive_row)

    LOGGER.info("Removed dataset from whitelist: %s", dataset_id)
    return True
