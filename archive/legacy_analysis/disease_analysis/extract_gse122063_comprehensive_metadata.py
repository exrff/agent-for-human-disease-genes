#!/usr/bin/env python3
"""
提取GSE122063阿尔兹海默症数据集的全面元数据信息
包括临床信息、样本特征、完整的子分类数据等
"""

import pandas as pd
import numpy as np
import gzip
import re
import warnings
warnings.filterwarnings('ignore')

def extract_comprehensive_gse122063_metadata():
    """提取GSE122063的全面元数据"""
    
    print("="*80)
    print("EXTRACTING COMPREHENSIVE GSE122063 ALZHEIMER'S METADATA")
    print("="*80)
    
    # 1. 从GEO数据中提取详细元数据
    print(f"\n📊 Extracting detailed metadata from GEO data...")
    sample_metadata = extract_geo_metadata()
    
    # 2. 增强临床标签
    print(f"\n🏥 Enhancing clinical labels...")
    enhanced_metadata = enhance_clinical_labels(sample_metadata)
    
    # 3. 分析子分类数据
    print(f"\n📈 Analyzing subcategory patterns...")
    subcategory_ranking = analyze_subcategory_patterns()
    
    # 4. 生成详细统计
    print(f"\n📊 Generating detailed statistics...")
    detailed_statistics = generate_detailed_statistics()
    
    # 5. 样本级别详细信息
    print(f"\n🔍 Creating sample-level details...")
    sample_details = create_sample_level_details(enhanced_metadata)
    
    # 6. 保存全面的元数据
    print(f"\n💾 Saving comprehensive metadata...")
    save_comprehensive_metadata(enhanced_metadata, subcategory_ranking, detailed_statistics, sample_details)
    
    return {
        'sample_metadata': enhanced_metadata,
        'subcategory_ranking': subcategory_ranking,
        'detailed_statistics': detailed_statistics,
        'sample_details': sample_details
    }

def extract_geo_metadata():
    """从GEO数据文件中提取元数据"""
    
    print(f"   • Reading GSE122063 series matrix...")
    
    # 读取压缩的series matrix文件
    with gzip.open('data/validation_datasets/GSE122063-阿尔兹海默症/GSE122063_series_matrix.txt.gz', 'rt') as f:
        lines = f.readlines()
    
    # 提取样本信息
    sample_info = {}
    
    # 查找样本相关的元数据行
    for line in lines:
        if line.startswith('!Sample_geo_accession'):
            sample_ids = line.strip().split('\t')[1:]
            sample_ids = [s.strip('"') for s in sample_ids]
        elif line.startswith('!Sample_title'):
            sample_titles = line.strip().split('\t')[1:]
            sample_titles = [s.strip('"') for s in sample_titles]
        elif line.startswith('!Sample_source_name'):
            sample_sources = line.strip().split('\t')[1:]
            sample_sources = [s.strip('"') for s in sample_sources]
        elif line.startswith('!Sample_characteristics'):
            # 这里包含了详细的临床信息
            characteristics = line.strip().split('\t')[1:]
            characteristics = [s.strip('"') for s in characteristics]
            
            # 解析特征信息
            if 'diagnosis:' in line:
                diagnoses = [extract_characteristic_value(c, 'diagnosis') for c in characteristics]
            elif 'age:' in line:
                ages = [extract_characteristic_value(c, 'age') for c in characteristics]
            elif 'Sex:' in line or 'gender:' in line:
                genders = [extract_characteristic_value(c, ['Sex', 'gender']) for c in characteristics]
            elif 'braak:' in line:
                braak_stages = [extract_characteristic_value(c, 'braak') for c in characteristics]
            elif 'cerad:' in line:
                cerad_scores = [extract_characteristic_value(c, 'cerad') for c in characteristics]
            elif 'apoe:' in line:
                apoe_genotypes = [extract_characteristic_value(c, 'apoe') for c in characteristics]
            elif 'pmi:' in line:
                pmi_hours = [extract_characteristic_value(c, 'pmi') for c in characteristics]
            elif 'brain region:' in line:
                brain_regions = [extract_characteristic_value(c, 'brain region') for c in characteristics]
    
    # 构建样本元数据DataFrame
    metadata_dict = {
        'sample_id': sample_ids,
        'sample_title': sample_titles,
        'source_name': sample_sources
    }
    
    # 添加提取的特征（如果存在）
    if 'diagnoses' in locals():
        metadata_dict['diagnosis'] = diagnoses
    if 'ages' in locals():
        metadata_dict['age'] = ages
    if 'genders' in locals():
        metadata_dict['gender'] = genders
    if 'braak_stages' in locals():
        metadata_dict['braak_stage'] = braak_stages
    if 'cerad_scores' in locals():
        metadata_dict['cerad_score'] = cerad_scores
    if 'apoe_genotypes' in locals():
        metadata_dict['apoe_genotype'] = apoe_genotypes
    if 'pmi_hours' in locals():
        metadata_dict['pmi_hours'] = pmi_hours
    if 'brain_regions' in locals():
        metadata_dict['brain_region'] = brain_regions
    
    sample_metadata = pd.DataFrame(metadata_dict)
    
    print(f"   • Extracted metadata for {len(sample_metadata)} samples")
    print(f"   • Available fields: {list(sample_metadata.columns)}")
    
    return sample_metadata

