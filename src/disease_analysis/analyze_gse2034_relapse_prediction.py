#!/usr/bin/env python3
"""
重新分析GSE2034乳腺癌数据集：按骨转移复发风险分组
评估五大系统和14个子分类的预测价值
"""

import pandas as pd
import numpy as np
from scipy import stats
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import RandomForestClassifier
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

def analyze_breast_cancer_relapse_prediction():
    """分析乳腺癌复发预测"""
    
    print("="*80)
    print("GSE2034 BREAST CANCER RELAPSE PREDICTION ANALYSIS")
    print("Bone Metastasis Risk Stratification")
    print("="*80)
    
    # 1. 加载和处理数据
    print(f"\n📊 Loading and processing data...")
    system_data, subcategory_data, relapse_data = load_and_process_data()
    
    # 2. 描述性统计
    print(f"\n📈 Descriptive statistics...")
    descriptive_stats = generate_descriptive_stats(relapse_data)
    
    # 3. 系统级别分析
    print(f"\n🔍 System-level analysis...")
    system_analysis = analyze_system_differences(system_data, relapse_data)
    
    # 4. 子分类级别分析
    print(f"\n🔬 Subcategory-level analysis...")
    subcategory_analysis = analyze_subcategory_differences(subcategory_data, relapse_data)
    
    # 5. 预测性能评估
    print(f"\n🎯 Predictive performance evaluation...")
    prediction_results = evaluate_prediction_performance(system_data, subcategory_data, relapse_data)
    
    # 6. 特征重要性分析
    print(f"\n⭐ Feature importance analysis...")
    feature_importance = analyze_feature_importance(system_data, subcategory_data, relapse_data)
    
    # 7. 生成综合报告
    print(f"\n📝 Generating comprehensive report...")
    comprehensive_report = generate_comprehensive_report(
        descriptive_stats, system_analysis, subcategory_analysis, 
        prediction_results, feature_importance
    )
    
    # 8. 保存结果
    print(f"\n💾 Saving results...")
    save_analysis_results(
        descriptive_stats, system_analysis, subcategory_analysis,
        prediction_results, feature_importance, comprehensive_report
    )
    
    return {
        'descriptive_stats': descriptive_stats,
        'system_analysis': system_analysis,
        'subcategory_analysis': subcategory_analysis,
        'prediction_results': prediction_results,
        'feature_importance': feature_importance,
        'comprehensive_report': comprehensive_report
    }

def load_and_process_data():
    """加载和处理数据"""
    
    # 加载系统得分
    system_data = pd.read_csv('results/disease_analysis/GSE2034-乳腺癌/clean_data/GSE2034_system_scores.csv')
    
    # 加载子分类得分
    subcategory_data = pd.read_csv('results/disease_analysis/GSE2034-乳腺癌/clean_data/GSE2034_subcategory_scores.csv')
    
    # 加载临床特征
    clinical_data = pd.read_csv('results/disease_analysis/GSE2034-乳腺癌/clean_data/GSE2034_clinical_features.csv')
    
    # 处理复发标签
    clinical_data['bone_relapse'] = clinical_data['survival_outcome'].str.extract(r'(\d+)$').astype(int)
    clinical_data['relapse_group'] = clinical_data['bone_relapse'].map({0: 'No_Relapse', 1: 'Relapse'})
    
    # 合并数据
    relapse_data = system_data.merge(clinical_data[['sample_id', 'bone_relapse', 'relapse_group']], on='sample_id')
    
    print(f"   • System data: {system_data.shape}")
    print(f"   • Subcategory data: {subcategory_data.shape}")
    print(f"   • Clinical data: {clinical_data.shape}")
    print(f"   • Merged data: {relapse_data.shape}")
    
    return system_data, subcategory_data, relapse_data

def generate_descriptive_stats(relapse_data):
    """生成描述性统计"""
    
    # 复发率统计
    relapse_counts = relapse_data['relapse_group'].value_counts()
    relapse_rate = relapse_data['bone_relapse'].mean()
    
    print(f"   • Total patients: {len(relapse_data)}")
    print(f"   • Bone relapse rate: {relapse_rate:.1%} ({relapse_counts['Relapse']}/{len(relapse_data)})")
    print(f"   • No relapse: {relapse_counts['No_Relapse']} patients")
    print(f"   • Relapse: {relapse_counts['Relapse']} patients")
    
    return {
        'total_patients': len(relapse_data),
        'relapse_rate': relapse_rate,
        'relapse_counts': relapse_counts.to_dict(),
        'no_relapse_count': relapse_counts['No_Relapse'],
        'relapse_count': relapse_counts['Relapse']
    }

