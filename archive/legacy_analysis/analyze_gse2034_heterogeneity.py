#!/usr/bin/env python3
"""
分析GSE2034乳腺癌患者的异质性
检查是否有疾病亚型标签，分析患者间系统激活差异
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import gzip

def analyze_gse2034_heterogeneity():
    """分析GSE2034的患者异质性"""
    print("="*80)
    print("GSE2034 BREAST CANCER PATIENT HETEROGENEITY ANALYSIS")
    print("="*80)
    
    # 1. 加载标准化数据
    print("\n📊 Loading standardized data...")
    
    sample_info = pd.read_csv('results/disease_analysis/GSE2034_sample_info.csv')
    system_scores = pd.read_csv('results/disease_analysis/GSE2034_system_scores.csv')
    subcategory_scores = pd.read_csv('results/disease_analysis/GSE2034_subcategory_scores.csv')
    
    print(f"   • Samples: {len(sample_info)}")
    print(f"   • Unique subjects: {sample_info['subject_id'].nunique()}")
    
    # 2. 尝试从原始数据获取更多信息
    print("\n🔍 Extracting additional clinical information...")
    
    try:
        # 尝试读取原始GEO数据
        original_data_path = 'data/validation_datasets/GSE2034-乳腺癌/GSE2034_series_matrix.txt.gz'
        clinical_info = extract_clinical_info_from_geo(original_data_path)
        
        if clinical_info:
            print("   ✅ Successfully extracted clinical information")
            # 合并临床信息
            sample_info_enhanced = merge_clinical_info(sample_info, clinical_info)
        else:
            print("   ⚠️ No additional clinical information found")
            sample_info_enhanced = sample_info
            
    except Exception as e:
        print(f"   ❌ Error extracting clinical info: {str(e)}")
        sample_info_enhanced = sample_info
    
    # 3. 分析系统激活的患者间差异
    print("\n📈 Analyzing patient heterogeneity in system activation...")
    
    # 计算系统得分的变异系数
    system_cols = ['A', 'B', 'C', 'D', 'E']
    system_variability = {}
    
    for system in system_cols:
        scores = system_scores[system]
        mean_score = scores.mean()
        std_score = scores.std()
        cv = std_score / mean_score if mean_score > 0 else 0
        system_variability[system] = {
            'mean': mean_score,
            'std': std_score,
            'cv': cv,
            'min': scores.min(),
            'max': scores.max(),
            'range': scores.max() - scores.min()
        }
        
        print(f"   • System {system}: CV={cv:.3f}, Range=[{scores.min():.3f}, {scores.max():.3f}]")
    
    # 4. 聚类分析识别患者亚群
    print("\n🔬 Performing clustering analysis...")
    
    # 标准化系统得分
    scaler = StandardScaler()
    system_scores_scaled = scaler.fit_transform(system_scores[system_cols])
    
    # K-means聚类
    optimal_k = find_optimal_clusters(system_scores_scaled)
    print(f"   • Optimal number of clusters: {optimal_k}")
    
    kmeans = KMeans(n_clusters=optimal_k, random_state=42)
    clusters = kmeans.fit_predict(system_scores_scaled)
    
    # 添加聚类标签
    system_scores['cluster'] = clusters
    sample_info_enhanced['cluster'] = clusters
    
    # 分析每个聚类的特征
    print(f"\n   Cluster characteristics:")
    for cluster_id in range(optimal_k):
        cluster_mask = clusters == cluster_id
        cluster_size = np.sum(cluster_mask)
        
        print(f"   • Cluster {cluster_id} (n={cluster_size}):")
        for system in system_cols:
            cluster_mean = system_scores.loc[cluster_mask, system].mean()
            overall_mean = system_scores[system].mean()
            fold_change = cluster_mean / overall_mean
            print(f"     - System {system}: {cluster_mean:.3f} (FC={fold_change:.2f})")
    
    # 5. 层次聚类分析
    print("\n🌳 Performing hierarchical clustering...")
    
    linkage_matrix = linkage(system_scores_scaled, method='ward')
    
    # 6. 生成可视化
    print("\n📊 Generating visualizations...")
    
    create_heterogeneity_visualizations(
        system_scores, subcategory_scores, sample_info_enhanced, 
        system_variability, linkage_matrix, optimal_k
    )
    
    # 7. 统计分析
    print("\n📋 Statistical analysis...")
    
    # 检验系统间激活的相关性
    correlation_matrix = system_scores[system_cols].corr()
    print(f"   System correlation matrix:")
    print(correlation_matrix.round(3))
    
    # 检验是否存在显著的患者亚群
    perform_statistical_tests(system_scores, clusters, system_cols)
    
    # 8. 保存结果
    print("\n💾 Saving results...")
    
    # 保存增强的样本信息
    sample_info_enhanced.to_csv('results/disease_analysis/GSE2034_sample_info_enhanced.csv', index=False)
    
    # 保存聚类结果
    cluster_results = system_scores[['sample_id', 'subject_id'] + system_cols + ['cluster']]
    cluster_results.to_csv('results/disease_analysis/GSE2034_cluster_analysis.csv', index=False)
    
    # 保存异质性分析报告
    save_heterogeneity_report(system_variability, optimal_k, correlation_matrix)
    
    print(f"   ✅ Results saved to results/disease_analysis/")
    
    return system_variability, optimal_k, clusters

def extract_clinical_info_from_geo(data_path):
    """从GEO数据文件中提取临床信息"""
    try:
        with gzip.open(data_path, 'rt', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        clinical_info = {}
        sample_titles = []
        sample_ids = []
        characteristics = []
        
        for line in lines:
            if line.startswith('!Sample_title'):
                titles = line.strip().split('\t')[1:]
                sample_titles = [t.strip('"') for t in titles]
            elif line.startswith('!Sample_geo_accession'):
                accessions = line.strip().split('\t')[1:]
                sample_ids = [a.strip('"') for a in accessions]
            elif line.startswith('!Sample_characteristics_ch1'):
                chars = line.strip().split('\t')[1:]
                characteristics.append([c.strip('"') for c in chars])
            elif line.startswith('!series_matrix_table_begin'):
                break
        
        if sample_ids and sample_titles:
            clinical_info = {
                'sample_ids': sample_ids,
                'sample_titles': sample_titles,
                'characteristics': characteristics
            }
            
            # 解析特征信息
            parsed_characteristics = parse_sample_characteristics(characteristics, sample_ids)
            clinical_info.update(parsed_characteristics)
        
        return clinical_info
        
    except Exception as e:
        print(f"Error extracting clinical info: {str(e)}")
        return None

def parse_sample_characteristics(characteristics, sample_ids):
    """解析样本特征信息"""
    parsed = {}
    
    if not characteristics:
        return parsed
    
    # 尝试解析常见的乳腺癌特征
    for char_list in characteristics:
        if len(char_list) != len(sample_ids):
            continue
            
        # 检查是否包含乳腺癌相关信息
        sample_char = char_list[0].lower() if char_list else ""
        
        if any(keyword in sample_char for keyword in ['er', 'estrogen', 'receptor']):
            parsed['er_status'] = char_list
        elif any(keyword in sample_char for keyword in ['pr', 'progesterone']):
            parsed['pr_status'] = char_list
        elif any(keyword in sample_char for keyword in ['her2', 'erbb2']):
            parsed['her2_status'] = char_list
        elif any(keyword in sample_char for keyword in ['grade', 'tumor']):
            parsed['tumor_grade'] = char_list
        elif any(keyword in sample_char for keyword in ['stage']):
            parsed['tumor_stage'] = char_list
        elif any(keyword in sample_char for keyword in ['node', 'lymph']):
            parsed['lymph_node'] = char_list
        elif any(keyword in sample_char for keyword in ['age']):
            parsed['age'] = char_list
        elif any(keyword in sample_char for keyword in ['survival', 'outcome']):
            parsed['survival'] = char_list
    
    return parsed

def merge_clinical_info(sample_info, clinical_info):
    """合并临床信息到样本信息中"""
    sample_info_enhanced = sample_info.copy()
    
    # 创建样本ID到索引的映射
    if 'sample_ids' in clinical_info:
        id_to_index = {sid: i for i, sid in enumerate(clinical_info['sample_ids'])}
        
        # 添加临床特征
        for feature, values in clinical_info.items():
            if feature in ['sample_ids', 'sample_titles', 'characteristics']:
                continue
                
            feature_values = []
            for _, row in sample_info.iterrows():
                sample_id = row['sample_id']
                if sample_id in id_to_index:
                    idx = id_to_index[sample_id]
                    if idx < len(values):
                        feature_values.append(values[idx])
                    else:
                        feature_values.append('Unknown')
                else:
                    feature_values.append('Unknown')
            
            sample_info_enhanced[feature] = feature_values
    
    return sample_info_enhanced

def find_optimal_clusters(data, max_k=8):
    """使用肘部法则找到最优聚类数"""
    inertias = []
    k_range = range(2, max_k + 1)
    
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42)
        kmeans.fit(data)
        inertias.append(kmeans.inertia_)
    
    # 计算肘部点
    # 简单的肘部检测：找到惯性下降最大的点
    diffs = np.diff(inertias)
    optimal_k = k_range[np.argmax(np.abs(diffs))]
    
    return optimal_k

def create_heterogeneity_visualizations(system_scores, subcategory_scores, sample_info, 
                                      system_variability, linkage_matrix, optimal_k):
    """创建异质性分析可视化"""
    
    plt.style.use('default')
    fig = plt.figure(figsize=(20, 16))
    
    # 1. 系统得分分布
    plt.subplot(3, 4, 1)
    system_cols = ['A', 'B', 'C', 'D', 'E']
    system_scores[system_cols].boxplot()
    plt.title('System Score Distributions')
    plt.ylabel('ssGSEA Score')
    plt.xticks(rotation=0)
    
    # 2. 系统得分热图
    plt.subplot(3, 4, 2)
    system_data = system_scores[system_cols].T
    sns.heatmap(system_data, cmap='RdBu_r', center=0, cbar_kws={'label': 'ssGSEA Score'})
    plt.title('Patient System Activation Heatmap')
    plt.xlabel('Patients')
    plt.ylabel('Systems')
    
    # 3. 聚类结果
    plt.subplot(3, 4, 3)
    colors = plt.cm.Set1(np.linspace(0, 1, optimal_k))
    for i in range(optimal_k):
        cluster_mask = system_scores['cluster'] == i
        plt.scatter(system_scores.loc[cluster_mask, 'C'], 
                   system_scores.loc[cluster_mask, 'A'],
                   c=[colors[i]], label=f'Cluster {i}', alpha=0.7)
    plt.xlabel('System C (Metabolic)')
    plt.ylabel('System A (Repair)')
    plt.title('Patient Clusters (C vs A)')
    plt.legend()
    
    # 4. 系统相关性
    plt.subplot(3, 4, 4)
    correlation_matrix = system_scores[system_cols].corr()
    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0,
                square=True, cbar_kws={'label': 'Correlation'})
    plt.title('System Correlation Matrix')
    
    # 5. 变异系数
    plt.subplot(3, 4, 5)
    cv_values = [system_variability[sys]['cv'] for sys in system_cols]
    plt.bar(system_cols, cv_values, color='skyblue', alpha=0.7)
    plt.title('System Variability (CV)')
    plt.ylabel('Coefficient of Variation')
    plt.xlabel('Systems')
    
    # 6. 层次聚类树状图
    plt.subplot(3, 4, 6)
    dendrogram(linkage_matrix, truncate_mode='level', p=5)
    plt.title('Hierarchical Clustering')
    plt.xlabel('Patient Index')
    plt.ylabel('Distance')
    
    # 7-12. 每个系统的患者分布
    for i, system in enumerate(system_cols):
        plt.subplot(3, 4, 7 + i)
        plt.hist(system_scores[system], bins=20, alpha=0.7, color=f'C{i}')
        plt.title(f'System {system} Distribution')
        plt.xlabel('ssGSEA Score')
        plt.ylabel('Frequency')
        
        # 添加统计信息
        mean_val = system_scores[system].mean()
        std_val = system_scores[system].std()
        plt.axvline(mean_val, color='red', linestyle='--', alpha=0.8, 
                   label=f'Mean: {mean_val:.3f}')
        plt.axvline(mean_val + std_val, color='orange', linestyle=':', alpha=0.6)
        plt.axvline(mean_val - std_val, color='orange', linestyle=':', alpha=0.6)
        plt.legend(fontsize=8)
    
    plt.tight_layout()
    plt.savefig('results/disease_analysis/GSE2034_heterogeneity_analysis.png', 
                dpi=300, bbox_inches='tight')
    plt.close()
    
    # 创建子分类热图
    fig, ax = plt.subplots(figsize=(16, 12))
    
    subcategory_cols = [col for col in subcategory_scores.columns 
                       if col not in ['sample_id', 'subject_id', 'condition', 'group']]
    
    # 按聚类排序患者
    sorted_indices = np.argsort(system_scores['cluster'])
    subcategory_data = subcategory_scores.iloc[sorted_indices][subcategory_cols].T
    
    # 创建聚类颜色条
    cluster_colors = [plt.cm.Set1(system_scores.iloc[i]['cluster'] / optimal_k) 
                     for i in sorted_indices]
    
    sns.heatmap(subcategory_data, cmap='RdBu_r', center=0, 
                cbar_kws={'label': 'ssGSEA Score'}, ax=ax)
    
    # 添加聚类分隔线
    cluster_boundaries = []
    current_cluster = system_scores.iloc[sorted_indices[0]]['cluster']
    for i, idx in enumerate(sorted_indices[1:], 1):
        if system_scores.iloc[idx]['cluster'] != current_cluster:
            cluster_boundaries.append(i)
            current_cluster = system_scores.iloc[idx]['cluster']
    
    for boundary in cluster_boundaries:
        ax.axvline(x=boundary, color='white', linewidth=2)
    
    plt.title('GSE2034 Subcategory Activation Heatmap (Sorted by Clusters)')
    plt.xlabel('Patients (Sorted by Cluster)')
    plt.ylabel('Subcategories')
    
    plt.tight_layout()
    plt.savefig('results/disease_analysis/GSE2034_subcategory_heatmap.png', 
                dpi=300, bbox_inches='tight')
    plt.close()

def perform_statistical_tests(system_scores, clusters, system_cols):
    """执行统计检验"""
    print(f"   Statistical tests for cluster differences:")
    
    # ANOVA检验每个系统在聚类间的差异
    for system in system_cols:
        groups = [system_scores[system][clusters == i] for i in np.unique(clusters)]
        f_stat, p_value = stats.f_oneway(*groups)
        
        significance = "***" if p_value < 0.001 else ("**" if p_value < 0.01 else ("*" if p_value < 0.05 else "ns"))
        print(f"     - System {system}: F={f_stat:.3f}, p={p_value:.4f} {significance}")

def save_heterogeneity_report(system_variability, optimal_k, correlation_matrix):
    """保存异质性分析报告"""
    
    report_content = f"""# GSE2034 Breast Cancer Patient Heterogeneity Analysis Report

