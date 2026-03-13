#!/usr/bin/env python3
"""
GSE28914 + GSE50425 组合分析

GSE28914: Human skin wound healing time course (25 samples)
GSE50425: 可能是相关的伤口愈合或皮肤研究数据集

将两个数据集组合分析，生成用于绘图的数据
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

class CombinedWoundHealingAnalyzer:
    def __init__(self):
        self.gse28914_path = "data/validation_datasets/GSE28914/GSE28914_series_matrix.txt.gz"
        self.gse28914_platform = "data/validation_datasets/GSE28914/GPL570-55999.txt"
        self.gse50425_path = "data/validation_datasets/GSE50425/GSE50425_series_matrix.txt.gz"
        self.gse50425_platform = "data/validation_datasets/GSE50425/GPL10558.annot.gz"
        
        self.classification_file = "results/full_classification/full_classification_results.csv"
        self.go_mapping_file = "data/go_annotations/go_to_genes.json"
        self.kegg_mapping_file = "data/kegg_mappings/kegg_to_genes.json"
        
        # 伤口愈合预期激活的系统和子分类
        self.expected_systems = ['System A', 'System B']
        self.expected_subcategories = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2']
        
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
    
    def load_gse_data(self, data_path, dataset_name):
        """加载GSE数据集"""
        print(f"\nLoading {dataset_name} data...")
        
        if not os.path.exists(data_path):
            print(f"Error: Data file not found: {data_path}")
            return None, None
            
        try:
            # 读取压缩文件
            with gzip.open(data_path, 'rt', encoding='utf-8', errors='ignore') as f:
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
            print(f"Error loading {dataset_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def load_platform_annotation(self, platform_file):
        """加载平台注释文件"""
        print(f"Loading platform annotation...")
        
        if not os.path.exists(platform_file):
            print("  Warning: No platform annotation file found")
            return None
        
        try:
            print(f"  Reading {os.path.basename(platform_file)}...")
            
            # 读取文件并找到数据开始位置
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
            
            # 创建探针到基因的映射
            probe_to_gene = {}
            valid_mappings = 0
            
            for _, row in platform_df.iterrows():
                probe_id = row.get('ID', '')
                gene_symbol = row.get(gene_col, '')
                
                # 跳过空的探针ID
                if not probe_id:
                    continue
                
                # 处理各种空/无效基因符号格式
                if not gene_symbol or str(gene_symbol).strip() in ['---', '', 'null', 'NULL', 'nan', 'NaN']:
                    continue
                
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
                    probe_to_gene[probe_id] = valid_genes
                    valid_mappings += 1
            
            print(f"  Mapped {len(probe_to_gene)} probes to genes ({valid_mappings} valid mappings)")
            
            return probe_to_gene
            
        except Exception as e:
            print(f"  Error loading platform annotation: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def load_illumina_platform_annotation(self, platform_file):
        """加载Illumina平台注释文件"""
        print(f"Loading Illumina platform annotation...")
        
        if not os.path.exists(platform_file):
            print("  Warning: No Illumina platform annotation file found")
            return None
        
        try:
            print(f"  Reading {os.path.basename(platform_file)}...")
            
            # 读取压缩文件
            with gzip.open(platform_file, 'rt', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Illumina注释文件通常以制表符分隔，第一行是标题
            header_line = None
            data_lines = []
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                if header_line is None:
                    header_line = line.split('\t')
                    print(f"  Header: {header_line[:5]}...")  # 显示前5列
                else:
                    data_lines.append(line.split('\t'))
            
            if not header_line or not data_lines:
                print("  Error: Could not parse Illumina platform file")
                return None
            
            # 创建DataFrame
            platform_df = pd.DataFrame(data_lines, columns=header_line)
            
            print(f"  Platform DataFrame shape: {platform_df.shape}")
            print(f"  Available columns: {platform_df.columns.tolist()}")
            
            # 查找探针ID列和基因符号列
            probe_id_col = None
            gene_symbol_col = None
            
            for col in platform_df.columns:
                col_lower = col.lower()
                if 'probe_id' in col_lower or 'id' in col_lower or col == 'ID':
                    probe_id_col = col
                elif any(term in col_lower for term in ['symbol', 'gene_symbol', 'gene symbol']):
                    gene_symbol_col = col
            
            if not probe_id_col:
                # 假设第一列是探针ID
                probe_id_col = platform_df.columns[0]
            
            if not gene_symbol_col:
                # 查找可能的基因符号列
                for col in platform_df.columns:
                    if 'Symbol' in col or 'SYMBOL' in col:
                        gene_symbol_col = col
                        break
            
            print(f"  Using probe ID column: {probe_id_col}")
            print(f"  Using gene symbol column: {gene_symbol_col}")
            
            if not gene_symbol_col:
                print("  Warning: No gene symbol column found")
                return None
            
            # 创建探针到基因的映射
            probe_to_gene = {}
            valid_mappings = 0
            
            for _, row in platform_df.iterrows():
                probe_id = str(row.get(probe_id_col, '')).strip()
                gene_symbol = str(row.get(gene_symbol_col, '')).strip()
                
                # 跳过空的探针ID
                if not probe_id or probe_id in ['', 'nan', 'NaN']:
                    continue
                
                # 处理各种空/无效基因符号格式
                if not gene_symbol or gene_symbol in ['---', '', 'null', 'NULL', 'nan', 'NaN']:
                    continue
                
                # 处理多个基因符号
                genes = []
                for separator in ['///', '//', ';', ',', '|']:
                    if separator in gene_symbol:
                        genes = [g.strip() for g in gene_symbol.split(separator)]
                        break
                
                if not genes:
                    genes = [gene_symbol]
                
                # 过滤有效基因符号
                valid_genes = []
                for g in genes:
                    g = g.strip()
                    if g and g not in ['---', '', 'null', 'NULL', 'nan', 'NaN']:
                        valid_genes.append(g)
                
                if valid_genes:
                    probe_to_gene[probe_id] = valid_genes
                    valid_mappings += 1
            
            print(f"  Mapped {len(probe_to_gene)} probes to genes ({valid_mappings} valid mappings)")
            
            # 检查是否找到了目标探针
            if 'ILMN_1343291' in probe_to_gene:
                print(f"  ✅ Found target probe ILMN_1343291 -> {probe_to_gene['ILMN_1343291']}")
            
            return probe_to_gene
            
        except Exception as e:
            print(f"  Error loading Illumina platform annotation: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
        """加载平台注释文件"""
        print(f"Loading platform annotation...")
        
        if not os.path.exists(platform_file):
            print("  Warning: No platform annotation file found")
            return None
        
        try:
            print(f"  Reading {os.path.basename(platform_file)}...")
            
            # 读取文件并找到数据开始位置
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
            
            # 创建探针到基因的映射
            probe_to_gene = {}
            valid_mappings = 0
            
            for _, row in platform_df.iterrows():
                probe_id = row.get('ID', '')
                gene_symbol = row.get(gene_col, '')
                
                # 跳过空的探针ID
                if not probe_id:
                    continue
                
                # 处理各种空/无效基因符号格式
                if not gene_symbol or str(gene_symbol).strip() in ['---', '', 'null', 'NULL', 'nan', 'NaN']:
                    continue
                
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
                    probe_to_gene[probe_id] = valid_genes
                    valid_mappings += 1
            
            print(f"  Mapped {len(probe_to_gene)} probes to genes ({valid_mappings} valid mappings)")
            
            return probe_to_gene
            
        except Exception as e:
            print(f"  Error loading platform annotation: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_gene_expression_matrix(self, expr_df, probe_to_gene):
        """创建基因级表达矩阵"""
        print("Creating gene-level expression matrix...")
        
        if probe_to_gene is None:
            print("  Warning: No probe-to-gene mapping, using probe IDs as gene names")
            # 如果没有平台注释，直接使用探针ID
            gene_expr_df = expr_df.copy()
            gene_expr_df.index.name = 'Gene'
            print(f"  Created expression matrix: {gene_expr_df.shape[0]} probes x {gene_expr_df.shape[1]} samples")
            return gene_expr_df
        
        # 收集每个基因的表达数据
        gene_expr = {}
        
        for probe_id, genes in probe_to_gene.items():
            if probe_id in expr_df.index:
                probe_expr = expr_df.loc[probe_id]
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
            print("  No valid gene expression data found, using probe IDs")
            gene_expr_df = expr_df.copy()
            gene_expr_df.index.name = 'Gene'
            return gene_expr_df
        
        # 对有多个探针的基因求平均
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
    
    def parse_sample_info(self, sample_info, dataset_name):
        """解析样本信息"""
        print(f"Parsing sample information for {dataset_name}...")
        
        sample_ids = sample_info.get('accessions', [])
        sample_titles = sample_info.get('titles', [])
        
        if not sample_ids:
            sample_ids = [f"{dataset_name}_Sample_{i+1}" for i in range(len(sample_titles))]
        
        sample_data = []
        
        for i, (sample_id, title) in enumerate(zip(sample_ids, sample_titles)):
            # 解析样本信息
            sample_record = {
                'sample_id': sample_id,
                'sample_title': title,
                'dataset': dataset_name,
                'timepoint': 'Unknown',
                'condition': 'Unknown',
                'group': 'Unknown'
            }
            
            title_lower = title.lower()
            
            if dataset_name == 'GSE28914':
                # GSE28914 伤口愈合时间序列
                if 'intact skin' in title_lower:
                    sample_record.update({
                        'timepoint': 'Baseline',
                        'condition': 'Intact_Skin',
                        'group': 'Baseline'
                    })
                elif 'acute wound' in title_lower:
                    sample_record.update({
                        'timepoint': 'Acute',
                        'condition': 'Acute_Wound',
                        'group': 'Acute'
                    })
                elif '3rd post-operative day' in title_lower:
                    sample_record.update({
                        'timepoint': 'Day_3',
                        'condition': 'Post_Op',
                        'group': 'Day_3'
                    })
                elif '7th post-operative day' in title_lower:
                    sample_record.update({
                        'timepoint': 'Day_7',
                        'condition': 'Post_Op',
                        'group': 'Day_7'
                    })
            
            elif dataset_name == 'GSE50425':
                # GSE50425 需要根据实际样本标题解析
                # 这里先设置为通用分组，后续可以根据实际数据调整
                if 'control' in title_lower or 'normal' in title_lower:
                    sample_record.update({
                        'timepoint': 'Control',
                        'condition': 'Control',
                        'group': 'Control'
                    })
                elif 'treatment' in title_lower or 'treated' in title_lower:
                    sample_record.update({
                        'timepoint': 'Treatment',
                        'condition': 'Treatment',
                        'group': 'Treatment'
                    })
                else:
                    # 如果无法解析，按顺序分组
                    group_num = (i // 3) + 1
                    sample_record.update({
                        'timepoint': f'Group_{group_num}',
                        'condition': f'Condition_{group_num}',
                        'group': f'Group_{group_num}'
                    })
            
            sample_data.append(sample_record)
        
        return sample_data
    
    def analyze_combined_datasets(self):
        """分析组合数据集"""
        print(f"\n{'='*80}")
        print(f"ANALYZING COMBINED GSE28914 + GSE50425 DATASETS")
        print(f"{'='*80}")
        
        # 加载分类数据
        self.load_classification_data()
        
        # 加载GSE28914数据
        gse28914_expr, gse28914_info = self.load_gse_data(self.gse28914_path, 'GSE28914')
        if gse28914_expr is None:
            return None
        
        # 加载GSE50425数据
        gse50425_expr, gse50425_info = self.load_gse_data(self.gse50425_path, 'GSE50425')
        if gse50425_expr is None:
            return None
        
        # 加载平台注释
        gse28914_probe_to_gene = self.load_platform_annotation(self.gse28914_platform)
        gse50425_probe_to_gene = self.load_illumina_platform_annotation(self.gse50425_platform)
        
        # 创建基因级表达矩阵
        gse28914_gene_expr = self.create_gene_expression_matrix(gse28914_expr, gse28914_probe_to_gene)
        gse50425_gene_expr = self.create_gene_expression_matrix(gse50425_expr, gse50425_probe_to_gene)
        
        if gse28914_gene_expr.empty and gse50425_gene_expr.empty:
            print(f"Failed to create gene expression matrices")
            return None
        
        # 解析样本信息
        gse28914_samples = self.parse_sample_info(gse28914_info, 'GSE28914')
        gse50425_samples = self.parse_sample_info(gse50425_info, 'GSE50425')
        
        # 分析每个数据集
        results = {
            'GSE28914': self.analyze_single_dataset(gse28914_gene_expr, gse28914_samples, 'GSE28914'),
            'GSE50425': self.analyze_single_dataset(gse50425_gene_expr, gse50425_samples, 'GSE50425')
        }
        
        # 组合分析结果
        combined_results = self.combine_analysis_results(results)
        
        return combined_results
    
    def analyze_single_dataset(self, gene_expr_df, sample_data, dataset_name):
        """分析单个数据集"""
        print(f"\nAnalyzing {dataset_name}...")
        
        if gene_expr_df.empty:
            print(f"  No gene expression data for {dataset_name}")
            return None
        
        # 执行ssGSEA分析
        print(f"  Performing ssGSEA for 14 subcategories...")
        subcategory_scores = {}
        
        for subcat_code, subcat_info in self.gene_sets.items():
            print(f"    Analyzing {subcat_code}: {subcat_info['name']}")
            
            # 获取该子分类的基因
            gene_set_genes = subcat_info['genes']
            
            if len(gene_set_genes) == 0:
                print(f"      No genes found for {subcat_code}")
                scores = np.zeros(gene_expr_df.shape[1])
            else:
                # 执行真实ssGSEA
                scores = self.perform_ssgsea(gene_expr_df, gene_set_genes)
                
                # 计算基因重叠
                available_genes = set(gene_expr_df.index)
                matched_genes = list(set(gene_set_genes) & available_genes)
                overlap_pct = len(matched_genes) / len(gene_set_genes) * 100 if gene_set_genes else 0
                
                print(f"      Gene overlap: {len(matched_genes)}/{len(gene_set_genes)} ({overlap_pct:.1f}%)")
                print(f"      ssGSEA scores: {np.mean(scores):.3f} ± {np.std(scores):.3f}")
            
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
        
        return {
            'dataset_info': {
                'name': dataset_name,
                'expected_systems': self.expected_systems,
                'expected_subcategories': self.expected_subcategories,
                'description': 'Wound healing and skin research'
            },
            'expression_shape': gene_expr_df.shape,
            'sample_data': sample_data,
            'subcategory_scores': subcategory_scores,
            'system_scores': system_scores,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def combine_analysis_results(self, results):
        """组合分析结果"""
        print(f"\nCombining analysis results...")
        
        # 合并样本数据
        all_samples = []
        all_subcategory_scores = []
        all_system_scores = []
        
        for dataset_name, dataset_results in results.items():
            if dataset_results is None:
                continue
                
            # 添加样本数据
            for sample in dataset_results['sample_data']:
                all_samples.append(sample)
            
            # 添加子分类得分
            for i, sample in enumerate(dataset_results['sample_data']):
                score_row = {'sample_id': sample['sample_id'], 'dataset': dataset_name}
                for subcat_code in self.subcategories.keys():
                    if subcat_code in dataset_results['subcategory_scores']:
                        score_row[subcat_code] = dataset_results['subcategory_scores'][subcat_code]['scores'][i]
                    else:
                        score_row[subcat_code] = 0.0
                all_subcategory_scores.append(score_row)
            
            # 添加系统得分
            for i, sample in enumerate(dataset_results['sample_data']):
                score_row = {'sample_id': sample['sample_id'], 'dataset': dataset_name}
                for system_name in ['System A', 'System B', 'System C', 'System D', 'System E']:
                    if system_name in dataset_results['system_scores']:
                        score_row[system_name] = dataset_results['system_scores'][system_name]['scores'][i]
                    else:
                        score_row[system_name] = 0.0
                all_system_scores.append(score_row)
        
        combined_results = {
            'analysis_info': {
                'title': 'Combined GSE28914 + GSE50425 Analysis',
                'description': 'Combined analysis of wound healing datasets',
                'datasets': list(results.keys()),
                'total_samples': len(all_samples),
                'timestamp': datetime.now().isoformat()
            },
            'sample_data': all_samples,
            'subcategory_scores': all_subcategory_scores,
            'system_scores': all_system_scores,
            'individual_results': results
        }
        
        return combined_results
    
    def save_results_for_plotting(self, results):
        """保存用于绘图的结果数据"""
        print("\nSaving results for plotting...")
        
        if results is None:
            print("No results to save")
            return
        
        # 创建输出目录
        output_dir = "combined_wound_healing_results"
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. 保存组合的子分类ssGSEA分数
        subcategory_df = pd.DataFrame(results['subcategory_scores'])
        subcategory_file = f"{output_dir}/combined_ssgsea_scores.csv"
        subcategory_df.to_csv(subcategory_file, index=False)
        print(f"  Saved combined subcategory scores: {subcategory_file}")
        
        # 2. 保存组合的样本信息
        sample_info_df = pd.DataFrame(results['sample_data'])
        sample_info_file = f"{output_dir}/combined_sample_info.csv"
        sample_info_df.to_csv(sample_info_file, index=False)
        print(f"  Saved combined sample info: {sample_info_file}")
        
        # 3. 保存组合的系统级分数
        system_df = pd.DataFrame(results['system_scores'])
        system_file = f"{output_dir}/combined_system_scores.csv"
        system_df.to_csv(system_file, index=False)
        print(f"  Saved combined system scores: {system_file}")
        
        # 4. 分别保存每个数据集的结果
        for dataset_name, dataset_results in results['individual_results'].items():
            if dataset_results is None:
                continue
                
            # 子分类得分
            dataset_subcategory_data = []
            for i, sample in enumerate(dataset_results['sample_data']):
                row = {'sample_id': sample['sample_id']}
                for subcat_code in self.subcategories.keys():
                    if subcat_code in dataset_results['subcategory_scores']:
                        row[subcat_code] = dataset_results['subcategory_scores'][subcat_code]['scores'][i]
                    else:
                        row[subcat_code] = 0.0
                dataset_subcategory_data.append(row)
            
            dataset_subcategory_df = pd.DataFrame(dataset_subcategory_data)
            dataset_subcategory_file = f"{output_dir}/{dataset_name.lower()}_ssgsea_scores.csv"
            dataset_subcategory_df.to_csv(dataset_subcategory_file, index=False)
            print(f"  Saved {dataset_name} subcategory scores: {dataset_subcategory_file}")
            
            # 样本信息
            dataset_sample_df = pd.DataFrame(dataset_results['sample_data'])
            dataset_sample_file = f"{output_dir}/{dataset_name.lower()}_sample_info.csv"
            dataset_sample_df.to_csv(dataset_sample_file, index=False)
            print(f"  Saved {dataset_name} sample info: {dataset_sample_file}")
            
            # 系统得分
            dataset_system_data = []
            for i, sample in enumerate(dataset_results['sample_data']):
                row = {'sample_id': sample['sample_id']}
                for system_name in ['System A', 'System B', 'System C', 'System D', 'System E']:
                    if system_name in dataset_results['system_scores']:
                        row[system_name] = dataset_results['system_scores'][system_name]['scores'][i]
                    else:
                        row[system_name] = 0.0
                dataset_system_data.append(row)
            
            dataset_system_df = pd.DataFrame(dataset_system_data)
            dataset_system_file = f"{output_dir}/{dataset_name.lower()}_system_scores.csv"
            dataset_system_df.to_csv(dataset_system_file, index=False)
            print(f"  Saved {dataset_name} system scores: {dataset_system_file}")
        
        # 5. 保存完整分析结果
        results_file = f"{output_dir}/combined_analysis_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"  Saved complete results: {results_file}")
        
        # 6. 生成分析摘要
        summary = self.generate_analysis_summary(results)
        summary_file = f"{output_dir}/combined_analysis_summary.md"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        print(f"  Saved analysis summary: {summary_file}")
        
        return output_dir
    
    def generate_analysis_summary(self, results):
        """生成分析摘要"""
        summary = f"""# Combined GSE28914 + GSE50425 Analysis Summary

