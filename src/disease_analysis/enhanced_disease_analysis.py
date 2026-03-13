#!/usr/bin/env python3
"""
增强疾病分析
1. GSE26168糖尿病数据集的双平台分析
2. 伤口愈合数据集的联合时间序列分析
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

class EnhancedDiseaseAnalyzer:
    def __init__(self):
        """初始化增强疾病分析器"""
        
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
    
    def analyze_gse26168_diabetes(self):
        """分析GSE26168糖尿病数据集的两个平台"""
        print(f"\n{'='*80}")
        print("ANALYZING GSE26168 DIABETES - DUAL PLATFORM ANALYSIS")
        print(f"{'='*80}")
        
        # 定义两个平台的数据
        platforms = {
            'GPL6883': {
                'data_file': 'data/validation_datasets/GSE26168-糖尿病/GSE26168-GPL6883_series_matrix.txt.gz',
                'platform_file': 'data/validation_datasets/GSE26168-糖尿病/GPL6883-11606.txt',
                'name': 'Illumina MouseRef-8 v2.0'
            },
            'GPL10322': {
                'data_file': 'data/validation_datasets/GSE26168-糖尿病/GSE26168-GPL10322_series_matrix.txt.gz',
                'platform_file': 'data/validation_datasets/GSE26168-糖尿病/GPL10322.txt',
                'name': 'Agilent-011978 Mouse Microarray'
            }
        }
        
        all_results = {}
        
        for platform_id, platform_info in platforms.items():
            print(f"\n🔬 Analyzing {platform_id} - {platform_info['name']}")
            
            # 检查文件是否存在
            if not os.path.exists(platform_info['data_file']):
                print(f"❌ Data file not found: {platform_info['data_file']}")
                continue
            
            # 加载表达数据
            expr_df, sample_info = self.load_expression_data(platform_info['data_file'], f"GSE26168-{platform_id}")
            if expr_df is None:
                continue
            
            # 加载平台注释
            probe_to_gene = None
            if os.path.exists(platform_info['platform_file']):
                probe_to_gene = self.load_platform_annotation(platform_info['platform_file'])
            
            # 创建基因级表达矩阵
            gene_expr_df = self.create_gene_expression_matrix(expr_df, probe_to_gene)
            if gene_expr_df.empty:
                print(f"❌ Failed to create gene expression matrix for {platform_id}")
                continue
            
            # 执行ssGSEA分析
            results = self.perform_dataset_ssgsea(gene_expr_df, sample_info, f"GSE26168-{platform_id}")
            
            if results is not None:
                results['platform_info'] = platform_info
                all_results[platform_id] = results
                print(f"✅ {platform_id} analysis completed")
            else:
                print(f"❌ {platform_id} analysis failed")
        
        # 保存结果
        if all_results:
            output_file = "gse26168_diabetes_dual_platform_results.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Results saved to: {output_file}")
            
            # 比较两个平台的结果
            self.compare_platform_results(all_results)
        
        return all_results
    
    def compare_platform_results(self, platform_results):
        """比较两个平台的分析结果"""
        print(f"\n📊 Platform Comparison Analysis:")
        
        if len(platform_results) < 2:
            print("  Need at least 2 platforms for comparison")
            return
        
        platform_ids = list(platform_results.keys())
        
        print(f"\n🔍 System Activation Comparison:")
        
        # 比较系统激活模式
        for system in self.systems.keys():
            print(f"\n  {system} ({self.systems[system]['chinese_name']}):")
            
            for platform_id in platform_ids:
                if 'system_scores' in platform_results[platform_id]:
                    system_scores = platform_results[platform_id]['system_scores']
                    if system in system_scores:
                        score = system_scores[system]['mean_score']
                        print(f"    {platform_id}: {score:.4f}")
        
        # 计算系统得分相关性
        if len(platform_ids) == 2:
            platform1, platform2 = platform_ids
            
            scores1 = []
            scores2 = []
            system_names = []
            
            for system in self.systems.keys():
                if ('system_scores' in platform_results[platform1] and 
                    'system_scores' in platform_results[platform2] and
                    system in platform_results[platform1]['system_scores'] and
                    system in platform_results[platform2]['system_scores']):
                    
                    score1 = platform_results[platform1]['system_scores'][system]['mean_score']
                    score2 = platform_results[platform2]['system_scores'][system]['mean_score']
                    
                    scores1.append(score1)
                    scores2.append(score2)
                    system_names.append(system)
            
            if len(scores1) > 2:
                correlation = np.corrcoef(scores1, scores2)[0, 1]
                print(f"\n📈 Platform Correlation:")
                print(f"  System score correlation: {correlation:.4f}")
                
                if correlation > 0.7:
                    print(f"  ✅ High correlation - consistent results across platforms")
                elif correlation > 0.4:
                    print(f"  ⚠️ Moderate correlation - some platform differences")
                else:
                    print(f"  ❌ Low correlation - significant platform differences")
    
    def analyze_wound_healing_temporal(self):
        """联合分析两个伤口愈合数据集的时间序列"""
        print(f"\n{'='*80}")
        print("WOUND HEALING TEMPORAL ANALYSIS - COMBINED DATASETS")
        print(f"{'='*80}")
        
        # 定义两个伤口愈合数据集
        datasets = {
            'GSE28914': {
                'data_file': 'data/validation_datasets/GSE28914-伤口愈合1/GSE28914_series_matrix.txt.gz',
                'platform_file': 'data/validation_datasets/GSE28914-伤口愈合1/GPL570-55999.txt',
                'name': 'Wound Healing Study 1',
                'timepoints': ['Baseline', 'Acute', 'Day_3', 'Day_7']
            },
            'GSE50425': {
                'data_file': 'data/validation_datasets/GSE50425-伤口愈合2/GSE50425_series_matrix.txt.gz',
                'platform_file': 'data/validation_datasets/GSE50425-伤口愈合2/GPL10558-50081.txt',
                'name': 'Wound Healing Study 2',
                'timepoints': []  # 需要从数据中提取
            }
        }
        
        all_results = {}
        
        # 分析每个数据集
        for dataset_id, dataset_info in datasets.items():
            print(f"\n🔬 Analyzing {dataset_id} - {dataset_info['name']}")
            
            # 检查文件是否存在
            if not os.path.exists(dataset_info['data_file']):
                print(f"❌ Data file not found: {dataset_info['data_file']}")
                continue
            
            # 加载表达数据
            expr_df, sample_info = self.load_expression_data(dataset_info['data_file'], dataset_id)
            if expr_df is None:
                continue
            
            # 加载平台注释
            probe_to_gene = None
            if os.path.exists(dataset_info['platform_file']):
                probe_to_gene = self.load_platform_annotation(dataset_info['platform_file'])
            
            # 创建基因级表达矩阵
            gene_expr_df = self.create_gene_expression_matrix(expr_df, probe_to_gene)
            if gene_expr_df.empty:
                print(f"❌ Failed to create gene expression matrix for {dataset_id}")
                continue
            
            # 解析时间点信息
            temporal_info = self.extract_temporal_information(sample_info, dataset_id)
            
            # 执行时间序列ssGSEA分析
            results = self.perform_temporal_ssgsea(gene_expr_df, temporal_info, dataset_id)
            
            if results is not None:
                results['dataset_info'] = dataset_info
                all_results[dataset_id] = results
                print(f"✅ {dataset_id} temporal analysis completed")
            else:
                print(f"❌ {dataset_id} temporal analysis failed")
        
        # 保存结果
        if all_results:
            output_file = "wound_healing_temporal_analysis_results.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Results saved to: {output_file}")
            
            # 分析时间序列模式和相位差
            self.analyze_temporal_patterns(all_results)
        
        return all_results
    
    def extract_temporal_information(self, sample_info, dataset_id):
        """提取时间点信息"""
        print(f"  Extracting temporal information for {dataset_id}...")
        
        temporal_info = {
            'sample_ids': sample_info.get('accessions', []),
            'sample_titles': sample_info.get('titles', []),
            'timepoints': [],
            'timepoint_mapping': {}
        }
        
        if dataset_id == 'GSE28914':
            # GSE28914的时间点信息
            for i, title in enumerate(temporal_info['sample_titles']):
                title_lower = title.lower()
                if 'intact skin' in title_lower or 'baseline' in title_lower:
                    timepoint = 'Baseline'
                    day_numeric = 0
                elif 'acute wound' in title_lower or 'acute' in title_lower:
                    timepoint = 'Acute'
                    day_numeric = 0
                elif '3rd post-operative' in title_lower or 'day 3' in title_lower:
                    timepoint = 'Day_3'
                    day_numeric = 3
                elif '7th post-operative' in title_lower or 'day 7' in title_lower:
                    timepoint = 'Day_7'
                    day_numeric = 7
                else:
                    timepoint = 'Unknown'
                    day_numeric = -1
                
                temporal_info['timepoints'].append({
                    'sample_index': i,
                    'sample_id': temporal_info['sample_ids'][i] if i < len(temporal_info['sample_ids']) else f"Sample_{i+1}",
                    'timepoint': timepoint,
                    'day_numeric': day_numeric,
                    'title': title
                })
        
        elif dataset_id == 'GSE50425':
            # GSE50425的时间点信息需要从样本标题中推断
            for i, title in enumerate(temporal_info['sample_titles']):
                title_lower = title.lower()
                
                # 尝试从标题中提取时间信息
                if 'day 0' in title_lower or 'd0' in title_lower or 'baseline' in title_lower:
                    timepoint = 'Day_0'
                    day_numeric = 0
                elif 'day 1' in title_lower or 'd1' in title_lower:
                    timepoint = 'Day_1'
                    day_numeric = 1
                elif 'day 3' in title_lower or 'd3' in title_lower:
                    timepoint = 'Day_3'
                    day_numeric = 3
                elif 'day 7' in title_lower or 'd7' in title_lower:
                    timepoint = 'Day_7'
                    day_numeric = 7
                elif 'day 14' in title_lower or 'd14' in title_lower:
                    timepoint = 'Day_14'
                    day_numeric = 14
                elif 'day 21' in title_lower or 'd21' in title_lower:
                    timepoint = 'Day_21'
                    day_numeric = 21
                else:
                    # 尝试从数字中提取
                    import re
                    day_match = re.search(r'day\s*(\d+)', title_lower)
                    if day_match:
                        day_num = int(day_match.group(1))
                        timepoint = f'Day_{day_num}'
                        day_numeric = day_num
                    else:
                        timepoint = 'Unknown'
                        day_numeric = -1
                
                temporal_info['timepoints'].append({
                    'sample_index': i,
                    'sample_id': temporal_info['sample_ids'][i] if i < len(temporal_info['sample_ids']) else f"Sample_{i+1}",
                    'timepoint': timepoint,
                    'day_numeric': day_numeric,
                    'title': title
                })
        
        # 创建时间点映射
        for tp_info in temporal_info['timepoints']:
            timepoint = tp_info['timepoint']
            if timepoint not in temporal_info['timepoint_mapping']:
                temporal_info['timepoint_mapping'][timepoint] = []
            temporal_info['timepoint_mapping'][timepoint].append(tp_info)
        
        # 显示时间点统计
        print(f"    Identified timepoints:")
        for timepoint, samples in temporal_info['timepoint_mapping'].items():
            print(f"      {timepoint}: {len(samples)} samples")
        
        return temporal_info
    
    def perform_temporal_ssgsea(self, gene_expr_df, temporal_info, dataset_id):
        """执行时间序列ssGSEA分析"""
        print(f"  Performing temporal ssGSEA for {dataset_id}...")
        
        # 按时间点分组计算ssGSEA得分
        temporal_results = {}
        
        for timepoint, sample_list in temporal_info['timepoint_mapping'].items():
            if timepoint == 'Unknown':
                continue
            
            print(f"    Analyzing timepoint: {timepoint}")
            
            # 获取该时间点的样本索引
            sample_indices = [s['sample_index'] for s in sample_list]
            sample_columns = [gene_expr_df.columns[i] for i in sample_indices if i < len(gene_expr_df.columns)]
            
            if not sample_columns:
                print(f"      No valid samples for {timepoint}")
                continue
            
            # 提取该时间点的表达数据
            timepoint_expr = gene_expr_df[sample_columns]
            
            # 计算每个子分类的ssGSEA得分
            subcategory_scores = {}
            
            for subcat_code, subcat_info in self.gene_sets.items():
                gene_set_genes = subcat_info['genes']
                
                if len(gene_set_genes) == 0:
                    scores = np.zeros(len(sample_columns))
                else:
                    scores = self.perform_ssgsea(timepoint_expr, gene_set_genes)
                
                subcategory_scores[subcat_code] = {
                    'scores': scores.tolist(),
                    'mean_score': float(np.mean(scores)),
                    'std_score': float(np.std(scores)),
                    'sample_count': len(sample_columns)
                }
            
            # 计算系统级分数
            system_scores = {}
            for system_name, system_info in self.systems.items():
                subcats = system_info['subcategories']
                system_score_arrays = []
                for subcat in subcats:
                    if subcat in subcategory_scores:
                        system_score_arrays.append(subcategory_scores[subcat]['scores'])
                
                if system_score_arrays:
                    system_scores_array = np.mean(system_score_arrays, axis=0)
                    system_scores[system_name] = {
                        'scores': system_scores_array.tolist(),
                        'mean_score': float(np.mean(system_scores_array)),
                        'std_score': float(np.std(system_scores_array))
                    }
            
            temporal_results[timepoint] = {
                'day_numeric': sample_list[0]['day_numeric'],
                'sample_count': len(sample_columns),
                'sample_info': sample_list,
                'subcategory_scores': subcategory_scores,
                'system_scores': system_scores
            }
        
        return {
            'dataset_id': dataset_id,
            'temporal_results': temporal_results,
            'temporal_info': temporal_info,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def analyze_temporal_patterns(self, all_results):
        """分析时间序列模式和相位差"""
        print(f"\n🕒 Temporal Pattern Analysis:")
        
        # 收集所有时间点数据
        combined_temporal_data = {}
        
        for dataset_id, results in all_results.items():
            print(f"\n📊 {dataset_id} Temporal Patterns:")
            
            temporal_results = results['temporal_results']
            
            # 按时间排序
            sorted_timepoints = sorted(temporal_results.items(), 
                                     key=lambda x: x[1]['day_numeric'])
            
            print(f"  Time progression:")
            for timepoint, data in sorted_timepoints:
                day = data['day_numeric']
                sample_count = data['sample_count']
                
                # 找出该时间点的主导系统
                system_scores = [(system, info['mean_score']) 
                               for system, info in data['system_scores'].items()]
                system_scores.sort(key=lambda x: x[1], reverse=True)
                
                if system_scores:
                    top_system = system_scores[0][0]
                    top_score = system_scores[0][1]
                    system_name = self.systems[top_system]['chinese_name']
                    print(f"    Day {day} ({timepoint}): {top_system} ({system_name}) - {top_score:.4f} (n={sample_count})")
                
                # 存储到组合数据中
                if day not in combined_temporal_data:
                    combined_temporal_data[day] = {}
                
                for system, info in data['system_scores'].items():
                    if system not in combined_temporal_data[day]:
                        combined_temporal_data[day][system] = []
                    combined_temporal_data[day][system].append({
                        'dataset': dataset_id,
                        'timepoint': timepoint,
                        'score': info['mean_score'],
                        'sample_count': sample_count
                    })
        
        # 分析跨数据集的时间模式
        self.analyze_cross_dataset_temporal_patterns(combined_temporal_data)
        
        # 分析系统激活的相位差
        self.analyze_system_phase_shifts(combined_temporal_data)
    
    def analyze_cross_dataset_temporal_patterns(self, combined_temporal_data):
        """分析跨数据集的时间模式"""
        print(f"\n🔄 Cross-Dataset Temporal Patterns:")
        
        # 按时间排序
        sorted_days = sorted(combined_temporal_data.keys())
        
        print(f"  Combined timeline analysis:")
        for day in sorted_days:
            print(f"\n    Day {day}:")
            
            # 计算每个系统在该时间点的平均激活
            system_avg_scores = {}
            for system in self.systems.keys():
                if system in combined_temporal_data[day]:
                    scores = [entry['score'] for entry in combined_temporal_data[day][system]]
                    datasets = [entry['dataset'] for entry in combined_temporal_data[day][system]]
                    
                    avg_score = np.mean(scores)
                    system_avg_scores[system] = {
                        'score': avg_score,
                        'datasets': datasets,
                        'count': len(scores)
                    }
            
            # 排序并显示
            sorted_systems = sorted(system_avg_scores.items(), 
                                  key=lambda x: x[1]['score'], reverse=True)
            
            for i, (system, info) in enumerate(sorted_systems):
                system_name = self.systems[system]['chinese_name']
                score = info['score']
                count = info['count']
                datasets = ', '.join(set(info['datasets']))
                print(f"      {i+1}. {system} ({system_name}): {score:.4f} (n={count}, {datasets})")
    
    def analyze_system_phase_shifts(self, combined_temporal_data):
        """分析系统激活的相位差"""
        print(f"\n⚡ System Phase Shift Analysis:")
        
        # 为每个系统找到峰值激活时间
        system_peak_times = {}
        
        for system in self.systems.keys():
            system_timeline = []
            
            for day in sorted(combined_temporal_data.keys()):
                if system in combined_temporal_data[day]:
                    scores = [entry['score'] for entry in combined_temporal_data[day][system]]
                    avg_score = np.mean(scores)
                    system_timeline.append((day, avg_score))
            
            if len(system_timeline) >= 2:
                # 找到峰值
                max_score = max(system_timeline, key=lambda x: x[1])
                peak_day = max_score[0]
                peak_score = max_score[1]
                
                system_peak_times[system] = {
                    'peak_day': peak_day,
                    'peak_score': peak_score,
                    'timeline': system_timeline
                }
        
        # 显示系统激活顺序
        print(f"\n  System activation sequence:")
        sorted_peaks = sorted(system_peak_times.items(), 
                            key=lambda x: x[1]['peak_day'])
        
        for i, (system, info) in enumerate(sorted_peaks):
            system_name = self.systems[system]['chinese_name']
            peak_day = info['peak_day']
            peak_score = info['peak_score']
            print(f"    {i+1}. {system} ({system_name}): Peak at Day {peak_day} (score: {peak_score:.4f})")
        
        # 分析相位差
        print(f"\n  Phase shift analysis:")
        if len(sorted_peaks) >= 2:
            for i in range(len(sorted_peaks) - 1):
                system1, info1 = sorted_peaks[i]
                system2, info2 = sorted_peaks[i + 1]
                
                phase_shift = info2['peak_day'] - info1['peak_day']
                
                system1_name = self.systems[system1]['chinese_name']
                system2_name = self.systems[system2]['chinese_name']
                
                print(f"    {system1} → {system2}: {phase_shift} days")
                print(f"      ({system1_name} → {system2_name})")
        
        # 保存相位分析结果
        phase_analysis = {
            'system_peak_times': system_peak_times,
            'activation_sequence': [(s, info['peak_day']) for s, info in sorted_peaks],
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        with open('wound_healing_phase_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(phase_analysis, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Phase analysis saved to: wound_healing_phase_analysis.json")
    
    # 复用之前的方法
    def load_expression_data(self, data_path, dataset_name):
        """加载表达数据"""
        print(f"  Loading expression data for {dataset_name}...")
        
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
                print(f"    Error: Could not find data table start")
                return None, None
            
            # 读取数据表
            data_lines = []
            for line in lines[data_start:]:
                if line.startswith('!series_matrix_table_end'):
                    break
                data_lines.append(line.strip().split('\t'))
            
            if len(data_lines) < 2:
                print(f"    Error: Insufficient data")
                return None, None
            
            # 创建DataFrame
            header = [col.strip('"') for col in data_lines[0]]
            data_rows = [[cell.strip('"') for cell in row] for row in data_lines[1:]]
            
            expr_df = pd.DataFrame(data_rows, columns=header)
            
            # 设置探针ID为索引
            if 'ID_REF' in expr_df.columns:
                expr_df = expr_df.set_index('ID_REF')
            else:
                print(f"    Error: ID_REF column not found")
                return None, None
            
            # 转换表达值为数值
            for col in expr_df.columns:
                expr_df[col] = pd.to_numeric(expr_df[col], errors='coerce')
            
            # 移除缺失值过多的行
            expr_df = expr_df.dropna(thresh=len(expr_df.columns) * 0.5)
            
            print(f"    Successfully loaded: {expr_df.shape[0]} probes x {expr_df.shape[1]} samples")
            print(f"    Expression range: {expr_df.min().min():.2f} to {expr_df.max().max():.2f}")
            
            return expr_df, sample_info
            
        except Exception as e:
            print(f"    Error loading {dataset_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def load_platform_annotation(self, platform_file):
        """加载平台注释文件"""
        print(f"    Loading platform annotation...")
        
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
                print(f"      Error: Could not find platform data start")
                return None
            
            # 读取平台数据
            platform_lines = []
            for line in lines[data_start:]:
                if line.startswith('!platform_table_end'):
                    break
                platform_lines.append(line.strip().split('\t'))
            
            if len(platform_lines) < 2:
                print(f"      Error: Insufficient platform data")
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
                print(f"      Error: No gene symbol column found")
                print(f"      Available columns: {platform_df.columns.tolist()}")
                return None
            
            # 使用第一个基因符号列
            gene_col = gene_symbol_cols[0]
            print(f"      Using gene symbol column: {gene_col}")
            
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
            
            print(f"      Mapped {len(probe_to_gene)} probes to genes ({valid_mappings} valid mappings)")
            
            return probe_to_gene
            
        except Exception as e:
            print(f"      Error loading platform annotation: {str(e)}")
            return None
    
    def create_gene_expression_matrix(self, expr_df, probe_to_gene):
        """创建基因级表达矩阵"""
        print(f"    Creating gene-level expression matrix...")
        
        if probe_to_gene is None:
            print(f"      Warning: No probe-to-gene mapping, using probe IDs as gene names")
            gene_expr_df = expr_df.copy()
            gene_expr_df.index.name = 'Gene'
            print(f"      Created expression matrix: {gene_expr_df.shape[0]} probes x {gene_expr_df.shape[1]} samples")
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
            print(f"      No valid gene expression data found, using probe IDs")
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
                    print(f"        Warning: Could not process gene {gene}: {e}")
                    continue
        
        if not gene_data:
            print(f"      Failed to create gene expression matrix")
            return pd.DataFrame()
        
        # 创建DataFrame
        gene_expr_df = pd.DataFrame.from_dict(gene_data, orient='index', columns=expr_df.columns)
        
        print(f"      Created gene expression matrix: {gene_expr_df.shape[0]} genes x {gene_expr_df.shape[1]} samples")
        
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
        print(f"    Performing ssGSEA for 14 subcategories...")
        
        subcategory_scores = {}
        
        for subcat_code, subcat_info in self.gene_sets.items():
            print(f"      Analyzing {subcat_code}: {subcat_info['name']}")
            
            # 获取该子分类的基因
            gene_set_genes = subcat_info['genes']
            
            if len(gene_set_genes) == 0:
                print(f"        No genes found for {subcat_code}")
                scores = np.zeros(gene_expr_df.shape[1])
            else:
                # 执行真实ssGSEA
                scores = self.perform_ssgsea(gene_expr_df, gene_set_genes)
                
                # 计算基因重叠
                available_genes = set(gene_expr_df.index)
                matched_genes = list(set(gene_set_genes) & available_genes)
                overlap_pct = len(matched_genes) / len(gene_set_genes) * 100 if gene_set_genes else 0
                
                print(f"        Gene overlap: {len(matched_genes)}/{len(gene_set_genes)} ({overlap_pct:.1f}%)")
                print(f"        ssGSEA scores: {np.mean(scores):.3f} ± {np.std(scores):.3f}")
            
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
    print("ENHANCED DISEASE ANALYSIS")
    print("="*80)
    
    try:
        analyzer = EnhancedDiseaseAnalyzer()
        
        print(f"\n🎯 Starting enhanced analysis...")
        
        # 1. 分析GSE26168糖尿病数据集的双平台
        print(f"\n{'='*60}")
        print("TASK 1: GSE26168 DIABETES DUAL PLATFORM ANALYSIS")
        print(f"{'='*60}")
        
        diabetes_results = analyzer.analyze_gse26168_diabetes()
        
        # 2. 分析伤口愈合数据集的时间序列
        print(f"\n{'='*60}")
        print("TASK 2: WOUND HEALING TEMPORAL ANALYSIS")
        print(f"{'='*60}")
        
        wound_healing_results = analyzer.analyze_wound_healing_temporal()
        
        print(f"\n{'='*80}")
        print("ENHANCED ANALYSIS COMPLETED!")
        print(f"{'='*80}")
        
        print(f"\n🎉 Summary:")
        if diabetes_results:
            print(f"   • GSE26168 diabetes analysis: {len(diabetes_results)} platforms analyzed")
        if wound_healing_results:
            print(f"   • Wound healing temporal analysis: {len(wound_healing_results)} datasets analyzed")
        
        print(f"\n📁 Generated files:")
        print(f"   • gse26168_diabetes_dual_platform_results.json")
        print(f"   • wound_healing_temporal_analysis_results.json")
        print(f"   • wound_healing_phase_analysis.json")
        
    except Exception as e:
        print(f"❌ Error in enhanced analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()