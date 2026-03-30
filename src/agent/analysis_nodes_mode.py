#!/usr/bin/env python3
"""Mode-aware analysis nodes for strategy detection, statistics, and plot planning."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .scoring_core import SUBCATEGORY_TO_SYSTEM, build_subcategory_gene_sets, compute_ssgsea_scores


SUPPORTED_MODES = {
    "case_control",
    "time_series",
    "subtype_comparison",
    "continuous_trait_association",
    "unsupervised_pattern_discovery",
}

TRAIT_KEYS = ("age", "bmi", "score", "hba1c", "crp", "esr", "nihss", "mmse", "severity")
TIME_KEYS = ("time", "timepoint", "day", "hour", "week", "month")
SUBTYPE_KEYS = ("subtype", "cluster", "phenotype", "class", "group")


def _to_text_blocks(sample_metadata: Optional[Dict[str, Any]]) -> List[str]:
    if not sample_metadata:
        return []
    blocks: List[str] = []
    for key in ("titles", "accessions"):
        blocks.extend([str(x) for x in (sample_metadata.get(key) or []) if x is not None])
    for row in (sample_metadata.get("characteristics") or []):
        if isinstance(row, list):
            blocks.extend([str(x) for x in row if x is not None])
        elif row is not None:
            blocks.append(str(row))
    return blocks


def _sample_count(sample_metadata: Optional[Dict[str, Any]]) -> int:
    return int((sample_metadata or {}).get("sample_count") or 0)


def _parse_characteristics_rows(sample_metadata: Optional[Dict[str, Any]]) -> List[List[str]]:
    rows = (sample_metadata or {}).get("characteristics") or []
    parsed: List[List[str]] = []
    for row in rows:
        if isinstance(row, list):
            parsed.append([str(v) for v in row if v is not None])
        elif row is not None:
            parsed.append([str(row)])
        else:
            parsed.append([])
    # Some datasets/scripts store characteristics as one long row with length == sample_count.
    # Normalize this shape into per-sample rows to keep downstream grouping logic stable.
    sample_count = _sample_count(sample_metadata)
    if sample_count > 1 and len(parsed) == 1 and len(parsed[0]) == sample_count:
        parsed = [[item] for item in parsed[0]]
    return parsed


def _parse_key_values_from_row(row: List[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for item in row:
        text = item.strip()
        if ":" in text:
            key, value = text.split(":", 1)
            out[key.strip().lower()] = value.strip()
        elif "=" in text:
            key, value = text.split("=", 1)
            out[key.strip().lower()] = value.strip()
    return out


def _extract_numeric_value(text: str) -> Optional[float]:
    m = re.search(r"(-?\d+(?:\.\d+)?)", text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def _extract_time_value(text: str) -> Optional[float]:
    lower = text.lower()
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*(h|hr|hour|d|day|wk|week|month|mo)?", lower)
    if not m:
        return None
    try:
        val = float(m.group(1))
    except Exception:
        return None
    unit = (m.group(2) or "").lower()
    if unit in {"h", "hr", "hour"}:
        return val / 24.0
    if unit in {"wk", "week"}:
        return val * 7.0
    if unit in {"month", "mo"}:
        return val * 30.0
    return val


def _normalize_group_label(text: str) -> str:
    lower = text.lower()
    if any(k in lower for k in ("control", "healthy", "normal", "wt", "wild type")):
        return "control"
    if any(k in lower for k in ("disease", "patient", "tumor", "case")):
        return "disease"
    return re.sub(r"\s+", "_", lower)[:40] if lower else "unknown"


def _extract_group_vector(sample_metadata: Optional[Dict[str, Any]]) -> List[str]:
    rows = _parse_characteristics_rows(sample_metadata)
    labels: List[str] = []
    for row in rows:
        kv = _parse_key_values_from_row(row)
        label = None
        for key in ("group", "condition", "status", "phenotype", "diagnosis"):
            if key in kv and kv[key]:
                label = _normalize_group_label(kv[key])
                break
        if not label:
            merged = " ".join(row)
            label = _normalize_group_label(merged) if merged else "unknown"
        labels.append(label)
    return labels


def _extract_subtype_vector(sample_metadata: Optional[Dict[str, Any]]) -> List[str]:
    rows = _parse_characteristics_rows(sample_metadata)
    labels: List[str] = []
    for row in rows:
        kv = _parse_key_values_from_row(row)
        subtype = None
        for key, value in kv.items():
            if any(tag in key for tag in SUBTYPE_KEYS):
                subtype = re.sub(r"\s+", "_", value.lower())[:40]
                break
        labels.append(subtype or "unknown")
    return labels


def _extract_time_vector(sample_metadata: Optional[Dict[str, Any]]) -> List[float]:
    rows = _parse_characteristics_rows(sample_metadata)
    values: List[float] = []
    for row in rows:
        kv = _parse_key_values_from_row(row)
        time_value: Optional[float] = None
        for key, value in kv.items():
            if any(tag in key for tag in TIME_KEYS):
                time_value = _extract_time_value(value)
                if time_value is not None:
                    break
        if time_value is None:
            joined = " ".join(row)
            if re.search(r"\btime\b|\bday\b|\bhour\b|\bweek\b|\bmonth\b", joined.lower()):
                time_value = _extract_time_value(joined)
        values.append(time_value if time_value is not None else float("nan"))
    return values


def _extract_continuous_trait(sample_metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    rows = _parse_characteristics_rows(sample_metadata)
    best_key = None
    best_values: List[float] = []
    for trait_key in TRAIT_KEYS:
        trait_values: List[float] = []
        hits = 0
        for row in rows:
            kv = _parse_key_values_from_row(row)
            found = None
            for key, value in kv.items():
                if trait_key in key:
                    found = _extract_numeric_value(value)
                    break
            if found is None:
                joined = " ".join(row).lower()
                if trait_key in joined:
                    found = _extract_numeric_value(joined)
            if found is None:
                trait_values.append(float("nan"))
            else:
                hits += 1
                trait_values.append(found)
        if hits >= 6:
            best_key = trait_key
            best_values = trait_values
            break
    return {"trait_name": best_key, "values": best_values}


def _valid_numeric_indices(values: np.ndarray) -> np.ndarray:
    return np.where(np.isfinite(values))[0]


def _mean_std(arr: np.ndarray) -> Tuple[float, float]:
    return float(np.mean(arr)), float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0


def _safe_welch_pvalue(x1: np.ndarray, x2: np.ndarray) -> float:
    if len(x1) < 2 or len(x2) < 2:
        return 1.0
    v1 = float(np.var(x1, ddof=1))
    v2 = float(np.var(x2, ddof=1))
    n1 = float(len(x1))
    n2 = float(len(x2))
    denom = math.sqrt((v1 / n1) + (v2 / n2))
    if denom <= 1e-12:
        return 1.0
    t_val = abs(float(np.mean(x1) - np.mean(x2)) / denom)
    return float(math.erfc(t_val / math.sqrt(2.0)))


def infer_analysis_mode(
    sample_metadata: Optional[Dict[str, Any]], dataset_info: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Infer mode and design hints from metadata with explicit fallback."""
    n = _sample_count(sample_metadata)
    groups = _extract_group_vector(sample_metadata)
    group_counts = Counter([g for g in groups if g != "unknown"])
    subtypes = _extract_subtype_vector(sample_metadata)
    subtype_counts = Counter([g for g in subtypes if g != "unknown"])
    time_values = np.array(_extract_time_vector(sample_metadata), dtype=float)
    trait = _extract_continuous_trait(sample_metadata)
    trait_values = np.array(trait["values"], dtype=float) if trait.get("values") else np.array([])

    has_time = len(_valid_numeric_indices(time_values)) >= 6 and len(np.unique(time_values[np.isfinite(time_values)])) >= 3
    has_case_control = group_counts.get("control", 0) >= 2 and group_counts.get("disease", 0) >= 2
    has_subtype = len([c for c in subtype_counts.values() if c >= 2]) >= 3
    has_trait = (
        trait.get("trait_name") is not None
        and len(_valid_numeric_indices(trait_values)) >= 6
        and np.std(trait_values[np.isfinite(trait_values)]) > 1e-9
    )

    mode = "unsupervised_pattern_discovery"
    primary_grouping: Optional[str] = None
    secondary_grouping: Optional[str] = None
    detected_signals: List[str] = []
    recommended_stats: List[str] = []

    if has_time:
        mode = "time_series"
        primary_grouping = "timepoint"
        detected_signals.append(">=3 unique timepoints with >=6 valid samples")
        recommended_stats = ["timepoint_mean", "trend_slope", "peak_timepoint", "early_late_shift"]
    elif has_case_control:
        mode = "case_control"
        primary_grouping = "control_vs_disease"
        detected_signals.append("control and disease groups detected")
        recommended_stats = ["mean_diff", "effect_size", "p_value", "top_up_down_subcategories"]
    elif has_subtype:
        mode = "subtype_comparison"
        primary_grouping = "subtype"
        detected_signals.append(">=3 subtype groups with >=2 samples each")
        recommended_stats = ["group_means", "between_group_spread", "subtype_signatures"]
    elif has_trait:
        mode = "continuous_trait_association"
        primary_grouping = trait.get("trait_name")
        detected_signals.append(f"continuous trait detected: {trait.get('trait_name')}")
        recommended_stats = ["pearson_correlation", "strongest_positive_negative_associations"]
    else:
        detected_signals.append("metadata signals insufficient, fallback to unsupervised mode")
        recommended_stats = ["top_bottom_subcategories", "system_profile_summary"]

    expected_systems = (dataset_info or {}).get("expected_systems") or []
    if expected_systems:
        secondary_grouping = "expected_systems"
        detected_signals.append(f"expected systems provided: {len(expected_systems)}")
    if n < 8:
        detected_signals.append("small sample size, interpretation should be conservative")

    return {
        "mode": mode,
        "primary_grouping": primary_grouping,
        "secondary_grouping": secondary_grouping,
        "detected_signals": detected_signals,
        "recommended_stats": recommended_stats,
    }


