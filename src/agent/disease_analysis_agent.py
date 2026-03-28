#!/usr/bin/env python3
"""Workflow orchestrator for the active disease analysis pipeline."""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from .analysis_nodes_data import (
    download_dataset as data_download_dataset,
    extract_dataset_metadata as data_extract_dataset_metadata,
    preprocess_data as data_preprocess_data,
)
from .analysis_nodes_reporting import (
    export_pdf as reporting_export_pdf,
    generate_report as reporting_generate_report,
    interpret_results as reporting_interpret_results,
)
from .analysis_nodes_scoring import (
    classify_genes as scoring_classify_genes,
    perform_ssgsea as scoring_perform_ssgsea,
)
from .geo_parsing import (
    extract_gene_symbol_from_annotation as parsing_extract_gene_symbol_from_annotation,
    extract_sample_info as parsing_extract_sample_info,
    find_gpl_file as parsing_find_gpl_file,
    map_probe_to_gene as parsing_map_probe_to_gene,
    parse_gpl_annotation as parsing_parse_gpl_annotation,
    parse_series_matrix as parsing_parse_series_matrix,
    validate_series_matrix as parsing_validate_series_matrix,
)
from .scoring_core import (
    SUBCATEGORY_NAMES,
    SUBCATEGORY_TO_SYSTEM,
    build_subcategory_gene_sets as shared_build_subcategory_gene_sets,
    compute_ssgsea_scores as shared_compute_ssgsea_scores,
)


class AnalysisState(TypedDict):
    dataset_id: str
    dataset_info: Dict[str, Any]
    raw_data_path: Optional[str]
    processed_data_path: Optional[str]
    expression_matrix: Optional[Any]
    sample_metadata: Optional[Dict[str, Any]]
    classification_results: Optional[Dict[str, Any]]
    ssgsea_scores: Optional[Dict[str, Any]]
    system_scores: Optional[Dict[str, Any]]
    statistical_results: Optional[Dict[str, Any]]
    disease_type: Optional[str]
    analysis_strategy: Optional[str]
    visualization_plan: List[str]
    metadata: Optional[Dict[str, Any]]
    report_content: Optional[str]
    figures: List[str]
    interpretation: Optional[str]
    report_path: Optional[str]
    log_messages: List[str]
    errors: List[str]
    current_step: str
    run_id: str
    node_events: List[Dict[str, Any]]
    llm_traces: List[Dict[str, Any]]
    needs_human_review: bool
    retry_count: int


def _ensure_runtime_state(state: AnalysisState) -> AnalysisState:
    if not state.get("run_id"):
        dataset_id = state.get("dataset_id", "unknown")
        state["run_id"] = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{dataset_id}"
    if state.get("node_events") is None:
        state["node_events"] = []
    if state.get("llm_traces") is None:
        state["llm_traces"] = []
    if state.get("metadata") is None:
        state["metadata"] = {}
    return state


def _shorten_text(value: Any, limit: int = 400) -> Any:
    if value is None:
        return None
    text = str(value)
    return text if len(text) <= limit else f"{text[:limit]}...<trimmed>"


def _make_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _make_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_make_json_safe(v) for v in value]
    if hasattr(value, "shape") and hasattr(value, "columns"):
        return {
            "type": type(value).__name__,
            "shape": list(value.shape),
            "rows": len(value.index) if hasattr(value, "index") else None,
            "columns": len(value.columns) if hasattr(value, "columns") else None,
        }
    return _shorten_text(value, limit=300)


def _capture_llm_trace(
    state: AnalysisState,
    node_name: str,
    trace: Optional[Dict[str, Any]],
    adopted_output: Optional[Any] = None,
) -> None:
    if not trace:
        return
    _ensure_runtime_state(state)
    trace_entry = _make_json_safe(trace)
    trace_entry["node"] = node_name
    if adopted_output is not None:
        trace_entry["adopted_output"] = _make_json_safe(adopted_output)
    state["llm_traces"].append(trace_entry)