def extract_characteristic_value(characteristic_string, key_names):
    """从特征字符串中提取值"""
    
    if isinstance(key_names, str):
        key_names = [key_names]
    
    for key_name in key_names:
        if f'{key_name}:' in characteristic_string.lower():
            try:
                value = characteristic_string.split(':')[1].strip()
                return value
            except:
                return 'Unknown'
    
    return 'Unknown'

def enhance_clinical_labels(sample_metadata):
    """增强临床标签"""
    
    # 读取现有的样本信息
    sample_info = pd.read_csv('results/disease_analysis/GSE122063-阿尔兹海默症/clean_data/GSE122063_sample_info.csv')
    
    # 合并数据
    enhanced_metadata = sample_info.merge(sample_metadata, on='sample_id', how='left')
    
    # 添加增强的生物学标签
    enhanced_labels = []
    
    for _, row in enhanced_metadata.iterrows():
        condition = row['condition']
        
        # 基于阿尔兹海默症的生物学特征添加标签
        if condition == 'Alzheimer_Disease':
            # 阿尔兹海默症相关的生物学过程
            cell_type = 'Mixed_Brain_Tissue'  # 脑组织混合细胞
            disease_state = 'Neurodegeneration'
            expected_primary_system = 'D_Neural_Regulation'  # 预期神经系统主导
            biological_relevance = 'Neuronal_Death_and_Inflammation'
            expected_pathways = 'Amyloid_Processing,Tau_Pathology,Neuroinflammation,Synaptic_Dysfunction'
            tissue_type = 'Brain_Cortex'
            pathology_stage = row.get('braak_stage', 'Unknown')
            cognitive_status = 'Dementia'
        else:
            # 对照组
            cell_type = 'Mixed_Brain_Tissue'
            disease_state = 'Healthy_Control'
            expected_primary_system = 'D_Neural_Regulation'
            biological_relevance = 'Normal_Brain_Function'
            expected_pathways = 'Normal_Synaptic_Function,Neuronal_Maintenance'
            tissue_type = 'Brain_Cortex'
            pathology_stage = 'None'
            cognitive_status = 'Normal'
        
        enhanced_labels.append({
            'sample_id': row['sample_id'],
            'cell_type': cell_type,
            'disease_state': disease_state,
            'expected_primary_system': expected_primary_system,
            'biological_relevance': biological_relevance,
            'expected_pathways': expected_pathways,
            'tissue_type': tissue_type,
            'pathology_stage': pathology_stage,
            'cognitive_status': cognitive_status,
            'age': row.get('age', 'Unknown'),
            'gender': row.get('gender', 'Unknown'),
            'braak_stage': row.get('braak_stage', 'Unknown'),
            'cerad_score': row.get('cerad_score', 'Unknown'),
            'apoe_genotype': row.get('apoe_genotype', 'Unknown'),
            'brain_region': row.get('brain_region', 'Frontal_Cortex'),
            'pmi_hours': row.get('pmi_hours', 'Unknown')
        })
    
    enhanced_df = pd.DataFrame(enhanced_labels)
    final_metadata = enhanced_metadata.merge(enhanced_df, on='sample_id', how='left')
    
    print(f"   • Enhanced metadata for {len(final_metadata)} samples")
    print(f"   • Added biological labels: cell_type, disease_state, pathology_stage, etc.")
    
    return final_metadata

