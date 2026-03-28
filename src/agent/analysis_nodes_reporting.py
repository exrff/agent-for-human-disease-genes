#!/usr/bin/env python3
"""Reporting-oriented analysis nodes for the active disease analysis pipeline."""

import json
import os
from datetime import datetime
from typing import Any, Callable, Dict


def interpret_results(
    state: Dict[str, Any],
    capture_llm_trace: Callable[[Dict[str, Any], str, Dict[str, Any], Any], None],
) -> Dict[str, Any]:
    """Generate an interpretation of the current analysis results."""
    state["current_step"] = "interpret"
    state["log_messages"].append(f"[{datetime.now()}] 解读分析结果...")

    try:
        from .llm_client import create_llm_integration

        llm = create_llm_integration()
        dataset_info = {
            "dataset_id": state["dataset_id"],
            **state.get("dataset_info", {}),
        }

        interpretation = llm.interpret_results(
            dataset_info=dataset_info,
            ssgsea_scores=state.get("ssgsea_scores", {}),
            statistical_results=state.get("statistical_results"),
        )
        capture_llm_trace(
            state,
            "interpret",
            llm.get_last_trace(),
            {"interpretation_preview": (interpretation or "")[:300]},
        )

        state["interpretation"] = interpretation
        state["log_messages"].append("LLM 结果解读完成")
    except Exception as exc:
        state["log_messages"].append(f"LLM 解读失败: {exc}")
        capture_llm_trace(
            state,
            "interpret",
            {
                "operation": "interpret_results",
                "status": "fallback",
                "fallback_used": True,
                "error": str(exc),
                "response_text": None,
            },
            None,
        )
        state["interpretation"] = (
            "# 分析结果\n\n"
            f"数据集: {state.get('dataset_info', {}).get('chinese_name', 'Unknown')}\n"
            f"分析策略: {state.get('analysis_strategy', 'Unknown')}\n\n"
            "本研究对该数据集进行了五维分类分析。详细结果请参考生成的图表和统计摘要。\n\n"
            "*注：自动解读功能当前不可用，建议人工复核。*\n"
        )

    return state


