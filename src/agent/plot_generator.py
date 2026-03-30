#!/usr/bin/env python3
"""Plot generation utilities for mode-aware disease analysis outputs."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .scoring_core import build_subcategory_gene_sets, compute_ssgsea_scores

logger = logging.getLogger(__name__)

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "axes.unicode_minus": False,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    }
)

SYSTEMS = ["System A", "System B", "System C", "System D", "System E"]
SYSTEM_COLORS = {
    "System A": "#E74C3C",
    "System B": "#3498DB",
    "System C": "#2ECC71",
    "System D": "#9B59B6",
    "System E": "#F39C12",
}
SUBCAT_TO_SYSTEM = {
    "A1": "System A",
    "A2": "System A",
    "A3": "System A",
    "A4": "System A",
    "B1": "System B",
    "B2": "System B",
    "B3": "System B",
    "C1": "System C",
    "C2": "System C",
    "C3": "System C",
    "D1": "System D",
    "D2": "System D",
    "E1": "System E",
    "E2": "System E",
}


def _parse_characteristics_rows(sample_metadata: Optional[Dict[str, Any]], n: int) -> List[List[str]]:
    rows = (sample_metadata or {}).get("characteristics") or []
    parsed: List[List[str]] = []
    for row in rows:
        if isinstance(row, list):
            parsed.append([str(x) for x in row if x is not None])
        elif row is not None:
            parsed.append([str(row)])
        else:
            parsed.append([])
    if n > 1 and len(parsed) == 1 and len(parsed[0]) == n:
        parsed = [[x] for x in parsed[0]]
    return parsed


def _extract_time_vector(sample_metadata: Optional[Dict[str, Any]], sample_names: List[str]) -> np.ndarray:
    rows = _parse_characteristics_rows(sample_metadata, len(sample_names))
    vals: List[float] = []
    for row in rows[: len(sample_names)]:
        text = " ".join(row).lower()
        m = re.search(r"(-?\d+(?:\.\d+)?)\s*(h|hr|hour|d|day|wk|week|month|mo)?", text)
        if not m:
            vals.append(np.nan)
            continue
        val = float(m.group(1))
        unit = (m.group(2) or "").lower()
        if unit in {"h", "hr", "hour"}:
            val /= 24.0
        elif unit in {"wk", "week"}:
            val *= 7.0
        elif unit in {"month", "mo"}:
            val *= 30.0
        vals.append(val)
    while len(vals) < len(sample_names):
        vals.append(np.nan)
    return np.array(vals[: len(sample_names)], dtype=float)


def _extract_subtype_vector(sample_metadata: Optional[Dict[str, Any]], sample_names: List[str]) -> List[str]:
    rows = _parse_characteristics_rows(sample_metadata, len(sample_names))
    labels: List[str] = []
    for row in rows[: len(sample_names)]:
        text = " ".join(row).lower()
        m = re.search(r"(?:subtype|cluster|class|group)\s*[:=]\s*([a-z0-9_\-]+)", text)
        labels.append(m.group(1) if m else "unknown")
    while len(labels) < len(sample_names):
        labels.append("unknown")
    return labels[: len(sample_names)]


def _extract_trait_vector(sample_metadata: Optional[Dict[str, Any]], sample_names: List[str]) -> Tuple[Optional[str], np.ndarray]:
    candidates = ["age", "score", "bmi", "hba1c", "nihss", "mmse", "severity"]
    rows = _parse_characteristics_rows(sample_metadata, len(sample_names))
    for trait in candidates:
        vals: List[float] = []
        hits = 0
        for row in rows[: len(sample_names)]:
            text = " ".join(row).lower()
            if trait not in text:
                vals.append(np.nan)
                continue
            m = re.search(r"(-?\d+(?:\.\d+)?)", text)
            if not m:
                vals.append(np.nan)
                continue
            vals.append(float(m.group(1)))
            hits += 1
        if hits >= 6:
            while len(vals) < len(sample_names):
                vals.append(np.nan)
            return trait, np.array(vals[: len(sample_names)], dtype=float)
    return None, np.array([np.nan] * len(sample_names), dtype=float)


def _resolve_plot_alias(viz: str) -> str:
    alias = {
        "grouped_subtype_boxplot": "subtype_boxplot",
        "trait_scatter_plot": "trait_scatter",
        "expected_vs_observed_barplot": "expected_vs_observed",
        "system_correlation_matrix": "correlation",
    }
    return alias.get(viz, viz)


def _compute_subcat_sample_scores(gene_expr_df: pd.DataFrame, focus_subcategories: Optional[List[str]] = None) -> Dict[str, np.ndarray]:
    gene_sets = build_subcategory_gene_sets()
    all_codes = list(gene_sets.keys())
    target_codes = [c for c in (focus_subcategories or []) if c in gene_sets]
    if not target_codes:
        target_codes = all_codes
    out: Dict[str, np.ndarray] = {}
    expr_genes = set(gene_expr_df.index)
    for code in target_codes:
        matched = list(set(gene_sets[code]) & expr_genes)
        if len(matched) < 5:
            continue
        out[code] = compute_ssgsea_scores(gene_expr_df, matched)
    return out


def _system_sample_scores(subcat_sample_scores: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    by_system: Dict[str, List[np.ndarray]] = {k: [] for k in SYSTEMS}
    for code, vec in subcat_sample_scores.items():
        system = SUBCAT_TO_SYSTEM.get(code)
        if system:
            by_system[system].append(vec)
    out: Dict[str, np.ndarray] = {}
    for system, vectors in by_system.items():
        if vectors:
            out[system] = np.mean(np.vstack(vectors), axis=0)
    return out


def generate_all_plots(
    dataset_id: str,
    ssgsea_scores: Dict[str, Any],
    system_scores: Dict[str, float],
    gene_expr_df,
    sample_metadata: Optional[Dict] = None,
    statistical_results: Optional[Dict[str, Any]] = None,
    focus_subcategories: Optional[List[str]] = None,
    output_dir: str = None,
    viz_plan: List[str] = None,
) -> List[str]:
    if output_dir is None:
        output_dir = f"results/agent_analysis/{dataset_id}/figures"
    os.makedirs(output_dir, exist_ok=True)
    if viz_plan is None:
        viz_plan = ["radar", "heatmap", "boxplot", "barplot", "correlation"]

    subcat_means = {code: info["mean_score"] for code, info in (ssgsea_scores or {}).items()}
    figures: List[str] = []

    for viz in viz_plan:
        resolved = _resolve_plot_alias(viz)
        try:
            path = None
            if resolved == "radar" and system_scores:
                path = plot_radar(system_scores, dataset_id, output_dir)
            elif resolved == "barplot" and subcat_means:
                path = plot_subcat_barplot(subcat_means, dataset_id, output_dir)
            elif resolved == "heatmap" and gene_expr_df is not None:
                path = plot_subcat_heatmap(gene_expr_df, dataset_id, output_dir, focus_subcategories)
            elif resolved == "boxplot" and gene_expr_df is not None:
                path = plot_system_boxplot(gene_expr_df, dataset_id, output_dir)
            elif resolved == "correlation" and gene_expr_df is not None:
                path = plot_system_correlation(gene_expr_df, dataset_id, output_dir)
            elif resolved == "time_series_system" and gene_expr_df is not None:
                path = plot_time_series_system(gene_expr_df, sample_metadata, dataset_id, output_dir)
            elif resolved == "time_series_subcategory" and gene_expr_df is not None:
                path = plot_time_series_subcategory(gene_expr_df, sample_metadata, dataset_id, output_dir, focus_subcategories)
            elif resolved == "subtype_boxplot" and gene_expr_df is not None:
                path = plot_grouped_subtype_boxplot(gene_expr_df, sample_metadata, dataset_id, output_dir, focus_subcategories)
            elif resolved == "trait_scatter" and gene_expr_df is not None:
                path = plot_trait_scatter(gene_expr_df, sample_metadata, dataset_id, output_dir, focus_subcategories)
            elif resolved == "expected_vs_observed" and system_scores:
                path = plot_expected_vs_observed_bar(system_scores, statistical_results or {}, dataset_id, output_dir)
            elif resolved == "heterogeneity_heatmap" and gene_expr_df is not None:
                path = plot_heterogeneity_heatmap(gene_expr_df, dataset_id, output_dir, focus_subcategories)
            if path:
                figures.append(path)
                logger.info("generated figure: %s", Path(path).name)
        except Exception as exc:
            message = str(exc).lower()
            if "insufficient" in message or "no " in message:
                logger.info("skip optional plot %s: %s", viz, exc)
            else:
                logger.warning("failed generating %s: %s", viz, exc)

    if len(figures) < 4:
        backfill = ["radar", "barplot", "heatmap", "boxplot", "correlation"]
        existing = {_resolve_plot_alias(v) for v in viz_plan}
        for viz in backfill:
            if viz in existing:
                continue
            try:
                path = None
                if viz == "radar" and system_scores:
                    path = plot_radar(system_scores, dataset_id, output_dir)
                elif viz == "barplot" and subcat_means:
                    path = plot_subcat_barplot(subcat_means, dataset_id, output_dir)
                elif viz == "heatmap" and gene_expr_df is not None:
                    path = plot_subcat_heatmap(gene_expr_df, dataset_id, output_dir, focus_subcategories)
                elif viz == "boxplot" and gene_expr_df is not None:
                    path = plot_system_boxplot(gene_expr_df, dataset_id, output_dir)
                elif viz == "correlation" and gene_expr_df is not None:
                    path = plot_system_correlation(gene_expr_df, dataset_id, output_dir)
                if path and path not in figures:
                    figures.append(path)
                if len(figures) >= 4:
                    break
            except Exception:
                continue
    return figures


def plot_radar(system_scores: Dict[str, float], dataset_id: str, output_dir: str) -> str:
    values = [system_scores.get(s, 0.0) for s in SYSTEMS]
    vmax = max(abs(v) for v in values) or 1.0
    norm = [v / vmax for v in values] + [values[0] / vmax]
    angles = np.linspace(0, 2 * np.pi, len(SYSTEMS), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    ax.plot(angles, norm, "o-", linewidth=2, color="#E74C3C")
    ax.fill(angles, norm, alpha=0.25, color="#E74C3C")
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(["A", "B", "C", "D", "E"], fontsize=12)
    ax.set_ylim(-1.0, 1.0)
    ax.set_title(f"{dataset_id} | Five-System Radar", fontsize=13, fontweight="bold")
    path = os.path.join(output_dir, "radar_system_scores.png")
    plt.savefig(path)
    plt.close()
    return path


def plot_subcat_barplot(subcat_means: Dict[str, float], dataset_id: str, output_dir: str) -> str:
    ranked = sorted(subcat_means.items(), key=lambda kv: kv[1], reverse=True)
    labels = [k for k, _ in ranked]
    values = [v for _, v in ranked]
    colors = [SYSTEM_COLORS.get(SUBCAT_TO_SYSTEM.get(code, ""), "#888888") for code in labels]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(labels, values, color=colors)
    ax.invert_yaxis()
    ax.axvline(0.0, color="black", linewidth=0.8)
    ax.set_title(f"{dataset_id} | Subcategory Ranking", fontsize=13, fontweight="bold")
    ax.set_xlabel("Mean ssGSEA score")
    path = os.path.join(output_dir, "barplot_subcat_ranking.png")
    plt.savefig(path)
    plt.close()
    return path


def plot_subcat_heatmap(
    gene_expr_df: pd.DataFrame, dataset_id: str, output_dir: str, focus_subcategories: Optional[List[str]]
) -> str:
    scores = _compute_subcat_sample_scores(gene_expr_df, focus_subcategories)
    if not scores:
        raise ValueError("no subcategory score available for heatmap")
    df = pd.DataFrame(scores, index=gene_expr_df.columns).T
    fig, ax = plt.subplots(figsize=(max(12, len(df.columns) * 0.15 + 4), 7))
    sns.heatmap(df, cmap="RdBu_r", center=0, linewidths=0, cbar_kws={"shrink": 0.6}, ax=ax)
    ax.set_title(f"{dataset_id} | Subcategory Heatmap", fontsize=13, fontweight="bold")
    ax.set_xlabel("Samples")
    ax.set_ylabel("Subcategory")
    path = os.path.join(output_dir, "heatmap_subcat_ssgsea.png")
    plt.savefig(path)
    plt.close()
    return path


def plot_system_boxplot(gene_expr_df: pd.DataFrame, dataset_id: str, output_dir: str) -> str:
    subcat_scores = _compute_subcat_sample_scores(gene_expr_df)
    sys_scores = _system_sample_scores(subcat_scores)
    rows = []
    for system, vals in sys_scores.items():
        for v in vals:
            rows.append({"System": system, "Score": float(v)})
    if not rows:
        raise ValueError("no system score available for boxplot")
    df = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.violinplot(data=df, x="System", y="Score", hue="System", palette=SYSTEM_COLORS, inner="box", legend=False, ax=ax)
    sns.stripplot(data=df, x="System", y="Score", color="black", alpha=0.15, size=2, jitter=True, ax=ax)
    ax.axhline(0.0, color="gray", linestyle="--", linewidth=0.8)
    ax.set_title(f"{dataset_id} | System Distribution", fontsize=13, fontweight="bold")
    path = os.path.join(output_dir, "boxplot_system_scores.png")
    plt.savefig(path)
    plt.close()
    return path


def plot_system_correlation(gene_expr_df: pd.DataFrame, dataset_id: str, output_dir: str) -> str:
    subcat_scores = _compute_subcat_sample_scores(gene_expr_df)
    sys_scores = _system_sample_scores(subcat_scores)
    df = pd.DataFrame(sys_scores)
    if df.shape[1] < 2 or df.shape[0] < 3:
        raise ValueError("insufficient system/sample coverage for correlation heatmap")
    corr = df.corr()
    if corr.shape[0] < 2:
        raise ValueError("correlation matrix has fewer than 2 systems")
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(corr, cmap="RdBu_r", center=0, vmin=-1, vmax=1, annot=True, fmt=".2f", square=True, ax=ax)
    ax.set_title(f"{dataset_id} | Inter-System Correlation", fontsize=13, fontweight="bold")
    path = os.path.join(output_dir, "correlation_system_scores.png")
    plt.savefig(path)
    plt.close()
    return path


def plot_time_series_system(gene_expr_df: pd.DataFrame, sample_metadata: Optional[Dict[str, Any]], dataset_id: str, output_dir: str) -> str:
    sample_names = list(gene_expr_df.columns)
    t = _extract_time_vector(sample_metadata, sample_names)
    valid = np.isfinite(t)
    if valid.sum() < 6 or len(np.unique(t[valid])) < 3:
        raise ValueError("insufficient timepoint metadata")
    subcat_scores = _compute_subcat_sample_scores(gene_expr_df)
    sys_scores = _system_sample_scores(subcat_scores)
    uniq = np.unique(t[valid])
    fig, ax = plt.subplots(figsize=(8, 5))
    for system, vals in sys_scores.items():
        vals = np.array(vals, dtype=float)
        means = [float(np.mean(vals[(t == tp) & valid])) for tp in uniq]
        ax.plot(uniq, means, marker="o", label=system, color=SYSTEM_COLORS.get(system))
    ax.set_xlabel("Time")
    ax.set_ylabel("Mean score")
    ax.set_title(f"{dataset_id} | Time Series (System)", fontsize=13, fontweight="bold")
    ax.legend(fontsize=8)
    path = os.path.join(output_dir, "time_series_system.png")
    plt.savefig(path)
    plt.close()
    return path


def plot_time_series_subcategory(
    gene_expr_df: pd.DataFrame,
    sample_metadata: Optional[Dict[str, Any]],
    dataset_id: str,
    output_dir: str,
    focus_subcategories: Optional[List[str]],
) -> str:
    sample_names = list(gene_expr_df.columns)
    t = _extract_time_vector(sample_metadata, sample_names)
    valid = np.isfinite(t)
    if valid.sum() < 6 or len(np.unique(t[valid])) < 3:
        raise ValueError("insufficient timepoint metadata")
    subcat_scores = _compute_subcat_sample_scores(gene_expr_df, focus_subcategories)
    if not subcat_scores:
        raise ValueError("no subcategory score for time-series plot")
    top_codes = list(subcat_scores.keys())[:5]
    uniq = np.unique(t[valid])
    fig, ax = plt.subplots(figsize=(8, 5))
    for code in top_codes:
        vals = np.array(subcat_scores[code], dtype=float)
        means = [float(np.mean(vals[(t == tp) & valid])) for tp in uniq]
        ax.plot(uniq, means, marker="o", label=code)
    ax.set_xlabel("Time")
    ax.set_ylabel("Mean score")
    ax.set_title(f"{dataset_id} | Time Series (Subcategory)", fontsize=13, fontweight="bold")
    ax.legend(fontsize=8, ncol=2)
    path = os.path.join(output_dir, "time_series_subcategory.png")
    plt.savefig(path)
    plt.close()
    return path


def plot_grouped_subtype_boxplot(
    gene_expr_df: pd.DataFrame,
    sample_metadata: Optional[Dict[str, Any]],
    dataset_id: str,
    output_dir: str,
    focus_subcategories: Optional[List[str]],
) -> str:
    sample_names = list(gene_expr_df.columns)
    subtype = np.array(_extract_subtype_vector(sample_metadata, sample_names))
    groups = [g for g, c in pd.Series(subtype).value_counts().items() if g != "unknown" and c >= 2]
    if len(groups) < 2:
        raise ValueError("insufficient subtype metadata")
    scores = _compute_subcat_sample_scores(gene_expr_df, focus_subcategories)
    if not scores:
        raise ValueError("no scores for subtype plot")
    code = list(scores.keys())[0]
    vals = np.array(scores[code], dtype=float)
    rows = [{"Subtype": subtype[i], "Score": float(vals[i])} for i in range(len(vals)) if subtype[i] in groups]
    df = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.boxplot(data=df, x="Subtype", y="Score", hue="Subtype", legend=False, ax=ax)
    sns.stripplot(data=df, x="Subtype", y="Score", color="black", alpha=0.2, size=2, jitter=True, ax=ax)
    ax.set_title(f"{dataset_id} | Subtype Boxplot ({code})", fontsize=13, fontweight="bold")
    path = os.path.join(output_dir, "grouped_subtype_boxplot.png")
    plt.savefig(path)
    plt.close()
    return path


def plot_trait_scatter(
    gene_expr_df: pd.DataFrame,
    sample_metadata: Optional[Dict[str, Any]],
    dataset_id: str,
    output_dir: str,
    focus_subcategories: Optional[List[str]],
) -> str:
    sample_names = list(gene_expr_df.columns)
    trait_name, x = _extract_trait_vector(sample_metadata, sample_names)
    valid = np.isfinite(x)
    if trait_name is None or valid.sum() < 6:
        raise ValueError("insufficient continuous trait metadata")
    scores = _compute_subcat_sample_scores(gene_expr_df, focus_subcategories)
    if not scores:
        raise ValueError("no scores for trait scatter")
    code = list(scores.keys())[0]
    y = np.array(scores[code], dtype=float)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(x[valid], y[valid], alpha=0.8, color="#2C3E50")
    if valid.sum() >= 3:
        p = np.polyfit(x[valid], y[valid], 1)
        xline = np.linspace(np.nanmin(x[valid]), np.nanmax(x[valid]), 50)
        ax.plot(xline, p[0] * xline + p[1], color="#E74C3C")
    ax.set_xlabel(trait_name)
    ax.set_ylabel(f"{code} score")
    ax.set_title(f"{dataset_id} | Trait Association", fontsize=13, fontweight="bold")
    path = os.path.join(output_dir, "trait_scatter_plot.png")
    plt.savefig(path)
    plt.close()
    return path


def plot_expected_vs_observed_bar(
    system_scores: Dict[str, float],
    statistical_results: Dict[str, Any],
    dataset_id: str,
    output_dir: str,
) -> str:
    evo = (statistical_results or {}).get("expected_vs_observed") or {}
    expected = set(evo.get("expected_systems") or [])
    labels = SYSTEMS
    values = [system_scores.get(s, 0.0) for s in labels]
    colors = ["#2ECC71" if s in expected else "#95A5A6" for s in labels]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(labels, values, color=colors)
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.tick_params(axis="x", rotation=20)
    ax.set_ylabel("System score")
    ax.set_title(f"{dataset_id} | Expected vs Observed", fontsize=13, fontweight="bold")
    path = os.path.join(output_dir, "expected_vs_observed_barplot.png")
    plt.savefig(path)
    plt.close()
    return path


def plot_heterogeneity_heatmap(
    gene_expr_df: pd.DataFrame,
    dataset_id: str,
    output_dir: str,
    focus_subcategories: Optional[List[str]],
) -> str:
    scores = _compute_subcat_sample_scores(gene_expr_df, focus_subcategories)
    if not scores:
        raise ValueError("no scores for heterogeneity heatmap")
    var_rank = sorted(scores.items(), key=lambda kv: np.var(kv[1]), reverse=True)
    top = dict(var_rank[:8])
    df = pd.DataFrame(top, index=gene_expr_df.columns).T
    fig, ax = plt.subplots(figsize=(max(10, len(df.columns) * 0.15 + 4), 6))
    sns.heatmap(df, cmap="vlag", center=0, linewidths=0, cbar_kws={"shrink": 0.6}, ax=ax)
    ax.set_title(f"{dataset_id} | Heterogeneity Heatmap", fontsize=13, fontweight="bold")
    ax.set_xlabel("Samples")
    ax.set_ylabel("High-variance subcategories")
    path = os.path.join(output_dir, "heterogeneity_heatmap.png")
    plt.savefig(path)
    plt.close()
    return path
