"""
可视化模块演示脚本

演示五大功能系统分类的完整可视化功能，包括结果导出、
统计报告生成和图表可视化。
"""

import sys
from pathlib import Path
import logging

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.visualization.result_exporter import ResultExporter
from src.visualization.statistics_generator import StatisticsGenerator
from src.visualization.chart_generator import ChartGenerator
from src.models.classification_result import ClassificationResult, FunctionalSystem
from src.models.biological_entry import BiologicalEntry


def create_sample_data():
    """创建示例数据用于演示"""
    
    # 创建示例生物学条目
    entries = [
        BiologicalEntry(
            id="GO:0008150",
            name="biological_process",
            definition="A biological process represents a specific objective that the organism is genetically programmed to achieve.",
            source="GO",
            namespace="biological_process"
        ),
        BiologicalEntry(
            id="GO:0006281",
            name="DNA repair",
            definition="The process of restoring DNA after damage.",
            source="GO",
            namespace="biological_process"
        ),
        BiologicalEntry(
            id="GO:0006955",
            name="immune response",
            definition="Any immune system process that functions in the calibrated response of an organism to a potential internal or invasive threat.",
            source="GO",
            namespace="biological_process"
        ),
        BiologicalEntry(
            id="GO:0008152",
            name="metabolic process",
            definition="The chemical reactions and pathways, including anabolism and catabolism.",
            source="GO",
            namespace="biological_process"
        ),
        BiologicalEntry(
            id="KEGG:04110",
            name="Cell cycle",
            definition="Cell cycle pathway",
            source="KEGG",
            hierarchy=("Genetic Information Processing", "Replication and repair")
        ),
        BiologicalEntry(
            id="KEGG:04612",
            name="Antigen processing and presentation",
            definition="Antigen processing and presentation pathway",
            source="KEGG",
            hierarchy=("Organismal Systems", "Immune system")
        )
    ]
    
    # 创建示例分类结果
    results = [
        ClassificationResult(
            entry_id="GO:0008150",
            primary_system=FunctionalSystem.SYSTEM_0.value,
            subsystem=None,
            all_systems=[FunctionalSystem.SYSTEM_0.value],
            confidence_score=0.95
        ),
        ClassificationResult(
            entry_id="GO:0006281",
            primary_system=FunctionalSystem.SYSTEM_A.value,
            subsystem="A1",
            all_systems=[FunctionalSystem.SYSTEM_A.value],
            confidence_score=0.92
        ),
        ClassificationResult(
            entry_id="GO:0006955",
            primary_system=FunctionalSystem.SYSTEM_B.value,
            subsystem="B1",
            all_systems=[FunctionalSystem.SYSTEM_B.value],
            inflammation_polarity="pro-inflammatory",
            confidence_score=0.88
        ),
        ClassificationResult(
            entry_id="GO:0008152",
            primary_system=FunctionalSystem.SYSTEM_C.value,
            subsystem="C1",
            all_systems=[FunctionalSystem.SYSTEM_C.value],
            confidence_score=0.90
        ),
        ClassificationResult(
            entry_id="KEGG:04110",
            primary_system=FunctionalSystem.SYSTEM_A.value,
            subsystem="A2",
            all_systems=[FunctionalSystem.SYSTEM_A.value],
            confidence_score=0.85
        ),
        ClassificationResult(
            entry_id="KEGG:04612",
            primary_system=FunctionalSystem.SYSTEM_B.value,
            subsystem="B2",
            all_systems=[FunctionalSystem.SYSTEM_B.value],
            confidence_score=0.93
        )
    ]
    
    return results, entries


def demo_result_export():
    """演示结果导出功能"""
    print("\n" + "="*60)
    print("演示结果导出功能")
    print("="*60)
    
    results, entries = create_sample_data()
    
    # 创建导出器
    exporter = ResultExporter(output_dir="results/demo_export")
    
    # 导出CSV格式
    csv_path = exporter.export_to_csv(results, entries, "demo_results.csv", "v8.0")
    print(f"✓ CSV导出完成: {csv_path}")
    
    # 导出JSON格式
    json_path = exporter.export_to_json(results, entries, "demo_results.json", "v8.0")
    print(f"✓ JSON导出完成: {json_path}")
    
    # 按系统导出
    system_paths = exporter.export_by_system(results, entries, "v8.0")
    print(f"✓ 按系统导出完成: {len(system_paths)} 个文件")
    
    # 导出元数据
    metadata_path = exporter.export_summary_metadata(results, entries, "v8.0")
    print(f"✓ 元数据导出完成: {metadata_path}")
    
    # 验证导出文件
    validation_result = exporter.validate_export(csv_path)
    print(f"✓ 文件验证: {'通过' if not validation_result['errors'] else '失败'}")
    if validation_result['errors']:
        for error in validation_result['errors']:
            print(f"  - 错误: {error}")