def _summarize_input(node_name: str, state: AnalysisState) -> Dict[str, Any]:
    summary = {
        "dataset_id": state.get("dataset_id"),
        "disease_type": state.get("disease_type"),
        "analysis_strategy": state.get("analysis_strategy"),
        "current_step": state.get("current_step"),
    }
    if node_name in {"download", "preprocess"}:
        summary["raw_data_path"] = state.get("raw_data_path")
    if node_name in {"classify", "ssgsea"}:
        matrix = state.get("expression_matrix")
        summary["expression_matrix_shape"] = list(matrix.shape) if matrix is not None else None
    if node_name in {"decide_visualization", "generate_plots"}:
        summary["visualization_plan"] = state.get("visualization_plan", [])
    return _make_json_safe(summary)


def _summarize_output(node_name: str, state: AnalysisState) -> Dict[str, Any]:
    output: Dict[str, Any] = {"errors": state.get("errors", [])[-3:]}
    if node_name == "extract_metadata":
        output["dataset_info"] = {
            "dataset_id": state.get("dataset_id"),
            "chinese_name": (state.get("dataset_info") or {}).get("chinese_name"),
            "disease_type": state.get("disease_type"),
        }
    elif node_name == "decide_strategy":
        output["analysis_strategy"] = state.get("analysis_strategy")
    elif node_name == "download":
        output["raw_data_path"] = state.get("raw_data_path")
    elif node_name == "preprocess":
        matrix = state.get("expression_matrix")
        output["expression_matrix_shape"] = list(matrix.shape) if matrix is not None else None
        output["sample_count"] = (state.get("sample_metadata") or {}).get("sample_count")
    elif node_name == "classify":
        result = state.get("classification_results") or {}
        output["classification_results"] = {
            "classified": result.get("classified"),
            "total_genes": result.get("total_genes"),
        }
    elif node_name == "ssgsea":
        output["system_scores"] = state.get("system_scores")
    elif node_name == "decide_visualization":
        output["visualization_plan"] = state.get("visualization_plan", [])
    elif node_name == "generate_plots":
        output["figures"] = state.get("figures", [])
    elif node_name == "interpret":
        output["interpretation_preview"] = _shorten_text(state.get("interpretation", ""), 200)
    elif node_name == "generate_report":
        output["report_length"] = len(state.get("report_content") or "")
    elif node_name == "export_pdf":
        output["report_path"] = state.get("report_path")
    return _make_json_safe(output)


def _collect_node_metrics(node_name: str, state: AnalysisState) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {}
    if node_name == "download":
        download_result = (state.get("metadata") or {}).get("download_result", {})
        metrics = {
            "series_matrix_file": download_result.get("series_matrix_file"),
            "platform_file_count": len(download_result.get("platform_files", [])),
            "used_cache": download_result.get("used_cache"),
        }
    elif node_name == "preprocess":
        matrix = state.get("expression_matrix")
        metrics = {
            "gene_count": int(matrix.shape[0]) if matrix is not None else 0,
            "sample_count": int(matrix.shape[1]) if matrix is not None else 0,
            "metadata_sample_count": (state.get("sample_metadata") or {}).get("sample_count", 0),
        }
    elif node_name == "classify":
        result = state.get("classification_results") or {}
        total = result.get("total_genes") or 0
        classified = result.get("classified") or 0
        metrics = {
            "total_genes": total,
            "classified_genes": classified,
            "unclassified_genes": result.get("unclassified", 0),
            "classification_rate": round(classified / total, 4) if total else 0,
            "system_counts": result.get("system_counts", {}),
        }
    elif node_name == "ssgsea":
        scores = state.get("ssgsea_scores") or {}
        top_subcategories = sorted(
            (
                {
                    "code": code,
                    "mean_score": info.get("mean_score", 0),
                    "matched_genes": info.get("matched_genes", 0),
                }
                for code, info in scores.items()
            ),
            key=lambda item: item["mean_score"],
            reverse=True,
        )[:5]
        metrics = {
            "subcategory_count": len(scores),
            "system_scores": state.get("system_scores") or {},
            "top_subcategories": top_subcategories,
        }
    elif node_name == "decide_visualization":
        metrics = {
            "visualization_count": len(state.get("visualization_plan", [])),
            "visualization_plan": state.get("visualization_plan", []),
        }
    elif node_name == "generate_plots":
        metrics = {
            "figure_count": len(state.get("figures", [])),
            "figures": state.get("figures", []),
        }
    elif node_name == "interpret":
        metrics = {"interpretation_length": len(state.get("interpretation") or "")}
    elif node_name == "generate_report":
        metrics = {"report_length": len(state.get("report_content") or "")}
    elif node_name == "export_pdf":
        metrics = {"report_path": state.get("report_path")}
    return _make_json_safe(metrics)


