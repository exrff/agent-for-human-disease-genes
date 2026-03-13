"""
分类覆盖率检查器

统计未分类条目数量，分析分类失败原因，生成数据质量报告。
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any
from collections import defaultdict, Counter
from datetime import datetime
import json
from pathlib import Path

# 设置日志
logger = logging.getLogger(__name__)


@dataclass
class ClassificationFailure:
    """分类失败记录"""
    
    entry_id: str
    entry_name: str
    source: str  # 'GO' or 'KEGG'
    failure_reason: str
    failure_category: str  # 'no_match', 'ambiguous', 'invalid_input', 'system_error'
    attempted_rules: List[str] = field(default_factory=list)
    partial_matches: List[str] = field(default_factory=list)
    suggested_system: Optional[str] = None
    confidence_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'entry_id': self.entry_id,
            'entry_name': self.entry_name,
            'source': self.source,
            'failure_reason': self.failure_reason,
            'failure_category': self.failure_category,
            'attempted_rules': self.attempted_rules,
            'partial_matches': self.partial_matches,
            'suggested_system': self.suggested_system,
            'confidence_score': self.confidence_score,
            'metadata': self.metadata
        }


@dataclass
class CoverageStatistics:
    """覆盖率统计信息"""
    
    total_entries: int = 0
    classified_entries: int = 0
    unclassified_entries: int = 0
    system_distribution: Dict[str, int] = field(default_factory=dict)
    source_distribution: Dict[str, Dict[str, int]] = field(default_factory=dict)
    failure_categories: Dict[str, int] = field(default_factory=dict)
    coverage_rate: float = 0.0
    
    def calculate_coverage_rate(self):
        """计算覆盖率"""
        if self.total_entries > 0:
            self.coverage_rate = self.classified_entries / self.total_entries
        else:
            self.coverage_rate = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'total_entries': self.total_entries,
            'classified_entries': self.classified_entries,
            'unclassified_entries': self.unclassified_entries,
            'system_distribution': self.system_distribution,
            'source_distribution': self.source_distribution,
            'failure_categories': self.failure_categories,
            'coverage_rate': self.coverage_rate
        }


@dataclass
class CoverageReport:
    """分类覆盖率报告"""
    
    report_id: str
    timestamp: datetime
    statistics: CoverageStatistics
    failures: List[ClassificationFailure] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    detailed_analysis: Dict[str, Any] = field(default_factory=dict)
    
    def add_failure(self, failure: ClassificationFailure):
        """添加分类失败记录"""
        self.failures.append(failure)
        self.statistics.failure_categories[failure.failure_category] = \
            self.statistics.failure_categories.get(failure.failure_category, 0) + 1
    
    def get_failures_by_category(self, category: str) -> List[ClassificationFailure]:
        """按类别获取失败记录"""
        return [f for f in self.failures if f.failure_category == category]
    
    def get_failures_by_source(self, source: str) -> List[ClassificationFailure]:
        """按数据源获取失败记录"""
        return [f for f in self.failures if f.source == source]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'report_id': self.report_id,
            'timestamp': self.timestamp.isoformat(),
            'statistics': self.statistics.to_dict(),
            'failures': [f.to_dict() for f in self.failures],
            'recommendations': self.recommendations,
            'detailed_analysis': self.detailed_analysis
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class ClassificationCoverageChecker:
    """
    分类覆盖率检查器
    
    统计未分类条目数量，分析分类失败原因，生成数据质量报告。
    """
    
    def __init__(self):
        """初始化覆盖率检查器"""
        self.valid_systems = {
            'System A', 'System B', 'System C', 'System D', 'System E', 'System 0'
        }
        self.valid_subsystems = {
            'A1', 'A2', 'A3', 'A4',
            'B1', 'B2', 'B3',
            'C1', 'C2', 'C3',
            'D1', 'D2',
            'E1', 'E2'
        }
    
    def check_classification_coverage(self, 
                                    classification_results: List,
                                    original_entries: List) -> CoverageReport:
        """
        检查分类覆盖率
        
        Args:
            classification_results: 分类结果列表
            original_entries: 原始条目列表
            
        Returns:
            覆盖率报告
        """
        logger.info("开始检查分类覆盖率")
        
        # 初始化报告
        report = CoverageReport(
            report_id=f"coverage_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(),
            statistics=CoverageStatistics()
        )
        
        # 构建分类结果映射
        classified_entries = {}
        for result in classification_results:
            if hasattr(result, 'entry_id'):
                classified_entries[result.entry_id] = result
            elif hasattr(result, 'id'):
                classified_entries[result.id] = result
        
        # 统计覆盖率
        self._calculate_coverage_statistics(original_entries, classified_entries, report)
        
        # 分析未分类条目
        self._analyze_unclassified_entries(original_entries, classified_entries, report)
        
        # 验证分类结果质量
        self._validate_classification_quality(classification_results, report)
        
        # 生成详细分析
        self._generate_detailed_analysis(report)
        
        # 生成建议
        self._generate_recommendations(report)
        
        logger.info(f"分类覆盖率检查完成，覆盖率: {report.statistics.coverage_rate:.2%}")
        return report
    
    def _calculate_coverage_statistics(self, 
                                     original_entries: List,
                                     classified_entries: Dict,
                                     report: CoverageReport):
        """计算覆盖率统计"""
        stats = report.statistics
        
        # 基本统计
        stats.total_entries = len(original_entries)
        stats.classified_entries = len(classified_entries)
        stats.unclassified_entries = stats.total_entries - stats.classified_entries
        stats.calculate_coverage_rate()
        
        # 按数据源统计
        source_stats = defaultdict(lambda: {'total': 0, 'classified': 0, 'unclassified': 0})
        
        for entry in original_entries:
            source = getattr(entry, 'source', 'unknown')
            entry_id = getattr(entry, 'id', str(entry))
            
            source_stats[source]['total'] += 1
            
            if entry_id in classified_entries:
                source_stats[source]['classified'] += 1
            else:
                source_stats[source]['unclassified'] += 1
        
        stats.source_distribution = dict(source_stats)
        
        # 按系统统计分类结果
        system_counts = defaultdict(int)
        for result in classified_entries.values():
            primary_system = getattr(result, 'primary_system', None)
            if primary_system:
                system_counts[primary_system] += 1
        
        stats.system_distribution = dict(system_counts)
    
    def _analyze_unclassified_entries(self, 
                                    original_entries: List,
                                    classified_entries: Dict,
                                    report: CoverageReport):
        """分析未分类条目"""
        for entry in original_entries:
            entry_id = getattr(entry, 'id', str(entry))
            
            if entry_id not in classified_entries:
                # 分析失败原因
                failure = self._analyze_classification_failure(entry)
                report.add_failure(failure)
    
    def _analyze_classification_failure(self, entry) -> ClassificationFailure:
        """分析单个条目的分类失败原因"""
        entry_id = getattr(entry, 'id', 'unknown')
        entry_name = getattr(entry, 'name', 'unknown')
        source = getattr(entry, 'source', 'unknown')
        
        # 基本失败信息
        failure = ClassificationFailure(
            entry_id=entry_id,
            entry_name=entry_name,
            source=source,
            failure_reason="未能分类到任何系统",
            failure_category="no_match"
        )
        
        # 分析具体原因
        if not entry_name or entry_name.strip() == '':
            failure.failure_reason = "条目名称为空"
            failure.failure_category = "invalid_input"
        elif len(entry_name) < 3:
            failure.failure_reason = "条目名称过短"
            failure.failure_category = "invalid_input"
        elif 'obsolete' in entry_name.lower():
            failure.failure_reason = "条目已过时"
            failure.failure_category = "invalid_input"
        else:
            # 尝试简单的关键词匹配分析
            failure = self._suggest_potential_system(entry, failure)
        
        return failure
    
    def _suggest_potential_system(self, entry, failure: ClassificationFailure) -> ClassificationFailure:
        """为未分类条目建议可能的系统"""
        entry_name = getattr(entry, 'name', '').lower()
        definition = getattr(entry, 'definition', '').lower()
        text = f"{entry_name} {definition}"
        
        # 简单的关键词匹配
        system_keywords = {
            'System A': ['repair', 'maintenance', 'healing', 'recovery', 'regeneration', 
                        'homeostasis', 'stability', 'integrity'],
            'System B': ['immune', 'defense', 'protection', 'pathogen', 'infection',
                        'antibody', 'antigen', 'inflammation', 'cytokine'],
            'System C': ['metabolism', 'energy', 'biosynthesis', 'catabolism',
                        'glucose', 'lipid', 'protein', 'nutrient'],
            'System D': ['neural', 'nervous', 'brain', 'neuron', 'signal',
                        'hormone', 'endocrine', 'regulation'],
            'System E': ['reproduction', 'development', 'embryo', 'growth',
                        'differentiation', 'maturation', 'gamete']
        }
        
        potential_matches = []
        for system, keywords in system_keywords.items():
            match_count = sum(1 for keyword in keywords if keyword in text)
            if match_count > 0:
                potential_matches.append((system, match_count))
        
        if potential_matches:
            # 按匹配数量排序
            potential_matches.sort(key=lambda x: x[1], reverse=True)
            best_match = potential_matches[0]
            
            failure.suggested_system = best_match[0]
            failure.confidence_score = min(0.8, best_match[1] * 0.2)
            failure.partial_matches = [match[0] for match in potential_matches]
            failure.failure_reason = f"可能属于 {best_match[0]}，但未达到分类阈值"
            failure.failure_category = "ambiguous"
        else:
            failure.failure_reason = "未找到匹配的系统关键词"
            failure.failure_category = "no_match"
        
        return failure
    
    def _validate_classification_quality(self, classification_results: List, report: CoverageReport):
        """验证分类结果质量"""
        quality_issues = []
        
        for result in classification_results:
            # 检查必需字段
            if not hasattr(result, 'primary_system') or not result.primary_system:
                quality_issues.append(f"条目 {getattr(result, 'entry_id', 'unknown')} 缺少主系统分类")
                continue
            
            # 检查系统有效性
            if result.primary_system not in self.valid_systems:
                quality_issues.append(f"条目 {getattr(result, 'entry_id', 'unknown')} 的主系统无效: {result.primary_system}")
            
            # 检查子系统有效性
            if hasattr(result, 'subsystem') and result.subsystem:
                if result.subsystem not in self.valid_subsystems:
                    quality_issues.append(f"条目 {getattr(result, 'entry_id', 'unknown')} 的子系统无效: {result.subsystem}")
            
            # 检查置信度分数
            if hasattr(result, 'confidence_score'):
                if not (0 <= result.confidence_score <= 1):
                    quality_issues.append(f"条目 {getattr(result, 'entry_id', 'unknown')} 的置信度分数无效: {result.confidence_score}")
        
        report.detailed_analysis['quality_issues'] = quality_issues
    
    def _generate_detailed_analysis(self, report: CoverageReport):
        """生成详细分析"""
        stats = report.statistics
        
        # 失败原因分析
        failure_analysis = {}
        for category, count in stats.failure_categories.items():
            percentage = (count / stats.unclassified_entries * 100) if stats.unclassified_entries > 0 else 0
            failure_analysis[category] = {
                'count': count,
                'percentage': percentage
            }
        
        # 数据源分析
        source_analysis = {}
        for source, source_stats in stats.source_distribution.items():
            coverage_rate = (source_stats['classified'] / source_stats['total'] * 100) if source_stats['total'] > 0 else 0
            source_analysis[source] = {
                'coverage_rate': coverage_rate,
                'total': source_stats['total'],
                'classified': source_stats['classified'],
                'unclassified': source_stats['unclassified']
            }
        
        # 系统分布分析
        system_analysis = {}
        total_classified = sum(stats.system_distribution.values())
        for system, count in stats.system_distribution.items():
            percentage = (count / total_classified * 100) if total_classified > 0 else 0
            system_analysis[system] = {
                'count': count,
                'percentage': percentage
            }
        
        # 潜在改进分析
        improvement_potential = self._analyze_improvement_potential(report)
        
        report.detailed_analysis.update({
            'failure_analysis': failure_analysis,
            'source_analysis': source_analysis,
            'system_analysis': system_analysis,
            'improvement_potential': improvement_potential
        })
    
    def _analyze_improvement_potential(self, report: CoverageReport) -> Dict[str, Any]:
        """分析改进潜力"""
        potential = {}
        
        # 分析有建议系统的失败条目
        suggested_failures = [f for f in report.failures if f.suggested_system]
        if suggested_failures:
            potential['recoverable_entries'] = len(suggested_failures)
            potential['potential_coverage_improvement'] = len(suggested_failures) / report.statistics.total_entries
            
            # 按建议系统分组
            suggested_systems = defaultdict(int)
            for failure in suggested_failures:
                suggested_systems[failure.suggested_system] += 1
            potential['suggested_system_distribution'] = dict(suggested_systems)
        
        # 分析高置信度建议
        high_confidence_suggestions = [f for f in suggested_failures if f.confidence_score > 0.5]
        if high_confidence_suggestions:
            potential['high_confidence_suggestions'] = len(high_confidence_suggestions)
        
        return potential
    
    def _generate_recommendations(self, report: CoverageReport):
        """生成改进建议"""
        recommendations = []
        stats = report.statistics
        
        # 基于覆盖率的建议
        if stats.coverage_rate < 0.8:
            recommendations.append(f"分类覆盖率较低 ({stats.coverage_rate:.1%})，建议优化分类规则")
        elif stats.coverage_rate < 0.9:
            recommendations.append(f"分类覆盖率中等 ({stats.coverage_rate:.1%})，有进一步优化空间")
        else:
            recommendations.append(f"分类覆盖率良好 ({stats.coverage_rate:.1%})")
        
        # 基于失败类别的建议
        failure_categories = stats.failure_categories
        
        if failure_categories.get('invalid_input', 0) > 0:
            recommendations.append("存在无效输入条目，建议加强数据预处理和验证")
        
        if failure_categories.get('no_match', 0) > stats.unclassified_entries * 0.5:
            recommendations.append("大量条目无法匹配任何系统，建议扩展分类规则覆盖范围")
        
        if failure_categories.get('ambiguous', 0) > 0:
            recommendations.append("存在模糊分类条目，建议优化决策规则或增加人工审核")
        
        # 基于数据源的建议
        for source, source_stats in stats.source_distribution.items():
            coverage_rate = source_stats['classified'] / source_stats['total'] if source_stats['total'] > 0 else 0
            if coverage_rate < 0.8:
                recommendations.append(f"{source} 数据源覆盖率较低 ({coverage_rate:.1%})，建议针对性优化")
        
        # 基于系统分布的建议
        system_counts = list(stats.system_distribution.values())
        if system_counts:
            max_count = max(system_counts)
            min_count = min(system_counts)
            if max_count > min_count * 5:
                recommendations.append("系统分布不均衡，建议检查分类规则是否存在偏向性")
        
        # 基于改进潜力的建议
        improvement_potential = report.detailed_analysis.get('improvement_potential', {})
        recoverable = improvement_potential.get('recoverable_entries', 0)
        if recoverable > 0:
            potential_improvement = improvement_potential.get('potential_coverage_improvement', 0)
            recommendations.append(f"有 {recoverable} 个条目可能通过规则优化重新分类，"
                                 f"潜在覆盖率提升 {potential_improvement:.1%}")
        
        report.recommendations = recommendations
    
    def analyze_classification_consistency(self, 
                                         classification_results: List,
                                         multiple_runs: bool = False) -> Dict[str, Any]:
        """
        分析分类一致性
        
        Args:
            classification_results: 分类结果列表
            multiple_runs: 是否为多次运行结果
            
        Returns:
            一致性分析结果
        """
        logger.info("开始分析分类一致性")
        
        consistency_analysis = {
            'total_entries': len(classification_results),
            'consistent_entries': 0,
            'inconsistent_entries': 0,
            'consistency_rate': 0.0,
            'inconsistency_details': []
        }
        
        if multiple_runs:
            # 多次运行一致性检查
            # 这里假设输入是多次运行结果的列表
            # 实际实现需要根据具体数据结构调整
            pass
        else:
            # 单次运行内部一致性检查
            entry_systems = {}
            
            for result in classification_results:
                entry_id = getattr(result, 'entry_id', None)
                primary_system = getattr(result, 'primary_system', None)
                all_systems = getattr(result, 'all_systems', [])
                
                if entry_id and primary_system:
                    # 检查主系统是否在所有系统列表中
                    if primary_system not in all_systems:
                        consistency_analysis['inconsistency_details'].append({
                            'entry_id': entry_id,
                            'issue': 'primary_system_not_in_all_systems',
                            'primary_system': primary_system,
                            'all_systems': all_systems
                        })
                        consistency_analysis['inconsistent_entries'] += 1
                    else:
                        consistency_analysis['consistent_entries'] += 1
        
        # 计算一致性率
        total = consistency_analysis['consistent_entries'] + consistency_analysis['inconsistent_entries']
        if total > 0:
            consistency_analysis['consistency_rate'] = consistency_analysis['consistent_entries'] / total
        
        logger.info(f"一致性分析完成，一致性率: {consistency_analysis['consistency_rate']:.2%}")
        return consistency_analysis
    
    def generate_coverage_summary_report(self, report: CoverageReport) -> str:
        """
        生成覆盖率摘要报告
        
        Args:
            report: 覆盖率报告
            
        Returns:
            摘要报告文本
        """
        stats = report.statistics
        
        summary_lines = [
            "# 分类覆盖率报告摘要",
            f"报告ID: {report.report_id}",
            f"生成时间: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 基本统计",
            f"- 总条目数: {stats.total_entries:,}",
            f"- 已分类条目: {stats.classified_entries:,}",
            f"- 未分类条目: {stats.unclassified_entries:,}",
            f"- 覆盖率: {stats.coverage_rate:.2%}",
            "",
            "## 系统分布"
        ]
        
        for system, count in sorted(stats.system_distribution.items()):
            percentage = (count / stats.classified_entries * 100) if stats.classified_entries > 0 else 0
            summary_lines.append(f"- {system}: {count:,} ({percentage:.1f}%)")
        
        summary_lines.extend([
            "",
            "## 数据源分析"
        ])
        
        for source, source_stats in stats.source_distribution.items():
            coverage_rate = (source_stats['classified'] / source_stats['total'] * 100) if source_stats['total'] > 0 else 0
            summary_lines.append(f"- {source}: {source_stats['classified']:,}/{source_stats['total']:,} ({coverage_rate:.1f}%)")
        
        if stats.failure_categories:
            summary_lines.extend([
                "",
                "## 失败原因分析"
            ])
            
            for category, count in sorted(stats.failure_categories.items()):
                percentage = (count / stats.unclassified_entries * 100) if stats.unclassified_entries > 0 else 0
                summary_lines.append(f"- {category}: {count:,} ({percentage:.1f}%)")
        
        if report.recommendations:
            summary_lines.extend([
                "",
                "## 改进建议"
            ])
            
            for i, recommendation in enumerate(report.recommendations, 1):
                summary_lines.append(f"{i}. {recommendation}")
        
        return "\n".join(summary_lines)
    
    def save_coverage_report(self, report: CoverageReport, output_path: str):
        """
        保存覆盖率报告
        
        Args:
            report: 覆盖率报告
            output_path: 输出文件路径
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存JSON格式报告
            json_path = output_file.with_suffix('.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(report.to_json())
            
            # 保存Markdown格式摘要
            md_path = output_file.with_suffix('.md')
            summary_report = self.generate_coverage_summary_report(report)
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(summary_report)
            
            logger.info(f"覆盖率报告已保存到: {json_path} 和 {md_path}")
            
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
            raise