def analyze_subcategory_patterns():
    """分析子分类模式"""
    
    # 读取子分类数据
    subcategory_data = pd.read_csv('results/disease_analysis/GSE122063-阿尔兹海默症/clean_data/GSE122063_subcategory_scores.csv')
    
    subcategory_cols = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'E1', 'E2']
    
    # 计算每个子分类的统计信息
    subcategory_stats = []
    
    for subcat in subcategory_cols:
        if subcat in subcategory_data.columns:
            # 按组分析
            ad_scores = subcategory_data[subcategory_data['group'] == 'AD'][subcat]
            control_scores = subcategory_data[subcategory_data['group'] == 'Control'][subcat]
            
            subcategory_stats.append({
                'subcategory': subcat,
                'system': subcat[0],
                'ad_mean': ad_scores.mean(),
                'ad_std': ad_scores.std(),
                'control_mean': control_scores.mean(),
                'control_std': control_scores.std(),
                'difference': ad_scores.mean() - control_scores.mean(),
                'fold_change': ad_scores.mean() / control_scores.mean() if control_scores.mean() > 0 else np.inf,
                'ad_samples': len(ad_scores),
                'control_samples': len(control_scores)
            })
    
    subcategory_ranking = pd.DataFrame(subcategory_stats)
    subcategory_ranking = subcategory_ranking.sort_values('ad_mean', ascending=False)
    
    print(f"   • Analyzed {len(subcategory_ranking)} subcategories")
    print(f"   • Top 3 subcategories in AD: {subcategory_ranking.head(3)['subcategory'].tolist()}")
    
    return subcategory_ranking

def generate_detailed_statistics():
    """生成详细统计"""
    
    # 读取所有数据
    system_data = pd.read_csv('results/disease_analysis/GSE122063-阿尔兹海默症/clean_data/GSE122063_system_scores.csv')
    subcategory_data = pd.read_csv('results/disease_analysis/GSE122063-阿尔兹海默症/clean_data/GSE122063_subcategory_scores.csv')
    
    system_cols = ['A', 'B', 'C', 'D', 'E']
    subcategory_cols = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'E1', 'E2']
    
    # 系统级统计
    system_stats = []
    for system in system_cols:
        if system in system_data.columns:
            ad_scores = system_data[system_data['group'] == 'AD'][system]
            control_scores = system_data[system_data['group'] == 'Control'][system]
            
            system_stats.append({
                'system': system,
                'ad_mean': ad_scores.mean(),
                'ad_std': ad_scores.std(),
                'ad_median': ad_scores.median(),
                'control_mean': control_scores.mean(),
                'control_std': control_scores.std(),
                'control_median': control_scores.median(),
                'difference': ad_scores.mean() - control_scores.mean(),
                'fold_change': ad_scores.mean() / control_scores.mean() if control_scores.mean() > 0 else np.inf,
                'ad_samples': len(ad_scores),
                'control_samples': len(control_scores)
            })
    
    system_statistics = pd.DataFrame(system_stats)
    
    # 相关性矩阵
    correlation_matrix = system_data[system_cols].corr()
    
    # 样本间变异性
    ad_data = system_data[system_data['group'] == 'AD'][system_cols]
    control_data = system_data[system_data['group'] == 'Control'][system_cols]
    
    ad_cv = ad_data.std() / ad_data.mean()  # 变异系数
    control_cv = control_data.std() / control_data.mean()
    
    variability_stats = pd.DataFrame({
        'system': system_cols,
        'ad_cv': ad_cv,
        'control_cv': control_cv,
        'cv_difference': ad_cv - control_cv
    })
    
    print(f"   • Generated system statistics for {len(system_statistics)} systems")
    print(f"   • Calculated correlation matrix and variability measures")
    
    return {
        'system_statistics': system_statistics,
        'correlation_matrix': correlation_matrix,
        'variability_stats': variability_stats
    }

