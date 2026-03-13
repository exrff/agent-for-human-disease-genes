"""
V7.5 五系统分数 vs PCA baseline 方法对比实验
Step 2.2: 比较两种 5 维表征在区分生物学/临床分组时的表现

方法一：V7.5 五大功能系统分数 (System A-E)
方法二：GO ssGSEA 矩阵的前 5 个 PCA 主成分 (PC1-PC5)

作者: AI Assistant
日期: 2025-12-03
"""

import pandas as pd
import numpy as np
import os
import warnings
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score, cross_validate
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, make_scorer
import matplotlib.pyplot as plt
import seaborn as sns

# 设置随机种子确保可复现
np.random.seed(42)
warnings.filterwarnings('ignore')

# 设置绘图样式
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.size'] = 11
plt.rcParams['figure.dpi'] = 300


def load_dataset(dataset_config):
    """
    加载单个数据集的三个文件并合并
    
    Args:
        dataset_config (dict): 包含文件路径的配置字典
            - name: 数据集名称
            - sample_info_path: 样本信息文件路径
            - system_scores_path: 五系统分数文件路径  
            - go_scores_path: GO term 分数文件路径
    
    Returns:
        tuple: (merged_data, sample_info, system_scores, go_scores)
               如果加载失败返回 (None, None, None, None)
    """
    print(f"\n{'='*60}")
    print(f"加载数据集: {dataset_config['name']}")
    print(f"{'='*60}")
    
    # 1. 加载三个文件
    try:
        sample_info = pd.read_csv(dataset_config['sample_info_path'])
        system_scores = pd.read_csv(dataset_config['system_scores_path'])
        go_scores = pd.read_csv(dataset_config['go_scores_path'])
        
        print(f"✓ 样本信息: {sample_info.shape}")
        print(f"✓ 系统分数: {system_scores.shape}")
        print(f"✓ GO 分数: {go_scores.shape}")
    except FileNotFoundError as e:
        print(f"❌ 文件未找到: {e}")
        return None, None, None, None
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        return None, None, None, None
    
    # 2. 检查必要的列
    required_cols = {
        'sample_info': ['sample_id', 'group'],
        'system_scores': ['sample_id', 'System_A', 'System_B', 'System_C', 'System_D', 'System_E'],
        'go_scores': ['sample_id']
    }
    
    for df_name, cols in required_cols.items():
        df = locals()[df_name]
        missing_cols = [col for col in cols if col not in df.columns]
        if missing_cols:
            print(f"❌ {df_name} 缺少必要列: {missing_cols}")
            print(f"   实际列: {list(df.columns)[:10]}...")
            return None, None, None, None
    
    # 3. 基于 sample_id 合并数据（取交集）
    print("\n合并数据...")
    # 先合并 sample_info 和 system_scores
    merged = pd.merge(sample_info, system_scores, on='sample_id', how='inner')
    print(f"  合并 (info + system): {merged.shape}")
    
    # 再合并 go_scores
    merged = pd.merge(merged, go_scores, on='sample_id', how='inner')
    print(f"  最终合并: {merged.shape}")
    
    if len(merged) == 0:
        print("❌ 合并后无数据，请检查 sample_id 是否匹配")
        return None, None, None, None
    
    # 4. 处理缺失值
    # 策略：GO 分数缺失用 0 填充（ssGSEA 分数可以为负，0 表示无富集）
    system_cols = ['System_A', 'System_B', 'System_C', 'System_D', 'System_E']
    go_cols = [col for col in merged.columns 
               if col not in ['sample_id', 'group'] + system_cols]
    
    # 检查系统分数缺失
    system_missing = merged[system_cols].isnull().sum().sum()
    if system_missing > 0:
        print(f"⚠️  系统分数有 {system_missing} 个缺失值，将删除这些样本")
        merged = merged.dropna(subset=system_cols)
    
    # 处理 GO 分数缺失
    go_missing_before = merged[go_cols].isnull().sum().sum()
    if go_missing_before > 0:
        print(f"⚠️  GO 分数有 {go_missing_before} 个缺失值，用 0 填充")
        merged[go_cols] = merged[go_cols].fillna(0)
    
    print(f"\n✓ 数据加载完成:")
    print(f"  - {len(merged)} 个样本")
    print(f"  - {len(go_cols)} 个 GO terms")
    print(f"  - 分组: {merged['group'].value_counts().to_dict()}")
    
    return merged, sample_info, system_scores, go_scores


