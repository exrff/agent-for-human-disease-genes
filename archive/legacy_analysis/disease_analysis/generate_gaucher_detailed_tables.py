#!/usr/bin/env python3
"""
生成戈谢病详细分析表格
包括系统激活、年龄相关性、性别差异等
"""

import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

def generate_gaucher_detailed_tables():
    """生成戈谢病详细分析表格"""
    
    print("="*80)
    print("GENERATING DETAILED GAUCHER DISEASE ANALYSIS TABLES")
    print("="*80)
    
    # 加载数据
    system_scores = pd.read_csv('results/disease_analysis/GSE21899-戈谢病/clean_data/GSE21899_system_scores.csv')
    subcategory_scores = pd.read_csv('results/disease_analysis/GSE21899-戈谢病/clean_data/GSE21899_subcategory_scores.csv')
    enhanced_info = pd.read_csv('results/disease_analysis/GSE21899-戈谢病/analysis_results/GSE21899_enhanced_sample_info.csv')
    clinical_metadata = pd.read_csv('results/disease_analysis/GSE21899-戈谢病/analysis_results/GSE21899_clinical_metadata.csv')
    
    # 合并数据
    merged_data = system_scores.merge(enhanced_info, on='sample_id')
    merged_data = merged_data.merge(clinical_metadata, on='sample_id')
    
    # 提取年龄和性别信息
    merged_data['age_numeric'] = merged_data['age_time'].str.extract(r'(\d+)').astype(float)
    merged_data['gender_clean'] = merged_data['gender'].str.extract(r'gender: (\w+)')
    
    # 1. 系统激活水平表格
    print("\n📊 Generating system activation table...")
    system_table = generate_system_activation_table(merged_data)
    
    # 2. 年龄相关性表格
    print("📊 Generating age correlation table...")
    age_table = generate_age_correlation_table(merged_data)
    
    # 3. 性别差异表格
    print("📊 Generating gender difference table...")
    gender_table = generate_gender_difference_table(merged_data)
    
    # 4. 子分类详细表格
    print("📊 Generating subcategory table...")
    subcategory_table = generate_subcategory_table(subcategory_scores)
    
    # 5. 样本详细信息表格
    print("📊 Generating sample details table...")
    sample_table = generate_sample_details_table(merged_data)
    
    # 保存所有表格
    output_dir = 'results/disease_analysis/GSE21899-戈谢病/analysis_results/'
    
    system_table.to_csv(f'{output_dir}gaucher_system_activation_table.csv', index=False)
    age_table.to_csv(f'{output_dir}gaucher_age_correlation_table.csv', index=False)
    gender_table.to_csv(f'{output_dir}gaucher_gender_difference_table.csv', index=False)
    subcategory_table.to_csv(f'{output_dir}gaucher_subcategory_table.csv', index=False)
    sample_table.to_csv(f'{output_dir}gaucher_sample_details_table.csv', index=False)
    
    print(f"\n✅ All tables saved to {output_dir}")
    
    return {
        'system_table': system_table,
        'age_table': age_table,
        'gender_table': gender_table,
        'subcategory_table': subcategory_table,
        'sample_table': sample_table
    }

def generate_system_activation_table(data):
    """生成系统激活水平表格"""
    
    system_cols = ['A', 'B', 'C', 'D', 'E']
    system_names = {
        'A': 'System A (Growth & Development)',
        'B': 'System B (Immune & Defense)', 
        'C': 'System C (Metabolism)',
        'D': 'System D (Information Processing)',
        'E': 'System E (Structural & Transport)'
    }
    
    results = []
    
    for system in system_cols:
        scores = data[system]
        
        results.append({
            'System': system_names[system],
            'System_Code': system,
            'Mean_Activation': scores.mean(),
            'Std_Deviation': scores.std(),
            'Min_Value': scores.min(),
            'Max_Value': scores.max(),
            'Coefficient_of_Variation': scores.std() / scores.mean(),
            'Sample_Count': len(scores)
        })
    
    df = pd.DataFrame(results)
    df = df.sort_values('Mean_Activation', ascending=False)
    df['Rank'] = range(1, len(df) + 1)
    
    return df