## Analysis Information
- **Title**: {results['analysis_info']['title']}
- **Description**: {results['analysis_info']['description']}
- **Datasets**: {', '.join(results['analysis_info']['datasets'])}
- **Total Samples**: {results['analysis_info']['total_samples']}

## Dataset Breakdown
"""
        
        for dataset_name, dataset_results in results['individual_results'].items():
            if dataset_results is None:
                continue
                
            summary += f"""
### {dataset_name}
- **Samples**: {len(dataset_results['sample_data'])}
- **Expression Matrix**: {dataset_results['expression_shape'][0]} genes x {dataset_results['expression_shape'][1]} samples
- **Expected Systems**: {', '.join(dataset_results['dataset_info']['expected_systems'])}
- **Expected Subcategories**: {', '.join(dataset_results['dataset_info']['expected_subcategories'])}

#### Sample Groups
"""
            
            # 统计样本分组
            sample_groups = {}
            for sample in dataset_results['sample_data']:
                group = sample['group']
                if group not in sample_groups:
                    sample_groups[group] = 0
                sample_groups[group] += 1
            
            for group, count in sample_groups.items():
                summary += f"- {group}: {count} samples\n"
            
            # 顶级系统和子分类
            system_scores = [(system, info['mean_score']) for system, info in dataset_results['system_scores'].items()]
            system_scores.sort(key=lambda x: x[1], reverse=True)
            
            subcat_scores = [(subcat, info['mean_score']) for subcat, info in dataset_results['subcategory_scores'].items() 
                            if info['matched_genes'] > 0]
            subcat_scores.sort(key=lambda x: x[1], reverse=True)
            
            summary += f"""
