"""Prompt builders backed by templates stored in data/prompts."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


PROMPTS_DIR = Path(__file__).resolve().parents[2] / "data" / "prompts"
PRINCIPLES_FILE = PROMPTS_DIR / "System_Classification_Principles.txt"


def _load_template(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def _render_template(name: str, replacements: Dict[str, str]) -> str:
    template = _load_template(name)
    for key, value in replacements.items():
        template = template.replace(f"__{key}__", value)
    return template


def _read_text_with_fallback(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "gbk"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="latin-1")


def _load_compact_principles() -> str:
    if not PRINCIPLES_FILE.exists():
        return ""
    content = _read_text_with_fallback(PRINCIPLES_FILE).strip()
    if not content:
        return ""
    return (
        "\n\n【五维分类短原则】\n"
        f"{content}\n"
    )


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
    prompt = _render_template(
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
    guidance = (
        "\n\n【额外分析要求】\n"
        "1. 不仅总结显著升高或突出的子类，也要关注显著偏低或持续低活性的子类，并讨论其是否提示功能缺失、抑制或退行性改变。\n"
        "2. 优先讨论疾病发生机制与子类活性模式之间的关系，包括哪些结果支持该机制，哪些结果不完全支持或存在矛盾。\n"
        "3. 聚焦“五维分类是否能够合理解释该疾病”的问题，但不得预设其一定正确；应同时说明支持证据、限制和替代解释。\n"
        "4. 避免把相关性直接表述为因果性；如证据不足，请明确写成“提示”“可能”“需要进一步验证”。\n"
    )
    return prompt + _load_compact_principles() + guidance


def build_report_summary_prompt(
    dataset_info: Dict[str, Any],
    analysis_results: Dict[str, Any],
) -> str:
    return _render_template(
        "report_summary.txt",
        {
            "CHINESE_NAME": str(dataset_info.get("chinese_name", "Unknown")),
            "ANALYSIS_STRATEGY": str(analysis_results.get("analysis_strategy", "Unknown")),
            "KEY_FINDINGS": json.dumps(
                analysis_results.get("key_findings", []),
                ensure_ascii=False,
            ),
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

    prompt = _render_template(
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
    selection_guidance = (
        "\n\n【额外选择要求】\n"
        "1. 优先选择最可能补充当前五维分类覆盖盲区的数据集。\n"
        "2. 尽量选择能检验系统边界、子类边界或疾病机制解释力的数据集，而不只是重复已有模式。\n"
        "3. 只能在候选列表中选择，不允许虚构数据集。\n"
    )
    return prompt + _load_compact_principles() + selection_guidance
