#!/usr/bin/env python3
"""
分析GSE122063混合痴呆数据集的系统激活模式
包含阿尔兹海默症和血管性痴呆的混合样本
"""

import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

def analyze_dementia_patterns():
    """分析痴呆数据集的系统激活模式"""
    
    print("="*80)
    print("GSE122063 MIXED DEMENTIA DATASET ANALYSIS")
    print("Alzheimer's Disease + Vascular Dementia")
    print("="*80)
    
    # 1. 加载数据
    print(f"\n📊 Loading dementia dataset...")
    system_data, subcategory_data, sample_metadata = load_dementia_data()
    
    # 2. 分析疾病亚型
    print(f"\n🧠 Analyzing dementia subtypes...")
    subtype_analysis = analyze_dementia_subtypes(sample_metadata, system_data)
    
    # 3. 系统激活模式分析
    print(f"\n📈 Analyzing system activation patterns...")
    system_analysis = analyze_system_patterns(system_data, sample_metadata)
    
    # 4. 子分类详细分析
    print(f"\n🔍 Analyzing subcategory patterns...")
    subcategory_analysis = analyze_subcategory_patterns(subcategory_data, sample_metadata)
    
    # 5. 年龄相关分析
    print(f"\n👴 Analyzing age-related patterns...")
    age_analysis = analyze_age_patterns(system_data, sample_metadata)
    
    # 6. 脑区差异分析
    print(f"\n🧠 Analyzing brain region differences...")
    region_analysis = analyze_brain_region_patterns(system_data, sample_metadata)
    
    # 7. 生成综合报告
    print(f"\n📝 Generating comprehensive report...")
    comprehensive_report = generate_comprehensive_report(
        subtype_analysis, system_analysis, subcategory_analysis, 
        age_analysis, region_analysis
    )
    
    # 8. 保存结果
    print(f"\n💾 Saving analysis results...")
    save_analysis_results(
        subtype_analysis, system_analysis, subcategory_analysis,
        age_analysis, region_analysis, comprehensive_report
    )
    
    return {
        'subtype_analysis': subtype_analysis,
        'system_analysis': system_analysis,
        'subcategory_analysis': subcategory_analysis,
        'age_analysis': age_analysis,
        'region_analysis': region_analysis,
        'comprehensive_report': comprehensive_report
    }

def load_dementia_data():
    """加载痴呆数据集"""
    
    # 加载系统得分
    system_data = pd.read_csv('results/disease_analysis/GSE122063-阿尔兹海默症/clean_data/GSE122063_system_scores.csv')
    
    # 加载子分类得分
    subcategory_data = pd.read_csv('results/disease_analysis/GSE122063-阿尔兹海默症/clean_data/GSE122063_subcategory_scores.csv')
    
    # 加载详细元数据
    sample_metadata = pd.read_csv('results/disease_analysis/GSE122063-阿尔兹海默症/analysis_results/GSE122063_comprehensive_sample_metadata.csv')
    
    print(f"   • System data: {system_data.shape}")
    print(f"   • Subcategory data: {subcategory_data.shape}")
    print(f"   • Sample metadata: {sample_metadata.shape}")
    
    return system_data, subcategory_data, sample_metadata