def build_representations(merged_data):
    """
    构建两种 5 维表征
    
    Args:
        merged_data (pd.DataFrame): 合并后的数据
    
    Returns:
        tuple: (X_systems, X_pca, y, label_encoder, pca_model, go_cols)
    """
    print(f"\n{'='*60}")
    print("构建两种表征")
    print(f"{'='*60}")
    
    # 1. 提取标签
    y_raw = merged_data['group'].values
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(y_raw)
    n_classes = len(np.unique(y))
    
    print(f"\n分类任务:")
    print(f"  - {n_classes} 类: {list(label_encoder.classes_)}")
    print(f"  - 样本分布: {dict(zip(*np.unique(y, return_counts=True)))}")
    
    # 2. Representation A: V7.5 Systems (5 维)
    system_cols = ['System_A', 'System_B', 'System_C', 'System_D', 'System_E']
    X_systems = merged_data[system_cols].values
    
    print(f"\n✓ V7.5 Systems 表征: {X_systems.shape}")
    print(f"  - 特征范围: [{X_systems.min():.3f}, {X_systems.max():.3f}]")
    print(f"  - 特征均值: {X_systems.mean(axis=0)}")
    
    # 3. Representation B: PCA Components (5 维)
    # 提取 GO 分数矩阵
    go_cols = [col for col in merged_data.columns 
               if col not in ['sample_id', 'group'] + system_cols]
    X_go = merged_data[go_cols].values
    
    print(f"\n✓ GO 矩阵: {X_go.shape}")
    print(f"  - 特征范围: [{X_go.min():.3f}, {X_go.max():.3f}]")
    
    # 标准化 GO 分数（PCA 前必须标准化）
    scaler = StandardScaler()
    X_go_scaled = scaler.fit_transform(X_go)
    
    # PCA 降维到 5 维
    pca = PCA(n_components=5, random_state=42)
    X_pca = pca.fit_transform(X_go_scaled)
    
    # 打印 PCA 信息
    explained_variance = pca.explained_variance_ratio_
    cumulative_variance = np.cumsum(explained_variance)
    
    print(f"\n✓ PCA 降维: {X_go.shape} → {X_pca.shape}")
    print(f"  - 各 PC 解释方差比:")
    for i, var in enumerate(explained_variance, 1):
        print(f"    PC{i}: {var:.4f} ({var*100:.2f}%)")
    print(f"  - 累计解释方差: {cumulative_variance[-1]:.4f} ({cumulative_variance[-1]*100:.2f}%)")
    
    return X_systems, X_pca, y, label_encoder, pca, go_cols


def evaluate_representation(X, y, representation_name, dataset_name, cv_folds=5):
    """
    使用交叉验证评估单个表征的分类性能
    
    Args:
        X (np.array): 特征矩阵
        y (np.array): 标签
        representation_name (str): 表征名称
        dataset_name (str): 数据集名称
        cv_folds (int): 交叉验证折数
    
    Returns:
        dict: 评估结果
    """
    print(f"\n{'='*60}")
    print(f"评估: {representation_name}")
    print(f"{'='*60}")
    
    n_classes = len(np.unique(y))
    is_binary = (n_classes == 2)
    
    # 检查样本数是否足够
    min_class_count = min(np.bincount(y))
    if min_class_count < cv_folds:
        cv_folds = min_class_count
        print(f"⚠️  最小类别样本数 ({min_class_count}) < 折数，调整为 {cv_folds} 折")
    
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
    
    # 定义评分指标
    scoring = {
        'accuracy': 'accuracy',
        'f1_macro': 'f1_macro'
    }
    
    # 如果是二分类，添加 AUC
    if is_binary:
        scoring['roc_auc'] = 'roc_auc'
    
    # 执行交叉验证
    print(f"\n执行 {cv_folds}-Fold 交叉验证...")
    cv_results = cross_validate(clf, X, y, cv=cv, scoring=scoring, return_train_score=False)
    
    # 整理结果
    results = {
        'dataset_name': dataset_name,
        'representation': representation_name,
        'n_samples': len(X),
        'n_features': X.shape[1],
        'n_classes': n_classes,
        'cv_folds': cv_folds,
        'accuracy_mean': cv_results['test_accuracy'].mean(),
        'accuracy_std': cv_results['test_accuracy'].std(),
        'f1_macro_mean': cv_results['test_f1_macro'].mean(),
        'f1_macro_std': cv_results['test_f1_macro'].std(),
    }
    
    # 如果是二分类，添加 AUC
    if is_binary:
        results['auc_mean'] = cv_results['test_roc_auc'].mean()
        results['auc_std'] = cv_results['test_roc_auc'].std()
    else:
        results['auc_mean'] = np.nan
        results['auc_std'] = np.nan
    
    # 打印结果
    print(f"\n结果:")
    print(f"  Accuracy: {results['accuracy_mean']:.4f} ± {results['accuracy_std']:.4f}")
    print(f"  Macro F1: {results['f1_macro_mean']:.4f} ± {results['f1_macro_std']:.4f}")
    if is_binary:
        print(f"  AUC:      {results['auc_mean']:.4f} ± {results['auc_std']:.4f}")
    
    return results