def analyze_system_differences(system_data, relapse_data):
    """分析系统级别差异"""
    
    system_cols = ['A', 'B', 'C', 'D', 'E']
    
    # 合并数据
    merged_data = system_data.merge(relapse_data[['sample_id', 'bone_relapse', 'relapse_group']], on='sample_id')
    
    # 按组分析
    no_relapse_data = merged_data[merged_data['relapse_group'] == 'No_Relapse']
    relapse_data_group = merged_data[merged_data['relapse_group'] == 'Relapse']
    
    system_differences = {}
    
    for system in system_cols:
        no_relapse_values = no_relapse_data[system]
        relapse_values = relapse_data_group[system]
        
        # t检验
        t_stat, p_value = stats.ttest_ind(relapse_values, no_relapse_values)
        
        # 效应量 (Cohen's d)
        pooled_std = np.sqrt(((len(relapse_values) - 1) * relapse_values.var() + 
                             (len(no_relapse_values) - 1) * no_relapse_values.var()) / 
                            (len(relapse_values) + len(no_relapse_values) - 2))
        cohens_d = (relapse_values.mean() - no_relapse_values.mean()) / pooled_std
        
        # AUC
        y_true = merged_data['bone_relapse']
        y_score = merged_data[system]
        auc = roc_auc_score(y_true, y_score)
        
        system_differences[system] = {
            'no_relapse_mean': no_relapse_values.mean(),
            'no_relapse_std': no_relapse_values.std(),
            'relapse_mean': relapse_values.mean(),
            'relapse_std': relapse_values.std(),
            'difference': relapse_values.mean() - no_relapse_values.mean(),
            'fold_change': relapse_values.mean() / no_relapse_values.mean() if no_relapse_values.mean() > 0 else np.inf,
            't_statistic': t_stat,
            'p_value': p_value,
            'cohens_d': cohens_d,
            'auc': auc,
            'significant': p_value < 0.05,
            'effect_size_interpretation': interpret_effect_size(abs(cohens_d))
        }
    
    # 排序结果
    sorted_systems = sorted(system_differences.items(), key=lambda x: abs(x[1]['cohens_d']), reverse=True)
    
    print(f"   • System differences analysis completed")
    print(f"   • Top 3 discriminative systems:")
    for i, (system, data) in enumerate(sorted_systems[:3]):
        print(f"     {i+1}. System {system}: Cohen's d = {data['cohens_d']:.3f}, AUC = {data['auc']:.3f}, p = {data['p_value']:.4f}")
    
    return system_differences

def analyze_subcategory_differences(subcategory_data, relapse_data):
    """分析子分类级别差异"""
    
    subcategory_cols = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'E1', 'E2']
    
    # 合并数据
    merged_data = subcategory_data.merge(relapse_data[['sample_id', 'bone_relapse', 'relapse_group']], on='sample_id')
    
    # 按组分析
    no_relapse_data = merged_data[merged_data['relapse_group'] == 'No_Relapse']
    relapse_data_group = merged_data[merged_data['relapse_group'] == 'Relapse']
    
    subcategory_differences = {}
    
    for subcat in subcategory_cols:
        if subcat in merged_data.columns:
            no_relapse_values = no_relapse_data[subcat]
            relapse_values = relapse_data_group[subcat]
            
            # t检验
            t_stat, p_value = stats.ttest_ind(relapse_values, no_relapse_values)
            
            # 效应量 (Cohen's d)
            pooled_std = np.sqrt(((len(relapse_values) - 1) * relapse_values.var() + 
                                 (len(no_relapse_values) - 1) * no_relapse_values.var()) / 
                                (len(relapse_values) + len(no_relapse_values) - 2))
            cohens_d = (relapse_values.mean() - no_relapse_values.mean()) / pooled_std
            
            # AUC
            y_true = merged_data['bone_relapse']
            y_score = merged_data[subcat]
            auc = roc_auc_score(y_true, y_score)
            
            subcategory_differences[subcat] = {
                'system': subcat[0],
                'no_relapse_mean': no_relapse_values.mean(),
                'no_relapse_std': no_relapse_values.std(),
                'relapse_mean': relapse_values.mean(),
                'relapse_std': relapse_values.std(),
                'difference': relapse_values.mean() - no_relapse_values.mean(),
                'fold_change': relapse_values.mean() / no_relapse_values.mean() if no_relapse_values.mean() > 0 else np.inf,
                't_statistic': t_stat,
                'p_value': p_value,
                'cohens_d': cohens_d,
                'auc': auc,
                'significant': p_value < 0.05,
                'effect_size_interpretation': interpret_effect_size(abs(cohens_d))
            }
    
    # 排序结果
    sorted_subcategories = sorted(subcategory_differences.items(), key=lambda x: abs(x[1]['cohens_d']), reverse=True)
    
    print(f"   • Subcategory differences analysis completed")
    print(f"   • Top 5 discriminative subcategories:")
    for i, (subcat, data) in enumerate(sorted_subcategories[:5]):
        print(f"     {i+1}. {subcat}: Cohen's d = {data['cohens_d']:.3f}, AUC = {data['auc']:.3f}, p = {data['p_value']:.4f}")
    
    return subcategory_differences

