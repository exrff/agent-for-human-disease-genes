#!/usr/bin/env python3
"""
为GSE65682生成论文用的统计表格
适合小效应量但统计显著的结果
"""

import pandas as pd
import numpy as np
from scipy import stats

def generate_publication_tables():
    """生成发表用的统计表格"""
    print("="*80)
    print("GENERATING GSE65682 PUBLICATION TABLES")
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
    
    # 生成各种表格
    generate_mars_table(merged_data, subcategory_cols)
    generate_mortality_table(merged_data, subcategory_cols)
    generate_age_correlation_table(merged_data, subcategory_cols)
    generate_sepsis_control_table(merged_data, subcategory_cols)
    
    print(f"\n✅ All publication tables generated!")

def generate_mars_table(data, subcategory_cols):
    """生成Mars内表型比较表"""
    
    mars_data = data[data['characteristic_6'].str.contains('Mars', na=False)].copy()
    
    if len(mars_data) == 0:
        return
    
    mars_data['mars_type'] = mars_data['characteristic_6'].str.extract(r'Mars(\d+)')
    
    # 创建表格
    table_data = []
    
    for subcat in subcategory_cols:
        row = {'Subcategory': subcat}
        
        # 各Mars类型的均值±标准差
        for mars_type in ['1', '2', '3', '4']:
            mars_subset = mars_data[mars_data['mars_type'] == mars_type]
            if len(mars_subset) > 0:
                mean_val = mars_subset[subcat].mean()
                std_val = mars_subset[subcat].std()
                row[f'Mars{mars_type}'] = f"{mean_val:.4f} ± {std_val:.4f}"
            else:
                row[f'Mars{mars_type}'] = "N/A"
        
        # 统计检验
        groups = []
        for mars_type in ['1', '2', '3', '4']:
            mars_subset = mars_data[mars_data['mars_type'] == mars_type]
            if len(mars_subset) > 0:
                groups.append(mars_subset[subcat].values)
        
        if len(groups) >= 2:
            f_stat, p_value = stats.f_oneway(*groups)
            
            # 计算eta-squared
            all_values = np.concatenate(groups)
            grand_mean = np.mean(all_values)
            ss_between = sum(len(group) * (np.mean(group) - grand_mean)**2 for group in groups)
            ss_total = sum((value - grand_mean)**2 for value in all_values)
            eta_squared = ss_between / ss_total if ss_total > 0 else 0
            
            row['F_statistic'] = f"{f_stat:.2f}"
            row['p_value'] = f"{p_value:.2e}" if p_value < 0.001 else f"{p_value:.3f}"
            row['eta_squared'] = f"{eta_squared:.3f}"
        else:
            row['F_statistic'] = "N/A"
            row['p_value'] = "N/A"
            row['eta_squared'] = "N/A"
        
        table_data.append(row)
    
    # 保存表格
    mars_table = pd.DataFrame(table_data)
    mars_table.to_csv('results/disease_analysis/GSE65682-脓毒症/analysis_results/Table_Mars_Endotypes.csv', index=False)
    
    print(f"\n📊 Table 1: Mars Endotype Comparison")
    print(mars_table.to_string(index=False))

def generate_mortality_table(data, subcategory_cols):
    """生成死亡率相关表"""
    
    mortality_data = data[data['characteristic_7'].str.contains('mortality_event_28days', na=False)].copy()
    
    if len(mortality_data) == 0:
        return
    
    mortality_data['mortality_28d'] = mortality_data['characteristic_7'].str.extract(r'mortality_event_28days: (\d+)').astype(float)
    mortality_data = mortality_data[mortality_data['mortality_28d'].isin([0.0, 1.0])]
    
    survivors = mortality_data[mortality_data['mortality_28d'] == 0.0]
    deaths = mortality_data[mortality_data['mortality_28d'] == 1.0]
    
    # 创建表格
    table_data = []
    
    for subcat in subcategory_cols:
        survivor_scores = survivors[subcat]
        death_scores = deaths[subcat]
        
        if len(survivor_scores) > 0 and len(death_scores) > 0:
            # 基本统计
            survivor_mean = survivor_scores.mean()
            survivor_std = survivor_scores.std()
            death_mean = death_scores.mean()
            death_std = death_scores.std()
            
            # 统计检验
            t_stat, p_value = stats.ttest_ind(survivor_scores, death_scores)
            
            # Cohen's d
            pooled_std = np.sqrt(((len(survivor_scores) - 1) * survivor_scores.var() + 
                                 (len(death_scores) - 1) * death_scores.var()) / 
                                (len(survivor_scores) + len(death_scores) - 2))
            cohens_d = (death_scores.mean() - survivor_scores.mean()) / pooled_std
            
            # 95% 置信区间
            se = pooled_std * np.sqrt(1/len(survivor_scores) + 1/len(death_scores))
            df = len(survivor_scores) + len(death_scores) - 2
            t_critical = stats.t.ppf(0.975, df)
            ci_lower = (death_mean - survivor_mean) - t_critical * se
            ci_upper = (death_mean - survivor_mean) + t_critical * se
            
            row = {
                'Subcategory': subcat,
                'Survivors_Mean_SD': f"{survivor_mean:.4f} ± {survivor_std:.4f}",
                'Deaths_Mean_SD': f"{death_mean:.4f} ± {death_std:.4f}",
                'Mean_Difference': f"{death_mean - survivor_mean:+.4f}",
                'Cohens_d': f"{cohens_d:+.3f}",
                '95%_CI': f"[{ci_lower:+.4f}, {ci_upper:+.4f}]",
                't_statistic': f"{t_stat:.2f}",
                'p_value': f"{p_value:.3f}" if p_value >= 0.001 else f"{p_value:.2e}"
            }
            
            table_data.append(row)
    
    # 保存表格
    mortality_table = pd.DataFrame(table_data)
    mortality_table.to_csv('results/disease_analysis/GSE65682-脓毒症/analysis_results/Table_Mortality_Analysis.csv', index=False)
    
    print(f"\n📊 Table 2: Mortality-Associated Subcategory Differences")
    print(f"Sample sizes: Survivors n={len(survivors)}, Deaths n={len(deaths)}")
    print(mortality_table.to_string(index=False))