def _record_node_event(
    state: AnalysisState,
    *,
    node_name: str,
    started_at: str,
    completed_at: str,
    duration_ms: int,
    status: str,
    input_summary: Dict[str, Any],
    output_summary: Dict[str, Any],
    metrics: Dict[str, Any],
    new_logs: List[str],
    new_errors: List[str],
) -> None:
    _ensure_runtime_state(state)
    status_labels = {"success": "成功", "warning": "警告", "failed": "失败"}
    state["node_events"].append(
        {
            "run_id": state.get("run_id"),
            "node": node_name,
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "status": status,
            "status_zh": status_labels.get(status, status),
            "input_summary": _make_json_safe(input_summary),
            "output_summary": _make_json_safe(output_summary),
            "metrics": _make_json_safe(metrics),
            "new_logs": _make_json_safe(new_logs),
            "new_errors": _make_json_safe(new_errors),
        }
    )


def _wrap_node(node_name: str, node_func):
    def wrapped(state: AnalysisState) -> AnalysisState:
        _ensure_runtime_state(state)
        started_at = datetime.now().isoformat()
        started_perf = time.perf_counter()
        input_summary = _summarize_input(node_name, state)
        log_start = len(state.get("log_messages", []))
        error_start = len(state.get("errors", []))

        try:
            result = node_func(state)
        except Exception as exc:
            completed_at = datetime.now().isoformat()
            duration_ms = int((time.perf_counter() - started_perf) * 1000)
            state.setdefault("errors", []).append(f"{node_name} unexpected error: {exc}")
            _record_node_event(
                state,
                node_name=node_name,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                status="failed",
                input_summary=input_summary,
                output_summary={"exception": str(exc)},
                metrics={},
                new_logs=state.get("log_messages", [])[log_start:],
                new_errors=state.get("errors", [])[error_start:],
            )
            raise

        result = result or state
        completed_at = datetime.now().isoformat()
        duration_ms = int((time.perf_counter() - started_perf) * 1000)
        new_logs = result.get("log_messages", [])[log_start:]
        new_errors = result.get("errors", [])[error_start:]

        status = "success"
        if new_errors:
            status = "failed"
        elif any(
            ("⚠" in line)
            or ("跳过" in line)
            or ("回退" in line)
            or ("LLM 不可用" in line)
            or ("LLM 解读失败" in line)
            for line in new_logs
        ):
            status = "warning"

        _record_node_event(
            result,
            node_name=node_name,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            status=status,
            input_summary=input_summary,
            output_summary=_summarize_output(node_name, result),
            metrics=_collect_node_metrics(node_name, result),
            new_logs=new_logs,
            new_errors=new_errors,
        )
        return result

    return wrapped


