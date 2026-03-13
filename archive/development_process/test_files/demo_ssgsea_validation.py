"""
ssGSEA验证模块演示脚本

展示如何使用ssGSEA验证器进行五大功能系统分类验证。

作者: AI Assistant
日期: 2025-12-24
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

from .ssgsea_validator import ssGSEAValidator
from ..config.settings import get_settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demo_basic_ssgsea_computation():
    """演示基本的ssGSEA计算"""
    print("=" * 80)
    print("演示1: 基本ssGSEA计算")
    print("=" * 80)
    
    # 初始化验证器
    validator = ssGSEAValidator()
    
    # 加载系统基因集
    try:
        gene_sets = validator.load_system_gene_sets()
        print(f"成功加载 {len(gene_sets)} 个系统的基因集")
        
        # 显示基因集信息
        for system, genes in gene_sets.items():
            print(f"  {system}: {len(genes)} 个基因")
    
    except Exception as e:
        print(f"加载基因集失败: {e}")
        print("使用模拟基因集进行演示...")
        
        # 创建模拟基因集
        gene_sets = {
            'System A': [f'GENE_A_{i}' for i in range(1, 21)],
            'System B': [f'GENE_B_{i}' for i in range(1, 21)],
            'System C': [f'GENE_C_{i}' for i in range(1, 21)]
        }
        validator.gene_sets = gene_sets
    
    # 创建模拟表达数据
    print("\n创建模拟基因表达数据...")
    all_genes = []
    for genes in gene_sets.values():
        all_genes.extend(genes)
    
    samples = [f'Sample_{i}' for i in range(1, 11)]
    
    # 生成模拟表达数据
    np.random.seed(42)
    expression_data = np.random.randn(len(all_genes), len(samples))
    expression_df = pd.DataFrame(expression_data, index=all_genes, columns=samples)
    
    print(f"表达矩阵: {expression_df.shape}")
    
    # 计算ssGSEA得分
    print("\n计算ssGSEA得分...")
    try:
        scores = validator.compute_system_scores(expression_df)
        print(f"ssGSEA得分矩阵: {scores.shape}")
        print("\n得分摘要:")
        print(scores.describe())
        
        return scores
        
    except Exception as e:
        print(f"ssGSEA计算失败: {e}")
        return None


def demo_time_series_analysis():
    """演示时间序列分析"""
    print("\n" + "=" * 80)
    print("演示2: 时间序列分析")
    print("=" * 80)
    
    validator = ssGSEAValidator()
    
    # 创建模拟时间序列数据
    systems = ['System A', 'System B', 'System C']
    time_points = ['0h', '6h', '12h', '24h', '48h']
    samples_per_time = 3
    
    # 生成样本名称
    samples = []
    sample_times = []
    for tp in time_points:
        for i in range(samples_per_time):
            samples.append(f'{tp}_Rep{i+1}')
            sample_times.append(tp)
    
    # 生成模拟得分数据（System A递增，System B递减，System C稳定）
    np.random.seed(42)
    scores_data = []
    
    for i, system in enumerate(systems):
        system_scores = []
        for j, tp in enumerate(time_points):
            base_score = 0
            if system == 'System A':
                base_score = j * 0.3  # 递增趋势
            elif system == 'System B':
                base_score = -j * 0.2  # 递减趋势
            # System C保持在0附近（稳定）
            
            # 为每个时间点的重复样本添加噪声
            for rep in range(samples_per_time):
                score = base_score + np.random.normal(0, 0.1)
                system_scores.append(score)
        
        scores_data.append(system_scores)
    
    scores_df = pd.DataFrame(scores_data, index=systems, columns=samples)
    
    print(f"时间序列得分矩阵: {scores_df.shape}")
    print(f"时间点: {time_points}")
    
    # 执行时间序列分析
    try:
        result = validator.analyze_time_series(scores_df, sample_times, "Demo Dataset")
        
        print("\n时间序列分析结果:")
        print(f"数据集: {result.dataset_name}")
        print(f"时间点数: {len(result.time_points)}")
        print("\n趋势分析:")
        for system, trend in result.trends.items():
            correlation = result.correlations[system]
            print(f"  {system}: {trend} (相关性: {correlation:.3f})")
        
        return result
        
    except Exception as e:
        print(f"时间序列分析失败: {e}")
        return None


def demo_disease_control_comparison():
    """演示疾病对比分析"""
    print("\n" + "=" * 80)
    print("演示3: 疾病对比分析")
    print("=" * 80)
    
    validator = ssGSEAValidator()
    
    # 创建模拟疾病对比数据
    systems = ['System A', 'System B', 'System C']
    disease_samples = [f'Disease_{i}' for i in range(1, 6)]
    control_samples = [f'Control_{i}' for i in range(1, 6)]
    all_samples = disease_samples + control_samples
    
    # 生成模拟得分数据（疾病组System A得分更高）
    np.random.seed(42)
    scores_data = []
    
    for system in systems:
        system_scores = []
        for sample in all_samples:
            if sample.startswith('Disease') and system == 'System A':
                # 疾病组System A得分更高
                score = np.random.normal(1.0, 0.3)
            elif sample.startswith('Control') and system == 'System A':
                # 对照组System A得分较低
                score = np.random.normal(0.0, 0.3)
            else:
                # 其他情况随机得分
                score = np.random.normal(0.0, 0.3)
            system_scores.append(score)
        
        scores_data.append(system_scores)
    
    scores_df = pd.DataFrame(scores_data, index=systems, columns=all_samples)
    
    print(f"疾病对比得分矩阵: {scores_df.shape}")
    print(f"疾病组样本: {len(disease_samples)}")
    print(f"对照组样本: {len(control_samples)}")
    
    # 执行疾病对比分析
    try:
        result = validator.compare_disease_control(
            scores_df, disease_samples, control_samples, "Demo Disease Dataset"
        )
        
        print("\n疾病对比分析结果:")
        print(f"数据集: {result.dataset_name}")
        print("\n统计结果:")
        for system in systems:
            fold_change = result.fold_changes[system]
            p_value = result.p_values[system]
            effect_size = result.effect_sizes[system]
            
            print(f"  {system}:")
            print(f"    Fold Change: {fold_change:.3f}")
            print(f"    P-value: {p_value:.3f}")
            print(f"    Effect Size: {effect_size:.3f}")
        
        print(f"\n显著差异系统: {result.significant_systems}")
        
        return result
        
    except Exception as e:
        print(f"疾病对比分析失败: {e}")
        return None


def demo_validation_workflow():
    """演示完整的验证工作流程"""
    print("\n" + "=" * 80)
    print("演示4: 完整验证工作流程")
    print("=" * 80)
    
    validator = ssGSEAValidator()
    
    # 检查验证数据集是否存在
    settings = get_settings()
    validation_datasets = [
        'GSE28914', 'GSE65682', 'GSE21899'
    ]
    
    available_datasets = []
    for dataset in validation_datasets:
        series_path = settings.validation_dir / dataset / f"{dataset}_series_matrix.txt.gz"
        if series_path.exists():
            available_datasets.append(dataset)
    
    if available_datasets:
        print(f"发现可用的验证数据集: {available_datasets}")
        print("注意: 完整的验证流程需要较长时间，这里仅演示流程...")
        
        # 可以取消注释下面的代码来运行完整验证
        # try:
        #     results = validator.run_comprehensive_validation()
        #     print("完整验证流程执行成功!")
        #     return results
        # except Exception as e:
        #     print(f"完整验证流程失败: {e}")
        
    else:
        print("未找到验证数据集文件，跳过完整验证演示")
        print("请确保以下文件存在:")
        for dataset in validation_datasets:
            series_path = settings.validation_dir / dataset / f"{dataset}_series_matrix.txt.gz"
            print(f"  {series_path}")
    
    return None


def main():
    """主演示函数"""
    print("ssGSEA验证模块演示")
    print("=" * 80)
    
    try:
        # 演示1: 基本ssGSEA计算
        scores = demo_basic_ssgsea_computation()
        
        # 演示2: 时间序列分析
        time_result = demo_time_series_analysis()
        
        # 演示3: 疾病对比分析
        comparison_result = demo_disease_control_comparison()
        
        # 演示4: 完整验证工作流程
        validation_result = demo_validation_workflow()
        
        print("\n" + "=" * 80)
        print("所有演示完成!")
        print("=" * 80)
        
        return {
            'basic_scores': scores,
            'time_series': time_result,
            'disease_comparison': comparison_result,
            'validation': validation_result
        }
        
    except Exception as e:
        print(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    results = main()