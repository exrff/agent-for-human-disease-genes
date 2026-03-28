#!/usr/bin/env python3
"""
Agent 分析结果可视化模块

根据 ssGSEA 得分和表达矩阵生成个性化图表：
1. 系统得分雷达图 — 五大系统激活全貌
2. 子类得分热图 — 14个子类 × 样本
3. 系统得分箱线图 — 样本间分布
4. 子类得分排名柱状图 — Top/Bottom 子类
5. 系统间相关性热图 — 系统协同/拮抗关系
"""

import os
import json
import logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # 非交互模式，避免 GUI 依赖
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import seaborn as sns
from pathlib import Path
from typing import Dict, Any, List, Optional

from .scoring_core import (
    build_subcategory_gene_sets as shared_build_subcategory_gene_sets,
    compute_ssgsea_scores as shared_compute_ssgsea_scores,
)

logger = logging.getLogger(__name__)

# ── 全局样式 ──────────────────────────────────────────────────────────────────
plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'axes.unicode_minus': False,
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
})

SYSTEM_COLORS = {
    'System A': '#E74C3C',
    'System B': '#3498DB',
    'System C': '#2ECC71',
    'System D': '#9B59B6',
    'System E': '#F39C12',
}

SUBCAT_COLORS = {
    'A': '#E74C3C', 'B': '#3498DB', 'C': '#2ECC71',
    'D': '#9B59B6', 'E': '#F39C12',
}

SUBCAT_LABELS = {
    'A1': 'A1 Genomic Stability',
    'A2': 'A2 Somatic Maintenance',
    'A3': 'A3 Cellular Homeostasis',
    'A4': 'A4 Inflammation Resolution',
    'B1': 'B1 Innate Immunity',
    'B2': 'B2 Adaptive Immunity',
    'B3': 'B3 Immune Regulation',
    'C1': 'C1 Energy Metabolism',
    'C2': 'C2 Biosynthesis',
    'C3': 'C3 Detoxification',
    'D1': 'D1 Neural Regulation',
    'D2': 'D2 Endocrine Regulation',
    'E1': 'E1 Reproduction',
    'E2': 'E2 Development',
}


# ── 本地辅助函数（避免循环导入）────────────────────────────────────────────────

def _build_subcategory_gene_sets() -> Dict[str, List[str]]:
    """从分类结果 + GO/KEGG 映射构建 14 个子类的基因集"""
    classification_file = "results/full_classification/full_classification_results.csv"
    go_mapping_file = "data/go_annotations/go_to_genes.json"
    kegg_mapping_file = "data/kegg_mappings/kegg_to_genes.json"

    df = pd.read_csv(classification_file)
    with open(go_mapping_file, 'r') as f:
        go_to_genes = json.load(f)
    with open(kegg_mapping_file, 'r') as f:
        kegg_raw = json.load(f)
    kegg_to_genes = {pid: info['genes'] for pid, info in kegg_raw.items()}

    subcategory_codes = ['A1','A2','A3','A4','B1','B2','B3','C1','C2','C3','D1','D2','E1','E2']
    gene_sets = {}
    for code in subcategory_codes:
        subset = df[df['Subcategory_Code'] == code]
        all_genes: set = set()
        for term_id in subset['ID']:
            if str(term_id).startswith('GO:') and term_id in go_to_genes:
                all_genes.update(go_to_genes[term_id])
            elif str(term_id).startswith('KEGG:') and term_id in kegg_to_genes:
                all_genes.update(kegg_to_genes[term_id])
        gene_sets[code] = list(all_genes)
    return gene_sets


def _compute_ssgsea_scores(gene_expr_df, gene_set_genes: list, alpha: float = 0.25) -> np.ndarray:
    """自实现 ssGSEA：加权 KS 统计量，对每个样本计算基因集富集得分"""
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
        N = len(sorted_expr)
        in_set = sorted_expr.index.isin(matched)
        Nh = in_set.sum()
        if Nh == 0:
            scores.append(0.0)
            continue
        weights = np.where(in_set, np.abs(sorted_expr.values) ** alpha, 0.0)
        weight_sum = weights[in_set].sum()
        if weight_sum == 0:
            scores.append(0.0)
            continue
        miss_penalty = 1.0 / (N - Nh) if N > Nh else 0.0
        running, max_es, min_es = 0.0, 0.0, 0.0
        for i in range(N):
            running += weights[i] / weight_sum if in_set[i] else -miss_penalty
            if running > max_es:
                max_es = running
            if running < min_es:
                min_es = running
        scores.append(max_es if abs(max_es) >= abs(min_es) else min_es)
    return np.array(scores)