def _write_structured_artifacts(state: AnalysisState, output_dir: str) -> Dict[str, str]:
    llm_trace_dir = os.path.join(output_dir, "llm_traces")
    os.makedirs(llm_trace_dir, exist_ok=True)

    node_events_path = os.path.join(output_dir, "node_events.jsonl")
    with open(node_events_path, "w", encoding="utf-8") as f:
        for event in state.get("node_events", []):
            f.write(json.dumps(_make_json_safe(event), ensure_ascii=False) + "\n")

    llm_index = []
    for idx, trace in enumerate(state.get("llm_traces", []), 1):
        trace_file = os.path.join(llm_trace_dir, f"{idx:02d}_{trace.get('node', 'llm')}.json")
        with open(trace_file, "w", encoding="utf-8") as f:
            json.dump(_make_json_safe(trace), f, ensure_ascii=False, indent=2)
        llm_index.append(
            {
                "node": trace.get("node"),
                "operation": trace.get("operation"),
                "status": trace.get("status"),
                "path": trace_file,
            }
        )

    run_log = {
        "run_id": state.get("run_id"),
        "dataset_id": state.get("dataset_id"),
        "dataset_name": (state.get("dataset_info") or {}).get("chinese_name"),
        "disease_type": state.get("disease_type"),
        "analysis_strategy": state.get("analysis_strategy"),
        "status": "failed" if state.get("errors") else "success",
        "status_zh": "失败" if state.get("errors") else "成功",
        "analysis_time": datetime.now().isoformat(),
        "node_count": len(state.get("node_events", [])),
        "llm_trace_count": len(state.get("llm_traces", [])),
        "figure_count": len(state.get("figures", [])),
        "errors": state.get("errors", []),
        "node_events": state.get("node_events", []),
        "llm_trace_index": llm_index,
    }

    run_log_path = os.path.join(output_dir, "run_log.json")
    with open(run_log_path, "w", encoding="utf-8") as f:
        json.dump(_make_json_safe(run_log), f, ensure_ascii=False, indent=2)

    return {
        "run_log_path": run_log_path,
        "node_events_path": node_events_path,
        "llm_trace_dir": llm_trace_dir,
    }


def _safe_console_text(text: Any) -> str:
    rendered = str(text)
    try:
        return rendered.encode("gbk", errors="replace").decode("gbk", errors="replace")
    except Exception:
        return rendered


def extract_dataset_metadata(state: AnalysisState) -> AnalysisState:
    return data_extract_dataset_metadata(state)


def decide_analysis_strategy(state: AnalysisState) -> AnalysisState:
    state["current_step"] = "decide_strategy"
    state["log_messages"].append(f"[{datetime.now()}] 决策分析策略...")

    try:
        from .llm_client import create_llm_integration

        llm = create_llm_integration()
        dataset_info = {"dataset_id": state["dataset_id"], **state.get("dataset_info", {})}
        decision = llm.decide_analysis_strategy(dataset_info)
        _capture_llm_trace(state, "decide_strategy", llm.get_last_trace(), decision)

        state["analysis_strategy"] = decision["strategy"]
        state["log_messages"].append(
            f"LLM 决策: {decision['strategy']} (置信度: {decision.get('confidence', 0):.2f})"
        )
        state["log_messages"].append(f"理由: {decision.get('reasoning', '')}")
        state.setdefault("metadata", {})
        state["metadata"]["strategy_decision"] = decision
    except Exception as exc:
        state["log_messages"].append(f"LLM 不可用，使用规则引擎: {exc}")
        _capture_llm_trace(
            state,
            "decide_strategy",
            {
                "operation": "decide_analysis_strategy",
                "status": "fallback",
                "fallback_used": True,
                "error": str(exc),
                "response_text": None,
            },
        )
        strategy_map = {
            "neurodegenerative": "case_control",
            "cancer": "subtype_comparison",
            "metabolic": "case_control",
            "repair": "time_series",
            "infection": "case_control",
        }
        strategy = strategy_map.get(state.get("disease_type", "unknown"), "case_control")
        state["analysis_strategy"] = strategy
        state["log_messages"].append(f"规则引擎决策: {strategy}")

    return state