#### Top Systems
"""
            for i, (system, score) in enumerate(system_scores[:3]):
                summary += f"{i+1}. **{system}**: {score:.4f}\n"
            
            summary += f"""
#### Top Subcategories
"""
            for i, (subcat, score) in enumerate(subcat_scores[:5]):
                info = dataset_results['subcategory_scores'][subcat]
                summary += f"{i+1}. **{subcat} ({info['name']})**: {score:.4f}\n"
        
        summary += f"""
## Combined Analysis Results

### Overall Sample Distribution
"""
        
        # 统计组合样本分组
        combined_groups = {}
        combined_datasets = {}
        for sample in results['sample_data']:
            group = sample['group']
            dataset = sample['dataset']
            
            if group not in combined_groups:
                combined_groups[group] = 0
            combined_groups[group] += 1
            
            if dataset not in combined_datasets:
                combined_datasets[dataset] = 0
            combined_datasets[dataset] += 1
        
        for group, count in combined_groups.items():
            summary += f"- {group}: {count} samples\n"
        
        summary += f"""
### Dataset Distribution
"""
        for dataset, count in combined_datasets.items():
            summary += f"- {dataset}: {count} samples\n"
        
        summary += f"""
## Analysis Timestamp
{results['analysis_info']['timestamp']}

