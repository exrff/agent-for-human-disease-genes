"""
五大系统分类与PCA基线方法性能对比分析

在相同数据集上比较两种方法的分类性能，计算准确率、F1分数、AUC等指标，
并进行统计显著性检验。

作者: AI Assistant
日期: 2025-12-24
"""

import pandas as pd
import numpy as np
import os
import json
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import logging
from dataclasses import asdict

from .pca_baseline import PCABaseline, ComparisonReport
from ..analysis.ssgsea_validator import ssGSEAValidator

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceComparator:
    """
    性能对比分析器
    
    负责协调五大系统分类与PCA基线方法的性能对比分析。
    """
    
    def __init__(self, output_dir: str = "results/comparison"):
        """
        初始化性能对比分析器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化PCA基线方法
        self.pca_baseline = PCABaseline(n_components=5)
        
        logger.info(f"性能对比分析器初始化完成，输出目录: {self.output_dir}")
    
    def load_validation_dataset(self, dataset_config: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        加载验证数据集
        
        Args:
            dataset_config: 数据集配置，包含文件路径
        
        Returns:
            加载的数据集字典，如果失败返回None
        """
        dataset_name = dataset_config['name']
        logger.info(f"加载数据集: {dataset_name}")
        
        try:
            # 加载样本信息
            sample_info = pd.read_csv(dataset_config['sample_info_path'])
            logger.info(f"  样本信息: {sample_info.shape}")
            
            # 加载五大系统分数
            system_scores = pd.read_csv(dataset_config['system_scores_path'])
            logger.info(f"  系统分数: {system_scores.shape}")
            
            # 加载GO分数
            go_scores = pd.read_csv(dataset_config['go_scores_path'])
            logger.info(f"  GO分数: {go_scores.shape}")
            
            # 检查必要的列
            required_cols = {
                'sample_info': ['sample_id', 'group'],
                'system_scores': ['sample_id', 'System_A', 'System_B', 'System_C', 'System_D', 'System_E'],
                'go_scores': ['sample_id']
            }
            
            for df_name, cols in required_cols.items():
                df = locals()[df_name]
                missing_cols = [col for col in cols if col not in df.columns]
                if missing_cols:
                    logger.error(f"{df_name} 缺少必要列: {missing_cols}")
                    return None
            
            # 基于sample_id合并数据
            merged = pd.merge(sample_info, system_scores, on='sample_id', how='inner')
            merged = pd.merge(merged, go_scores, on='sample_id', how='inner')
            
            if len(merged) == 0:
                logger.error("合并后无数据，请检查sample_id是否匹配")
                return None
            
            logger.info(f"  合并后数据: {merged.shape}")
            logger.info(f"  分组分布: {merged['group'].value_counts().to_dict()}")
            
            # 处理缺失值
            system_cols = ['System_A', 'System_B', 'System_C', 'System_D', 'System_E']
            go_cols = [col for col in merged.columns 
                      if col not in ['sample_id', 'group'] + system_cols]
            
            # 检查系统分数缺失
            system_missing = merged[system_cols].isnull().sum().sum()
            if system_missing > 0:
                logger.warning(f"系统分数有 {system_missing} 个缺失值，将删除这些样本")
                merged = merged.dropna(subset=system_cols)
            
            # 处理GO分数缺失
            go_missing_before = merged[go_cols].isnull().sum().sum()
            if go_missing_before > 0:
                logger.warning(f"GO分数有 {go_missing_before} 个缺失值，用0填充")
                merged[go_cols] = merged[go_cols].fillna(0)
            
            return {
                'name': dataset_name,
                'merged_data': merged,
                'sample_info': sample_info,
                'system_scores': system_scores,
                'go_scores': go_scores,
                'system_cols': system_cols,
                'go_cols': go_cols
            }
            
        except FileNotFoundError as e:
            logger.error(f"文件未找到: {e}")
            return None
        except Exception as e:
            logger.error(f"加载数据集失败: {e}")
            return None
    
    def compare_single_dataset(self, dataset: Dict[str, Any]) -> Optional[ComparisonReport]:
        """
        对单个数据集进行性能对比分析
        
        Args:
            dataset: 数据集字典
        
        Returns:
            对比分析报告，如果失败返回None
        """
        dataset_name = dataset['name']
        merged_data = dataset['merged_data']
        system_cols = dataset['system_cols']
        go_cols = dataset['go_cols']
        
        logger.info(f"开始性能对比分析: {dataset_name}")
        
        try:
            # 准备五大系统分数
            five_system_df = merged_data[['sample_id'] + system_cols].copy()
            
            # 准备GO分数并进行PCA降维
            go_scores_df = merged_data[['sample_id'] + go_cols].copy()
            pca_scores_df = self.pca_baseline.fit_transform(go_scores_df)
            
            # 准备标签
            labels = merged_data['group'].values
            
            # 执行性能对比
            comparison_report = self.pca_baseline.compare_performance(
                five_system_scores=five_system_df,
                pca_scores=pca_scores_df,
                labels=labels,
                dataset_name=dataset_name
            )
            
            return comparison_report
            
        except Exception as e:
            logger.error(f"性能对比分析失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run_comprehensive_comparison(self, datasets_config: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """
        运行全面的性能对比分析
        
        Args:
            datasets_config: 数据集配置字典
        
        Returns:
            完整的对比分析结果
        """
        logger.info("开始全面性能对比分析")
        
        all_reports = {}
        summary_data = []
        
        # 处理每个数据集
        for dataset_key, dataset_config in datasets_config.items():
            logger.info(f"\n{'='*80}")
            logger.info(f"处理数据集: {dataset_config['name']}")
            logger.info(f"{'='*80}")
            
            # 加载数据集
            dataset = self.load_validation_dataset(dataset_config)
            if dataset is None:
                logger.error(f"跳过数据集: {dataset_config['name']}")
                continue
            
            # 执行对比分析
            report = self.compare_single_dataset(dataset)
            if report is None:
                logger.error(f"对比分析失败: {dataset_config['name']}")
                continue
            
            all_reports[dataset_key] = report
            
            # 收集摘要数据
            summary_data.append({
                'dataset': report.dataset_name,
                'n_samples': report.n_samples,
                'n_classes': report.n_classes,
                'pca_explained_variance': report.pca_explained_variance,
                'five_system_accuracy': report.five_system_metrics.accuracy_mean,
                'five_system_f1': report.five_system_metrics.f1_macro_mean,
                'pca_accuracy': report.pca_metrics.accuracy_mean,
                'pca_f1': report.pca_metrics.f1_macro_mean,
                'accuracy_p_value': report.statistical_tests['accuracy']['p_value'],
                'f1_p_value': report.statistical_tests['f1_macro']['p_value'],
                'accuracy_effect_size': report.statistical_tests['accuracy']['effect_size'],
                'f1_effect_size': report.statistical_tests['f1_macro']['effect_size']
            })
            
            # 如果有AUC数据，添加到摘要中
            if report.five_system_metrics.auc_mean is not None:
                summary_data[-1].update({
                    'five_system_auc': report.five_system_metrics.auc_mean,
                    'pca_auc': report.pca_metrics.auc_mean
                })
        
        # 生成摘要报告
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            self._save_summary_report(summary_df)
            self._generate_summary_visualization(summary_df)
        
        # 保存详细报告
        self._save_detailed_reports(all_reports)
        
        # 生成个别数据集的可视化
        for dataset_key, report in all_reports.items():
            viz_path = self.output_dir / f"{dataset_key}_comparison.png"
            self.pca_baseline.generate_comparison_visualization(report, viz_path)
        
        return {
            'reports': all_reports,
            'summary': summary_df if summary_data else None,
            'output_dir': str(self.output_dir)
        }
    
    def _save_summary_report(self, summary_df: pd.DataFrame) -> None:
        """
        保存摘要报告
        
        Args:
            summary_df: 摘要数据框
        """
        # 保存CSV格式
        csv_path = self.output_dir / "performance_comparison_summary.csv"
        summary_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"摘要报告已保存: {csv_path}")
        
        # 生成Markdown格式报告
        md_path = self.output_dir / "performance_comparison_report.md"
        self._generate_markdown_report(summary_df, md_path)
    
    def _generate_markdown_report(self, summary_df: pd.DataFrame, output_path: Path) -> None:
        """
        生成Markdown格式的对比报告
        
        Args:
            summary_df: 摘要数据框
            output_path: 输出路径
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 五大系统分类 vs PCA基线方法性能对比报告\n\n")
            f.write(f"生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## 摘要\n\n")
            f.write("本报告比较了五大功能系统分类方法与PCA基线方法在多个验证数据集上的分类性能。\n\n")
            
            f.write("## 数据集概览\n\n")
            f.write("| 数据集 | 样本数 | 类别数 | PCA解释方差 |\n")
            f.write("|--------|--------|--------|-------------|\n")
            for _, row in summary_df.iterrows():
                f.write(f"| {row['dataset']} | {row['n_samples']} | {row['n_classes']} | {row['pca_explained_variance']:.1%} |\n")
            
            f.write("\n## 性能对比结果\n\n")
            f.write("### Accuracy对比\n\n")
            f.write("| 数据集 | 五大系统 | PCA基线 | p值 | 效应量 | 显著性 |\n")
            f.write("|--------|----------|---------|-----|--------|--------|\n")
            for _, row in summary_df.iterrows():
                p_val = row['accuracy_p_value']
                effect_size = row['accuracy_effect_size']
                significance = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "ns"
                f.write(f"| {row['dataset']} | {row['five_system_accuracy']:.4f} | {row['pca_accuracy']:.4f} | {p_val:.4f} | {effect_size:.3f} | {significance} |\n")
            
            f.write("\n### Macro F1对比\n\n")
            f.write("| 数据集 | 五大系统 | PCA基线 | p值 | 效应量 | 显著性 |\n")
            f.write("|--------|----------|---------|-----|--------|--------|\n")
            for _, row in summary_df.iterrows():
                p_val = row['f1_p_value']
                effect_size = row['f1_effect_size']
                significance = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "ns"
                f.write(f"| {row['dataset']} | {row['five_system_f1']:.4f} | {row['pca_f1']:.4f} | {p_val:.4f} | {effect_size:.3f} | {significance} |\n")
            
            # 如果有AUC数据
            if 'five_system_auc' in summary_df.columns:
                f.write("\n### AUC对比\n\n")
                f.write("| 数据集 | 五大系统 | PCA基线 |\n")
                f.write("|--------|----------|---------|\n")
                for _, row in summary_df.iterrows():
                    if pd.notna(row.get('five_system_auc')):
                        f.write(f"| {row['dataset']} | {row['five_system_auc']:.4f} | {row['pca_auc']:.4f} |\n")
            
            f.write("\n## 结论\n\n")
            
            # 计算总体优势
            five_system_wins = 0
            total_comparisons = 0
            
            for _, row in summary_df.iterrows():
                if row['five_system_accuracy'] > row['pca_accuracy']:
                    five_system_wins += 1
                total_comparisons += 1
                
                if row['five_system_f1'] > row['pca_f1']:
                    five_system_wins += 1
                total_comparisons += 1
            
            win_rate = five_system_wins / total_comparisons if total_comparisons > 0 else 0
            
            f.write(f"- 五大系统分类方法在 {win_rate:.1%} 的指标对比中表现更好\n")
            f.write(f"- 共分析了 {len(summary_df)} 个数据集，{total_comparisons} 个指标对比\n")
            
            # 显著性分析
            significant_improvements = 0
            for _, row in summary_df.iterrows():
                if (row['accuracy_p_value'] < 0.05 and row['accuracy_effect_size'] > 0):
                    significant_improvements += 1
                if (row['f1_p_value'] < 0.05 and row['f1_effect_size'] > 0):
                    significant_improvements += 1
            
            f.write(f"- 其中 {significant_improvements} 个指标显示五大系统方法有显著改进 (p<0.05)\n")
            
            f.write("\n注: *** p<0.001, ** p<0.01, * p<0.05, ns 不显著\n")
        
        logger.info(f"Markdown报告已保存: {output_path}")
    
    def _generate_summary_visualization(self, summary_df: pd.DataFrame) -> None:
        """
        生成摘要可视化图表
        
        Args:
            summary_df: 摘要数据框
        """
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        # 设置绘图样式
        plt.style.use('default')
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('五大系统 vs PCA基线方法性能对比摘要', fontsize=16, fontweight='bold')
        
        datasets = summary_df['dataset'].values
        n_datasets = len(datasets)
        
        # 1. Accuracy对比
        ax1 = axes[0, 0]
        x = np.arange(n_datasets)
        width = 0.35
        
        bars1 = ax1.bar(x - width/2, summary_df['five_system_accuracy'], width, 
                       label='五大系统', color='#3498db', alpha=0.8)
        bars2 = ax1.bar(x + width/2, summary_df['pca_accuracy'], width,
                       label='PCA基线', color='#e74c3c', alpha=0.8)
        
        ax1.set_xlabel('数据集')
        ax1.set_ylabel('Accuracy')
        ax1.set_title('Accuracy对比')
        ax1.set_xticks(x)
        ax1.set_xticklabels(datasets, rotation=45, ha='right')
        ax1.legend()
        ax1.grid(axis='y', alpha=0.3)
        
        # 2. Macro F1对比
        ax2 = axes[0, 1]
        bars1 = ax2.bar(x - width/2, summary_df['five_system_f1'], width,
                       label='五大系统', color='#3498db', alpha=0.8)
        bars2 = ax2.bar(x + width/2, summary_df['pca_f1'], width,
                       label='PCA基线', color='#e74c3c', alpha=0.8)
        
        ax2.set_xlabel('数据集')
        ax2.set_ylabel('Macro F1')
        ax2.set_title('Macro F1对比')
        ax2.set_xticks(x)
        ax2.set_xticklabels(datasets, rotation=45, ha='right')
        ax2.legend()
        ax2.grid(axis='y', alpha=0.3)
        
        # 3. 效应量分析
        ax3 = axes[1, 0]
        effect_sizes_acc = summary_df['accuracy_effect_size'].values
        effect_sizes_f1 = summary_df['f1_effect_size'].values
        
        bars1 = ax3.bar(x - width/2, effect_sizes_acc, width,
                       label='Accuracy', color='#2ecc71', alpha=0.8)
        bars2 = ax3.bar(x + width/2, effect_sizes_f1, width,
                       label='Macro F1', color='#f39c12', alpha=0.8)
        
        ax3.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        ax3.axhline(y=0.2, color='gray', linestyle='--', alpha=0.5, label='小效应')
        ax3.axhline(y=0.5, color='gray', linestyle='--', alpha=0.7, label='中效应')
        ax3.axhline(y=0.8, color='gray', linestyle='--', alpha=0.9, label='大效应')
        
        ax3.set_xlabel('数据集')
        ax3.set_ylabel("Cohen's d")
        ax3.set_title('效应量分析 (五大系统 vs PCA)')
        ax3.set_xticks(x)
        ax3.set_xticklabels(datasets, rotation=45, ha='right')
        ax3.legend()
        ax3.grid(axis='y', alpha=0.3)
        
        # 4. 统计显著性热图
        ax4 = axes[1, 1]
        
        # 准备显著性矩阵
        sig_matrix = np.zeros((n_datasets, 2))  # datasets x metrics
        for i, (_, row) in enumerate(summary_df.iterrows()):
            sig_matrix[i, 0] = 1 if row['accuracy_p_value'] < 0.05 else 0
            sig_matrix[i, 1] = 1 if row['f1_p_value'] < 0.05 else 0
        
        im = ax4.imshow(sig_matrix.T, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
        
        ax4.set_xticks(range(n_datasets))
        ax4.set_xticklabels(datasets, rotation=45, ha='right')
        ax4.set_yticks(range(2))
        ax4.set_yticklabels(['Accuracy', 'Macro F1'])
        ax4.set_title('统计显著性 (p<0.05)')
        
        # 添加文本标注
        for i in range(n_datasets):
            for j in range(2):
                text = '✓' if sig_matrix[i, j] == 1 else '✗'
                ax4.text(i, j, text, ha='center', va='center', 
                        color='white' if sig_matrix[i, j] == 1 else 'black',
                        fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        # 保存图表
        viz_path = self.output_dir / "performance_comparison_summary.png"
        plt.savefig(viz_path, dpi=300, bbox_inches='tight', facecolor='white')
        logger.info(f"摘要可视化已保存: {viz_path}")
        plt.close()
    
    def _save_detailed_reports(self, all_reports: Dict[str, ComparisonReport]) -> None:
        """
        保存详细的对比报告
        
        Args:
            all_reports: 所有对比报告
        """
        # 保存JSON格式的详细报告
        json_data = {}
        for dataset_key, report in all_reports.items():
            json_data[dataset_key] = report.to_dict()
        
        json_path = self.output_dir / "detailed_comparison_reports.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"详细报告已保存: {json_path}")


def main():
    """
    主函数：执行完整的性能对比分析
    """
    print("="*80)
    print("五大系统分类 vs PCA基线方法性能对比分析")
    print("="*80)
    
    # 数据集配置
    datasets_config = {
        'wound_healing': {
            'name': 'Wound Healing',
            'sample_info_path': 'data/comparison/Wound_Healing_sample_info.csv',
            'system_scores_path': 'data/comparison/Wound_Healing_system_scores.csv',
            'go_scores_path': 'data/comparison/Wound_Healing_go_scores.csv'
        },
        'sepsis': {
            'name': 'Sepsis',
            'sample_info_path': 'data/comparison/Sepsis_sample_info.csv',
            'system_scores_path': 'data/comparison/Sepsis_system_scores.csv',
            'go_scores_path': 'data/comparison/Sepsis_go_scores.csv'
        },
        'gaucher': {
            'name': 'Gaucher Disease',
            'sample_info_path': 'data/comparison/Gaucher_sample_info.csv',
            'system_scores_path': 'data/comparison/Gaucher_system_scores.csv',
            'go_scores_path': 'data/comparison/Gaucher_go_scores.csv'
        }
    }
    
    # 创建性能对比分析器
    comparator = PerformanceComparator()
    
    # 运行全面对比分析
    results = comparator.run_comprehensive_comparison(datasets_config)
    
    # 打印最终摘要
    print(f"\n{'='*80}")
    print("分析完成！")
    print(f"{'='*80}")
    print(f"\n生成的文件:")
    print(f"  - {results['output_dir']}/performance_comparison_summary.csv")
    print(f"  - {results['output_dir']}/performance_comparison_report.md")
    print(f"  - {results['output_dir']}/performance_comparison_summary.png")
    print(f"  - {results['output_dir']}/detailed_comparison_reports.json")
    print(f"  - {results['output_dir']}/*_comparison.png (各数据集详细对比图)")
    
    if results['summary'] is not None:
        print(f"\n处理的数据集数量: {len(results['summary'])}")
        print(f"成功生成的对比报告数量: {len(results['reports'])}")


if __name__ == "__main__":
    main()