def download_dataset(state: AnalysisState) -> AnalysisState:
    return data_download_dataset(state, parsing_validate_series_matrix)


def preprocess_data(state: AnalysisState) -> AnalysisState:
    return data_preprocess_data(
        state,
        parsing_find_gpl_file,
        parsing_parse_series_matrix,
        parsing_parse_gpl_annotation,
        parsing_map_probe_to_gene,
        parsing_extract_sample_info,
    )


def _validate_series_matrix(series_file) -> dict:
    return parsing_validate_series_matrix(series_file)


def _find_gpl_file(series_file, dataset_dir):
    return parsing_find_gpl_file(series_file, dataset_dir)


def _parse_series_matrix(series_file):
    return parsing_parse_series_matrix(series_file)


def _parse_gpl_annotation(gpl_file):
    return parsing_parse_gpl_annotation(gpl_file)


def _extract_gene_symbol_from_annotation(annotation: str) -> str:
    return parsing_extract_gene_symbol_from_annotation(annotation)


def _map_probe_to_gene(expr_df, mapping_df):
    return parsing_map_probe_to_gene(expr_df, mapping_df)


def _build_subcategory_gene_sets() -> Dict[str, List[str]]:
    return shared_build_subcategory_gene_sets()


def _extract_sample_info(series_file) -> Dict[str, Any]:
    return parsing_extract_sample_info(series_file)


def classify_genes(state: AnalysisState) -> AnalysisState:
    return scoring_classify_genes(state)


def perform_ssgsea(state: AnalysisState) -> AnalysisState:
    return scoring_perform_ssgsea(state)


def _compute_ssgsea_scores(gene_expr_df, gene_set_genes: list, alpha: float = 0.25):
    return shared_compute_ssgsea_scores(gene_expr_df, gene_set_genes, alpha=alpha)


def decide_visualization(state: AnalysisState) -> AnalysisState:
    state["current_step"] = "decide_visualization"
    viz_map = {
        "heatmap": "heatmap",
        "boxplot": "boxplot",
        "correlation_heatmap": "correlation",
        "correlation": "correlation",
        "time_series": "heatmap",
        "clustering": "heatmap",
        "network": "correlation",
        "volcano": "barplot",
        "trajectory": "barplot",
        "immune_profile": "barplot",
        "pathway": "barplot",
    }
    always_include = ["radar", "barplot"]

    try:
        from .llm_client import create_llm_integration

        llm = create_llm_integration()
        data_characteristics = {
            "sample_count": state.get("sample_metadata", {}).get("sample_count", 0),
            "has_time_series": "time" in str(state.get("sample_metadata", {})).lower(),
            "analysis_strategy": state.get("analysis_strategy", "case_control"),
        }
        decision = llm.decide_visualization_strategy(
            state.get("analysis_strategy", "case_control"),
            data_characteristics,
        )
        _capture_llm_trace(state, "decide_visualization", llm.get_last_trace(), decision)
        mapped = [viz_map[t] for t in decision.get("primary_visualizations", []) if t in viz_map]
        state["visualization_plan"] = list(dict.fromkeys(always_include + mapped))
        state["log_messages"].append(
            f"可视化计划 (LLM): {', '.join(state['visualization_plan'])}"
        )
    except Exception as exc:
        state["log_messages"].append(f"可视化决策回退: {exc}")
        _capture_llm_trace(
            state,
            "decide_visualization",
            {
                "operation": "decide_visualization_strategy",
                "status": "fallback",
                "fallback_used": True,
                "error": str(exc),
                "response_text": None,
            },
        )
        extra = {
            "case_control": ["heatmap", "boxplot", "correlation"],
            "subtype_comparison": ["heatmap", "correlation"],
            "time_series": ["heatmap", "boxplot"],
            "correlation_analysis": ["correlation", "heatmap"],
        }.get(state.get("analysis_strategy", "case_control"), ["heatmap", "boxplot"])
        state["visualization_plan"] = list(dict.fromkeys(always_include + extra))
        state["log_messages"].append(
            f"可视化计划 (默认): {', '.join(state['visualization_plan'])}"
        )
    return state