def demo_statistics_generation():
    """演示统计报告生成功能"""
    print("\n" + "="*60)
    print("演示统计报告生成功能")
    print("="*60)
    
    results, entries = create_sample_data()
    
    # 创建统计生成器
    stats_generator = StatisticsGenerator(output_dir="results/demo_reports")
    
    # 生成系统分布报告
    distribution = stats_generator.generate_system_distribution_report(results, entries)
    print(f"✓ 系统分布统计: {distribution['total_entries']} 个条目")
    for system, data in distribution['systems'].items():
        print(f"  - {system}: {data['count']} ({data['percentage']:.1f}%)")
    
    # 生成覆盖率分析
    coverage = stats_generator.generate_coverage_analysis(results, entries)
    print(f"✓ 分类覆盖率: {coverage['overall_coverage']['classification_rate']:.1f}%")
    
    # 生成质量指标
    quality = stats_generator.generate_quality_metrics(results)
    print(f"✓ 平均置信度: {quality['confidence_statistics']['mean']:.3f}")
    
    # 生成子系统分析
    subsystem_analysis = stats_generator.generate_subsystem_analysis(results)
    print(f"✓ 子系统分析: {len(subsystem_analysis)} 个主系统")
    
    # 生成炎症分析
    inflammation_analysis = stats_generator.generate_inflammation_analysis(results)
    print(f"✓ 炎症极性分析: {len(inflammation_analysis['overall_distribution'])} 种极性")
    
    # 生成综合报告
    report_path = stats_generator.generate_comprehensive_report(results, entries, "v8.0")
    print(f"✓ 综合报告生成: {report_path}")


def demo_chart_generation():
    """演示图表生成功能"""
    print("\n" + "="*60)
    print("演示图表生成功能")
    print("="*60)
    
    results, entries = create_sample_data()
    
    # 创建图表生成器
    chart_generator = ChartGenerator(output_dir="results/demo_figures")
    
    try:
        # 生成系统分布饼图
        pie_path = chart_generator.generate_system_distribution_pie(results)
        print(f"✓ 系统分布饼图: {pie_path}")
        
        # 生成系统分布条形图
        bar_path = chart_generator.generate_system_bar_chart(results, entries)
        print(f"✓ 系统分布条形图: {bar_path}")
        
        # 生成词云图
        wordcloud_path = chart_generator.generate_wordclouds(results, entries)
        if wordcloud_path:
            print(f"✓ 系统词云图: {wordcloud_path}")
        else:
            print("⚠ 词云图生成跳过 (数据不足)")
        
        # 生成置信度分布图
        confidence_path = chart_generator.generate_confidence_distribution(results)
        print(f"✓ 置信度分布图: {confidence_path}")
        
        # 生成综合仪表板
        dashboard_path = chart_generator.generate_comprehensive_dashboard(results, entries)
        print(f"✓ 综合仪表板: {dashboard_path}")
        
    except Exception as e:
        print(f"⚠ 图表生成过程中出现错误: {e}")
        print("这可能是由于缺少matplotlib或其他可视化依赖库")


def main():
    """主演示函数"""
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("五大功能系统分类 - 可视化模块演示")
    print("="*60)
    
    try:
        # 演示结果导出
        demo_result_export()
        
        # 演示统计报告生成
        demo_statistics_generation()
        
        # 演示图表生成
        demo_chart_generation()
        
        print("\n" + "="*60)
        print("演示完成！")
        print("="*60)
        print("\n生成的文件位置:")
        print("- 导出结果: results/demo_export/")
        print("- 统计报告: results/demo_reports/")
        print("- 可视化图表: results/demo_figures/")
        
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()