def plot_comparison(results_df, metric='f1_macro', output_dir='结果/可视化'):
    """
    为每个数据集绘制方法对比图
    
    Args:
        results_df (pd.DataFrame): 结果数据框
        metric (str): 要绘制的指标 ('accuracy', 'f1_macro', 'auc')
        output_dir (str): 输出目录
    """
    print(f"\n{'='*60}")
    print(f"生成对比图: {metric}")
    print(f"{'='*60}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    datasets = results_df['dataset_name'].unique()
    
    for dataset in datasets:
        dataset_data = results_df[results_df['dataset_name'] == dataset]
        
        # 跳过没有该指标的数据集（例如多分类没有 AUC）
        if metric == 'auc' and dataset_data[f'{metric}_mean'].isna().all():
            print(f"  ⚠️  {dataset}: 无 {metric} 数据，跳过")
            continue
        
        if len(dataset_data) < 2:
            print(f"  ⚠️  {dataset}: 数据不足，跳过")
            continue
        
        # 准备数据
        representations = dataset_data['representation'].values
        means = dataset_data[f'{metric}_mean'].values
        stds = dataset_data[f'{metric}_std'].values
        
        # 创建图形
        fig, ax = plt.subplots(figsize=(8, 6))
        
        # 绘制条形图
        x_pos = np.arange(len(representations))
        colors = ['#3498db', '#e74c3c']  # 蓝色和红色
        bars = ax.bar(x_pos, means, yerr=stds, capsize=8, 
                     color=colors[:len(representations)], alpha=0.8, 
                     edgecolor='black', linewidth=1.5)
        
        # 设置标签和标题
        metric_labels = {
            'accuracy': 'Accuracy',
            'f1_macro': 'Macro F1-Score',
            'auc': 'AUC'
        }
        
        ax.set_xlabel('Representation Method', fontsize=13, fontweight='bold')
        ax.set_ylabel(metric_labels.get(metric, metric), fontsize=13, fontweight='bold')
        ax.set_title(f'{dataset}: {metric_labels.get(metric, metric)} Comparison', 
                    fontsize=14, fontweight='bold', pad=15)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(representations, fontsize=12)
        
        # 添加数值标注
        for i, (mean, std) in enumerate(zip(means, stds)):
            ax.text(i, mean + std + 0.02, f'{mean:.3f}\n±{std:.3f}', 
                   ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        # 设置 y 轴范围
        y_max = max(means + stds) * 1.2
        ax.set_ylim(0, min(y_max, 1.0))
        
        # 美化
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # 保存图片
        filename = f"{dataset.replace(' ', '_')}_{metric}.png"
        filepath = os.path.join(output_dir, filename)
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"  ✓ 已保存: {filepath}")


def print_console_report(results_df):
    """
    打印控制台报告
    
    Args:
        results_df (pd.DataFrame): 结果数据框
    """
    print(f"\n{'='*80}")
    print("V7.5 vs PCA 对比实验结果汇总")
    print(f"{'='*80}\n")
    
    datasets = results_df['dataset_name'].unique()
    
    for dataset in datasets:
        print(f"Dataset: {dataset}")
        print("-" * 70)
        
        dataset_data = results_df[results_df['dataset_name'] == dataset]
        
        for _, row in dataset_data.iterrows():
            rep_name = row['representation']
            acc_mean, acc_std = row['accuracy_mean'], row['accuracy_std']
            f1_mean, f1_std = row['f1_macro_mean'], row['f1_macro_std']
            
            print(f"  {rep_name:20s}: accuracy = {acc_mean:.4f} ± {acc_std:.4f}, "
                  f"macro F1 = {f1_mean:.4f} ± {f1_std:.4f}", end='')
            
            # 如果有 AUC
            if not pd.isna(row['auc_mean']):
                auc_mean, auc_std = row['auc_mean'], row['auc_std']
                print(f", AUC = {auc_mean:.4f} ± {auc_std:.4f}")
            else:
                print()
        
        print()


def main():
    """
    主函数：执行完整的对比实验
    """
    print("\n" + "="*80)
    print("V7.5 五系统分数 vs PCA Baseline 对比实验")
    print("="*80)
    
    # ========================================================================
    # 数据集配置（已自动生成）
    # ========================================================================
    datasets = {
        'wound_healing': {
            'name': 'Wound Healing',
            'sample_info_path': '数据/对比实验/Wound_Healing_sample_info.csv',
            'system_scores_path': '数据/对比实验/Wound_Healing_system_scores.csv',
            'go_scores_path': '数据/对比实验/Wound_Healing_go_scores.csv'
        },
        'sepsis': {
            'name': 'Sepsis',
            'sample_info_path': '数据/对比实验/Sepsis_sample_info.csv',
            'system_scores_path': '数据/对比实验/Sepsis_system_scores.csv',
            'go_scores_path': '数据/对比实验/Sepsis_go_scores.csv'
        },
        'gaucher': {
            'name': 'Gaucher Disease',
            'sample_info_path': '数据/对比实验/Gaucher_sample_info.csv',
            'system_scores_path': '数据/对比实验/Gaucher_system_scores.csv',
            'go_scores_path': '数据/对比实验/Gaucher_go_scores.csv'
        }
    }
    # ========================================================================
    
    # 存储所有结果
    all_results = []
    
    # 处理每个数据集
    for dataset_key, dataset_config in datasets.items():
        print(f"\n\n{'#'*80}")
        print(f"# 处理数据集: {dataset_config['name']}")
        print(f"{'#'*80}")
        
        # 1. 加载数据
        merged_data, sample_info, system_scores, go_scores = load_dataset(dataset_config)
        
        if merged_data is None:
            print(f"\n❌ 跳过数据集: {dataset_config['name']}")
            continue
        
        # 2. 构建表征
        X_systems, X_pca, y, label_encoder, pca_model, go_cols = build_representations(merged_data)
        
        # 3. 评估两种表征
        # V7.5 Systems
        results_systems = evaluate_representation(
            X_systems, y, 'V7.5_Systems', dataset_config['name']
        )
        all_results.append(results_systems)
        
        # PCA Components  
        results_pca = evaluate_representation(
            X_pca, y, 'PCA_5', dataset_config['name']
        )
        all_results.append(results_pca)
    
    # 4. 整理结果
    if not all_results:
        print("\n❌ 没有成功处理的数据集，请检查文件路径")
        return
    
    results_df = pd.DataFrame(all_results)
    
    # 5. 保存结果表
    output_dir = '结果'
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, 'v75_vs_pca_results.csv')
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n✓ 结果已保存: {output_file}")
    
    # 6. 生成对比图
    print(f"\n{'='*80}")
    print("生成可视化")
    print(f"{'='*80}")
    
    plot_comparison(results_df, metric='f1_macro')
    plot_comparison(results_df, metric='accuracy')
    
    # 如果有二分类数据集，也画 AUC
    if not results_df['auc_mean'].isna().all():
        plot_comparison(results_df, metric='auc')
    
    # 7. 打印控制台报告
    print_console_report(results_df)
    
    # 8. 保存详细的长格式结果（便于后续分析）
    detailed_results = []
    for _, row in results_df.iterrows():
        base_info = {
            'dataset_name': row['dataset_name'],
            'representation': row['representation'],
            'n_samples': row['n_samples'],
            'n_features': row['n_features'],
            'n_classes': row['n_classes'],
            'cv_folds': row['cv_folds']
        }
        
        # 添加各个指标
        for metric in ['accuracy', 'f1_macro', 'auc']:
            if not pd.isna(row[f'{metric}_mean']):
                detailed_results.append({
                    **base_info,
                    'metric': metric,
                    'mean': row[f'{metric}_mean'],
                    'std': row[f'{metric}_std']
                })
    
    detailed_df = pd.DataFrame(detailed_results)
    detailed_output = os.path.join(output_dir, 'v75_vs_pca_detailed_results.csv')
    detailed_df.to_csv(detailed_output, index=False, encoding='utf-8-sig')
    print(f"✓ 详细结果已保存: {detailed_output}")
    
    print(f"\n{'='*80}")
    print("实验完成！")
    print("="*80)
    print(f"\n生成的文件:")
    print(f"  - {output_file}")
    print(f"  - {detailed_output}")
    print(f"  - 结果/可视化/*.png")
    print()


if __name__ == "__main__":
    main()