def evaluate_prediction_performance(system_data, subcategory_data, relapse_data):
    """评估预测性能"""
    
    # 准备数据
    system_cols = ['A', 'B', 'C', 'D', 'E']
    subcategory_cols = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'E1', 'E2']
    
    # 合并数据
    full_data = system_data.merge(subcategory_data, on='sample_id')
    full_data = full_data.merge(relapse_data[['sample_id', 'bone_relapse']], on='sample_id')
    
    # 准备特征和标签
    X_systems = full_data[system_cols]
    X_subcategories = full_data[subcategory_cols]
    X_combined = full_data[system_cols + subcategory_cols]
    y = full_data['bone_relapse']
    
    # 评估不同特征组合的性能
    results = {}
    
    # 系统级别预测
    rf_systems = RandomForestClassifier(n_estimators=100, random_state=42)
    cv_scores_systems = cross_val_score(rf_systems, X_systems, y, cv=5, scoring='roc_auc')
    results['systems_only'] = {
        'mean_auc': cv_scores_systems.mean(),
        'std_auc': cv_scores_systems.std(),
        'feature_count': len(system_cols)
    }
    
    # 子分类级别预测
    rf_subcategories = RandomForestClassifier(n_estimators=100, random_state=42)
    cv_scores_subcategories = cross_val_score(rf_subcategories, X_subcategories, y, cv=5, scoring='roc_auc')
    results['subcategories_only'] = {
        'mean_auc': cv_scores_subcategories.mean(),
        'std_auc': cv_scores_subcategories.std(),
        'feature_count': len(subcategory_cols)
    }
    
    # 组合特征预测
    rf_combined = RandomForestClassifier(n_estimators=100, random_state=42)
    cv_scores_combined = cross_val_score(rf_combined, X_combined, y, cv=5, scoring='roc_auc')
    results['combined'] = {
        'mean_auc': cv_scores_combined.mean(),
        'std_auc': cv_scores_combined.std(),
        'feature_count': len(system_cols) + len(subcategory_cols)
    }
    
    print(f"   • Prediction performance evaluation completed")
    print(f"   • Systems only: AUC = {results['systems_only']['mean_auc']:.3f} ± {results['systems_only']['std_auc']:.3f}")
    print(f"   • Subcategories only: AUC = {results['subcategories_only']['mean_auc']:.3f} ± {results['subcategories_only']['std_auc']:.3f}")
    print(f"   • Combined: AUC = {results['combined']['mean_auc']:.3f} ± {results['combined']['std_auc']:.3f}")
    
    return results

