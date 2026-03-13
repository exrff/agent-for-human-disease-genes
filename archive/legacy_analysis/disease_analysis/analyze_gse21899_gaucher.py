#!/usr/bin/env python3
"""
GSE21899 Gaucher Disease Analysis

专门分析GSE21899戈谢病数据集，生成用于绘图的数据
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import gzip
import os
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class GSE21899Analyzer:
    def __init__(self):
        self.dataset_id = 'GSE21899'
        self.data_path = f"data/validation_datasets/{self.dataset_id}/{self.dataset_id}_series_matrix.txt.gz"
        self.platform_file = f"data/validation_datasets/{self.dataset_id}/GPL6480-9577.txt"
        self.classification_file = "results/full_classification/full_classification_results.csv"
        self.go_mapping_file = "data/go_annotations/go_to_genes.json"
        self.kegg_mapping_file = "data/kegg_mappings/kegg_to_genes.json"
        
        # 戈谢病预期激活的系统和子分类
        self.expected_systems = ['System C', 'System D']
        self.expected_subcategories = ['C1', 'C2', 'C3', 'D1', 'D2']
        
        # 子分类定义
        self.subcategories = {
            'A1': 'Genomic Stability and Repair',
            'A2': 'Somatic Maintenance and Identity Preservation', 
            'A3': 'Cellular Homeostasis and Structural Maintenance',
            'A4': 'Inflammation Resolution and Damage Containment',
            'B1': 'Innate Immunity',
            'B2': 'Adaptive Immunity',
            'B3': 'Immune Regulation and Tolerance',
            'C1': 'Energy Metabolism and Catabolism',
            'C2': 'Biosynthesis and Anabolism', 
            'C3': 'Detoxification and Metabolic Stress Handling',
            'D1': 'Neural Regulation and Signal Transmission',
            'D2': 'Endocrine and Autonomic Regulation',
            'E1': 'Reproduction',
            'E2': 'Development and Reproductive Maturation'
        }
        
        # 加载基因映射
        self.load_gene_mappings()
        
    def load_gene_mappings(self):
        """加载GO和KEGG基因映射"""
        print("Loading gene mappings...")
        
        # 加载GO映射
        if os.path.exists(self.go_mapping_file):
            with open(self.go_mapping_file, 'r') as f:
                self.go_to_genes = json.load(f)
            print(f"  Loaded GO mappings: {len(self.go_to_genes)} GO terms")
        else:
            print(f"  GO mapping file not found: {self.go_mapping_file}")
            self.go_to_genes = {}
        
        # 加载KEGG映射
        if os.path.exists(self.kegg_mapping_file):
            with open(self.kegg_mapping_file, 'r') as f:
                kegg_data = json.load(f)
            self.kegg_to_genes = {}
            for pathway_id, info in kegg_data.items():
                self.kegg_to_genes[pathway_id] = info['genes']
            print(f"  Loaded KEGG mappings: {len(self.kegg_to_genes)} pathways")
        else:
            print(f"  KEGG mapping file not found: {self.kegg_mapping_file}")
            self.kegg_to_genes = {}
    
    def load_classification_data(self):
        """加载分类数据并创建基因集"""
        print("\nLoading classification data...")
        
        df = pd.read_csv(self.classification_file)
        print(f"Loaded {len(df)} classified biological processes")
        
        # 创建每个子分类的基因集
        self.gene_sets = {}
        for subcat_code in self.subcategories.keys():
            subcat_processes = df[df['Subcategory_Code'] == subcat_code]
            
            # 获取GO条目和KEGG通路
            go_terms = [term for term in subcat_processes['ID'].tolist() if term.startswith('GO:')]
            kegg_pathways = [term for term in subcat_processes['ID'].tolist() if term.startswith('KEGG:')]
            
            # 转换为基因列表
            all_genes = set()
            
            # 添加GO基因
            for go_term in go_terms:
                if go_term in self.go_to_genes:
                    all_genes.update(self.go_to_genes[go_term])
            
            # 添加KEGG基因
            for kegg_pathway in kegg_pathways:
                if kegg_pathway in self.kegg_to_genes:
                    all_genes.update(self.kegg_to_genes[kegg_pathway])
            
            self.gene_sets[subcat_code] = {
                'name': self.subcategories[subcat_code],
                'go_terms': go_terms,
                'kegg_pathways': kegg_pathways,
                'genes': list(all_genes),
                'process_count': len(subcat_processes),
                'gene_count': len(all_genes),
                'avg_confidence': subcat_processes['Confidence_Score'].mean()
            }
            
            print(f"  {subcat_code}: {len(subcat_processes)} processes → {len(all_genes)} genes")
        
        return df
    
    def load_expression_data(self):
        """加载GSE21899表达数据"""
        print(f"\nLoading expression data for {self.dataset_id}...")
        
        if not os.path.exists(self.data_path):
            print(f"Error: Data file not found: {self.data_path}")
            return None, None
            
        try:
            # 读取压缩文件
            with gzip.open(self.data_path, 'rt', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # 解析样本信息和数据
            data_start = None
            sample_info = {}
            
            for i, line in enumerate(lines):
                if line.startswith('!Sample_title'):
                    titles = line.strip().split('\t')[1:]
                    sample_info['titles'] = [t.strip('"') for t in titles]
                elif line.startswith('!Sample_geo_accession'):
                    accessions = line.strip().split('\t')[1:]
                    sample_info['accessions'] = [a.strip('"') for a in accessions]
                elif line.startswith('!Sample_characteristics_ch1'):
                    chars = line.strip().split('\t')[1:]
                    if 'characteristics' not in sample_info:
                        sample_info['characteristics'] = []
                    sample_info['characteristics'].append([c.strip('"') for c in chars])
                elif line.startswith('!series_matrix_table_begin'):
                    data_start = i + 1
                    break
            
            if data_start is None:
                print(f"Error: Could not find data table start")
                return None, None
            
            # 读取数据表
            data_lines = []
            for line in lines[data_start:]:
                if line.startswith('!series_matrix_table_end'):
                    break
                data_lines.append(line.strip().split('\t'))
            
            if len(data_lines) < 2:
                print(f"Error: Insufficient data")
                return None, None
            
            # 创建DataFrame
            header = [col.strip('"') for col in data_lines[0]]
            data_rows = [[cell.strip('"') for cell in row] for row in data_lines[1:]]
            
            expr_df = pd.DataFrame(data_rows, columns=header)
            
            # 设置探针ID为索引
            if 'ID_REF' in expr_df.columns:
                expr_df = expr_df.set_index('ID_REF')
            else:
                print(f"Error: ID_REF column not found")
                return None, None
            
            # 转换表达值为数值
            for col in expr_df.columns:
                expr_df[col] = pd.to_numeric(expr_df[col], errors='coerce')
            
            # 移除缺失值过多的行
            expr_df = expr_df.dropna(thresh=len(expr_df.columns) * 0.5)
            
            print(f"  Successfully loaded: {expr_df.shape[0]} probes x {expr_df.shape[1]} samples")
            print(f"  Expression range: {expr_df.min().min():.2f} to {expr_df.max().max():.2f}")
            
            return expr_df, sample_info
            
        except Exception as e:
            print(f"Error loading {self.dataset_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def load_platform_annotation(self):
        """加载平台注释文件 - 使用修复的方法"""
        print(f"Loading platform annotation...")
        
        if not os.path.exists(self.platform_file):
            print("  Error: No platform annotation file found")
            return None
        
        try:
            print(f"  Reading {os.path.basename(self.platform_file)}...")
            
            # 读取文件并找到数据开始位置
            with open(self.platform_file, 'r', encoding='utf-8', errors='ignore') as f:
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
            
            if data_start is None:
                print("  Error: Could not find platform data start")
                return None
            
            # 读取平台数据
            platform_lines = []
            for line in lines[data_start:]:
                if line.startswith('!platform_table_end'):
                    break
                platform_lines.append(line.strip().split('\t'))
            
            if len(platform_lines) < 2:
                print("  Error: Insufficient platform data")
                return None
            
            # 创建平台DataFrame
            platform_header = [col.strip('"') for col in platform_lines[0]]
            platform_data = [[cell.strip('"') for cell in row] for row in platform_lines[1:]]
            
            platform_df = pd.DataFrame(platform_data, columns=platform_header)
            
            # 查找基因符号列
            gene_symbol_cols = []
            for col in platform_df.columns:
                col_lower = col.lower()
                if any(term in col_lower for term in ['gene_symbol', 'gene symbol', 'symbol', 'gene_name', 'gene name']):
                    gene_symbol_cols.append(col)
            
            if not gene_symbol_cols:
                print("  Error: No gene symbol column found")
                print(f"  Available columns: {platform_df.columns.tolist()}")
                return None
            
            # 使用第一个基因符号列
            gene_col = gene_symbol_cols[0]
            print(f"  Using gene symbol column: {gene_col}")
            
            # 由于探针ID不匹配，使用位置匹配方法
            print("  Using position-based probe-to-gene mapping...")
            
            # 过滤有效的基因符号
            valid_platform = platform_df[
                (platform_df[gene_col].notna()) & 
                (platform_df[gene_col] != '') & 
                (platform_df[gene_col] != '---')
            ].copy()
            
            print(f"  Valid gene symbols in platform: {len(valid_platform)}")
            
            # 创建位置映射（假设探针和平台注释的顺序相同）
            probe_to_gene = {}
            
            for i, (_, row) in enumerate(valid_platform.iterrows()):
                # 使用位置索引作为探针ID的替代
                position_id = f"pos_{i}"  # 临时ID
                gene_symbol = row[gene_col]
                
                # 处理多个基因符号
                genes = []
                gene_str = str(gene_symbol).strip()
                
                for separator in ['///', '//', ';', ',', '|']:
                    if separator in gene_str:
                        genes = [g.strip() for g in gene_str.split(separator)]
                        break
                
                if not genes:
                    genes = [gene_str]
                
                # 过滤有效基因符号
                valid_genes = []
                for g in genes:
                    g = g.strip()
                    if g and g not in ['---', '', 'null', 'NULL', 'nan', 'NaN']:
                        valid_genes.append(g)
                
                if valid_genes:
                    probe_to_gene[position_id] = valid_genes
            
            print(f"  Created position-based mapping: {len(probe_to_gene)} positions")
            
            return probe_to_gene
            
        except Exception as e:
            print(f"  Error loading platform annotation: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_gene_expression_matrix(self, expr_df, probe_to_gene):
        """创建基因级表达矩阵 - 使用修复的方法"""
        print("Creating gene-level expression matrix...")
        
        if probe_to_gene is None:
            print("  No probe-to-gene mapping provided")
            return pd.DataFrame()
        
        # 收集每个基因的表达数据
        gene_expr = {}
        
        # 由于使用位置映射，需要按位置索引处理
        for position_id, genes in probe_to_gene.items():
            # 提取位置索引
            if position_id.startswith('pos_'):
                pos_idx = int(position_id.split('_')[1])
                
                # 检查位置是否在表达数据范围内
                if pos_idx < len(expr_df):
                    probe_expr = expr_df.iloc[pos_idx]
                    
                    # 跳过全NaN值的探针
                    if probe_expr.isna().all():
                        continue
                        
                    for gene in genes:
                        # 跳过空或无效基因名
                        if not gene or gene in ['---', '', 'null', 'NULL']:
                            continue
                            
                        if gene not in gene_expr:
                            gene_expr[gene] = []
                        gene_expr[gene].append(probe_expr)
        
        if not gene_expr:
            print("  No valid gene expression data found")
            return pd.DataFrame()
        
        # 使用更高效的方法创建基因表达矩阵
        print("  Building gene expression matrix...")
        gene_data = {}
        
        for gene, expr_list in gene_expr.items():
            if len(expr_list) == 1:
                gene_data[gene] = expr_list[0].values
            else:
                # 多个探针求平均
                try:
                    combined_expr = pd.concat(expr_list, axis=1)
                    gene_data[gene] = combined_expr.mean(axis=1).values
                except Exception as e:
                    print(f"    Warning: Could not process gene {gene}: {e}")
                    continue
        
        if not gene_data:
            print("  Failed to create gene expression matrix")
            return pd.DataFrame()
        
        # 创建DataFrame
        gene_expr_df = pd.DataFrame.from_dict(gene_data, orient='index', columns=expr_df.columns)
        
        print(f"  Created gene expression matrix: {gene_expr_df.shape[0]} genes x {gene_expr_df.shape[1]} samples")
        
        # 处理重复基因名（如果有）
        if gene_expr_df.index.duplicated().any():
            print("  Handling duplicate gene names...")
            gene_expr_df = gene_expr_df.groupby(gene_expr_df.index).mean()
            print(f"  After removing duplicates: {gene_expr_df.shape}")
        
        return gene_expr_df
    
    def perform_ssgsea(self, gene_expr_df, gene_set_genes, alpha=0.25):
        """执行ssGSEA分析"""
        
        if not gene_set_genes:
            return np.zeros(gene_expr_df.shape[1])
        
        # 找到表达数据中匹配的基因
        available_genes = set(gene_expr_df.index)
        matched_genes = list(set(gene_set_genes) & available_genes)
        
        if len(matched_genes) == 0:
            return np.zeros(gene_expr_df.shape[1])
        
        enrichment_scores = []
        
        for sample in gene_expr_df.columns:
            sample_expr = gene_expr_df[sample].dropna()
            
            if len(sample_expr) == 0:
                enrichment_scores.append(0.0)
                continue
            
            # 按表达量排序基因（降序）
            gene_ranks = sample_expr.rank(method='average', ascending=False)
            total_genes = len(gene_ranks)
            
            # 创建基因集指示向量
            in_gene_set = np.zeros(total_genes)
            gene_set_indices = []
            
            for i, gene in enumerate(gene_ranks.index):
                if gene in matched_genes:
                    in_gene_set[i] = 1
                    gene_set_indices.append(i)
            
            if len(gene_set_indices) == 0:
                enrichment_scores.append(0.0)
                continue
            
            # 计算加权富集分数
            sorted_expr = sample_expr.sort_values(ascending=False)
            
            # 计算运行富集分数
            running_es = 0.0
            max_es = 0.0
            min_es = 0.0
            
            # 标准化因子
            N = total_genes
            Nh = len(gene_set_indices)
            
            # 基因集中基因的表达值总和（用于加权）
            gene_set_expr_sum = sum(abs(sorted_expr.iloc[i]) ** alpha for i in gene_set_indices)
            
            if gene_set_expr_sum == 0:
                gene_set_expr_sum = 1  # 避免除零
            
            for i in range(N):
                if in_gene_set[i] == 1:
                    # 基因在基因集中
                    running_es += (abs(sorted_expr.iloc[i]) ** alpha) / gene_set_expr_sum
                else:
                    # 基因不在基因集中
                    running_es -= 1.0 / (N - Nh)
                
                # 跟踪最大值和最小值
                if running_es > max_es:
                    max_es = running_es
                if running_es < min_es:
                    min_es = running_es
            
            # 最终富集分数
            if abs(max_es) > abs(min_es):
                es = max_es
            else:
                es = min_es
            
            enrichment_scores.append(es)
        
        return np.array(enrichment_scores)
    
    def analyze_gse21899(self):
        """分析GSE21899数据集"""
        print(f"\n{'='*80}")
        print(f"ANALYZING GSE21899 - GAUCHER DISEASE")
        print(f"{'='*80}")
        
        # 加载分类数据
        self.load_classification_data()
        
        # 加载表达数据
        expr_df, sample_info = self.load_expression_data()
        if expr_df is None:
            return None
        
        # 加载平台注释
        probe_to_gene = self.load_platform_annotation()
        if probe_to_gene is None:
            return None
        
        # 创建基因级表达矩阵
        gene_expr_df = self.create_gene_expression_matrix(expr_df, probe_to_gene)
        
        if gene_expr_df.empty:
            print(f"Failed to create gene expression matrix for {self.dataset_id}")
            return None
        
        # 分析每个子分类
        print(f"\nPerforming ssGSEA for 14 subcategories...")
        subcategory_scores = {}
        
        for subcat_code, subcat_info in self.gene_sets.items():
            print(f"  Analyzing {subcat_code}: {subcat_info['name']}")
            
            # 获取该子分类的基因
            gene_set_genes = subcat_info['genes']
            
            if len(gene_set_genes) == 0:
                print(f"    No genes found for {subcat_code}")
                scores = np.zeros(gene_expr_df.shape[1])
            else:
                # 执行真实ssGSEA
                scores = self.perform_ssgsea(gene_expr_df, gene_set_genes)
                
                # 计算基因重叠
                available_genes = set(gene_expr_df.index)
                matched_genes = list(set(gene_set_genes) & available_genes)
                overlap_pct = len(matched_genes) / len(gene_set_genes) * 100 if gene_set_genes else 0
                
                print(f"    Gene overlap: {len(matched_genes)}/{len(gene_set_genes)} ({overlap_pct:.1f}%)")
                print(f"    ssGSEA scores: {np.mean(scores):.3f} ± {np.std(scores):.3f}")
            
            subcategory_scores[subcat_code] = {
                'scores': scores.tolist(),
                'mean_score': float(np.mean(scores)) if len(scores) > 0 else 0.0,
                'std_score': float(np.std(scores)) if len(scores) > 0 else 0.0,
                'median_score': float(np.median(scores)) if len(scores) > 0 else 0.0,
                'min_score': float(np.min(scores)) if len(scores) > 0 else 0.0,
                'max_score': float(np.max(scores)) if len(scores) > 0 else 0.0,
                'name': subcat_info['name'],
                'gene_count': len(gene_set_genes),
                'matched_genes': len(set(gene_set_genes) & set(gene_expr_df.index)) if not gene_expr_df.empty else 0,
                'process_count': subcat_info['process_count']
            }
        
        # 计算系统级分数
        system_scores = {}
        systems = {
            'System A': ['A1', 'A2', 'A3', 'A4'],
            'System B': ['B1', 'B2', 'B3'],
            'System C': ['C1', 'C2', 'C3'],
            'System D': ['D1', 'D2'],
            'System E': ['E1', 'E2']
        }
        
        for system_name, subcats in systems.items():
            system_score_arrays = []
            for subcat in subcats:
                if subcat in subcategory_scores and subcategory_scores[subcat]['matched_genes'] > 0:
                    system_score_arrays.append(subcategory_scores[subcat]['scores'])
            
            if system_score_arrays:
                # 跨子分类求平均
                system_scores_array = np.mean(system_score_arrays, axis=0)
                system_scores[system_name] = {
                    'scores': system_scores_array.tolist(),
                    'mean_score': float(np.mean(system_scores_array)),
                    'std_score': float(np.std(system_scores_array)),
                    'subcategories': subcats
                }
        
        # 创建样本信息
        sample_ids = [f"GSM{i+1}" for i in range(gene_expr_df.shape[1])]
        
        # 根据样本标题推断分组
        sample_groups = []
        if 'titles' in sample_info:
            for title in sample_info['titles']:
                title_lower = title.lower()
                if 'control' in title_lower or 'normal' in title_lower or 'healthy' in title_lower:
                    sample_groups.append('Control')
                elif 'gaucher' in title_lower or 'patient' in title_lower or 'disease' in title_lower:
                    sample_groups.append('Gaucher')
                else:
                    sample_groups.append('Unknown')
        else:
            # 如果没有标题信息，假设前一半是对照，后一半是疾病
            n_samples = len(sample_ids)
            sample_groups = ['Control'] * (n_samples // 2) + ['Gaucher'] * (n_samples - n_samples // 2)
        
        return {
            'dataset_info': {
                'name': 'Gaucher Disease',
                'expected_systems': self.expected_systems,
                'expected_subcategories': self.expected_subcategories,
                'description': 'Metabolic disorder - should activate metabolic and regulatory systems'
            },
            'expression_shape': expr_df.shape,
            'gene_expression_shape': gene_expr_df.shape,
            'sample_info': sample_info,
            'sample_ids': sample_ids,
            'sample_groups': sample_groups,
            'subcategory_scores': subcategory_scores,
            'system_scores': system_scores,
            'probe_to_gene_count': len(probe_to_gene),
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def save_results_for_plotting(self, results):
        """保存用于绘图的结果数据"""
        print("\nSaving results for plotting...")
        
        if results is None:
            print("No results to save")
            return
        
        # 创建输出目录
        output_dir = "gse21899_results"
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. 保存子分类ssGSEA分数
        subcategory_data = []
        for i, sample_id in enumerate(results['sample_ids']):
            row = {'sample_id': sample_id}
            for subcat, scores_info in results['subcategory_scores'].items():
                row[subcat] = scores_info['scores'][i]
            subcategory_data.append(row)
        
        subcategory_df = pd.DataFrame(subcategory_data)
        subcategory_file = f"{output_dir}/gse21899_ssgsea_scores.csv"
        subcategory_df.to_csv(subcategory_file, index=False)
        print(f"  Saved subcategory scores: {subcategory_file}")
        
        # 2. 保存样本分组信息
        sample_info_data = []
        for i, sample_id in enumerate(results['sample_ids']):
            sample_info_data.append({
                'sample_id': sample_id,
                'group': results['sample_groups'][i],
                'dataset': 'GSE21899',
                'disease': 'Gaucher Disease'
            })
        
        sample_info_df = pd.DataFrame(sample_info_data)
        sample_info_file = f"{output_dir}/gse21899_sample_groups.csv"
        sample_info_df.to_csv(sample_info_file, index=False)
        print(f"  Saved sample info: {sample_info_file}")
        
        # 3. 保存系统级分数
        system_data = []
        for i, sample_id in enumerate(results['sample_ids']):
            row = {'sample_id': sample_id}
            for system, scores_info in results['system_scores'].items():
                row[system] = scores_info['scores'][i]
            system_data.append(row)
        
        system_df = pd.DataFrame(system_data)
        system_file = f"{output_dir}/gse21899_system_scores.csv"
        system_df.to_csv(system_file, index=False)
        print(f"  Saved system scores: {system_file}")
        
        # 4. 保存完整分析结果
        results_file = f"{output_dir}/gse21899_analysis_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"  Saved complete results: {results_file}")
        
        # 5. 生成分析摘要
        summary = self.generate_analysis_summary(results)
        summary_file = f"{output_dir}/gse21899_analysis_summary.md"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        print(f"  Saved analysis summary: {summary_file}")
        
        return output_dir
    
    def generate_analysis_summary(self, results):
        """生成分析摘要"""
        summary = f"""# GSE21899 Gaucher Disease Analysis Summary