def generate_age_correlation_table(data):
    """生成年龄相关性表格"""
    
    system_cols = ['A', 'B', 'C', 'D', 'E']
    system_names = {
        'A': 'System A (Growth & Development)',
        'B': 'System B (Immune & Defense)', 
        'C': 'System C (Metabolism)',
        'D': 'System D (Information Processing)',
        'E': 'System E (Structural & Transport)'
    }
    
    results = []
    
    for system in system_cols:
        correlation, p_value = stats.pearsonr(data['age_numeric'], data[system])
        
        # 计算置信区间
        n = len(data)
        r_z = np.arctanh(correlation)
        se = 1/np.sqrt(n-3)
        z_crit = stats.norm.ppf(0.975)  # 95% CI
        lo_z, hi_z = r_z - z_crit*se, r_z + z_crit*se
        lo_r, hi_r = np.tanh((lo_z, hi_z))
        
        results.append({
            'System': system_names[system],
            'System_Code': system,
            'Correlation_r': correlation,
            'P_Value': p_value,
            'R_Squared': correlation**2,
            'CI_Lower': lo_r,
            'CI_Upper': hi_r,
            'Significance': get_significance_level(p_value),
            'Effect_Size': get_correlation_effect_size(abs(correlation)),
            'Sample_Count': n
        })
    
    df = pd.DataFrame(results)
    df = df.sort_values('Correlation_r', key=abs, ascending=False)
    
    return df

def generate_gender_difference_table(data):
    """生成性别差异表格"""
    
    system_cols = ['A', 'B', 'C', 'D', 'E']
    system_names = {
        'A': 'System A (Growth & Development)',
        'B': 'System B (Immune & Defense)', 
        'C': 'System C (Metabolism)',
        'D': 'System D (Information Processing)',
        'E': 'System E (Structural & Transport)'
    }
    
    results = []
    
    for system in system_cols:
        male_scores = data[data['gender_clean'] == 'male'][system]
        female_scores = data[data['gender_clean'] == 'female'][system]
        
        if len(male_scores) > 0 and len(female_scores) > 0:
            # t检验
            t_stat, p_value = stats.ttest_ind(male_scores, female_scores)
            
            # Cohen's d
            pooled_std = np.sqrt(((len(male_scores) - 1) * male_scores.var() + 
                                 (len(female_scores) - 1) * female_scores.var()) / 
                                (len(male_scores) + len(female_scores) - 2))
            cohens_d = (male_scores.mean() - female_scores.mean()) / pooled_std
            
            results.append({
                'System': system_names[system],
                'System_Code': system,
                'Male_Mean': male_scores.mean(),
                'Male_Std': male_scores.std(),
                'Male_Count': len(male_scores),
                'Female_Mean': female_scores.mean(),
                'Female_Std': female_scores.std(),
                'Female_Count': len(female_scores),
                'Mean_Difference': male_scores.mean() - female_scores.mean(),
                'Cohens_D': cohens_d,
                'T_Statistic': t_stat,
                'P_Value': p_value,
                'Significance': get_significance_level(p_value),
                'Effect_Size': get_cohens_d_effect_size(abs(cohens_d))
            })
    
    df = pd.DataFrame(results)
    df = df.sort_values('Cohens_D', key=abs, ascending=False)
    
    return df

def generate_subcategory_table(subcategory_scores):
    """生成子分类表格"""
    
    subcategory_cols = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'E1', 'E2']
    
    subcategory_names = {
        'A1': 'A1 (Cell Cycle & Division)',
        'A2': 'A2 (Development & Morphogenesis)', 
        'A3': 'A3 (Growth Factors)',
        'A4': 'A4 (Stem Cell & Regeneration)',
        'B1': 'B1 (Innate Immunity)',
        'B2': 'B2 (Adaptive Immunity)',
        'B3': 'B3 (Inflammatory Response)',
        'C1': 'C1 (Energy Metabolism)',
        'C2': 'C2 (Biosynthesis)',
        'C3': 'C3 (Catabolism & Degradation)',
        'D1': 'D1 (Signal Transduction)',
        'D2': 'D2 (Gene Expression)',
        'E1': 'E1 (Structural Components)',
        'E2': 'E2 (Transport & Localization)'
    }
    
    results = []
    
    for subcat in subcategory_cols:
        scores = subcategory_scores[subcat]
        
        results.append({
            'Subcategory': subcategory_names.get(subcat, subcat),
            'Subcategory_Code': subcat,
            'Parent_System': subcat[0],
            'Mean_Activation': scores.mean(),
            'Std_Deviation': scores.std(),
            'Min_Value': scores.min(),
            'Max_Value': scores.max(),
            'Coefficient_of_Variation': scores.std() / scores.mean(),
            'Sample_Count': len(scores)
        })
    
    df = pd.DataFrame(results)
    df = df.sort_values('Mean_Activation', ascending=False)
    df['Overall_Rank'] = range(1, len(df) + 1)
    
    # 添加系统内排名
    df['Within_System_Rank'] = df.groupby('Parent_System')['Mean_Activation'].rank(ascending=False, method='dense').astype(int)
    
    return df

