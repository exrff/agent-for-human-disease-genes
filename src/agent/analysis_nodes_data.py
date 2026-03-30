#!/usr/bin/env python3
"""Data-oriented analysis nodes for the active disease analysis pipeline."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import gzip
import re


def extract_dataset_metadata(state: Dict[str, Any]) -> Dict[str, Any]:
    """Populate dataset metadata from runtime config and whitelist."""
    state["current_step"] = "extract_metadata"
    state["log_messages"].append(f"[{datetime.now()}] extracting dataset metadata...")

    dataset_id = state["dataset_id"]

    from .runtime_config import AgentConfig
    from .whitelist_repository import get_dataset_info

    dataset_info = AgentConfig.get_dataset_config(dataset_id)
    if not dataset_info:
        dataset_info = get_dataset_info(dataset_id) or {}

    if not dataset_info and state.get("dataset_info"):
        dataset_info = state["dataset_info"]

    state["dataset_info"] = dataset_info
    state["disease_type"] = dataset_info.get("disease_type", "unknown")

    state["log_messages"].append(f"dataset: {dataset_info.get('chinese_name', dataset_id)}")
    state["log_messages"].append(f"disease_type: {state['disease_type']}")
    state["log_messages"].append(f"dataset {dataset_id} metadata extracted")
    return state


def download_dataset(
    state: Dict[str, Any],
    validate_series_matrix,
) -> Dict[str, Any]:
    """Ensure raw GEO files exist locally, downloading them when necessary."""
    state["current_step"] = "download"
    state["log_messages"].append(f"[{datetime.now()}] preparing dataset files...")

    dataset_id = state["dataset_id"]
    data_path = f"data/validation_datasets/{dataset_id}"

    import os

    if os.path.exists(data_path):
        series_file = os.path.join(data_path, f"{dataset_id}_series_matrix.txt.gz")
        if os.path.exists(series_file):
            validation = validate_series_matrix(series_file)
            if not validation["has_data"]:
                state["errors"].append(
                    f"{dataset_id} has invalid expression matrix: {validation['reason']}"
                )
                state["log_messages"].append(f"dataset invalid: {validation['reason']}")
                return state

            platform_ids = _extract_series_platform_ids(Path(series_file))
            has_platform = _has_any_cached_platform(platform_ids)
            if platform_ids and not has_platform:
                state["log_messages"].append(
                    "series matrix exists, but required GPL file is not in data/gpl_platforms; downloading platform..."
                )
            else:
                state["raw_data_path"] = data_path
                state["log_messages"].append(f"dataset already exists: {data_path}")
                state["log_messages"].append(f"  - series matrix: {os.path.basename(series_file)}")
                state["log_messages"].append(
                    f"  - platform source: {'data/gpl_platforms' if has_platform else 'not declared'}"
                )
                state["log_messages"].append("dataset ready")
                return state

        state["log_messages"].append("dataset folder incomplete, redownloading...")

    state["log_messages"].append(f"downloading {dataset_id} from GEO...")

    try:
        from src.data_extraction.geo_downloader import download_geo_dataset

        result = download_geo_dataset(dataset_id)
        if result["success"]:
            series_file_path = result["series_matrix_file"]
            validation = validate_series_matrix(series_file_path)
            if not validation["has_data"]:
                state["errors"].append(
                    f"{dataset_id} has invalid expression matrix: {validation['reason']}"
                )
                state["log_messages"].append(f"dataset invalid: {validation['reason']}")
                return state

            state["raw_data_path"] = data_path
            state["log_messages"].append("download success")
            state["log_messages"].append(
                f"  - series matrix: {os.path.basename(result['series_matrix_file'])}"
            )
            state["log_messages"].append(
                f"  - platform files: {len(result['platform_files'])}"
            )
            state.setdefault("metadata", {})
            state["metadata"]["download_result"] = result
        else:
            error_msg = f"{dataset_id} download failed, missing GPL platform files"
            state["log_messages"].append(error_msg)
            for error in result.get("errors", []):
                state["log_messages"].append(f"  {error}")
            state["log_messages"].append(
                "please place required GPL files under data/gpl_platforms and retry"
            )
            state["errors"].append(error_msg)
            return state

    except Exception as exc:
        error_msg = f"downloader exception: {exc}"
        state["log_messages"].append(error_msg)
        state["log_messages"].append(
            "please place required GPL files under data/gpl_platforms and retry"
        )
        state["errors"].append(error_msg)
        return state

    state["log_messages"].append("dataset ready")
    return state


def _extract_series_platform_ids(series_file: Path) -> list[str]:
    platform_ids: list[str] = []
    try:
        with gzip.open(series_file, "rt", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if line.startswith("!Series_platform_id"):
                    match = re.search(r"GPL\d+", line)
                    if match:
                        platform_ids.append(match.group())
                if line.startswith("!series_matrix_table_begin"):
                    break
    except Exception:
        return []
    return list(dict.fromkeys(platform_ids))


def _has_any_cached_platform(platform_ids: list[str]) -> bool:
    if not platform_ids:
        return False
    cache_dir = Path("data/gpl_platforms")
    if not cache_dir.exists():
        return False
    for platform_id in platform_ids:
        for file in cache_dir.iterdir():
            if file.name.startswith(platform_id):
                return True
    return False


def _find_dataset_dir(dataset_id: str) -> Path:
    data_dir = Path("data/validation_datasets")
    for directory in data_dir.iterdir():
        if directory.is_dir() and directory.name.startswith(dataset_id):
            return directory
    return data_dir / dataset_id


def _probe_like_ratio(index_values) -> float:
    probe_hits = 0
    total = 0
    for raw in list(index_values)[:500]:
        text = str(raw).strip()
        if not text:
            continue
        total += 1
        if (
            text.startswith(("ILMN_", "AFFX", "A_", "cg", "TC", "HTA"))
            or re.search(r"_(at|s_at|x_at|st)$", text, flags=re.IGNORECASE)
            or re.match(r"^TC\d+\..*hg\.\d+$", text, flags=re.IGNORECASE)
            or re.match(r"^TSUnmapped\d+", text, flags=re.IGNORECASE)
            or "|" in text
            or ":" in text
        ):
            probe_hits += 1
    if total == 0:
        return 0.0
    return probe_hits / total


def preprocess_data(
    state: Dict[str, Any],
    find_gpl_file,
    parse_series_matrix,
    infer_matrix_identifier_type,
    parse_gpl_annotation,
    map_probe_to_gene,
    extract_sample_info,
) -> Dict[str, Any]:
    """Parse raw GEO files into a gene-level expression matrix."""
    state["current_step"] = "preprocess"
    state["log_messages"].append(f"[{datetime.now()}] preprocessing dataset...")

    dataset_id = state["dataset_id"]
    dataset_dir = _find_dataset_dir(dataset_id)
    series_file = dataset_dir / f"{dataset_id}_series_matrix.txt.gz"

    if not series_file.exists():
        state["errors"].append(f"series matrix file not found: {series_file}")
        state["log_messages"].append("series matrix file not found")
        return state

    state["log_messages"].append(f"series matrix: {series_file.name}")

    try:
        expr_df = parse_series_matrix(series_file)
        state["log_messages"].append(
            f"raw matrix: {expr_df.shape[0]} rows x {expr_df.shape[1]} samples"
        )
        if expr_df.shape[0] == 0:
            state["errors"].append(
                "series matrix contains header only and no expression rows; dataset is not analyzable"
            )
            state["log_messages"].append(
                "preprocess stop: empty expression matrix in series_matrix_table"
            )
            return state

        matrix_type = infer_matrix_identifier_type(expr_df)
        state.setdefault("metadata", {})
        state["metadata"]["matrix_identifier_type"] = matrix_type
        state["log_messages"].append(f"matrix identifier type inferred as: {matrix_type}")
        probe_ratio = _probe_like_ratio(expr_df.index)
        state["metadata"]["probe_like_ratio"] = probe_ratio
        state["log_messages"].append(f"probe-like id ratio: {probe_ratio:.3f}")

        gpl_file = find_gpl_file(series_file, dataset_dir)
        should_map = matrix_type in {"probe", "unknown"}
        # Safety override: even if inferred "gene", obvious probe signatures should trigger mapping.
        if matrix_type == "gene" and probe_ratio >= 0.08:
            if gpl_file is not None:
                should_map = True
                state["log_messages"].append(
                    "probe-like signatures detected in row IDs, forcing probe-to-gene mapping"
                )
            else:
                state["errors"].append(
                    "matrix looks probe-like but GPL annotation is missing; cannot safely continue"
                )
                state["log_messages"].append(
                    "preprocess stop: probe-like matrix without GPL annotation"
                )
                return state

        if not should_map:
            gene_expr_df = expr_df.copy()
            gene_expr_df.index = gene_expr_df.index.astype(str).str.strip()
            gene_expr_df = gene_expr_df[gene_expr_df.index != ""]
            gene_expr_df = gene_expr_df.groupby(gene_expr_df.index).mean()
            state["log_messages"].append("gene-level matrix detected, skip probe-to-gene mapping")
        else:
            if gpl_file is None:
                state["errors"].append("GPL annotation not found and matrix is not gene-level")
                state["log_messages"].append("cannot map probe->gene without GPL annotation")
                return state

            state["log_messages"].append(f"GPL file: {gpl_file.name}")
            mapping_df = parse_gpl_annotation(gpl_file)
            state["log_messages"].append(
                f"mapping: {mapping_df['probe_id'].nunique()} probes -> "
                f"{mapping_df['gene_symbol'].nunique()} genes"
            )
            gene_expr_df = map_probe_to_gene(expr_df, mapping_df)
            if gene_expr_df.shape[0] < 200 and probe_ratio >= 0.08:
                state["errors"].append(
                    "probe mapping produced too few genes; likely wrong platform mapping or annotation column"
                )
                state["log_messages"].append(
                    "preprocess stop: mapped gene matrix too small for probe-like input"
                )
                return state

        state["log_messages"].append(
            f"gene matrix: {gene_expr_df.shape[0]} genes x {gene_expr_df.shape[1]} samples"
        )
        if gene_expr_df.shape[0] == 0:
            state["errors"].append("gene matrix is empty after preprocessing (0 genes)")
            state["log_messages"].append("preprocess failed: empty gene matrix")
            return state

        state["expression_matrix"] = gene_expr_df
        state["sample_metadata"] = extract_sample_info(series_file)
        state["processed_data_path"] = str(dataset_dir)
        state["log_messages"].append("preprocessing complete")
    except Exception as exc:
        import traceback

        state["errors"].append(f"preprocess failed: {exc}")
        state["log_messages"].append(f"preprocess failed: {exc}\n{traceback.format_exc()}")

    return state