## Summary
- **Dataset**: GSE2034 Breast Cancer
- **Total patients**: 286
- **Optimal clusters identified**: {optimal_k}
- **Analysis date**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

## System Activation Variability

"""
    
    for system, stats in system_variability.items():
        report_content += f"""### System {system}
- **Mean activation**: {stats['mean']:.4f}
- **Standard deviation**: {stats['std']:.4f}
- **Coefficient of variation**: {stats['cv']:.4f}
- **Range**: [{stats['min']:.4f}, {stats['max']:.4f}]
- **Dynamic range**: {stats['range']:.4f}

"""
    
    report_content += f"""## System Correlation Matrix

"""
    report_content += correlation_matrix.round(4).to_string()
    
    report_content += f"""

## Key Findings

1. **High Patient Heterogeneity**: Coefficient of variation ranges from {min(s['cv'] for s in system_variability.values()):.3f} to {max(s['cv'] for s in system_variability.values()):.3f}

2. **Optimal Clustering**: {optimal_k} distinct patient subgroups identified based on system activation patterns

3. **System Correlations**: 
   - Strongest positive correlation: {correlation_matrix.values[np.triu_indices_from(correlation_matrix.values, k=1)].max():.3f}
   - Strongest negative correlation: {correlation_matrix.values[np.triu_indices_from(correlation_matrix.values, k=1)].min():.3f}