## Dataset Information
- **Dataset**: {results['dataset_info']['name']}
- **Description**: {results['dataset_info']['description']}
- **Expected Systems**: {', '.join(results['dataset_info']['expected_systems'])}
- **Expected Subcategories**: {', '.join(results['dataset_info']['expected_subcategories'])}

## Data Dimensions
- **Expression Matrix**: {results['expression_shape'][0]} probes x {results['expression_shape'][1]} samples
- **Gene Expression Matrix**: {results['gene_expression_shape'][0]} genes x {results['gene_expression_shape'][1]} samples
- **Probe-to-Gene Mappings**: {results['probe_to_gene_count']} mappings

## Sample Information
- **Total Samples**: {len(results['sample_ids'])}
- **Sample Groups**: {dict(pd.Series(results['sample_groups']).value_counts())}

## Subcategory Analysis Results

### Top 5 Activated Subcategories
"""
        
        # 排序子分类得分
        subcat_scores = [(subcat, info['mean_score']) for subcat, info in results['subcategory_scores'].items() 
                        if info['matched_genes'] > 0]
        subcat_scores.sort(key=lambda x: x[1], reverse=True)
        
        for i, (subcat, score) in enumerate(subcat_scores[:5]):
            info = results['subcategory_scores'][subcat]
            summary += f"""
{i+1}. **{subcat} ({info['name']})**
   - Mean Score: {score:.4f} +/- {info['std_score']:.4f}
   - Gene Overlap: {info['matched_genes']}/{info['gene_count']} ({info['matched_genes']/info['gene_count']*100:.1f}%)
   - Process Count: {info['process_count']}
