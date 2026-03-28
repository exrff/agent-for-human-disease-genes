#!/usr/bin/env python3
"""Shared scoring helpers for gene-set construction and ssGSEA."""

import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd


SUBCATEGORY_CODES = [
    "A1", "A2", "A3", "A4",
    "B1", "B2", "B3",
    "C1", "C2", "C3",
    "D1", "D2",
    "E1", "E2",
]

SUBCATEGORY_NAMES = {
    "A1": "Genomic Stability and Repair",
    "A2": "Somatic Maintenance and Identity Preservation",
    "A3": "Cellular Homeostasis and Structural Maintenance",
    "A4": "Inflammation Resolution and Damage Containment",
    "B1": "Innate Immunity",
    "B2": "Adaptive Immunity",
    "B3": "Immune Regulation and Tolerance",
    "C1": "Energy Metabolism and Catabolism",
    "C2": "Biosynthesis and Anabolism",
    "C3": "Detoxification and Metabolic Stress Handling",
    "D1": "Neural Regulation and Signal Transmission",
    "D2": "Endocrine and Autonomic Regulation",
    "E1": "Reproduction",
    "E2": "Development and Reproductive Maturation",
}

SUBCATEGORY_TO_SYSTEM = {
    "A1": "System A", "A2": "System A", "A3": "System A", "A4": "System A",
    "B1": "System B", "B2": "System B", "B3": "System B",
    "C1": "System C", "C2": "System C", "C3": "System C",
    "D1": "System D", "D2": "System D",
    "E1": "System E", "E2": "System E",
}

CLASSIFICATION_FILE = Path("results/full_classification/full_classification_results.csv")
GO_MAPPING_FILE = Path("data/go_annotations/go_to_genes.json")
KEGG_MAPPING_FILE = Path("data/kegg_mappings/kegg_to_genes.json")


def build_subcategory_gene_sets() -> Dict[str, List[str]]:
    """Build the 14 subcategory gene sets from classification and GO/KEGG mappings."""
    df = pd.read_csv(CLASSIFICATION_FILE)

    with open(GO_MAPPING_FILE, "r", encoding="utf-8") as f:
        go_to_genes = json.load(f)

    with open(KEGG_MAPPING_FILE, "r", encoding="utf-8") as f:
        kegg_raw = json.load(f)
    kegg_to_genes = {pid: info["genes"] for pid, info in kegg_raw.items()}

    gene_sets: Dict[str, List[str]] = {}
    for code in SUBCATEGORY_CODES:
        subset = df[df["Subcategory_Code"] == code]
        all_genes = set()
        for term_id in subset["ID"]:
            term_id = str(term_id)
            if term_id.startswith("GO:") and term_id in go_to_genes:
                all_genes.update(go_to_genes[term_id])
            elif term_id.startswith("KEGG:") and term_id in kegg_to_genes:
                all_genes.update(kegg_to_genes[term_id])
        gene_sets[code] = list(all_genes)

    return gene_sets


def compute_ssgsea_scores(gene_expr_df, gene_set_genes: List[str], alpha: float = 0.25) -> np.ndarray:
    """Compute ssGSEA-like enrichment scores across samples for one gene set."""
    if not gene_set_genes:
        return np.zeros(gene_expr_df.shape[1])

    matched = list(set(gene_set_genes) & set(gene_expr_df.index))
    if not matched:
        return np.zeros(gene_expr_df.shape[1])

    scores = []
    for sample in gene_expr_df.columns:
        expr = gene_expr_df[sample].dropna()
        if len(expr) == 0:
            scores.append(0.0)
            continue

        sorted_expr = expr.sort_values(ascending=False)
        total_genes = len(sorted_expr)
        in_set = sorted_expr.index.isin(matched)
        matched_count = in_set.sum()
        if matched_count == 0:
            scores.append(0.0)
            continue

        weights = np.where(in_set, np.abs(sorted_expr.values) ** alpha, 0.0)
        weight_sum = weights[in_set].sum()
        if weight_sum == 0:
            scores.append(0.0)
            continue

        miss_penalty = 1.0 / (total_genes - matched_count) if total_genes > matched_count else 0.0
        running, max_es, min_es = 0.0, 0.0, 0.0
        for i in range(total_genes):
            running += weights[i] / weight_sum if in_set[i] else -miss_penalty
            if running > max_es:
                max_es = running
            if running < min_es:
                min_es = running

        scores.append(max_es if abs(max_es) >= abs(min_es) else min_es)

    return np.array(scores)