def _compute_subcategory_sample_scores(state: Dict[str, Any]) -> Dict[str, np.ndarray]:
    expr = state.get("expression_matrix")
    if expr is None:
        return {}
    gene_sets = build_subcategory_gene_sets()
    output: Dict[str, np.ndarray] = {}
    expr_genes = set(expr.index)
    for code, genes in gene_sets.items():
        matched = list(set(genes) & expr_genes)
        if len(matched) < 5:
            continue
        output[code] = compute_ssgsea_scores(expr, matched)
    return output


def _system_sample_matrix(scores_by_subcat: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    by_system: Dict[str, List[np.ndarray]] = defaultdict(list)
    for code, vec in scores_by_subcat.items():
        system = SUBCATEGORY_TO_SYSTEM.get(code)
        if system:
            by_system[system].append(vec)
    output: Dict[str, np.ndarray] = {}
    for system, vectors in by_system.items():
        stacked = np.vstack(vectors)
        output[system] = np.mean(stacked, axis=0)
    return output


def _system_mean_from_subcategory(scores_by_subcat: Dict[str, np.ndarray]) -> Dict[str, float]:
    sample_matrix = _system_sample_matrix(scores_by_subcat)
    return {system: float(np.mean(vec)) for system, vec in sample_matrix.items()}


def _subcategory_means(scores_by_subcat: Dict[str, np.ndarray]) -> Dict[str, float]:
    return {code: float(np.mean(vec)) for code, vec in scores_by_subcat.items()}


def _top_bottom_from_means(subcat_means: Dict[str, float], top_n: int = 5) -> Tuple[List[str], List[str]]:
    if not subcat_means:
        return [], []
    ranked = sorted(subcat_means.items(), key=lambda x: x[1], reverse=True)
    return [k for k, _ in ranked[:top_n]], [k for k, _ in ranked[-top_n:]]


def run_case_control_analysis(state: Dict[str, Any], scores_by_subcat: Dict[str, np.ndarray]) -> Dict[str, Any]:
    groups = np.array(_extract_group_vector(state.get("sample_metadata")))
    if not scores_by_subcat or len(groups) == 0:
        return {"status": "insufficient_data"}
    n = min(len(groups), len(next(iter(scores_by_subcat.values()))))
    groups = groups[:n]
    case_idx = np.where(groups == "disease")[0]
    ctrl_idx = np.where(groups == "control")[0]
    if len(case_idx) < 2 or len(ctrl_idx) < 2:
        return {"status": "insufficient_grouping"}

    diffs: Dict[str, Dict[str, float]] = {}
    for code, vec in scores_by_subcat.items():
        y = np.array(vec[:n], dtype=float)
        case = y[case_idx]
        ctrl = y[ctrl_idx]
        case_mean, case_std = _mean_std(case)
        ctrl_mean, ctrl_std = _mean_std(ctrl)
        diff = case_mean - ctrl_mean
        pooled = math.sqrt(((len(case) - 1) * (case_std**2) + (len(ctrl) - 1) * (ctrl_std**2)) / max(len(case) + len(ctrl) - 2, 1))
        effect_size = diff / pooled if pooled > 1e-12 else 0.0
        p_value = _safe_welch_pvalue(case, ctrl)
        fold_change = (case_mean + 1e-6) / (ctrl_mean + 1e-6) if abs(ctrl_mean) > 1e-9 else float("inf")
        diffs[code] = {
            "case_mean": case_mean,
            "control_mean": ctrl_mean,
            "mean_diff": diff,
            "fold_change": float(fold_change),
            "p_value": float(p_value),
            "effect_size": float(effect_size),
        }

    ranked = sorted(diffs.items(), key=lambda kv: kv[1]["mean_diff"], reverse=True)
    return {
        "status": "ok",
        "group_counts": {"disease": int(len(case_idx)), "control": int(len(ctrl_idx))},
        "group_differences": diffs,
        "top_up_subcategories": [k for k, _ in ranked[:5]],
        "top_down_subcategories": [k for k, _ in ranked[-5:]],
    }


def run_time_series_analysis(state: Dict[str, Any], scores_by_subcat: Dict[str, np.ndarray]) -> Dict[str, Any]:
    t = np.array(_extract_time_vector(state.get("sample_metadata")), dtype=float)
    if not scores_by_subcat or len(_valid_numeric_indices(t)) < 6:
        return {"status": "insufficient_data"}
    n = min(len(t), len(next(iter(scores_by_subcat.values()))))
    t = t[:n]
    valid = np.isfinite(t)
    if valid.sum() < 6:
        return {"status": "insufficient_timepoints"}
    uniq = np.unique(t[valid])
    if len(uniq) < 3:
        return {"status": "insufficient_timepoints"}

    summary: Dict[str, Dict[str, Any]] = {}
    for code, vec in scores_by_subcat.items():
        y = np.array(vec[:n], dtype=float)
        y_valid = y[valid]
        t_valid = t[valid]
        per_tp = {}
        for tp in uniq:
            vals = y_valid[t_valid == tp]
            if len(vals):
                per_tp[str(float(tp))] = float(np.mean(vals))
        slope = float(np.polyfit(t_valid, y_valid, 1)[0]) if len(y_valid) >= 3 else 0.0
        peak_tp = float(t_valid[int(np.argmax(y_valid))]) if len(y_valid) else None
        early_mean = float(np.mean(y_valid[t_valid == uniq[0]])) if np.any(t_valid == uniq[0]) else 0.0
        late_mean = float(np.mean(y_valid[t_valid == uniq[-1]])) if np.any(t_valid == uniq[-1]) else 0.0
        summary[code] = {
            "timepoint_means": per_tp,
            "trend_direction": "up" if slope > 0 else ("down" if slope < 0 else "flat"),
            "trend_slope": slope,
            "peak_timepoint": peak_tp,
            "early_late_shift": late_mean - early_mean,
        }

    ranked_up = sorted(summary.items(), key=lambda kv: kv[1]["early_late_shift"], reverse=True)
    return {
        "status": "ok",
        "timepoint_count": int(len(uniq)),
        "time_series_summary": summary,
        "up_shift_subcategories": [k for k, _ in ranked_up[:5]],
        "down_shift_subcategories": [k for k, _ in ranked_up[-5:]],
    }


def run_subtype_comparison_analysis(state: Dict[str, Any], scores_by_subcat: Dict[str, np.ndarray]) -> Dict[str, Any]:
    subtypes = np.array(_extract_subtype_vector(state.get("sample_metadata")))
    if not scores_by_subcat or len(subtypes) == 0:
        return {"status": "insufficient_data"}
    n = min(len(subtypes), len(next(iter(scores_by_subcat.values()))))
    subtypes = subtypes[:n]
    groups = [g for g, c in Counter(subtypes).items() if g != "unknown" and c >= 2]
    if len(groups) < 3:
        return {"status": "insufficient_subtypes"}

    subtype_summary: Dict[str, Dict[str, Any]] = {}
    group_signature: Dict[str, List[str]] = {}
    for code, vec in scores_by_subcat.items():
        y = np.array(vec[:n], dtype=float)
        means = {g: float(np.mean(y[subtypes == g])) for g in groups}
        spread = float(max(means.values()) - min(means.values())) if means else 0.0
        subtype_summary[code] = {"group_means": means, "between_group_spread": spread}

    for g in groups:
        ranked = sorted(
            subtype_summary.items(),
            key=lambda kv: kv[1]["group_means"].get(g, -9999.0)
            - np.mean([v for k, v in kv[1]["group_means"].items() if k != g] or [0.0]),
            reverse=True,
        )
        group_signature[g] = [k for k, _ in ranked[:3]]

    ranked_spread = sorted(subtype_summary.items(), key=lambda kv: kv[1]["between_group_spread"], reverse=True)
    return {
        "status": "ok",
        "subtype_count": len(groups),
        "subtype_summary": subtype_summary,
        "most_discriminative_subcategories": [k for k, _ in ranked_spread[:5]],
        "subtype_specific_signatures": group_signature,
    }


def run_continuous_trait_analysis(state: Dict[str, Any], scores_by_subcat: Dict[str, np.ndarray]) -> Dict[str, Any]:
    trait = _extract_continuous_trait(state.get("sample_metadata"))
    x = np.array(trait.get("values") or [], dtype=float)
    if not scores_by_subcat or trait.get("trait_name") is None or len(x) < 6:
        return {"status": "insufficient_data"}
    n = min(len(x), len(next(iter(scores_by_subcat.values()))))
    x = x[:n]
    valid = np.isfinite(x)
    if valid.sum() < 6 or np.std(x[valid]) <= 1e-9:
        return {"status": "insufficient_trait_variance"}

    associations = {}
    for code, vec in scores_by_subcat.items():
        y = np.array(vec[:n], dtype=float)
        y_valid = y[valid]
        x_valid = x[valid]
        corr = float(np.corrcoef(x_valid, y_valid)[0, 1]) if np.std(y_valid) > 1e-9 else 0.0
        associations[code] = {"correlation": corr}
    ranked = sorted(associations.items(), key=lambda kv: kv[1]["correlation"], reverse=True)
    return {
        "status": "ok",
        "trait_name": trait.get("trait_name"),
        "trait_associations": associations,
        "strongest_positive": [k for k, _ in ranked[:5]],
        "strongest_negative": [k for k, _ in ranked[-5:]],
    }


def run_unsupervised_pattern_analysis(scores_by_subcat: Dict[str, np.ndarray]) -> Dict[str, Any]:
    means = _subcategory_means(scores_by_subcat)
    top, bottom = _top_bottom_from_means(means)
    return {"status": "ok", "top_subcategories": top, "bottom_subcategories": bottom}


def run_expected_vs_observed_analysis(
    state: Dict[str, Any], subcat_means: Dict[str, float], system_means: Dict[str, float]
) -> Dict[str, Any]:
    expected = (state.get("dataset_info") or {}).get("expected_systems") or []
    if not expected:
        return {"status": "no_expected_systems"}
    ranked_systems = sorted(system_means.items(), key=lambda kv: kv[1], reverse=True)
    active_top = [k for k, _ in ranked_systems[:3]]
    suppressed_bottom = [k for k, _ in ranked_systems[-2:]]
    matched = [s for s in expected if s in active_top]
    missing = [s for s in expected if s not in active_top]
    unexpected = [s for s in active_top if s not in expected]
    return {
        "status": "ok",
        "expected_systems": expected,
        "matched_expected_systems": matched,
        "missing_expected_systems": missing,
        "unexpected_activated_systems": unexpected,
        "suppressed_systems": suppressed_bottom,
    }


def run_system_coordination_analysis(scores_by_subcat: Dict[str, np.ndarray]) -> Dict[str, Any]:
    system_sample = _system_sample_matrix(scores_by_subcat)
    systems = list(system_sample.keys())
    if len(systems) < 3:
        return {"status": "insufficient_systems"}
    mat = np.vstack([system_sample[s] for s in systems])
    corr = np.corrcoef(mat)
    pair_values = []
    for i in range(len(systems)):
        for j in range(i + 1, len(systems)):
            pair_values.append(((systems[i], systems[j]), float(corr[i, j])))
    pair_values.sort(key=lambda kv: kv[1], reverse=True)
    return {
        "status": "ok",
        "systems": systems,
        "correlation_matrix": {systems[i]: {systems[j]: float(corr[i, j]) for j in range(len(systems))} for i in range(len(systems))},
        "synergy_pairs": [{"pair": list(p[0]), "correlation": p[1]} for p in pair_values[:3]],
        "antagonism_pairs": [{"pair": list(p[0]), "correlation": p[1]} for p in pair_values[-3:]],
    }


def run_heterogeneity_analysis(scores_by_subcat: Dict[str, np.ndarray]) -> Dict[str, Any]:
    if not scores_by_subcat:
        return {"status": "insufficient_data"}
    subcat_var = {code: float(np.var(vec, ddof=1)) if len(vec) > 1 else 0.0 for code, vec in scores_by_subcat.items()}
    sys_vectors = _system_sample_matrix(scores_by_subcat)
    system_var = {sys: float(np.var(vec, ddof=1)) if len(vec) > 1 else 0.0 for sys, vec in sys_vectors.items()}
    ranked_subcat = sorted(subcat_var.items(), key=lambda kv: kv[1], reverse=True)
    ranked_system = sorted(system_var.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "status": "ok",
        "patient_level_variance": {"subcategory": subcat_var, "system": system_var},
        "most_heterogeneous_subcategories": [k for k, _ in ranked_subcat[:5]],
        "most_heterogeneous_systems": [k for k, _ in ranked_system[:3]],
    }


def run_paired_analysis(
    state: Dict[str, Any], scores_by_subcat: Dict[str, np.ndarray]
) -> Dict[str, Any]:
    rows = _parse_characteristics_rows(state.get("sample_metadata"))
    if not scores_by_subcat or not rows:
        return {"status": "insufficient_data"}
    pair_ids: List[Optional[str]] = []
    pair_phase: List[Optional[str]] = []
    for row in rows:
        kv = _parse_key_values_from_row(row)
        pid = kv.get("pair_id") or kv.get("patient_id") or kv.get("subject")
        phase = kv.get("phase") or kv.get("condition") or kv.get("timepoint")
        if phase:
            p = phase.lower()
            if any(k in p for k in ("pre", "before", "baseline")):
                phase = "pre"
            elif any(k in p for k in ("post", "after", "followup", "follow-up")):
                phase = "post"
        pair_ids.append(pid)
        pair_phase.append(phase)
    n = min(len(pair_ids), len(next(iter(scores_by_subcat.values()))))
    index_by_pair: Dict[str, Dict[str, int]] = defaultdict(dict)
    for i in range(n):
        pid = pair_ids[i]
        ph = pair_phase[i]
        if pid and ph in {"pre", "post"}:
            index_by_pair[pid][ph] = i
    usable_pairs = [pid for pid, m in index_by_pair.items() if "pre" in m and "post" in m]
    if len(usable_pairs) < 2:
        return {"status": "insufficient_pairs"}
    pair_delta = {}
    for code, vec in scores_by_subcat.items():
        y = np.array(vec[:n], dtype=float)
        deltas = [float(y[index_by_pair[pid]["post"]] - y[index_by_pair[pid]["pre"]]) for pid in usable_pairs]
        pair_delta[code] = {
            "mean_delta": float(np.mean(deltas)),
            "std_delta": float(np.std(deltas, ddof=1)) if len(deltas) > 1 else 0.0,
        }
    ranked = sorted(pair_delta.items(), key=lambda kv: kv[1]["mean_delta"], reverse=True)
    return {
        "status": "ok",
        "pair_count": len(usable_pairs),
        "paired_delta": pair_delta,
        "top_positive_delta_subcategories": [k for k, _ in ranked[:5]],
        "top_negative_delta_subcategories": [k for k, _ in ranked[-5:]],
    }


def run_response_stratification_analysis(
    state: Dict[str, Any], scores_by_subcat: Dict[str, np.ndarray]
) -> Dict[str, Any]:
    rows = _parse_characteristics_rows(state.get("sample_metadata"))
    if not scores_by_subcat or not rows:
        return {"status": "insufficient_data"}
    labels: List[str] = []
    for row in rows:
        kv = _parse_key_values_from_row(row)
        raw = kv.get("response") or kv.get("responder") or kv.get("outcome") or "unknown"
        low = str(raw).lower()
        if any(k in low for k in ("responder", "response", "sensitive", "remission")):
            labels.append("responder")
        elif any(k in low for k in ("non-responder", "refractory", "resistant", "progression")):
            labels.append("non_responder")
        else:
            labels.append("unknown")
    n = min(len(labels), len(next(iter(scores_by_subcat.values()))))
    g = np.array(labels[:n])
    r = np.where(g == "responder")[0]
    nr = np.where(g == "non_responder")[0]
    if len(r) < 2 or len(nr) < 2:
        return {"status": "insufficient_response_groups"}
    diff = {}
    for code, vec in scores_by_subcat.items():
        y = np.array(vec[:n], dtype=float)
        diff[code] = {
            "responder_mean": float(np.mean(y[r])),
            "non_responder_mean": float(np.mean(y[nr])),
            "mean_diff": float(np.mean(y[r]) - np.mean(y[nr])),
        }
    ranked = sorted(diff.items(), key=lambda kv: kv[1]["mean_diff"], reverse=True)
    return {
        "status": "ok",
        "group_counts": {"responder": int(len(r)), "non_responder": int(len(nr))},
        "response_summary": diff,
        "response_enriched_subcategories": [k for k, _ in ranked[:5]],
        "response_depleted_subcategories": [k for k, _ in ranked[-5:]],
    }


def run_severity_progression_analysis(
    state: Dict[str, Any], scores_by_subcat: Dict[str, np.ndarray]
) -> Dict[str, Any]:
    rows = _parse_characteristics_rows(state.get("sample_metadata"))
    if not scores_by_subcat or not rows:
        return {"status": "insufficient_data"}
    sev: List[float] = []
    for row in rows:
        kv = _parse_key_values_from_row(row)
        raw = None
        for key, value in kv.items():
            if any(tag in key for tag in ("severity", "stage", "grade")):
                raw = value
                break
        if raw is None:
            raw = " ".join(row)
        value = _extract_numeric_value(str(raw))
        sev.append(value if value is not None else float("nan"))
    x = np.array(sev, dtype=float)
    n = min(len(x), len(next(iter(scores_by_subcat.values()))))
    x = x[:n]
    valid = np.isfinite(x)
    if valid.sum() < 6 or np.std(x[valid]) <= 1e-9:
        return {"status": "insufficient_severity_signal"}
    assoc = {}
    for code, vec in scores_by_subcat.items():
        y = np.array(vec[:n], dtype=float)
        corr = float(np.corrcoef(x[valid], y[valid])[0, 1]) if np.std(y[valid]) > 1e-9 else 0.0
        assoc[code] = {"severity_correlation": corr}
    ranked = sorted(assoc.items(), key=lambda kv: kv[1]["severity_correlation"], reverse=True)
    return {
        "status": "ok",
        "severity_summary": assoc,
        "severity_positive_associations": [k for k, _ in ranked[:5]],
        "severity_negative_associations": [k for k, _ in ranked[-5:]],
    }


def _focus_subcategories(
    state: Dict[str, Any], mode_result: Dict[str, Any], subcat_means: Dict[str, float]
) -> List[str]:
    top, bottom = _top_bottom_from_means(subcat_means, top_n=5)
    expected_systems = set((state.get("dataset_info") or {}).get("expected_systems") or [])
    expected_codes = [c for c, system in SUBCATEGORY_TO_SYSTEM.items() if system in expected_systems]
    mode_focus = []
    for key in (
        "top_up_subcategories",
        "top_down_subcategories",
        "up_shift_subcategories",
        "down_shift_subcategories",
        "most_discriminative_subcategories",
        "strongest_positive",
        "strongest_negative",
        "top_subcategories",
        "bottom_subcategories",
    ):
        mode_focus.extend(mode_result.get(key) or [])
    merged = list(dict.fromkeys(top + bottom + expected_codes[:4] + mode_focus))
    return merged[:16]


def decide_analysis_mode(state: Dict[str, Any]) -> Dict[str, Any]:
    state["current_step"] = "decide_analysis_mode"
    state["log_messages"].append(f"[{datetime.now()}] deciding analysis mode from metadata...")
    decision = infer_analysis_mode(state.get("sample_metadata"), state.get("dataset_info"))
    mode = decision.get("mode") or "unsupervised_pattern_discovery"
    if mode not in SUPPORTED_MODES:
        mode = "unsupervised_pattern_discovery"
    state["analysis_mode"] = mode
    state["analysis_design"] = {
        "primary_grouping": decision.get("primary_grouping"),
        "secondary_grouping": decision.get("secondary_grouping"),
        "detected_signals": decision.get("detected_signals", []),
        "recommended_stats": decision.get("recommended_stats", []),
    }
    state["grouping_info"] = {
        "primary_grouping": decision.get("primary_grouping"),
        "secondary_grouping": decision.get("secondary_grouping"),
    }
    state.setdefault("metadata", {})
    state["metadata"]["analysis_mode_decision"] = decision
    state["log_messages"].append(f"analysis_mode = {mode}")
    if decision.get("detected_signals"):
        state["log_messages"].append("mode signals: " + "; ".join(decision["detected_signals"][:4]))
    return state


def compute_mode_specific_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    state["current_step"] = "compute_mode_specific_analysis"
    state["log_messages"].append(f"[{datetime.now()}] computing mode-specific and cross-cutting statistics...")
    mode = state.get("analysis_mode") or "unsupervised_pattern_discovery"
    scores_by_subcat = _compute_subcategory_sample_scores(state)
    subcat_means = _subcategory_means(scores_by_subcat)
    system_means = _system_mean_from_subcategory(scores_by_subcat)
    top_subcats, bottom_subcats = _top_bottom_from_means(subcat_means)

    if mode == "case_control":
        mode_result = run_case_control_analysis(state, scores_by_subcat)
    elif mode == "time_series":
        mode_result = run_time_series_analysis(state, scores_by_subcat)
    elif mode == "subtype_comparison":
        mode_result = run_subtype_comparison_analysis(state, scores_by_subcat)
    elif mode == "continuous_trait_association":
        mode_result = run_continuous_trait_analysis(state, scores_by_subcat)
    else:
        mode_result = run_unsupervised_pattern_analysis(scores_by_subcat)

    if mode_result.get("status") != "ok" and mode != "unsupervised_pattern_discovery":
        fallback = run_unsupervised_pattern_analysis(scores_by_subcat)
        mode_result = {
            "status": "fallback_unsupervised",
            "reason": mode_result.get("status"),
            "fallback_result": fallback,
        }
        state["log_messages"].append(f"mode fallback activated: {mode_result['reason']}")

    expected_vs_observed = run_expected_vs_observed_analysis(state, subcat_means, system_means)
    system_coordination = run_system_coordination_analysis(scores_by_subcat)
    heterogeneity = run_heterogeneity_analysis(scores_by_subcat)
    paired_summary = run_paired_analysis(state, scores_by_subcat)
    response_summary = run_response_stratification_analysis(state, scores_by_subcat)
    severity_summary = run_severity_progression_analysis(state, scores_by_subcat)

    focus_subcats = _focus_subcategories(state, mode_result if mode_result else {}, subcat_means)
    focus_systems = sorted(
        {
            SUBCATEGORY_TO_SYSTEM.get(code)
            for code in focus_subcats
            if SUBCATEGORY_TO_SYSTEM.get(code)
        }
    )

    state["focus_subcategories"] = focus_subcats
    state["focus_systems"] = focus_systems
    state["mode_specific_results"] = mode_result
    state["statistical_results"] = {
        "analysis_mode": mode,
        "analysis_design": state.get("analysis_design") or {},
        "system_means": system_means,
        "top_subcategories": top_subcats,
        "bottom_subcategories": bottom_subcats,
        "group_differences": mode_result.get("group_differences", {}),
        "time_series_summary": mode_result.get("time_series_summary", {}),
        "subtype_summary": mode_result.get("subtype_summary", {}),
        "trait_associations": mode_result.get("trait_associations", {}),
        "expected_vs_observed": expected_vs_observed,
        "system_coordination": system_coordination,
        "heterogeneity_summary": heterogeneity,
        "paired_summary": paired_summary,
        "response_summary": response_summary,
        "severity_summary": severity_summary,
        "mode_specific_results": mode_result,
    }
    state["log_messages"].append(
        "mode statistics ready: "
        f"mode={mode}, focus_subcategories={len(focus_subcats)}, focus_systems={len(focus_systems)}"
    )
    return state


def decide_plot_plan(state: Dict[str, Any]) -> Dict[str, Any]:
    state["current_step"] = "decide_plot_plan"
    state["log_messages"].append(f"[{datetime.now()}] deciding mode-aware plot plan...")
    mode = state.get("analysis_mode") or "unsupervised_pattern_discovery"

    base_plots = ["radar", "barplot"]
    mode_plots = {
        "case_control": ["boxplot", "heatmap", "expected_vs_observed_barplot"],
        "time_series": ["time_series_system", "time_series_subcategory", "heatmap"],
        "subtype_comparison": ["grouped_subtype_boxplot", "heatmap", "correlation"],
        "continuous_trait_association": ["trait_scatter_plot", "correlation", "heatmap"],
        "unsupervised_pattern_discovery": ["heatmap", "correlation", "heterogeneity_heatmap"],
    }
    plots = base_plots + mode_plots.get(mode, ["heatmap", "correlation"])

    stat = state.get("statistical_results") or {}
    if (stat.get("expected_vs_observed") or {}).get("status") == "ok":
        plots.append("expected_vs_observed_barplot")
    if (stat.get("system_coordination") or {}).get("status") == "ok":
        plots.append("system_correlation_matrix")
    if (stat.get("heterogeneity_summary") or {}).get("status") == "ok":
        plots.append("heterogeneity_heatmap")

    plots = list(dict.fromkeys(plots))
    focus_subcategories = state.get("focus_subcategories") or []
    focus_systems = state.get("focus_systems") or []
    focus_reasoning = "; ".join(
        [
            f"mode={mode}",
            f"focus_subcategories={','.join(focus_subcategories[:8]) or 'none'}",
            f"focus_systems={','.join(focus_systems) or 'none'}",
            f"expected_vs_observed={(stat.get('expected_vs_observed') or {}).get('status', 'na')}",
        ]
    )
    plan = {
        "plots": plots,
        "focus_subcategories": focus_subcategories,
        "focus_systems": focus_systems,
        "focus_reasoning": focus_reasoning,
        "priority_order": plots,
    }
    state["plot_plan"] = plan
    state["visualization_plan"] = plots
    state["log_messages"].append("plot plan ready: " + ", ".join(plots))
    return state