def create_sample_level_details(enhanced_metadata):
    """创建样本级别的详细信息"""
    
    # 读取系统和子分类数据
    system_data = pd.read_csv('results/disease_analysis/GSE122063-阿尔兹海默症/clean_data/GSE122063_system_scores.csv')
    subcategory_data = pd.read_csv('results/disease_analysis/GSE122063-阿尔兹海默症/clean_data/GSE122063_subcategory_scores.csv')
    
    # 合并所有数据
    sample_details = enhanced_metadata.merge(system_data, on='sample_id', how='left')
    sample_details = sample_details.merge(subcategory_data, on='sample_id', how='left')
    
    # 添加样本特异性分析
    system_cols = ['A', 'B', 'C', 'D', 'E']
    
    # 为每个样本计算主导系统
    sample_details['dominant_system'] = sample_details[system_cols].idxmax(axis=1)
    sample_details['dominant_system_score'] = sample_details[system_cols].max(axis=1)
    
    # 计算系统激活模式
    sample_details['system_activation_pattern'] = sample_details.apply(
        lambda row: '_'.join([f"{sys}:{row[sys]:.3f}" for sys in system_cols]), axis=1
    )
    
    # 计算与组平均的偏差
    for group in ['AD', 'Control']:
        group_data = sample_details[sample_details['group'] == group]
        group_means = group_data[system_cols].mean()
        
        for sys in system_cols:
            sample_details.loc[sample_details['group'] == group, f'{sys}_deviation_from_group'] = \
                sample_details.loc[sample_details['group'] == group, sys] - group_means[sys]
    
    print(f"   • Created detailed information for {len(sample_details)} samples")
    print(f"   • Added dominant system analysis and deviation calculations")
    
    return sample_details

def save_comprehensive_metadata(sample_metadata, subcategory_ranking, detailed_statistics, sample_details):
    """保存全面的元数据"""
    
    output_dir = 'results/disease_analysis/GSE122063-阿尔兹海默症/analysis_results/'
    
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存样本元数据
    sample_metadata.to_csv(f'{output_dir}GSE122063_comprehensive_sample_metadata.csv', index=False)
    
    # 保存完整子分类排名
    subcategory_ranking.to_csv(f'{output_dir}GSE122063_complete_subcategory_ranking.csv', index=False)
    
    # 保存系统统计
    detailed_statistics['system_statistics'].to_csv(f'{output_dir}GSE122063_detailed_system_statistics.csv', index=False)
    
    # 保存相关性矩阵
    detailed_statistics['correlation_matrix'].to_csv(f'{output_dir}GSE122063_system_correlation_matrix.csv')
    
    # 保存变异性统计
    detailed_statistics['variability_stats'].to_csv(f'{output_dir}GSE122063_variability_statistics.csv', index=False)
    
    # 保存样本详细信息
    sample_details.to_csv(f'{output_dir}GSE122063_sample_level_details.csv', index=False)
    
    print(f"   ✅ All comprehensive metadata saved to {output_dir}")

def main():
    """主函数"""
    try:
        results = extract_comprehensive_gse122063_metadata()
        
        print(f"\n{'='*80}")
        print("GSE122063 COMPREHENSIVE METADATA EXTRACTION COMPLETED")
        print(f"{'='*80}")
        
        # 显示关键结果
        sample_metadata = results['sample_metadata']
        subcategory_ranking = results['subcategory_ranking']
        system_stats = results['detailed_statistics']['system_statistics']
        
        print(f"\n🎯 Key Results:")
        print(f"   • Total samples: {len(sample_metadata)}")
        
        # 显示组分布
        if 'group' in sample_metadata.columns:
            group_counts = sample_metadata['group'].value_counts()
            print(f"   • Group distribution: {dict(group_counts)}")
        
        # 显示顶级子分类
        print(f"   • Top 3 subcategories in AD:")
        for i, row in subcategory_ranking.head(3).iterrows():
            print(f"     {i+1}. {row['subcategory']}: {row['ad_mean']:.4f}")
        
        # 显示系统排名
        system_ranking = system_stats.sort_values('ad_mean', ascending=False)
        print(f"   • System ranking in AD:")
        for i, row in system_ranking.iterrows():
            print(f"     {row['system']}: {row['ad_mean']:.4f}")
        
        print(f"\n📝 Analysis Summary:")
        print(f"   阿尔兹海默症数据集包含{len(sample_metadata)}个样本，")
        print(f"   主导系统为{system_ranking.iloc[0]['system']}系统，")
        print(f"   顶级子分类为{subcategory_ranking.iloc[0]['subcategory']}。")
        
    except Exception as e:
        print(f"❌ Error in metadata extraction: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()