## Files Generated
- `combined_ssgsea_scores.csv` - Combined subcategory ssGSEA scores
- `combined_sample_info.csv` - Combined sample information
- `combined_system_scores.csv` - Combined system-level scores
- Individual dataset files for GSE28914 and GSE50425
- `combined_analysis_results.json` - Complete analysis results
- `combined_analysis_summary.md` - This summary file
"""
        
        return summary

def main():
    """主函数"""
    print("="*80)
    print("COMBINED GSE28914 + GSE50425 WOUND HEALING ANALYSIS")
    print("="*80)
    
    try:
        analyzer = CombinedWoundHealingAnalyzer()
        
        # 执行组合分析
        results = analyzer.analyze_combined_datasets()
        
        if results is None:
            print("Analysis failed")
            return
        
        # 保存结果
        output_dir = analyzer.save_results_for_plotting(results)
        
        print(f"\n{'='*80}")
        print("COMBINED ANALYSIS COMPLETED SUCCESSFULLY!")
        print(f"{'='*80}")
        
        print(f"\nResults saved to: {output_dir}/")
        print(f"\nKey Findings:")
        
        # 显示关键发现
        total_samples = results['analysis_info']['total_samples']
        datasets = results['analysis_info']['datasets']
        
        print(f"   • Total samples analyzed: {total_samples}")
        print(f"   • Datasets combined: {', '.join(datasets)}")
        
        # 显示每个数据集的顶级系统
        for dataset_name, dataset_results in results['individual_results'].items():
            if dataset_results is None:
                continue
                
            system_scores = [(system, info['mean_score']) for system, info in dataset_results['system_scores'].items()]
            system_scores.sort(key=lambda x: x[1], reverse=True)
            
            if system_scores:
                print(f"   • {dataset_name} top system: {system_scores[0][0]} (score: {system_scores[0][1]:.4f})")
        
        print(f"   • Expected wound healing activation: System A (repair) and System B (immune)")
        
    except Exception as e:
        print(f"Error in combined analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()