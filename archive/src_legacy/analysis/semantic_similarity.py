"""
语义相似度计算模块

基于GO DAG结构计算语义相似度，实现信息内容和路径距离方法。
优化大规模计算性能。
"""

import numpy as np
import networkx as nx
from typing import Dict, Set, List, Tuple, Optional, Any
from dataclasses import dataclass
from collections import defaultdict, deque
import logging
import math
from functools import lru_cache
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import pickle

logger = logging.getLogger(__name__)


@dataclass
class SimilarityConfig:
    """语义相似度计算配置"""
    method: str = 'resnik'  # 'resnik', 'lin', 'jiang', 'depth', 'jaccard'
    use_information_content: bool = True
    ic_method: str = 'intrinsic'  # 'intrinsic', 'annotation'
    cache_size: int = 10000
    parallel: bool = True
    n_workers: int = 4
    batch_size: int = 1000


class InformationContent:
    """
    信息内容计算器
    
    计算GO条目的信息内容，用于基于信息内容的语义相似度计算。
    """
    
    def __init__(self, go_dag: nx.DiGraph, method: str = 'intrinsic'):
        """
        初始化信息内容计算器
        
        Args:
            go_dag: GO本体DAG图
            method: 计算方法 ('intrinsic', 'annotation')
        """
        self.go_dag = go_dag
        self.method = method
        self.ic_values: Dict[str, float] = {}
        self.term_frequencies: Dict[str, int] = {}
        self.total_annotations = 0
        
        logger.info(f"初始化信息内容计算器: method={method}")
    
    def calculate_intrinsic_ic(self) -> Dict[str, float]:
        """
        计算内在信息内容
        
        基于GO DAG结构计算信息内容，不依赖于注释数据。
        """
        logger.info("计算内在信息内容...")
        
        # 计算每个节点的后代数量
        descendant_counts = {}
        
        for term_id in self.go_dag.nodes():
            descendants = nx.descendants(self.go_dag, term_id)
            descendant_counts[term_id] = len(descendants) + 1  # 包含自身
        
        # 找到最大后代数量（通常是根节点）
        max_descendants = max(descendant_counts.values()) if descendant_counts else 1
        
        # 计算信息内容: IC(t) = -log(P(t)) = -log(descendants(t) / max_descendants)
        for term_id, desc_count in descendant_counts.items():
            probability = desc_count / max_descendants
            ic = -math.log(probability) if probability > 0 else 0.0
            self.ic_values[term_id] = ic
        
        logger.info(f"计算完成，共 {len(self.ic_values)} 个条目的信息内容")
        return self.ic_values
    
    def calculate_annotation_ic(self, annotation_counts: Dict[str, int]) -> Dict[str, float]:
        """
        基于注释数据计算信息内容
        
        Args:
            annotation_counts: 条目ID到注释数量的映射
        """
        logger.info("基于注释数据计算信息内容...")
        
        self.term_frequencies = annotation_counts.copy()
        self.total_annotations = sum(annotation_counts.values())
        
        if self.total_annotations == 0:
            logger.warning("注释数据为空，回退到内在信息内容")
            return self.calculate_intrinsic_ic()
        
        # 传播注释计数到祖先节点
        propagated_counts = defaultdict(int)
        
        for term_id, count in annotation_counts.items():
            if term_id in self.go_dag:
                # 将计数传播到所有祖先
                ancestors = nx.ancestors(self.go_dag, term_id)
                ancestors.add(term_id)  # 包含自身
                
                for ancestor in ancestors:
                    propagated_counts[ancestor] += count
        
        # 计算信息内容
        for term_id, prop_count in propagated_counts.items():
            probability = prop_count / self.total_annotations
            ic = -math.log(probability) if probability > 0 else 0.0
            self.ic_values[term_id] = ic
        
        logger.info(f"计算完成，共 {len(self.ic_values)} 个条目的信息内容")
        return self.ic_values
    
    def get_ic(self, term_id: str) -> float:
        """获取条目的信息内容"""
        return self.ic_values.get(term_id, 0.0)
    
    def get_max_ic(self) -> float:
        """获取最大信息内容值"""
        return max(self.ic_values.values()) if self.ic_values else 0.0


