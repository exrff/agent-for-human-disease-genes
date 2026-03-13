"""
数据质量检查演示

演示数据质量检查器和分类覆盖率检查器的功能。
"""

import sys
from pathlib import Path
import logging
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_quality_manager import DataQualityManager
from models.biological_entry import BiologicalEntry
from preprocessing.go_parser import GOParser
from preprocessing.kegg_parser import KEGGParser

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import classifier, but handle gracefully if not available
try:
    from classification.five_system_classifier import FiveSystemClassifier
    CLASSIFIER_AVAILABLE = True
except ImportError:
    CLASSIFIER_AVAILABLE = False
    logger.warning("FiveSystemClassifier not available, will skip classification demo")


def demo_data_quality_check():
    """演示数据质量检查功能"""
    print("=" * 60)
    print("数据质量和完整性检查演示")
    print("=" * 60)
    
    # 初始化数据质量管理器
    manager = DataQualityManager()
    
    # 数据文件路径
    go_file = "data/ontology/go-basic.obo"
    kegg_file = "data/ontology/br_br08901.txt"
    
    # 检查文件是否存在
    if not Path(go_file).exists():
        print(f"GO文件不存在: {go_file}")
        print("请确保数据文件存在后重新运行演示")
        return
    
    if not Path(kegg_file).exists():
        print(f"KEGG文件不存在: {kegg_file}")
        print("请确保数据文件存在后重新运行演示")
        return
    
    print(f"\n1. 检查数据文件质量...")
    print(f"   GO文件: {go_file}")
    print(f"   KEGG文件: {kegg_file}")
    
    # 执行数据质量检查
    try:
        data_quality_report = manager.check_data_files_quality(go_file, kegg_file)
        
        print(f"\n数据质量检查结果:")
        print(f"- 总条目数: {data_quality_report.total_entries:,}")
        print(f"- 有效条目数: {data_quality_report.valid_entries:,}")
        print(f"- 数据质量分数: {data_quality_report.calculate_quality_score():.1f}/100")
        
        # 显示问题统计
        error_count = len(data_quality_report.get_issues_by_severity('error'))
        warning_count = len(data_quality_report.get_issues_by_severity('warning'))
        info_count = len(data_quality_report.get_issues_by_severity('info'))
        
        print(f"- 错误数量: {error_count}")
        print(f"- 警告数量: {warning_count}")
        print(f"- 信息数量: {info_count}")
        
        # 显示前几个问题
        if error_count > 0:
            print(f"\n前3个错误:")
            for i, issue in enumerate(data_quality_report.get_issues_by_severity('error')[:3], 1):
                print(f"  {i}. {issue.description}")
        
        if warning_count > 0:
            print(f"\n前3个警告:")
            for i, issue in enumerate(data_quality_report.get_issues_by_severity('warning')[:3], 1):
                print(f"  {i}. {issue.description}")
        
        # 显示统计信息
        if 'go_statistics' in data_quality_report.statistics:
            go_stats = data_quality_report.statistics['go_statistics']
            print(f"\nGO数据统计:")
            if 'namespace_distribution' in go_stats:
                for namespace, count in go_stats['namespace_distribution'].items():
                    print(f"  {namespace}: {count:,}")
        
        if 'kegg_statistics' in data_quality_report.statistics:
            kegg_stats = data_quality_report.statistics['kegg_statistics']
            print(f"\nKEGG数据统计:")
            if 'class_a_distribution' in kegg_stats:
                print(f"  Class A分类数: {len(kegg_stats['class_a_distribution'])}")
                for class_a, count in list(kegg_stats['class_a_distribution'].items())[:5]:
                    print(f"    {class_a}: {count}")
        
    except Exception as e:
        print(f"数据质量检查失败: {e}")
        return
    
    print(f"\n2. 演示分类覆盖率检查...")
    
    # 解析部分数据进行分类演示
    try:
        # 解析GO数据 (限制数量以加快演示)
        go_parser = GOParser(go_file)
        go_terms = go_parser.get_biological_process_terms(exclude_obsolete=True)
        
        # 只取前100个条目进行演示
        sample_go_terms = dict(list(go_terms.items())[:50])
        go_entries = go_parser.to_biological_entries(sample_go_terms)
        
        # 解析KEGG数据
        kegg_parser = KEGGParser(kegg_file)
        kegg_pathways = kegg_parser.parse_pathways()
        
        # 只取前50个通路进行演示
        sample_kegg_pathways = kegg_pathways[:25]
        kegg_entries = kegg_parser.to_biological_entries(sample_kegg_pathways)
        
        # 合并条目
        all_entries = go_entries + kegg_entries
        
        print(f"   准备分类 {len(all_entries)} 个条目...")
        
        # 执行分类 (如果分类器可用)
        if CLASSIFIER_AVAILABLE:
            classifier = FiveSystemClassifier()
            classification_results = []
            
            for entry in all_entries:
                try:
                    result = classifier.classify_entry(entry)
                    classification_results.append(result)
                except Exception as e:
                    logger.warning(f"分类条目 {entry.id} 失败: {e}")
                    continue
            
            print(f"   成功分类 {len(classification_results)} 个条目")
        else:
            # 创建模拟分类结果用于演示
            from unittest.mock import Mock
            classification_results = []
            
            for i, entry in enumerate(all_entries[:len(all_entries)//2]):  # 模拟50%覆盖率
                mock_result = Mock()
                mock_result.entry_id = entry.id
                mock_result.primary_system = ['System A', 'System B', 'System C'][i % 3]
                mock_result.subsystem = None
                mock_result.all_systems = [mock_result.primary_system]
                mock_result.confidence_score = 0.8
                classification_results.append(mock_result)
            
            print(f"   使用模拟分类结果 {len(classification_results)} 个条目 (分类器不可用)")
        
        # 检查分类覆盖率
        coverage_report = manager.check_classification_coverage(classification_results, all_entries)
        
        print(f"\n分类覆盖率检查结果:")
        print(f"- 总条目数: {coverage_report.statistics.total_entries:,}")
        print(f"- 已分类条目: {coverage_report.statistics.classified_entries:,}")
        print(f"- 未分类条目: {coverage_report.statistics.unclassified_entries:,}")
        print(f"- 覆盖率: {coverage_report.statistics.coverage_rate:.2%}")
        
        # 显示系统分布
        if coverage_report.statistics.system_distribution:
            print(f"\n系统分布:")
            for system, count in sorted(coverage_report.statistics.system_distribution.items()):
                percentage = (count / coverage_report.statistics.classified_entries * 100) \
                    if coverage_report.statistics.classified_entries > 0 else 0
                print(f"  {system}: {count:,} ({percentage:.1f}%)")
        
        # 显示数据源分析
        if coverage_report.statistics.source_distribution:
            print(f"\n数据源分析:")
            for source, source_stats in coverage_report.statistics.source_distribution.items():
                coverage_rate = (source_stats['classified'] / source_stats['total'] * 100) \
                    if source_stats['total'] > 0 else 0
                print(f"  {source}: {source_stats['classified']:,}/{source_stats['total']:,} ({coverage_rate:.1f}%)")
        
        # 显示失败原因分析
        if coverage_report.statistics.failure_categories:
            print(f"\n失败原因分析:")
            for category, count in coverage_report.statistics.failure_categories.items():
                percentage = (count / coverage_report.statistics.unclassified_entries * 100) \
                    if coverage_report.statistics.unclassified_entries > 0 else 0
                print(f"  {category}: {count:,} ({percentage:.1f}%)")
        
        # 显示改进建议
        if coverage_report.recommendations:
            print(f"\n改进建议:")
            for i, recommendation in enumerate(coverage_report.recommendations[:5], 1):
                print(f"  {i}. {recommendation}")
        
        print(f"\n3. 运行综合质量检查...")
        
        # 运行综合质量检查
        comprehensive_report = manager.run_comprehensive_quality_check(
            go_file, kegg_file, classification_results, all_entries
        )
        
        print(f"\n综合质量检查结果:")
        print(f"- 综合质量分数: {comprehensive_report.quality_score:.1f}/100")
        print(f"- 质量等级: {manager._get_quality_level(comprehensive_report.quality_score)}")
        
        # 显示集成分析
        if 'quality_coverage_correlation' in comprehensive_report.integration_analysis:
            correlation = comprehensive_report.integration_analysis['quality_coverage_correlation']
            print(f"- 质量-覆盖率关联: {correlation['correlation_strength']}")
            print(f"  {correlation['analysis']}")
        
        # 显示问题优先级
        issue_priorities = comprehensive_report.integration_analysis.get('issue_priorities', [])
        if issue_priorities:
            print(f"\n问题优先级 (前5个):")
            for i, issue in enumerate(issue_priorities[:5], 1):
                print(f"  {i}. [{issue['priority'].upper()}] {issue['description']}")
        
        # 显示综合建议
        if comprehensive_report.overall_recommendations:
            print(f"\n综合建议:")
            for i, recommendation in enumerate(comprehensive_report.overall_recommendations[:5], 1):
                print(f"  {i}. {recommendation}")
        
        # 生成质量仪表板数据
        dashboard_data = manager.generate_quality_dashboard_data(comprehensive_report)
        
        print(f"\n4. 质量仪表板摘要:")
        overview = dashboard_data['overview']
        print(f"- 综合质量分数: {overview['overall_quality_score']:.1f}")
        print(f"- 质量等级: {overview['quality_level']}")
        
        if 'data_quality' in dashboard_data['metrics']:
            dq_metrics = dashboard_data['metrics']['data_quality']
            print(f"- 数据质量分数: {dq_metrics['score']:.1f}")
            print(f"- 数据有效率: {dq_metrics['valid_entries']/dq_metrics['total_entries']:.2%}")
        
        if 'coverage' in dashboard_data['metrics']:
            cov_metrics = dashboard_data['metrics']['coverage']
            print(f"- 分类覆盖率: {cov_metrics['coverage_rate']:.2%}")
        
        # 显示警报
        alerts = dashboard_data.get('alerts', [])
        if alerts:
            print(f"\n质量警报:")
            for alert in alerts[:3]:
                severity_icon = "🔴" if alert['severity'] == 'critical' else "🟡" if alert['severity'] == 'high' else "🟢"
                print(f"  {severity_icon} [{alert['severity'].upper()}] {alert['message']}")
        
        print(f"\n5. 保存报告...")
        
        # 保存报告到结果目录
        output_dir = "results/data_quality_demo"
        manager.save_comprehensive_report(comprehensive_report, output_dir)
        
        print(f"   报告已保存到: {output_dir}")
        print(f"   - JSON格式: {comprehensive_report.report_id}_comprehensive.json")
        print(f"   - Markdown摘要: {comprehensive_report.report_id}_summary.md")
        print(f"   - 仪表板数据: {comprehensive_report.report_id}_dashboard.json")
        
    except Exception as e:
        print(f"分类覆盖率检查失败: {e}")
        logger.exception("详细错误信息:")
        return
    
    print(f"\n" + "=" * 60)
    print("数据质量检查演示完成！")
    print("=" * 60)


def demo_consistency_validation():
    """演示分类一致性验证"""
    print("\n" + "=" * 60)
    print("分类一致性验证演示")
    print("=" * 60)
    
    # 创建模拟分类结果
    from unittest.mock import Mock
    
    # 一致的分类结果
    consistent_results = [
        Mock(
            entry_id='GO:0000001',
            primary_system='System A',
            all_systems=['System A', 'System B'],
            confidence_score=0.9
        ),
        Mock(
            entry_id='GO:0000002',
            primary_system='System B',
            all_systems=['System B'],
            confidence_score=0.8
        ),
        Mock(
            entry_id='KEGG:00010',
            primary_system='System C',
            all_systems=['System C'],
            confidence_score=0.85
        )
    ]
    
    # 不一致的分类结果
    inconsistent_results = [
        Mock(
            entry_id='GO:0000003',
            primary_system='System A',
            all_systems=['System B', 'System C'],  # 主系统不在列表中
            confidence_score=0.7
        ),
        Mock(
            entry_id='GO:0000004',
            primary_system='System D',
            all_systems=['System D'],
            confidence_score=0.6
        )
    ]
    
    all_results = consistent_results + inconsistent_results
    
    # 执行一致性分析
    manager = DataQualityManager()
    consistency_analysis = manager.validate_classification_consistency(all_results)
    
    print(f"一致性验证结果:")
    print(f"- 总条目数: {consistency_analysis['total_entries']}")
    print(f"- 一致条目数: {consistency_analysis['consistent_entries']}")
    print(f"- 不一致条目数: {consistency_analysis['inconsistent_entries']}")
    print(f"- 一致性率: {consistency_analysis['consistency_rate']:.2%}")
    
    if consistency_analysis['inconsistency_details']:
        print(f"\n不一致详情:")
        for detail in consistency_analysis['inconsistency_details']:
            print(f"  - 条目 {detail['entry_id']}: {detail['issue']}")
            print(f"    主系统: {detail['primary_system']}")
            print(f"    所有系统: {detail['all_systems']}")
    
    print("分类一致性验证演示完成！")


if __name__ == "__main__":
    try:
        # 运行主要演示
        demo_data_quality_check()
        
        # 运行一致性验证演示
        demo_consistency_validation()
        
    except KeyboardInterrupt:
        print("\n演示被用户中断")
    except Exception as e:
        print(f"\n演示过程中发生错误: {e}")
        logger.exception("详细错误信息:")