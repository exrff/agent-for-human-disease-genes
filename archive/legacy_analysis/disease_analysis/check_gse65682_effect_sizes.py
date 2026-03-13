#!/usr/bin/env python3
"""
检查GSE65682中统计显著差异的实际效应量
评估是否适合可视化展示
"""

import pandas as pd
import numpy as np
from scipy import stats

def check_effect_sizes():
    """检查效应量"""
    print("="*80)
    print("GSE65682 EFFECT SIZE ANALYSIS")
    print("="*80)
    
    # 加载数据
    ssgsea_scores = pd.read_csv('gse65682_ssgsea_scores.csv')
    sample_groups = pd.read_csv('gse65682_sample_groups.csv')
    detailed_info = pd.read_csv('gse65682_detailed_sample_info.csv')
    
    # 合并数据
    merged_data = ssgsea_scores.merge(sample_groups, on='sample_id')
    merged_data = merged_data.merge(detailed_info, on='sample_id', suffixes=('', '_detail'))
    
    if 'group_x' in merged_data.columns:
        merged_data['group'] = merged_data['group_x']
    elif 'group_y' in merged_data.columns:
        merged_data['group'] = merged_data['group_y']
    
    subcategory_cols = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'E1', 'E2']
    
    print(f"\n📊 1. Mars Endotype Effect Sizes:")
    check_mars_effect_sizes(merged_data, subcategory_cols)
    
    print(f"\n📊 2. Mortality Effect Sizes:")
    check_mortality_effect_sizes(merged_data, subcategory_cols)
    
    print(f"\n📊 3. Age Correlation Effect Sizes:")
    check_age_effect_sizes(merged_data, subcategory_cols)
    
    print(f"\n📊 4. Sepsis vs Control Effect Sizes:")
    check_sepsis_control_effect_sizes(merged_data, subcategory_cols)

def check_mars_effect_sizes(data, subcategory_cols):
    """检查Mars内表型的效应量"""
    
    mars_data = data[data['characteristic_6'].str.contains('Mars', na=False)].copy()
    
    if len(mars_data) == 0:
        print("   No Mars data available")
        return
    
    mars_data['mars_type'] = mars_data['characteristic_6'].str.extract(r'Mars(\d+)')
    
    print(f"   Mars samples: {len(mars_data)}")
    print(f"   Mars distribution: {dict(mars_data['mars_type'].value_counts())}")
    
    # 计算eta-squared (效应量)
    print(f"\n   Effect sizes (eta-squared):")
    
    for subcat in subcategory_cols:
        groups = []
        for mars_type in ['1', '2', '3', '4']:
            mars_subset = mars_data[mars_data['mars_type'] == mars_type]
            if len(mars_subset) > 0:
                groups.append(mars_subset[subcat].values)
        
        if len(groups) >= 2:
            # 计算ANOVA
            f_stat, p_value = stats.f_oneway(*groups)
            
            # 计算eta-squared
            all_values = np.concatenate(groups)
            grand_mean = np.mean(all_values)
            
            ss_between = sum(len(group) * (np.mean(group) - grand_mean)**2 for group in groups)
            ss_total = sum((value - grand_mean)**2 for value in all_values)
            
            eta_squared = ss_between / ss_total if ss_total > 0 else 0
            
            # 计算实际差异范围
            group_means = [np.mean(group) for group in groups]
            min_mean = min(group_means)
            max_mean = max(group_means)
            range_diff = max_mean - min_mean
            
            # 效应量解释
            effect_interpretation = "Large" if eta_squared >= 0.14 else ("Medium" if eta_squared >= 0.06 else "Small")
            
            print(f"     {subcat}: η²={eta_squared:.4f} ({effect_interpretation}), Range={range_diff:.6f}, F={f_stat:.1f}, p={p_value:.2e}")