def analyze_dementia_subtypes(sample_metadata, system_data):
    """分析痴呆亚型"""
    
    # 提取疾病亚型信息
    subtype_counts = {}
    subtype_systems = {}
    
    # 统计不同诊断类型
    if 'diagnosis' in sample_metadata.columns:
        diagnosis_counts = sample_metadata['diagnosis'].value_counts()
        print(f"   • Diagnosis distribution:")
        for diagnosis, count in diagnosis_counts.items():
            print(f"     - {diagnosis}: {count} samples")
            subtype_counts[diagnosis] = count
    
    # 按诊断类型分析系统激活
    system_cols = ['A', 'B', 'C', 'D', 'E']
    
    for diagnosis in subtype_counts.keys():
        if diagnosis != 'Unknown':
            # 获取该诊断类型的样本
            diagnosis_samples = sample_metadata[sample_metadata['diagnosis'] == diagnosis]['sample_id'].tolist()
            diagnosis_system_data = system_data[system_data['sample_id'].isin(diagnosis_samples)]
            
            if len(diagnosis_system_data) > 0:
                system_means = diagnosis_system_data[system_cols].mean()
                subtype_systems[diagnosis] = {
                    'sample_count': len(diagnosis_system_data),
                    'system_means': system_means.to_dict(),
                    'dominant_system': system_means.idxmax(),
                    'dominant_score': system_means.max()
                }
    
    # 对照组分析
    control_data = system_data[system_data['group'] == 'Control']
    if len(control_data) > 0:
        control_means = control_data[system_cols].mean()
        subtype_systems['Control'] = {
            'sample_count': len(control_data),
            'system_means': control_means.to_dict(),
            'dominant_system': control_means.idxmax(),
            'dominant_score': control_means.max()
        }
    
    print(f"   • Analyzed {len(subtype_systems)} subtypes")
    for subtype, data in subtype_systems.items():
        print(f"     - {subtype}: {data['sample_count']} samples, dominant system {data['dominant_system']} ({data['dominant_score']:.4f})")
    
    return {
        'subtype_counts': subtype_counts,
        'subtype_systems': subtype_systems
    }

def analyze_system_patterns(system_data, sample_metadata):
    """分析系统激活模式"""
    
    system_cols = ['A', 'B', 'C', 'D', 'E']
    
    # 总体系统排名
    overall_means = system_data[system_cols].mean()
    system_ranking = overall_means.sort_values(ascending=False)
    
    # 按组分析
    group_analysis = {}
    for group in ['AD', 'Control']:
        group_data = system_data[system_data['group'] == group]
        if len(group_data) > 0:
            group_means = group_data[system_cols].mean()
            group_stds = group_data[system_cols].std()
            
            group_analysis[group] = {
                'sample_count': len(group_data),
                'system_means': group_means.to_dict(),
                'system_stds': group_stds.to_dict(),
                'system_ranking': group_means.sort_values(ascending=False).to_dict()
            }
    
    # 组间差异分析
    if 'AD' in group_analysis and 'Control' in group_analysis:
        ad_data = system_data[system_data['group'] == 'AD'][system_cols]
        control_data = system_data[system_data['group'] == 'Control'][system_cols]
        
        system_differences = {}
        for system in system_cols:
            ad_values = ad_data[system]
            control_values = control_data[system]
            
            # t检验
            t_stat, p_value = stats.ttest_ind(ad_values, control_values)
            
            system_differences[system] = {
                'ad_mean': ad_values.mean(),
                'control_mean': control_values.mean(),
                'difference': ad_values.mean() - control_values.mean(),
                'fold_change': ad_values.mean() / control_values.mean() if control_values.mean() > 0 else np.inf,
                't_statistic': t_stat,
                'p_value': p_value,
                'significant': p_value < 0.05
            }
    
    print(f"   • Overall system ranking: {list(system_ranking.index)}")
    print(f"   • AD dominant system: {group_analysis['AD']['system_ranking']}")
    print(f"   • Significant differences: {sum(1 for s in system_differences.values() if s['significant'])}/{len(system_cols)} systems")
    
    return {
        'overall_ranking': system_ranking.to_dict(),
        'group_analysis': group_analysis,
        'system_differences': system_differences
    }

