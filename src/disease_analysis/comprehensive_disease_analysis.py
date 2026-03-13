#!/usr/bin/env python3
"""
综合疾病数据集分析
分析多种疾病的系统激活模式，验证五大系统分类的正确性
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

class ComprehensiveDiseaseAnalyzer:
    def __init__(self):
        """初始化综合疾病分析器"""
        
        # 数据集定义
        self.datasets = {
            'GSE122063': {
                'name': 'Alzheimer Disease',
                'chinese_name': '阿尔兹海默症',
                'path': 'data/validation_datasets/GSE122063-阿尔兹海默症/GSE122063_series_matrix.txt.gz',
                'platform': 'data/validation_datasets/GSE122063-阿尔兹海默症/GPL16699-15607.txt',
                'expected_systems': ['System D', 'System A'],  # 神经调节 + 修复
                'expected_subcategories': ['D1', 'D2', 'A1', 'A2'],
                'description': 'Neurodegenerative disease - should activate neural regulation and repair systems',
                'biological_rationale': '神经退行性疾病，预期激活神经调节系统(D1)和修复系统(A1,A2)'
            },
            'GSE2034': {
                'name': 'Breast Cancer',
                'chinese_name': '乳腺癌',
                'path': 'data/validation_datasets/GSE2034-乳腺癌/GSE2034_series_matrix.txt.gz',
                'platform': 'data/validation_datasets/GSE2034-乳腺癌/GPL96-57554.txt',
                'expected_systems': ['System A', 'System B', 'System E'],  # 修复 + 免疫 + 发育
                'expected_subcategories': ['A1', 'A2', 'B1', 'B2', 'E2'],
                'description': 'Cancer - should activate repair, immune, and development systems',
                'biological_rationale': '癌症，预期激活基因组稳定性(A1)、免疫系统(B1,B2)和发育系统(E2)'
            },
            'GSE26168': {
                'name': 'Diabetes',
                'chinese_name': '糖尿病',
                'path': 'data/validation_datasets/GSE26168-糖尿病/GSE26168_series_matrix.txt.gz',
                'platform': 'data/validation_datasets/GSE26168-糖尿病/GPL6883-11606.txt',
                'expected_systems': ['System C', 'System D'],  # 代谢 + 调节
                'expected_subcategories': ['C1', 'C2', 'C3', 'D2'],
                'description': 'Metabolic disorder - should activate metabolic and regulatory systems',
                'biological_rationale': '代谢疾病，预期激活能量代谢(C1)、生物合成(C2)和内分泌调节(D2)'
            },
            'GSE21899': {
                'name': 'Gaucher Disease',
                'chinese_name': '戈谢病',
                'path': 'data/validation_datasets/GSE21899-戈谢病/GSE21899_series_matrix.txt.gz',
                'platform': 'data/validation_datasets/GSE21899-戈谢病/GPL571-17391.txt',
                'expected_systems': ['System C', 'System D'],  # 代谢 + 调节
                'expected_subcategories': ['C1', 'C2', 'C3', 'D1', 'D2'],
                'description': 'Lysosomal storage disorder - should activate metabolic systems',
                'biological_rationale': '溶酶体贮积病，预期激活代谢系统(C1,C2,C3)和调节系统(D1,D2)'
            },
            'GSE28914': {
                'name': 'Wound Healing',
                'chinese_name': '伤口愈合',
                'path': 'data/validation_datasets/GSE28914-伤口愈合1/GSE28914_series_matrix.txt.gz',
                'platform': 'data/validation_datasets/GSE28914-伤口愈合1/GPL570-55999.txt',
                'expected_systems': ['System A', 'System B'],  # 修复 + 免疫
                'expected_subcategories': ['A1', 'A2', 'A3', 'A4', 'B1', 'B2'],
                'description': 'Wound healing - should activate repair and immune systems',
                'biological_rationale': '伤口愈合，预期激活修复系统(A1-A4)和免疫系统(B1,B2)'
            },
            'GSE50425': {
                'name': 'Wound Healing Extended',
                'chinese_name': '伤口愈合扩展',
                'path': 'data/validation_datasets/GSE50425-伤口愈合2/GSE50425_series_matrix.txt.gz',
                'platform': 'data/validation_datasets/GSE50425-伤口愈合2/GPL10558-50081.txt',
                'expected_systems': ['System A', 'System B'],  # 修复 + 免疫
                'expected_subcategories': ['A1', 'A2', 'A3', 'A4', 'B1', 'B2'],
                'description': 'Extended wound healing - should activate repair and immune systems',
                'biological_rationale': '扩展伤口愈合研究，预期激活修复和免疫系统'
            },
            'GSE65682': {
                'name': 'Sepsis',
                'chinese_name': '脓毒症',
                'path': 'data/validation_datasets/GSE65682-脓毒症/GSE65682_series_matrix.txt.gz',
                'platform': None,  # 已有数据
                'expected_systems': ['System B', 'System C'],  # 免疫 + 代谢
                'expected_subcategories': ['B1', 'B2', 'B3', 'C1', 'C3'],
                'description': 'Sepsis - should activate immune and metabolic systems',
                'biological_rationale': '脓毒症，预期激活免疫系统(B1-B3)和代谢应激(C1,C3)'
            }
        }
        
        # 五大系统定义
        self.systems = {
            'System A': {
                'name': 'Homeostasis and Repair',
                'chinese_name': '稳态与修复',
                'subcategories': ['A1', 'A2', 'A3', 'A4'],
                'color': '#FF6B6B'
            },
            'System B': {
                'name': 'Immune Defense',
                'chinese_name': '免疫防御',
                'subcategories': ['B1', 'B2', 'B3'],
                'color': '#4ECDC4'
            },
            'System C': {
                'name': 'Metabolic Regulation',
                'chinese_name': '代谢调节',
                'subcategories': ['C1', 'C2', 'C3'],
                'color': '#45B7D1'
            },
            'System D': {
                'name': 'Regulatory Coordination',
                'chinese_name': '调节协调',
                'subcategories': ['D1', 'D2'],
                'color': '#96CEB4'
            },
            'System E': {
                'name': 'Reproduction and Development',
                'chinese_name': '生殖与发育',
                'subcategories': ['E1', 'E2'],
                'color': '#FFEAA7'
            }
        }
        
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
        
        # 加载基因映射和分类数据
        self.load_gene_mappings()
        self.load_classification_data()
    
    def load_gene_mappings(self):
        """加载GO和KEGG基因映射"""
        print("Loading gene mappings...")
        
        # 加载GO映射
        go_mapping_file = "data/go_annotations/go_to_genes.json"
        if os.path.exists(go_mapping_file):
            with open(go_mapping_file, 'r') as f:
                self.go_to_genes = json.load(f)
            print(f"  Loaded GO mappings: {len(self.go_to_genes)} GO terms")
        else:
            print(f"  GO mapping file not found: {go_mapping_file}")
            self.go_to_genes = {}
        
        # 加载KEGG映射
        kegg_mapping_file = "data/kegg_mappings/kegg_to_genes.json"
        if os.path.exists(kegg_mapping_file):
            with open(kegg_mapping_file, 'r') as f:
                kegg_data = json.load(f)
            self.kegg_to_genes = {}
            for pathway_id, info in kegg_data.items():
                self.kegg_to_genes[pathway_id] = info['genes']
            print(f"  Loaded KEGG mappings: {len(self.kegg_to_genes)} pathways")
        else:
            print(f"  KEGG mapping file not found: {kegg_mapping_file}")
            self.kegg_to_genes = {}
    
    def load_classification_data(self):
        """加载分类数据并创建基因集"""
        print("\nLoading classification data...")
        
        classification_file = "results/full_classification/full_classification_results.csv"
        df = pd.read_csv(classification_file)
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
    
    def create_analysis_plan(self):
        """创建分析计划"""
        print(f"\n{'='*80}")
        print("COMPREHENSIVE DISEASE ANALYSIS PLAN")
        print(f"{'='*80}")
        
        print(f"\n🎯 Analysis Objectives:")
        print(f"   • Validate five-system classification across diverse diseases")
        print(f"   • Demonstrate disease-specific system activation patterns")
        print(f"   • Provide multi-dimensional evidence for biological relevance")
        
        print(f"\n📊 Dataset Overview:")
        for dataset_id, info in self.datasets.items():
            print(f"   • {dataset_id} ({info['chinese_name']})")
            print(f"     - Expected systems: {', '.join(info['expected_systems'])}")
            print(f"     - Rationale: {info['biological_rationale']}")
        
        print(f"\n🔬 Expected Validation Patterns:")
        
        # 按系统分组显示预期激活的疾病
        system_disease_map = {}
        for system in self.systems.keys():
            system_disease_map[system] = []
            for dataset_id, info in self.datasets.items():
                if system in info['expected_systems']:
                    system_disease_map[system].append(f"{dataset_id}({info['chinese_name']})")
        
        for system, diseases in system_disease_map.items():
            system_info = self.systems[system]
            print(f"   • {system} ({system_info['chinese_name']}): {', '.join(diseases)}")
        
        print(f"\n📈 Analysis Strategy:")
        print(f"   1. Individual dataset analysis with ssGSEA")
        print(f"   2. Cross-disease system activation comparison")
        print(f"   3. Disease-specific vs. general activation patterns")
        print(f"   4. Statistical validation of expected patterns")
        print(f"   5. Comprehensive visualization and reporting")
        
        return system_disease_map
    
    def analyze_single_dataset(self, dataset_id):
        """分析单个数据集"""
        print(f"\n{'='*60}")
        print(f"ANALYZING {dataset_id} - {self.datasets[dataset_id]['chinese_name']}")
        print(f"{'='*60}")
        
        dataset_info = self.datasets[dataset_id]
        
        # 检查文件是否存在
        if not os.path.exists(dataset_info['path']):
            print(f"❌ Data file not found: {dataset_info['path']}")
            return None
        
        # 加载表达数据
        expr_df, sample_info = self.load_expression_data(dataset_info['path'], dataset_id)
        if expr_df is None:
            return None
        
        # 加载平台注释
        probe_to_gene = None
        if dataset_info['platform'] and os.path.exists(dataset_info['platform']):
            probe_to_gene = self.load_platform_annotation(dataset_info['platform'])
        
        # 创建基因级表达矩阵
        gene_expr_df = self.create_gene_expression_matrix(expr_df, probe_to_gene)
        if gene_expr_df.empty:
            print(f"❌ Failed to create gene expression matrix")
            return None
        
        # 执行ssGSEA分析
        results = self.perform_dataset_ssgsea(gene_expr_df, sample_info, dataset_id)
        
        return results
    
    def load_expression_data(self, data_path, dataset_name):
        """加载表达数据"""
        print(f"Loading expression data for {dataset_name}...")
        
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
                print(f"  Error: Could not find data table start")
                return None, None
            
            # 读取数据表
            data_lines = []
            for line in lines[data_start:]:
                if line.startswith('!series_matrix_table_end'):
                    break
                data_lines.append(line.strip().split('\t'))
            
            if len(data_lines) < 2:
                print(f"  Error: Insufficient data")
                return None, None
            
            # 创建DataFrame
            header = [col.strip('"') for col in data_lines[0]]
            data_rows = [[cell.strip('"') for cell in row] for row in data_lines[1:]]
            
            expr_df = pd.DataFrame(data_rows, columns=header)
            
            # 设置探针ID为索引
            if 'ID_REF' in expr_df.columns:
                expr_df = expr_df.set_index('ID_REF')
            else:
                print(f"  Error: ID_REF column not found")
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
            print(f"  Error loading {dataset_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def load_platform_annotation(self, platform_file):
        """加载平台注释文件"""
        print(f"  Loading platform annotation...")
        
        try:
            # 检查文件格式
            if platform_file.endswith('.gz'):
                # 压缩文件
                with gzip.open(platform_file, 'rt', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
            else:
                # 普通文本文件
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
                print(f"    Error: Could not find platform data start")
                return None
            
            # 读取平台数据
            platform_lines = []
            for line in lines[data_start:]:
                if line.startswith('!platform_table_end'):
                    break
                platform_lines.append(line.strip().split('\t'))
            
            if len(platform_lines) < 2:
                print(f"    Error: Insufficient platform data")
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
                print(f"    Error: No gene symbol column found")
                print(f"    Available columns: {platform_df.columns.tolist()}")
                return None
            
            # 使用第一个基因符号列
            gene_col = gene_symbol_cols[0]
            print(f"    Using gene symbol column: {gene_col}")
            
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
            
            print(f"    Mapped {len(probe_to_gene)} probes to genes ({valid_mappings} valid mappings)")
            
            return probe_to_gene
            
        except Exception as e:
            print(f"    Error loading platform annotation: {str(e)}")
            return None
    
    def create_gene_expression_matrix(self, expr_df, probe_to_gene):
        """创建基因级表达矩阵"""
        print(f"  Creating gene-level expression matrix...")
        
        if probe_to_gene is None:
            print(f"    Warning: No probe-to-gene mapping, using probe IDs as gene names")
            gene_expr_df = expr_df.copy()
            gene_expr_df.index.name = 'Gene'
            print(f"    Created expression matrix: {gene_expr_df.shape[0]} probes x {gene_expr_df.shape[1]} samples")
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
            print(f"    No valid gene expression data found, using probe IDs")
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
                    print(f"      Warning: Could not process gene {gene}: {e}")
                    continue
        
        if not gene_data:
            print(f"    Failed to create gene expression matrix")
            return pd.DataFrame()
        
        # 创建DataFrame
        gene_expr_df = pd.DataFrame.from_dict(gene_data, orient='index', columns=expr_df.columns)
        
        print(f"    Created gene expression matrix: {gene_expr_df.shape[0]} genes x {gene_expr_df.shape[1]} samples")
        
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
    
    def perform_dataset_ssgsea(self, gene_expr_df, sample_info, dataset_id):
        """对数据集执行ssGSEA分析"""
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
        for system_name, system_info in self.systems.items():
            subcats = system_info['subcategories']
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
        sample_ids = sample_info.get('accessions', [])
        if not sample_ids:
            sample_ids = [f"{dataset_id}_Sample_{i+1}" for i in range(gene_expr_df.shape[1])]
        
        return {
            'dataset_info': self.datasets[dataset_id],
            'expression_shape': gene_expr_df.shape,
            'sample_info': sample_info,
            'sample_ids': sample_ids,
            'subcategory_scores': subcategory_scores,
            'system_scores': system_scores,
            'analysis_timestamp': datetime.now().isoformat()
        }

def main():
    """主函数"""
    print("="*80)
    print("COMPREHENSIVE DISEASE ANALYSIS")
    print("="*80)
    
    try:
        analyzer = ComprehensiveDiseaseAnalyzer()
        
        # 创建分析计划
        system_disease_map = analyzer.create_analysis_plan()
        
        print(f"\n🚀 Starting comprehensive analysis...")
        
        # 分析每个数据集
        all_results = {}
        
        for dataset_id in analyzer.datasets.keys():
            try:
                results = analyzer.analyze_single_dataset(dataset_id)
                if results is not None:
                    all_results[dataset_id] = results
                    print(f"✅ {dataset_id} analysis completed")
                else:
                    print(f"❌ {dataset_id} analysis failed")
            except Exception as e:
                print(f"❌ Error analyzing {dataset_id}: {str(e)}")
        
        print(f"\n📊 Analysis Summary:")
        print(f"   • Total datasets: {len(analyzer.datasets)}")
        print(f"   • Successfully analyzed: {len(all_results)}")
        print(f"   • Failed: {len(analyzer.datasets) - len(all_results)}")
        
        if all_results:
            # 保存结果
            output_file = "comprehensive_disease_analysis_results.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Results saved to: {output_file}")
            
            # 显示关键发现
            print(f"\n🎯 Key Findings:")
            for dataset_id, results in all_results.items():
                dataset_info = analyzer.datasets[dataset_id]
                system_scores = [(system, info['mean_score']) for system, info in results['system_scores'].items()]
                system_scores.sort(key=lambda x: x[1], reverse=True)
                
                if system_scores:
                    top_system = system_scores[0][0]
                    expected_systems = dataset_info['expected_systems']
                    validation = "✅" if top_system in expected_systems else "⚠️"
                    
                    print(f"   • {dataset_id} ({dataset_info['chinese_name']}): {top_system} {validation}")
        
    except Exception as e:
        print(f"❌ Error in comprehensive analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()