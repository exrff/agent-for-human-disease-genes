#!/usr/bin/env python3
"""
Debug GSE21899 data processing issues
"""

import pandas as pd
import numpy as np
import gzip
import os

def debug_gse21899():
    """调试GSE21899数据处理问题"""
    
    print("="*80)
    print("DEBUGGING GSE21899 DATA PROCESSING")
    print("="*80)
    
    # 1. 检查表达数据
    data_path = "data/validation_datasets/GSE21899/GSE21899_series_matrix.txt.gz"
    platform_file = "data/validation_datasets/GSE21899/GPL6480-9577.txt"
    
    print("\n1. Loading expression data...")
    
    with gzip.open(data_path, 'rt', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # 找到数据开始位置
    data_start = None
    sample_info = {}
    
    for i, line in enumerate(lines):
        if line.startswith('!Sample_title'):
            titles = line.strip().split('\t')[1:]
            sample_info['titles'] = [t.strip('"') for t in titles]
        elif line.startswith('!Sample_geo_accession'):
            accessions = line.strip().split('\t')[1:]
            sample_info['accessions'] = [a.strip('"') for a in accessions]
        elif line.startswith('!series_matrix_table_begin'):
            data_start = i + 1
            break
    
    print(f"Data starts at line: {data_start}")
    print(f"Sample titles: {sample_info.get('titles', [])[:3]}...")
    print(f"Sample accessions: {sample_info.get('accessions', [])[:3]}...")
    
    # 读取数据表
    data_lines = []
    for line in lines[data_start:]:
        if line.startswith('!series_matrix_table_end'):
            break
        data_lines.append(line.strip().split('\t'))
    
    print(f"Data lines: {len(data_lines)}")
    
    # 创建DataFrame
    header = [col.strip('"') for col in data_lines[0]]
    data_rows = [[cell.strip('"') for cell in row] for row in data_lines[1:]]
    
    expr_df = pd.DataFrame(data_rows, columns=header)
    expr_df = expr_df.set_index('ID_REF')
    
    print(f"Expression DataFrame shape: {expr_df.shape}")
    print(f"Columns: {expr_df.columns.tolist()}")
    print(f"Index (first 5): {expr_df.index[:5].tolist()}")
    
    # 转换为数值
    for col in expr_df.columns:
        expr_df[col] = pd.to_numeric(expr_df[col], errors='coerce')
    
    print(f"After numeric conversion:")
    print(f"Expression range: {expr_df.min().min():.2f} to {expr_df.max().max():.2f}")
    print(f"NaN values: {expr_df.isna().sum().sum()}")
    
    # 2. 检查平台注释
    print(f"\n2. Loading platform annotation...")
    
    with open(platform_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # 找到数据开始位置
    data_start = None
    for i, line in enumerate(lines):
        if line.startswith('ID\t') or line.startswith('"ID"'):
            data_start = i
            break
        elif line.startswith('!platform_table_begin'):
            data_start = i + 1
            break
    
    print(f"Platform data starts at line: {data_start}")
    
    # 读取平台数据
    platform_lines = []
    for line in lines[data_start:]:
        if line.startswith('!platform_table_end'):
            break
        platform_lines.append(line.strip().split('\t'))
    
    platform_header = [col.strip('"') for col in platform_lines[0]]
    platform_data = [[cell.strip('"') for cell in row] for row in platform_lines[1:]]
    
    platform_df = pd.DataFrame(platform_data, columns=platform_header)
    
    print(f"Platform DataFrame shape: {platform_df.shape}")
    print(f"Platform columns: {platform_df.columns.tolist()}")
    
    # 查找基因符号列
    gene_symbol_cols = []
    for col in platform_df.columns:
        col_lower = col.lower()
        if any(term in col_lower for term in ['gene_symbol', 'gene symbol', 'symbol', 'gene_name', 'gene name']):
            gene_symbol_cols.append(col)
    
    print(f"Gene symbol columns: {gene_symbol_cols}")
    
    if gene_symbol_cols:
        gene_col = gene_symbol_cols[0]
        print(f"Using gene symbol column: {gene_col}")
        
        # 检查基因符号
        gene_symbols = platform_df[gene_col].value_counts()
        print(f"Total gene symbols: {len(gene_symbols)}")
        print(f"Non-empty gene symbols: {len(gene_symbols[gene_symbols.index != ''])}")
        print(f"Sample gene symbols: {gene_symbols.head().index.tolist()}")
        
        # 检查探针ID匹配
        platform_probe_ids = set(platform_df['ID'].tolist())
        expr_probe_ids = set(expr_df.index.tolist())
        
        print(f"\n3. Probe ID matching:")
        print(f"Platform probe IDs: {len(platform_probe_ids)}")
        print(f"Expression probe IDs: {len(expr_probe_ids)}")
        print(f"Matching probe IDs: {len(platform_probe_ids & expr_probe_ids)}")
        
        # 检查匹配的探针中有多少有基因符号
        matching_probes = platform_probe_ids & expr_probe_ids
        matching_platform = platform_df[platform_df['ID'].isin(matching_probes)]
        
        valid_gene_symbols = matching_platform[
            (matching_platform[gene_col].notna()) & 
            (matching_platform[gene_col] != '') & 
            (matching_platform[gene_col] != '---')
        ]
        
        print(f"Matching probes with valid gene symbols: {len(valid_gene_symbols)}")
        
        if len(valid_gene_symbols) > 0:
            print(f"Sample valid mappings:")
            for i, (_, row) in enumerate(valid_gene_symbols.head().iterrows()):
                print(f"  {row['ID']} -> {row[gene_col]}")
        
        # 4. 尝试创建基因表达矩阵
        print(f"\n4. Creating gene expression matrix...")
        
        gene_expr = {}
        
        for _, row in valid_gene_symbols.iterrows():
            probe_id = row['ID']
            gene_symbol = row[gene_col]
            
            if probe_id in expr_df.index:
                probe_expr = expr_df.loc[probe_id]
                
                # 检查是否全为NaN
                if not probe_expr.isna().all():
                    if gene_symbol not in gene_expr:
                        gene_expr[gene_symbol] = []
                    gene_expr[gene_symbol].append(probe_expr)
        
        print(f"Genes with expression data: {len(gene_expr)}")
        
        if len(gene_expr) > 0:
            # 创建基因表达矩阵
            gene_expr_df = pd.DataFrame()
            for gene, expr_list in gene_expr.items():
                if len(expr_list) == 1:
                    gene_expr_df[gene] = expr_list[0]
                else:
                    gene_expr_df[gene] = pd.concat(expr_list, axis=1).mean(axis=1)
            
            gene_expr_df = gene_expr_df.T
            
            print(f"Final gene expression matrix: {gene_expr_df.shape}")
            print(f"Sample genes: {gene_expr_df.index[:5].tolist()}")
            print(f"Sample values: {gene_expr_df.iloc[0, :3].tolist()}")
            
            return gene_expr_df, sample_info
        else:
            print("❌ No genes with valid expression data found")
            return None, None

if __name__ == "__main__":
    debug_gse21899()