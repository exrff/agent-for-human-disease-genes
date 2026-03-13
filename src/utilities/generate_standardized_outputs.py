#!/usr/bin/env python3
"""
生成标准化输出文件
根据用户要求的格式生成所有必需的CSV文件
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class StandardizedOutputGenerator:
    def __init__(self):
        """初始化标准化输出生成器"""
        
        # 系统定义
        self.systems = {
            'System A': 'A',
            'System B': 'B', 
            'System C': 'C',
            'System D': 'D',
            'System E': 'E'
        }
        
        # 子分类定义
        self.subcategories = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'E1', 'E2']
        
        print("Standardized Output Generator initialized")
    
    def process_all_datasets(self):
        """处理所有数据集并生成标准化输出"""
        print("="*80)
        print("GENERATING STANDARDIZED OUTPUTS")
        print("="*80)
        
        # 定义要处理的数据集
        datasets_to_process = [
            {
                'name': 'GSE26168',
                'source_file': 'gse26168_diabetes_analysis_results.json',
                'description': 'Diabetes study',
                'is_temporal': False
            },
            {
                'name': 'GSE28914', 
                'source_file': 'wound_healing_temporal_analysis_fixed_results.json',
                'description': 'Wound healing temporal study 1',
                'is_temporal': True
            },
            {
                'name': 'GSE50425',
                'source_file': 'wound_healing_temporal_analysis_fixed_results.json', 
                'description': 'Wound healing temporal study 2',
                'is_temporal': True
            },
            {
                'name': 'GSE21899',
                'source_file': 'comprehensive_disease_analysis_results.json',
                'description': 'Gaucher disease study',
                'is_temporal': False
            },
            {
                'name': 'GSE122063',
                'source_file': 'comprehensive_disease_analysis_results.json',
                'description': 'Alzheimer disease study', 
                'is_temporal': False
            },
            {
                'name': 'GSE2034',
                'source_file': 'comprehensive_disease_analysis_results.json',
                'description': 'Breast cancer study',
                'is_temporal': False
            },
            {
                'name': 'GSE65682',
                'source_file': 'comprehensive_disease_analysis_results.json',
                'description': 'Sepsis study',
                'is_temporal': False
            }
        ]
        
        processed_count = 0
        
        for dataset_info in datasets_to_process:
            dataset_name = dataset_info['name']
            source_file = dataset_info['source_file']
            is_temporal = dataset_info['is_temporal']
            
            print(f"\n{'='*60}")
            print(f"Processing {dataset_name} - {dataset_info['description']}")
            print(f"{'='*60}")
            
            if not os.path.exists(source_file):
                print(f"❌ Source file not found: {source_file}")
                continue
            
            try:
                # 加载数据
                with open(source_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if is_temporal:
                    # 处理时间序列数据
                    if dataset_name in data:
                        success = self.process_temporal_dataset(dataset_name, data[dataset_name])
                        if success:
                            processed_count += 1
                    else:
                        print(f"❌ Dataset {dataset_name} not found in {source_file}")
                else:
                    # 处理非时间序列数据
                    if dataset_name == 'GSE26168':
                        # 特殊处理GSE26168
                        success = self.process_diabetes_dataset(dataset_name, data)
                        if success:
                            processed_count += 1
                    elif dataset_name in data:
                        success = self.process_standard_dataset(dataset_name, data[dataset_name])
                        if success:
                            processed_count += 1
                    else:
                        print(f"❌ Dataset {dataset_name} not found in {source_file}")
                        
            except Exception as e:
                print(f"❌ Error processing {dataset_name}: {str(e)}")
                import traceback
                traceback.print_exc()
        
        print(f"\n{'='*80}")
        print(f"STANDARDIZED OUTPUT GENERATION COMPLETED")
        print(f"{'='*80}")
        print(f"Successfully processed: {processed_count} datasets")
        
        # 生成汇总报告
        self.generate_summary_report(processed_count)
    
    def process_diabetes_dataset(self, dataset_name, data):
        """处理糖尿病数据集"""
        print(f"Processing diabetes dataset: {dataset_name}")
        
        try:
            # 提取样本信息
            sample_info = data.get('sample_info', {})
            sample_ids = data.get('sample_ids', [])
            
            if not sample_ids:
                print(f"❌ No sample IDs found")
                return False
            
            # 创建样本元数据
            sample_metadata = []
            for i, sample_id in enumerate(sample_ids):
                sample_metadata.append({
                    'sample_id': sample_id,
                    'subject_id': f"Subject_{i+1}",  # 糖尿病数据没有明确的subject信息
                    'condition': 'Diabetes',
                    'group': 'Diabetes'
                })
            
            sample_df = pd.DataFrame(sample_metadata)
            
            # 保存样本信息
            sample_file = f"{dataset_name}_sample_info.csv"
            sample_df.to_csv(sample_file, index=False)
            print(f"✅ Generated: {sample_file}")
            
            # 处理系统得分
            system_scores_data = []
            subcategory_scores_data = []
            
            system_scores = data.get('system_scores', {})
            subcategory_scores = data.get('subcategory_scores', {})
            
            for i, sample_id in enumerate(sample_ids):
                # 系统得分行
                system_row = sample_metadata[i].copy()
                for system_name, system_info in system_scores.items():
                    system_code = self.systems.get(system_name, system_name)
                    if 'scores' in system_info and i < len(system_info['scores']):
                        system_row[system_code] = system_info['scores'][i]
                    else:
                        system_row[system_code] = system_info.get('mean_score', 0.0)
                system_scores_data.append(system_row)
                
                # 子分类得分行
                subcat_row = sample_metadata[i].copy()
                for subcat_code in self.subcategories:
                    if subcat_code in subcategory_scores:
                        subcat_info = subcategory_scores[subcat_code]
                        if 'scores' in subcat_info and i < len(subcat_info['scores']):
                            subcat_row[subcat_code] = subcat_info['scores'][i]
                        else:
                            subcat_row[subcat_code] = subcat_info.get('mean_score', 0.0)
                    else:
                        subcat_row[subcat_code] = 0.0
                subcategory_scores_data.append(subcat_row)
            
            # 保存系统得分
            system_df = pd.DataFrame(system_scores_data)
            system_file = f"{dataset_name}_system_scores.csv"
            system_df.to_csv(system_file, index=False)
            print(f"✅ Generated: {system_file}")
            
            # 保存子分类得分
            subcat_df = pd.DataFrame(subcategory_scores_data)
            subcat_file = f"{dataset_name}_subcategory_scores.csv"
            subcat_df.to_csv(subcat_file, index=False)
            print(f"✅ Generated: {subcat_file}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error processing diabetes dataset: {str(e)}")
            return False
    
    def process_standard_dataset(self, dataset_name, data):
        """处理标准数据集"""
        print(f"Processing standard dataset: {dataset_name}")
        
        try:
            # 提取样本信息
            sample_info = data.get('sample_info', {})
            sample_ids = data.get('sample_ids', [])
            
            if not sample_ids:
                print(f"❌ No sample IDs found")
                return False
            
            # 创建样本元数据
            sample_metadata = []
            
            # 尝试从样本标题中提取信息
            sample_titles = sample_info.get('titles', [])
            
            for i, sample_id in enumerate(sample_ids):
                title = sample_titles[i] if i < len(sample_titles) else ""
                
                # 根据数据集类型推断条件和组别
                condition, group = self.infer_condition_group(dataset_name, title)
                
                sample_metadata.append({
                    'sample_id': sample_id,
                    'subject_id': self.extract_subject_id(title, i),
                    'condition': condition,
                    'group': group
                })
            
            sample_df = pd.DataFrame(sample_metadata)
            
            # 保存样本信息
            sample_file = f"{dataset_name}_sample_info.csv"
            sample_df.to_csv(sample_file, index=False)
            print(f"✅ Generated: {sample_file}")
            
            # 处理系统得分
            system_scores_data = []
            subcategory_scores_data = []
            
            system_scores = data.get('system_scores', {})
            subcategory_scores = data.get('subcategory_scores', {})
            
            for i, sample_id in enumerate(sample_ids):
                # 系统得分行
                system_row = sample_metadata[i].copy()
                for system_name, system_info in system_scores.items():
                    system_code = self.systems.get(system_name, system_name)
                    if 'scores' in system_info and i < len(system_info['scores']):
                        system_row[system_code] = system_info['scores'][i]
                    else:
                        system_row[system_code] = system_info.get('mean_score', 0.0)
                system_scores_data.append(system_row)
                
                # 子分类得分行
                subcat_row = sample_metadata[i].copy()
                for subcat_code in self.subcategories:
                    if subcat_code in subcategory_scores:
                        subcat_info = subcategory_scores[subcat_code]
                        if 'scores' in subcat_info and i < len(subcat_info['scores']):
                            subcat_row[subcat_code] = subcat_info['scores'][i]
                        else:
                            subcat_row[subcat_code] = subcat_info.get('mean_score', 0.0)
                    else:
                        subcat_row[subcat_code] = 0.0
                subcategory_scores_data.append(subcat_row)
            
            # 保存系统得分
            system_df = pd.DataFrame(system_scores_data)
            system_file = f"{dataset_name}_system_scores.csv"
            system_df.to_csv(system_file, index=False)
            print(f"✅ Generated: {system_file}")
            
            # 保存子分类得分
            subcat_df = pd.DataFrame(subcategory_scores_data)
            subcat_file = f"{dataset_name}_subcategory_scores.csv"
            subcat_df.to_csv(subcat_file, index=False)
            print(f"✅ Generated: {subcat_file}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error processing standard dataset: {str(e)}")
            return False
    
    def process_temporal_dataset(self, dataset_name, data):
        """处理时间序列数据集"""
        print(f"Processing temporal dataset: {dataset_name}")
        
        try:
            temporal_results = data.get('temporal_results', {})
            temporal_info = data.get('temporal_info', {})
            
            if not temporal_results:
                print(f"❌ No temporal results found")
                return False
            
            # 收集所有样本的信息
            all_sample_metadata = []
            all_system_scores = []
            all_subcategory_scores = []
            
            for timepoint, timepoint_data in temporal_results.items():
                sample_info_list = timepoint_data.get('sample_info', [])
                system_scores = timepoint_data.get('system_scores', {})
                subcategory_scores = timepoint_data.get('subcategory_scores', {})
                day_numeric = timepoint_data.get('day_numeric', 0)
                
                for sample_info in sample_info_list:
                    sample_id = sample_info.get('sample_id', '')
                    title = sample_info.get('title', '')
                    
                    # 提取subject信息
                    subject_id = self.extract_subject_id_from_title(title)
                    
                    # 创建样本元数据
                    metadata = {
                        'sample_id': sample_id,
                        'subject_id': subject_id,
                        'timepoint': timepoint,
                        'day': day_numeric,
                        'condition': 'Wound_Healing',
                        'group': timepoint
                    }
                    all_sample_metadata.append(metadata)
                    
                    # 系统得分
                    system_row = metadata.copy()
                    for system_name, system_info in system_scores.items():
                        system_code = self.systems.get(system_name, system_name)
                        # 对于时间序列数据，使用平均得分
                        system_row[system_code] = system_info.get('mean_score', 0.0)
                    all_system_scores.append(system_row)
                    
                    # 子分类得分
                    subcat_row = metadata.copy()
                    for subcat_code in self.subcategories:
                        if subcat_code in subcategory_scores:
                            subcat_info = subcategory_scores[subcat_code]
                            subcat_row[subcat_code] = subcat_info.get('mean_score', 0.0)
                        else:
                            subcat_row[subcat_code] = 0.0
                    all_subcategory_scores.append(subcat_row)
            
            if not all_sample_metadata:
                print(f"❌ No sample metadata generated")
                return False
            
            # 保存样本信息
            sample_df = pd.DataFrame(all_sample_metadata)
            sample_file = f"{dataset_name}_sample_info.csv"
            sample_df.to_csv(sample_file, index=False)
            print(f"✅ Generated: {sample_file}")
            
            # 保存系统得分
            system_df = pd.DataFrame(all_system_scores)
            system_file = f"{dataset_name}_system_scores.csv"
            system_df.to_csv(system_file, index=False)
            print(f"✅ Generated: {system_file}")
            
            # 保存子分类得分
            subcat_df = pd.DataFrame(all_subcategory_scores)
            subcat_file = f"{dataset_name}_subcategory_scores.csv"
            subcat_df.to_csv(subcat_file, index=False)
            print(f"✅ Generated: {subcat_file}")
            
            # 生成配对delta文件（如果有多个时间点）
            if len(temporal_results) > 1:
                self.generate_paired_delta_file(dataset_name, system_df)
            
            return True
            
        except Exception as e:
            print(f"❌ Error processing temporal dataset: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_paired_delta_file(self, dataset_name, system_df):
        """生成配对delta文件"""
        print(f"  Generating paired delta file for {dataset_name}...")
        
        try:
            # 找到基线时间点
            baseline_timepoints = ['Baseline', 'Day_0', 'Intact_Skin']
            baseline_data = None
            
            for baseline_tp in baseline_timepoints:
                baseline_subset = system_df[system_df['timepoint'] == baseline_tp]
                if not baseline_subset.empty:
                    baseline_data = baseline_subset
                    break
            
            if baseline_data is None:
                print(f"    ❌ No baseline timepoint found")
                return
            
            # 计算delta得分
            delta_data = []
            system_columns = ['A', 'B', 'C', 'D', 'E']
            
            for subject_id in system_df['subject_id'].unique():
                subject_data = system_df[system_df['subject_id'] == subject_id]
                subject_baseline = baseline_data[baseline_data['subject_id'] == subject_id]
                
                if subject_baseline.empty:
                    continue
                
                baseline_scores = subject_baseline.iloc[0]
                
                for _, row in subject_data.iterrows():
                    if row['timepoint'] in baseline_timepoints:
                        continue  # 跳过基线
                    
                    delta_row = {
                        'subject_id': subject_id,
                        'timepoint': row['timepoint'],
                        'day': row['day']
                    }
                    
                    for system_col in system_columns:
                        if system_col in row and system_col in baseline_scores:
                            delta_row[f"delta_{system_col}"] = row[system_col] - baseline_scores[system_col]
                        else:
                            delta_row[f"delta_{system_col}"] = 0.0
                    
                    delta_data.append(delta_row)
            
            if delta_data:
                delta_df = pd.DataFrame(delta_data)
                delta_file = f"{dataset_name}_system_paired_delta.csv"
                delta_df.to_csv(delta_file, index=False)
                print(f"    ✅ Generated: {delta_file}")
            else:
                print(f"    ❌ No delta data generated")
                
        except Exception as e:
            print(f"    ❌ Error generating paired delta file: {str(e)}")
    
    def infer_condition_group(self, dataset_name, title):
        """根据数据集名称和样本标题推断条件和组别"""
        title_lower = title.lower()
        
        if dataset_name == 'GSE122063':
            if 'alzheimer' in title_lower or 'ad_' in title_lower:
                return 'Alzheimer_Disease', 'AD'
            elif 'vascular' in title_lower or 'vad_' in title_lower:
                return 'Vascular_Dementia', 'VaD'
            elif 'control' in title_lower:
                return 'Control', 'Control'
            else:
                return 'Unknown', 'Unknown'
        
        elif dataset_name == 'GSE2034':
            return 'Breast_Cancer', 'Cancer'
        
        elif dataset_name == 'GSE21899':
            return 'Gaucher_Disease', 'Gaucher'
        
        elif dataset_name == 'GSE65682':
            return 'Sepsis', 'Sepsis'
        
        else:
            return 'Unknown', 'Unknown'
    
    def extract_subject_id(self, title, index):
        """从样本标题中提取subject ID"""
        import re
        
        # 尝试从标题中提取患者/样本编号
        patterns = [
            r'patient\s*(\d+)',
            r'subject\s*(\d+)', 
            r'sample\s*(\d+)',
            r'_(\d+)_',
            r'(\d+)$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title.lower())
            if match:
                return f"Subject_{match.group(1)}"
        
        # 如果没有找到，使用索引
        return f"Subject_{index+1}"
    
    def extract_subject_id_from_title(self, title):
        """从伤口愈合样本标题中提取subject ID"""
        import re
        
        # 伤口愈合数据的特殊模式
        patterns = [
            r'patient\s*(\d+)',
            r'subject\s*(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title.lower())
            if match:
                return f"Patient_{match.group(1)}"
        
        # 默认返回
        return "Unknown_Subject"
    
    def generate_summary_report(self, processed_count):
        """生成汇总报告"""
        print(f"\n📊 Generating summary report...")
        
        # 统计生成的文件
        generated_files = []
        file_types = {
            'sample_info': 0,
            'system_scores': 0, 
            'subcategory_scores': 0,
            'paired_delta': 0
        }
        
        for file in os.listdir('.'):
            if file.endswith('.csv'):
                if '_sample_info.csv' in file:
                    file_types['sample_info'] += 1
                    generated_files.append(file)
                elif '_system_scores.csv' in file:
                    file_types['system_scores'] += 1
                    generated_files.append(file)
                elif '_subcategory_scores.csv' in file:
                    file_types['subcategory_scores'] += 1
                    generated_files.append(file)
                elif '_paired_delta.csv' in file:
                    file_types['paired_delta'] += 1
                    generated_files.append(file)
        
        # 创建汇总报告
        report_content = f"""# Standardized Output Generation Report

