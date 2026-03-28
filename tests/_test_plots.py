#!/usr/bin/env python3
"""Quick plot-generation check using an existing local dataset."""

import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, ".")

from src.agent.geo_parsing import (
    find_gpl_file,
    map_probe_to_gene,
    parse_gpl_annotation,
    parse_series_matrix,
)
from src.agent.plot_generator import generate_all_plots
from src.agent.scoring_core import (
    SUBCATEGORY_NAMES,
    SUBCATEGORY_TO_SYSTEM,
    build_subcategory_gene_sets,
    compute_ssgsea_scores,
)


def load_env() -> None:
    env_file = ".env"
    if not os.path.exists(env_file):
        return
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()


def main() -> None:
    load_env()

    print("Step 1: 预处理 GSE2034...")
    dataset_dir = Path("data/validation_datasets/GSE2034-乳腺癌")
    series_file = dataset_dir / "GSE2034_series_matrix.txt.gz"
    gpl_file = find_gpl_file(series_file, dataset_dir)
    print(f"  GPL: {gpl_file.name}")

    expr_df = parse_series_matrix(series_file)
    mapping_df = parse_gpl_annotation(gpl_file)
    gene_expr_df = map_probe_to_gene(expr_df, mapping_df)
    print(f"  Gene matrix: {gene_expr_df.shape}")

    print("Step 2: ssGSEA...")
    gene_sets = build_subcategory_gene_sets()
    available = set(gene_expr_df.index)
    ssgsea_scores = {}
    system_score_lists = {f"System {s}": [] for s in "ABCDE"}

    for code, genes in gene_sets.items():
        matched = list(set(genes) & available)
        scores = compute_ssgsea_scores(gene_expr_df, matched)
        mean_score = float(np.mean(scores))
        ssgsea_scores[code] = {
            "mean_score": mean_score,
            "std_score": float(np.std(scores)),
            "median_score": float(np.median(scores)),
            "name": SUBCATEGORY_NAMES.get(code, code),
            "gene_count": len(genes),
            "matched_genes": len(matched),
        }
        system = SUBCATEGORY_TO_SYSTEM.get(code)
        if system:
            system_score_lists[system].append(mean_score)

    system_scores = {
        system: float(np.mean(values)) if values else 0.0
        for system, values in system_score_lists.items()
    }
    print(f"  系统得分: {system_scores}")

    print("Step 3: 生成图表...")
    figures = generate_all_plots(
        dataset_id="GSE2034",
        ssgsea_scores=ssgsea_scores,
        system_scores=system_scores,
        gene_expr_df=gene_expr_df,
        output_dir="results/agent_analysis/_test_plots",
    )
    print(f"  生成 {len(figures)} 个图表")
    for figure in figures:
        size_kb = os.path.getsize(figure) / 1024
        print(f"    {Path(figure).name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
