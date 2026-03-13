"""
可视化模块测试

测试五大功能系统分类的可视化功能，包括结果导出、
统计报告生成和图表可视化。
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import json
import pandas as pd

from src.visualization.result_exporter import ResultExporter
from src.visualization.statistics_generator import StatisticsGenerator
from src.visualization.chart_generator import ChartGenerator
from src.models.classification_result import ClassificationResult, FunctionalSystem
from src.models.biological_entry import BiologicalEntry


class TestResultExporter(unittest.TestCase):
    """测试结果导出器"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.exporter = ResultExporter(output_dir=self.temp_dir)
        
        # 创建测试数据
        self.entries = [
            BiologicalEntry(
                id="GO:0006281",
                name="DNA repair",
                definition="The process of restoring DNA after damage.",
                source="GO",
                namespace="biological_process"
            ),
            BiologicalEntry(
                id="KEGG:04110",
                name="Cell cycle",
                definition="Cell cycle pathway",
                source="KEGG",
                hierarchy=("Genetic Information Processing", "Replication and repair")
            )
        ]
        
        self.results = [
            ClassificationResult(
                entry_id="GO:0006281",
                primary_system=FunctionalSystem.SYSTEM_A.value,
                subsystem="A1",
                all_systems=[FunctionalSystem.SYSTEM_A.value],
                confidence_score=0.92
            ),
            ClassificationResult(
                entry_id="KEGG:04110",
                primary_system=FunctionalSystem.SYSTEM_A.value,
                subsystem="A2",
                all_systems=[FunctionalSystem.SYSTEM_A.value],
                confidence_score=0.85
            )
        ]
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)
    
    def test_export_to_csv(self):
        """测试CSV导出功能"""
        output_path = self.exporter.export_to_csv(self.results, self.entries)
        
        # 验证文件存在
        self.assertTrue(output_path.exists())
        
        # 验证CSV内容
        df = pd.read_csv(output_path)
        self.assertEqual(len(df), 2)
        self.assertIn('ID', df.columns)
        self.assertIn('Primary_System', df.columns)
        self.assertEqual(df.iloc[0]['ID'], 'GO:0006281')
    
    def test_export_to_json(self):
        """测试JSON导出功能"""
        output_path = self.exporter.export_to_json(self.results, self.entries)
        
        # 验证文件存在
        self.assertTrue(output_path.exists())
        
        # 验证JSON内容
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertIn('metadata', data)
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 2)
    
    def test_export_by_system(self):
        """测试按系统导出功能"""
        output_paths = self.exporter.export_by_system(self.results, self.entries)
        
        # 验证文件数量
        self.assertEqual(len(output_paths), 1)  # 只有System A
        
        # 验证文件存在
        for path in output_paths.values():
            self.assertTrue(path.exists())
    
    def test_validate_export(self):
        """测试导出验证功能"""
        output_path = self.exporter.export_to_csv(self.results, self.entries)
        validation_result = self.exporter.validate_export(output_path)
        
        self.assertTrue(validation_result['file_exists'])
        self.assertTrue(validation_result['required_fields_present'])
        self.assertEqual(validation_result['row_count'], 2)
        self.assertEqual(len(validation_result['errors']), 0)


class TestStatisticsGenerator(unittest.TestCase):
    """测试统计生成器"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.stats_generator = StatisticsGenerator(output_dir=self.temp_dir)
        
        # 创建测试数据
        self.entries = [
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
                definition="Any immune system process that functions in the calibrated response.",
                source="GO",
                namespace="biological_process"
            )
        ]
        
        self.results = [
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
            )
        ]
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)
    
    def test_generate_system_distribution_report(self):
        """测试系统分布报告生成"""
        distribution = self.stats_generator.generate_system_distribution_report(
            self.results, self.entries
        )
        
        self.assertEqual(distribution['total_entries'], 2)
        self.assertIn('systems', distribution)
        self.assertIn('System A', distribution['systems'])
        self.assertIn('System B', distribution['systems'])
    
    def test_generate_coverage_analysis(self):
        """测试覆盖率分析"""
        coverage = self.stats_generator.generate_coverage_analysis(
            self.results, self.entries
        )
        
        self.assertIn('overall_coverage', coverage)
        self.assertEqual(coverage['overall_coverage']['total_entries'], 2)
        self.assertEqual(coverage['overall_coverage']['classified_entries'], 2)
        self.assertEqual(coverage['overall_coverage']['classification_rate'], 100.0)
    
    def test_generate_quality_metrics(self):
        """测试质量指标生成"""
        quality = self.stats_generator.generate_quality_metrics(self.results)
        
        self.assertIn('confidence_statistics', quality)
        self.assertIn('mean', quality['confidence_statistics'])
        self.assertAlmostEqual(quality['confidence_statistics']['mean'], 0.9, places=1)
    
    def test_generate_comprehensive_report(self):
        """测试综合报告生成"""
        report_path = self.stats_generator.generate_comprehensive_report(
            self.results, self.entries, "test_v1.0"
        )
        
        # 验证文件存在
        self.assertTrue(report_path.exists())
        
        # 验证JSON内容
        with open(report_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertIn('report_metadata', data)
        self.assertIn('system_distribution', data)
        self.assertIn('coverage_analysis', data)
        self.assertIn('quality_metrics', data)


class TestChartGenerator(unittest.TestCase):
    """测试图表生成器"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.chart_generator = ChartGenerator(output_dir=self.temp_dir)
        
        # 创建测试数据
        self.entries = [
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
                definition="Any immune system process that functions in the calibrated response.",
                source="GO",
                namespace="biological_process"
            )
        ]
        
        self.results = [
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
                confidence_score=0.88
            )
        ]
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)
    
    def test_generate_system_distribution_pie(self):
        """测试饼图生成"""
        try:
            output_path = self.chart_generator.generate_system_distribution_pie(self.results)
            self.assertTrue(output_path.exists())
        except ImportError:
            self.skipTest("matplotlib not available")
    
    def test_generate_system_bar_chart(self):
        """测试条形图生成"""
        try:
            output_path = self.chart_generator.generate_system_bar_chart(
                self.results, self.entries
            )
            self.assertTrue(output_path.exists())
        except ImportError:
            self.skipTest("matplotlib not available")
    
    def test_generate_confidence_distribution(self):
        """测试置信度分布图生成"""
        try:
            output_path = self.chart_generator.generate_confidence_distribution(self.results)
            self.assertTrue(output_path.exists())
        except ImportError:
            self.skipTest("matplotlib not available")
    
    def test_clean_text_for_wordcloud(self):
        """测试文本清洗功能"""
        text = "DNA repair process involved in metabolic response"
        cleaned = self.chart_generator._clean_text_for_wordcloud(text)
        
        # 验证停用词被移除
        self.assertNotIn('process', cleaned)
        self.assertNotIn('involved', cleaned)
        
        # 验证有效词保留
        self.assertIn('repair', cleaned)
        self.assertIn('metabolic', cleaned)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestResultExporter,
        TestStatisticsGenerator,
        TestChartGenerator
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)