def check_mortality_effect_sizes(data, subcategory_cols):
    """检查死亡率的效应量"""
    
    mortality_data = data[data['characteristic_7'].str.contains('mortality_event_28days', na=False)].copy()
    
    if len(mortality_data) == 0:
        print("   No mortality data available")
        return
    
    mortality_data['mortality_28d'] = mortality_data['characteristic_7'].str.extract(r'mortality_event_28days: (\d+)').astype(float)
    mortality_data = mortality_data[mortality_data['mortality_28d'].isin([0.0, 1.0])]
    
    survivors = mortality_data[mortality_data['mortality_28d'] == 0.0]
    deaths = mortality_data[mortality_data['mortality_28d'] == 1.0]
    
    print(f"   Survivors: {len(survivors)}, Deaths: {len(deaths)}")
    print(f"   Mortality rate: {len(deaths)/(len(survivors)+len(deaths))*100:.1f}%")
    
    print(f"\n   Effect sizes (Cohen's d):")
    
    for subcat in subcategory_cols:
        survivor_scores = survivors[subcat]
        death_scores = deaths[subcat]
        
        if len(survivor_scores) > 0 and len(death_scores) > 0:
            # Cohen's d
            pooled_std = np.sqrt(((len(survivor_scores) - 1) * survivor_scores.var() + 
                                 (len(death_scores) - 1) * death_scores.var()) / 
                                (len(survivor_scores) + len(death_scores) - 2))
            
            cohens_d = (death_scores.mean() - survivor_scores.mean()) / pooled_std
            
            # t检验
            t_stat, p_value = stats.ttest_ind(survivor_scores, death_scores)
            
            # 实际差异
            mean_diff = death_scores.mean() - survivor_scores.mean()
            
            # 效应量解释
            effect_interpretation = "Large" if abs(cohens_d) >= 0.8 else ("Medium" if abs(cohens_d) >= 0.5 else "Small")
            
            print(f"     {subcat}: d={cohens_d:+.4f} ({effect_interpretation}), Diff={mean_diff:+.6f}, t={t_stat:.2f}, p={p_value:.3f}")

def check_age_effect_sizes(data, subcategory_cols):
    """检查年龄相关性的效应量"""
    
    age_data = data[data['characteristic_2'].str.contains('age:', na=False)].copy()
    
    if len(age_data) == 0:
        print("   No age data available")
        return
    
    age_data['age'] = age_data['characteristic_2'].str.extract(r'age: (\d+)').astype(float)
    
    print(f"   Age data samples: {len(age_data)}")
    print(f"   Age range: {age_data['age'].min():.0f}-{age_data['age'].max():.0f} years")
    
    print(f"\n   Correlation effect sizes (r²):")
    
    for subcat in subcategory_cols:
        correlation, p_value = stats.pearsonr(age_data['age'], age_data[subcat])
        
        r_squared = correlation**2
        
        # 效应量解释
        effect_interpretation = "Large" if r_squared >= 0.25 else ("Medium" if r_squared >= 0.09 else "Small")
        
        if p_value < 0.05:
            print(f"     {subcat}: r={correlation:+.4f}, r²={r_squared:.4f} ({effect_interpretation}), p={p_value:.3f}")

def check_sepsis_control_effect_sizes(data, subcategory_cols):
    """检查脓毒症vs对照组的效应量"""
    
    sepsis_data = data[data['group'] == 'Sepsis']
    control_data = data[data['group'] == 'Control']
    
    print(f"   Sepsis: {len(sepsis_data)}, Control: {len(control_data)}")
    
    print(f"\n   Sepsis vs Control effect sizes (Cohen's d):")
    
    for subcat in subcategory_cols:
        sepsis_scores = sepsis_data[subcat]
        control_scores = control_data[subcat]
        
        if len(sepsis_scores) > 0 and len(control_scores) > 0:
            # Cohen's d
            pooled_std = np.sqrt(((len(sepsis_scores) - 1) * sepsis_scores.var() + 
                                 (len(control_scores) - 1) * control_scores.var()) / 
                                (len(sepsis_scores) + len(control_scores) - 2))
            
            cohens_d = (sepsis_scores.mean() - control_scores.mean()) / pooled_std
            
            # t检验
            t_stat, p_value = stats.ttest_ind(sepsis_scores, control_scores)
            
            # 实际差异
            mean_diff = sepsis_scores.mean() - control_scores.mean()
            
            # 效应量解释
            effect_interpretation = "Large" if abs(cohens_d) >= 0.8 else ("Medium" if abs(cohens_d) >= 0.5 else "Small")
            
            if p_value < 0.05:
                print(f"     {subcat}: d={cohens_d:+.4f} ({effect_interpretation}), Diff={mean_diff:+.6f}, t={t_stat:.2f}, p={p_value:.3f}")

def main():
    """主函数"""
    try:
        check_effect_sizes()
        
        print(f"\n{'='*80}")
        print("EFFECT SIZE ANALYSIS COMPLETED")
        print(f"{'='*80}")
        
        print(f"\n💡 Interpretation Guidelines:")
        print(f"   • Cohen's d: Small (0.2), Medium (0.5), Large (0.8)")
        print(f"   • Eta-squared: Small (0.01), Medium (0.06), Large (0.14)")
        print(f"   • R-squared: Small (0.01), Medium (0.09), Large (0.25)")
        
        print(f"\n📝 Recommendation for paper:")
        print(f"   • If effect sizes are small: Use tables + statistical tests")
        print(f"   • If effect sizes are medium+: Use visualizations")
        print(f"   • Always report both statistical significance AND effect sizes")
        
    except Exception as e:
        print(f"❌ Error in analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()