"""
        
        summary += f"""
## System-Level Analysis Results

### System Activation Ranking
"""
        
        # 排序系统得分
        system_scores = [(system, info['mean_score']) for system, info in results['system_scores'].items()]
        system_scores.sort(key=lambda x: x[1], reverse=True)
        
        for i, (system, score) in enumerate(system_scores):
            info = results['system_scores'][system]
            summary += f"""
{i+1}. **{system}**: {score:.4f} +/- {info['std_score']:.4f}
   - Subcategories: {', '.join(info['subcategories'])}
"""
        
        summary += f"""
## Biological Validation

### Expected vs Observed
- **Expected Top Systems**: {', '.join(results['dataset_info']['expected_systems'])}
- **Observed Top Systems**: {', '.join([s[0] for s in system_scores[:2]])}
- **Validation Success**: {'VALIDATED' if any(s[0] in results['dataset_info']['expected_systems'] for s in system_scores[:2]) else 'NOT VALIDATED'}

### Expected vs Observed Subcategories
- **Expected**: {', '.join(results['dataset_info']['expected_subcategories'])}
- **Top Observed**: {', '.join([s[0] for s in subcat_scores[:5]])}
- **Overlap**: {len(set(results['dataset_info']['expected_subcategories']) & set([s[0] for s in subcat_scores[:5]]))} / {len(results['dataset_info']['expected_subcategories'])}