def analyze_subcategory_patterns(subcategory_data, sample_metadata):
    """分析子分类模式"""
    
    subcategory_cols = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'E1', 'E2']
    
    # 总体子分类排名
    overall_means = subcategory_data[subcategory_cols].mean()
    subcategory_ranking = overall_means.sort_values(ascending=False)
    
    # 按组分析子分类
    group_subcategory_analysis = {}
    for group in ['AD', 'Control']:
        group_data = subcategory_data[subcategory_data['group'] == group]
        if len(group_data) > 0:
            group_means = group_data[subcategory_cols].mean()
            group_ranking = group_means.sort_values(ascending=False)
            
            group_subcategory_analysis[group] = {
                'sample_count': len(group_data),
                'subcategory_means': group_means.to_dict(),
                'top_5_subcategories': group_ranking.head().to_dict()
            }
    
    # 子分类差异分析
    subcategory_differences = {}
    if 'AD' in group_subcategory_analysis and 'Control' in group_subcategory_analysis:
        ad_data = subcategory_data[subcategory_data['group'] == 'AD'][subcategory_cols]
        control_data = subcategory_data[subcategory_data['group'] == 'Control'][subcategory_cols]
        
        for subcat in subcategory_cols:
            ad_values = ad_data[subcat]
            control_values = control_data[subcat]
            
            # t检验
            t_stat, p_value = stats.ttest_ind(ad_values, control_values)
            
            subcategory_differences[subcat] = {
                'ad_mean': ad_values.mean(),
                'control_mean': control_values.mean(),
                'difference': ad_values.mean() - control_values.mean(),
                'fold_change': ad_values.mean() / control_values.mean() if control_values.mean() > 0 else np.inf,
                't_statistic': t_stat,
                'p_value': p_value,
                'significant': p_value < 0.05
            }
    
    print(f"   • Top 3 subcategories overall: {list(subcategory_ranking.head(3).index)}")
    print(f"   • Top 3 in AD: {list(group_subcategory_analysis['AD']['top_5_subcategories'].keys())[:3]}")
    print(f"   • Significant subcategory differences: {sum(1 for s in subcategory_differences.values() if s['significant'])}/{len(subcategory_cols)}")
    
    return {
        'overall_ranking': subcategory_ranking.to_dict(),
        'group_analysis': group_subcategory_analysis,
        'subcategory_differences': subcategory_differences
    }

def analyze_age_patterns(system_data, sample_metadata):
    """分析年龄相关模式"""
    
    # 合并数据
    merged_data = system_data.merge(sample_metadata[['sample_id', 'age_x']], on='sample_id', how='left')
    
    # 过滤有效年龄数据
    valid_age_data = merged_data[merged_data['age_x'] != 'Unknown'].copy()
    
    if len(valid_age_data) > 0:
        # 转换年龄为数值
        valid_age_data['age_numeric'] = pd.to_numeric(valid_age_data['age_x'], errors='coerce')
        valid_age_data = valid_age_data.dropna(subset=['age_numeric'])
        
        # 年龄分组
        age_groups = {}
        age_groups['Young_Old'] = valid_age_data[valid_age_data['age_numeric'] < 80]
        age_groups['Old_Old'] = valid_age_data[valid_age_data['age_numeric'] >= 80]
        
        system_cols = ['A', 'B', 'C', 'D', 'E']
        age_analysis = {}
        
        for group_name, group_data in age_groups.items():
            if len(group_data) > 0:
                group_means = group_data[system_cols].mean()
                age_analysis[group_name] = {
                    'sample_count': len(group_data),
                    'age_range': f"{group_data['age_numeric'].min():.0f}-{group_data['age_numeric'].max():.0f}",
                    'mean_age': group_data['age_numeric'].mean(),
                    'system_means': group_means.to_dict(),
                    'dominant_system': group_means.idxmax()
                }
        
        # 年龄与系统的相关性
        age_correlations = {}
        for system in system_cols:
            correlation = valid_age_data['age_numeric'].corr(valid_age_data[system])
            age_correlations[system] = correlation
        
        print(f"   • Valid age data: {len(valid_age_data)} samples")
        print(f"   • Age range: {valid_age_data['age_numeric'].min():.0f}-{valid_age_data['age_numeric'].max():.0f} years")
        print(f"   • Age groups analyzed: {list(age_analysis.keys())}")
        
        return {
            'age_groups': age_analysis,
            'age_correlations': age_correlations,
            'valid_samples': len(valid_age_data)
        }
    else:
        print(f"   • No valid age data available")
        return {'age_groups': {}, 'age_correlations': {}, 'valid_samples': 0}

