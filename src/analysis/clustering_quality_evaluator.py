"""
聚类质量评估器

计算系统内部平均相似度、系统间平均相似度，生成语义一致性验证报告。
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import logging
from itertools import combinations
import json
from datetime import datetime

from .semantic_coherence_validator import SemanticCoherenceValidator, CoherenceReport, SimilarityStats
from .semantic_similarity import SemanticSimilarityCalculator, SimilarityConfig

logger = logging.getLogger(__name__)


@dataclass
class ClusteringMetrics:
    """聚类质量指标"""
    silhouette_score: float
    calinski_harabasz_score: float
    davies_bouldin_score: float
    intra_cluster_variance: float
    inter_cluster_separation: float
    coherence_ratio: float
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            'silhouette_score': self.silhouette_score,
            'calinski_harabasz_score': self.calinski_harabasz_score,
            'davies_bouldin_score': self.davies_bouldin_score,
            'intra_cluster_variance': self.intra_cluster_variance,
            'inter_cluster_separation': self.inter_cluster_separation,
            'coherence_ratio': self.coherence_ratio
        }


@dataclass
class QualityAssessmentReport:
    """质量评估报告"""
    timestamp: str
    system_count: int
    total_terms: int
    clustering_metrics: ClusteringMetrics
    coherence_report: CoherenceReport
    system_statistics: Dict[str, Dict[str, Any]]
    visualization_paths: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def save_to_json(self, output_path: str):
        """保存报告为JSON格式"""
        report_dict = {
            'timestamp': self.timestamp,
            'system_count': self.system_count,
            'total_terms': self.total_terms,
            'clustering_metrics': self.clustering_metrics.to_dict(),
            'coherence_summary': {
                'avg_intra_similarity': self.coherence_report.avg_intra_similarity,
                'avg_inter_similarity': self.coherence_report.avg_inter_similarity,
                'coherence_ratio': self.coherence_report.coherence_ratio,
                'validation_passed': self.coherence_report.validation_passed,
                'clustering_quality_score': self.coherence_report.clustering_quality_score
            },
            'system_statistics': self.system_statistics,
            'visualization_paths': self.visualization_paths,
            'recommendations': self.recommendations
        }
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"质量评估报告已保存到: {output_path}")


class ClusteringQualityEvaluator:
    """
    聚类质量评估器
    
    综合评估五大系统分类的聚类质量，包括语义一致性、统计指标和可视化分析。
    """
    
    def __init__(self, 
                 semantic_validator: Optional[SemanticCoherenceValidator] = None,
                 output_dir: str = "results/clustering_quality"):
        """
        初始化聚类质量评估器
        
        Args:
            semantic_validator: 语义一致性验证器
            output_dir: 输出目录
        """
        self.semantic_validator = semantic_validator
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置matplotlib中文字体
        plt.rcParams['font.family'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        logger.info(f"初始化聚类质量评估器，输出目录: {self.output_dir}")
    
    def evaluate_clustering_quality(self, 
                                  system_terms: Dict[str, List[str]],
                                  generate_visualizations: bool = True,
                                  save_detailed_report: bool = True) -> QualityAssessmentReport:
        """
        评估聚类质量
        
        Args:
            system_terms: 系统名称到GO条目ID列表的映射
            generate_visualizations: 是否生成可视化图表
            save_detailed_report: 是否保存详细报告
            
        Returns:
            质量评估报告
        """
        logger.info("开始聚类质量评估...")
        
        # 1. 语义一致性验证
        if self.semantic_validator is None:
            raise ValueError("需要设置语义一致性验证器")
        
        coherence_report = self.semantic_validator.validate_clustering_quality(system_terms)
        
        # 2. 计算聚类指标
        clustering_metrics = self._calculate_clustering_metrics(system_terms, coherence_report)
        
        # 3. 计算系统统计信息
        system_statistics = self._calculate_system_statistics(system_terms, coherence_report)
        
        # 4. 生成可视化
        visualization_paths = []
        if generate_visualizations:
            visualization_paths = self._generate_visualizations(
                system_terms, coherence_report, clustering_metrics
            )
        
        # 5. 生成建议
        recommendations = self._generate_recommendations(coherence_report, clustering_metrics)
        
        # 6. 创建报告
        report = QualityAssessmentReport(
            timestamp=datetime.now().isoformat(),
            system_count=len(system_terms),
            total_terms=sum(len(terms) for terms in system_terms.values()),
            clustering_metrics=clustering_metrics,
            coherence_report=coherence_report,
            system_statistics=system_statistics,
            visualization_paths=visualization_paths,
            recommendations=recommendations
        )
        
        # 7. 保存详细报告
        if save_detailed_report:
            self._save_detailed_report(report)
        
        logger.info("聚类质量评估完成")
        return report
    
    def _calculate_clustering_metrics(self, 
                                    system_terms: Dict[str, List[str]],
                                    coherence_report: CoherenceReport) -> ClusteringMetrics:
        """计算聚类质量指标"""
        logger.info("计算聚类质量指标...")
        
        # 基于语义相似度的轮廓系数
        silhouette_score = self._calculate_semantic_silhouette_score(coherence_report)
        
        # Calinski-Harabasz指数（类间分散度/类内分散度）
        calinski_harabasz_score = self._calculate_calinski_harabasz_score(coherence_report)
        
        # Davies-Bouldin指数（越小越好）
        davies_bouldin_score = self._calculate_davies_bouldin_score(coherence_report)
        
        # 类内方差
        intra_cluster_variance = self._calculate_intra_cluster_variance(coherence_report)
        
        # 类间分离度
        inter_cluster_separation = self._calculate_inter_cluster_separation(coherence_report)
        
        # 一致性比值
        coherence_ratio = coherence_report.coherence_ratio
        
        return ClusteringMetrics(
            silhouette_score=silhouette_score,
            calinski_harabasz_score=calinski_harabasz_score,
            davies_bouldin_score=davies_bouldin_score,
            intra_cluster_variance=intra_cluster_variance,
            inter_cluster_separation=inter_cluster_separation,
            coherence_ratio=coherence_ratio
        )
    
    def _calculate_semantic_silhouette_score(self, coherence_report: CoherenceReport) -> float:
        """计算基于语义相似度的轮廓系数"""
        if not coherence_report.intra_system_similarity or not coherence_report.inter_system_similarity:
            return 0.0
        
        # 对每个系统计算轮廓系数
        silhouette_scores = []
        
        for system_name, intra_stats in coherence_report.intra_system_similarity.items():
            # 该系统的内部相似度（越高越好）
            a = 1 - intra_stats.mean  # 转换为距离
            
            # 该系统与其他系统的最小平均相似度
            min_inter_sim = float('inf')
            for pair_key, inter_stats in coherence_report.inter_system_similarity.items():
                if system_name in pair_key:
                    min_inter_sim = min(min_inter_sim, inter_stats.mean)
            
            if min_inter_sim == float('inf'):
                continue
            
            b = 1 - min_inter_sim  # 转换为距离
            
            # 轮廓系数
            if max(a, b) > 0:
                silhouette = (b - a) / max(a, b)
                silhouette_scores.append(silhouette)
        
        return np.mean(silhouette_scores) if silhouette_scores else 0.0
    
    def _calculate_calinski_harabasz_score(self, coherence_report: CoherenceReport) -> float:
        """计算Calinski-Harabasz指数"""
        if len(coherence_report.intra_system_similarity) < 2:
            return 0.0
        
        # 类间分散度
        inter_cluster_dispersion = np.var([
            stats.mean for stats in coherence_report.inter_system_similarity.values()
        ])
        
        # 类内分散度
        intra_cluster_dispersion = np.mean([
            stats.std ** 2 for stats in coherence_report.intra_system_similarity.values()
        ])
        
        if intra_cluster_dispersion == 0:
            return float('inf') if inter_cluster_dispersion > 0 else 0.0
        
        n_clusters = len(coherence_report.intra_system_similarity)
        return inter_cluster_dispersion / intra_cluster_dispersion * (n_clusters - 1)
    
    def _calculate_davies_bouldin_score(self, coherence_report: CoherenceReport) -> float:
        """计算Davies-Bouldin指数"""
        systems = list(coherence_report.intra_system_similarity.keys())
        if len(systems) < 2:
            return 0.0
        
        db_scores = []
        
        for i, sys1 in enumerate(systems):
            max_ratio = 0.0
            
            for j, sys2 in enumerate(systems):
                if i != j:
                    # 系统内分散度
                    s1 = coherence_report.intra_system_similarity[sys1].std
                    s2 = coherence_report.intra_system_similarity[sys2].std
                    
                    # 系统间距离
                    pair_key1 = f"{sys1} vs {sys2}"
                    pair_key2 = f"{sys2} vs {sys1}"
                    
                    if pair_key1 in coherence_report.inter_system_similarity:
                        d12 = 1 - coherence_report.inter_system_similarity[pair_key1].mean
                    elif pair_key2 in coherence_report.inter_system_similarity:
                        d12 = 1 - coherence_report.inter_system_similarity[pair_key2].mean
                    else:
                        continue
                    
                    if d12 > 0:
                        ratio = (s1 + s2) / d12
                        max_ratio = max(max_ratio, ratio)
            
            db_scores.append(max_ratio)
        
        return np.mean(db_scores) if db_scores else 0.0
    
    def _calculate_intra_cluster_variance(self, coherence_report: CoherenceReport) -> float:
        """计算类内方差"""
        variances = [stats.std ** 2 for stats in coherence_report.intra_system_similarity.values()]
        return np.mean(variances) if variances else 0.0
    
    def _calculate_inter_cluster_separation(self, coherence_report: CoherenceReport) -> float:
        """计算类间分离度"""
        separations = [1 - stats.mean for stats in coherence_report.inter_system_similarity.values()]
        return np.mean(separations) if separations else 0.0
    
    def _calculate_system_statistics(self, 
                                   system_terms: Dict[str, List[str]],
                                   coherence_report: CoherenceReport) -> Dict[str, Dict[str, Any]]:
        """计算系统统计信息"""
        logger.info("计算系统统计信息...")
        
        statistics = {}
        
        for system_name, terms in system_terms.items():
            stats = {
                'term_count': len(terms),
                'percentage': len(terms) / sum(len(t) for t in system_terms.values()) * 100
            }
            
            # 添加语义相似度统计
            if system_name in coherence_report.intra_system_similarity:
                intra_stats = coherence_report.intra_system_similarity[system_name]
                stats.update({
                    'intra_similarity_mean': intra_stats.mean,
                    'intra_similarity_std': intra_stats.std,
                    'intra_similarity_median': intra_stats.median,
                    'intra_pairs_count': intra_stats.n_pairs
                })
            
            # 计算与其他系统的平均相似度
            inter_similarities = []
            for pair_key, inter_stats in coherence_report.inter_system_similarity.items():
                if system_name in pair_key:
                    inter_similarities.append(inter_stats.mean)
            
            if inter_similarities:
                stats.update({
                    'avg_inter_similarity': np.mean(inter_similarities),
                    'min_inter_similarity': np.min(inter_similarities),
                    'max_inter_similarity': np.max(inter_similarities)
                })
            
            statistics[system_name] = stats
        
        return statistics
    
    def _generate_visualizations(self, 
                               system_terms: Dict[str, List[str]],
                               coherence_report: CoherenceReport,
                               clustering_metrics: ClusteringMetrics) -> List[str]:
        """生成可视化图表"""
        logger.info("生成可视化图表...")
        
        visualization_paths = []
        
        # 1. 相似度对比图
        similarity_comparison_path = self._plot_similarity_comparison(coherence_report)
        visualization_paths.append(similarity_comparison_path)
        
        # 2. 系统统计图
        system_stats_path = self._plot_system_statistics(system_terms, coherence_report)
        visualization_paths.append(system_stats_path)
        
        # 3. 聚类质量指标雷达图
        metrics_radar_path = self._plot_clustering_metrics_radar(clustering_metrics)
        visualization_paths.append(metrics_radar_path)
        
        # 4. 相似度热图
        heatmap_path = self._plot_similarity_heatmap(coherence_report)
        visualization_paths.append(heatmap_path)
        
        return visualization_paths
    
    def _plot_similarity_comparison(self, coherence_report: CoherenceReport) -> str:
        """绘制相似度对比图"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # 左图：系统内部相似度箱线图
        intra_data = []
        intra_labels = []
        for system_name, stats in coherence_report.intra_system_similarity.items():
            if stats.values:
                intra_data.append(stats.values)
                intra_labels.append(system_name)
        
        if intra_data:
            bp1 = ax1.boxplot(intra_data, labels=intra_labels, patch_artist=True,
                             boxprops=dict(facecolor='lightblue', alpha=0.7),
                             medianprops=dict(color='red', linewidth=2))
        
        ax1.set_ylabel('Semantic Similarity', fontsize=12, fontweight='bold')
        ax1.set_xlabel('System', fontsize=12, fontweight='bold')
        ax1.set_title('Intra-System Similarity\n(Within System)', fontsize=14, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)
        ax1.set_ylim([0, 1])
        
        # 右图：系统间相似度对比
        inter_means = [stats.mean for stats in coherence_report.inter_system_similarity.values()]
        inter_labels = list(coherence_report.inter_system_similarity.keys())
        
        if inter_means:
            bars = ax2.bar(range(len(inter_means)), inter_means, 
                          color='lightcoral', alpha=0.7)
            ax2.set_xticks(range(len(inter_labels)))
            ax2.set_xticklabels(inter_labels, rotation=45, ha='right')
        
        ax2.set_ylabel('Mean Similarity', fontsize=12, fontweight='bold')
        ax2.set_xlabel('System Pairs', fontsize=12, fontweight='bold')
        ax2.set_title('Inter-System Similarity\n(Between Systems)', fontsize=14, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)
        ax2.set_ylim([0, 1])
        
        plt.tight_layout()
        
        output_path = self.output_dir / 'similarity_comparison.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"相似度对比图已保存: {output_path}")
        return str(output_path)
    
    def _plot_system_statistics(self, 
                              system_terms: Dict[str, List[str]],
                              coherence_report: CoherenceReport) -> str:
        """绘制系统统计图"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # 左图：系统条目数量
        systems = list(system_terms.keys())
        counts = [len(terms) for terms in system_terms.values()]
        
        bars1 = ax1.bar(systems, counts, color='skyblue', alpha=0.7)
        ax1.set_ylabel('Number of Terms', fontsize=12, fontweight='bold')
        ax1.set_xlabel('System', fontsize=12, fontweight='bold')
        ax1.set_title('Terms per System', fontsize=14, fontweight='bold')
        
        # 添加数值标签
        for bar, count in zip(bars1, counts):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(counts)*0.01,
                    str(count), ha='center', va='bottom', fontweight='bold')
        
        # 右图：系统内相似度对比
        intra_means = []
        intra_systems = []
        for system_name in systems:
            if system_name in coherence_report.intra_system_similarity:
                intra_means.append(coherence_report.intra_system_similarity[system_name].mean)
                intra_systems.append(system_name)
        
        if intra_means:
            bars2 = ax2.bar(intra_systems, intra_means, color='lightgreen', alpha=0.7)
            ax2.set_ylabel('Mean Intra-System Similarity', fontsize=12, fontweight='bold')
            ax2.set_xlabel('System', fontsize=12, fontweight='bold')
            ax2.set_title('Intra-System Coherence', fontsize=14, fontweight='bold')
            ax2.set_ylim([0, 1])
            
            # 添加数值标签
            for bar, mean_val in zip(bars2, intra_means):
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                        f'{mean_val:.3f}', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        
        output_path = self.output_dir / 'system_statistics.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"系统统计图已保存: {output_path}")
        return str(output_path)
    
    def _plot_clustering_metrics_radar(self, clustering_metrics: ClusteringMetrics) -> str:
        """绘制聚类质量指标雷达图"""
        # 准备数据
        metrics_dict = clustering_metrics.to_dict()
        
        # 归一化指标到[0,1]范围
        normalized_metrics = {}
        for key, value in metrics_dict.items():
            if key == 'davies_bouldin_score':
                # Davies-Bouldin越小越好，需要反转
                normalized_metrics[key] = max(0, 1 - min(value, 2) / 2)
            elif key == 'coherence_ratio':
                # 一致性比值，归一化到[0,1]
                normalized_metrics[key] = min(value / 5, 1)  # 假设5是很好的比值
            else:
                # 其他指标直接使用或限制在[0,1]
                normalized_metrics[key] = max(0, min(value, 1))
        
        # 创建雷达图
        labels = [
            'Silhouette Score',
            'Calinski-Harabasz',
            'Davies-Bouldin (inv)',
            'Intra Variance (inv)',
            'Inter Separation',
            'Coherence Ratio'
        ]
        
        values = [
            normalized_metrics['silhouette_score'],
            normalized_metrics['calinski_harabasz_score'] / 100,  # 缩放
            normalized_metrics['davies_bouldin_score'],
            1 - normalized_metrics['intra_cluster_variance'],  # 反转
            normalized_metrics['inter_cluster_separation'],
            normalized_metrics['coherence_ratio']
        ]
        
        # 计算角度
        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
        values += values[:1]  # 闭合图形
        angles += angles[:1]
        
        # 绘制雷达图
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        ax.plot(angles, values, 'o-', linewidth=2, label='Clustering Quality', color='blue')
        ax.fill(angles, values, alpha=0.25, color='blue')
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, fontsize=11)
        ax.set_ylim(0, 1)
        ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], fontsize=10)
        ax.grid(True)
        
        plt.title('Clustering Quality Metrics\n(Normalized)', size=16, fontweight='bold', pad=20)
        plt.legend(loc='upper right', bbox_to_anchor=(1.2, 1.0))
        
        output_path = self.output_dir / 'clustering_metrics_radar.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"聚类指标雷达图已保存: {output_path}")
        return str(output_path)
    
    def _plot_similarity_heatmap(self, coherence_report: CoherenceReport) -> str:
        """绘制相似度热图"""
        # 构建相似度矩阵
        systems = list(coherence_report.intra_system_similarity.keys())
        n_systems = len(systems)
        
        if n_systems == 0:
            logger.warning("没有系统数据，跳过热图生成")
            return ""
        
        similarity_matrix = np.zeros((n_systems, n_systems))
        
        # 填充对角线（系统内相似度）
        for i, system in enumerate(systems):
            if system in coherence_report.intra_system_similarity:
                similarity_matrix[i, i] = coherence_report.intra_system_similarity[system].mean
        
        # 填充非对角线（系统间相似度）
        for i, sys1 in enumerate(systems):
            for j, sys2 in enumerate(systems):
                if i != j:
                    pair_key1 = f"{sys1} vs {sys2}"
                    pair_key2 = f"{sys2} vs {sys1}"
                    
                    if pair_key1 in coherence_report.inter_system_similarity:
                        similarity_matrix[i, j] = coherence_report.inter_system_similarity[pair_key1].mean
                    elif pair_key2 in coherence_report.inter_system_similarity:
                        similarity_matrix[i, j] = coherence_report.inter_system_similarity[pair_key2].mean
        
        # 绘制热图
        plt.figure(figsize=(10, 8))
        
        mask = similarity_matrix == 0
        sns.heatmap(similarity_matrix, 
                   annot=True, 
                   fmt='.3f',
                   cmap='RdYlGn',
                   vmin=0, 
                   vmax=1,
                   xticklabels=systems,
                   yticklabels=systems,
                   mask=mask,
                   cbar_kws={'label': 'Semantic Similarity'})
        
        plt.title('System Similarity Matrix\n(Diagonal: Intra-system, Off-diagonal: Inter-system)', 
                 fontsize=14, fontweight='bold', pad=20)
        plt.xlabel('System', fontsize=12, fontweight='bold')
        plt.ylabel('System', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        
        output_path = self.output_dir / 'similarity_heatmap.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"相似度热图已保存: {output_path}")
        return str(output_path)
    
    def _generate_recommendations(self, 
                                coherence_report: CoherenceReport,
                                clustering_metrics: ClusteringMetrics) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于一致性比值的建议
        if coherence_report.coherence_ratio < 1.5:
            recommendations.append(
                "一致性比值较低，建议优化分类规则以提高系统内相似度或降低系统间相似度"
            )
        elif coherence_report.coherence_ratio > 5.0:
            recommendations.append(
                "一致性比值很高，分类质量良好，可以考虑进一步细化子系统分类"
            )
        
        # 基于轮廓系数的建议
        if clustering_metrics.silhouette_score < 0.3:
            recommendations.append(
                "轮廓系数较低，建议检查分类边界模糊的条目，可能需要重新分类"
            )
        elif clustering_metrics.silhouette_score > 0.7:
            recommendations.append(
                "轮廓系数很高，聚类质量优秀"
            )
        
        # 基于Davies-Bouldin指数的建议
        if clustering_metrics.davies_bouldin_score > 1.0:
            recommendations.append(
                "Davies-Bouldin指数较高，系统间区分度不够，建议优化分类规则"
            )
        
        # 基于系统大小不平衡的建议
        system_sizes = [stats.n_pairs for stats in coherence_report.intra_system_similarity.values()]
        if system_sizes and (max(system_sizes) / min(system_sizes) > 10):
            recommendations.append(
                "系统大小不平衡，建议考虑合并小系统或拆分大系统"
            )
        
        # 基于验证结果的建议
        if not coherence_report.validation_passed:
            recommendations.append(
                "语义一致性验证未通过，建议重新审视分类规则和系统定义"
            )
        else:
            recommendations.append(
                "语义一致性验证通过，分类系统具有良好的生物学合理性"
            )
        
        return recommendations
    
    def _save_detailed_report(self, report: QualityAssessmentReport):
        """保存详细报告"""
        # 保存JSON格式报告
        json_path = self.output_dir / 'quality_assessment_report.json'
        report.save_to_json(str(json_path))
        
        # 保存Markdown格式报告
        markdown_path = self.output_dir / 'quality_assessment_report.md'
        markdown_content = self._generate_markdown_report(report)
        
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logger.info(f"详细报告已保存: {json_path}, {markdown_path}")
    
    def _generate_markdown_report(self, report: QualityAssessmentReport) -> str:
        """生成Markdown格式报告"""
        lines = []
        
        lines.append("# 聚类质量评估报告")
        lines.append("")
        lines.append(f"**生成时间**: {report.timestamp}")
        lines.append(f"**系统数量**: {report.system_count}")
        lines.append(f"**总条目数**: {report.total_terms}")
        lines.append("")
        
        # 聚类质量指标
        lines.append("## 聚类质量指标")
        lines.append("")
        metrics = report.clustering_metrics
        lines.append("| 指标 | 数值 | 说明 |")
        lines.append("|------|------|------|")
        lines.append(f"| 轮廓系数 | {metrics.silhouette_score:.4f} | 越高越好，>0.5为良好 |")
        lines.append(f"| Calinski-Harabasz指数 | {metrics.calinski_harabasz_score:.4f} | 越高越好 |")
        lines.append(f"| Davies-Bouldin指数 | {metrics.davies_bouldin_score:.4f} | 越低越好，<1为良好 |")
        lines.append(f"| 类内方差 | {metrics.intra_cluster_variance:.4f} | 越低越好 |")
        lines.append(f"| 类间分离度 | {metrics.inter_cluster_separation:.4f} | 越高越好 |")
        lines.append(f"| 一致性比值 | {metrics.coherence_ratio:.4f} | >1.5为良好 |")
        lines.append("")
        
        # 语义一致性摘要
        coherence = report.coherence_report
        lines.append("## 语义一致性摘要")
        lines.append("")
        lines.append(f"- **平均系统内相似度**: {coherence.avg_intra_similarity:.4f}")
        lines.append(f"- **平均系统间相似度**: {coherence.avg_inter_similarity:.4f}")
        lines.append(f"- **一致性比值**: {coherence.coherence_ratio:.2f}x")
        lines.append(f"- **聚类质量得分**: {coherence.clustering_quality_score:.4f}")
        lines.append(f"- **验证结果**: {'✅ 通过' if coherence.validation_passed else '⚠️ 未通过'}")
        lines.append("")
        
        # 系统统计
        lines.append("## 系统统计")
        lines.append("")
        lines.append("| 系统 | 条目数 | 占比(%) | 系统内相似度 | 平均系统间相似度 |")
        lines.append("|------|--------|---------|--------------|------------------|")
        
        for system_name, stats in report.system_statistics.items():
            intra_sim = stats.get('intra_similarity_mean', 0)
            inter_sim = stats.get('avg_inter_similarity', 0)
            lines.append(f"| {system_name} | {stats['term_count']} | "
                        f"{stats['percentage']:.1f} | {intra_sim:.4f} | {inter_sim:.4f} |")
        
        lines.append("")
        
        # 改进建议
        lines.append("## 改进建议")
        lines.append("")
        for i, recommendation in enumerate(report.recommendations, 1):
            lines.append(f"{i}. {recommendation}")
        
        lines.append("")
        
        # 可视化文件
        if report.visualization_paths:
            lines.append("## 生成的可视化文件")
            lines.append("")
            for path in report.visualization_paths:
                filename = Path(path).name
                lines.append(f"- {filename}")
        
        return '\n'.join(lines)
    
    def compare_multiple_classifications(self, 
                                       classifications: Dict[str, Dict[str, List[str]]],
                                       output_prefix: str = "comparison") -> Dict[str, QualityAssessmentReport]:
        """
        比较多个分类方案的质量
        
        Args:
            classifications: 分类方案名称到系统条目映射的字典
            output_prefix: 输出文件前缀
            
        Returns:
            每个分类方案的质量评估报告
        """
        logger.info(f"比较 {len(classifications)} 个分类方案...")
        
        reports = {}
        
        for name, system_terms in classifications.items():
            logger.info(f"评估分类方案: {name}")
            
            # 为每个方案创建单独的输出目录
            method_output_dir = self.output_dir / f"{output_prefix}_{name}"
            method_evaluator = ClusteringQualityEvaluator(
                semantic_validator=self.semantic_validator,
                output_dir=str(method_output_dir)
            )
            
            report = method_evaluator.evaluate_clustering_quality(
                system_terms, 
                generate_visualizations=True,
                save_detailed_report=True
            )
            
            reports[name] = report
        
        # 生成比较报告
        self._generate_comparison_report(reports, output_prefix)
        
        return reports
    
    def _generate_comparison_report(self, 
                                  reports: Dict[str, QualityAssessmentReport],
                                  output_prefix: str):
        """生成比较报告"""
        comparison_data = []
        
        for name, report in reports.items():
            comparison_data.append({
                'Method': name,
                'System Count': report.system_count,
                'Total Terms': report.total_terms,
                'Silhouette Score': report.clustering_metrics.silhouette_score,
                'Coherence Ratio': report.clustering_metrics.coherence_ratio,
                'Validation Passed': report.coherence_report.validation_passed,
                'Avg Intra Similarity': report.coherence_report.avg_intra_similarity,
                'Avg Inter Similarity': report.coherence_report.avg_inter_similarity
            })
        
        # 保存比较表格
        df = pd.DataFrame(comparison_data)
        csv_path = self.output_dir / f"{output_prefix}_comparison.csv"
        df.to_csv(csv_path, index=False)
        
        # 生成比较可视化
        self._plot_method_comparison(df, output_prefix)
        
        logger.info(f"比较报告已保存: {csv_path}")
    
    def _plot_method_comparison(self, df: pd.DataFrame, output_prefix: str):
        """绘制方法比较图"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # 轮廓系数比较
        axes[0, 0].bar(df['Method'], df['Silhouette Score'], color='skyblue', alpha=0.7)
        axes[0, 0].set_title('Silhouette Score Comparison', fontweight='bold')
        axes[0, 0].set_ylabel('Silhouette Score')
        axes[0, 0].tick_params(axis='x', rotation=45)
        
        # 一致性比值比较
        axes[0, 1].bar(df['Method'], df['Coherence Ratio'], color='lightgreen', alpha=0.7)
        axes[0, 1].set_title('Coherence Ratio Comparison', fontweight='bold')
        axes[0, 1].set_ylabel('Coherence Ratio')
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # 系统内外相似度比较
        x = np.arange(len(df))
        width = 0.35
        
        axes[1, 0].bar(x - width/2, df['Avg Intra Similarity'], width, 
                      label='Intra-system', color='orange', alpha=0.7)
        axes[1, 0].bar(x + width/2, df['Avg Inter Similarity'], width,
                      label='Inter-system', color='red', alpha=0.7)
        axes[1, 0].set_title('Similarity Comparison', fontweight='bold')
        axes[1, 0].set_ylabel('Average Similarity')
        axes[1, 0].set_xticks(x)
        axes[1, 0].set_xticklabels(df['Method'], rotation=45)
        axes[1, 0].legend()
        
        # 验证通过率
        validation_counts = df['Validation Passed'].value_counts()
        axes[1, 1].pie(validation_counts.values, labels=validation_counts.index, 
                      autopct='%1.1f%%', startangle=90)
        axes[1, 1].set_title('Validation Pass Rate', fontweight='bold')
        
        plt.tight_layout()
        
        output_path = self.output_dir / f"{output_prefix}_comparison.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"方法比较图已保存: {output_path}")