"""
数据质量和完整性管理器

整合数据质量检查和分类覆盖率检查，提供统一的质量管理接口。
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime
import json

from .data_quality_checker import DataQualityChecker, DataQualityReport
from .classification_coverage_checker import ClassificationCoverageChecker, CoverageReport

# 设置日志
logger = logging.getLogger(__name__)


@dataclass
class ComprehensiveQualityReport:
    """综合质量报告"""
    
    report_id: str
    timestamp: datetime
    data_quality_report: Optional[DataQualityReport] = None
    coverage_report: Optional[CoverageReport] = None
    integration_analysis: Dict[str, Any] = field(default_factory=dict)
    overall_recommendations: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    
    def calculate_overall_quality_score(self) -> float:
        """计算综合质量分数"""
        scores = []
        weights = []
        
        # 数据质量分数 (权重: 0.4)
        if self.data_quality_report:
            data_quality_score = self.data_quality_report.calculate_quality_score()
            scores.append(data_quality_score)
            weights.append(0.4)
        
        # 覆盖率分数 (权重: 0.6)
        if self.coverage_report:
            coverage_score = self.coverage_report.statistics.coverage_rate * 100
            scores.append(coverage_score)
            weights.append(0.6)
        
        if scores:
            weighted_score = sum(score * weight for score, weight in zip(scores, weights))
            total_weight = sum(weights)
            self.quality_score = weighted_score / total_weight if total_weight > 0 else 0
        else:
            self.quality_score = 0.0
        
        return self.quality_score
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'report_id': self.report_id,
            'timestamp': self.timestamp.isoformat(),
            'data_quality_report': self.data_quality_report.to_dict() if self.data_quality_report else None,
            'coverage_report': self.coverage_report.to_dict() if self.coverage_report else None,
            'integration_analysis': self.integration_analysis,
            'overall_recommendations': self.overall_recommendations,
            'quality_score': self.quality_score
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class DataQualityManager:
    """
    数据质量和完整性管理器
    
    提供统一的数据质量检查、分类覆盖率分析和质量报告生成功能。
    """
    
    def __init__(self, log_level: str = 'INFO'):
        """
        初始化数据质量管理器
        
        Args:
            log_level: 日志级别
        """
        self.data_quality_checker = DataQualityChecker()
        self.coverage_checker = ClassificationCoverageChecker()
        
        # 设置日志级别
        logging.basicConfig(level=getattr(logging, log_level.upper()))
        
        # 质量阈值配置
        self.quality_thresholds = {
            'data_quality_min': 80.0,      # 数据质量最低分数
            'coverage_rate_min': 0.85,     # 最低覆盖率
            'consistency_rate_min': 0.95,  # 最低一致性率
            'overall_quality_min': 75.0    # 综合质量最低分数
        }
    
    def run_comprehensive_quality_check(self,
                                      go_file_path: str,
                                      kegg_file_path: str,
                                      classification_results: Optional[List] = None,
                                      original_entries: Optional[List] = None) -> ComprehensiveQualityReport:
        """
        运行综合质量检查
        
        Args:
            go_file_path: GO文件路径
            kegg_file_path: KEGG文件路径
            classification_results: 分类结果列表 (可选)
            original_entries: 原始条目列表 (可选)
            
        Returns:
            综合质量报告
        """
        logger.info("开始运行综合数据质量检查")
        
        # 初始化综合报告
        report = ComprehensiveQualityReport(
            report_id=f"comprehensive_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now()
        )
        
        try:
            # 1. 数据质量检查
            logger.info("执行数据质量检查...")
            report.data_quality_report = self.data_quality_checker.check_data_consistency(
                go_file_path, kegg_file_path
            )
            
            # 2. 分类覆盖率检查 (如果提供了分类结果)
            if classification_results and original_entries:
                logger.info("执行分类覆盖率检查...")
                report.coverage_report = self.coverage_checker.check_classification_coverage(
                    classification_results, original_entries
                )
            
            # 3. 集成分析
            logger.info("执行集成分析...")
            self._perform_integration_analysis(report)
            
            # 4. 生成综合建议
            logger.info("生成综合建议...")
            self._generate_overall_recommendations(report)
            
            # 5. 计算综合质量分数
            report.calculate_overall_quality_score()
            
            logger.info(f"综合质量检查完成，综合质量分数: {report.quality_score:.1f}")
            
        except Exception as e:
            logger.error(f"综合质量检查失败: {e}")
            raise
        
        return report
    
    def check_data_files_quality(self, go_file_path: str, kegg_file_path: str) -> DataQualityReport:
        """
        检查数据文件质量
        
        Args:
            go_file_path: GO文件路径
            kegg_file_path: KEGG文件路径
            
        Returns:
            数据质量报告
        """
        logger.info("检查数据文件质量")
        return self.data_quality_checker.check_data_consistency(go_file_path, kegg_file_path)
    
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
        logger.info("检查分类覆盖率")
        return self.coverage_checker.check_classification_coverage(
            classification_results, original_entries
        )
    
    def validate_classification_consistency(self, classification_results: List) -> Dict[str, Any]:
        """
        验证分类一致性
        
        Args:
            classification_results: 分类结果列表
            
        Returns:
            一致性分析结果
        """
        logger.info("验证分类一致性")
        return self.coverage_checker.analyze_classification_consistency(classification_results)
    
    def _perform_integration_analysis(self, report: ComprehensiveQualityReport):
        """执行集成分析"""
        integration_analysis = {}
        
        # 数据质量与覆盖率关联分析
        if report.data_quality_report and report.coverage_report:
            data_quality_score = report.data_quality_report.calculate_quality_score()
            coverage_rate = report.coverage_report.statistics.coverage_rate
            
            # 分析质量与覆盖率的关系
            quality_coverage_correlation = self._analyze_quality_coverage_correlation(
                data_quality_score, coverage_rate
            )
            integration_analysis['quality_coverage_correlation'] = quality_coverage_correlation
            
            # 分析数据源特定问题
            source_analysis = self._analyze_source_specific_issues(
                report.data_quality_report, report.coverage_report
            )
            integration_analysis['source_specific_analysis'] = source_analysis
        
        # 问题优先级分析
        priority_analysis = self._analyze_issue_priorities(report)
        integration_analysis['issue_priorities'] = priority_analysis
        
        # 改进影响评估
        improvement_impact = self._assess_improvement_impact(report)
        integration_analysis['improvement_impact'] = improvement_impact
        
        report.integration_analysis = integration_analysis
    
    def _analyze_quality_coverage_correlation(self, 
                                            data_quality_score: float, 
                                            coverage_rate: float) -> Dict[str, Any]:
        """分析数据质量与覆盖率的关联"""
        correlation_analysis = {
            'data_quality_score': data_quality_score,
            'coverage_rate': coverage_rate * 100,  # 转换为百分比
            'correlation_strength': 'unknown',
            'analysis': ''
        }
        
        # 简单的关联分析
        quality_level = 'high' if data_quality_score >= 80 else 'medium' if data_quality_score >= 60 else 'low'
        coverage_level = 'high' if coverage_rate >= 0.9 else 'medium' if coverage_rate >= 0.7 else 'low'
        
        if quality_level == coverage_level:
            correlation_analysis['correlation_strength'] = 'positive'
            correlation_analysis['analysis'] = f"数据质量({quality_level})与覆盖率({coverage_level})呈正相关"
        elif (quality_level == 'high' and coverage_level == 'low') or \
             (quality_level == 'low' and coverage_level == 'high'):
            correlation_analysis['correlation_strength'] = 'negative'
            correlation_analysis['analysis'] = f"数据质量({quality_level})与覆盖率({coverage_level})存在负相关，需要进一步调查"
        else:
            correlation_analysis['correlation_strength'] = 'weak'
            correlation_analysis['analysis'] = f"数据质量({quality_level})与覆盖率({coverage_level})关联较弱"
        
        return correlation_analysis
    
    def _analyze_source_specific_issues(self, 
                                      data_quality_report: DataQualityReport,
                                      coverage_report: CoverageReport) -> Dict[str, Any]:
        """分析数据源特定问题"""
        source_analysis = {}
        
        # 获取数据质量问题按源文件分组
        go_issues = [issue for issue in data_quality_report.issues 
                    if 'go-basic' in issue.source_file.lower() or 'go' in issue.source_file.lower()]
        kegg_issues = [issue for issue in data_quality_report.issues 
                      if 'kegg' in issue.source_file.lower() or 'br_br08901' in issue.source_file.lower()]
        
        # 获取覆盖率问题按数据源分组
        coverage_stats = coverage_report.statistics.source_distribution
        
        # GO数据源分析
        go_coverage = coverage_stats.get('GO', {})
        source_analysis['GO'] = {
            'data_quality_issues': len(go_issues),
            'coverage_stats': go_coverage,
            'major_issues': [issue.description for issue in go_issues if issue.severity == 'error'][:3]
        }
        
        # KEGG数据源分析
        kegg_coverage = coverage_stats.get('KEGG', {})
        source_analysis['KEGG'] = {
            'data_quality_issues': len(kegg_issues),
            'coverage_stats': kegg_coverage,
            'major_issues': [issue.description for issue in kegg_issues if issue.severity == 'error'][:3]
        }
        
        return source_analysis
    
    def _analyze_issue_priorities(self, report: ComprehensiveQualityReport) -> List[Dict[str, Any]]:
        """分析问题优先级"""
        priorities = []
        
        # 数据质量问题优先级
        if report.data_quality_report:
            error_count = len(report.data_quality_report.get_issues_by_severity('error'))
            if error_count > 0:
                priorities.append({
                    'category': 'data_quality_errors',
                    'priority': 'high',
                    'count': error_count,
                    'description': f"{error_count} 个数据质量错误需要立即修复",
                    'impact': 'critical'
                })
            
            warning_count = len(report.data_quality_report.get_issues_by_severity('warning'))
            if warning_count > 0:
                priorities.append({
                    'category': 'data_quality_warnings',
                    'priority': 'medium',
                    'count': warning_count,
                    'description': f"{warning_count} 个数据质量警告建议修复",
                    'impact': 'moderate'
                })
        
        # 覆盖率问题优先级
        if report.coverage_report:
            coverage_rate = report.coverage_report.statistics.coverage_rate
            if coverage_rate < self.quality_thresholds['coverage_rate_min']:
                priorities.append({
                    'category': 'low_coverage',
                    'priority': 'high',
                    'count': report.coverage_report.statistics.unclassified_entries,
                    'description': f"覆盖率过低 ({coverage_rate:.1%})，需要优化分类规则",
                    'impact': 'high'
                })
            
            # 分析失败类别优先级
            failure_categories = report.coverage_report.statistics.failure_categories
            for category, count in failure_categories.items():
                if count > 0:
                    priority_level = 'high' if category == 'system_error' else 'medium'
                    priorities.append({
                        'category': f'classification_failure_{category}',
                        'priority': priority_level,
                        'count': count,
                        'description': f"{count} 个 {category} 类型的分类失败",
                        'impact': 'moderate'
                    })
        
        # 按优先级和影响排序
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        priorities.sort(key=lambda x: (priority_order.get(x['priority'], 0), x['count']), reverse=True)
        
        return priorities
    
    def _assess_improvement_impact(self, report: ComprehensiveQualityReport) -> Dict[str, Any]:
        """评估改进影响"""
        impact_assessment = {
            'potential_improvements': [],
            'estimated_quality_gain': 0.0,
            'effort_estimation': 'unknown'
        }
        
        # 评估数据质量改进影响
        if report.data_quality_report:
            error_count = len(report.data_quality_report.get_issues_by_severity('error'))
            warning_count = len(report.data_quality_report.get_issues_by_severity('warning'))
            
            if error_count > 0:
                quality_gain = min(20.0, error_count * 2)  # 每个错误修复可提升2分，最多20分
                impact_assessment['potential_improvements'].append({
                    'type': 'fix_data_quality_errors',
                    'description': f"修复 {error_count} 个数据质量错误",
                    'estimated_gain': quality_gain,
                    'effort': 'high' if error_count > 10 else 'medium'
                })
                impact_assessment['estimated_quality_gain'] += quality_gain
        
        # 评估覆盖率改进影响
        if report.coverage_report:
            improvement_potential = report.coverage_report.detailed_analysis.get('improvement_potential', {})
            recoverable_entries = improvement_potential.get('recoverable_entries', 0)
            
            if recoverable_entries > 0:
                coverage_gain = improvement_potential.get('potential_coverage_improvement', 0) * 100
                impact_assessment['potential_improvements'].append({
                    'type': 'improve_classification_rules',
                    'description': f"优化分类规则可恢复 {recoverable_entries} 个条目",
                    'estimated_gain': coverage_gain,
                    'effort': 'medium'
                })
                impact_assessment['estimated_quality_gain'] += coverage_gain * 0.6  # 覆盖率权重0.6
        
        # 估算总体努力程度
        total_improvements = len(impact_assessment['potential_improvements'])
        if total_improvements == 0:
            impact_assessment['effort_estimation'] = 'minimal'
        elif total_improvements <= 2:
            impact_assessment['effort_estimation'] = 'low'
        elif total_improvements <= 4:
            impact_assessment['effort_estimation'] = 'medium'
        else:
            impact_assessment['effort_estimation'] = 'high'
        
        return impact_assessment
    
    def _generate_overall_recommendations(self, report: ComprehensiveQualityReport):
        """生成综合建议"""
        recommendations = []
        
        # 基于综合质量分数的建议
        quality_score = report.calculate_overall_quality_score()
        
        if quality_score >= 90:
            recommendations.append("数据质量优秀，建议保持当前的质量管理流程")
        elif quality_score >= 75:
            recommendations.append("数据质量良好，有进一步优化空间")
        elif quality_score >= 60:
            recommendations.append("数据质量中等，建议重点改进关键问题")
        else:
            recommendations.append("数据质量较差，需要全面的质量改进计划")
        
        # 基于问题优先级的建议
        issue_priorities = report.integration_analysis.get('issue_priorities', [])
        high_priority_issues = [issue for issue in issue_priorities if issue['priority'] == 'high']
        
        if high_priority_issues:
            recommendations.append(f"发现 {len(high_priority_issues)} 个高优先级问题，建议优先处理")
            for issue in high_priority_issues[:3]:  # 只显示前3个
                recommendations.append(f"- {issue['description']}")
        
        # 基于改进影响的建议
        improvement_impact = report.integration_analysis.get('improvement_impact', {})
        potential_gain = improvement_impact.get('estimated_quality_gain', 0)
        
        if potential_gain > 10:
            effort = improvement_impact.get('effort_estimation', 'unknown')
            recommendations.append(f"通过改进可提升质量分数约 {potential_gain:.1f} 分，预估工作量: {effort}")
        
        # 基于关联分析的建议
        correlation = report.integration_analysis.get('quality_coverage_correlation', {})
        if correlation.get('correlation_strength') == 'negative':
            recommendations.append("数据质量与覆盖率存在负相关，建议深入调查原因")
        
        # 数据源特定建议
        source_analysis = report.integration_analysis.get('source_specific_analysis', {})
        for source, analysis in source_analysis.items():
            if analysis.get('data_quality_issues', 0) > 5:
                recommendations.append(f"{source} 数据源问题较多，建议重点检查")
        
        report.overall_recommendations = recommendations
    
    def generate_quality_dashboard_data(self, report: ComprehensiveQualityReport) -> Dict[str, Any]:
        """
        生成质量仪表板数据
        
        Args:
            report: 综合质量报告
            
        Returns:
            仪表板数据字典
        """
        dashboard_data = {
            'overview': {
                'overall_quality_score': report.quality_score,
                'quality_level': self._get_quality_level(report.quality_score),
                'timestamp': report.timestamp.isoformat()
            },
            'metrics': {},
            'charts': {},
            'alerts': []
        }
        
        # 数据质量指标
        if report.data_quality_report:
            data_quality_score = report.data_quality_report.calculate_quality_score()
            dashboard_data['metrics']['data_quality'] = {
                'score': data_quality_score,
                'total_entries': report.data_quality_report.total_entries,
                'valid_entries': report.data_quality_report.valid_entries,
                'error_count': len(report.data_quality_report.get_issues_by_severity('error')),
                'warning_count': len(report.data_quality_report.get_issues_by_severity('warning'))
            }
        
        # 覆盖率指标
        if report.coverage_report:
            dashboard_data['metrics']['coverage'] = {
                'coverage_rate': report.coverage_report.statistics.coverage_rate,
                'total_entries': report.coverage_report.statistics.total_entries,
                'classified_entries': report.coverage_report.statistics.classified_entries,
                'unclassified_entries': report.coverage_report.statistics.unclassified_entries,
                'system_distribution': report.coverage_report.statistics.system_distribution
            }
        
        # 生成警报
        dashboard_data['alerts'] = self._generate_quality_alerts(report)
        
        return dashboard_data
    
    def _get_quality_level(self, score: float) -> str:
        """获取质量等级"""
        if score >= 90:
            return 'excellent'
        elif score >= 75:
            return 'good'
        elif score >= 60:
            return 'fair'
        else:
            return 'poor'
    
    def _generate_quality_alerts(self, report: ComprehensiveQualityReport) -> List[Dict[str, Any]]:
        """生成质量警报"""
        alerts = []
        
        # 综合质量分数警报
        if report.quality_score < self.quality_thresholds['overall_quality_min']:
            alerts.append({
                'type': 'quality_score_low',
                'severity': 'high',
                'message': f"综合质量分数过低: {report.quality_score:.1f}",
                'threshold': self.quality_thresholds['overall_quality_min']
            })
        
        # 数据质量警报
        if report.data_quality_report:
            data_quality_score = report.data_quality_report.calculate_quality_score()
            if data_quality_score < self.quality_thresholds['data_quality_min']:
                alerts.append({
                    'type': 'data_quality_low',
                    'severity': 'high',
                    'message': f"数据质量分数过低: {data_quality_score:.1f}",
                    'threshold': self.quality_thresholds['data_quality_min']
                })
            
            error_count = len(report.data_quality_report.get_issues_by_severity('error'))
            if error_count > 0:
                alerts.append({
                    'type': 'data_quality_errors',
                    'severity': 'critical',
                    'message': f"发现 {error_count} 个数据质量错误",
                    'count': error_count
                })
        
        # 覆盖率警报
        if report.coverage_report:
            coverage_rate = report.coverage_report.statistics.coverage_rate
            if coverage_rate < self.quality_thresholds['coverage_rate_min']:
                alerts.append({
                    'type': 'coverage_rate_low',
                    'severity': 'medium',
                    'message': f"分类覆盖率过低: {coverage_rate:.1%}",
                    'threshold': self.quality_thresholds['coverage_rate_min']
                })
        
        return alerts
    
    def save_comprehensive_report(self, report: ComprehensiveQualityReport, output_dir: str):
        """
        保存综合质量报告
        
        Args:
            report: 综合质量报告
            output_dir: 输出目录
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 保存JSON格式的完整报告
            json_path = output_path / f"{report.report_id}_comprehensive.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(report.to_json())
            
            # 保存Markdown格式的摘要报告
            md_path = output_path / f"{report.report_id}_summary.md"
            summary_report = self._generate_comprehensive_summary(report)
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(summary_report)
            
            # 保存仪表板数据
            dashboard_path = output_path / f"{report.report_id}_dashboard.json"
            dashboard_data = self.generate_quality_dashboard_data(report)
            with open(dashboard_path, 'w', encoding='utf-8') as f:
                json.dump(dashboard_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"综合质量报告已保存到: {output_path}")
            
        except Exception as e:
            logger.error(f"保存综合报告失败: {e}")
            raise
    
    def _generate_comprehensive_summary(self, report: ComprehensiveQualityReport) -> str:
        """生成综合摘要报告"""
        lines = [
            "# 数据质量和完整性综合报告",
            f"报告ID: {report.report_id}",
            f"生成时间: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"综合质量分数: {report.quality_score:.1f}/100",
            f"质量等级: {self._get_quality_level(report.quality_score)}",
            ""
        ]
        
        # 数据质量摘要
        if report.data_quality_report:
            data_quality_score = report.data_quality_report.calculate_quality_score()
            lines.extend([
                "## 数据质量摘要",
                f"- 数据质量分数: {data_quality_score:.1f}/100",
                f"- 总条目数: {report.data_quality_report.total_entries:,}",
                f"- 有效条目数: {report.data_quality_report.valid_entries:,}",
                f"- 错误数量: {len(report.data_quality_report.get_issues_by_severity('error'))}",
                f"- 警告数量: {len(report.data_quality_report.get_issues_by_severity('warning'))}",
                ""
            ])
        
        # 覆盖率摘要
        if report.coverage_report:
            lines.extend([
                "## 分类覆盖率摘要",
                f"- 覆盖率: {report.coverage_report.statistics.coverage_rate:.2%}",
                f"- 总条目数: {report.coverage_report.statistics.total_entries:,}",
                f"- 已分类条目: {report.coverage_report.statistics.classified_entries:,}",
                f"- 未分类条目: {report.coverage_report.statistics.unclassified_entries:,}",
                ""
            ])
            
            # 系统分布
            if report.coverage_report.statistics.system_distribution:
                lines.append("### 系统分布")
                for system, count in sorted(report.coverage_report.statistics.system_distribution.items()):
                    percentage = (count / report.coverage_report.statistics.classified_entries * 100) \
                        if report.coverage_report.statistics.classified_entries > 0 else 0
                    lines.append(f"- {system}: {count:,} ({percentage:.1f}%)")
                lines.append("")
        
        # 综合建议
        if report.overall_recommendations:
            lines.extend([
                "## 综合建议"
            ])
            for i, recommendation in enumerate(report.overall_recommendations, 1):
                lines.append(f"{i}. {recommendation}")
            lines.append("")
        
        # 问题优先级
        issue_priorities = report.integration_analysis.get('issue_priorities', [])
        if issue_priorities:
            lines.extend([
                "## 问题优先级"
            ])
            for priority in issue_priorities[:5]:  # 显示前5个优先级问题
                lines.append(f"- **{priority['priority'].upper()}**: {priority['description']}")
            lines.append("")
        
        return "\n".join(lines)