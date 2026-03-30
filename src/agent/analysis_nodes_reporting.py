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
    state["log_messages"].append(f"[{datetime.now()}] interpreting results...")

    try:
        from .llm_client import create_llm_integration

        llm = create_llm_integration()
        dataset_info = {
            "dataset_id": state["dataset_id"],
            **state.get("dataset_info", {}),
            "analysis_mode": state.get("analysis_mode"),
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
        state["log_messages"].append("LLM interpretation completed")
    except Exception as exc:
        state["log_messages"].append(f"LLM interpretation fallback: {exc}")
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
            "# Analysis Interpretation\n\n"
            f"- Dataset: {state.get('dataset_id', 'Unknown')}\n"
            f"- Strategy: {state.get('analysis_strategy', 'Unknown')}\n"
            f"- Mode: {state.get('analysis_mode', 'Unknown')}\n\n"
            "Automated interpretation is currently unavailable. "
            "Please review system and subcategory score summaries manually.\n"
        )

    return state


def generate_report(state: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble the markdown report body."""
    state["current_step"] = "generate_report"
    state["log_messages"].append(f"[{datetime.now()}] generating report...")

    dataset_info = state.get("dataset_info", {})
    ssgsea_scores = state.get("ssgsea_scores", {})
    system_scores = state.get("system_scores", {})
    classification_results = state.get("classification_results", {})
    statistical_results = state.get("statistical_results", {})
    mode_specific_results = state.get("mode_specific_results", {})

    report_content = f"""# {dataset_info.get('chinese_name', dataset_info.get('name', state['dataset_id']))} Analysis Report

**Dataset ID**: {state['dataset_id']}  
**Disease Type**: {state.get('disease_type', 'Unknown')}  
**Analysis Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Analysis Strategy**: {state.get('analysis_strategy', 'Unknown')}  
**Analysis Mode**: {state.get('analysis_mode', 'Unknown')}

---

## 1. Dataset Overview
- **Name**: {dataset_info.get('name', 'Unknown')}
- **Chinese Name**: {dataset_info.get('chinese_name', 'Unknown')}
- **Description**: {dataset_info.get('description', 'Unknown')}
- **Expected Systems**: {', '.join(dataset_info.get('expected_systems', []))}

## 2. Data Processing Summary
- **Sample Count**: {(state.get('sample_metadata') or {}).get('sample_count', 'Unknown')}
- **Total Genes**: {(classification_results or {}).get('total_genes', 'Unknown')}
- **Classified Genes**: {(classification_results or {}).get('classified', 'Unknown')}

## 3. Five-System Classification Summary
"""

    for system, count in classification_results.get("system_counts", {}).items():
        report_content += f"- **{system}**: {count} genes\n"

    report_content += "\n### Top Subcategory Counts\n"
    for subcat, count in list(classification_results.get("subcategory_counts", {}).items())[:10]:
        report_content += f"- **{subcat}**: {count} genes\n"

    report_content += "\n## 4. ssGSEA System Scores\n"
    for system, score in system_scores.items():
        report_content += f"- **{system}**: {score:.3f}\n"

    report_content += "\n### Top 5 Subcategory Scores\n"
    sorted_subcats = sorted(
        ssgsea_scores.items(),
        key=lambda item: item[1]["mean_score"],
        reverse=True,
    )[:5]
    for code, info in sorted_subcats:
        report_content += f"- **{code} ({info['name']})**: {info['mean_score']:.3f}\n"

    report_content += "\n## 5. Mode-Specific Statistics\n"
    report_content += f"- **Focus Subcategories**: {', '.join(state.get('focus_subcategories', [])[:12]) or 'None'}\n"
    report_content += f"- **Focus Systems**: {', '.join(state.get('focus_systems', [])) or 'None'}\n"
    report_content += (
        f"- **Analysis Design**: {json.dumps(state.get('analysis_design') or {}, ensure_ascii=False)}\n"
    )
    report_content += (
        f"- **Statistical Summary**: {json.dumps(statistical_results, ensure_ascii=False)[:2000]}\n"
    )
    report_content += (
        f"- **Mode Result**: {json.dumps(mode_specific_results, ensure_ascii=False)[:2000]}\n"
    )

    report_content += "\n## 6. Cross-Cutting Findings\n"
    report_content += (
        f"- **Expected vs Observed**: {json.dumps((statistical_results or {}).get('expected_vs_observed', {}), ensure_ascii=False)[:1200]}\n"
    )
    report_content += (
        f"- **System Coordination**: {json.dumps((statistical_results or {}).get('system_coordination', {}), ensure_ascii=False)[:1200]}\n"
    )
    report_content += (
        f"- **Heterogeneity**: {json.dumps((statistical_results or {}).get('heterogeneity_summary', {}), ensure_ascii=False)[:1200]}\n"
    )
    report_content += (
        f"- **Paired Summary**: {json.dumps((statistical_results or {}).get('paired_summary', {}), ensure_ascii=False)[:1200]}\n"
    )
    report_content += (
        f"- **Response Stratification**: {json.dumps((statistical_results or {}).get('response_summary', {}), ensure_ascii=False)[:1200]}\n"
    )
    report_content += (
        f"- **Severity Progression**: {json.dumps((statistical_results or {}).get('severity_summary', {}), ensure_ascii=False)[:1200]}\n"
    )

    report_content += "\n## 7. Interpretation\n\n"
    interpretation = state.get("interpretation", "")
    report_content += interpretation if interpretation else "Interpretation pending.\n"

    report_content += "\n## 8. Figures\n"
    for i, fig_path in enumerate(state.get("figures", []), 1):
        report_content += f"{i}. {fig_path}\n"

    report_content += "\n---\n\n*Generated by the disease analysis agent pipeline.*\n"

    state["report_content"] = report_content
    state["log_messages"].append("report generated")
    state["log_messages"].append(f"report length: {len(report_content)} chars")
    return state


def export_pdf(
    state: Dict[str, Any],
    write_structured_artifacts: Callable[[Dict[str, Any], str], Dict[str, str]],
) -> Dict[str, Any]:
    """Persist report and structured run artifacts."""
    state["current_step"] = "export_pdf"
    state["log_messages"].append(f"[{datetime.now()}] exporting report and summary...")

    output_dir = f"results/agent_analysis/{state['dataset_id']}"
    os.makedirs(output_dir, exist_ok=True)

    report_path = os.path.join(output_dir, f"{state['dataset_id']}_report.md")
    report_content = state.get("report_content")
    if not report_content:
        errors = state.get("errors", [])
        error_lines = "\n".join(f"- {error}" for error in errors) if errors else "- no detailed errors"
        report_content = f"""# {state['dataset_id']} Analysis Report

Analysis did not complete successfully. A failure summary is provided below.

## Dataset
- ID: {state['dataset_id']}
- Name: {state.get('dataset_info', {}).get('chinese_name', state['dataset_id'])}
- Disease Type: {state.get('disease_type', 'unknown')}

## Failed Step
- Current Step: {state.get('current_step', 'unknown')}

## Errors
{error_lines}
"""
        state["report_content"] = report_content

    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(report_content)

    state["report_path"] = report_path
    state["log_messages"].append(f"report saved: {report_path}")
    state["log_messages"].append(f"report size: {len(report_content)} bytes")

    summary_path = os.path.join(output_dir, "analysis_summary.json")
    summary = {
        "run_id": state.get("run_id"),
        "dataset_id": state["dataset_id"],
        "dataset_name": state.get("dataset_info", {}).get("chinese_name", "Unknown"),
        "disease_type": state.get("disease_type", "Unknown"),
        "analysis_strategy": state.get("analysis_strategy", "Unknown"),
        "analysis_mode": state.get("analysis_mode"),
        "analysis_design": state.get("analysis_design"),
        "grouping_info": state.get("grouping_info"),
        "analysis_time": datetime.now().isoformat(),
        "classification_results": state.get("classification_results", {}),
        "system_scores": state.get("system_scores", {}),
        "statistical_results": state.get("statistical_results", {}),
        "focus_subcategories": state.get("focus_subcategories", []),
        "focus_systems": state.get("focus_systems", []),
        "plot_plan": state.get("plot_plan", {}),
        "mode_specific_results": state.get("mode_specific_results", {}),
        "expected_vs_observed": (state.get("statistical_results") or {}).get("expected_vs_observed", {}),
        "coordination_summary": (state.get("statistical_results") or {}).get("system_coordination", {}),
        "heterogeneity_summary": (state.get("statistical_results") or {}).get("heterogeneity_summary", {}),
        "paired_summary": (state.get("statistical_results") or {}).get("paired_summary", {}),
        "response_summary": (state.get("statistical_results") or {}).get("response_summary", {}),
        "severity_summary": (state.get("statistical_results") or {}).get("severity_summary", {}),
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

    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    state["log_messages"].append(f"summary saved: {summary_path}")

    artifact_paths = write_structured_artifacts(state, output_dir)
    state.setdefault("metadata", {})
    state["metadata"]["structured_artifacts"] = artifact_paths
    state["log_messages"].append(f"structured logs saved: {artifact_paths['run_log_path']}")
    return state