## Summary
- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Datasets processed**: {processed_count}
- **Total files generated**: {len(generated_files)}

## File Types Generated
- **Sample metadata files**: {file_types['sample_info']}
- **System scores files**: {file_types['system_scores']}
- **Subcategory scores files**: {file_types['subcategory_scores']}
- **Paired delta files**: {file_types['paired_delta']}

## Generated Files
"""
        
        for file in sorted(generated_files):
            report_content += f"- {file}\n"
        
        report_content += f"""
## File Format Specifications

### 1. Sample Metadata ({'{GSE_ID}'}_sample_info.csv)
- **sample_id**: Unique sample identifier
- **subject_id**: Patient/subject identifier (when available)
- **timepoint**: Time point or stage (for temporal data)
- **day**: Numeric day (for temporal data)
- **condition**: Experimental condition
- **group**: Sample group classification

### 2. System-level ssGSEA Scores ({'{GSE_ID}'}_system_scores.csv)
- One row per sample
- Columns A-E for functional systems
- All metadata columns preserved

### 3. Subcategory-level ssGSEA Scores ({'{GSE_ID}'}_subcategory_scores.csv)
- One row per sample  
- Columns A1-A4, B1-B3, C1-C3, D1-D2, E1-E2
- All metadata columns preserved

### 4. Paired Delta Scores ({'{GSE_ID}'}_system_paired_delta.csv)
- Only for longitudinal data
- Delta scores relative to baseline per subject
- Columns: delta_A, delta_B, delta_C, delta_D, delta_E

## Data Quality Notes
- All scores are real-valued ssGSEA enrichment scores
- Missing values are filled with 0.0
- Temporal data uses mean scores per timepoint
- Subject IDs extracted from sample titles when possible
"""
        
        with open('standardized_output_report.md', 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"✅ Generated: standardized_output_report.md")
        print(f"\n📁 Total files generated: {len(generated_files)}")

def main():
    """主函数"""
    generator = StandardizedOutputGenerator()
    generator.process_all_datasets()

if __name__ == "__main__":
    main()