def _build_subcategory_gene_sets() -> Dict[str, List[str]]:
    """Compatibility wrapper that delegates to the shared scoring core."""
    return shared_build_subcategory_gene_sets()


def _compute_ssgsea_scores(gene_expr_df, gene_set_genes: list, alpha: float = 0.25) -> np.ndarray:
    """Compatibility wrapper that delegates to the shared scoring core."""
    return shared_compute_ssgsea_scores(gene_expr_df, gene_set_genes, alpha=alpha)


def generate_all_plots(
    dataset_id: str,
    ssgsea_scores: Dict[str, Any],
    system_scores: Dict[str, float],
    gene_expr_df,           # pd.DataFrame or None
    sample_metadata: Optional[Dict] = None,
    output_dir: str = None,
    viz_plan: List[str] = None,
) -> List[str]:
    """
    根据 viz_plan 生成所有图表，返回生成的文件路径列表。

    viz_plan 可选值: radar, heatmap, boxplot, barplot, correlation
    默认全部生成。
    """
    if output_dir is None:
        output_dir = f"results/agent_analysis/{dataset_id}/figures"
    os.makedirs(output_dir, exist_ok=True)

    if viz_plan is None:
        viz_plan = ['radar', 'heatmap', 'boxplot', 'barplot', 'correlation']

    figures = []

    # 提取子类均值得分 Series
    subcat_means = {
        code: info['mean_score']
        for code, info in ssgsea_scores.items()
    } if ssgsea_scores else {}

    for viz in viz_plan:
        try:
            path = None
            if viz == 'radar' and system_scores:
                path = plot_radar(system_scores, dataset_id, output_dir)
            elif viz == 'heatmap' and gene_expr_df is not None and ssgsea_scores:
                path = plot_subcat_heatmap(ssgsea_scores, gene_expr_df, dataset_id, output_dir)
            elif viz == 'boxplot' and gene_expr_df is not None and ssgsea_scores:
                path = plot_system_boxplot(ssgsea_scores, gene_expr_df, dataset_id, output_dir)
            elif viz == 'barplot' and subcat_means:
                path = plot_subcat_barplot(subcat_means, ssgsea_scores, dataset_id, output_dir)
            elif viz == 'correlation' and system_scores:
                path = plot_system_correlation(ssgsea_scores, gene_expr_df, dataset_id, output_dir)

            if path:
                figures.append(path)
                logger.info(f"  ✓ 生成图表: {Path(path).name}")
        except Exception as e:
            logger.warning(f"  ⚠ 生成 {viz} 失败: {e}")

    return figures


# ── 图1: 雷达图 ───────────────────────────────────────────────────────────────

def plot_radar(system_scores: Dict[str, float], dataset_id: str, output_dir: str) -> str:
    """五大系统激活雷达图"""
    systems = ['System A', 'System B', 'System C', 'System D', 'System E']
    labels = ['A\nHomeostasis', 'B\nImmunity', 'C\nMetabolism', 'D\nRegulation', 'E\nReproduction']
    values = [system_scores.get(s, 0.0) for s in systems]

    # 归一化到 [0, 1]
    vmax = max(abs(v) for v in values) or 1.0
    norm_values = [v / vmax for v in values]
    norm_values += norm_values[:1]  # 闭合

    angles = np.linspace(0, 2 * np.pi, len(systems), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))

    ax.plot(angles, norm_values, 'o-', linewidth=2, color='#E74C3C')
    ax.fill(angles, norm_values, alpha=0.25, color='#E74C3C')

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=12)
    ax.set_ylim(-1, 1)
    ax.set_yticks([-0.5, 0, 0.5, 1.0])
    ax.set_yticklabels(['-0.5', '0', '0.5', '1.0'], fontsize=8, color='gray')
    ax.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.7)

    # 在每个顶点标注原始得分
    for angle, val, sys in zip(angles[:-1], values, systems):
        ax.annotate(f'{val:.3f}', xy=(angle, norm_values[systems.index(sys)]),
                    xytext=(angle, norm_values[systems.index(sys)] + 0.12),
                    fontsize=9, ha='center', color=SYSTEM_COLORS[sys], fontweight='bold')

    ax.set_title(f'{dataset_id}\nFive-System Activation Radar', fontsize=14, fontweight='bold', pad=20)

    path = os.path.join(output_dir, 'radar_system_scores.png')
    plt.savefig(path)
    plt.close()
    return path


# ── 图2: 子类热图 ─────────────────────────────────────────────────────────────