def analyze_feature_importance(system_data, subcategory_data, relapse_data):
    """分析特征重要性"""
    
    # 合并数据
    system_cols = ['A', 'B', 'C', 'D', 'E']
    subcategory_cols = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'E1', 'E2']
    
    full_data = system_data.merge(subcategory_data, on='sample_id')
    full_data = full_data.merge(relapse_data[['sample_id', 'bone_relapse']], on='sample_id')
    
    # 训练随机森林模型
    X = full_data[system_cols + subcategory_cols]
    y = full_data['bone_relapse']
    
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X, y)
    
    # 获取特征重要性
    feature_importance = pd.DataFrame({
        'feature': system_cols + subcategory_cols,
        'importance': rf.feature_importances_
    }).sort_values('importance', ascending=False)
    
    # 分别统计系统和子分类的重要性
    system_importance = feature_importance[feature_importance['feature'].isin(system_cols)]
    subcategory_importance = feature_importance[feature_importance['feature'].isin(subcategory_cols)]
    
    print(f"   • Feature importance analysis completed")
    print(f"   • Top 5 most important features:")
    for i, row in feature_importance.head().iterrows():
        print(f"     {i+1}. {row['feature']}: {row['importance']:.4f}")
    
    return {
        'all_features': feature_importance,
        'system_features': system_importance,
        'subcategory_features': subcategory_importance,
        'top_system': system_importance.iloc[0]['feature'] if len(system_importance) > 0 else None,
        'top_subcategory': subcategory_importance.iloc[0]['feature'] if len(subcategory_importance) > 0 else None
    }

def interpret_effect_size(cohens_d):
    """解释效应量大小"""
    if cohens_d < 0.2:
        return "Negligible"
    elif cohens_d < 0.5:
        return "Small"
    elif cohens_d < 0.8:
        return "Medium"
    else:
        return "Large"

def generate_comprehensive_report(descriptive_stats, system_analysis, subcategory_analysis, 
                                prediction_results, feature_importance):
    """生成综合报告"""
    
    report = {
        'executive_summary': '',
        'key_findings': [],
        'system_insights': '',
        'subcategory_insights': '',
        'prediction_performance': '',
        'clinical_implications': '',
        'recommendation': ''
    }
    
    # 执行摘要
    relapse_rate = descriptive_stats['relapse_rate']
    best_auc = max([pred['mean_auc'] for pred in prediction_results.values()])
    
    report['executive_summary'] = (
        f"GSE2034乳腺癌数据集包含{descriptive_stats['total_patients']}名患者，"
        f"骨转移复发率为{relapse_rate:.1%}。五大分类系统的最佳预测性能AUC为{best_auc:.3f}。"
    )
    
    # 系统洞察
    best_system = max(system_analysis.items(), key=lambda x: abs(x[1]['cohens_d']))
    system_name, system_data = best_system
    
    if abs(system_data['cohens_d']) > 0.2:  # 至少小效应量
        report['system_insights'] = (
            f"系统{system_name}显示最强的复发预测能力，"
            f"效应量为{system_data['cohens_d']:.3f}（{system_data['effect_size_interpretation']}），"
            f"AUC为{system_data['auc']:.3f}。"
        )
        report['key_findings'].append(f"系统{system_name}具有复发预测价值")
    else:
        report['system_insights'] = "系统级别特征对复发预测的区分能力有限。"
    
    # 子分类洞察
    best_subcat = max(subcategory_analysis.items(), key=lambda x: abs(x[1]['cohens_d']))
    subcat_name, subcat_data = best_subcat
    
    if abs(subcat_data['cohens_d']) > 0.2:  # 至少小效应量
        report['subcategory_insights'] = (
            f"子分类{subcat_name}显示最强的复发预测能力，"
            f"效应量为{subcat_data['cohens_d']:.3f}（{subcat_data['effect_size_interpretation']}），"
            f"AUC为{subcat_data['auc']:.3f}。"
        )
        report['key_findings'].append(f"子分类{subcat_name}具有复发预测价值")
    else:
        report['subcategory_insights'] = "子分类级别特征对复发预测的区分能力有限。"
    
    # 预测性能
    best_model = max(prediction_results.items(), key=lambda x: x[1]['mean_auc'])
    model_name, model_data = best_model
    
    report['prediction_performance'] = (
        f"最佳预测模型为{model_name}，交叉验证AUC为{model_data['mean_auc']:.3f}±{model_data['std_auc']:.3f}。"
    )
    
    # 临床意义和推荐
    if best_auc > 0.7:
        report['clinical_implications'] = (
            "五大分类系统显示出良好的乳腺癌骨转移复发预测能力，"
            "可作为临床风险分层的辅助工具。"
        )
        report['recommendation'] = "推荐将此案例纳入论文，展示五大分类的临床预测价值。"
        report['key_findings'].append("具有临床应用潜力")
    elif best_auc > 0.6:
        report['clinical_implications'] = (
            "五大分类系统对乳腺癌骨转移复发具有一定的预测能力，"
            "但可能需要与其他临床指标结合使用。"
        )
        report['recommendation'] = "可考虑纳入论文，但需要谨慎解释预测性能的局限性。"
        report['key_findings'].append("中等预测能力")
    else:
        report['clinical_implications'] = (
            "五大分类系统对乳腺癌骨转移复发的预测能力有限，"
            "可能不适合作为独立的预测工具。"
        )
        report['recommendation'] = "不推荐将此案例作为主要验证案例纳入论文。"
        report['key_findings'].append("预测能力有限")
    
    return report

