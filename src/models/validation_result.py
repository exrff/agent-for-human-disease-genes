"""
验证结果数据模型

定义了分类系统验证结果的数据结构。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional
import json
from datetime import datetime


@dataclass
class ValidationResult:
    """
    验证结果的数据结构
    
    包含语义一致性验证、ssGSEA验证和基线对比的结果。
    
    Attributes:
        validation_type: 验证类型 ('semantic_coherence', 'ssgsea', 'baseline_comparison')
        intra_system_similarity: 系统内部相似度 {system: similarity_score}
        inter_system_similarity: 系统间相似度 {(system1, system2): similarity_score}
        clustering_quality_score: 聚类质量分数
        statistical_significance: 统计显著性结果 {test_name: p_value}
        performance_metrics: 性能指标 {metric_name: value}
        validation_date: 验证日期
        metadata: 额外的验证元数据
    """
    
    validation_type: str
    intra_system_similarity: Dict[str, float] = field(default_factory=dict)
    inter_system_similarity: Dict[Tuple[str, str], float] = field(default_factory=dict)
    clustering_quality_score: float = 0.0
    statistical_significance: Dict[str, float] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    validation_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """数据验证和后处理"""
        # 验证必需字段
        if not self.validation_type:
            raise ValueError("validation_type is required")
        
        # 验证验证类型
        valid_types = ['semantic_coherence', 'ssgsea', 'baseline_comparison', 'integration_test']
        if self.validation_type not in valid_types:
            raise ValueError(f"Invalid validation_type: {self.validation_type}")
        
        # 设置默认验证日期
        if self.validation_date is None:
            self.validation_date = datetime.now()
        
        # 验证相似度分数范围
        for system, score in self.intra_system_similarity.items():
            if not 0 <= score <= 1:
                raise ValueError(f"Intra-system similarity score for {system} must be between 0 and 1")
        
        for (sys1, sys2), score in self.inter_system_similarity.items():
            if not 0 <= score <= 1:
                raise ValueError(f"Inter-system similarity score for {sys1}-{sys2} must be between 0 and 1")
    
    def calculate_clustering_quality(self) -> float:
        """计算聚类质量分数"""
        if not self.intra_system_similarity or not self.inter_system_similarity:
            return 0.0
        
        # 计算平均系统内相似度
        avg_intra = sum(self.intra_system_similarity.values()) / len(self.intra_system_similarity)
        
        # 计算平均系统间相似度
        avg_inter = sum(self.inter_system_similarity.values()) / len(self.inter_system_similarity)
        
        # 聚类质量 = 系统内相似度 / 系统间相似度
        if avg_inter > 0:
            self.clustering_quality_score = avg_intra / avg_inter
        else:
            self.clustering_quality_score = float('inf') if avg_intra > 0 else 1.0
        
        return self.clustering_quality_score
    
    def is_clustering_valid(self, threshold: float = 1.5) -> bool:
        """检查聚类是否有效"""
        quality_score = self.calculate_clustering_quality()
        return quality_score >= threshold
    
    def get_best_performing_system(self) -> Optional[str]:
        """获取表现最好的系统（基于系统内相似度）"""
        if not self.intra_system_similarity:
            return None
        return max(self.intra_system_similarity.items(), key=lambda x: x[1])[0]
    
    def get_worst_performing_system(self) -> Optional[str]:
        """获取表现最差的系统（基于系统内相似度）"""
        if not self.intra_system_similarity:
            return None
        return min(self.intra_system_similarity.items(), key=lambda x: x[1])[0]
    
    def get_most_similar_system_pair(self) -> Optional[Tuple[str, str]]:
        """获取最相似的系统对"""
        if not self.inter_system_similarity:
            return None
        return max(self.inter_system_similarity.items(), key=lambda x: x[1])[0]
    
    def get_least_similar_system_pair(self) -> Optional[Tuple[str, str]]:
        """获取最不相似的系统对"""
        if not self.inter_system_similarity:
            return None
        return min(self.inter_system_similarity.items(), key=lambda x: x[1])[0]
    
    def add_performance_metric(self, metric_name: str, value: float):
        """添加性能指标"""
        self.performance_metrics[metric_name] = value
    
    def add_statistical_test(self, test_name: str, p_value: float):
        """添加统计检验结果"""
        self.statistical_significance[test_name] = p_value
    
    def is_statistically_significant(self, test_name: str, alpha: float = 0.05) -> bool:
        """检查统计检验是否显著"""
        p_value = self.statistical_significance.get(test_name)
        if p_value is None:
            return False
        return p_value < alpha
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        # 处理inter_system_similarity的键（元组）
        inter_similarity_dict = {
            f"{sys1}_vs_{sys2}": score 
            for (sys1, sys2), score in self.inter_system_similarity.items()
        }
        
        return {
            'validation_type': self.validation_type,
            'intra_system_similarity': self.intra_system_similarity,
            'inter_system_similarity': inter_similarity_dict,
            'clustering_quality_score': self.clustering_quality_score,
            'statistical_significance': self.statistical_significance,
            'performance_metrics': self.performance_metrics,
            'validation_date': self.validation_date.isoformat() if self.validation_date else None,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValidationResult':
        """从字典创建实例"""
        # 处理inter_system_similarity的键
        inter_similarity = {}
        for key, score in data.get('inter_system_similarity', {}).items():
            if '_vs_' in key:
                sys1, sys2 = key.split('_vs_', 1)
                inter_similarity[(sys1, sys2)] = score
        
        # 处理validation_date
        validation_date = None
        if data.get('validation_date'):
            validation_date = datetime.fromisoformat(data['validation_date'])
        
        return cls(
            validation_type=data['validation_type'],
            intra_system_similarity=data.get('intra_system_similarity', {}),
            inter_system_similarity=inter_similarity,
            clustering_quality_score=data.get('clustering_quality_score', 0.0),
            statistical_significance=data.get('statistical_significance', {}),
            performance_metrics=data.get('performance_metrics', {}),
            validation_date=validation_date,
            metadata=data.get('metadata', {})
        )
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ValidationResult':
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def generate_summary_report(self) -> str:
        """生成验证结果摘要报告"""
        report_lines = [
            f"验证类型: {self.validation_type}",
            f"验证日期: {self.validation_date.strftime('%Y-%m-%d %H:%M:%S') if self.validation_date else 'N/A'}",
            f"聚类质量分数: {self.clustering_quality_score:.4f}",
            ""
        ]
        
        if self.intra_system_similarity:
            report_lines.append("系统内部相似度:")
            for system, score in sorted(self.intra_system_similarity.items()):
                report_lines.append(f"  {system}: {score:.4f}")
            report_lines.append("")
        
        if self.inter_system_similarity:
            report_lines.append("系统间相似度:")
            for (sys1, sys2), score in sorted(self.inter_system_similarity.items()):
                report_lines.append(f"  {sys1} vs {sys2}: {score:.4f}")
            report_lines.append("")
        
        if self.performance_metrics:
            report_lines.append("性能指标:")
            for metric, value in sorted(self.performance_metrics.items()):
                report_lines.append(f"  {metric}: {value:.4f}")
            report_lines.append("")
        
        if self.statistical_significance:
            report_lines.append("统计显著性:")
            for test, p_value in sorted(self.statistical_significance.items()):
                significance = "显著" if p_value < 0.05 else "不显著"
                report_lines.append(f"  {test}: p={p_value:.4f} ({significance})")
        
        return "\n".join(report_lines)
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"ValidationResult({self.validation_type}, quality={self.clustering_quality_score:.3f})"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"ValidationResult(validation_type='{self.validation_type}', clustering_quality_score={self.clustering_quality_score})"