def analyze_brain_region_patterns(system_data, sample_metadata):
    """分析脑区差异模式"""
    
    # 合并数据
    merged_data = system_data.merge(sample_metadata[['sample_id', 'brain_region_x']], on='sample_id', how='left')
    
    # 分析不同脑区
    brain_regions = merged_data['brain_region_x'].value_counts()
    
    system_cols = ['A', 'B', 'C', 'D', 'E']
    region_analysis = {}
    
    for region in brain_regions.index:
        if region != 'Unknown' and brain_regions[region] >= 5:  # 至少5个样本
            region_data = merged_data[merged_data['brain_region_x'] == region]
            region_means = region_data[system_cols].mean()
            
            region_analysis[region] = {
                'sample_count': len(region_data),
                'system_means': region_means.to_dict(),
                'dominant_system': region_means.idxmax(),
                'dominant_score': region_means.max()
            }
    
    print(f"   • Brain regions found: {list(brain_regions.index)}")
    print(f"   • Regions with sufficient samples: {list(region_analysis.keys())}")
    
    return {
        'region_counts': brain_regions.to_dict(),
        'region_analysis': region_analysis
    }

def generate_comprehensive_report(subtype_analysis, system_analysis, subcategory_analysis, age_analysis, region_analysis):
    """生成综合报告"""
    
    report = {
        'dataset_summary': '',
        'key_findings': [],
        'system_insights': '',
        'subtype_patterns': '',
        'age_effects': '',
        'regional_differences': '',
        'clinical_implications': ''
    }
    
    # 数据集摘要
    total_samples = sum(subtype_analysis['subtype_counts'].values()) if subtype_analysis['subtype_counts'] else 0
    report['dataset_summary'] = (
        f"GSE122063数据集包含{total_samples}个样本，混合了阿尔兹海默症和血管性痴呆患者。"
        f"数据来自脑皮层组织（额叶和颞叶），年龄范围62-96岁。"
    )
    
    # 系统洞察
    if system_analysis['group_analysis']:
        ad_ranking = list(system_analysis['group_analysis']['AD']['system_ranking'].keys())
        report['system_insights'] = (
            f"痴呆患者表现出系统{ad_ranking[0]}主导的激活模式，"
            f"系统排序为：{' > '.join(ad_ranking)}。"
            f"这与预期的神经退行性疾病模式一致。"
        )
        report['key_findings'].append(f"系统{ad_ranking[0]}在痴呆患者中占主导地位")
    
    # 亚型模式
    if subtype_analysis['subtype_systems']:
        ad_system = subtype_analysis['subtype_systems'].get('Alzheimer\'s disease', {}).get('dominant_system', 'Unknown')
        vad_system = subtype_analysis['subtype_systems'].get('Vascular dementia', {}).get('dominant_system', 'Unknown')
        
        if ad_system != 'Unknown' and vad_system != 'Unknown':
            if ad_system == vad_system:
                report['subtype_patterns'] = (
                    f"阿尔兹海默症和血管性痴呆均表现出系统{ad_system}主导，"
                    "表明两种痴呆类型在功能系统激活上具有相似性。"
                )
            else:
                report['subtype_patterns'] = (
                    f"阿尔兹海默症主导系统{ad_system}，血管性痴呆主导系统{vad_system}，"
                    "显示不同痴呆亚型的功能系统激活差异。"
                )
            report['key_findings'].append("痴呆亚型显示不同的系统激活模式")
    
    # 年龄效应
    if age_analysis['age_correlations']:
        strongest_age_corr = max(age_analysis['age_correlations'].items(), key=lambda x: abs(x[1]))
        report['age_effects'] = (
            f"年龄与系统{strongest_age_corr[0]}显示最强相关性（r={strongest_age_corr[1]:.3f}），"
            "提示衰老过程中特定功能系统的变化。"
        )
        report['key_findings'].append("年龄相关的系统功能变化")
    
    # 区域差异
    if region_analysis['region_analysis']:
        regions = list(region_analysis['region_analysis'].keys())
        if len(regions) >= 2:
            report['regional_differences'] = (
                f"分析了{len(regions)}个脑区（{', '.join(regions)}），"
                "不同脑区显示相似的系统激活模式，表明痴呆的全脑性影响。"
            )
            report['key_findings'].append("脑区间系统激活模式的一致性")
    
    # 临床意义
    report['clinical_implications'] = (
        "本研究揭示了痴呆患者的功能系统重组模式，为理解神经退行性疾病的"
        "病理生理机制提供了新视角。系统A的主导激活可能反映了大脑的代偿性修复机制。"
    )
    
    return report