def generate_plots(state: AnalysisState) -> AnalysisState:
    state["current_step"] = "generate_plots"
    state["log_messages"].append(f"[{datetime.now()}] 生成可视化图表...")

    ssgsea_scores = state.get("ssgsea_scores")
    system_scores = state.get("system_scores")
    gene_expr_df = state.get("expression_matrix")
    if not ssgsea_scores or not system_scores:
        state["log_messages"].append("无 ssGSEA 得分，跳过绘图")
        return state

    output_dir = f"results/agent_analysis/{state['dataset_id']}/figures"
    os.makedirs(output_dir, exist_ok=True)
    viz_plan = state.get("visualization_plan") or [
        "radar",
        "barplot",
        "heatmap",
        "boxplot",
        "correlation",
    ]
    if gene_expr_df is None:
        viz_plan = [v for v in viz_plan if v not in ("heatmap", "boxplot", "correlation")]
        state["log_messages"].append("无表达矩阵，跳过依赖样本数据的图表")

    try:
        from .plot_generator import generate_all_plots

        figures = generate_all_plots(
            dataset_id=state["dataset_id"],
            ssgsea_scores=ssgsea_scores,
            system_scores=system_scores,
            gene_expr_df=gene_expr_df,
            sample_metadata=state.get("sample_metadata"),
            output_dir=output_dir,
            viz_plan=viz_plan,
        )
        state["figures"] = figures
        state["log_messages"].append(f"共生成 {len(figures)} 个图表")
    except Exception as exc:
        import traceback

        state["log_messages"].append(f"绘图失败: {exc}\n{traceback.format_exc()}")
    return state


def interpret_results(state: AnalysisState) -> AnalysisState:
    return reporting_interpret_results(state, _capture_llm_trace)


def generate_report(state: AnalysisState) -> AnalysisState:
    return reporting_generate_report(state)


def export_pdf(state: AnalysisState) -> AnalysisState:
    return reporting_export_pdf(state, _write_structured_artifacts)


def handle_error(state: AnalysisState) -> AnalysisState:
    state["current_step"] = "error_handling"
    state["log_messages"].append(f"[{datetime.now()}] 处理错误...")
    if state.get("errors"):
        state["log_messages"].append(f"发现 {len(state['errors'])} 个错误:")
        for i, error in enumerate(state["errors"], 1):
            state["log_messages"].append(f"  {i}. {error}")
    if state.get("retry_count", 0) < 3:
        state["retry_count"] = state.get("retry_count", 0) + 1
        state["log_messages"].append(f"准备重试 (第 {state['retry_count']} 次)...")
    else:
        state["log_messages"].append("已达到最大重试次数，停止重试")
    return state


def should_retry(state: AnalysisState) -> str:
    if state["errors"] and state["retry_count"] < 3:
        return "retry"
    if state["errors"]:
        return "fail"
    return "continue"


def route_by_strategy(state: AnalysisState) -> str:
    strategy = state.get("analysis_strategy", "default")
    if strategy == "case_control":
        return "case_control_analysis"
    if strategy == "subtype_comparison":
        return "subtype_analysis"
    if strategy == "time_series":
        return "time_series_analysis"
    if strategy == "correlation":
        return "correlation_analysis"
    return "default_analysis"


def needs_human_review(state: AnalysisState) -> str:
    return "human_review" if state.get("needs_human_review", False) else "continue"