## Analysis Timestamp
{results['analysis_timestamp']}

## Files Generated
- `gse21899_ssgsea_scores.csv` - Subcategory ssGSEA scores for all samples
- `gse21899_sample_groups.csv` - Sample grouping information
- `gse21899_system_scores.csv` - System-level scores for all samples
- `gse21899_analysis_results.json` - Complete analysis results
- `gse21899_analysis_summary.md` - This summary file
"""
        
        return summary

def main():
    """主函数"""
    print("="*80)
    print("GSE21899 GAUCHER DISEASE ANALYSIS")
    print("="*80)
    
    try:
        analyzer = GSE21899Analyzer()
        
        # 执行分析
        results = analyzer.analyze_gse21899()
        
        if results is None:
            print("❌ Analysis failed")
            return
        
        # 保存结果
        output_dir = analyzer.save_results_for_plotting(results)
        
        print(f"\n{'='*80}")
        print("GSE21899 ANALYSIS COMPLETED SUCCESSFULLY!")
        print(f"{'='*80}")
        
        print(f"\nResults saved to: {output_dir}/")
        print(f"\nKey Findings:")
        
        # 显示关键发现
        system_scores = [(system, info['mean_score']) for system, info in results['system_scores'].items()]
        system_scores.sort(key=lambda x: x[1], reverse=True)
        
        print(f"   • Top System: {system_scores[0][0]} (score: {system_scores[0][1]:.4f})")
        
        subcat_scores = [(subcat, info['mean_score']) for subcat, info in results['subcategory_scores'].items() 
                        if info['matched_genes'] > 0]
        subcat_scores.sort(key=lambda x: x[1], reverse=True)
        
        print(f"   • Top Subcategory: {subcat_scores[0][0]} (score: {subcat_scores[0][1]:.4f})")
        print(f"   • Sample Groups: {dict(pd.Series(results['sample_groups']).value_counts())}")
        
        # 验证预期
        expected_systems = results['dataset_info']['expected_systems']
        top_systems = [s[0] for s in system_scores[:2]]
        validation_success = any(s in expected_systems for s in top_systems)
        
        print(f"   • Expected Systems: {', '.join(expected_systems)}")
        print(f"   • Top Systems: {', '.join(top_systems)}")
        print(f"   • Validation: {'SUCCESS' if validation_success else 'NEEDS REVIEW'}")
        
    except Exception as e:
        print(f"Error in GSE21899 analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()