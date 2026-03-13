#!/usr/bin/env python3
"""
从GSE2034原始数据中提取详细的临床信息
尝试关联聚类结果与已知的乳腺癌分子亚型
"""

import pandas as pd
import numpy as np
import gzip
import re

def extract_detailed_clinical_info():
    """从GEO数据中提取详细临床信息"""
    print("="*80)
    print("GSE2034 CLINICAL DATA EXTRACTION")
    print("="*80)
    
    # 读取原始GEO数据
    data_path = 'data/validation_datasets/GSE2034-乳腺癌/GSE2034_series_matrix.txt.gz'
    
    print(f"\n📂 Reading GEO series matrix file...")
    
    try:
        with gzip.open(data_path, 'rt', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        print(f"   • Total lines in file: {len(lines)}")
        
        # 解析元数据
        metadata = parse_geo_metadata(lines)
        
        # 显示找到的信息
        print(f"\n🔍 Metadata found:")
        for key, value in metadata.items():
            if isinstance(value, list):
                print(f"   • {key}: {len(value)} entries")
                if len(value) > 0:
                    print(f"     - Example: {value[0][:100]}...")
            else:
                print(f"   • {key}: {str(value)[:100]}...")
        
        # 尝试解析样本特征
        if 'sample_characteristics' in metadata:
            clinical_features = parse_sample_characteristics(metadata)
            
            if clinical_features:
                print(f"\n🧬 Clinical features extracted:")
                for feature, values in clinical_features.items():
                    unique_values = list(set(values))
                    print(f"   • {feature}: {len(unique_values)} unique values")
                    print(f"     - Values: {unique_values[:5]}...")
                
                # 保存临床特征
                save_clinical_features(clinical_features, metadata.get('sample_ids', []))
                
                # 与聚类结果关联
                correlate_with_clusters(clinical_features, metadata.get('sample_ids', []))
            else:
                print(f"   ⚠️ No structured clinical features found")
        
    except Exception as e:
        print(f"❌ Error reading GEO file: {str(e)}")
        import traceback
        traceback.print_exc()

def parse_geo_metadata(lines):
    """解析GEO元数据"""
    metadata = {}
    
    # 查找关键信息
    sample_ids = []
    sample_titles = []
    sample_characteristics = []
    sample_descriptions = []
    
    current_characteristic_line = None
    
    for line in lines:
        line = line.strip()
        
        if line.startswith('!Sample_geo_accession'):
            parts = line.split('\t')
            sample_ids = [p.strip('"') for p in parts[1:] if p.strip()]
            
        elif line.startswith('!Sample_title'):
            parts = line.split('\t')
            sample_titles = [p.strip('"') for p in parts[1:] if p.strip()]
            
        elif line.startswith('!Sample_description'):
            parts = line.split('\t')
            sample_descriptions = [p.strip('"') for p in parts[1:] if p.strip()]
            
        elif line.startswith('!Sample_characteristics_ch1'):
            parts = line.split('\t')
            characteristics = [p.strip('"') for p in parts[1:] if p.strip()]
            sample_characteristics.append(characteristics)
            
        elif line.startswith('!series_matrix_table_begin'):
            break
    
    metadata['sample_ids'] = sample_ids
    metadata['sample_titles'] = sample_titles
    metadata['sample_descriptions'] = sample_descriptions
    metadata['sample_characteristics'] = sample_characteristics
    
    return metadata

def parse_sample_characteristics(metadata):
    """解析样本特征信息"""
    characteristics_lines = metadata.get('sample_characteristics', [])
    sample_ids = metadata.get('sample_ids', [])
    
    if not characteristics_lines or not sample_ids:
        return None
    
    print(f"\n   Parsing {len(characteristics_lines)} characteristic lines...")
    
    # 显示原始特征信息
    for i, char_line in enumerate(characteristics_lines[:5]):  # 显示前5行
        print(f"   Line {i+1}: {len(char_line)} samples")
        if char_line:
            print(f"     Example: {char_line[0]}")
    
    # 尝试识别特征类型
    clinical_features = {}
    
    for i, char_line in enumerate(characteristics_lines):
        if len(char_line) != len(sample_ids):
            print(f"   ⚠️ Line {i+1}: Length mismatch ({len(char_line)} vs {len(sample_ids)})")
            continue
        
        # 分析第一个样本的特征来确定类型
        if char_line:
            sample_char = char_line[0].lower()
            
            # 检查是否包含乳腺癌相关关键词
            if any(keyword in sample_char for keyword in ['er', 'estrogen']):
                clinical_features['er_status'] = char_line
                print(f"   ✅ Found ER status information")
                
            elif any(keyword in sample_char for keyword in ['pr', 'progesterone']):
                clinical_features['pr_status'] = char_line
                print(f"   ✅ Found PR status information")
                
            elif any(keyword in sample_char for keyword in ['her2', 'erbb2']):
                clinical_features['her2_status'] = char_line
                print(f"   ✅ Found HER2 status information")
                
            elif any(keyword in sample_char for keyword in ['grade', 'tumor']):
                clinical_features['tumor_grade'] = char_line
                print(f"   ✅ Found tumor grade information")
                
            elif any(keyword in sample_char for keyword in ['stage']):
                clinical_features['tumor_stage'] = char_line
                print(f"   ✅ Found tumor stage information")
                
            elif any(keyword in sample_char for keyword in ['node', 'lymph']):
                clinical_features['lymph_node_status'] = char_line
                print(f"   ✅ Found lymph node status information")
                
            elif any(keyword in sample_char for keyword in ['age']):
                clinical_features['age'] = char_line
                print(f"   ✅ Found age information")
                
            elif any(keyword in sample_char for keyword in ['survival', 'outcome', 'relapse', 'recurrence']):
                clinical_features['survival_outcome'] = char_line
                print(f"   ✅ Found survival outcome information")
                
            elif any(keyword in sample_char for keyword in ['size']):
                clinical_features['tumor_size'] = char_line
                print(f"   ✅ Found tumor size information")
                
            else:
                # 通用特征
                feature_name = f"characteristic_{i+1}"
                clinical_features[feature_name] = char_line
                print(f"   • Generic feature {i+1}: {sample_char[:50]}...")
    
    return clinical_features if clinical_features else None

def save_clinical_features(clinical_features, sample_ids):
    """保存临床特征到CSV文件"""
    
    if not clinical_features or not sample_ids:
        return
    
    # 创建DataFrame
    clinical_df = pd.DataFrame({'sample_id': sample_ids})
    
    for feature_name, feature_values in clinical_features.items():
        if len(feature_values) == len(sample_ids):
            clinical_df[feature_name] = feature_values
    
    # 保存到文件
    output_path = 'results/disease_analysis/GSE2034_clinical_features.csv'
    clinical_df.to_csv(output_path, index=False)
    
    print(f"\n💾 Clinical features saved to: {output_path}")
    print(f"   • Samples: {len(clinical_df)}")
    print(f"   • Features: {len(clinical_df.columns) - 1}")

def correlate_with_clusters(clinical_features, sample_ids):
    """将临床特征与聚类结果关联"""
    
    try:
        # 读取聚类结果
        cluster_data = pd.read_csv('results/disease_analysis/GSE2034_cluster_analysis.csv')
        
        print(f"\n🔗 Correlating clinical features with clusters...")
        
        # 创建临床特征DataFrame
        clinical_df = pd.DataFrame({'sample_id': sample_ids})
        for feature_name, feature_values in clinical_features.items():
            if len(feature_values) == len(sample_ids):
                clinical_df[feature_name] = feature_values
        
        # 合并数据
        merged_data = cluster_data.merge(clinical_df, on='sample_id', how='inner')
        
        print(f"   • Merged samples: {len(merged_data)}")
        
        # 分析每个临床特征与聚类的关联
        for feature in clinical_features.keys():
            if feature in merged_data.columns:
                analyze_feature_cluster_association(merged_data, feature)
        
        # 保存合并的数据
        output_path = 'results/disease_analysis/GSE2034_clinical_clusters.csv'
        merged_data.to_csv(output_path, index=False)
        print(f"\n💾 Clinical-cluster data saved to: {output_path}")
        
    except Exception as e:
        print(f"❌ Error correlating with clusters: {str(e)}")

def analyze_feature_cluster_association(data, feature):
    """分析临床特征与聚类的关联"""
    
    print(f"\n   📊 Analyzing {feature}:")
    
    # 统计每个聚类中的特征分布
    feature_cluster_counts = data.groupby(['cluster', feature]).size().unstack(fill_value=0)
    
    if len(feature_cluster_counts) > 0:
        print(f"     Distribution by cluster:")
        for cluster_id in feature_cluster_counts.index:
            cluster_total = feature_cluster_counts.loc[cluster_id].sum()
            print(f"     Cluster {cluster_id} (n={cluster_total}):")
            
            for feature_value in feature_cluster_counts.columns:
                count = feature_cluster_counts.loc[cluster_id, feature_value]
                percentage = (count / cluster_total * 100) if cluster_total > 0 else 0
                print(f"       - {feature_value}: {count} ({percentage:.1f}%)")
        
        # 卡方检验（如果适用）
        try:
            from scipy.stats import chi2_contingency
            
            chi2, p_value, dof, expected = chi2_contingency(feature_cluster_counts)
            
            significance = "***" if p_value < 0.001 else ("**" if p_value < 0.01 else ("*" if p_value < 0.05 else "ns"))
            print(f"     Chi-square test: χ²={chi2:.3f}, p={p_value:.4f} {significance}")
            
        except Exception as e:
            print(f"     Chi-square test failed: {str(e)}")

def main():
    """主函数"""
    try:
        extract_detailed_clinical_info()
        
        print(f"\n{'='*80}")
        print("CLINICAL DATA EXTRACTION COMPLETED")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"❌ Error in clinical data extraction: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()