"""
自动化计算真实 GO term ssGSEA 分数
从 GEO series matrix 到 GO ssGSEA 的完整流程

Step 1: 解析 GEO series_matrix 为表达矩阵
Step 2: probe → gene symbol 映射
Step 3: 准备 GO 基因集
Step 4: 计算 GO term ssGSEA 分数
Step 5: 保存结果

作者: AI Assistant
日期: 2025-12-03
"""

import pandas as pd
import numpy as np
import gzip
import warnings
from pathlib import Path
import gseapy as gp

warnings.filterwarnings('ignore')

# ============================================================================
# Step 1: 解析 GEO series_matrix 为表达矩阵
# ============================================================================

def load_series_matrix(filepath):
    """
    解析 GEO series_matrix 文件为表达矩阵
    
    Args:
        filepath (str): series_matrix 文件路径 (.txt.gz)
    
    Returns:
        pd.DataFrame: 表达矩阵 (probe × sample)
    """
    print(f"\n{'='*80}")
    print(f"Step 1: 解析 series_matrix 文件")
    print(f"{'='*80}")
    print(f"文件: {filepath}")
    
    # 读取文件（自动处理 .gz 压缩）
    if filepath.endswith('.gz'):
        with gzip.open(filepath, 'rt', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    else:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    
    print(f"  读取了 {len(lines)} 行")
    
    # 跳过所有以 ! 开头的注释行，找到数据起始位置
    data_start_idx = None
    for i, line in enumerate(lines):
        if not line.startswith('!'):
            data_start_idx = i
            break
    
    if data_start_idx is None:
        raise ValueError("未找到数据起始行（所有行都是注释）")
    
    print(f"  数据起始行: {data_start_idx + 1}")
    
    # 提取数据部分
    data_lines = lines[data_start_idx:]
    
    # 跳过空行，找到真正的列名行
    # 注意：第一个非空行可能是 "!Sample_title"，需要跳过
    header_line = None
    header_idx = 0
    for i, line in enumerate(data_lines):
        if line.strip() and not line.startswith('!'):  # 非空且非注释行
            header_line = line.strip().split('\t')
            header_idx = i
            break
    
    if header_line is None:
        raise ValueError("未找到列名行")
    
    print(f"  列名行索引: {header_idx}")
    
    # 清洗列名：删除引号和可能的前缀
    clean_headers = []
    for h in header_line:
        h = h.strip('"').strip()
        # 删除常见的前缀（如 "X", "x"）
        if h.startswith('X') and len(h) > 1 and h[1:].startswith('GSM'):
            h = h[1:]
        elif h.startswith('x') and len(h) > 1 and h[1:].startswith('GSM'):
            h = h[1:]
        clean_headers.append(h)
    
    print(f"  列数: {len(clean_headers)}")
    print(f"  前5列: {clean_headers[:5]}")
    
    # 解析数据行（从列名行的下一行开始）
    data_rows = []
    for line in data_lines[header_idx + 1:]:
        if line.strip():  # 跳过空行
            parts = line.strip().split('\t')
            # 清洗每个值（删除引号）
            clean_parts = [p.strip('"').strip() for p in parts]
            # 确保列数匹配
            if len(clean_parts) == len(clean_headers):
                data_rows.append(clean_parts)
    
    print(f"  数据行数: {len(data_rows)}")
    
    # 创建 DataFrame
    df = pd.DataFrame(data_rows, columns=clean_headers)
    
    # 第一列是 probe ID，设为索引
    df = df.set_index(df.columns[0])
    df.index.name = 'probe_id'
    
    # 将表达值转换为数值类型
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    print(f"\n✓ 表达矩阵: {df.shape}")
    print(f"  Probe 数: {len(df)}")
    print(f"  样本数: {len(df.columns)}")
    print(f"  缺失值: {df.isnull().sum().sum()}")
    
    return df


# ============================================================================
# Step 2: probe → gene symbol 映射
# ============================================================================

def load_gpl_annotation(gpl_filepath, probe_col_candidates=None, gene_col_candidates=None):
    """
    解析 GPL 平台注释文件，提取 probe → gene 映射
    
    Args:
        gpl_filepath (str): GPL 注释文件路径
        probe_col_candidates (list): probe ID 列名候选（自动检测）
        gene_col_candidates (list): gene symbol 列名候选（自动检测）
    
    Returns:
        pd.DataFrame: 包含 probe_id 和 gene_symbol 的映射表
    """
    print(f"\n{'='*80}")
    print(f"Step 2: 解析 GPL 平台注释")
    print(f"{'='*80}")
    print(f"文件: {gpl_filepath}")
    
    # 默认候选列名
    if probe_col_candidates is None:
        probe_col_candidates = ['ID', 'Probe_ID', 'ProbeID', 'PROBE_ID', 'probe_id']
    
    if gene_col_candidates is None:
        gene_col_candidates = [
            'Gene Symbol', 'GENE_SYMBOL', 'Gene_Symbol', 'Symbol', 
            'SYMBOL', 'gene_symbol', 'Gene', 'GENE', 'gene'
        ]
    
    # 读取文件（跳过注释行）
    with open(gpl_filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # 找到数据起始行（跳过 # 或 ! 开头的注释）
    data_start_idx = None
    for i, line in enumerate(lines):
        if not line.startswith('#') and not line.startswith('!'):
            data_start_idx = i
            break
    
    if data_start_idx is None:
        raise ValueError("未找到数据起始行")
    
    print(f"  数据起始行: {data_start_idx + 1}")
    
    # 读取为 DataFrame
    df = pd.read_csv(
        gpl_filepath, 
        sep='\t', 
        skiprows=data_start_idx,
        low_memory=False
    )
    
    print(f"  原始行数: {len(df)}")
    print(f"  列数: {len(df.columns)}")
    print(f"  前10列: {list(df.columns[:10])}")
    
    # 自动识别 probe ID 列
    probe_col = None
    for candidate in probe_col_candidates:
        if candidate in df.columns:
            probe_col = candidate
            break
    
    if probe_col is None:
        # 如果没找到，使用第一列
        probe_col = df.columns[0]
        print(f"  ⚠️  未找到标准 probe ID 列，使用第一列: {probe_col}")
    else:
        print(f"  ✓ Probe ID 列: {probe_col}")
    
    # 自动识别 gene symbol 列
    gene_col = None
    for candidate in gene_col_candidates:
        if candidate in df.columns:
            gene_col = candidate
            break
    
    if gene_col is None:
        raise ValueError(f"未找到 gene symbol 列，可用列: {list(df.columns)}")
    
    print(f"  ✓ Gene Symbol 列: {gene_col}")
    
    # 提取映射关系
    mapping = df[[probe_col, gene_col]].copy()
    mapping.columns = ['probe_id', 'gene_symbol']
    
    # 清洗 gene symbol
    # 1. 删除空值
    mapping = mapping.dropna(subset=['gene_symbol'])
    
    # 2. 删除空字符串和 "---"
    mapping = mapping[mapping['gene_symbol'].str.strip() != '']
    mapping = mapping[mapping['gene_symbol'].str.strip() != '---']
    
    # 3. 处理多个基因符号（用 /// 或 // 分隔）
    # 策略：只保留第一个基因符号
    mapping['gene_symbol'] = mapping['gene_symbol'].str.split('///').str[0]
    mapping['gene_symbol'] = mapping['gene_symbol'].str.split('//').str[0]
    mapping['gene_symbol'] = mapping['gene_symbol'].str.strip()
    
    print(f"\n✓ 映射关系:")
    print(f"  有效映射数: {len(mapping)}")
    print(f"  唯一 probe 数: {mapping['probe_id'].nunique()}")
    print(f"  唯一 gene 数: {mapping['gene_symbol'].nunique()}")
    
    return mapping


def map_probe_to_gene(expr_df, mapping_df, method='mean'):
    """
    将 probe 表达矩阵映射为 gene 表达矩阵
    
    Args:
        expr_df (pd.DataFrame): probe × sample 表达矩阵
        mapping_df (pd.DataFrame): probe → gene 映射表
        method (str): 多个 probe 映射到同一基因时的聚合方法
                     'mean' (默认): 取平均值
                     'max': 取最大值（适用于多个 probe 可能有噪声的情况）
                     'median': 取中位数
    
    Returns:
        pd.DataFrame: gene × sample 表达矩阵
    """
    print(f"\n{'='*80}")
    print(f"Step 2 (续): Probe → Gene 映射")
    print(f"{'='*80}")
    print(f"聚合方法: {method}")
    
    # 合并表达数据和映射关系
    expr_df_reset = expr_df.reset_index()
    merged = expr_df_reset.merge(
        mapping_df, 
        left_on='probe_id', 
        right_on='probe_id', 
        how='inner'
    )
    
    print(f"\n  合并后保留的 probe 数: {len(merged)}")
    print(f"  丢弃的 probe 数: {len(expr_df) - len(merged)}")
    
    # 删除 probe_id 列，只保留 gene_symbol 和表达值
    merged = merged.drop('probe_id', axis=1)
    
    # 按 gene_symbol 分组聚合
    if method == 'mean':
        gene_expr = merged.groupby('gene_symbol').mean()
    elif method == 'max':
        gene_expr = merged.groupby('gene_symbol').max()
    elif method == 'median':
        gene_expr = merged.groupby('gene_symbol').median()
    else:
        raise ValueError(f"不支持的聚合方法: {method}")
    
    print(f"\n✓ Gene 表达矩阵: {gene_expr.shape}")
    print(f"  基因数: {len(gene_expr)}")
    print(f"  样本数: {len(gene_expr.columns)}")
    
    # 统计多个 probe 映射到同一基因的情况
    probe_per_gene = merged.groupby('gene_symbol').size()
    multi_probe_genes = probe_per_gene[probe_per_gene > 1]
    print(f"\n  多 probe 基因数: {len(multi_probe_genes)}")
    if len(multi_probe_genes) > 0:
        print(f"  最多 probe 数: {multi_probe_genes.max()}")
        print(f"  示例: {multi_probe_genes.head(3).to_dict()}")
    
    return gene_expr


# ============================================================================
# Step 3: 准备 GO 基因集
# ============================================================================

def load_go_genesets():
    """
    从 gseapy 加载 GO Biological Process 基因集
    
    Returns:
        dict: GO 基因集 {term_name: [gene1, gene2, ...]}
    """
    print(f"\n{'='*80}")
    print(f"Step 3: 加载 GO Biological Process 基因集")
    print(f"{'='*80}")
    
    try:
        # 尝试加载 GO-BP 基因集
        print("  尝试加载 GO_Biological_Process_2023...")
        gene_sets = gp.get_library_name()
        
        # 查找可用的 GO-BP 版本
        go_bp_versions = [name for name in gene_sets if 'GO_Biological_Process' in name]
        print(f"  可用的 GO-BP 版本: {go_bp_versions[:5]}")
        
        # 使用最新版本
        if go_bp_versions:
            go_bp_name = go_bp_versions[0]
        else:
            # 备选方案
            go_bp_name = 'GO_Biological_Process_2023'
        
        print(f"  使用版本: {go_bp_name}")
        
        # 下载基因集
        gene_sets_dict = gp.get_library(name=go_bp_name, organism='Human')
        
        print(f"\n✓ GO 基因集加载完成:")
        print(f"  GO term 数: {len(gene_sets_dict)}")
        
        # 显示示例
        sample_terms = list(gene_sets_dict.keys())[:3]
        for term in sample_terms:
            print(f"  {term}: {len(gene_sets_dict[term])} genes")
        
        return gene_sets_dict
    
    except Exception as e:
        print(f"  ❌ 加载失败: {e}")
        print(f"\n  尝试备选方案...")
        
        # 备选方案：使用本地 GMT 文件或其他来源
        # 这里可以添加从本地文件加载的代码
        raise RuntimeError("无法加载 GO 基因集，请检查网络连接或使用本地 GMT 文件")


# ============================================================================
# Step 4: 计算 GO term ssGSEA 分数
# ============================================================================

def compute_ssgsea(gene_expr_df, gene_sets_dict, output_path=None):
    """
    计算 ssGSEA 分数
    
    Args:
        gene_expr_df (pd.DataFrame): gene × sample 表达矩阵
        gene_sets_dict (dict): GO 基因集
        output_path (str): 输出文件路径（可选）
    
    Returns:
        pd.DataFrame: GO term × sample ssGSEA 分数矩阵
    """
    print(f"\n{'='*80}")
    print(f"Step 4: 计算 ssGSEA 分数")
    print(f"{'='*80}")
    
    print(f"  输入矩阵: {gene_expr_df.shape}")
    print(f"  基因集数: {len(gene_sets_dict)}")
    
    # gseapy.ssgsea 的输入格式要求：
    # - DataFrame: gene × sample (基因为行，样本为列)
    # - 或者 sample × gene (样本为行，基因为列)
    # 根据文档，应该是 gene × sample 格式，不需要转置
    expr_for_ssgsea = gene_expr_df.copy()
    
    print(f"  输入格式: {expr_for_ssgsea.shape} (gene × sample)")
    print(f"  基因数: {len(expr_for_ssgsea)}")
    print(f"  样本数: {len(expr_for_ssgsea.columns)}")
    print(f"  前5个基因: {list(expr_for_ssgsea.index[:5])}")
    print(f"  前5个样本: {list(expr_for_ssgsea.columns[:5])}")
    
    try:
        # 运行 ssGSEA
        print(f"\n  开始计算 ssGSEA...")
        print(f"  (这可能需要几分钟，取决于数据集大小)")
        
        ss = gp.ssgsea(
            data=expr_for_ssgsea,
            gene_sets=gene_sets_dict,
            outdir=None,  # 不保存中间文件
            sample_norm_method='rank',  # 标准化方法
            no_plot=True,  # 不生成图表
            processes=4,  # 并行进程数
            min_size=15,  # 最小基因集大小
            max_size=500,  # 最大基因集大小
            permutation_num=0  # ssGSEA 不需要 permutation
        )
        
        # 提取结果
        # gseapy 的 ssgsea 结果存储在 ss.res2d 中
        # 格式: DataFrame with columns ['Name', 'Term', 'ES', 'NES']
        # Name 是样本名，Term 是 GO term，NES 是标准化富集分数
        
        res_df = ss.res2d
        print(f"\n  原始结果: {res_df.shape}")
        print(f"  列: {list(res_df.columns)}")
        
        # 转换为 term × sample 矩阵
        # 使用 pivot 将长格式转换为宽格式
        ssgsea_scores = res_df.pivot(index='Term', columns='Name', values='NES')
        
        print(f"\n✓ ssGSEA 计算完成:")
        print(f"  结果矩阵: {ssgsea_scores.shape}")
        print(f"  GO term 数: {len(ssgsea_scores)}")
        print(f"  样本数: {len(ssgsea_scores.columns)}")
        
        # 保存结果
        if output_path:
            ssgsea_scores.to_csv(output_path, encoding='utf-8-sig')
            print(f"  ✓ 已保存: {output_path}")
        
        return ssgsea_scores
    
    except Exception as e:
        print(f"  ❌ ssGSEA 计算失败: {e}")
        raise


# ============================================================================
# Step 5: 主函数 - 完整流程
# ============================================================================

def process_dataset(dataset_name, series_matrix_path, gpl_path, output_dir):
    """
    处理单个数据集的完整流程
    
    Args:
        dataset_name (str): 数据集名称（如 'GSE21899'）
        series_matrix_path (str): series_matrix 文件路径
        gpl_path (str): GPL 注释文件路径
        output_dir (str): 输出目录
    """
    print(f"\n{'#'*80}")
    print(f"# 处理数据集: {dataset_name}")
    print(f"{'#'*80}")
    
    # 创建输出目录
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Step 1: 加载表达矩阵
        expr_df = load_series_matrix(series_matrix_path)
        
        # 保存 probe 表达矩阵
        probe_expr_path = output_dir / 'probe_expression.csv'
        expr_df.to_csv(probe_expr_path, encoding='utf-8-sig')
        print(f"\n✓ Probe 表达矩阵已保存: {probe_expr_path}")
        
        # Step 2: 加载 GPL 注释并映射
        mapping_df = load_gpl_annotation(gpl_path)
        
        # 映射 probe → gene
        gene_expr_df = map_probe_to_gene(expr_df, mapping_df, method='mean')
        
        # 保存 gene 表达矩阵
        gene_expr_path = output_dir / 'gene_expression.csv'
        gene_expr_df.to_csv(gene_expr_path, encoding='utf-8-sig')
        print(f"\n✓ Gene 表达矩阵已保存: {gene_expr_path}")
        
        # Step 3: 加载 GO 基因集（只需加载一次）
        if not hasattr(process_dataset, 'gene_sets'):
            process_dataset.gene_sets = load_go_genesets()
        
        # Step 4: 计算 ssGSEA
        ssgsea_path = output_dir / 'go_ssgsea.csv'
        ssgsea_scores = compute_ssgsea(
            gene_expr_df, 
            process_dataset.gene_sets,
            output_path=ssgsea_path
        )
        
        print(f"\n{'='*80}")
        print(f"✓ {dataset_name} 处理完成！")
        print(f"{'='*80}")
        print(f"生成的文件:")
        print(f"  - {probe_expr_path}")
        print(f"  - {gene_expr_path}")
        print(f"  - {ssgsea_path}")
        
        return True
    
    except Exception as e:
        print(f"\n{'='*80}")
        print(f"❌ {dataset_name} 处理失败: {e}")
        print(f"{'='*80}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    主函数：处理所有数据集
    """
    print("="*80)
    print("自动化计算真实 GO term ssGSEA 分数")
    print("="*80)
    
    # 配置数据集
    # 注意：GSE28914 实际使用的是 GPL570，而不是 GPL6480
    datasets = {
        'GSE21899': {
            'series_matrix': '验证数据集/GSE21899_series_matrix.txt.gz',
            'gpl': '验证数据集/GPL570-55999.txt',
            'output_dir': 'results/GSE21899'
        },
        'GSE28914': {
            'series_matrix': '验证数据集/GSE28914_series_matrix.txt.gz',
            'gpl': '验证数据集/GPL570-55999.txt',  # 修正：使用 GPL570
            'output_dir': 'results/GSE28914'
        },
        'GSE65682': {
            'series_matrix': '验证数据集/GSE65682_series_matrix.txt.gz',
            'gpl': '验证数据集/GPL13667-15572.txt',
            'output_dir': 'results/GSE65682'
        }
    }
    
    # 处理每个数据集
    results = {}
    for dataset_name, config in datasets.items():
        success = process_dataset(
            dataset_name=dataset_name,
            series_matrix_path=config['series_matrix'],
            gpl_path=config['gpl'],
            output_dir=config['output_dir']
        )
        results[dataset_name] = success
    
    # 打印总结
    print(f"\n{'='*80}")
    print("处理总结")
    print(f"{'='*80}")
    for dataset_name, success in results.items():
        status = "✓ 成功" if success else "❌ 失败"
        print(f"  {dataset_name}: {status}")
    
    print(f"\n{'='*80}")
    print("所有任务完成！")
    print(f"{'='*80}")
    print("\n下一步：")
    print("  1. 检查 results/ 目录下的输出文件")
    print("  2. 将 go_ssgsea.csv 文件复制到 数据/对比实验/ 目录")
    print("  3. 重新运行 compare_v75_vs_pca.py 进行对比实验")


if __name__ == "__main__":
    main()
