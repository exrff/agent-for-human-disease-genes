"""Prompt builders backed by templates stored in data/prompts."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


PROMPTS_DIR = Path(__file__).resolve().parents[2] / "data" / "prompts"


def _load_template(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def _render_template(name: str, replacements: Dict[str, str]) -> str:
    template = _load_template(name)
    for key, value in replacements.items():
        template = template.replace(f"__{key}__", value)
    return template


def build_analysis_strategy_prompt(dataset_info: Dict[str, Any]) -> str:
    return _render_template(
        "analysis_strategy.txt",
        {
            "DATASET_ID": str(dataset_info.get("dataset_id", "Unknown")),
            "NAME": str(dataset_info.get("name", "Unknown")),
            "CHINESE_NAME": str(dataset_info.get("chinese_name", "Unknown")),
            "DISEASE_TYPE": str(dataset_info.get("disease_type", "Unknown")),
            "DESCRIPTION": str(dataset_info.get("description", "Unknown")),
        },
    )


def build_visualization_strategy_prompt(
    analysis_strategy: str,
    data_characteristics: Dict[str, Any],
) -> str:
    return _render_template(
        "visualization_strategy.txt",
        {
            "ANALYSIS_STRATEGY": analysis_strategy,
            "DATA_CHARACTERISTICS": json.dumps(
                data_characteristics,
                ensure_ascii=False,
                indent=2,
            ),
        },
    )


def build_result_interpretation_prompt(
    dataset_info: Dict[str, Any],
    score_summary: str,
    statistical_results: Optional[Dict[str, Any]] = None,
) -> str:
    return _render_template(
        "result_interpretation.txt",
        {
            "NAME": str(dataset_info.get("name", "Unknown")),
            "CHINESE_NAME": str(dataset_info.get("chinese_name", "Unknown")),
            "DISEASE_TYPE": str(dataset_info.get("disease_type", "Unknown")),
            "DESCRIPTION": str(dataset_info.get("description", "Unknown")),
            "SCORE_SUMMARY": score_summary or "无",
            "STATISTICAL_RESULTS": json.dumps(
                statistical_results,
                ensure_ascii=False,
                indent=2,
            ) if statistical_results else "无",
        },
    )


def build_report_summary_prompt(
    dataset_info: Dict[str, Any],
    analysis_results: Dict[str, Any],
) -> str:
    return _render_template(
        "report_summary.txt",
        {
            "CHINESE_NAME": str(dataset_info.get("chinese_name", "Unknown")),
            "ANALYSIS_STRATEGY": str(analysis_results.get("analysis_strategy", "Unknown")),
            "KEY_FINDINGS": str(analysis_results.get("key_findings", [])),
        },
    )


def build_dataset_selection_prompt(
    analyzed: Dict[str, Any],
    unanalyzed: List[Dict[str, Any]],
) -> str:
    analyzed_lines = []
    for dataset in analyzed.get("datasets", []):
        systems = ", ".join(dataset.get("systems_activated", [])) or "无"
        analyzed_lines.append(
            f"- **{dataset['dataset_id']}**: {dataset['disease_type']}, 激活系统: {systems}"
        )

    if not analyzed_lines:
        analyzed_lines.append("（尚未分析任何数据集）")

    system_lines = []
    for system, count in sorted(analyzed.get("system_coverage", {}).items()):
        system_lines.append(f"- {system}: {count} 次")

    if not system_lines:
        system_lines.append("（尚无统计数据）")

    unanalyzed_lines = []
    for dataset in unanalyzed:
        expected_systems = ", ".join(dataset.get("expected_systems", [])) or "无"
        sample_count = dataset.get("n_samples", "?")
        unanalyzed_lines.append(
            f"- **{dataset['dataset_id']}** | {dataset['chinese_name']} ({dataset['name']}) | "
            f"疾病类型: {dataset['disease_type']} | "
            f"预期系统: {expected_systems} | "
            f"样本数: {sample_count} | "
            f"{dataset['description']}"
        )

    return _render_template(
        "dataset_selection.txt",
        {
            "TOTAL_COUNT": str(analyzed.get("total_count", 0)),
            "ANALYZED_DATASETS": "\n".join(analyzed_lines),
            "DISEASE_TYPES": ", ".join(analyzed.get("disease_types", [])) or "无",
            "SYSTEM_COVERAGE": "\n".join(system_lines),
            "UNANALYZED_COUNT": str(len(unanalyzed)),
            "UNANALYZED_DATASETS": "\n".join(unanalyzed_lines),
        },
    )