def save_analysis_results(descriptive_stats, system_analysis, subcategory_analysis,
                         prediction_results, feature_importance, comprehensive_report):
    """保存分析结果"""
    
    output_dir = 'results/disease_analysis/GSE2034-乳腺癌/analysis_results/'
    
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存系统差异分析
    system_df = pd.DataFrame.from_dict(system_analysis, orient='index')
    system_df.to_csv(f'{output_dir}relapse_system_differences.csv')
    
    # 保存子分类差异分析
    subcategory_df = pd.DataFrame.from_dict(subcategory_analysis, orient='index')
    subcategory_df.to_csv(f'{output_dir}relapse_subcategory_differences.csv')
    
    # 保存预测性能结果
    prediction_df = pd.DataFrame.from_dict(prediction_results, orient='index')
    prediction_df.to_csv(f'{output_dir}relapse_prediction_performance.csv')
    
    # 保存特征重要性
    feature_importance['all_features'].to_csv(f'{output_dir}relapse_feature_importance.csv', index=False)
    
    # 保存描述性统计
    with open(f'{output_dir}relapse_descriptive_stats.txt', 'w', encoding='utf-8') as f:
        f.write("GSE2034乳腺癌骨转移复发描述性统计\n")
        f.write("="*50 + "\n\n")
        f.write(f"总患者数: {descriptive_stats['total_patients']}\n")
        f.write(f"骨转移复发率: {descriptive_stats['relapse_rate']:.1%}\n")
        f.write(f"无复发患者: {descriptive_stats['no_relapse_count']}\n")
        f.write(f"复发患者: {descriptive_stats['relapse_count']}\n")
    
    # 保存综合报告
    with open(f'{output_dir}relapse_comprehensive_report.txt', 'w', encoding='utf-8') as f:
        f.write("GSE2034乳腺癌骨转移复发预测综合分析报告\n")
        f.write("="*60 + "\n\n")
        
        f.write("1. 执行摘要:\n")
        f.write(comprehensive_report['executive_summary'] + "\n\n")
        
        f.write("2. 系统级别洞察:\n")
        f.write(comprehensive_report['system_insights'] + "\n\n")
        
        f.write("3. 子分类级别洞察:\n")
        f.write(comprehensive_report['subcategory_insights'] + "\n\n")
        
        f.write("4. 预测性能:\n")
        f.write(comprehensive_report['prediction_performance'] + "\n\n")
        
        f.write("5. 临床意义:\n")
        f.write(comprehensive_report['clinical_implications'] + "\n\n")
        
        f.write("6. 推荐:\n")
        f.write(comprehensive_report['recommendation'] + "\n\n")
        
        f.write("7. 关键发现:\n")
        for finding in comprehensive_report['key_findings']:
            f.write(f"   • {finding}\n")
    
    print(f"   ✅ All analysis results saved to {output_dir}")

def main():
    """主函数"""
    try:
        results = analyze_breast_cancer_relapse_prediction()
        
        print(f"\n{'='*80}")
        print("GSE2034 BREAST CANCER RELAPSE PREDICTION ANALYSIS COMPLETED")
        print(f"{'='*80}")
        
        # 显示关键结果
        descriptive_stats = results['descriptive_stats']
        prediction_results = results['prediction_results']
        report = results['comprehensive_report']
        
        print(f"\n🎯 Key Results:")
        print(f"   • Total patients: {descriptive_stats['total_patients']}")
        print(f"   • Relapse rate: {descriptive_stats['relapse_rate']:.1%}")
        
        best_auc = max([pred['mean_auc'] for pred in prediction_results.values()])
        print(f"   • Best prediction AUC: {best_auc:.3f}")
        
        print(f"\n📝 Key Findings:")
        for finding in report['key_findings']:
            print(f"   • {finding}")
        
        print(f"\n💡 Recommendation:")
        print(f"   {report['recommendation']}")
        
    except Exception as e:
        print(f"❌ Error in analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()