def generate_sample_details_table(data):
    """生成样本详细信息表格"""
    
    system_cols = ['A', 'B', 'C', 'D', 'E']
    
    sample_details = []
    
    for _, row in data.iterrows():
        sample_details.append({
            'Sample_ID': row['sample_id'],
            'Subject_ID': row.get('subject_id', 'Unknown'),  # 使用get方法避免KeyError
            'Age': row['age_numeric'],
            'Gender': row['gender_clean'],
            'Age_Group': 'Child' if row['age_numeric'] < 18 else ('Adult' if row['age_numeric'] < 65 else 'Elderly'),
            'System_A': row['A'],
            'System_B': row['B'],
            'System_C': row['C'],
            'System_D': row['D'],
            'System_E': row['E'],
            'Highest_System': max(system_cols, key=lambda x: row[x]),
            'Highest_Activation': max([row[x] for x in system_cols]),
            'System_C_Rank': sorted(system_cols, key=lambda x: row[x], reverse=True).index('C') + 1
        })
    
    df = pd.DataFrame(sample_details)
    df = df.sort_values(['Age', 'Sample_ID'])
    
    return df

def get_significance_level(p_value):
    """获取显著性水平标记"""
    if p_value < 0.001:
        return "***"
    elif p_value < 0.01:
        return "**"
    elif p_value < 0.05:
        return "*"
    else:
        return "ns"

def get_correlation_effect_size(r):
    """获取相关系数效应量大小"""
    if r < 0.1:
        return "Negligible"
    elif r < 0.3:
        return "Small"
    elif r < 0.5:
        return "Medium"
    else:
        return "Large"

def get_cohens_d_effect_size(d):
    """获取Cohen's d效应量大小"""
    if d < 0.2:
        return "Negligible"
    elif d < 0.5:
        return "Small"
    elif d < 0.8:
        return "Medium"
    else:
        return "Large"

def main():
    """主函数"""
    try:
        tables = generate_gaucher_detailed_tables()
        
        print(f"\n{'='*80}")
        print("DETAILED TABLES GENERATION COMPLETED")
        print(f"{'='*80}")
        
        # 显示关键统计信息
        print(f"\n🎯 Key Statistical Findings:")
        
        system_table = tables['system_table']
        print(f"   • Highest activated system: {system_table.iloc[0]['System_Code']} ({system_table.iloc[0]['Mean_Activation']:.4f})")
        
        age_table = tables['age_table']
        strong_age_corr = age_table[abs(age_table['Correlation_r']) > 0.3]
        if len(strong_age_corr) > 0:
            print(f"   • Systems with strong age correlations: {len(strong_age_corr)}")
        
        gender_table = tables['gender_table']
        large_gender_diff = gender_table[abs(gender_table['Cohens_D']) > 0.5]
        if len(large_gender_diff) > 0:
            print(f"   • Systems with large gender differences: {len(large_gender_diff)}")
        
        subcategory_table = tables['subcategory_table']
        top_subcat = subcategory_table.iloc[0]
        print(f"   • Highest activated subcategory: {top_subcat['Subcategory_Code']} ({top_subcat['Mean_Activation']:.4f})")
        
        sample_table = tables['sample_table']
        c_rank_1 = len(sample_table[sample_table['System_C_Rank'] == 1])
        print(f"   • Samples with System C as highest: {c_rank_1}/{len(sample_table)} ({c_rank_1/len(sample_table)*100:.1f}%)")
        
    except Exception as e:
        print(f"❌ Error generating tables: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()