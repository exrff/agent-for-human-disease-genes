#!/usr/bin/env python3
"""
深度分析戈谢病与五大系统分类的潜在契合规律
基于增强的标签和生物学背景挖掘隐藏模式
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')

def analyze_gaucher_system_correlations():
    """分析戈谢病与系统分类的深层关联"""
    print("="*80)
    print("GAUCHER DISEASE - FIVE SYSTEM CLASSIFICATION ANALYSIS")
    print("="*80)
    
    # 1. 加载数据
    print(f"\n📊 Loading Gaucher disease data...")
    
    system_scores = pd.read_csv('results/disease_analysis/GSE21899-戈谢病/clean_data/GSE21899_system_scores.csv')
    subcategory_scores = pd.read_csv('results/disease_analysis/GSE21899-戈谢病/clean_data/GSE21899_subcategory_scores.csv')
    enhanced_info = pd.read_csv('results/disease_analysis/GSE21899-戈谢病/analysis_results/GSE21899_enhanced_sample_info.csv')
    clinical_metadata = pd.read_csv('results/disease_analysis/GSE21899-戈谢病/analysis_results/GSE21899_clinical_metadata.csv')
    
    # 合并所有信息
    merged_data = system_scores.merge(enhanced_info, on='sample_id')
    merged_data = merged_data.merge(clinical_metadata, on='sample_id')
    
    print(f"   • Total samples: {len(merged_data)}")
    print(f"   • All samples are Gaucher disease patients")
    
    # 2. 基础系统激活分析
    print(f"\n🔬 Basic system activation analysis...")
    basic_analysis = analyze_basic_system_activation(merged_data)
    
    # 3. 年龄相关分析
    print(f"\n👴 Age-related system changes...")
    age_analysis = analyze_age_related_changes(merged_data)
    
    # 4. 性别差异分析
    print(f"\n⚥ Gender-specific patterns...")
    gender_analysis = analyze_gender_differences(merged_data)
    
    # 5. 子分类详细分析
    print(f"\n🧬 Subcategory detailed analysis...")
    subcategory_analysis = analyze_subcategory_patterns(merged_data, subcategory_scores)
    
    return {
        'basic_analysis': basic_analysis,
        'age_analysis': age_analysis,
        'gender_analysis': gender_analysis,
        'subcategory_analysis': subcategory_analysis
    }

def analyze_basic_system_activation(data):
    """基础系统激活分析 - 专注于戈谢病内部模式"""
    
    system_cols = ['A', 'B', 'C', 'D', 'E']
    
    print(f"   System activation levels in Gaucher disease:")
    
    results = {}
    
    for system in system_cols:
        scores = data[system]
        
        results[system] = {
            'mean': scores.mean(),
            'std': scores.std(),
            'min': scores.min(),
            'max': scores.max(),
            'cv': scores.std() / scores.mean()  # 变异系数
        }
        
        print(f"     • System {system}: {scores.mean():.4f} ± {scores.std():.4f}")
        print(f"       Range: [{scores.min():.4f}, {scores.max():.4f}], CV: {results[system]['cv']:.3f}")
    
    # 找出最高激活的系统
    max_system = max(results.keys(), key=lambda x: results[x]['mean'])
    print(f"\n   🎯 Highest activated system: {max_system} ({results[max_system]['mean']:.4f})")
    
    # 系统间相关性分析
    print(f"\n   System correlations:")
    for i, sys1 in enumerate(system_cols):
        for sys2 in system_cols[i+1:]:
            correlation, p_value = stats.pearsonr(data[sys1], data[sys2])
            if abs(correlation) > 0.5:  # 中等以上相关性
                direction = "+" if correlation > 0 else "-"
                significance = "***" if p_value < 0.001 else ("**" if p_value < 0.01 else ("*" if p_value < 0.05 else "ns"))
                print(f"     • {sys1}-{sys2}: r={correlation:+.3f} {direction} (p={p_value:.3f}) {significance}")
    
    return results

def analyze_age_related_changes(data):
    """分析年龄相关的系统变化"""
    
    # 提取年龄信息
    data['age_numeric'] = data['age_time'].str.extract(r'(\d+)').astype(float)
    
    system_cols = ['A', 'B', 'C', 'D', 'E']
    
    print(f"   Age range: {data['age_numeric'].min():.0f}-{data['age_numeric'].max():.0f} years")
    
    age_correlations = {}
    
    for system in system_cols:
        correlation, p_value = stats.pearsonr(data['age_numeric'], data[system])
        
        age_correlations[system] = {
            'correlation': correlation,
            'p_value': p_value,
            'r_squared': correlation**2
        }
        
        if abs(correlation) > 0.3:  # 中等相关性
            direction = "↑" if correlation > 0 else "↓"
            significance = "***" if p_value < 0.001 else ("**" if p_value < 0.01 else ("*" if p_value < 0.05 else "ns"))
            print(f"     • System {system}: r={correlation:.3f} {direction} (p={p_value:.3f}) {significance}")
    
    return age_correlations

def analyze_gender_differences(data):
    """分析性别差异"""
    
    # 提取性别信息
    data['gender_clean'] = data['gender'].str.extract(r'gender: (\w+)')
    
    system_cols = ['A', 'B', 'C', 'D', 'E']
    
    gender_counts = data['gender_clean'].value_counts()
    print(f"   Gender distribution: {dict(gender_counts)}")
    
    if len(gender_counts) >= 2:
        gender_results = {}
        
        for system in system_cols:
            male_scores = data[data['gender_clean'] == 'male'][system]
            female_scores = data[data['gender_clean'] == 'female'][system]
            
            if len(male_scores) > 0 and len(female_scores) > 0:
                t_stat, p_value = stats.ttest_ind(male_scores, female_scores)
                
                pooled_std = np.sqrt(((len(male_scores) - 1) * male_scores.var() + 
                                     (len(female_scores) - 1) * female_scores.var()) / 
                                    (len(male_scores) + len(female_scores) - 2))
                cohens_d = (male_scores.mean() - female_scores.mean()) / pooled_std
                
                gender_results[system] = {
                    'male_mean': male_scores.mean(),
                    'female_mean': female_scores.mean(),
                    'difference': male_scores.mean() - female_scores.mean(),
                    'cohens_d': cohens_d,
                    'p_value': p_value
                }
                
                if abs(cohens_d) > 0.5:  # 中等效应量
                    direction = "M>F" if cohens_d > 0 else "F>M"
                    significance = "***" if p_value < 0.001 else ("**" if p_value < 0.01 else ("*" if p_value < 0.05 else "ns"))
                    print(f"     • System {system}: {direction}, d={cohens_d:.3f}, p={p_value:.3f} {significance}")
        
        return gender_results
    
    return None

def analyze_subcategory_patterns(data, subcategory_scores):
    """分析子分类模式"""
    
    subcategory_cols = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'E1', 'E2']
    
    print(f"   Subcategory activation levels:")
    
    subcategory_results = {}
    
    for subcat in subcategory_cols:
        scores = subcategory_scores[subcat]
        
        subcategory_results[subcat] = {
            'mean': scores.mean(),
            'std': scores.std(),
            'cv': scores.std() / scores.mean()
        }
    
    # 按平均激活水平排序，显示前5个
    sorted_subcats = sorted(subcategory_results.items(), 
                           key=lambda x: x[1]['mean'], reverse=True)
    
    print(f"   Top 5 activated subcategories:")
    for i, (subcat, results) in enumerate(sorted_subcats[:5]):
        print(f"     {i+1}. {subcat}: {results['mean']:.4f} ± {results['std']:.4f} (CV: {results['cv']:.3f})")
    
    # 分析C系统的子分类（预期最高）
    c_subcats = ['C1', 'C2', 'C3']
    print(f"\n   System C (Metabolism) subcategories:")
    for subcat in c_subcats:
        if subcat in subcategory_results:
            result = subcategory_results[subcat]
            print(f"     • {subcat}: {result['mean']:.4f} ± {result['std']:.4f}")
    
    return subcategory_results

def main():
    """主函数"""
    try:
        results = analyze_gaucher_system_correlations()
        
        print(f"\n{'='*80}")
        print("GAUCHER DISEASE ANALYSIS COMPLETED")
        print(f"{'='*80}")
        
        print(f"\n🎯 Key Findings Summary:")
        
        # 总结主要发现
        if 'basic_analysis' in results:
            basic = results['basic_analysis']
            max_system = max(basic.keys(), key=lambda x: basic[x]['mean'])
            print(f"   • Highest activated system: {max_system} ({basic[max_system]['mean']:.4f})")
            
            # 验证是否符合预期（System C应该最高）
            if max_system == 'C':
                print(f"   ✅ Validates hypothesis: System C (Metabolism) is highest activated")
            else:
                print(f"   ⚠️  Unexpected: System {max_system} is highest, not System C")
        
        if 'age_analysis' in results and results['age_analysis']:
            age = results['age_analysis']
            strong_correlations = [sys for sys, res in age.items() if abs(res['correlation']) > 0.3]
            if strong_correlations:
                print(f"   • Age-correlated systems: {strong_correlations}")
        
        if 'gender_analysis' in results and results['gender_analysis']:
            gender = results['gender_analysis']
            gender_differences = [sys for sys, res in gender.items() if abs(res['cohens_d']) > 0.5]
            if gender_differences:
                print(f"   • Gender-different systems: {gender_differences}")
        
        print(f"\n💡 Biological Insights:")
        print(f"   • System C (Metabolism) expected to be highest - validates lysosomal storage disorder")
        print(f"   • Age correlations may reflect disease progression or treatment effects")
        print(f"   • Gender differences could inform personalized treatment approaches")
        print(f"   • Subcategory patterns reveal specific pathway disruptions")
        
    except Exception as e:
        print(f"❌ Error in analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()