def plot_subcat_heatmap(
    ssgsea_scores: Dict[str, Any],
    gene_expr_df,
    dataset_id: str,
    output_dir: str,
    max_samples: int = 60,
) -> str:
    """14个子类 × 样本 ssGSEA 得分热图（逐样本计算）"""
    gene_sets = _build_subcategory_gene_sets()
    subcats = [c for c in SUBCAT_LABELS if c in gene_sets]

    # 抽样（样本太多时）
    samples = list(gene_expr_df.columns)
    if len(samples) > max_samples:
        step = len(samples) // max_samples
        samples = samples[::step][:max_samples]
    expr_sub = gene_expr_df[samples]

    # 计算每个子类每个样本的得分
    score_matrix = {}
    for code in subcats:
        genes = gene_sets.get(code, [])
        scores = _compute_ssgsea_scores(expr_sub, genes)
        score_matrix[code] = scores

    df_heat = pd.DataFrame(score_matrix, index=samples).T
    df_heat.index = [SUBCAT_LABELS.get(c, c) for c in df_heat.index]

    # 按系统分组排序（已经是A→E顺序）
    fig, ax = plt.subplots(figsize=(max(12, len(samples) * 0.15 + 4), 8))

    # 行颜色条（系统标识）
    row_colors = [SUBCAT_COLORS[c[0]] for c in subcats]

    sns.heatmap(
        df_heat, ax=ax,
        cmap='RdBu_r', center=0,
        xticklabels=False,
        yticklabels=True,
        linewidths=0,
        cbar_kws={'label': 'ssGSEA Score', 'shrink': 0.6},
    )

    # 在左侧加系统色块
    for i, code in enumerate(subcats):
        ax.add_patch(mpatches.Rectangle(
            (-0.015, (len(subcats) - i - 1) / len(subcats)),
            0.012, 1 / len(subcats),
            transform=ax.transAxes, clip_on=False,
            color=SUBCAT_COLORS[code[0]], linewidth=0
        ))

    ax.set_title(f'{dataset_id} — 14-Subcategory ssGSEA Heatmap\n(n={len(samples)} samples)',
                 fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel('Samples', fontsize=11)
    ax.set_ylabel('')
    ax.tick_params(axis='y', labelsize=9)

    # 图例：系统颜色
    patches = [mpatches.Patch(color=SUBCAT_COLORS[s], label=f'System {s}') for s in 'ABCDE']
    ax.legend(handles=patches, loc='upper right', bbox_to_anchor=(1.18, 1.02),
              fontsize=9, title='System', title_fontsize=9)

    path = os.path.join(output_dir, 'heatmap_subcat_ssgsea.png')
    plt.savefig(path)
    plt.close()
    return path


# ── 图3: 系统得分箱线图 ───────────────────────────────────────────────────────

def plot_system_boxplot(
    ssgsea_scores: Dict[str, Any],
    gene_expr_df,
    dataset_id: str,
    output_dir: str,
) -> str:
    """五大系统 ssGSEA 得分样本分布箱线图"""
    gene_sets = _build_subcategory_gene_sets()
    subcat_to_system = {
        'A1': 'System A', 'A2': 'System A', 'A3': 'System A', 'A4': 'System A',
        'B1': 'System B', 'B2': 'System B', 'B3': 'System B',
        'C1': 'System C', 'C2': 'System C', 'C3': 'System C',
        'D1': 'System D', 'D2': 'System D',
        'E1': 'System E', 'E2': 'System E',
    }

    # 每个系统：合并其子类基因集，计算每样本得分
    system_sample_scores = {}
    for sys in ['System A', 'System B', 'System C', 'System D', 'System E']:
        codes = [c for c, s in subcat_to_system.items() if s == sys]
        all_genes = list({g for c in codes for g in gene_sets.get(c, [])})
        scores = _compute_ssgsea_scores(gene_expr_df, all_genes)
        system_sample_scores[sys] = scores

    # 转为长格式 DataFrame
    rows = []
    for sys, scores in system_sample_scores.items():
        for s in scores:
            rows.append({'System': sys, 'ssGSEA Score': s})
    df = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(10, 6))
    palette = {s: SYSTEM_COLORS[s] for s in SYSTEM_COLORS if s in df['System'].unique()}

    sns.violinplot(data=df, x='System', y='ssGSEA Score',
                   palette=palette, hue='System', legend=False,
                   inner='box', ax=ax, linewidth=1.2)
    sns.stripplot(data=df, x='System', y='ssGSEA Score',
                  color='black', alpha=0.15, size=2, ax=ax, jitter=True)

    ax.axhline(0, color='gray', linestyle='--', linewidth=0.8, alpha=0.7)
    ax.set_title(f'{dataset_id} — System ssGSEA Score Distribution\n(n={gene_expr_df.shape[1]} samples)',
                 fontsize=13, fontweight='bold')
    ax.set_xlabel('Functional System', fontsize=12)
    ax.set_ylabel('ssGSEA Score', fontsize=12)
    ax.tick_params(axis='x', labelsize=11)

    path = os.path.join(output_dir, 'boxplot_system_scores.png')
    plt.savefig(path)
    plt.close()
    return path


