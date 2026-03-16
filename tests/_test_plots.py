#!/usr/bin/env python3
"""测试绘图模块，使用 GSE2034 已有数据"""
import sys, os
sys.path.insert(0, '.')

# 加载 .env
with open('.env', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

from pathlib import Path
from src.agent.disease_analysis_agent import (
    _parse_series_matrix, _parse_gpl_annotation,
    _map_probe_to_gene, _find_gpl_file,
    _build_subcategory_gene_sets, _compute_ssgsea_scores
)
import numpy as np

print("Step 1: 预处理 GSE2034...")
dataset_dir = Path("data/validation_datasets/GSE2034-乳腺癌")
series_file = dataset_dir / "GSE2034_series_matrix.txt.gz"
gpl_file = _find_gpl_file(series_file, dataset_dir)
print(f"  GPL: {gpl_file.name}")

expr_df = _parse_series_matrix(series_file)
mapping_df = _parse_gpl_annotation(gpl_file)
gene_expr_df = _map_probe_to_gene(expr_df, mapping_df)
print(f"  Gene matrix: {gene_expr_df.shape}")

print("Step 2: ssGSEA...")
gene_sets = _build_subcategory_gene_sets()
subcat_to_system = {
    'A1':'System A','A2':'System A','A3':'System A','A4':'System A',
    'B1':'System B','B2':'System B','B3':'System B',
    'C1':'System C','C2':'System C','C3':'System C',
    'D1':'System D','D2':'System D',
    'E1':'System E','E2':'System E',
}
subcategory_names = {
    'A1':'Genomic Stability and Repair','A2':'Somatic Maintenance and Identity Preservation',
    'A3':'Cellular Homeostasis and Structural Maintenance','A4':'Inflammation Resolution and Damage Containment',
    'B1':'Innate Immunity','B2':'Adaptive Immunity','B3':'Immune Regulation and Tolerance',
    'C1':'Energy Metabolism and Catabolism','C2':'Biosynthesis and Anabolism',
    'C3':'Detoxification and Metabolic Stress Handling',
    'D1':'Neural Regulation and Signal Transmission','D2':'Endocrine and Autonomic Regulation',
    'E1':'Reproduction','E2':'Development and Reproductive Maturation',
}

available = set(gene_expr_df.index)
ssgsea_scores = {}
system_score_lists = {f'System {s}': [] for s in 'ABCDE'}

for code, genes in gene_sets.items():
    matched = list(set(genes) & available)
    scores = _compute_ssgsea_scores(gene_expr_df, matched)
    mean_score = float(np.mean(scores))
    ssgsea_scores[code] = {
        'mean_score': mean_score,
        'std_score': float(np.std(scores)),
        'median_score': float(np.median(scores)),
        'name': subcategory_names.get(code, code),
        'gene_count': len(genes),
        'matched_genes': len(matched),
    }
    sys = subcat_to_system.get(code)
    if sys:
        system_score_lists[sys].append(mean_score)

system_scores = {s: float(np.mean(v)) if v else 0.0 for s, v in system_score_lists.items()}
print(f"  系统得分: {system_scores}")

print("Step 3: 生成图表...")
from src.agent.plot_generator import generate_all_plots
figures = generate_all_plots(
    dataset_id='GSE2034',
    ssgsea_scores=ssgsea_scores,
    system_scores=system_scores,
    gene_expr_df=gene_expr_df,
    output_dir='results/agent_analysis/_test_plots',
)
print(f"  生成 {len(figures)} 个图表:")
for f in figures:
    size = os.path.getsize(f)
    print(f"    {Path(f).name} ({size/1024:.1f} KB)")
