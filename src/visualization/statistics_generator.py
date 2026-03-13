"""
统计报告生成模块

生成五大功能系统分类的详细统计报告，包括系统分布、覆盖率分析、
版本对比等功能。

Requirements: 8.2, 9.3
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import logging
from collections import Counter, defaultdict

from ..models.classification_result import ClassificationResult, FunctionalSystem
from ..models.biological_entry import BiologicalEntry


class StatisticsGenerator:
    """
    统计报告生成器
    
    提供全面的分类结果统计分析功能，包括系统分布、覆盖率、
    质量指标和版本对比分析。
    """
    
    def __init__(self, output_dir: str = "results/reports"):
        """
        初始化统计生成器
        
        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 系统名称映射
        self.system_names = {
            FunctionalSystem.SYSTEM_A.value: "System A",
            FunctionalSystem.SYSTEM_B.value: "System B", 
            FunctionalSystem.SYSTEM_C.value: "System C",
            FunctionalSystem.SYSTEM_D.value: "System D",
            FunctionalSystem.SYSTEM_E.value: "System E",
            FunctionalSystem.SYSTEM_0.value: "System 0",
            FunctionalSystem.UNCLASSIFIED.value: "Unclassified"
        }
    
    def generate_system_distribution_report(self,
                                          results: List[ClassificationResult],
                                          entries: List[BiologicalEntry]) -> Dict[str, Any]:
        """
        生成系统分布统计报告
        
        Args:
            results: 分类结果列表
            entries: 生物学条目列表
            
        Returns:
            系统分布统计数据
        """
        # 创建条目映射
        entry_map = {entry.id: entry for entry in entries}
        
        # 统计系统分布
        system_counts = Counter()
        source_by_system = defaultdict(Counter)
        namespace_by_system = defaultdict(Counter)
        
        for result in results:
            system = result.primary_system
            system_counts[system] += 1
            
            # 获取对应条目
            entry = entry_map.get(result.entry_id)
            if entry:
                source_by_system[system][entry.source] += 1
                if entry.namespace:
                    namespace_by_system[system][entry.namespace] += 1
        
        total_entries = len(results)
        
        # 构建报告数据
        distribution_data = {
            'total_entries': total_entries,
            'systems': {}
        }
        
        for system_full_name, count in system_counts.items():
            system_short = self.system_names.get(system_full_name, system_full_name)
            percentage = (count / total_entries) * 100
            
            distribution_data['systems'][system_short] = {
                'full_name': system_full_name,
                'count': count,
                'percentage': round(percentage, 2),
                'sources': dict(source_by_system[system_full_name]),
                'namespaces': dict(namespace_by_system[system_full_name])
            }
        
        return distribution_data
    
    def generate_coverage_analysis(self,
                                 results: List[ClassificationResult],
                                 entries: List[BiologicalEntry]) -> Dict[str, Any]:
        """
        生成分类覆盖率分析
        
        Args:
            results: 分类结果列表
            entries: 生物学条目列表
            
        Returns:
            覆盖率分析数据
        """
        total_entries = len(results)
        
        # 分类覆盖率统计
        classified_count = len([r for r in results if not r.is_unclassified()])
        unclassified_count = total_entries - classified_count
        
        # 按数据源统计覆盖率
        entry_map = {entry.id: entry for entry in entries}
        source_coverage = defaultdict(lambda: {'total': 0, 'classified': 0})
        
        for result in results:
            entry = entry_map.get(result.entry_id)
            if entry:
                source = entry.source
                source_coverage[source]['total'] += 1
                if not result.is_unclassified():
                    source_coverage[source]['classified'] += 1
        
        # 计算覆盖率百分比
        for source_data in source_coverage.values():
            if source_data['total'] > 0:
                source_data['coverage_percentage'] = (source_data['classified'] / source_data['total']) * 100
            else:
                source_data['coverage_percentage'] = 0
        
        # 子系统覆盖率
        subsystem_count = len([r for r in results if r.subsystem])
        
        # 炎症极性标注覆盖率
        inflammation_count = len([r for r in results if r.inflammation_polarity])
        
        coverage_data = {
            'overall_coverage': {
                'total_entries': total_entries,
                'classified_entries': classified_count,
                'unclassified_entries': unclassified_count,
                'classification_rate': round((classified_count / total_entries) * 100, 2)
            },
            'source_coverage': dict(source_coverage),
            'annotation_coverage': {
                'subsystem_annotated': subsystem_count,
                'subsystem_rate': round((subsystem_count / total_entries) * 100, 2),
                'inflammation_annotated': inflammation_count,
                'inflammation_rate': round((inflammation_count / total_entries) * 100, 2)
            }
        }
        
        return coverage_data
    
    def generate_quality_metrics(self,
                               results: List[ClassificationResult]) -> Dict[str, Any]:
        """
        生成分类质量指标
        
        Args:
            results: 分类结果列表
            
        Returns:
            质量指标数据
        """
        if not results:
            return {'error': 'No results provided'}
        
        # 置信度统计
        confidence_scores = [r.confidence_score for r in results]
        
        # 决策路径长度统计
        decision_path_lengths = [len(r.decision_path) for r in results]
        
        # 多系统匹配统计
        multi_system_count = len([r for r in results if len(r.all_systems) > 1])
        
        # 系统分布均匀性 (使用基尼系数)
        system_counts = Counter(r.primary_system for r in results)
        gini_coefficient = self._calculate_gini_coefficient(list(system_counts.values()))
        
        quality_metrics = {
            'confidence_statistics': {
                'mean': round(np.mean(confidence_scores), 3),
                'median': round(np.median(confidence_scores), 3),
                'std': round(np.std(confidence_scores), 3),
                'min': round(np.min(confidence_scores), 3),
                'max': round(np.max(confidence_scores), 3)
            },
            'decision_complexity': {
                'mean_path_length': round(np.mean(decision_path_lengths), 2),
                'median_path_length': round(np.median(decision_path_lengths), 2),
                'max_path_length': max(decision_path_lengths) if decision_path_lengths else 0
            },
            'classification_specificity': {
                'multi_system_matches': multi_system_count,
                'multi_system_rate': round((multi_system_count / len(results)) * 100, 2)
            },
            'distribution_balance': {
                'gini_coefficient': round(gini_coefficient, 3),
                'balance_interpretation': self._interpret_gini(gini_coefficient)
            }
        }
        
        return quality_metrics
    
    def generate_subsystem_analysis(self,
                                  results: List[ClassificationResult]) -> Dict[str, Any]:
        """
        生成子系统分析报告
        
        Args:
            results: 分类结果列表
            
        Returns:
            子系统分析数据
        """
        # 按主系统分组统计子系统
        system_subsystems = defaultdict(Counter)
        
        for result in results:
            if result.subsystem:
                main_system = result.get_system_letter()
                system_subsystems[main_system][result.subsystem] += 1
        
        # 构建子系统分析数据
        subsystem_analysis = {}
        
        for system, subsystem_counts in system_subsystems.items():
            total_subsystem_entries = sum(subsystem_counts.values())
            
            subsystem_analysis[f"System {system}"] = {
                'total_subsystem_entries': total_subsystem_entries,
                'subsystems': {}
            }
            
            for subsystem, count in subsystem_counts.items():
                percentage = (count / total_subsystem_entries) * 100
                subsystem_analysis[f"System {system}"]['subsystems'][subsystem] = {
                    'count': count,
                    'percentage': round(percentage, 2)
                }
        
        return subsystem_analysis
    
    def generate_inflammation_analysis(self,
                                     results: List[ClassificationResult]) -> Dict[str, Any]:
        """
        生成炎症极性分析报告
        
        Args:
            results: 分类结果列表
            
        Returns:
            炎症极性分析数据
        """
        # 统计炎症极性分布
        inflammation_counts = Counter()
        inflammation_by_system = defaultdict(Counter)
        
        for result in results:
            if result.inflammation_polarity:
                inflammation_counts[result.inflammation_polarity] += 1
                system = result.get_system_letter()
                inflammation_by_system[system][result.inflammation_polarity] += 1
        
        total_inflammation = sum(inflammation_counts.values())
        
        # 构建炎症分析数据
        inflammation_analysis = {
            'overall_distribution': {},
            'by_system': {}
        }
        
        # 总体分布
        for polarity, count in inflammation_counts.items():
            percentage = (count / total_inflammation) * 100 if total_inflammation > 0 else 0
            inflammation_analysis['overall_distribution'][polarity] = {
                'count': count,
                'percentage': round(percentage, 2)
            }
        
        # 按系统分布
        for system, polarity_counts in inflammation_by_system.items():
            system_total = sum(polarity_counts.values())
            inflammation_analysis['by_system'][f"System {system}"] = {}
            
            for polarity, count in polarity_counts.items():
                percentage = (count / system_total) * 100
                inflammation_analysis['by_system'][f"System {system}"][polarity] = {
                    'count': count,
                    'percentage': round(percentage, 2)
                }
        
        return inflammation_analysis
    
    def compare_versions(self,
                        current_results: List[ClassificationResult],
                        previous_results: List[ClassificationResult],
                        current_version: str = "current",
                        previous_version: str = "previous") -> Dict[str, Any]:
        """
        生成版本对比报告
        
        Args:
            current_results: 当前版本分类结果
            previous_results: 之前版本分类结果
            current_version: 当前版本号
            previous_version: 之前版本号
            
        Returns:
            版本对比数据
        """
        # 构建结果映射
        current_map = {r.entry_id: r for r in current_results}
        previous_map = {r.entry_id: r for r in previous_results}
        
        # 找出共同条目
        common_ids = set(current_map.keys()) & set(previous_map.keys())
        
        # 统计变化
        system_changes = 0
        subsystem_changes = 0
        confidence_changes = []
        
        for entry_id in common_ids:
            current = current_map[entry_id]
            previous = previous_map[entry_id]
            
            # 系统变化
            if current.primary_system != previous.primary_system:
                system_changes += 1
            
            # 子系统变化
            if current.subsystem != previous.subsystem:
                subsystem_changes += 1
            
            # 置信度变化
            confidence_diff = current.confidence_score - previous.confidence_score
            confidence_changes.append(confidence_diff)
        
        # 新增和删除的条目
        new_entries = set(current_map.keys()) - set(previous_map.keys())
        removed_entries = set(previous_map.keys()) - set(current_map.keys())
        
        # 系统分布对比
        current_systems = Counter(r.primary_system for r in current_results)
        previous_systems = Counter(r.primary_system for r in previous_results)
        
        version_comparison = {
            'version_info': {
                'current_version': current_version,
                'previous_version': previous_version,
                'comparison_date': datetime.now().isoformat()
            },
            'entry_changes': {
                'common_entries': len(common_ids),
                'new_entries': len(new_entries),
                'removed_entries': len(removed_entries),
                'total_current': len(current_results),
                'total_previous': len(previous_results)
            },
            'classification_changes': {
                'system_changes': system_changes,
                'system_change_rate': round((system_changes / len(common_ids)) * 100, 2) if common_ids else 0,
                'subsystem_changes': subsystem_changes,
                'subsystem_change_rate': round((subsystem_changes / len(common_ids)) * 100, 2) if common_ids else 0
            },
            'confidence_changes': {
                'mean_change': round(np.mean(confidence_changes), 3) if confidence_changes else 0,
                'std_change': round(np.std(confidence_changes), 3) if confidence_changes else 0,
                'improved_count': len([c for c in confidence_changes if c > 0]),
                'degraded_count': len([c for c in confidence_changes if c < 0])
            },
            'system_distribution_changes': self._compare_distributions(current_systems, previous_systems)
        }
        
        return version_comparison
    
    def generate_comprehensive_report(self,
                                    results: List[ClassificationResult],
                                    entries: List[BiologicalEntry],
                                    version: str = "v8.0",
                                    previous_results: Optional[List[ClassificationResult]] = None) -> Path:
        """
        生成综合统计报告
        
        Args:
            results: 分类结果列表
            entries: 生物学条目列表
            version: 版本号
            previous_results: 之前版本的结果（用于对比）
            
        Returns:
            报告文件路径
        """
        report_data = {
            'report_metadata': {
                'version': version,
                'generation_date': datetime.now().isoformat(),
                'total_entries': len(results),
                'total_biological_entries': len(entries)
            },
            'system_distribution': self.generate_system_distribution_report(results, entries),
            'coverage_analysis': self.generate_coverage_analysis(results, entries),
            'quality_metrics': self.generate_quality_metrics(results),
            'subsystem_analysis': self.generate_subsystem_analysis(results),
            'inflammation_analysis': self.generate_inflammation_analysis(results)
        }
        
        # 添加版本对比（如果提供了之前的结果）
        if previous_results:
            report_data['version_comparison'] = self.compare_versions(
                results, previous_results, version, "previous"
            )
        
        # 保存JSON格式报告
        json_path = self.output_dir / f"classification_report_{version}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        # 生成Markdown格式报告
        md_path = self.output_dir / f"classification_report_{version}.md"
        self._generate_markdown_report(report_data, md_path)
        
        self.logger.info(f"Generated comprehensive report: {json_path}")
        return json_path
    
    def _calculate_gini_coefficient(self, values: List[int]) -> float:
        """计算基尼系数"""
        if not values or all(v == 0 for v in values):
            return 0.0
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        cumsum = np.cumsum(sorted_values)
        
        return (n + 1 - 2 * sum((n + 1 - i) * y for i, y in enumerate(sorted_values, 1))) / (n * sum(sorted_values))
    
    def _interpret_gini(self, gini: float) -> str:
        """解释基尼系数"""
        if gini < 0.2:
            return "Very balanced distribution"
        elif gini < 0.4:
            return "Moderately balanced distribution"
        elif gini < 0.6:
            return "Moderately unbalanced distribution"
        else:
            return "Highly unbalanced distribution"
    
    def _compare_distributions(self, current: Counter, previous: Counter) -> Dict[str, Any]:
        """对比两个分布"""
        all_systems = set(current.keys()) | set(previous.keys())
        
        changes = {}
        for system in all_systems:
            current_count = current.get(system, 0)
            previous_count = previous.get(system, 0)
            change = current_count - previous_count
            
            changes[system] = {
                'current': current_count,
                'previous': previous_count,
                'change': change,
                'change_percentage': round((change / previous_count) * 100, 2) if previous_count > 0 else float('inf') if change > 0 else 0
            }
        
        return changes
    
    def _generate_markdown_report(self, report_data: Dict[str, Any], output_path: Path):
        """生成Markdown格式的报告"""
        md_content = []
        
        # 标题和元数据
        metadata = report_data['report_metadata']
        md_content.append(f"# 五大功能系统分类报告 - {metadata['version']}")
        md_content.append(f"\n生成时间: {metadata['generation_date']}")
        md_content.append(f"总条目数: {metadata['total_entries']:,}")
        
        # 系统分布
        md_content.append("\n## 系统分布统计")
        distribution = report_data['system_distribution']
        md_content.append("\n| 系统 | 条目数 | 百分比 | GO条目 | KEGG条目 |")
        md_content.append("|------|--------|--------|--------|----------|")
        
        for system, data in distribution['systems'].items():
            go_count = data['sources'].get('GO', 0)
            kegg_count = data['sources'].get('KEGG', 0)
            md_content.append(f"| {system} | {data['count']:,} | {data['percentage']:.2f}% | {go_count:,} | {kegg_count:,} |")
        
        # 覆盖率分析
        md_content.append("\n## 分类覆盖率分析")
        coverage = report_data['coverage_analysis']
        overall = coverage['overall_coverage']
        md_content.append(f"\n- 总体分类率: {overall['classification_rate']:.2f}%")
        md_content.append(f"- 已分类条目: {overall['classified_entries']:,}")
        md_content.append(f"- 未分类条目: {overall['unclassified_entries']:,}")
        
        # 质量指标
        md_content.append("\n## 分类质量指标")
        quality = report_data['quality_metrics']
        conf_stats = quality['confidence_statistics']
        md_content.append(f"\n- 平均置信度: {conf_stats['mean']:.3f}")
        md_content.append(f"- 置信度标准差: {conf_stats['std']:.3f}")
        md_content.append(f"- 分布均匀性 (基尼系数): {quality['distribution_balance']['gini_coefficient']:.3f}")
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_content))
        
        self.logger.info(f"Generated markdown report: {output_path}")