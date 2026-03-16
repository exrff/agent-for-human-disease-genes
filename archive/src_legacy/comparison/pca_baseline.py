"""
PCA基线方法对比模块

实现PCA降维作为基线方法，与五大功能系统分类进行性能对比。

作者: AI Assistant
日期: 2025-12-24
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
import logging
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 设置随机种子确保可复现性
np.random.seed(42)


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    accuracy_mean: float
    accuracy_std: float
    f1_macro_mean: float
    f1_macro_std: float
    auc_mean: Optional[float] = None
    auc_std: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'accuracy_mean': self.accuracy_mean,
            'accuracy_std': self.accuracy_std,
            'f1_macro_mean': self.f1_macro_mean,
            'f1_macro_std': self.f1_macro_std
        }
        if self.auc_mean is not None:
            result['auc_mean'] = self.auc_mean
            result['auc_std'] = self.auc_std
        return result


@dataclass
class ComparisonReport:
    """对比分析报告数据类"""
    dataset_name: str
    five_system_metrics: PerformanceMetrics
    pca_metrics: PerformanceMetrics
    statistical_tests: Dict[str, Dict[str, float]]  # metric -> {'p_value': float, 'effect_size': float}
    n_samples: int
    n_classes: int
    pca_explained_variance: float
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'dataset_name': self.dataset_name,
            'five_system_metrics': self.five_system_metrics.to_dict(),
            'pca_metrics': self.pca_metrics.to_dict(),
            'statistical_tests': self.statistical_tests,
            'n_samples': self.n_samples,
            'n_classes': self.n_classes,
            'pca_explained_variance': self.pca_explained_variance
        }


class PCABaseline:
    """
    PCA基线方法类
    
    实现PCA降维作为基线方法，与五大功能系统分类进行性能对比。
    """
    
    def __init__(self, n_components: int = 5, random_state: int = 42):
        """
        初始化PCA基线方法
        
        Args:
            n_components: PCA主成分数量，默认5个
            random_state: 随机种子
        """
        self.n_components = n_components
        self.random_state = random_state
        self.pca = None
        self.scaler = None
        self.is_fitted = False
        
        logger.info(f"初始化PCA基线方法，成分数: {n_components}")
    
    def fit_transform(self, go_scores: pd.DataFrame) -> pd.DataFrame:
        """
        对GO分数矩阵进行PCA降维
        
        Args:
            go_scores: GO分数矩阵，行为样本，列为GO条目
        
        Returns:
            PCA降维后的特征矩阵
        """
        logger.info(f"PCA降维: {go_scores.shape} -> {self.n_components}维")
        
        # 提取特征矩阵（排除sample_id列）
        if 'sample_id' in go_scores.columns:
            X = go_scores.drop('sample_id', axis=1).values
            sample_ids = go_scores['sample_id'].values
        else:
            X = go_scores.values
            sample_ids = go_scores.index.values
        
        # 标准化
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # PCA降维
        self.pca = PCA(n_components=self.n_components, random_state=self.random_state)
        X_pca = self.pca.fit_transform(X_scaled)
        
        # 创建结果DataFrame
        pca_columns = [f'PC{i+1}' for i in range(self.n_components)]
        result_df = pd.DataFrame(X_pca, columns=pca_columns)
        result_df['sample_id'] = sample_ids
        
        self.is_fitted = True
        
        # 记录解释方差
        explained_variance = self.pca.explained_variance_ratio_.sum()
        logger.info(f"PCA解释方差: {explained_variance:.3f} ({explained_variance*100:.1f}%)")
        
        return result_df
    
    def transform(self, go_scores: pd.DataFrame) -> pd.DataFrame:
        """
        使用已拟合的PCA模型转换新数据
        
        Args:
            go_scores: GO分数矩阵
        
        Returns:
            PCA降维后的特征矩阵
        """
        if not self.is_fitted:
            raise ValueError("PCA模型尚未拟合，请先调用fit_transform方法")
        
        # 提取特征矩阵
        if 'sample_id' in go_scores.columns:
            X = go_scores.drop('sample_id', axis=1).values
            sample_ids = go_scores['sample_id'].values
        else:
            X = go_scores.values
            sample_ids = go_scores.index.values
        
        # 标准化和PCA转换
        X_scaled = self.scaler.transform(X)
        X_pca = self.pca.transform(X_scaled)
        
        # 创建结果DataFrame
        pca_columns = [f'PC{i+1}' for i in range(self.n_components)]
        result_df = pd.DataFrame(X_pca, columns=pca_columns)
        result_df['sample_id'] = sample_ids
        
        return result_df
    
    def _evaluate_method(self, X: np.ndarray, y: np.ndarray, 
                        method_name: str, cv_folds: int = 5) -> PerformanceMetrics:
        """
        使用交叉验证评估单个方法的性能
        
        Args:
            X: 特征矩阵
            y: 标签
            method_name: 方法名称
            cv_folds: 交叉验证折数
        
        Returns:
            性能指标
        """
        logger.info(f"评估方法: {method_name}, 特征维度: {X.shape}")
        
        n_classes = len(np.unique(y))
        is_binary = (n_classes == 2)
        
        # 检查样本数是否足够
        min_class_count = min(np.bincount(y))
        if min_class_count < cv_folds:
            cv_folds = min_class_count
            logger.warning(f"最小类别样本数 ({min_class_count}) < 折数，调整为 {cv_folds} 折")
        
        # 创建分类器
        if is_binary:
            clf = LogisticRegression(random_state=self.random_state, max_iter=1000)
        else:
            clf = LogisticRegression(
                random_state=self.random_state, 
                max_iter=1000, 
                multi_class='multinomial', 
                solver='lbfgs'
            )
        
        # 交叉验证
        cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=self.random_state)
        
        # 定义评分指标
        scoring = {
            'accuracy': 'accuracy',
            'f1_macro': 'f1_macro'
        }
        
        # 如果是二分类，添加AUC
        if is_binary:
            scoring['roc_auc'] = 'roc_auc'
        
        # 执行交叉验证
        cv_results = cross_validate(clf, X, y, cv=cv, scoring=scoring, return_train_score=False)
        
        # 整理结果
        metrics = PerformanceMetrics(
            accuracy_mean=cv_results['test_accuracy'].mean(),
            accuracy_std=cv_results['test_accuracy'].std(),
            f1_macro_mean=cv_results['test_f1_macro'].mean(),
            f1_macro_std=cv_results['test_f1_macro'].std()
        )
        
        # 如果是二分类，添加AUC
        if is_binary:
            metrics.auc_mean = cv_results['test_roc_auc'].mean()
            metrics.auc_std = cv_results['test_roc_auc'].std()
        
        logger.info(f"{method_name} - Accuracy: {metrics.accuracy_mean:.4f}±{metrics.accuracy_std:.4f}, "
                   f"F1: {metrics.f1_macro_mean:.4f}±{metrics.f1_macro_std:.4f}")
        
        return metrics
    
    def _perform_statistical_tests(self, five_system_scores: List[float], 
                                 pca_scores: List[float], 
                                 metric_name: str) -> Dict[str, float]:
        """
        执行统计显著性检验
        
        Args:
            five_system_scores: 五系统方法的得分列表
            pca_scores: PCA方法的得分列表
            metric_name: 指标名称
        
        Returns:
            统计检验结果
        """
        # 配对t检验
        t_stat, p_value = stats.ttest_rel(five_system_scores, pca_scores)
        
        # 计算效应量 (Cohen's d)
        pooled_std = np.sqrt((np.var(five_system_scores, ddof=1) + np.var(pca_scores, ddof=1)) / 2)
        if pooled_std > 0:
            cohens_d = (np.mean(five_system_scores) - np.mean(pca_scores)) / pooled_std
        else:
            cohens_d = 0.0
        
        return {
            'p_value': p_value,
            'effect_size': cohens_d,
            't_statistic': t_stat
        }
    
    def compare_performance(self, five_system_scores: pd.DataFrame, 
                          pca_scores: pd.DataFrame, 
                          labels: List[Union[str, int]],
                          dataset_name: str = "Unknown") -> ComparisonReport:
        """
        比较五大系统分类与PCA基线方法的性能
        
        Args:
            five_system_scores: 五大系统分数矩阵
            pca_scores: PCA降维后的分数矩阵
            labels: 样本标签
            dataset_name: 数据集名称
        
        Returns:
            对比分析报告
        """
        logger.info(f"性能对比分析: {dataset_name}")
        
        # 准备五系统特征矩阵
        system_cols = ['System_A', 'System_B', 'System_C', 'System_D', 'System_E']
        if 'sample_id' in five_system_scores.columns:
            X_systems = five_system_scores[system_cols].values
        else:
            X_systems = five_system_scores.values
        
        # 准备PCA特征矩阵
        pca_cols = [col for col in pca_scores.columns if col.startswith('PC')]
        if 'sample_id' in pca_scores.columns:
            X_pca = pca_scores[pca_cols].values
        else:
            X_pca = pca_scores.values
        
        # 编码标签
        from sklearn.preprocessing import LabelEncoder
        le = LabelEncoder()
        y = le.fit_transform(labels)
        
        n_samples = len(y)
        n_classes = len(np.unique(y))
        
        logger.info(f"样本数: {n_samples}, 类别数: {n_classes}")
        
        # 评估两种方法
        five_system_metrics = self._evaluate_method(X_systems, y, "五大系统")
        pca_metrics = self._evaluate_method(X_pca, y, "PCA基线")
        
        # 统计显著性检验（需要重新进行交叉验证获取每折的得分）
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.random_state)
        
        # 获取每折的得分用于统计检验
        clf = LogisticRegression(random_state=self.random_state, max_iter=1000)
        
        five_system_acc_scores = []
        five_system_f1_scores = []
        pca_acc_scores = []
        pca_f1_scores = []
        
        for train_idx, test_idx in cv.split(X_systems, y):
            # 五系统方法
            clf.fit(X_systems[train_idx], y[train_idx])
            y_pred = clf.predict(X_systems[test_idx])
            five_system_acc_scores.append(accuracy_score(y[test_idx], y_pred))
            five_system_f1_scores.append(f1_score(y[test_idx], y_pred, average='macro'))
            
            # PCA方法
            clf.fit(X_pca[train_idx], y[train_idx])
            y_pred = clf.predict(X_pca[test_idx])
            pca_acc_scores.append(accuracy_score(y[test_idx], y_pred))
            pca_f1_scores.append(f1_score(y[test_idx], y_pred, average='macro'))
        
        # 执行统计检验
        statistical_tests = {
            'accuracy': self._perform_statistical_tests(
                five_system_acc_scores, pca_acc_scores, 'accuracy'
            ),
            'f1_macro': self._perform_statistical_tests(
                five_system_f1_scores, pca_f1_scores, 'f1_macro'
            )
        }
        
        # 获取PCA解释方差
        pca_explained_variance = self.pca.explained_variance_ratio_.sum() if self.pca else 0.0
        
        # 创建对比报告
        report = ComparisonReport(
            dataset_name=dataset_name,
            five_system_metrics=five_system_metrics,
            pca_metrics=pca_metrics,
            statistical_tests=statistical_tests,
            n_samples=n_samples,
            n_classes=n_classes,
            pca_explained_variance=pca_explained_variance
        )
        
        # 打印结果摘要
        self._print_comparison_summary(report)
        
        return report
    
    def _print_comparison_summary(self, report: ComparisonReport) -> None:
        """
        打印对比结果摘要
        
        Args:
            report: 对比分析报告
        """
        print(f"\n{'='*80}")
        print(f"性能对比结果: {report.dataset_name}")
        print(f"{'='*80}")
        
        print(f"\n数据集信息:")
        print(f"  样本数: {report.n_samples}")
        print(f"  类别数: {report.n_classes}")
        print(f"  PCA解释方差: {report.pca_explained_variance:.3f} ({report.pca_explained_variance*100:.1f}%)")
        
        print(f"\n性能指标:")
        print(f"  {'方法':<15} {'Accuracy':<20} {'Macro F1':<20} {'AUC':<20}")
        print(f"  {'-'*75}")
        
        # 五系统结果
        five_acc = f"{report.five_system_metrics.accuracy_mean:.4f}±{report.five_system_metrics.accuracy_std:.4f}"
        five_f1 = f"{report.five_system_metrics.f1_macro_mean:.4f}±{report.five_system_metrics.f1_macro_std:.4f}"
        five_auc = "N/A"
        if report.five_system_metrics.auc_mean is not None:
            five_auc = f"{report.five_system_metrics.auc_mean:.4f}±{report.five_system_metrics.auc_std:.4f}"
        
        print(f"  {'五大系统':<15} {five_acc:<20} {five_f1:<20} {five_auc:<20}")
        
        # PCA结果
        pca_acc = f"{report.pca_metrics.accuracy_mean:.4f}±{report.pca_metrics.accuracy_std:.4f}"
        pca_f1 = f"{report.pca_metrics.f1_macro_mean:.4f}±{report.pca_metrics.f1_macro_std:.4f}"
        pca_auc = "N/A"
        if report.pca_metrics.auc_mean is not None:
            pca_auc = f"{report.pca_metrics.auc_mean:.4f}±{report.pca_metrics.auc_std:.4f}"
        
        print(f"  {'PCA基线':<15} {pca_acc:<20} {pca_f1:<20} {pca_auc:<20}")
        
        print(f"\n统计显著性检验:")
        for metric, test_result in report.statistical_tests.items():
            p_val = test_result['p_value']
            effect_size = test_result['effect_size']
            significance = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "ns"
            
            print(f"  {metric:<12}: p={p_val:.4f} {significance}, Cohen's d={effect_size:.3f}")
        
        print(f"\n注: *** p<0.001, ** p<0.01, * p<0.05, ns 不显著")
    
    def generate_comparison_visualization(self, report: ComparisonReport,
                                        output_path: Optional[Union[str, Path]] = None) -> None:
        """
        生成对比分析可视化图表
        
        Args:
            report: 对比分析报告
            output_path: 输出路径，如果为None则显示图表
        """
        logger.info(f"生成对比可视化: {report.dataset_name}")
        
        # 设置绘图样式
        plt.style.use('default')
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'{report.dataset_name}: 五大系统 vs PCA基线对比', 
                     fontsize=16, fontweight='bold', y=0.98)
        
        # 准备数据
        methods = ['五大系统', 'PCA基线']
        metrics_data = {
            'Accuracy': {
                'means': [report.five_system_metrics.accuracy_mean, report.pca_metrics.accuracy_mean],
                'stds': [report.five_system_metrics.accuracy_std, report.pca_metrics.accuracy_std]
            },
            'Macro F1': {
                'means': [report.five_system_metrics.f1_macro_mean, report.pca_metrics.f1_macro_mean],
                'stds': [report.five_system_metrics.f1_macro_std, report.pca_metrics.f1_macro_std]
            }
        }
        
        # 如果有AUC数据，添加到指标中
        if (report.five_system_metrics.auc_mean is not None and 
            report.pca_metrics.auc_mean is not None):
            metrics_data['AUC'] = {
                'means': [report.five_system_metrics.auc_mean, report.pca_metrics.auc_mean],
                'stds': [report.five_system_metrics.auc_std, report.pca_metrics.auc_std]
            }
        
        # 颜色配置
        colors = ['#3498db', '#e74c3c']  # 蓝色和红色
        
        # 绘制各个指标的对比图
        plot_positions = [(0, 0), (0, 1), (1, 0)]
        
        for idx, (metric_name, data) in enumerate(metrics_data.items()):
            if idx >= len(plot_positions):
                break
                
            row, col = plot_positions[idx]
            ax = axes[row, col]
            
            x_pos = np.arange(len(methods))
            bars = ax.bar(x_pos, data['means'], yerr=data['stds'], 
                         capsize=8, color=colors, alpha=0.8, 
                         edgecolor='black', linewidth=1.5)
            
            ax.set_xlabel('方法', fontsize=12, fontweight='bold')
            ax.set_ylabel(metric_name, fontsize=12, fontweight='bold')
            ax.set_title(f'{metric_name} 对比', fontsize=13, fontweight='bold')
            ax.set_xticks(x_pos)
            ax.set_xticklabels(methods, fontsize=11)
            
            # 添加数值标注
            for i, (mean, std) in enumerate(zip(data['means'], data['stds'])):
                ax.text(i, mean + std + 0.01, f'{mean:.3f}\n±{std:.3f}', 
                       ha='center', va='bottom', fontsize=10, fontweight='bold')
            
            # 添加显著性标记
            if metric_name.lower().replace(' ', '_') in report.statistical_tests:
                p_val = report.statistical_tests[metric_name.lower().replace(' ', '_')]['p_value']
                if p_val < 0.05:
                    y_max = max(data['means']) + max(data['stds']) + 0.05
                    ax.plot([0, 1], [y_max, y_max], 'k-', linewidth=1)
                    significance = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*"
                    ax.text(0.5, y_max + 0.01, significance, ha='center', va='bottom', 
                           fontsize=12, fontweight='bold')
            
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
        
        # 第四个子图：统计信息摘要
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        # 创建统计信息表格
        stats_text = f"""数据集信息:
样本数: {report.n_samples}
类别数: {report.n_classes}
PCA解释方差: {report.pca_explained_variance:.1%}

统计显著性检验:"""
        
        for metric, test_result in report.statistical_tests.items():
            p_val = test_result['p_value']
            effect_size = test_result['effect_size']
            significance = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "ns"
            stats_text += f"\n{metric}: p={p_val:.4f} {significance}"
            stats_text += f"\nCohen's d={effect_size:.3f}"
        
        ax4.text(0.1, 0.9, stats_text, transform=ax4.transAxes, fontsize=11,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        
        plt.tight_layout()
        
        # 保存或显示图表
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
            logger.info(f"对比图表已保存: {output_path}")
        else:
            plt.show()
        
        plt.close()