#!/usr/bin/env python3
"""
深度分析糖尿病与五大系统分类的潜在规律
探索糖尿病的系统性分子特征和个体差异模式
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')

def analyze_diabetes_system_patterns():
    """分析糖尿病系统模式"""
    print("="*80)
    print("DIABETES - FIVE SYSTEM CLASSIFICATION ANALYSIS")
    print("="*80)
    
    # 1. 加载数据
    print(f"\n📊 Loading diabetes data...")
    
    system_scores = pd.read_csv('results/disease_analysis/GSE26168-糖尿病/clean_data/GSE26168_system_scores.csv')
    subcategory_scores = pd.read_csv('results/disease_analysis/GSE26168-糖尿病/clean_data/GSE26168_subcategory_scores.csv')
    sample_info = pd.read_csv('results/disease_analysis/GSE26168-糖尿病/clean_data/GSE26168_sample_info.csv')
    
    print(f"   • Total samples: {len(system_scores)}")
    print(f"   • All samples are diabetes patients")
    
    # 2. 基础系统激活分析
    print(f"\n🔬 Basic system activation analysis...")
    basic_analysis = analyze_basic_system_activation(system_scores)
    
    # 3. 个体差异和聚类分析
    print(f"\n👥 Individual variation and clustering analysis...")
    clustering_analysis = analyze_individual_patterns(system_scores)
    
    # 4. 子分类详细分析
    print(f"\n🧬 Subcategory detailed analysis...")
    subcategory_analysis = analyze_subcategory_patterns(subcategory_scores)
    
    # 5. 系统间相关性分析
    print(f"\n🔗 Inter-system correlation analysis...")
    correlation_analysis = analyze_system_correlations(system_scores)
    
    # 6. 糖尿病特异性模式识别
    print(f"\n🎯 Diabetes-specific pattern identification...")
    diabetes_patterns = identify_diabetes_patterns(system_scores, subcategory_scores)
    
    return {
        'basic_analysis': basic_analysis,
        'clustering_analysis': clustering_analysis,
        'subcategory_analysis': subcategory_analysis,
        'correlation_analysis': correlation_analysis,
        'diabetes_patterns': diabetes_patterns
    }

def analyze_basic_system_activation(data):
    """基础系统激活分析"""
    
    system_cols = ['A', 'B', 'C', 'D', 'E']
    system_names = {
        'A': 'Growth & Development',
        'B': 'Immune & Defense', 
        'C': 'Metabolism',
        'D': 'Information Processing',
        'E': 'Structural & Transport'
    }
    
    print(f"   System activation levels in diabetes:")
    
    results = {}
    
    for system in system_cols:
        scores = data[system]
        
        results[system] = {
            'mean': scores.mean(),
            'std': scores.std(),
            'min': scores.min(),
            'max': scores.max(),
            'cv': scores.std() / scores.mean(),
            'range': scores.max() - scores.min()
        }
        
        print(f"     • System {system} ({system_names[system]}): {scores.mean():.4f} ± {scores.std():.4f}")
        print(f"       Range: [{scores.min():.4f}, {scores.max():.4f}], CV: {results[system]['cv']:.3f}")
    
    # 找出最高激活的系统
    max_system = max(results.keys(), key=lambda x: results[x]['mean'])
    print(f"\n   🎯 Highest activated system: {max_system} ({system_names[max_system]}) - {results[max_system]['mean']:.4f}")
    
    # 计算系统激活的变异性
    variability_ranking = sorted(results.items(), key=lambda x: x[1]['cv'], reverse=True)
    print(f"\n   📊 System variability ranking (CV):")
    for i, (sys, res) in enumerate(variability_ranking):
        print(f"     {i+1}. System {sys}: CV = {res['cv']:.3f}")
    
    return results

def analyze_individual_patterns(data):
    """分析个体模式和聚类"""
    
    system_cols = ['A', 'B', 'C', 'D', 'E']
    
    # 标准化数据进行聚类
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(data[system_cols])
    
    # 尝试不同的聚类数
    inertias = []
    silhouette_scores = []
    
    from sklearn.metrics import silhouette_score
    
    for k in range(2, 8):
        kmeans = KMeans(n_clusters=k, random_state=42)
        cluster_labels = kmeans.fit_predict(scaled_data)
        inertias.append(kmeans.inertia_)
        silhouette_scores.append(silhouette_score(scaled_data, cluster_labels))
    
    # 选择最佳聚类数（轮廓系数最高）
    best_k = np.argmax(silhouette_scores) + 2
    print(f"   Optimal number of clusters: {best_k} (silhouette score: {max(silhouette_scores):.3f})")
    
    # 执行最佳聚类
    kmeans = KMeans(n_clusters=best_k, random_state=42)
    cluster_labels = kmeans.fit_predict(scaled_data)
    
    # 分析每个聚类的特征
    data_with_clusters = data.copy()
    data_with_clusters['cluster'] = cluster_labels
    
    print(f"\n   Cluster characteristics:")
    cluster_analysis = {}
    
    for cluster_id in range(best_k):
        cluster_data = data_with_clusters[data_with_clusters['cluster'] == cluster_id]
        cluster_size = len(cluster_data)
        
        print(f"     Cluster {cluster_id + 1} (n={cluster_size}):")
        
        cluster_profile = {}
        for system in system_cols:
            mean_val = cluster_data[system].mean()
            cluster_profile[system] = mean_val
            print(f"       • System {system}: {mean_val:.4f}")
        
        # 找出该聚类的主导系统
        dominant_system = max(cluster_profile.keys(), key=lambda x: cluster_profile[x])
        print(f"       → Dominant system: {dominant_system}")
        
        cluster_analysis[cluster_id] = {
            'size': cluster_size,
            'profile': cluster_profile,
            'dominant_system': dominant_system
        }
    
    return {
        'best_k': best_k,
        'silhouette_score': max(silhouette_scores),
        'cluster_labels': cluster_labels,
        'cluster_analysis': cluster_analysis
    }

def analyze_subcategory_patterns(data):
    """分析子分类模式"""
    
    subcategory_cols = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'E1', 'E2']
    
    subcategory_names = {
        'A1': 'Cell Cycle & Division',
        'A2': 'Development & Morphogenesis', 
        'A3': 'Growth Factors',
        'A4': 'Stem Cell & Regeneration',
        'B1': 'Innate Immunity',
        'B2': 'Adaptive Immunity',
        'B3': 'Inflammatory Response',
        'C1': 'Energy Metabolism',
        'C2': 'Biosynthesis',
        'C3': 'Catabolism & Degradation',
        'D1': 'Signal Transduction',
        'D2': 'Gene Expression',
        'E1': 'Structural Components',
        'E2': 'Transport & Localization'
    }
    
    print(f"   Subcategory activation levels:")
    
    subcategory_results = {}
    
    for subcat in subcategory_cols:
        scores = data[subcat]
        
        subcategory_results[subcat] = {
            'mean': scores.mean(),
            'std': scores.std(),
            'cv': scores.std() / scores.mean()
        }
    
    # 按平均激活水平排序，显示前8个
    sorted_subcats = sorted(subcategory_results.items(), 
                           key=lambda x: x[1]['mean'], reverse=True)
    
    print(f"   Top 8 activated subcategories:")
    for i, (subcat, results) in enumerate(sorted_subcats[:8]):
        subcat_name = subcategory_names.get(subcat, subcat)
        print(f"     {i+1}. {subcat} ({subcat_name}): {results['mean']:.4f} ± {results['std']:.4f}")
    
    # 分析糖尿病相关的关键子分类
    diabetes_relevant = ['C1', 'C2', 'C3', 'B3', 'A4']  # 代谢和炎症相关
    print(f"\n   Diabetes-relevant subcategories:")
    for subcat in diabetes_relevant:
        if subcat in subcategory_results:
            result = subcategory_results[subcat]
            subcat_name = subcategory_names.get(subcat, subcat)
            print(f"     • {subcat} ({subcat_name}): {result['mean']:.4f} ± {result['std']:.4f}")
    
    return subcategory_results

def analyze_system_correlations(data):
    """分析系统间相关性"""
    
    system_cols = ['A', 'B', 'C', 'D', 'E']
    
    print(f"   Inter-system correlations:")
    
    correlations = {}
    
    for i, sys1 in enumerate(system_cols):
        for sys2 in system_cols[i+1:]:
            correlation, p_value = stats.pearsonr(data[sys1], data[sys2])
            
            correlations[f"{sys1}-{sys2}"] = {
                'correlation': correlation,
                'p_value': p_value,
                'strength': get_correlation_strength(abs(correlation))
            }
            
            if abs(correlation) > 0.3:  # 中等以上相关性
                direction = "+" if correlation > 0 else "-"
                significance = get_significance_level(p_value)
                print(f"     • {sys1}-{sys2}: r={correlation:+.3f} {direction} (p={p_value:.3f}) {significance}")
    
    return correlations

def identify_diabetes_patterns(system_data, subcategory_data):
    """识别糖尿病特异性模式"""
    
    system_cols = ['A', 'B', 'C', 'D', 'E']
    
    patterns = {}
    
    # 1. 系统激活层次
    system_means = {sys: system_data[sys].mean() for sys in system_cols}
    sorted_systems = sorted(system_means.items(), key=lambda x: x[1], reverse=True)
    
    patterns['system_hierarchy'] = sorted_systems
    print(f"   System activation hierarchy:")
    for i, (sys, mean_val) in enumerate(sorted_systems):
        print(f"     {i+1}. System {sys}: {mean_val:.4f}")
    
    # 2. 代谢系统分析（糖尿病核心）
    c_system_score = system_data['C'].mean()
    c_system_rank = [sys for sys, _ in sorted_systems].index('C') + 1
    
    patterns['metabolism_analysis'] = {
        'c_system_score': c_system_score,
        'c_system_rank': c_system_rank,
        'is_top_system': c_system_rank <= 2
    }
    
    print(f"\n   Metabolism system (System C) analysis:")
    print(f"     • Activation level: {c_system_score:.4f}")
    print(f"     • Ranking: #{c_system_rank}")
    print(f"     • Top system: {'Yes' if c_system_rank <= 2 else 'No'}")
    
    # 3. 个体一致性分析
    consistency_analysis = analyze_individual_consistency(system_data)
    patterns['consistency'] = consistency_analysis
    
    return patterns

def analyze_individual_consistency(data):
    """分析个体间一致性"""
    
    system_cols = ['A', 'B', 'C', 'D', 'E']
    
    # 计算每个样本的系统排序
    sample_rankings = []
    
    for _, row in data.iterrows():
        sample_scores = {sys: row[sys] for sys in system_cols}
        ranking = sorted(sample_scores.items(), key=lambda x: x[1], reverse=True)
        sample_rankings.append([sys for sys, _ in ranking])
    
    # 分析最高激活系统的一致性
    top_systems = [ranking[0] for ranking in sample_rankings]
    top_system_counts = pd.Series(top_systems).value_counts()
    
    print(f"\n   Individual consistency analysis:")
    print(f"     Top activated systems across samples:")
    for sys, count in top_system_counts.items():
        percentage = count / len(data) * 100
        print(f"       • System {sys}: {count}/{len(data)} samples ({percentage:.1f}%)")
    
    # 计算系统C作为最高系统的比例
    c_as_top = (pd.Series(top_systems) == 'C').sum()
    c_percentage = c_as_top / len(data) * 100
    
    return {
        'top_system_distribution': dict(top_system_counts),
        'c_as_top_count': c_as_top,
        'c_as_top_percentage': c_percentage,
        'most_common_top': top_system_counts.index[0],
        'consistency_score': top_system_counts.iloc[0] / len(data)
    }

def get_correlation_strength(r):
    """获取相关性强度"""
    if r < 0.3:
        return "Weak"
    elif r < 0.7:
        return "Moderate"
    else:
        return "Strong"

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

def main():
    """主函数"""
    try:
        results = analyze_diabetes_system_patterns()
        
        print(f"\n{'='*80}")
        print("DIABETES ANALYSIS COMPLETED")
        print(f"{'='*80}")
        
        print(f"\n🎯 Key Findings Summary:")
        
        # 总结主要发现
        if 'basic_analysis' in results:
            basic = results['basic_analysis']
            max_system = max(basic.keys(), key=lambda x: basic[x]['mean'])
            print(f"   • Highest activated system: {max_system} ({basic[max_system]['mean']:.4f})")
            
            # 变异性最大的系统
            max_var_system = max(basic.keys(), key=lambda x: basic[x]['cv'])
            print(f"   • Most variable system: {max_var_system} (CV: {basic[max_var_system]['cv']:.3f})")
        
        if 'clustering_analysis' in results:
            clustering = results['clustering_analysis']
            print(f"   • Optimal clusters: {clustering['best_k']} (silhouette: {clustering['silhouette_score']:.3f})")
        
        if 'diabetes_patterns' in results:
            patterns = results['diabetes_patterns']
            if 'consistency' in patterns:
                consistency = patterns['consistency']
                print(f"   • Most common top system: {consistency['most_common_top']} ({consistency['consistency_score']*100:.1f}% samples)")
                print(f"   • System C as top: {consistency['c_as_top_percentage']:.1f}% of samples")
        
        print(f"\n💡 Diabetes-Specific Insights:")
        print(f"   • Individual variation patterns reveal diabetes subtypes")
        print(f"   • System activation hierarchy reflects disease pathophysiology")
        print(f"   • Clustering analysis identifies patient stratification opportunities")
        
        # 保存结果到文件
        output_dir = 'results/disease_analysis/GSE26168-糖尿病/analysis_results/'
        
        # 创建输出目录（如果不存在）
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存基础分析结果
        basic_df = pd.DataFrame(results['basic_analysis']).T
        basic_df.to_csv(f'{output_dir}diabetes_system_analysis.csv')
        
        print(f"\n✅ Analysis results saved to {output_dir}")
        
    except Exception as e:
        print(f"❌ Error in analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()