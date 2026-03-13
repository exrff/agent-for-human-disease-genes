"""
最终项目报告测试

测试最终项目报告的生成功能。
"""

import unittest
from pathlib import Path
import json
import pandas as pd
from .final_project_report import FinalProjectReportGenerator, ProjectSummary


class FinalReportTest(unittest.TestCase):
    """最终报告测试类"""
    
    def setUp(self):
        """测试初始化"""
        self.generator = FinalProjectReportGenerator()
    
    def test_generate_comprehensive_report(self):
        """测试生成综合报告"""
        print("\n生成最终项目报告...")
        
        # 生成报告
        report = self.generator.generate_comprehensive_report()
        
        # 验证报告结构
        self.assertIn('project_summary', report)
        self.assertIn('executive_summary', report)
        self.assertIn('methodology', report)
        self.assertIn('figures', report)
        self.assertIn('tables', report)
        self.assertIn('validation_results', report)
        self.assertIn('recommendations', report)
        self.assertIn('future_work', report)
        
        # 验证文件生成
        report_file = self.generator.report_dir / "final_project_report.json"
        self.assertTrue(report_file.exists(), "JSON报告文件未生成")
        
        markdown_file = self.generator.report_dir / "final_project_report.md"
        self.assertTrue(markdown_file.exists(), "Markdown报告文件未生成")
        
        # 验证图表生成
        expected_figures = [
            "figure_1_system_distribution.png",
            "figure_2_validation_heatmap.png", 
            "figure_3_time_series.png",
            "figure_4_similarity_matrix.png"
        ]
        
        for fig_name in expected_figures:
            fig_path = self.generator.report_dir / fig_name
            self.assertTrue(fig_path.exists(), f"图表文件未生成: {fig_name}")
        
        # 验证表格生成
        expected_tables = [
            "table_1_system_statistics.csv",
            "table_2_validation_results.csv",
            "table_3_performance_comparison.csv"
        ]
        
        for table_name in expected_tables:
            table_path = self.generator.report_dir / table_name
            self.assertTrue(table_path.exists(), f"表格文件未生成: {table_name}")
        
        print(f"  - 报告生成完成: {report_file}")
        print(f"  - Markdown版本: {markdown_file}")
        print(f"  - 生成图表: {len(expected_figures)}个")
        print(f"  - 生成表格: {len(expected_tables)}个")
        
        # 验证报告内容质量
        self.assertGreater(len(report['executive_summary']), 100, "执行摘要内容过短")
        self.assertGreater(len(report['methodology']), 3, "方法学部分内容不足")
        self.assertGreater(len(report['recommendations']), 3, "建议数量不足")
        self.assertGreater(len(report['future_work']), 3, "未来工作建议不足")
    
    def test_project_summary_creation(self):
        """测试项目摘要创建"""
        print("\n测试项目摘要创建...")
        
        summary = self.generator._collect_project_data()
        
        self.assertIsInstance(summary, ProjectSummary)
        self.assertEqual(summary.project_name, "五大功能系统分类研究")
        self.assertIsNotNone(summary.version)
        self.assertIsNotNone(summary.completion_date)
        
        print(f"  - 项目名称: {summary.project_name}")
        print(f"  - 版本: {summary.version}")
        print(f"  - GO条目: {summary.total_go_terms}")
        print(f"  - KEGG通路: {summary.total_kegg_pathways}")
    
    def test_methodology_document(self):
        """测试方法学文档生成"""
        print("\n测试方法学文档生成...")
        
        methodology = self.generator._generate_methodology_document()
        
        expected_sections = [
            'overview', 'classification_framework', 'data_sources',
            'classification_algorithm', 'validation_approach', 'statistical_methods'
        ]
        
        for section in expected_sections:
            self.assertIn(section, methodology, f"缺少方法学部分: {section}")
            self.assertGreater(len(methodology[section]), 50, f"方法学部分内容过短: {section}")
        
        print(f"  - 方法学部分数量: {len(methodology)}")
        print(f"  - 总字数: {sum(len(content) for content in methodology.values())}")
    
    def test_statistical_tables(self):
        """测试统计表格生成"""
        print("\n测试统计表格生成...")
        
        tables_info = self.generator._generate_statistical_tables()
        
        self.assertEqual(len(tables_info), 3, "应该生成3个统计表格")
        
        # 验证每个表格文件
        for table_name, table_path in tables_info.items():
            path = Path(table_path)
            self.assertTrue(path.exists(), f"表格文件不存在: {table_path}")
            
            # 验证CSV内容
            df = pd.read_csv(path)
            self.assertGreater(len(df), 0, f"表格内容为空: {table_name}")
            
            print(f"  - {table_name}: {len(df)}行 x {len(df.columns)}列")
    
    def test_validation_results_collection(self):
        """测试验证结果收集"""
        print("\n测试验证结果收集...")
        
        validation_results = self.generator._collect_validation_results()
        
        self.assertIn('datasets_tested', validation_results)
        self.assertIn('datasets_passed', validation_results)
        self.assertIn('success_rate', validation_results)
        self.assertIn('key_findings', validation_results)
        self.assertIn('statistical_significance', validation_results)
        
        self.assertGreater(len(validation_results['key_findings']), 0, "缺少关键发现")
        
        print(f"  - 测试数据集: {validation_results['datasets_tested']}")
        print(f"  - 通过验证: {validation_results['datasets_passed']}")
        print(f"  - 成功率: {validation_results['success_rate']:.1%}")
        print(f"  - 关键发现: {len(validation_results['key_findings'])}条")


if __name__ == '__main__':
    unittest.main(verbosity=2)