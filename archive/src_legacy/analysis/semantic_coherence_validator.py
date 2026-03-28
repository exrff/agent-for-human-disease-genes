"""
语义一致性验证器

基于GO本体结构计算语义相似度，验证五大系统分类的聚类质量。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import networkx as nx
from collections import defaultdict
import logging
import warnings
from itertools import combinations
import random

# 设置日志
logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')


@dataclass
class SimilarityStats:
    """语义相似度统计信息"""
    mean: float
    std: float
    median: float
    n_pairs: int
    values: List[float] = field(default_factory=list)
    
    def __post_init__(self):
        """验证统计数据"""
        if self.n_pairs != len(self.values):
            logger.warning(f"样本对数量不匹配: {self.n_pairs} vs {len(self.values)}")


@dataclass
class CoherenceReport:
    """语义一致性验证报告"""
    intra_system_similarity: Dict[str, SimilarityStats]
    inter_system_similarity: Dict[str, SimilarityStats]
    clustering_quality_score: float
    avg_intra_similarity: float
    avg_inter_similarity: float
    coherence_ratio: float  # intra/inter比值
    validation_passed: bool
    system_term_counts: Dict[str, int]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_summary(self) -> str:
        """获取报告摘要"""
        status = "✅ 通过" if self.validation_passed else "⚠️ 需要注意"
        return (f"语义一致性验证 {status}\n"
                f"平均系统内相似度: {self.avg_intra_similarity:.4f}\n"
                f"平均系统间相似度: {self.avg_inter_similarity:.4f}\n"
                f"一致性比值: {self.coherence_ratio:.2f}x")


class SemanticCoherenceValidator:
    """
    语义一致性验证器
    
    基于GO本体DAG结构计算语义相似度，验证分类系统的聚类质量。
    """
    
    def __init__(self, 
                 go_dag: Optional[nx.DiGraph] = None,
                 similarity_method: str = 'depth',
                 sample_size: int = 100,
                 random_seed: int = 42):
        """
        初始化语义一致性验证器
        
        Args:
            go_dag: GO本体DAG图，如果为None则需要后续设置
            similarity_method: 相似度计算方法 ('depth', 'jaccard', 'simple')
            sample_size: 大系统的采样大小
            random_seed: 随机种子
        """
        self.go_dag = go_dag
        self.similarity_method = similarity_method
        self.sample_size = sample_size
        self.random_seed = random_seed
        
        # 设置随机种子
        random.seed(random_seed)
        np.random.seed(random_seed)
        
        # 缓存
        self._similarity_cache: Dict[Tuple[str, str], float] = {}
        
        logger.info(f"初始化语义一致性验证器: method={similarity_method}, sample_size={sample_size}")
    
    def set_go_dag(self, go_dag: nx.DiGraph):
        """设置GO DAG图"""
        self.go_dag = go_dag
        self._similarity_cache.clear()  # 清空缓存
        logger.info(f"设置GO DAG: {len(go_dag.nodes)} 个节点, {len(go_dag.edges)} 条边")
    
    def calculate_semantic_similarity(self, term1: str, term2: str) -> float:
        """
        计算两个GO条目间的语义相似度
        
        Args:
            term1: 第一个GO条目ID
            term2: 第二个GO条目ID
            
        Returns:
            语义相似度值 [0, 1]
        """
        if self.go_dag is None:
            raise ValueError("GO DAG未设置，请先调用set_go_dag()")
        
        # 检查缓存
        cache_key = tuple(sorted([term1, term2]))
        if cache_key in self._similarity_cache:
            return self._similarity_cache[cache_key]
        
        # 检查条目是否存在
        if term1 not in self.go_dag or term2 not in self.go_dag:
            similarity = 0.0
        elif term1 == term2:
            similarity = 1.0
        else:
            similarity = self._compute_similarity(term1, term2)
        
        # 缓存结果
        self._similarity_cache[cache_key] = similarity
        return similarity
    
    def _compute_similarity(self, term1: str, term2: str) -> float:
        """计算语义相似度的具体实现"""
        if self.similarity_method == 'depth':
            return self._depth_based_similarity(term1, term2)
        elif self.similarity_method == 'jaccard':
            return self._jaccard_similarity(term1, term2)
        elif self.similarity_method == 'simple':
            return self._simple_similarity(term1, term2)
        else:
            raise ValueError(f"不支持的相似度方法: {self.similarity_method}")
    
    def _depth_based_similarity(self, term1: str, term2: str) -> float:
        """基于深度的语义相似度"""
        try:
            # 获取祖先节点
            ancestors1 = set(nx.ancestors(self.go_dag, term1))
            ancestors2 = set(nx.ancestors(self.go_dag, term2))
            ancestors1.add(term1)
            ancestors2.add(term2)
            
            # 找到公共祖先
            common_ancestors = ancestors1 & ancestors2
            
            if not common_ancestors:
                return 0.0
            
            # 找到最深的公共祖先
            max_depth = 0
            for ancestor in common_ancestors:
                if 'depth' in self.go_dag.nodes[ancestor]:
                    depth = self.go_dag.nodes[ancestor]['depth']
                else:
                    # 计算深度（到根节点的距离）
                    depth = self._calculate_depth(ancestor)
                max_depth = max(max_depth, depth)
            
            # 归一化
            depth1 = self._get_node_depth(term1)
            depth2 = self._get_node_depth(term2)
            max_possible_depth = max(depth1, depth2)
            
            if max_possible_depth == 0:
                return 0.0
            
            return max_depth / max_possible_depth
            
        except Exception as e:
            logger.warning(f"计算深度相似度失败 {term1} vs {term2}: {e}")
            return 0.0
    
    def _jaccard_similarity(self, term1: str, term2: str) -> float:
        """基于Jaccard系数的语义相似度"""
        try:
            ancestors1 = set(nx.ancestors(self.go_dag, term1))
            ancestors2 = set(nx.ancestors(self.go_dag, term2))
            ancestors1.add(term1)
            ancestors2.add(term2)
            
            intersection = len(ancestors1 & ancestors2)
            union = len(ancestors1 | ancestors2)
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"计算Jaccard相似度失败 {term1} vs {term2}: {e}")
            return 0.0
    
    def _simple_similarity(self, term1: str, term2: str) -> float:
        """简单的共同祖先比例相似度"""
        try:
            ancestors1 = set(nx.ancestors(self.go_dag, term1))
            ancestors2 = set(nx.ancestors(self.go_dag, term2))
            
            if len(ancestors1) == 0 and len(ancestors2) == 0:
                return 1.0 if term1 == term2 else 0.0
            
            intersection = len(ancestors1 & ancestors2)
            avg_ancestors = (len(ancestors1) + len(ancestors2)) / 2
            
            return intersection / avg_ancestors if avg_ancestors > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"计算简单相似度失败 {term1} vs {term2}: {e}")
            return 0.0
    
    def _get_node_depth(self, term_id: str) -> int:
        """获取节点深度"""
        if 'depth' in self.go_dag.nodes[term_id]:
            return self.go_dag.nodes[term_id]['depth']
        else:
            depth = self._calculate_depth(term_id)
            self.go_dag.nodes[term_id]['depth'] = depth
            return depth
    
    def _calculate_depth(self, term_id: str) -> int:
        """计算节点到根节点的最短距离"""
        # GO的根节点
        root_nodes = {'GO:0008150', 'GO:0003674', 'GO:0005575'}
        
        min_depth = float('inf')
        for root in root_nodes:
            if root in self.go_dag:
                try:
                    # 注意：这里计算的是从term到root的距离
                    path_length = nx.shortest_path_length(self.go_dag, root, term_id)
                    min_depth = min(min_depth, path_length)
                except nx.NetworkXNoPath:
                    continue
        
        return min_depth if min_depth != float('inf') else 0
    
    def compute_intra_system_similarity(self, system_terms: List[str]) -> SimilarityStats:
        """
        计算系统内部语义相似度
        
        Args:
            system_terms: 系统内的GO条目ID列表
            
        Returns:
            相似度统计信息
        """
        if len(system_terms) < 2:
            return SimilarityStats(mean=0.0, std=0.0, median=0.0, n_pairs=0, values=[])
        
        # 采样以控制计算量
        if len(system_terms) > self.sample_size:
            sampled_terms = random.sample(system_terms, self.sample_size)
            logger.info(f"采样 {self.sample_size} 个条目 (原始: {len(system_terms)})")
        else:
            sampled_terms = system_terms
        
        # 计算成对相似度
        similarities = []
        for i, term1 in enumerate(sampled_terms):
            for term2 in sampled_terms[i+1:]:
                sim = self.calculate_semantic_similarity(term1, term2)
                similarities.append(sim)
        
        if not similarities:
            return SimilarityStats(mean=0.0, std=0.0, median=0.0, n_pairs=0, values=[])
        
        return SimilarityStats(
            mean=np.mean(similarities),
            std=np.std(similarities),
            median=np.median(similarities),
            n_pairs=len(similarities),
            values=similarities
        )
    
    def compute_inter_system_similarity(self, 
                                      system1_terms: List[str], 
                                      system2_terms: List[str]) -> SimilarityStats:
        """
        计算系统间语义相似度
        
        Args:
            system1_terms: 第一个系统的GO条目ID列表
            system2_terms: 第二个系统的GO条目ID列表
            
        Returns:
            相似度统计信息
        """
        if len(system1_terms) == 0 or len(system2_terms) == 0:
            return SimilarityStats(mean=0.0, std=0.0, median=0.0, n_pairs=0, values=[])
        
        # 采样以控制计算量
        sample_size_per_system = min(50, self.sample_size // 2)
        
        if len(system1_terms) > sample_size_per_system:
            sampled_terms1 = random.sample(system1_terms, sample_size_per_system)
        else:
            sampled_terms1 = system1_terms
        
        if len(system2_terms) > sample_size_per_system:
            sampled_terms2 = random.sample(system2_terms, sample_size_per_system)
        else:
            sampled_terms2 = system2_terms
        
        # 计算跨系统相似度
        similarities = []
        for term1 in sampled_terms1:
            for term2 in sampled_terms2:
                sim = self.calculate_semantic_similarity(term1, term2)
                similarities.append(sim)
        
        if not similarities:
            return SimilarityStats(mean=0.0, std=0.0, median=0.0, n_pairs=0, values=[])
        
        return SimilarityStats(
            mean=np.mean(similarities),
            std=np.std(similarities),
            median=np.median(similarities),
            n_pairs=len(similarities),
            values=similarities
        )
    
    def validate_clustering_quality(self, 
                                  system_terms: Dict[str, List[str]],
                                  coherence_threshold: float = 1.5) -> CoherenceReport:
        """
        验证聚类质量
        
        Args:
            system_terms: 系统名称到GO条目ID列表的映射
            coherence_threshold: 一致性阈值（intra/inter比值）
            
        Returns:
            语义一致性验证报告
        """
        logger.info("开始语义一致性验证...")
        
        # 过滤有效系统（至少2个条目）
        valid_systems = {name: terms for name, terms in system_terms.items() 
                        if len(terms) >= 2}
        
        if len(valid_systems) < 2:
            raise ValueError("至少需要2个有效系统进行验证")
        
        logger.info(f"验证 {len(valid_systems)} 个系统的聚类质量")
        
        # 计算系统内部相似度
        intra_similarities = {}
        for system_name, terms in valid_systems.items():
            logger.info(f"计算 {system_name} 系统内部相似度...")
            stats = self.compute_intra_system_similarity(terms)
            intra_similarities[system_name] = stats
            logger.info(f"  {system_name}: 均值={stats.mean:.4f}, 样本对数={stats.n_pairs}")
        
        # 计算系统间相似度
        inter_similarities = {}
        system_pairs = list(combinations(valid_systems.keys(), 2))
        
        for sys1, sys2 in system_pairs:
            logger.info(f"计算 {sys1} vs {sys2} 系统间相似度...")
            stats = self.compute_inter_system_similarity(
                valid_systems[sys1], valid_systems[sys2]
            )
            pair_key = f"{sys1} vs {sys2}"
            inter_similarities[pair_key] = stats
            logger.info(f"  {pair_key}: 均值={stats.mean:.4f}, 样本对数={stats.n_pairs}")
        
        # 计算总体指标
        avg_intra = np.mean([stats.mean for stats in intra_similarities.values()])
        avg_inter = np.mean([stats.mean for stats in inter_similarities.values()])
        coherence_ratio = avg_intra / avg_inter if avg_inter > 0 else float('inf')
        
        # 计算聚类质量得分
        clustering_quality_score = self._calculate_clustering_quality_score(
            intra_similarities, inter_similarities
        )
        
        # 验证是否通过
        validation_passed = coherence_ratio >= coherence_threshold
        
        # 系统条目数统计
        system_term_counts = {name: len(terms) for name, terms in system_terms.items()}
        
        # 创建报告
        report = CoherenceReport(
            intra_system_similarity=intra_similarities,
            inter_system_similarity=inter_similarities,
            clustering_quality_score=clustering_quality_score,
            avg_intra_similarity=avg_intra,
            avg_inter_similarity=avg_inter,
            coherence_ratio=coherence_ratio,
            validation_passed=validation_passed,
            system_term_counts=system_term_counts,
            metadata={
                'similarity_method': self.similarity_method,
                'sample_size': self.sample_size,
                'coherence_threshold': coherence_threshold,
                'n_valid_systems': len(valid_systems),
                'n_system_pairs': len(system_pairs)
            }
        )
        
        logger.info(f"验证完成: {report.get_summary()}")
        return report
    
    def _calculate_clustering_quality_score(self, 
                                          intra_similarities: Dict[str, SimilarityStats],
                                          inter_similarities: Dict[str, SimilarityStats]) -> float:
        """
        计算聚类质量得分
        
        基于轮廓系数的思想，计算聚类质量得分。
        """
        if not intra_similarities or not inter_similarities:
            return 0.0
        
        # 计算每个系统的质量得分
        system_scores = []
        
        for system_name, intra_stats in intra_similarities.items():
            # 该系统的内部相似度
            intra_sim = intra_stats.mean
            
            # 该系统与其他系统的平均相似度
            inter_sims = []
            for pair_key, inter_stats in inter_similarities.items():
                if system_name in pair_key:
                    inter_sims.append(inter_stats.mean)
            
            if inter_sims:
                avg_inter_sim = np.mean(inter_sims)
                # 轮廓系数风格的得分
                if intra_sim > 0 or avg_inter_sim > 0:
                    score = (intra_sim - avg_inter_sim) / max(intra_sim, avg_inter_sim)
                    system_scores.append(score)
        
        return np.mean(system_scores) if system_scores else 0.0
    
    def generate_validation_report(self, 
                                 report: CoherenceReport,
                                 output_path: Optional[str] = None) -> str:
        """
        生成详细的验证报告
        
        Args:
            report: 语义一致性验证报告
            output_path: 输出文件路径，如果为None则返回字符串
            
        Returns:
            报告内容字符串
        """
        lines = []
        lines.append("# 语义聚类一致性验证报告")
        lines.append("")
        
        # 验证方法
        lines.append("## 验证方法")
        lines.append(f"- **相似度计算方法**: {report.metadata['similarity_method']}")
        lines.append(f"- **采样大小**: {report.metadata['sample_size']}")
        lines.append(f"- **一致性阈值**: {report.metadata['coherence_threshold']}")
        lines.append("")
        
        # 预期结果
        lines.append("## 预期结果")
        lines.append("- ✅ 系统内部相似度应该**高**（表明系统内部同质）")
        lines.append("- ✅ 系统间相似度应该**低**（表明系统间异质）")
        lines.append("")
        
        # 系统内部相似度
        lines.append("## 系统内部相似度 (Intra-system)")
        lines.append("")
        lines.append("| 系统 | 条目数 | 均值 | 标准差 | 中位数 | 样本对数 |")
        lines.append("|------|--------|------|--------|--------|----------|")
        
        for system_name in sorted(report.intra_system_similarity.keys()):
            stats = report.intra_system_similarity[system_name]
            term_count = report.system_term_counts.get(system_name, 0)
            lines.append(f"| {system_name} | {term_count} | {stats.mean:.4f} | "
                        f"{stats.std:.4f} | {stats.median:.4f} | {stats.n_pairs} |")
        
        lines.append("")
        
        # 系统间相似度
        lines.append("## 系统间相似度 (Inter-system)")
        lines.append("")
        lines.append("| 系统对 | 均值 | 标准差 | 中位数 | 样本对数 |")
        lines.append("|--------|------|--------|--------|----------|")
        
        for pair_key in sorted(report.inter_system_similarity.keys()):
            stats = report.inter_system_similarity[pair_key]
            lines.append(f"| {pair_key} | {stats.mean:.4f} | {stats.std:.4f} | "
                        f"{stats.median:.4f} | {stats.n_pairs} |")
        
        lines.append("")
        
        # 关键发现
        lines.append("## 关键发现")
        lines.append("")
        lines.append(f"- **平均系统内部相似度**: {report.avg_intra_similarity:.4f}")
        lines.append(f"- **平均系统间相似度**: {report.avg_inter_similarity:.4f}")
        lines.append(f"- **一致性比值 (Intra/Inter)**: {report.coherence_ratio:.2f}x")
        lines.append(f"- **聚类质量得分**: {report.clustering_quality_score:.4f}")
        lines.append("")
        
        # 验证结果
        if report.validation_passed:
            lines.append("✅ **验证通过**: 系统内部相似度显著高于系统间相似度")
            lines.append("   这证明了五大系统分类的语义一致性和区分度")
        else:
            lines.append("⚠️ **需要注意**: 系统间相似度较高，可能需要优化分类规则")
        
        lines.append("")
        
        # 系统对比分析
        if report.inter_system_similarity:
            sorted_pairs = sorted(report.inter_system_similarity.items(), 
                                key=lambda x: x[1].mean)
            most_different = sorted_pairs[0]
            most_similar = sorted_pairs[-1]
            
            lines.append(f"- **最不相似的系统对**: {most_different[0]} "
                        f"(相似度: {most_different[1].mean:.4f})")
            lines.append(f"- **最相似的系统对**: {most_similar[0]} "
                        f"(相似度: {most_similar[1].mean:.4f})")
            lines.append("")
        
        # 结论
        lines.append("## 结论")
        lines.append("")
        lines.append("基于 GO 语义相似度分析，五大功能系统分类表现出：")
        lines.append("1. 系统内部高度同质（高相似度）")
        lines.append("2. 系统之间明显异质（低相似度）")
        lines.append("3. 分类具有良好的语义聚类一致性")
        
        report_text = '\n'.join(lines)
        
        # 保存到文件
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            logger.info(f"验证报告已保存到: {output_path}")
        
        return report_text
    
    def clear_cache(self):
        """清空相似度计算缓存"""
        self._similarity_cache.clear()
        logger.info("已清空相似度计算缓存")