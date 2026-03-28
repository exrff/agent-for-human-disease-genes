#!/usr/bin/env python3
"""Data-oriented analysis nodes for the active disease analysis pipeline."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def extract_dataset_metadata(state: Dict[str, Any]) -> Dict[str, Any]:
    """Populate dataset metadata from runtime config and whitelist."""
    state["current_step"] = "extract_metadata"
    state["log_messages"].append(f"[{datetime.now()}] 开始提取数据集元信息...")

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

    state["log_messages"].append(f"数据集: {dataset_info.get('chinese_name', dataset_id)}")
    state["log_messages"].append(f"疾病类型: {state['disease_type']}")
    state["log_messages"].append(f"数据集 {dataset_id} 元信息提取完成")
    return state


def download_dataset(
    state: Dict[str, Any],
    validate_series_matrix,
) -> Dict[str, Any]:
    """Ensure raw GEO files exist locally, downloading them when necessary."""
    state["current_step"] = "download"
    state["log_messages"].append(f"[{datetime.now()}] 准备数据集...")

    dataset_id = state["dataset_id"]
    data_path = f"data/validation_datasets/{dataset_id}"

    import os

    if os.path.exists(data_path):
        series_file = os.path.join(data_path, f"{dataset_id}_series_matrix.txt.gz")
        platform_files = [f for f in os.listdir(data_path) if f.startswith("GPL")]

        if os.path.exists(series_file) and len(platform_files) > 0:
            validation = validate_series_matrix(series_file)
            if not validation["has_data"]:
                state["errors"].append(
                    f"{dataset_id} 无有效表达矩阵: {validation['reason']}"
                )
                state["log_messages"].append(f"数据集无效: {validation['reason']}")
                return state

            state["raw_data_path"] = data_path
            state["log_messages"].append(f"数据已存在: {data_path}")
            state["log_messages"].append(f"  - Series matrix: {os.path.basename(series_file)}")
            state["log_messages"].append(f"  - Platform 文件: {len(platform_files)} 个")
            state["log_messages"].append("数据准备完成")
            return state

        state["log_messages"].append("数据不完整，重新下载...")

    state["log_messages"].append(f"开始从 GEO 下载 {dataset_id}...")

    try:
        from src.data_extraction.geo_downloader import download_geo_dataset

        result = download_geo_dataset(dataset_id)
        if result["success"]:
            series_file_path = result["series_matrix_file"]
            validation = validate_series_matrix(series_file_path)
            if not validation["has_data"]:
                state["errors"].append(
                    f"{dataset_id} 无有效表达矩阵: {validation['reason']}"
                )
                state["log_messages"].append(f"数据集无效: {validation['reason']}")
                state["log_messages"].append("请重新选择数据集")
                return state

            state["raw_data_path"] = data_path
            state["log_messages"].append("数据下载成功")
            state["log_messages"].append(
                f"  - Series matrix: {os.path.basename(result['series_matrix_file'])}"
            )
            state["log_messages"].append(
                f"  - Platform 文件: {len(result['platform_files'])} 个"
            )

            state.setdefault("metadata", {})
            state["metadata"]["download_result"] = result
        else:
            error_msg = f"{dataset_id} 下载失败，缺少 GPL 平台文件，终止分析"
            state["log_messages"].append(error_msg)
            for error in result.get("errors", []):
                state["log_messages"].append(f"  {error}")
            state["log_messages"].append(
                "请将对应 GPL 文件放入 data/gpl_platforms/ 后重试"
            )
            state["errors"].append(error_msg)
            return state

    except Exception as exc:
        error_msg = f"下载器异常: {exc}"
        state["log_messages"].append(error_msg)
        state["log_messages"].append(
            "请将对应 GPL 文件放入 data/gpl_platforms/ 后重试"
        )
        state["errors"].append(error_msg)
        return state

    state["log_messages"].append("数据准备完成")
    return state


def preprocess_data(
    state: Dict[str, Any],
    find_gpl_file,
    parse_series_matrix,
    parse_gpl_annotation,
    map_probe_to_gene,
    extract_sample_info,
) -> Dict[str, Any]:
    """Parse raw GEO files into a gene-level expression matrix."""
    state["current_step"] = "preprocess"
    state["log_messages"].append(f"[{datetime.now()}] 数据预处理...")

    dataset_id = state["dataset_id"]
    data_dir = Path("data/validation_datasets")

    dataset_dir = None
    for directory in data_dir.iterdir():
        if directory.is_dir() and directory.name.startswith(dataset_id):
            dataset_dir = directory
            break
    if dataset_dir is None:
        dataset_dir = data_dir / dataset_id

    series_file = dataset_dir / f"{dataset_id}_series_matrix.txt.gz"
    if not series_file.exists():
        state["errors"].append(f"Series matrix 文件不存在: {series_file}")
        state["log_messages"].append("找不到 series matrix 文件")
        return state

    gpl_file = find_gpl_file(series_file, dataset_dir)
    if gpl_file is None:
        state["errors"].append("找不到 GPL 平台注释文件")
        state["log_messages"].append("找不到 GPL 平台文件")
        return state

    state["log_messages"].append(f"Series matrix: {series_file.name}")
    state["log_messages"].append(f"GPL 文件: {gpl_file.name}")

    try:
        expr_df = parse_series_matrix(series_file)
        state["log_messages"].append(
            f"Probe 矩阵: {expr_df.shape[0]} probes x {expr_df.shape[1]} samples"
        )

        mapping_df = parse_gpl_annotation(gpl_file)
        state["log_messages"].append(
            f"映射: {mapping_df['probe_id'].nunique()} probes -> "
            f"{mapping_df['gene_symbol'].nunique()} genes"
        )

        gene_expr_df = map_probe_to_gene(expr_df, mapping_df)
        state["log_messages"].append(
            f"Gene 矩阵: {gene_expr_df.shape[0]} genes x {gene_expr_df.shape[1]} samples"
        )

        state["expression_matrix"] = gene_expr_df
        state["sample_metadata"] = extract_sample_info(series_file)
        state["processed_data_path"] = str(dataset_dir)
        state["log_messages"].append("预处理完成")
    except Exception as exc:
        import traceback

        state["errors"].append(f"预处理失败: {exc}")
        state["log_messages"].append(f"预处理失败: {exc}\n{traceback.format_exc()}")

    return state
