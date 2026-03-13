"""
基线方法对比演示脚本

演示如何使用PCA基线方法与五大系统分类进行性能对比。

作者: AI Assistant
日期: 2025-12-24
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path

from .pca_baseline import PCABaseline
from .performance_comparison import PerformanceComparator


def create_demo_data():
    """
    创建演示数据
    
    Returns:
        演示数据集配置
    """
    print("创建演示数据...")
    
    # 创建输出目录
    demo_dir = Path("demo_data")
    demo_dir.mkdir(exist_ok=True)
    
    # 设置随机种子
    np.random.seed(42)
    
    # 创建两个演示数据集
    datasets = {}
    
    for dataset_name, config in [
        ("Demo_Dataset_1", {"n_samples": 150, "n_go_terms": 200, "effect_size": 1.0}),
        ("Demo_Dataset_2", {"n_samples": 100, "n_go_terms": 150, "effect_size": 0.5})
    ]:
        n_samples = config["n_samples"]
        n_go_terms = config["n_go_terms"]
        effect_size = config["effect_size"]
        
        print(f"  创建 {dataset_name}: {n_samples} 样本, {n_go_terms} GO条目")
        
        # 创建有结构的数据（两组有不同的表达模式）
        group1_size = n_samples // 2
        group2_size = n_samples - group1_size
        
        # 组1：前半部分GO terms高表达
        group1_data = np.random.normal(0, 1, (group1_size, n_go_terms))
        group1_data[:, :n_go_terms//2] += effect_size
        
        # 组2：后半部分GO terms高表达
        group2_data = np.random.normal(0, 1, (group2_size, n_go_terms))
        group2_data[:, n_go_terms//2:] += effect_size
        
        # 合并数据
        go_data = np.vstack([group1_data, group2_data])
        
        # 创建GO分数DataFrame
        go_scores = pd.DataFrame(
            go_data,
            columns=[f'GO_{i:04d}' for i in range(n_go_terms)]
        )
        go_scores['sample_id'] = [f'sample_{i}' for i in range(n_samples)]
        
        # 创建五大系统分数（基于GO分数的聚合）
        chunk_size = n_go_terms // 5
        system_scores = pd.DataFrame({
            'sample_id': go_scores['sample_id'],
            'System_A': go_scores.iloc[:, :chunk_size].mean(axis=1),
            'System_B': go_scores.iloc[:, chunk_size:2*chunk_size].mean(axis=1),
            'System_C': go_scores.iloc[:, 2*chunk_size:3*chunk_size].mean(axis=1),
            'System_D': go_scores.iloc[:, 3*chunk_size:4*chunk_size].mean(axis=1),
            'System_E': go_scores.iloc[:, 4*chunk_size:].mean(axis=1)
        })
        
        # 创建样本信息
        sample_info = pd.DataFrame({
            'sample_id': go_scores['sample_id'],
            'group': ['group1'] * group1_size + ['group2'] * group2_size
        })
        
        # 保存文件
        sample_info.to_csv(demo_dir / f"{dataset_name}_sample_info.csv", index=False)
        system_scores.to_csv(demo_dir / f"{dataset_name}_system_scores.csv", index=False)
        go_scores.to_csv(demo_dir / f"{dataset_name}_go_scores.csv", index=False)
        
        # 添加到数据集配置
        datasets[dataset_name.lower()] = {
            'name': dataset_name.replace('_', ' '),
            'sample_info_path': str(demo_dir / f"{dataset_name}_sample_info.csv"),
            'system_scores_path': str(demo_dir / f"{dataset_name}_system_scores.csv"),
            'go_scores_path': str(demo_dir / f"{dataset_name}_go_scores.csv")
        }
    
    print(f"演示数据已保存到: {demo_dir}")
    return datasets


def demo_single_comparison():
    """演示单个数据集的对比分析"""
    print("\n" + "="*80)
    print("演示1: 单个数据集的PCA基线对比")
    print("="*80)
    
    # 创建简单的测试数据
    np.random.seed(42)
    n_samples = 120
    n_go_terms = 100
    
    # 创建有差异的数据
    group1_size = 60
    group2_size = 60
    
    # 组1：前50个GO terms高表达
    group1_data = np.random.normal(0, 1, (group1_size, n_go_terms))
    group1_data[:, :50] += 1.5
    
    # 组2：后50个GO terms高表达
    group2_data = np.random.normal(0, 1, (group2_size, n_go_terms))
    group2_data[:, 50:] += 1.5
    
    # 合并数据
    go_data = np.vstack([group1_data, group2_data])
    
    # 创建DataFrame
    go_scores = pd.DataFrame(
        go_data,
        columns=[f'GO_{i:04d}' for i in range(n_go_terms)]
    )
    go_scores['sample_id'] = [f'sample_{i}' for i in range(n_samples)]
    
    # 创建五大系统分数
    system_scores = pd.DataFrame({
        'sample_id': go_scores['sample_id'],
        'System_A': go_scores.iloc[:, :20].mean(axis=1),
        'System_B': go_scores.iloc[:, 20:40].mean(axis=1),
        'System_C': go_scores.iloc[:, 40:60].mean(axis=1),
        'System_D': go_scores.iloc[:, 60:80].mean(axis=1),
        'System_E': go_scores.iloc[:, 80:100].mean(axis=1)
    })
    
    # 标签
    labels = ['control'] * group1_size + ['treatment'] * group2_size
    
    # 创建PCA基线方法
    pca_baseline = PCABaseline(n_components=5, random_state=42)
    
    # 执行PCA降维
    pca_scores = pca_baseline.fit_transform(go_scores)
    
    # 执行性能对比
    report = pca_baseline.compare_performance(
        five_system_scores=system_scores,
        pca_scores=pca_scores,
        labels=labels,
        dataset_name="Demo Single Dataset"
    )
    
    # 生成可视化
    output_dir = Path("demo_results")
    output_dir.mkdir(exist_ok=True)
    
    viz_path = output_dir / "demo_single_comparison.png"
    pca_baseline.generate_comparison_visualization(report, viz_path)
    
    print(f"\n可视化已保存: {viz_path}")
    
    return report


def demo_comprehensive_comparison():
    """演示全面的对比分析"""
    print("\n" + "="*80)
    print("演示2: 多数据集全面对比分析")
    print("="*80)
    
    # 创建演示数据
    datasets_config = create_demo_data()
    
    # 创建性能对比分析器
    comparator = PerformanceComparator(output_dir="demo_results/comprehensive")
    
    # 运行全面对比分析
    results = comparator.run_comprehensive_comparison(datasets_config)
    
    print(f"\n全面对比分析完成!")
    print(f"处理的数据集数量: {len(results['reports'])}")
    print(f"结果保存在: {results['output_dir']}")
    
    return results


def demo_custom_pca_components():
    """演示不同PCA成分数的影响"""
    print("\n" + "="*80)
    print("演示3: 不同PCA成分数的性能对比")
    print("="*80)
    
    # 创建测试数据
    np.random.seed(42)
    n_samples = 100
    n_go_terms = 200
    
    # 创建有结构的数据
    go_data = np.random.normal(0, 1, (n_samples, n_go_terms))
    # 添加一些主要的变异模式
    for i in range(5):
        pattern = np.random.normal(0, 1, n_go_terms)
        weights = np.random.normal(0, 1, n_samples)
        go_data += np.outer(weights, pattern) * (0.5 ** i)
    
    go_scores = pd.DataFrame(
        go_data,
        columns=[f'GO_{i:04d}' for i in range(n_go_terms)]
    )
    go_scores['sample_id'] = [f'sample_{i}' for i in range(n_samples)]
    
    # 创建五大系统分数
    system_scores = pd.DataFrame({
        'sample_id': go_scores['sample_id'],
        'System_A': go_scores.iloc[:, :40].mean(axis=1),
        'System_B': go_scores.iloc[:, 40:80].mean(axis=1),
        'System_C': go_scores.iloc[:, 80:120].mean(axis=1),
        'System_D': go_scores.iloc[:, 120:160].mean(axis=1),
        'System_E': go_scores.iloc[:, 160:200].mean(axis=1)
    })
    
    # 随机标签
    labels = np.random.choice(['A', 'B', 'C'], n_samples)
    
    # 测试不同的PCA成分数
    component_counts = [3, 5, 10, 20]
    results = {}
    
    for n_components in component_counts:
        print(f"\n测试 {n_components} 个PCA成分...")
        
        pca_baseline = PCABaseline(n_components=n_components, random_state=42)
        pca_scores = pca_baseline.fit_transform(go_scores)
        
        report = pca_baseline.compare_performance(
            five_system_scores=system_scores,
            pca_scores=pca_scores,
            labels=labels,
            dataset_name=f"PCA-{n_components} Components"
        )
        
        results[n_components] = {
            'explained_variance': report.pca_explained_variance,
            'pca_accuracy': report.pca_metrics.accuracy_mean,
            'pca_f1': report.pca_metrics.f1_macro_mean
        }
        
        print(f"  解释方差: {report.pca_explained_variance:.3f}")
        print(f"  PCA Accuracy: {report.pca_metrics.accuracy_mean:.3f}")
        print(f"  PCA F1: {report.pca_metrics.f1_macro_mean:.3f}")
    
    # 打印总结
    print(f"\n{'='*60}")
    print("PCA成分数对比总结:")
    print(f"{'='*60}")
    print(f"{'成分数':<8} {'解释方差':<12} {'Accuracy':<12} {'Macro F1':<12}")
    print("-" * 48)
    for n_comp, result in results.items():
        print(f"{n_comp:<8} {result['explained_variance']:<12.3f} "
              f"{result['pca_accuracy']:<12.3f} {result['pca_f1']:<12.3f}")
    
    return results


def main():
    """主演示函数"""
    print("PCA基线方法对比演示")
    print("="*80)
    
    try:
        # 演示1: 单个数据集对比
        single_report = demo_single_comparison()
        
        # 演示2: 全面对比分析
        comprehensive_results = demo_comprehensive_comparison()
        
        # 演示3: 不同PCA成分数的影响
        component_results = demo_custom_pca_components()
        
        print(f"\n{'='*80}")
        print("所有演示完成!")
        print(f"{'='*80}")
        print("\n生成的文件:")
        print("  - demo_results/demo_single_comparison.png")
        print("  - demo_results/comprehensive/performance_comparison_summary.csv")
        print("  - demo_results/comprehensive/performance_comparison_report.md")
        print("  - demo_results/comprehensive/performance_comparison_summary.png")
        print("  - demo_data/*.csv (演示数据)")
        
    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()