# ── 图4: 子类得分排名柱状图 ───────────────────────────────────────────────────

def plot_subcat_barplot(
    subcat_means: Dict[str, float],
    ssgsea_scores: Dict[str, Any],
    dataset_id: str,
    output_dir: str,
) -> str:
    """14个子类均值得分排名柱状图，附匹配基因数标注"""
    codes = list(SUBCAT_LABELS.keys())
    means = [subcat_means.get(c, 0.0) for c in codes]
    matched = [ssgsea_scores.get(c, {}).get('matched_genes', 0) for c in codes]
    labels = [SUBCAT_LABELS[c] for c in codes]
    colors = [SUBCAT_COLORS[c[0]] for c in codes]

    # 按得分排序
    order = np.argsort(means)[::-1]
    codes_s = [codes[i] for i in order]
    means_s = [means[i] for i in order]
    matched_s = [matched[i] for i in order]
    labels_s = [labels[i] for i in order]
    colors_s = [colors[i] for i in order]

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(range(len(codes_s)), means_s, color=colors_s, edgecolor='white', linewidth=0.5)

    # 标注匹配基因数
    for i, (bar, m) in enumerate(zip(bars, matched_s)):
        x = bar.get_width()
        ax.text(x + 0.002, i, f'n={m}', va='center', fontsize=8, color='#555')

    ax.set_yticks(range(len(codes_s)))
    ax.set_yticklabels(labels_s, fontsize=9)
    ax.axvline(0, color='black', linewidth=0.8)
    ax.set_xlabel('Mean ssGSEA Score', fontsize=11)
    ax.set_title(f'{dataset_id} — Subcategory ssGSEA Score Ranking', fontsize=13, fontweight='bold')

    # 图例
    patches = [mpatches.Patch(color=SUBCAT_COLORS[s], label=f'System {s}') for s in 'ABCDE']
    ax.legend(handles=patches, loc='lower right', fontsize=9)

    plt.tight_layout()
    path = os.path.join(output_dir, 'barplot_subcat_ranking.png')
    plt.savefig(path)
    plt.close()
    return path


# ── 图5: 系统间相关性热图 ─────────────────────────────────────────────────────

def plot_system_correlation(
    ssgsea_scores: Dict[str, Any],
    gene_expr_df,
    dataset_id: str,
    output_dir: str,
) -> str:
    """五大系统 ssGSEA 得分的样本间相关性热图"""
    gene_sets = _build_subcategory_gene_sets()
    subcat_to_system = {
        'A1': 'A', 'A2': 'A', 'A3': 'A', 'A4': 'A',
        'B1': 'B', 'B2': 'B', 'B3': 'B',
        'C1': 'C', 'C2': 'C', 'C3': 'C',
        'D1': 'D', 'D2': 'D',
        'E1': 'E', 'E2': 'E',
    }

    system_scores_matrix = {}
    for sys_letter in 'ABCDE':
        codes = [c for c, s in subcat_to_system.items() if s == sys_letter]
        all_genes = list({g for c in codes for g in gene_sets.get(c, [])})
        scores = _compute_ssgsea_scores(gene_expr_df, all_genes)
        system_scores_matrix[f'System {sys_letter}'] = scores

    df_sys = pd.DataFrame(system_scores_matrix)
    corr = df_sys.corr()

    fig, ax = plt.subplots(figsize=(6, 5))
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)  # 只显示下三角

    sns.heatmap(
        corr, ax=ax, mask=mask,
        cmap='RdBu_r', center=0, vmin=-1, vmax=1,
        annot=True, fmt='.2f', annot_kws={'size': 11},
        square=True, linewidths=0.5,
        cbar_kws={'label': 'Pearson r', 'shrink': 0.8},
    )

    ax.set_title(f'{dataset_id} — Inter-System Score Correlation', fontsize=13, fontweight='bold', pad=12)
    ax.tick_params(axis='both', labelsize=10)

    path = os.path.join(output_dir, 'correlation_system_scores.png')
    plt.savefig(path)
    plt.close()
    return path
