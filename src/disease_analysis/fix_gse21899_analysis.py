#!/usr/bin/env python3
"""
Fixed GSE21899 Analysis - Handle probe ID mismatch
"""

import pandas as pd
import numpy as np
import gzip
import os

def check_probe_id_formats():
    """检查探针ID格式"""
    
    print("Checking probe ID formats...")
    
    # 表达数据
    data_path = "data/validation_datasets/GSE21899/GSE21899_series_matrix.txt.gz"
    with gzip.open(data_path, 'rt', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    data_start = None
    for i, line in enumerate(lines):
        if line.startswith('!series_matrix_table_begin'):
            data_start = i + 1
            break
    
    data_lines = []
    for line in lines[data_start:]:
        if line.startswith('!series_matrix_table_end'):
            break
        data_lines.append(line.strip().split('\t'))
    
    header = [col.strip('"') for col in data_lines[0]]
    data_rows = [[cell.strip('"') for cell in row] for row in data_lines[1:]]
    
    expr_df = pd.DataFrame(data_rows, columns=header)
    expr_df = expr_df.set_index('ID_REF')
    
    print(f"Expression probe IDs (first 10): {expr_df.index[:10].tolist()}")
    
    # 平台注释
    platform_file = "data/validation_datasets/GSE21899/GPL6480-9577.txt"
    with open(platform_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    data_start = None
    for i, line in enumerate(lines):
        if line.startswith('ID\t') or line.startswith('"ID"'):
            data_start = i
            break
        elif line.startswith('!platform_table_begin'):
            data_start = i + 1
            break
    
    platform_lines = []
    for line in lines[data_start:]:
        if line.startswith('!platform_table_end'):
            break
        platform_lines.append(line.strip().split('\t'))
    
    platform_header = [col.strip('"') for col in platform_lines[0]]
    platform_data = [[cell.strip('"') for cell in row] for row in platform_lines[1:]]
    
    platform_df = pd.DataFrame(platform_data, columns=platform_header)
    
    print(f"Platform probe IDs (first 10): {platform_df['ID'][:10].tolist()}")
    
    # 检查是否有匹配
    expr_ids = set(expr_df.index)
    platform_ids = set(platform_df['ID'])
    
    print(f"Expression IDs count: {len(expr_ids)}")
    print(f"Platform IDs count: {len(platform_ids)}")
    print(f"Matching IDs: {len(expr_ids & platform_ids)}")
    
    # 检查是否有部分匹配
    expr_sample = list(expr_ids)[:100]
    platform_sample = list(platform_ids)[:100]
    
    print(f"\nSample expression IDs: {expr_sample[:5]}")
    print(f"Sample platform IDs: {platform_sample[:5]}")
    
    # 尝试找到匹配模式
    for expr_id in expr_sample[:10]:
        for platform_id in platform_sample[:10]:
            if expr_id in platform_id or platform_id in expr_id:
                print(f"Potential match: {expr_id} <-> {platform_id}")
    
    return expr_df, platform_df

def create_fixed_gse21899_analysis():
    """创建修复的GSE21899分析"""
    
    print("="*80)
    print("FIXED GSE21899 ANALYSIS")
    print("="*80)
    
    expr_df, platform_df = check_probe_id_formats()
    
    # 由于探针ID不匹配，我们需要使用不同的策略
    # 检查平台文件中是否有其他ID列可以匹配
    
    print(f"\nPlatform columns: {platform_df.columns.tolist()}")
    
    # 检查各种可能的ID列
    id_column = 'ID'  # 默认使用ID列
    
    if 'SPOT_ID' in platform_df.columns:
        spot_ids = set(platform_df['SPOT_ID'].dropna())
        expr_ids = set(expr_df.index)
        matching_spot = len(spot_ids & expr_ids)
        print(f"SPOT_ID matches: {matching_spot}")
        
        if matching_spot > 0:
            print("Using SPOT_ID for matching...")
            id_column = 'SPOT_ID'
    
    if id_column == 'ID':
        # 尝试其他列
        for col in ['REFSEQ', 'GB_ACC', 'ACCESSION_STRING']:
            if col in platform_df.columns:
                col_ids = set(platform_df[col].dropna())
                matching_col = len(col_ids & expr_ids)
                print(f"{col} matches: {matching_col}")
                if matching_col > 0:
                    id_column = col
                    break
    
    # 创建探针到基因的映射
    print(f"\nCreating probe-to-gene mapping using {id_column}...")
    
    # 找到基因符号列
    gene_symbol_col = None
    for col in platform_df.columns:
        col_lower = col.lower()
        if any(term in col_lower for term in ['gene_symbol', 'gene symbol', 'symbol', 'gene_name', 'gene name']):
            gene_symbol_col = col
            break
    
    if gene_symbol_col is None:
        print("❌ No gene symbol column found")
        return None, None
    
    print(f"Using gene symbol column: {gene_symbol_col}")
    
    # 过滤有效的基因符号
    valid_platform = platform_df[
        (platform_df[gene_symbol_col].notna()) & 
        (platform_df[gene_symbol_col] != '') & 
        (platform_df[gene_symbol_col] != '---')
    ].copy()
    
    print(f"Valid gene symbols in platform: {len(valid_platform)}")
    
    # 转换表达数据为数值
    print("Converting expression data to numeric...")
    for col in expr_df.columns:
        expr_df[col] = pd.to_numeric(expr_df[col], errors='coerce')
    
    # 创建基因表达矩阵
    gene_expr = {}
    
    # 检查是否有ID匹配
    expr_ids = set(expr_df.index)
    platform_ids = set(valid_platform[id_column])
    matching_ids = expr_ids & platform_ids
    
    print(f"ID matching: {len(matching_ids)} matches found")
    
    if len(matching_ids) > 0:
        # 使用ID匹配
        print("Using ID-based matching...")
        for _, row in valid_platform.iterrows():
            probe_id = row[id_column]
            gene_symbol = row[gene_symbol_col]
            
            if probe_id in expr_df.index:
                probe_expr = expr_df.loc[probe_id]
                
                if not probe_expr.isna().all():
                    if gene_symbol not in gene_expr:
                        gene_expr[gene_symbol] = []
                    gene_expr[gene_symbol].append(probe_expr)
    else:
        # 使用位置匹配（假设顺序相同）
        print("Using position-based matching...")
        
        # 确保两个数据框的长度匹配
        min_length = min(len(expr_df), len(valid_platform))
        
        for i in range(min_length):
            if i < len(expr_df) and i < len(valid_platform):
                probe_expr = expr_df.iloc[i]
                gene_symbol = valid_platform.iloc[i][gene_symbol_col]
                
                if gene_symbol and gene_symbol not in ['', '---']:
                    if not probe_expr.isna().all():
                        if gene_symbol not in gene_expr:
                            gene_expr[gene_symbol] = []
                        gene_expr[gene_symbol].append(probe_expr)
    
    print(f"Genes with expression data: {len(gene_expr)}")
    
    if len(gene_expr) == 0:
        print("❌ No gene expression data found")
        return None, None
    
    # 创建基因表达矩阵
    print("Creating final gene expression matrix...")
    gene_expr_df = pd.DataFrame()
    
    for gene, expr_list in gene_expr.items():
        if len(expr_list) == 1:
            gene_expr_df[gene] = expr_list[0]
        else:
            # 多个探针求平均
            try:
                gene_expr_df[gene] = pd.concat(expr_list, axis=1).mean(axis=1)
            except Exception as e:
                print(f"Warning: Could not process gene {gene}: {e}")
                continue
    
    if gene_expr_df.empty:
        print("❌ Failed to create gene expression matrix")
        return None, None
    
    gene_expr_df = gene_expr_df.T  # 转置，基因为行
    
    print(f"✅ Created gene expression matrix: {gene_expr_df.shape}")
    
    # 处理重复基因名（取平均值）
    if gene_expr_df.index.duplicated().any():
        print("Handling duplicate gene names...")
        gene_expr_df = gene_expr_df.groupby(gene_expr_df.index).mean()
        print(f"After removing duplicates: {gene_expr_df.shape}")
    
    return gene_expr_df, expr_df

if __name__ == "__main__":
    gene_expr_df, expr_df = create_fixed_gse21899_analysis()
    
    if gene_expr_df is not None:
        print(f"\n✅ Successfully created gene expression matrix!")
        print(f"Shape: {gene_expr_df.shape}")
        print(f"Sample genes: {gene_expr_df.index[:5].tolist()}")
        print(f"Sample values: {gene_expr_df.iloc[0, :3].values}")
    else:
        print(f"\n❌ Failed to create gene expression matrix")