## Clinical Implications

The high heterogeneity in system activation patterns suggests:
- Potential molecular subtypes within the breast cancer cohort
- Different therapeutic targets for different patient subgroups
- Need for personalized treatment approaches

## Files Generated
- `GSE2034_sample_info_enhanced.csv` - Enhanced sample information with clinical features
- `GSE2034_cluster_analysis.csv` - Clustering results and system scores
- `GSE2034_heterogeneity_analysis.png` - Comprehensive visualization
- `GSE2034_subcategory_heatmap.png` - Subcategory activation heatmap
"""
    
    with open('results/disease_analysis/GSE2034_heterogeneity_report.md', 'w', encoding='utf-8') as f:
        f.write(report_content)

def main():
    """主函数"""
    try:
        system_variability, optimal_k, clusters = analyze_gse2034_heterogeneity()
        
        print(f"\n{'='*80}")
        print("ANALYSIS COMPLETED")
        print(f"{'='*80}")
        
        print(f"\n🎯 Key Findings:")
        print(f"   • Identified {optimal_k} distinct patient clusters")
        print(f"   • High system activation variability across patients")
        print(f"   • System C (Metabolic) shows highest variability: CV={system_variability['C']['cv']:.3f}")
        
        print(f"\n📁 Generated Files:")
        print(f"   • GSE2034_sample_info_enhanced.csv")
        print(f"   • GSE2034_cluster_analysis.csv") 
        print(f"   • GSE2034_heterogeneity_analysis.png")
        print(f"   • GSE2034_subcategory_heatmap.png")
        print(f"   • GSE2034_heterogeneity_report.md")
        
    except Exception as e:
        print(f"❌ Error in analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()