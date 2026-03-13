"""
自动确定最佳 PCA 成分数

对三个数据集（Wound Healing, Sepsis, Gaucher）分别测试不同的 PCA 成分数，
使用交叉验证找到最佳配置。

作者: AI Assistant
日期: 2025-12-03
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
import warnings
import os

warnings.filterwarnings('ignore')

# 设置随机种子
np.random.seed(42)

# 设置绘图样式
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.size'] = 11
plt.rcParams['figure.dpi'] = 300
sns.set_style("whitegrid")


def load_dataset(dataset_name, data_dir='数据/对比实验'):
    """
    加载数据集
    
    Args:
        dataset_name: 数据集名称
        data_dir: 数据目录
    
    Returns:
        go_scores: GO term 分数矩阵 (samples × GO terms)
        y: 标签
        label_names: 标签名称
    """
    print(f"\n{'='*80}")
    print(f"加载数据集: {dataset_name}")
    print(f"{'='*80}")
    
    # 加载样本信息
    sample_info = pd.read_csv(f'{data_dir}/{dataset_name}_sample_info.csv')
    print(f"  样本信息: {sample_info.shape}")
    print(f"  分组: {sample_info['group'].value_counts().to_dict()}")
    
    # 加载 GO 分数
    go_scores = pd.read_csv(f'{data_dir}/{dataset_name}_go_scores.csv')
    print(f"  GO 分数: {go_scores.shape}")
    
    # 提取特征和标签
    X = go_scores.drop('sample_id', axis=1).values
    
    # 编码标签
    le = LabelEncoder()
    y = le.fit_transform(sample_info['group'])
    label_names = le.classes_
    
    print(f"  特征矩阵: {X.shape}")
    print(f"  标签: {len(np.unique(y))} 类 - {list(label_names)}")
    
    return X, y, label_names


def analyze_pca_variance(X, dataset_name, max_components=200):
    """
    分析 PCA 解释方差
    
    Args:
        X: 特征矩阵
        dataset_name: 数据集名称
        max_components: 最大成分数
    
    Returns:
        pca: 拟合的 PCA 对象
        variance_info: 方差信息字典
    """
    print(f"\n📊 PCA 方差分析...")
    
    # 标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # PCA
    n_components = min(max_components, X.shape[0], X.shape[1])
    pca = PCA(n_components=n_components)
    pca.fit(X_scaled)
    
    # 计算累计解释方差
    explained_var = pca.explained_variance_ratio_
    cumsum_var = np.cumsum(explained_var)
    
    # 找到不同阈值对应的成分数
    thresholds = [0.70, 0.80, 0.85, 0.90, 0.95, 0.99]
    variance_info = {}
    
    print(f"\n  解释方差阈值分析:")
    for threshold in thresholds:
        n = np.argmax(cumsum_var >= threshold) + 1
        if n < len(cumsum_var):
            variance_info[f'{int(threshold*100)}%'] = n
            print(f"    {threshold:.0%} 方差: {n:3d} 个成分")
    
    # 打印前10个成分的方差
    print(f"\n  前10个主成分的解释方差:")
    for i in range(min(10, len(explained_var))):
        print(f"    PC{i+1:2d}: {explained_var[i]:.4f} ({explained_var[i]*100:.2f}%)")
    
    return pca, variance_info, scaler


def evaluate_pca_components(X, y, n_components_list, dataset_name):
    """
    使用交叉验证评估不同 PCA 成分数的性能
    
    Args:
        X: 特征矩阵
        y: 标签
        n_components_list: 要测试的成分数列表
        dataset_name: 数据集名称
    
    Returns:
        results_df: 结果 DataFrame
    """
    print(f"\n🎯 交叉验证评估...")
    
    # 标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 确定交叉验证折数
    min_class_count = min(np.bincount(y))
    cv_folds = min(5, min_class_count)
    print(f"  使用 {cv_folds}-Fold 交叉验证")
    
    # 是否是二分类
    is_binary = len(np.unique(y)) == 2
    
    results = []
    
    for n in n_components_list:
        if n > min(X.shape):
            print(f"  ⚠️  跳过 n={n} (超过数据维度)")
            continue
        
        print(f"  测试 n={n:3d}...", end=' ')
        
        # PCA 降维
        pca = PCA(n_components=n, random_state=42)
        X_pca = pca.fit_transform(X_scaled)
        
        # 创建分类器
        if is_binary:
            clf = LogisticRegression(random_state=42, max_iter=1000)
        else:
            clf = LogisticRegression(
                random_state=42, 
                max_iter=1000,
                multi_class='multinomial',
                solver='lbfgs'
            )
        
        # 交叉验证
        cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        
        # 计算多个指标
        acc_scores = cross_val_score(clf, X_pca, y, cv=cv, scoring='accuracy')
        f1_scores = cross_val_score(clf, X_pca, y, cv=cv, scoring='f1_macro')
        
        result = {
            'n_components': n,
            'accuracy_mean': acc_scores.mean(),
            'accuracy_std': acc_scores.std(),
            'f1_macro_mean': f1_scores.mean(),
            'f1_macro_std': f1_scores.std(),
            'explained_variance': pca.explained_variance_ratio_.sum()
        }
        
        # 如果是二分类，计算 AUC
        if is_binary:
            auc_scores = cross_val_score(clf, X_pca, y, cv=cv, scoring='roc_auc')
            result['auc_mean'] = auc_scores.mean()
            result['auc_std'] = auc_scores.std()
            print(f"Acc={acc_scores.mean():.4f}, F1={f1_scores.mean():.4f}, "
                  f"AUC={auc_scores.mean():.4f}, Var={pca.explained_variance_ratio_.sum():.2%}")
        else:
            result['auc_mean'] = np.nan
            result['auc_std'] = np.nan
            print(f"Acc={acc_scores.mean():.4f}, F1={f1_scores.mean():.4f}, "
                  f"Var={pca.explained_variance_ratio_.sum():.2%}")
        
        results.append(result)
    
    results_df = pd.DataFrame(results)
    return results_df


def plot_results(results_df, variance_info, dataset_name, output_dir='结果/PCA分析'):
    """
    绘制结果图表
    
    Args:
        results_df: 结果 DataFrame
        variance_info: 方差信息
        dataset_name: 数据集名称
        output_dir: 输出目录
    """
    print(f"\n📊 生成可视化...")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建图表
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(f'{dataset_name}: PCA Component Analysis', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    # 1. 解释方差曲线
    ax1 = axes[0, 0]
    ax1.plot(results_df['n_components'], results_df['explained_variance'], 
             'b-o', linewidth=2, markersize=8, label='Explained Variance')
    ax1.axhline(y=0.80, color='r', linestyle='--', alpha=0.5, label='80%')
    ax1.axhline(y=0.90, color='g', linestyle='--', alpha=0.5, label='90%')
    ax1.axhline(y=0.95, color='orange', linestyle='--', alpha=0.5, label='95%')
    ax1.set_xlabel('Number of Components', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Cumulative Explained Variance', fontsize=12, fontweight='bold')
    ax1.set_title('Explained Variance vs Components', fontsize=13, fontweight='bold')
    ax1.legend(loc='lower right')
    ax1.grid(True, alpha=0.3)
    
    # 2. Accuracy 曲线
    ax2 = axes[0, 1]
    ax2.errorbar(results_df['n_components'], results_df['accuracy_mean'],
                 yerr=results_df['accuracy_std'], marker='o', capsize=5,
                 linewidth=2, markersize=8, color='green', label='Accuracy')
    best_acc_idx = results_df['accuracy_mean'].idxmax()
    best_acc_n = results_df.loc[best_acc_idx, 'n_components']
    ax2.axvline(x=best_acc_n, color='red', linestyle='--', linewidth=2,
                label=f'Best: n={best_acc_n:.0f}')
    ax2.set_xlabel('Number of Components', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Accuracy', fontsize=12, fontweight='bold')
    ax2.set_title('Accuracy vs Components', fontsize=13, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. Macro F1 曲线
    ax3 = axes[1, 0]
    ax3.errorbar(results_df['n_components'], results_df['f1_macro_mean'],
                 yerr=results_df['f1_macro_std'], marker='o', capsize=5,
                 linewidth=2, markersize=8, color='blue', label='Macro F1')
    best_f1_idx = results_df['f1_macro_mean'].idxmax()
    best_f1_n = results_df.loc[best_f1_idx, 'n_components']
    ax3.axvline(x=best_f1_n, color='red', linestyle='--', linewidth=2,
                label=f'Best: n={best_f1_n:.0f}')
    ax3.set_xlabel('Number of Components', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Macro F1 Score', fontsize=12, fontweight='bold')
    ax3.set_title('Macro F1 vs Components', fontsize=13, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. AUC 曲线（如果有）
    ax4 = axes[1, 1]
    if not results_df['auc_mean'].isna().all():
        ax4.errorbar(results_df['n_components'], results_df['auc_mean'],
                     yerr=results_df['auc_std'], marker='o', capsize=5,
                     linewidth=2, markersize=8, color='purple', label='AUC')
        best_auc_idx = results_df['auc_mean'].idxmax()
        best_auc_n = results_df.loc[best_auc_idx, 'n_components']
        ax4.axvline(x=best_auc_n, color='red', linestyle='--', linewidth=2,
                    label=f'Best: n={best_auc_n:.0f}')
        ax4.set_xlabel('Number of Components', fontsize=12, fontweight='bold')
        ax4.set_ylabel('AUC', fontsize=12, fontweight='bold')
        ax4.set_title('AUC vs Components', fontsize=13, fontweight='bold')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
    else:
        # 如果没有 AUC，显示性能对比表
        ax4.axis('off')
        
        # 创建表格数据
        table_data = []
        for metric in ['accuracy', 'f1_macro']:
            best_idx = results_df[f'{metric}_mean'].idxmax()
            best_n = results_df.loc[best_idx, 'n_components']
            best_score = results_df.loc[best_idx, f'{metric}_mean']
            table_data.append([
                metric.replace('_', ' ').title(),
                f'{best_n:.0f}',
                f'{best_score:.4f}'
            ])
        
        table = ax4.table(cellText=table_data,
                         colLabels=['Metric', 'Best n', 'Score'],
                         cellLoc='center',
                         loc='center',
                         colWidths=[0.4, 0.3, 0.3])
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1, 2)
        
        # 设置表头样式
        for i in range(3):
            table[(0, i)].set_facecolor('#4CAF50')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        ax4.set_title('Best Configurations', fontsize=13, fontweight='bold')
    
    plt.tight_layout()
    
    # 保存图表
    output_path = os.path.join(output_dir, f'{dataset_name}_pca_analysis.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"  ✓ 已保存: {output_path}")


def find_optimal_components(results_df, dataset_name):
    """
    找到最佳的 PCA 成分数
    
    Args:
        results_df: 结果 DataFrame
        dataset_name: 数据集名称
    
    Returns:
        optimal_config: 最佳配置字典
    """
    print(f"\n{'='*80}")
    print(f"最佳配置分析: {dataset_name}")
    print(f"{'='*80}")
    
    # 基于不同指标找最佳
    best_acc_idx = results_df['accuracy_mean'].idxmax()
    best_f1_idx = results_df['f1_macro_mean'].idxmax()
    
    optimal_config = {
        'dataset': dataset_name,
        'best_by_accuracy': {
            'n_components': int(results_df.loc[best_acc_idx, 'n_components']),
            'accuracy': results_df.loc[best_acc_idx, 'accuracy_mean'],
            'f1_macro': results_df.loc[best_acc_idx, 'f1_macro_mean'],
            'explained_var': results_df.loc[best_acc_idx, 'explained_variance']
        },
        'best_by_f1': {
            'n_components': int(results_df.loc[best_f1_idx, 'n_components']),
            'accuracy': results_df.loc[best_f1_idx, 'accuracy_mean'],
            'f1_macro': results_df.loc[best_f1_idx, 'f1_macro_mean'],
            'explained_var': results_df.loc[best_f1_idx, 'explained_variance']
        }
    }
    
    # 如果有 AUC
    if not results_df['auc_mean'].isna().all():
        best_auc_idx = results_df['auc_mean'].idxmax()
        optimal_config['best_by_auc'] = {
            'n_components': int(results_df.loc[best_auc_idx, 'n_components']),
            'accuracy': results_df.loc[best_auc_idx, 'accuracy_mean'],
            'f1_macro': results_df.loc[best_auc_idx, 'f1_macro_mean'],
            'auc': results_df.loc[best_auc_idx, 'auc_mean'],
            'explained_var': results_df.loc[best_auc_idx, 'explained_variance']
        }
    
    # 打印结果
    print(f"\n📊 基于 Accuracy 的最佳配置:")
    print(f"  成分数: {optimal_config['best_by_accuracy']['n_components']}")
    print(f"  Accuracy: {optimal_config['best_by_accuracy']['accuracy']:.4f}")
    print(f"  Macro F1: {optimal_config['best_by_accuracy']['f1_macro']:.4f}")
    print(f"  解释方差: {optimal_config['best_by_accuracy']['explained_var']:.2%}")
    
    print(f"\n📊 基于 Macro F1 的最佳配置: ⭐ 推荐")
    print(f"  成分数: {optimal_config['best_by_f1']['n_components']}")
    print(f"  Accuracy: {optimal_config['best_by_f1']['accuracy']:.4f}")
    print(f"  Macro F1: {optimal_config['best_by_f1']['f1_macro']:.4f}")
    print(f"  解释方差: {optimal_config['best_by_f1']['explained_var']:.2%}")
    
    if 'best_by_auc' in optimal_config:
        print(f"\n📊 基于 AUC 的最佳配置:")
        print(f"  成分数: {optimal_config['best_by_auc']['n_components']}")
        print(f"  Accuracy: {optimal_config['best_by_auc']['accuracy']:.4f}")
        print(f"  Macro F1: {optimal_config['best_by_auc']['f1_macro']:.4f}")
        print(f"  AUC: {optimal_config['best_by_auc']['auc']:.4f}")
        print(f"  解释方差: {optimal_config['best_by_auc']['explained_var']:.2%}")
    
    # 推荐配置（基于 Macro F1）
    recommended_n = optimal_config['best_by_f1']['n_components']
    print(f"\n✅ 推荐使用: {recommended_n} 个 PCA 成分")
    
    return optimal_config


def main():
    """
    主函数：分析所有数据集
    """
    print("="*80)
    print("自动确定最佳 PCA 成分数")
    print("="*80)
    
    # 数据集配置
    datasets = {
        'Wound_Healing': {
            'name': 'Wound Healing',
            'n_components_list': [5, 10, 15, 20, 30, 40, 50, 75, 100]
        },
        'Sepsis': {
            'name': 'Sepsis',
            'n_components_list': [5, 10, 20, 30, 50, 75, 100, 150, 200]
        },
        'Gaucher': {
            'name': 'Gaucher',
            'n_components_list': [5, 10, 15, 20, 30, 40, 50]
        }
    }
    
    all_results = {}
    all_optimal_configs = {}
    
    # 处理每个数据集
    for dataset_key, config in datasets.items():
        try:
            # 加载数据
            X, y, label_names = load_dataset(dataset_key)
            
            # 方差分析
            pca, variance_info, scaler = analyze_pca_variance(
                X, config['name'], max_components=200
            )
            
            # 交叉验证评估
            results_df = evaluate_pca_components(
                X, y, config['n_components_list'], config['name']
            )
            
            # 保存结果
            output_dir = '结果/PCA分析'
            os.makedirs(output_dir, exist_ok=True)
            results_path = os.path.join(output_dir, f'{dataset_key}_pca_results.csv')
            results_df.to_csv(results_path, index=False, encoding='utf-8-sig')
            print(f"\n✓ 结果已保存: {results_path}")
            
            # 绘制图表
            plot_results(results_df, variance_info, config['name'], output_dir)
            
            # 找到最佳配置
            optimal_config = find_optimal_components(results_df, config['name'])
            
            all_results[dataset_key] = results_df
            all_optimal_configs[dataset_key] = optimal_config
            
        except Exception as e:
            print(f"\n❌ {config['name']} 处理失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 生成总结报告
    print(f"\n{'='*80}")
    print("总结报告")
    print(f"{'='*80}")
    
    summary_data = []
    for dataset_key, optimal_config in all_optimal_configs.items():
        summary_data.append({
            'Dataset': optimal_config['dataset'],
            'Recommended_n': optimal_config['best_by_f1']['n_components'],
            'Accuracy': optimal_config['best_by_f1']['accuracy'],
            'Macro_F1': optimal_config['best_by_f1']['f1_macro'],
            'Explained_Var': optimal_config['best_by_f1']['explained_var']
        })
    
    summary_df = pd.DataFrame(summary_data)
    
    print("\n推荐的 PCA 成分数（基于 Macro F1）:")
    print(summary_df.to_string(index=False))
    
    # 保存总结
    summary_path = '结果/PCA分析/optimal_pca_components_summary.csv'
    summary_df.to_csv(summary_path, index=False, encoding='utf-8-sig')
    print(f"\n✓ 总结已保存: {summary_path}")
    
    # 保存详细配置
    import json
    config_path = '结果/PCA分析/optimal_pca_configs.json'
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(all_optimal_configs, f, indent=2, ensure_ascii=False)
    print(f"✓ 详细配置已保存: {config_path}")
    
    print(f"\n{'='*80}")
    print("分析完成！")
    print(f"{'='*80}")
    print("\n生成的文件:")
    print("  - 结果/PCA分析/*_pca_results.csv (详细结果)")
    print("  - 结果/PCA分析/*_pca_analysis.png (可视化)")
    print("  - 结果/PCA分析/optimal_pca_components_summary.csv (总结)")
    print("  - 结果/PCA分析/optimal_pca_configs.json (详细配置)")


if __name__ == "__main__":
    main()
