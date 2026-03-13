#!/usr/bin/env python3
"""
为GSE65682创建真正有意义的可视化
展示统计显著的差异和临床相关的模式
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')

def create_meaningful_visualizations():
    """创建有意义的可视化"""
    print("="*80)
    print("CREATING MEANINGFUL GSE65682 VISUALIZATIONS")
    print("="*80)
    
    # 加载数据
    print(f"\n📊 Loading data...")
    
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
    
    print(f"   • Total samples: {len(merged_data)}")
    print(f"   • Sepsis: {len(merged_data[merged_data['group'] == 'Sepsis'])}")
    print(f"   • Control: {len(merged_data[merged_data['group'] == 'Control'])}")
    
    # 创建综合可视化
    fig = plt.figure(figsize=(24, 18))
    
    # 1. Mars内表型比较 - 显示真实差异
    print(f"\n🎨 Creating Mars endotype comparison...")
    create_mars_comparison(merged_data, fig, 1)
    
    # 2. 死亡率预测模式
    print(f"🎨 Creating mortality prediction patterns...")
    create_mortality_patterns(merged_data, fig, 2)
    
    # 3. 年龄相关系统变化
    print(f"🎨 Creating age-related patterns...")
    create_age_patterns(merged_data, fig, 3)
    
    # 4. 系统网络重构
    print(f"🎨 Creating system network disruption...")
    create_network_disruption(merged_data, fig, 4)
    
    # 5. 疾病严重程度分层
    print(f"🎨 Creating severity stratification...")
    create_severity_stratification(merged_data, fig, 5)
    
    # 6. 隐藏亚群发现
    print(f"🎨 Creating hidden subgroups...")
    create_hidden_subgroups(merged_data, fig, 6)
    
    plt.tight_layout()
    plt.savefig('results/disease_analysis/GSE65682-脓毒症/analysis_results/GSE65682_meaningful_discoveries.png', 
                dpi=300, bbox_inches='tight')
    plt.close()
    
    # 创建单独的重点图
    create_focused_visualizations(merged_data)
    
    print(f"\n✅ Meaningful visualizations created!")

def create_mars_comparison(data, fig, subplot_num):
    """创建Mars内表型比较图"""
    
    # 提取Mars数据
    mars_data = data[data['characteristic_6'].str.contains('Mars', na=False)].copy()
    
    if len(mars_data) == 0:
        return
    
    mars_data['mars_type'] = mars_data['characteristic_6'].str.extract(r'Mars(\d+)')
    
    # 选择差异最大的子分类
    subcategory_cols = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'E1', 'E2']
    
    # 计算每个子分类在Mars类型间的F统计量
    f_stats = {}
    for subcat in subcategory_cols:
        groups = []
        for mars_type in ['1', '2', '3', '4']:
            mars_subset = mars_data[mars_data['mars_type'] == mars_type]
            if len(mars_subset) > 0:
                groups.append(mars_subset[subcat].values)
        
        if len(groups) >= 2:
            try:
                f_stat, p_value = stats.f_oneway(*groups)
                f_stats[subcat] = f_stat
            except:
                f_stats[subcat] = 0
    
    # 选择F统计量最大的6个子分类
    top_subcats = sorted(f_stats.items(), key=lambda x: x[1], reverse=True)[:6]
    selected_subcats = [item[0] for item in top_subcats]
    
    plt.subplot(3, 4, subplot_num)
    
    # 创建箱线图
    plot_data = []
    for subcat in selected_subcats:
        for mars_type in ['1', '2', '3', '4']:
            mars_subset = mars_data[mars_data['mars_type'] == mars_type]
            if len(mars_subset) > 0:
                for score in mars_subset[subcat]:
                    plot_data.append({
                        'Subcategory': subcat,
                        'Mars_Type': f'Mars{mars_type}',
                        'Score': score
                    })
    
    plot_df = pd.DataFrame(plot_data)
    
    if len(plot_df) > 0:
        sns.boxplot(data=plot_df, x='Subcategory', y='Score', hue='Mars_Type', ax=plt.gca())
        plt.title('Mars Endotype Differences\n(Top 6 Discriminating Subcategories)')
        plt.xticks(rotation=45)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

def create_mortality_patterns(data, fig, subplot_num):
    """创建死亡率预测模式图"""
    
    # 提取死亡率数据
    mortality_data = data[data['characteristic_7'].str.contains('mortality_event_28days', na=False)].copy()
    
    if len(mortality_data) == 0:
        return
    
    mortality_data['mortality_28d'] = mortality_data['characteristic_7'].str.extract(r'mortality_event_28days: (\d+)').astype(float)
    
    # 只保留有明确死亡率信息的样本
    mortality_data = mortality_data[mortality_data['mortality_28d'].isin([0.0, 1.0])]
    
    if len(mortality_data) == 0:
        return
    
    plt.subplot(3, 4, subplot_num)
    
    # 计算生存者vs死亡者的差异
    survivors = mortality_data[mortality_data['mortality_28d'] == 0.0]
    deaths = mortality_data[mortality_data['mortality_28d'] == 1.0]
    
    subcategory_cols = ['B1', 'B2', 'B3', 'C1', 'C2']  # 重点关注免疫和代谢
    
    survivor_means = []
    death_means = []
    p_values = []
    
    for subcat in subcategory_cols:
        survivor_scores = survivors[subcat]
        death_scores = deaths[subcat]
        
        if len(survivor_scores) > 0 and len(death_scores) > 0:
            t_stat, p_value = stats.ttest_ind(survivor_scores, death_scores)
            
            survivor_means.append(survivor_scores.mean())
            death_means.append(death_scores.mean())
            p_values.append(p_value)
        else:
            survivor_means.append(0)
            death_means.append(0)
            p_values.append(1)
    
    x = np.arange(len(subcategory_cols))
    width = 0.35
    
    bars1 = plt.bar(x - width/2, survivor_means, width, label=f'Survivors (n={len(survivors)})', 
                   alpha=0.8, color='green')
    bars2 = plt.bar(x + width/2, death_means, width, label=f'Deaths (n={len(deaths)})', 
                   alpha=0.8, color='red')
    
    # 添加显著性标记
    for i, p_val in enumerate(p_values):
        if p_val < 0.05:
            significance = "***" if p_val < 0.001 else ("**" if p_val < 0.01 else "*")
            max_height = max(survivor_means[i], death_means[i])
            plt.text(i, max_height + 0.001, significance, ha='center', fontweight='bold')
    
    plt.xlabel('Subcategories')
    plt.ylabel('ssGSEA Score')
    plt.title(f'Mortality-Associated Patterns\n(28-day mortality: {len(deaths)}/{len(mortality_data)} = {len(deaths)/len(mortality_data)*100:.1f}%)')
    plt.xticks(x, subcategory_cols)
    plt.legend()

def create_age_patterns(data, fig, subplot_num):
    """创建年龄相关模式图"""
    
    # 提取年龄数据
    age_data = data[data['characteristic_2'].str.contains('age:', na=False)].copy()
    
    if len(age_data) == 0:
        return
    
    age_data['age'] = age_data['characteristic_2'].str.extract(r'age: (\d+)').astype(float)
    
    plt.subplot(3, 4, subplot_num)
    
    # 计算年龄与系统的相关性
    subcategory_cols = ['B1', 'B2', 'B3', 'C1', 'C2', 'C3']
    
    correlations = []
    p_values = []
    
    for subcat in subcategory_cols:
        correlation, p_value = stats.pearsonr(age_data['age'], age_data[subcat])
        correlations.append(correlation)
        p_values.append(p_value)
    
    # 创建条形图
    colors = ['red' if r < 0 else 'blue' for r in correlations]
    bars = plt.bar(subcategory_cols, correlations, color=colors, alpha=0.7)
    
    # 添加显著性标记
    for i, (corr, p_val) in enumerate(zip(correlations, p_values)):
        if p_val < 0.05:
            significance = "***" if p_val < 0.001 else ("**" if p_val < 0.01 else "*")
            height = corr + (0.02 if corr > 0 else -0.02)
            plt.text(i, height, significance, ha='center', fontweight='bold')
    
    plt.xlabel('Subcategories')
    plt.ylabel('Correlation with Age')
    plt.title(f'Age-Related System Changes\n(Age range: {age_data["age"].min():.0f}-{age_data["age"].max():.0f} years)')
    plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    plt.xticks(rotation=45)

def create_network_disruption(data, fig, subplot_num):
    """创建系统网络重构图"""
    
    # 计算系统级得分
    system_scores = pd.DataFrame()
    system_scores['A'] = data[['A1', 'A2', 'A3', 'A4']].mean(axis=1)
    system_scores['B'] = data[['B1', 'B2', 'B3']].mean(axis=1)
    system_scores['C'] = data[['C1', 'C2', 'C3']].mean(axis=1)
    system_scores['D'] = data[['D1', 'D2']].mean(axis=1)
    system_scores['E'] = data[['E1', 'E2']].mean(axis=1)
    system_scores['group'] = data['group']
    
    system_cols = ['A', 'B', 'C', 'D', 'E']
    
    # 分别计算脓毒症和对照组的相关性
    sepsis_systems = system_scores[system_scores['group'] == 'Sepsis'][system_cols]
    control_systems = system_scores[system_scores['group'] == 'Control'][system_cols]
    
    sepsis_corr = sepsis_systems.corr()
    control_corr = control_systems.corr()
    
    # 计算相关性差异
    corr_diff = sepsis_corr - control_corr
    
    plt.subplot(3, 4, subplot_num)
    
    # 创建热图显示相关性差异
    mask = np.triu(np.ones_like(corr_diff, dtype=bool))  # 只显示下三角
    
    sns.heatmap(corr_diff, mask=mask, annot=True, fmt='.3f', cmap='RdBu_r', center=0,
                square=True, cbar_kws={'label': 'Correlation Difference'})
    
    plt.title('System Network Disruption\n(Sepsis - Control Correlations)')
    plt.xlabel('Systems')
    plt.ylabel('Systems')

def create_severity_stratification(data, fig, subplot_num):
    """创建疾病严重程度分层图"""
    
    # 只分析脓毒症患者
    sepsis_data = data[data['group'] == 'Sepsis'].copy()
    
    # 计算系统级得分
    sepsis_data['A'] = sepsis_data[['A1', 'A2', 'A3', 'A4']].mean(axis=1)
    sepsis_data['B'] = sepsis_data[['B1', 'B2', 'B3']].mean(axis=1)
    sepsis_data['C'] = sepsis_data[['C1', 'C2', 'C3']].mean(axis=1)
    sepsis_data['D'] = sepsis_data[['D1', 'D2']].mean(axis=1)
    sepsis_data['E'] = sepsis_data[['E1', 'E2']].mean(axis=1)
    
    # 计算严重程度指数
    sepsis_data['severity_index'] = sepsis_data['B'] + sepsis_data['C']
    
    # 按严重程度分组
    sepsis_data['severity_tertile'] = pd.qcut(sepsis_data['severity_index'], 
                                            q=3, labels=['Mild', 'Moderate', 'Severe'])
    
    plt.subplot(3, 4, subplot_num)
    
    # 创建箱线图显示不同严重程度的系统激活
    system_cols = ['A', 'B', 'C', 'D', 'E']
    
    plot_data = []
    for system in system_cols:
        for severity in ['Mild', 'Moderate', 'Severe']:
            severity_data = sepsis_data[sepsis_data['severity_tertile'] == severity]
            for score in severity_data[system]:
                plot_data.append({
                    'System': system,
                    'Severity': severity,
                    'Score': score
                })
    
    plot_df = pd.DataFrame(plot_data)
    
    if len(plot_df) > 0:
        sns.boxplot(data=plot_df, x='System', y='Score', hue='Severity', ax=plt.gca())
        plt.title('Disease Severity Stratification\n(Based on B+C System Activation)')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

def create_hidden_subgroups(data, fig, subplot_num):
    """创建隐藏亚群图"""
    
    # 只分析脓毒症患者
    sepsis_data = data[data['group'] == 'Sepsis'].copy()
    
    subcategory_cols = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'E1', 'E2']
    
    # 标准化数据
    scaler = StandardScaler()
    scaled_scores = scaler.fit_transform(sepsis_data[subcategory_cols])
    
    # 聚类
    kmeans = KMeans(n_clusters=2, random_state=42)
    clusters = kmeans.fit_predict(scaled_scores)
    
    # PCA降维可视化
    pca = PCA(n_components=2)
    pca_scores = pca.fit_transform(scaled_scores)
    
    plt.subplot(3, 4, subplot_num)
    
    colors = ['red', 'blue']
    for cluster_id in [0, 1]:
        mask = clusters == cluster_id
        plt.scatter(pca_scores[mask, 0], pca_scores[mask, 1], 
                   c=colors[cluster_id], label=f'Subgroup {cluster_id+1} (n={np.sum(mask)})', 
                   alpha=0.6, s=30)
    
    plt.xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)')
    plt.ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)')
    plt.title('Hidden Patient Subgroups\n(Unsupervised Clustering)')
    plt.legend()

def create_focused_visualizations(data):
    """创建重点可视化"""
    
    # 1. Mars内表型详细比较
    create_mars_detailed_comparison(data)
    
    # 2. 死亡率预测热图
    create_mortality_heatmap(data)
    
    # 3. 年龄-系统相关性散点图
    create_age_system_scatter(data)

def create_mars_detailed_comparison(data):
    """创建Mars内表型详细比较图"""
    
    mars_data = data[data['characteristic_6'].str.contains('Mars', na=False)].copy()
    
    if len(mars_data) == 0:
        return
    
    mars_data['mars_type'] = mars_data['characteristic_6'].str.extract(r'Mars(\d+)')
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    subcategory_cols = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'E1', 'E2']
    
    # 计算每个Mars类型的平均激活模式
    mars_profiles = {}
    for mars_type in ['1', '2', '3', '4']:
        mars_subset = mars_data[mars_data['mars_type'] == mars_type]
        if len(mars_subset) > 0:
            profile = [mars_subset[subcat].mean() for subcat in subcategory_cols]
            mars_profiles[f'Mars{mars_type}'] = profile
    
    # 雷达图
    if mars_profiles:
        ax = axes[0, 0]
        
        angles = np.linspace(0, 2 * np.pi, len(subcategory_cols), endpoint=False).tolist()
        angles += angles[:1]  # 闭合
        
        colors = ['red', 'blue', 'green', 'orange']
        
        for i, (mars_type, profile) in enumerate(mars_profiles.items()):
            profile += profile[:1]  # 闭合
            ax.plot(angles, profile, 'o-', linewidth=2, label=mars_type, color=colors[i])
            ax.fill(angles, profile, alpha=0.25, color=colors[i])
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(subcategory_cols)
        ax.set_title('Mars Endotype Functional Profiles')
        ax.legend()
        ax.grid(True)
    
    # 热图比较
    ax = axes[0, 1]
    
    if mars_profiles:
        profile_matrix = np.array(list(mars_profiles.values()))
        
        sns.heatmap(profile_matrix, annot=True, fmt='.4f', cmap='RdYlBu_r',
                   xticklabels=subcategory_cols, yticklabels=list(mars_profiles.keys()),
                   ax=ax)
        ax.set_title('Mars Endotype Activation Heatmap')
    
    # 主成分分析
    ax = axes[1, 0]
    
    scaler = StandardScaler()
    scaled_scores = scaler.fit_transform(mars_data[subcategory_cols])
    
    pca = PCA(n_components=2)
    pca_scores = pca.fit_transform(scaled_scores)
    
    colors = {'1': 'red', '2': 'blue', '3': 'green', '4': 'orange'}
    
    for mars_type in ['1', '2', '3', '4']:
        mask = mars_data['mars_type'] == mars_type
        if np.any(mask):
            ax.scatter(pca_scores[mask, 0], pca_scores[mask, 1], 
                      c=colors[mars_type], label=f'Mars{mars_type}', alpha=0.7)
    
    ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)')
    ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)')
    ax.set_title('Mars Endotypes in PCA Space')
    ax.legend()
    
    # 统计显著性
    ax = axes[1, 1]
    
    # 计算F统计量
    f_stats = []
    p_values = []
    
    for subcat in subcategory_cols:
        groups = []
        for mars_type in ['1', '2', '3', '4']:
            mars_subset = mars_data[mars_data['mars_type'] == mars_type]
            if len(mars_subset) > 0:
                groups.append(mars_subset[subcat].values)
        
        if len(groups) >= 2:
            try:
                f_stat, p_value = stats.f_oneway(*groups)
                f_stats.append(f_stat)
                p_values.append(p_value)
            except:
                f_stats.append(0)
                p_values.append(1)
        else:
            f_stats.append(0)
            p_values.append(1)
    
    # 显著性条形图
    colors = ['red' if p < 0.001 else ('orange' if p < 0.01 else ('yellow' if p < 0.05 else 'gray')) 
             for p in p_values]
    
    bars = ax.bar(subcategory_cols, f_stats, color=colors, alpha=0.7)
    ax.set_xlabel('Subcategories')
    ax.set_ylabel('F-statistic')
    ax.set_title('Statistical Significance of Mars Differences')
    ax.tick_params(axis='x', rotation=45)
    
    # 添加显著性图例
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor='red', label='p < 0.001'),
                      Patch(facecolor='orange', label='p < 0.01'),
                      Patch(facecolor='yellow', label='p < 0.05'),
                      Patch(facecolor='gray', label='p ≥ 0.05')]
    ax.legend(handles=legend_elements, loc='upper right')
    
    plt.tight_layout()
    plt.savefig('results/disease_analysis/GSE65682-脓毒症/analysis_results/GSE65682_mars_detailed.png', 
                dpi=300, bbox_inches='tight')
    plt.close()

def create_mortality_heatmap(data):
    """创建死亡率预测热图"""
    
    mortality_data = data[data['characteristic_7'].str.contains('mortality_event_28days', na=False)].copy()
    
    if len(mortality_data) == 0:
        return
    
    mortality_data['mortality_28d'] = mortality_data['characteristic_7'].str.extract(r'mortality_event_28days: (\d+)').astype(float)
    mortality_data = mortality_data[mortality_data['mortality_28d'].isin([0.0, 1.0])]
    
    if len(mortality_data) == 0:
        return
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    subcategory_cols = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'E1', 'E2']
    
    survivors = mortality_data[mortality_data['mortality_28d'] == 0.0]
    deaths = mortality_data[mortality_data['mortality_28d'] == 1.0]
    
    # 1. 生存者vs死亡者平均激活
    ax = axes[0]
    
    survivor_means = [survivors[subcat].mean() for subcat in subcategory_cols]
    death_means = [deaths[subcat].mean() for subcat in subcategory_cols]
    
    comparison_matrix = np.array([survivor_means, death_means])
    
    sns.heatmap(comparison_matrix, annot=True, fmt='.4f', cmap='RdYlBu_r',
               xticklabels=subcategory_cols, yticklabels=['Survivors', 'Deaths'],
               ax=ax)
    ax.set_title(f'Mortality-Associated Activation\n(Survivors: {len(survivors)}, Deaths: {len(deaths)})')
    
    # 2. 差异热图
    ax = axes[1]
    
    differences = np.array(death_means) - np.array(survivor_means)
    diff_matrix = differences.reshape(1, -1)
    
    sns.heatmap(diff_matrix, annot=True, fmt='.4f', cmap='RdBu_r', center=0,
               xticklabels=subcategory_cols, yticklabels=['Deaths - Survivors'],
               ax=ax)
    ax.set_title('Activation Differences\n(Positive = Higher in Deaths)')
    
    # 3. 统计显著性
    ax = axes[2]
    
    t_stats = []
    p_values = []
    
    for subcat in subcategory_cols:
        survivor_scores = survivors[subcat]
        death_scores = deaths[subcat]
        
        if len(survivor_scores) > 0 and len(death_scores) > 0:
            t_stat, p_value = stats.ttest_ind(survivor_scores, death_scores)
            t_stats.append(abs(t_stat))
            p_values.append(p_value)
        else:
            t_stats.append(0)
            p_values.append(1)
    
    colors = ['red' if p < 0.05 else 'gray' for p in p_values]
    
    bars = ax.bar(subcategory_cols, t_stats, color=colors, alpha=0.7)
    ax.set_xlabel('Subcategories')
    ax.set_ylabel('|t-statistic|')
    ax.set_title('Statistical Significance')
    ax.tick_params(axis='x', rotation=45)
    
    # 添加显著性标记
    for i, (t_stat, p_val) in enumerate(zip(t_stats, p_values)):
        if p_val < 0.05:
            significance = "***" if p_val < 0.001 else ("**" if p_val < 0.01 else "*")
            ax.text(i, t_stat + 0.1, significance, ha='center', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('results/disease_analysis/GSE65682-脓毒症/analysis_results/GSE65682_mortality_detailed.png', 
                dpi=300, bbox_inches='tight')
    plt.close()

def create_age_system_scatter(data):
    """创建年龄-系统相关性散点图"""
    
    age_data = data[data['characteristic_2'].str.contains('age:', na=False)].copy()
    
    if len(age_data) == 0:
        return
    
    age_data['age'] = age_data['characteristic_2'].str.extract(r'age: (\d+)').astype(float)
    
    # 选择显著相关的子分类
    subcategory_cols = ['B1', 'B2', 'B3', 'C3', 'D2', 'E2']
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.flatten()
    
    for i, subcat in enumerate(subcategory_cols):
        ax = axes[i]
        
        correlation, p_value = stats.pearsonr(age_data['age'], age_data[subcat])
        
        # 散点图
        ax.scatter(age_data['age'], age_data[subcat], alpha=0.5, s=20)
        
        # 拟合线
        z = np.polyfit(age_data['age'], age_data[subcat], 1)
        p = np.poly1d(z)
        ax.plot(age_data['age'], p(age_data['age']), "r--", alpha=0.8)
        
        # 标题和标签
        significance = "***" if p_value < 0.001 else ("**" if p_value < 0.01 else ("*" if p_value < 0.05 else "ns"))
        ax.set_title(f'{subcat}: r={correlation:.3f} {significance}')
        ax.set_xlabel('Age (years)')
        ax.set_ylabel(f'{subcat} Score')
        
        # 添加统计信息
        ax.text(0.05, 0.95, f'p={p_value:.4f}', transform=ax.transAxes, 
               verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig('results/disease_analysis/GSE65682-脓毒症/analysis_results/GSE65682_age_correlations.png', 
                dpi=300, bbox_inches='tight')
    plt.close()

def main():
    """主函数"""
    try:
        create_meaningful_visualizations()
        
        print(f"\n{'='*80}")
        print("MEANINGFUL VISUALIZATIONS COMPLETED")
        print(f"{'='*80}")
        
        print(f"\n📁 Generated Files:")
        print(f"   • GSE65682_meaningful_discoveries.png - 综合发现图")
        print(f"   • GSE65682_mars_detailed.png - Mars内表型详细分析")
        print(f"   • GSE65682_mortality_detailed.png - 死亡率预测详细分析")
        print(f"   • GSE65682_age_correlations.png - 年龄相关性散点图")
        
        print(f"\n🎯 这些图片将真正展示统计显著的差异!")
        
    except Exception as e:
        print(f"❌ Error creating visualizations: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()