def generate_report(state: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble the markdown report body."""
    state["current_step"] = "generate_report"
    state["log_messages"].append(f"[{datetime.now()}] 生成分析报告...")

    dataset_info = state.get("dataset_info", {})
    ssgsea_scores = state.get("ssgsea_scores", {})
    system_scores = state.get("system_scores", {})
    classification_results = state.get("classification_results", {})

    report_content = f"""# {dataset_info.get('chinese_name', 'Unknown')} 分析报告

**数据集ID**: {state['dataset_id']}  
**疾病类型**: {state.get('disease_type', 'Unknown')}  
**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**分析策略**: {state.get('analysis_strategy', 'Unknown')}

---

## 1. 数据集信息

- **名称**: {dataset_info.get('name', 'Unknown')}
- **中文名**: {dataset_info.get('chinese_name', 'Unknown')}
- **描述**: {dataset_info.get('description', 'Unknown')}
- **预期系统**: {', '.join(dataset_info.get('expected_systems', []))}

## 2. 数据处理

- **样本数量**: {(state.get('sample_metadata') or {}).get('sample_count', 'Unknown')}
- **基因数量**: {(classification_results or {}).get('total_genes', 'Unknown')}
- **分类基因**: {(classification_results or {}).get('classified', 'Unknown')}

## 3. 五大系统分类结果

### 系统分布

"""

    for system, count in classification_results.get("system_counts", {}).items():
        report_content += f"- **{system}**: {count} 个基因\n"

    report_content += "\n### 子类分布\n\n"
    for subcat, count in list(classification_results.get("subcategory_counts", {}).items())[:10]:
        report_content += f"- **{subcat}**: {count} 个基因\n"

    report_content += "\n## 4. ssGSEA 分析结果\n\n### 系统激活得分\n\n"
    for system, score in system_scores.items():
        report_content += f"- **{system}**: {score:.3f}\n"

    report_content += "\n### 子类激活得分（Top 5）\n\n"
    sorted_subcats = sorted(
        ssgsea_scores.items(),
        key=lambda item: item[1]["mean_score"],
        reverse=True,
    )[:5]
    for code, info in sorted_subcats:
        report_content += f"- **{code} ({info['name']})**: {info['mean_score']:.3f}\n"

    report_content += "\n## 5. 结果解读\n\n"
    interpretation = state.get("interpretation", "")
    report_content += interpretation if interpretation else "结果解读正在生成中...\n"

    report_content += "\n## 6. 可视化图表\n\n"
    for i, fig_path in enumerate(state.get("figures", []), 1):
        report_content += f"{i}. {fig_path}\n"

    report_content += "\n---\n\n*本报告由疾病分析智能体自动生成。*\n"

    state["report_content"] = report_content
    state["log_messages"].append("报告生成完成")
    state["log_messages"].append(f"报告长度: {len(report_content)} 字符")
    return state


def export_pdf(
    state: Dict[str, Any],
    write_structured_artifacts: Callable[[Dict[str, Any], str], Dict[str, str]],
) -> Dict[str, Any]:
    """Persist report and structured run artifacts."""
    state["current_step"] = "export_pdf"
    state["log_messages"].append(f"[{datetime.now()}] 导出 PDF 报告...")

    output_dir = f"results/agent_analysis/{state['dataset_id']}"
    os.makedirs(output_dir, exist_ok=True)

    report_path = os.path.join(output_dir, f"{state['dataset_id']}_report.md")
    report_content = state.get("report_content")
    if not report_content:
        errors = state.get("errors", [])
        error_lines = "\n".join(f"- {error}" for error in errors) if errors else "- 无详细错误信息"
        report_content = f"""# {state['dataset_id']} 分析报告

本次分析未能完成主流程，已生成失败摘要。

## 数据集

- ID: {state['dataset_id']}
- 名称: {state.get('dataset_info', {}).get('chinese_name', state['dataset_id'])}
- 疾病类型: {state.get('disease_type', 'unknown')}

## 失败阶段

- 当前步骤: {state.get('current_step', 'unknown')}

## 错误信息

{error_lines}
"""
        state["report_content"] = report_content

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    state["report_path"] = report_path
    state["log_messages"].append(f"报告已保存: {report_path}")
    state["log_messages"].append(f"文件大小: {len(report_content)} 字节")

    summary_path = os.path.join(output_dir, "analysis_summary.json")
    summary = {
        "run_id": state.get("run_id"),
        "dataset_id": state["dataset_id"],
        "dataset_name": state.get("dataset_info", {}).get("chinese_name", "Unknown"),
        "disease_type": state.get("disease_type", "Unknown"),
        "analysis_strategy": state.get("analysis_strategy", "Unknown"),
        "analysis_time": datetime.now().isoformat(),
        "classification_results": state.get("classification_results", {}),
        "system_scores": state.get("system_scores", {}),
        "ssgsea_scores": {
            code: {k: v for k, v in info.items() if k != "matched_genes"}
            for code, info in (state.get("ssgsea_scores") or {}).items()
        },
        "top_systems": [
            system
            for system, _ in sorted(
                (state.get("system_scores") or {}).items(),
                key=lambda item: item[1],
                reverse=True,
            )[:3]
        ],
        "figures": state.get("figures", []),
        "report_path": report_path,
        "errors": state.get("errors", []),
        "pipeline_log": state.get("log_messages", [])[-30:],
        "node_event_count": len(state.get("node_events", [])),
        "llm_trace_count": len(state.get("llm_traces", [])),
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    state["log_messages"].append(f"摘要已保存: {summary_path}")

    artifact_paths = write_structured_artifacts(state, output_dir)
    state.setdefault("metadata", {})
    state["metadata"]["structured_artifacts"] = artifact_paths
    state["log_messages"].append(f"结构化日志已保存: {artifact_paths['run_log_path']}")
    return state
