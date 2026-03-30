#!/usr/bin/env python3
"""Scoring-oriented analysis nodes for the active disease analysis pipeline."""

from datetime import datetime
from typing import Any, Dict

import numpy as np

from .scoring_core import (
    SUBCATEGORY_NAMES,
    SUBCATEGORY_TO_SYSTEM,
    build_subcategory_gene_sets,
    compute_ssgsea_scores,
)


def classify_genes(state: Dict[str, Any]) -> Dict[str, Any]:
    """Count expressed genes covered by the 14 subcategory gene sets."""
    state["current_step"] = "classify"
    state["log_messages"].append(f"[{datetime.now()}] 执行五大系统分类...")

    gene_expr_df = state.get("expression_matrix")
    if gene_expr_df is None:
        state["errors"].append("无表达矩阵，跳过分类")
        return state

    try:
        gene_sets = build_subcategory_gene_sets()
        expressed_genes = set(gene_expr_df.index)

        system_counts = {f"System {s}": 0 for s in "ABCDE"}
        subcategory_counts = {}
        classified_genes = set()

        for code, genes in gene_sets.items():
            matched = expressed_genes & set(genes)
            subcategory_counts[code] = len(matched)
            classified_genes.update(matched)
            system = SUBCATEGORY_TO_SYSTEM.get(code)
            if system:
                system_counts[system] += len(matched)

        state["classification_results"] = {
            "total_genes": len(expressed_genes),
            "classified": len(classified_genes),
            "unclassified": len(expressed_genes) - len(classified_genes),
            "system_counts": system_counts,
            "subcategory_counts": subcategory_counts,
        }

        state["log_messages"].append(
            f"分类完成: {len(classified_genes)}/{len(expressed_genes)} 基因匹配到基因集"
        )
        for system_name, count in system_counts.items():
            state["log_messages"].append(f"  {system_name}: {count} 基因")
    except Exception as exc:
        state["errors"].append(f"分类失败: {exc}")
        state["log_messages"].append(f"分类失败: {exc}")

    return state


def perform_ssgsea(state: Dict[str, Any]) -> Dict[str, Any]:
    """Compute ssGSEA scores for all subcategories and systems."""
    state["current_step"] = "ssgsea"
    state["log_messages"].append(f"[{datetime.now()}] 执行 ssGSEA 分析...")

    gene_expr_df = state.get("expression_matrix")
    if gene_expr_df is None:
        state["errors"].append("无表达矩阵，跳过 ssGSEA")
        return state

    try:
        gene_sets = build_subcategory_gene_sets()
        gene_sets = {code: genes for code, genes in gene_sets.items() if len(genes) >= 5}

        available_genes = set(gene_expr_df.index)
        ssgsea_scores = {}
        system_score_lists: Dict[str, list] = {f"System {s}": [] for s in "ABCDE"}

        for code, gene_list in gene_sets.items():
            matched = list(set(gene_list) & available_genes)
            scores = compute_ssgsea_scores(gene_expr_df, matched)
            mean_score = float(np.mean(scores))

            ssgsea_scores[code] = {
                "mean_score": mean_score,
                "std_score": float(np.std(scores)),
                "median_score": float(np.median(scores)),
                "name": SUBCATEGORY_NAMES.get(code, code),
                "gene_count": len(gene_list),
                "matched_genes": len(matched),
            }
            system = SUBCATEGORY_TO_SYSTEM.get(code)
            if system:
                system_score_lists[system].append(mean_score)

        total_matched = sum(v.get("matched_genes", 0) for v in ssgsea_scores.values())
        if total_matched == 0:
            state["errors"].append(
                "ssGSEA matched_genes are all zero; this usually indicates missing/incorrect probe-to-gene mapping"
            )
            hint = (
                (state.get("metadata") or {}).get("matrix_identifier_type")
                if isinstance(state.get("metadata"), dict)
                else None
            )
            state["log_messages"].append(
                "ssGSEA stop: all subcategories have 0 matched genes; "
                f"matrix_identifier_type={hint}"
            )
            return state

        system_scores = {
            system: float(np.mean(values)) if values else 0.0
            for system, values in system_score_lists.items()
        }

        state["ssgsea_scores"] = ssgsea_scores
        state["system_scores"] = system_scores

        state["log_messages"].append(f"ssGSEA 完成: {len(ssgsea_scores)} 个子类")
        for system_name, score in sorted(system_scores.items()):
            state["log_messages"].append(f"  {system_name}: {score:.4f}")
    except Exception as exc:
        import traceback

        state["errors"].append(f"ssGSEA 失败: {exc}")
        state["log_messages"].append(f"ssGSEA 失败: {exc}\n{traceback.format_exc()}")

    return state