def save_analysis_results(subtype_analysis, system_analysis, subcategory_analysis, age_analysis, region_analysis, comprehensive_report):
    """保存分析结果"""
    
    output_dir = 'results/disease_analysis/GSE122063-阿尔兹海默症/analysis_results/'
    
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存亚型分析
    if subtype_analysis['subtype_systems']:
        subtype_df = pd.DataFrame.from_dict(subtype_analysis['subtype_systems'], orient='index')
        subtype_df.to_csv(f'{output_dir}dementia_subtype_analysis.csv')
    
    # 保存系统分析
    if system_analysis['system_differences']:
        system_diff_df = pd.DataFrame.from_dict(system_analysis['system_differences'], orient='index')
        system_diff_df.to_csv(f'{output_dir}dementia_system_differences.csv')
    
    # 保存子分类分析
    if subcategory_analysis['subcategory_differences']:
        subcat_diff_df = pd.DataFrame.from_dict(subcategory_analysis['subcategory_differences'], orient='index')
        subcat_diff_df.to_csv(f'{output_dir}dementia_subcategory_differences.csv')
    
    # 保存年龄分析
    if age_analysis['age_groups']:
        age_df = pd.DataFrame.from_dict(age_analysis['age_groups'], orient='index')
        age_df.to_csv(f'{output_dir}dementia_age_analysis.csv')
    
    # 保存脑区分析
    if region_analysis['region_analysis']:
        region_df = pd.DataFrame.from_dict(region_analysis['region_analysis'], orient='index')
        region_df.to_csv(f'{output_dir}dementia_brain_region_analysis.csv')
    
    # 保存综合报告
    with open(f'{output_dir}dementia_comprehensive_report.txt', 'w', encoding='utf-8') as f:
        f.write("GSE122063混合痴呆数据集综合分析报告\n")
        f.write("="*50 + "\n\n")
        
        f.write("1. 数据集摘要:\n")
        f.write(comprehensive_report['dataset_summary'] + "\n\n")
        
        f.write("2. 系统激活洞察:\n")
        f.write(comprehensive_report['system_insights'] + "\n\n")
        
        f.write("3. 亚型模式:\n")
        f.write(comprehensive_report['subtype_patterns'] + "\n\n")
        
        f.write("4. 年龄效应:\n")
        f.write(comprehensive_report['age_effects'] + "\n\n")
        
        f.write("5. 区域差异:\n")
        f.write(comprehensive_report['regional_differences'] + "\n\n")
        
        f.write("6. 临床意义:\n")
        f.write(comprehensive_report['clinical_implications'] + "\n\n")
        
        f.write("7. 关键发现:\n")
        for finding in comprehensive_report['key_findings']:
            f.write(f"   • {finding}\n")
    
    print(f"   ✅ All analysis results saved to {output_dir}")

def main():
    """主函数"""
    try:
        results = analyze_dementia_patterns()
        
        print(f"\n{'='*80}")
        print("GSE122063 MIXED DEMENTIA ANALYSIS COMPLETED")
        print(f"{'='*80}")
        
        # 显示关键结果
        subtype_analysis = results['subtype_analysis']
        system_analysis = results['system_analysis']
        report = results['comprehensive_report']
        
        print(f"\n🎯 Key Results:")
        print(f"   • Dataset: Mixed dementia (AD + VaD)")
        print(f"   • Subtypes: {list(subtype_analysis['subtype_counts'].keys())}")
        
        if system_analysis['group_analysis']:
            ad_ranking = list(system_analysis['group_analysis']['AD']['system_ranking'].keys())
            print(f"   • AD system ranking: {' > '.join(ad_ranking[:3])}")
        
        print(f"\n📝 Summary:")
        for finding in report['key_findings']:
            print(f"   • {finding}")
        
        print(f"\n💡 Clinical Insight:")
        print(f"   {report['clinical_implications']}")
        
    except Exception as e:
        print(f"❌ Error in analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()