def generate_age_correlation_table(data, subcategory_cols):
    """生成年龄相关性表"""
    
    age_data = data[data['characteristic_2'].str.contains('age:', na=False)].copy()
    
    if len(age_data) == 0:
        return
    
    age_data['age'] = age_data['characteristic_2'].str.extract(r'age: (\d+)').astype(float)
    
    # 创建表格
    table_data = []
    
    for subcat in subcategory_cols:
        correlation, p_value = stats.pearsonr(age_data['age'], age_data[subcat])
        
        # 95% 置信区间 (Fisher's z transformation)
        n = len(age_data)
        z = 0.5 * np.log((1 + correlation) / (1 - correlation))
        se_z = 1 / np.sqrt(n - 3)
        z_critical = stats.norm.ppf(0.975)
        
        z_lower = z - z_critical * se_z
        z_upper = z + z_critical * se_z
        
        r_lower = (np.exp(2 * z_lower) - 1) / (np.exp(2 * z_lower) + 1)
        r_upper = (np.exp(2 * z_upper) - 1) / (np.exp(2 * z_upper) + 1)
        
        row = {
            'Subcategory': subcat,
            'Correlation_r': f"{correlation:+.4f}",
            'r_squared': f"{correlation**2:.4f}",
            '95%_CI': f"[{r_lower:+.3f}, {r_upper:+.3f}]",
            'p_value': f"{p_value:.3f}" if p_value >= 0.001 else f"{p_value:.2e}",
            'Sample_size': f"{n}"
        }
        
        table_data.append(row)
    
    # 保存表格
    age_table = pd.DataFrame(table_data)
    age_table.to_csv('results/disease_analysis/GSE65682-脓毒症/analysis_results/Table_Age_Correlations.csv', index=False)
    
    print(f"\n📊 Table 3: Age-System Correlation Analysis")
    print(f"Age range: {age_data['age'].min():.0f}-{age_data['age'].max():.0f} years")
    print(age_table.to_string(index=False))

def generate_sepsis_control_table(data, subcategory_cols):
    """生成脓毒症vs对照组比较表"""
    
    sepsis_data = data[data['group'] == 'Sepsis']
    control_data = data[data['group'] == 'Control']
    
    # 创建表格
    table_data = []
    
    for subcat in subcategory_cols:
        sepsis_scores = sepsis_data[subcat]
        control_scores = control_data[subcat]
        
        if len(sepsis_scores) > 0 and len(control_scores) > 0:
            # 基本统计
            sepsis_mean = sepsis_scores.mean()
            sepsis_std = sepsis_scores.std()
            control_mean = control_scores.mean()
            control_std = control_scores.std()
            
            # 统计检验
            t_stat, p_value = stats.ttest_ind(sepsis_scores, control_scores)
            
            # Cohen's d
            pooled_std = np.sqrt(((len(sepsis_scores) - 1) * sepsis_scores.var() + 
                                 (len(control_scores) - 1) * control_scores.var()) / 
                                (len(sepsis_scores) + len(control_scores) - 2))
            cohens_d = (sepsis_scores.mean() - control_scores.mean()) / pooled_std
            
            # 95% 置信区间
            se = pooled_std * np.sqrt(1/len(sepsis_scores) + 1/len(control_scores))
            df = len(sepsis_scores) + len(control_scores) - 2
            t_critical = stats.t.ppf(0.975, df)
            ci_lower = (sepsis_mean - control_mean) - t_critical * se
            ci_upper = (sepsis_mean - control_mean) + t_critical * se
            
            row = {
                'Subcategory': subcat,
                'Sepsis_Mean_SD': f"{sepsis_mean:.4f} ± {sepsis_std:.4f}",
                'Control_Mean_SD': f"{control_mean:.4f} ± {control_std:.4f}",
                'Mean_Difference': f"{sepsis_mean - control_mean:+.4f}",
                'Cohens_d': f"{cohens_d:+.3f}",
                '95%_CI': f"[{ci_lower:+.4f}, {ci_upper:+.4f}]",
                't_statistic': f"{t_stat:.2f}",
                'p_value': f"{p_value:.3f}" if p_value >= 0.001 else f"{p_value:.2e}"
            }
            
            table_data.append(row)
    
    # 保存表格
    sepsis_table = pd.DataFrame(table_data)
    sepsis_table.to_csv('results/disease_analysis/GSE65682-脓毒症/analysis_results/Table_Sepsis_Control.csv', index=False)
    
    print(f"\n📊 Table 4: Sepsis vs Control Comparison")
    print(f"Sample sizes: Sepsis n={len(sepsis_data)}, Control n={len(control_data)}")
    print(sepsis_table.to_string(index=False))

def main():
    """主函数"""
    try:
        generate_publication_tables()
        
        print(f"\n{'='*80}")
        print("PUBLICATION TABLES COMPLETED")
        print(f"{'='*80}")
        
        print(f"\n📝 Usage in paper:")
        print(f"   • Use tables for small effect sizes (mortality, age)")
        print(f"   • Use figures for large effect sizes (sepsis vs control, Mars)")
        print(f"   • Always report effect sizes alongside p-values")
        print(f"   • Include 95% confidence intervals")
        
    except Exception as e:
        print(f"❌ Error generating tables: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()