class SemanticSimilarityCalculator:
    """
    语义相似度计算器
    
    实现多种基于GO本体的语义相似度计算方法。
    """
    
    def __init__(self, go_dag: nx.DiGraph, config: Optional[SimilarityConfig] = None):
        """
        初始化语义相似度计算器
        
        Args:
            go_dag: GO本体DAG图
            config: 计算配置
        """
        self.go_dag = go_dag
        self.config = config or SimilarityConfig()
        
        # 初始化信息内容计算器
        if self.config.use_information_content:
            self.ic_calculator = InformationContent(go_dag, self.config.ic_method)
            if self.config.ic_method == 'intrinsic':
                self.ic_calculator.calculate_intrinsic_ic()
        else:
            self.ic_calculator = None
        
        # 缓存
        self._similarity_cache: Dict[Tuple[str, str], float] = {}
        self._lca_cache: Dict[Tuple[str, str], Set[str]] = {}
        self._depth_cache: Dict[str, int] = {}
        
        logger.info(f"初始化语义相似度计算器: method={self.config.method}")
    
    def set_annotation_counts(self, annotation_counts: Dict[str, int]):
        """设置注释计数数据"""
        if self.ic_calculator and self.config.ic_method == 'annotation':
            self.ic_calculator.calculate_annotation_ic(annotation_counts)
            self._similarity_cache.clear()  # 清空缓存
    
    @lru_cache(maxsize=10000)
    def _get_ancestors(self, term_id: str) -> frozenset:
        """获取祖先节点（带缓存）"""
        if term_id not in self.go_dag:
            return frozenset()
        
        ancestors = nx.ancestors(self.go_dag, term_id)
        ancestors.add(term_id)  # 包含自身
        return frozenset(ancestors)
    
    def _get_lowest_common_ancestors(self, term1: str, term2: str) -> Set[str]:
        """获取最低公共祖先"""
        cache_key = tuple(sorted([term1, term2]))
        if cache_key in self._lca_cache:
            return self._lca_cache[cache_key]
        
        ancestors1 = self._get_ancestors(term1)
        ancestors2 = self._get_ancestors(term2)
        
        common_ancestors = ancestors1 & ancestors2
        
        if not common_ancestors:
            self._lca_cache[cache_key] = set()
            return set()
        
        # 找到最低公共祖先（没有后代在公共祖先集合中的节点）
        lca_set = set()
        for ancestor in common_ancestors:
            descendants = nx.descendants(self.go_dag, ancestor)
            if not (descendants & common_ancestors):
                lca_set.add(ancestor)
        
        self._lca_cache[cache_key] = lca_set
        return lca_set
    
    def _get_depth(self, term_id: str) -> int:
        """获取节点深度（带缓存）"""
        if term_id in self._depth_cache:
            return self._depth_cache[term_id]
        
        if term_id not in self.go_dag:
            self._depth_cache[term_id] = 0
            return 0
        
        # GO的根节点
        root_nodes = {'GO:0008150', 'GO:0003674', 'GO:0005575'}
        
        min_depth = float('inf')
        for root in root_nodes:
            if root in self.go_dag:
                try:
                    depth = nx.shortest_path_length(self.go_dag, root, term_id)
                    min_depth = min(min_depth, depth)
                except nx.NetworkXNoPath:
                    continue
        
        depth = min_depth if min_depth != float('inf') else 0
        self._depth_cache[term_id] = depth
        return depth
    
    def calculate_similarity(self, term1: str, term2: str) -> float:
        """
        计算两个GO条目间的语义相似度
        
        Args:
            term1: 第一个GO条目ID
            term2: 第二个GO条目ID
            
        Returns:
            语义相似度值 [0, 1]
        """
        # 检查缓存
        cache_key = tuple(sorted([term1, term2]))
        if cache_key in self._similarity_cache:
            return self._similarity_cache[cache_key]
        
        # 基本检查
        if term1 == term2:
            similarity = 1.0
        elif term1 not in self.go_dag or term2 not in self.go_dag:
            similarity = 0.0
        else:
            similarity = self._compute_similarity(term1, term2)
        
        # 缓存结果
        if len(self._similarity_cache) < self.config.cache_size:
            self._similarity_cache[cache_key] = similarity
        
        return similarity
    
    def _compute_similarity(self, term1: str, term2: str) -> float:
        """计算语义相似度的具体实现"""
        method = self.config.method.lower()
        
        if method == 'resnik':
            return self._resnik_similarity(term1, term2)
        elif method == 'lin':
            return self._lin_similarity(term1, term2)
        elif method == 'jiang':
            return self._jiang_similarity(term1, term2)
        elif method == 'depth':
            return self._depth_similarity(term1, term2)
        elif method == 'jaccard':
            return self._jaccard_similarity(term1, term2)
        else:
            raise ValueError(f"不支持的相似度方法: {method}")
    
    def _resnik_similarity(self, term1: str, term2: str) -> float:
        """Resnik语义相似度"""
        if not self.ic_calculator:
            logger.warning("Resnik方法需要信息内容，回退到深度方法")
            return self._depth_similarity(term1, term2)
        
        lca_set = self._get_lowest_common_ancestors(term1, term2)
        if not lca_set:
            return 0.0
        
        # 选择信息内容最高的LCA
        max_ic = 0.0
        for lca in lca_set:
            ic = self.ic_calculator.get_ic(lca)
            max_ic = max(max_ic, ic)
        
        # 归一化到[0,1]
        max_possible_ic = self.ic_calculator.get_max_ic()
        return max_ic / max_possible_ic if max_possible_ic > 0 else 0.0
    
    def _lin_similarity(self, term1: str, term2: str) -> float:
        """Lin语义相似度"""
        if not self.ic_calculator:
            logger.warning("Lin方法需要信息内容，回退到深度方法")
            return self._depth_similarity(term1, term2)
        
        lca_set = self._get_lowest_common_ancestors(term1, term2)
        if not lca_set:
            return 0.0
        
        # 选择信息内容最高的LCA
        max_lca_ic = 0.0
        for lca in lca_set:
            ic = self.ic_calculator.get_ic(lca)
            max_lca_ic = max(max_lca_ic, ic)
        
        ic1 = self.ic_calculator.get_ic(term1)
        ic2 = self.ic_calculator.get_ic(term2)
        
        if ic1 + ic2 == 0:
            return 0.0
        
        return (2 * max_lca_ic) / (ic1 + ic2)
    
    def _jiang_similarity(self, term1: str, term2: str) -> float:
        """Jiang & Conrath语义相似度"""
        if not self.ic_calculator:
            logger.warning("Jiang方法需要信息内容，回退到深度方法")
            return self._depth_similarity(term1, term2)
        
        lca_set = self._get_lowest_common_ancestors(term1, term2)
        if not lca_set:
            return 0.0
        
        # 选择信息内容最高的LCA
        max_lca_ic = 0.0
        for lca in lca_set:
            ic = self.ic_calculator.get_ic(lca)
            max_lca_ic = max(max_lca_ic, ic)
        
        ic1 = self.ic_calculator.get_ic(term1)
        ic2 = self.ic_calculator.get_ic(term2)
        
        distance = ic1 + ic2 - 2 * max_lca_ic
        
        # 转换为相似度（距离越小，相似度越高）
        max_distance = self.ic_calculator.get_max_ic() * 2
        if max_distance == 0:
            return 0.0
        
        return 1 - (distance / max_distance)
    
    def _depth_similarity(self, term1: str, term2: str) -> float:
        """基于深度的语义相似度"""
        lca_set = self._get_lowest_common_ancestors(term1, term2)
        if not lca_set:
            return 0.0
        
        # 选择深度最大的LCA
        max_lca_depth = 0
        for lca in lca_set:
            depth = self._get_depth(lca)
            max_lca_depth = max(max_lca_depth, depth)
        
        depth1 = self._get_depth(term1)
        depth2 = self._get_depth(term2)
        max_depth = max(depth1, depth2)
        
        if max_depth == 0:
            return 0.0
        
        return max_lca_depth / max_depth
    
    def _jaccard_similarity(self, term1: str, term2: str) -> float:
        """基于Jaccard系数的语义相似度"""
        ancestors1 = self._get_ancestors(term1)
        ancestors2 = self._get_ancestors(term2)
        
        intersection = len(ancestors1 & ancestors2)
        union = len(ancestors1 | ancestors2)
        
        return intersection / union if union > 0 else 0.0
    
    def calculate_pairwise_similarities(self, 
                                     term_list: List[str],
                                     symmetric: bool = True) -> np.ndarray:
        """
        计算条目列表的成对相似度矩阵
        
        Args:
            term_list: GO条目ID列表
            symmetric: 是否利用对称性优化计算
            
        Returns:
            相似度矩阵
        """
        n = len(term_list)
        similarity_matrix = np.zeros((n, n))
        
        if self.config.parallel and n > 100:
            # 并行计算
            similarity_matrix = self._calculate_parallel(term_list, symmetric)
        else:
            # 串行计算
            for i in range(n):
                similarity_matrix[i, i] = 1.0  # 对角线
                
                start_j = i + 1 if symmetric else 0
                for j in range(start_j, n):
                    if i != j:
                        sim = self.calculate_similarity(term_list[i], term_list[j])
                        similarity_matrix[i, j] = sim
                        if symmetric:
                            similarity_matrix[j, i] = sim
        
        return similarity_matrix
    
    def _calculate_parallel(self, term_list: List[str], symmetric: bool) -> np.ndarray:
        """并行计算相似度矩阵"""
        n = len(term_list)
        similarity_matrix = np.zeros((n, n))
        
        # 对角线设为1
        np.fill_diagonal(similarity_matrix, 1.0)
        
        # 生成需要计算的索引对
        if symmetric:
            pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        else:
            pairs = [(i, j) for i in range(n) for j in range(n) if i != j]
        
        # 分批处理
        batch_size = self.config.batch_size
        batches = [pairs[i:i + batch_size] for i in range(0, len(pairs), batch_size)]
        
        logger.info(f"并行计算 {len(pairs)} 个相似度对，分为 {len(batches)} 批")
        
        with ProcessPoolExecutor(max_workers=self.config.n_workers) as executor:
            # 提交批次任务
            future_to_batch = {}
            for batch_idx, batch in enumerate(batches):
                future = executor.submit(
                    _calculate_batch_similarities,
                    batch, term_list, self.go_dag, self.config
                )
                future_to_batch[future] = batch_idx
            
            # 收集结果
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    batch_results = future.result()
                    batch = batches[batch_idx]
                    
                    for (i, j), sim in zip(batch, batch_results):
                        similarity_matrix[i, j] = sim
                        if symmetric:
                            similarity_matrix[j, i] = sim
                            
                except Exception as e:
                    logger.error(f"批次 {batch_idx} 计算失败: {e}")
        
        return similarity_matrix
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取计算器统计信息"""
        stats = {
            'method': self.config.method,
            'cache_size': len(self._similarity_cache),
            'lca_cache_size': len(self._lca_cache),
            'depth_cache_size': len(self._depth_cache),
            'dag_nodes': len(self.go_dag.nodes),
            'dag_edges': len(self.go_dag.edges)
        }
        
        if self.ic_calculator:
            stats['ic_values'] = len(self.ic_calculator.ic_values)
            stats['ic_method'] = self.ic_calculator.method
        
        return stats
    
    def clear_cache(self):
        """清空所有缓存"""
        self._similarity_cache.clear()
        self._lca_cache.clear()
        self._depth_cache.clear()
        logger.info("已清空所有缓存")


def _calculate_batch_similarities(batch_pairs: List[Tuple[int, int]], 
                                term_list: List[str],
                                go_dag: nx.DiGraph,
                                config: SimilarityConfig) -> List[float]:
    """
    批量计算相似度（用于并行处理）
    
    这个函数需要在模块级别定义以支持pickle序列化。
    """
    # 创建临时计算器
    calculator = SemanticSimilarityCalculator(go_dag, config)
    
    results = []
    for i, j in batch_pairs:
        sim = calculator.calculate_similarity(term_list[i], term_list[j])
        results.append(sim)
    
    return results