def create_disease_analysis_graph():
    workflow = StateGraph(AnalysisState)
    workflow.add_node("extract_metadata", _wrap_node("extract_metadata", extract_dataset_metadata))
    workflow.add_node("decide_strategy", _wrap_node("decide_strategy", decide_analysis_strategy))
    workflow.add_node("download", _wrap_node("download", download_dataset))
    workflow.add_node("preprocess", _wrap_node("preprocess", preprocess_data))
    workflow.add_node("classify", _wrap_node("classify", classify_genes))
    workflow.add_node("ssgsea", _wrap_node("ssgsea", perform_ssgsea))
    workflow.add_node("decide_visualization", _wrap_node("decide_visualization", decide_visualization))
    workflow.add_node("generate_plots", _wrap_node("generate_plots", generate_plots))
    workflow.add_node("interpret", _wrap_node("interpret", interpret_results))
    workflow.add_node("generate_report", _wrap_node("generate_report", generate_report))
    workflow.add_node("export_pdf", _wrap_node("export_pdf", export_pdf))
    workflow.add_node("error_handler", _wrap_node("error_handler", handle_error))

    workflow.set_entry_point("extract_metadata")
    workflow.add_edge("extract_metadata", "decide_strategy")
    workflow.add_conditional_edges(
        "decide_strategy",
        route_by_strategy,
        {
            "case_control_analysis": "download",
            "subtype_analysis": "download",
            "time_series_analysis": "download",
            "correlation_analysis": "download",
            "default_analysis": "download",
        },
    )
    workflow.add_conditional_edges(
        "download",
        lambda s: "preprocess" if s.get("raw_data_path") else "export_pdf",
        {"preprocess": "preprocess", "export_pdf": "export_pdf"},
    )
    workflow.add_conditional_edges(
        "preprocess",
        lambda s: "classify" if s.get("expression_matrix") is not None else "export_pdf",
        {"classify": "classify", "export_pdf": "export_pdf"},
    )
    workflow.add_edge("classify", "ssgsea")
    workflow.add_edge("ssgsea", "decide_visualization")
    workflow.add_edge("decide_visualization", "generate_plots")
    workflow.add_edge("generate_plots", "interpret")
    workflow.add_edge("interpret", "generate_report")
    workflow.add_edge("generate_report", "export_pdf")
    workflow.add_edge("export_pdf", END)
    return workflow.compile()


def run_disease_analysis(
    dataset_id: str,
    config: Optional[Dict[str, Any]] = None,
    dataset_info: Optional[Dict[str, Any]] = None,
):
    app = create_disease_analysis_graph()
    initial_state: AnalysisState = {
        "dataset_id": dataset_id,
        "dataset_info": dataset_info or {},
        "raw_data_path": None,
        "processed_data_path": None,
        "expression_matrix": None,
        "sample_metadata": None,
        "classification_results": None,
        "ssgsea_scores": None,
        "system_scores": None,
        "statistical_results": None,
        "disease_type": None,
        "analysis_strategy": None,
        "visualization_plan": [],
        "metadata": None,
        "report_content": None,
        "figures": [],
        "interpretation": None,
        "report_path": None,
        "log_messages": [],
        "errors": [],
        "current_step": "init",
        "run_id": f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{dataset_id}",
        "node_events": [],
        "llm_traces": [],
        "needs_human_review": False,
        "retry_count": 0,
    }

    print(f"开始分析数据集: {dataset_id}")
    print("=" * 80)
    final_state = initial_state
    for output in app.stream(initial_state):
        for node_name, node_output in output.items():
            final_state = node_output
            print(_safe_console_text(f"\n[{node_name}] 执行完成"))
            if node_output.get("log_messages"):
                print(_safe_console_text(f"  最新日志: {node_output['log_messages'][-1]}"))
            if node_output.get("node_events"):
                latest_event = node_output["node_events"][-1]
                print(
                    _safe_console_text(
                        f"  状态: {latest_event.get('status')} | "
                        f"耗时: {latest_event.get('duration_ms')} ms"
                    )
                )

    print("\n" + "=" * 80)
    print(_safe_console_text("分析完成！"))
    return final_state


if __name__ == "__main__":
    run_disease_analysis("GSE2034")
