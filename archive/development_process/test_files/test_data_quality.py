"""
数据质量检查测试

测试数据质量检查器和分类覆盖率检查器的功能。
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch
import sys

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_quality_checker import DataQualityChecker, DataQualityIssue, DataQualityReport
from utils.classification_coverage_checker import (
    ClassificationCoverageChecker, ClassificationFailure, CoverageReport, CoverageStatistics
)
from utils.data_quality_manager import DataQualityManager, ComprehensiveQualityReport
from models.biological_entry import BiologicalEntry
from models.classification_result import ClassificationResult


class TestDataQualityChecker:
    """数据质量检查器测试"""
    
    def setup_method(self):
        """测试设置"""
        self.checker = DataQualityChecker()
    
    def create_test_go_file(self, content: str) -> str:
        """创建测试GO文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.obo', delete=False, encoding='utf-8') as f:
            f.write(content)
            return f.name
    
    def create_test_kegg_file(self, content: str) -> str:
        """创建测试KEGG文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
            return f.name
    
    def test_go_file_quality_check_valid(self):
        """测试有效GO文件的质量检查"""
        go_content = """
[Term]
id: GO:0000001
name: mitochondrion inheritance
namespace: biological_process
def: "The distribution of mitochondria, including the mitochondrial genome, into daughter cells after mitosis or meiosis, mediated by interactions between mitochondria and the cytoskeleton." [GOC:mcc, PMID:10873824, PMID:11389764]

[Term]
id: GO:0000002
name: mitochondrial genome maintenance
namespace: biological_process
def: "The maintenance of the structure and integrity of the mitochondrial genome; includes replication and segregation of the mitochondrial chromosome." [GOC:ai, GOC:vw]
"""
        
        go_file = self.create_test_go_file(go_content)
        
        try:
            report = self.checker.check_go_file_quality(go_file)
            
            assert report is not None
            assert report.total_entries == 2
            assert report.valid_entries == 2
            assert len(report.get_issues_by_severity('error')) == 0
            
        finally:
            Path(go_file).unlink()
    
    def test_go_file_quality_check_invalid(self):
        """测试无效GO文件的质量检查"""
        go_content = """
[Term]
id: INVALID_ID
name: 
namespace: invalid_namespace

[Term]
id: GO:0000002
name: valid term
namespace: biological_process
"""
        
        go_file = self.create_test_go_file(go_content)
        
        try:
            report = self.checker.check_go_file_quality(go_file)
            
            assert report is not None
            assert report.total_entries == 2
            assert report.valid_entries == 1
            assert len(report.get_issues_by_severity('error')) > 0
            
            # 检查具体错误
            errors = report.get_issues_by_severity('error')
            error_descriptions = [error.description for error in errors]
            
            assert any('GO ID格式不正确' in desc for desc in error_descriptions)
            assert any('缺少必需字段' in desc for desc in error_descriptions)
            assert any('无效的命名空间' in desc for desc in error_descriptions)
            
        finally:
            Path(go_file).unlink()
    
    def test_kegg_file_quality_check_valid(self):
        """测试有效KEGG文件的质量检查"""
        kegg_content = """
AMetabolism
B  Carbohydrate metabolism
C    00010  Glycolysis / Gluconeogenesis
C    00020  Citrate cycle (TCA cycle)
B  Lipid metabolism
C    00061  Fatty acid biosynthesis
"""
        
        kegg_file = self.create_test_kegg_file(kegg_content)
        
        try:
            report = self.checker.check_kegg_file_quality(kegg_file)
            
            assert report is not None
            assert report.total_entries == 3
            assert report.valid_entries == 3
            assert len(report.get_issues_by_severity('error')) == 0
            
        finally:
            Path(kegg_file).unlink()
    
    def test_kegg_file_quality_check_invalid(self):
        """测试无效KEGG文件的质量检查"""
        kegg_content = """
AMetabolism
B  Carbohydrate metabolism
C    INVALID  
C    00020  
B  
C    00061  Fatty acid biosynthesis
"""
        
        kegg_file = self.create_test_kegg_file(kegg_content)
        
        try:
            report = self.checker.check_kegg_file_quality(kegg_file)
            
            assert report is not None
            assert len(report.get_issues_by_severity('error')) > 0
            
            # 检查具体错误 - 更新为实际的错误消息
            errors = report.get_issues_by_severity('error')
            error_descriptions = [error.description for error in errors]
            
            # 检查是否有格式错误或无效条目
            has_format_error = any('格式' in desc or 'INVALID' in desc for desc in error_descriptions)
            assert has_format_error, f"Expected format error, got: {error_descriptions}"
            
        finally:
            Path(kegg_file).unlink()
    
    def test_data_consistency_check(self):
        """测试数据一致性检查"""
        go_content = """
[Term]
id: GO:0000001
name: test term
namespace: biological_process
def: "Test definition" [GOC:test]
"""
        
        kegg_content = """
AMetabolism
B  Carbohydrate metabolism
C    00010  Glycolysis / Gluconeogenesis
"""
        
        go_file = self.create_test_go_file(go_content)
        kegg_file = self.create_test_kegg_file(kegg_content)
        
        try:
            report = self.checker.check_data_consistency(go_file, kegg_file)
            
            assert report is not None
            assert len(report.source_files) == 2
            assert report.total_entries == 2  # 1 GO + 1 KEGG
            assert 'go_statistics' in report.statistics
            assert 'kegg_statistics' in report.statistics
            
        finally:
            Path(go_file).unlink()
            Path(kegg_file).unlink()
    
    def test_missing_file_handling(self):
        """测试缺失文件处理"""
        non_existent_file = "/path/to/non/existent/file.obo"
        
        report = self.checker.check_go_file_quality(non_existent_file)
        
        assert report is not None
        assert len(report.get_issues_by_severity('error')) > 0
        
        error = report.get_issues_by_severity('error')[0]
        assert error.issue_type == 'missing'
        assert '不存在' in error.description


class TestClassificationCoverageChecker:
    """分类覆盖率检查器测试"""
    
    def setup_method(self):
        """测试设置"""
        self.checker = ClassificationCoverageChecker()
    
    def create_test_entries(self) -> list:
        """创建测试条目"""
        return [
            BiologicalEntry(
                id='GO:0000001',
                name='DNA repair',
                definition='Process of repairing DNA damage',
                source='GO',
                namespace='biological_process'
            ),
            BiologicalEntry(
                id='GO:0000002',
                name='immune response',
                definition='Response to pathogen invasion',
                source='GO',
                namespace='biological_process'
            ),
            BiologicalEntry(
                id='KEGG:00010',
                name='Glycolysis',
                definition='Glucose metabolism pathway',
                source='KEGG',
                hierarchy=('Metabolism', 'Carbohydrate metabolism')
            )
        ]
    
    def create_test_classification_results(self) -> list:
        """创建测试分类结果"""
        return [
            Mock(
                entry_id='GO:0000001',
                primary_system='System A',
                subsystem='A1',
                all_systems=['System A'],
                confidence_score=0.9
            ),
            Mock(
                entry_id='KEGG:00010',
                primary_system='System C',
                subsystem='C1',
                all_systems=['System C'],
                confidence_score=0.8
            )
            # 注意：GO:0000002 没有分类结果，用于测试未分类情况
        ]
    
    def test_classification_coverage_check(self):
        """测试分类覆盖率检查"""
        entries = self.create_test_entries()
        results = self.create_test_classification_results()
        
        report = self.checker.check_classification_coverage(results, entries)
        
        assert report is not None
        assert report.statistics.total_entries == 3
        assert report.statistics.classified_entries == 2
        assert report.statistics.unclassified_entries == 1
        assert report.statistics.coverage_rate == 2/3
        
        # 检查失败记录
        assert len(report.failures) == 1
        failure = report.failures[0]
        assert failure.entry_id == 'GO:0000002'
        assert failure.source == 'GO'
    
    def test_classification_failure_analysis(self):
        """测试分类失败分析"""
        # 创建一个有效的条目但没有分类结果来模拟分类失败
        valid_entry = BiologicalEntry(
            id='GO:0000003',
            name='unknown process',
            definition='Process with no clear classification',
            source='GO',
            namespace='biological_process'
        )
        
        failure = self.checker._analyze_classification_failure(valid_entry)
        
        assert failure.entry_id == 'GO:0000003'
        # 由于条目是有效的，失败类别应该是no_match而不是invalid_input
        assert failure.failure_category in ['no_match', 'ambiguous_match']
    
    def test_system_suggestion(self):
        """测试系统建议功能"""
        # 创建包含免疫关键词的条目
        immune_entry = BiologicalEntry(
            id='GO:0000004',
            name='immune defense response',
            definition='Defense against pathogen infection',
            source='GO',
            namespace='biological_process'
        )
        
        failure = self.checker._suggest_potential_system(
            immune_entry, 
            ClassificationFailure(
                entry_id='GO:0000004',
                entry_name='immune defense response',
                source='GO',
                failure_reason='',
                failure_category='no_match'
            )
        )
        
        assert failure.suggested_system == 'System B'
        assert failure.confidence_score > 0
        assert failure.failure_category == 'ambiguous'
    
    def test_classification_consistency_analysis(self):
        """测试分类一致性分析"""
        # 创建一致的分类结果
        consistent_results = [
            Mock(
                entry_id='GO:0000001',
                primary_system='System A',
                all_systems=['System A', 'System B']
            ),
            Mock(
                entry_id='GO:0000002',
                primary_system='System B',
                all_systems=['System B']
            )
        ]
        
        analysis = self.checker.analyze_classification_consistency(consistent_results)
        
        assert analysis['total_entries'] == 2
        assert analysis['consistent_entries'] == 2
        assert analysis['inconsistent_entries'] == 0
        assert analysis['consistency_rate'] == 1.0
    
    def test_coverage_report_serialization(self):
        """测试覆盖率报告序列化"""
        entries = self.create_test_entries()
        results = self.create_test_classification_results()
        
        report = self.checker.check_classification_coverage(results, entries)
        
        # 测试JSON序列化
        json_str = report.to_json()
        assert isinstance(json_str, str)
        
        # 验证JSON可以解析
        json_data = json.loads(json_str)
        assert 'report_id' in json_data
        assert 'statistics' in json_data
        assert 'failures' in json_data


class TestDataQualityManager:
    """数据质量管理器测试"""
    
    def setup_method(self):
        """测试设置"""
        self.manager = DataQualityManager()
    
    def create_test_files(self):
        """创建测试文件"""
        go_content = """
[Term]
id: GO:0000001
name: test process
namespace: biological_process
def: "Test definition" [GOC:test]
"""
        
        kegg_content = """
AMetabolism
B  Carbohydrate metabolism
C    00010  Test pathway
"""
        
        go_file = tempfile.NamedTemporaryFile(mode='w', suffix='.obo', delete=False, encoding='utf-8')
        go_file.write(go_content)
        go_file.close()
        
        kegg_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        kegg_file.write(kegg_content)
        kegg_file.close()
        
        return go_file.name, kegg_file.name
    
    def test_comprehensive_quality_check(self):
        """测试综合质量检查"""
        go_file, kegg_file = self.create_test_files()
        
        try:
            # 创建测试数据
            entries = [
                BiologicalEntry(
                    id='GO:0000001',
                    name='test process',
                    definition='Test definition',
                    source='GO',
                    namespace='biological_process'
                )
            ]
            
            results = [
                Mock(
                    entry_id='GO:0000001',
                    primary_system='System A',
                    all_systems=['System A'],
                    confidence_score=0.9
                )
            ]
            
            report = self.manager.run_comprehensive_quality_check(
                go_file, kegg_file, results, entries
            )
            
            assert report is not None
            assert report.data_quality_report is not None
            assert report.coverage_report is not None
            assert report.quality_score > 0
            assert len(report.overall_recommendations) > 0
            
        finally:
            Path(go_file).unlink()
            Path(kegg_file).unlink()
    
    def test_quality_score_calculation(self):
        """测试质量分数计算"""
        report = ComprehensiveQualityReport(
            report_id='test',
            timestamp=datetime.now()
        )
        
        # 模拟数据质量报告
        data_quality_report = Mock()
        data_quality_report.calculate_quality_score.return_value = 80.0
        report.data_quality_report = data_quality_report
        
        # 模拟覆盖率报告
        coverage_report = Mock()
        coverage_report.statistics = Mock()
        coverage_report.statistics.coverage_rate = 0.9
        report.coverage_report = coverage_report
        
        quality_score = report.calculate_overall_quality_score()
        
        # 验证加权计算: 80 * 0.4 + 90 * 0.6 = 86
        expected_score = 80 * 0.4 + 90 * 0.6
        assert abs(quality_score - expected_score) < 0.1
    
    def test_quality_dashboard_data_generation(self):
        """测试质量仪表板数据生成"""
        report = ComprehensiveQualityReport(
            report_id='test',
            timestamp=datetime.now(),
            quality_score=85.0
        )
        
        # 模拟报告数据
        data_quality_report = Mock()
        data_quality_report.calculate_quality_score.return_value = 80.0
        data_quality_report.total_entries = 100
        data_quality_report.valid_entries = 95
        data_quality_report.get_issues_by_severity.return_value = []
        report.data_quality_report = data_quality_report
        
        coverage_report = Mock()
        coverage_report.statistics = Mock()
        coverage_report.statistics.coverage_rate = 0.9
        coverage_report.statistics.total_entries = 100
        coverage_report.statistics.classified_entries = 90
        coverage_report.statistics.unclassified_entries = 10
        coverage_report.statistics.system_distribution = {'System A': 30, 'System B': 25}
        report.coverage_report = coverage_report
        
        dashboard_data = self.manager.generate_quality_dashboard_data(report)
        
        assert 'overview' in dashboard_data
        assert 'metrics' in dashboard_data
        assert 'alerts' in dashboard_data
        assert dashboard_data['overview']['overall_quality_score'] == 85.0
        assert dashboard_data['metrics']['data_quality']['score'] == 80.0
        assert dashboard_data['metrics']['coverage']['coverage_rate'] == 0.9
    
    def test_quality_alerts_generation(self):
        """测试质量警报生成"""
        report = ComprehensiveQualityReport(
            report_id='test',
            timestamp=datetime.now(),
            quality_score=50.0  # 低质量分数
        )
        
        # 模拟低质量数据
        data_quality_report = Mock()
        data_quality_report.calculate_quality_score.return_value = 60.0
        data_quality_report.get_issues_by_severity.return_value = [Mock(), Mock()]  # 2个错误
        report.data_quality_report = data_quality_report
        
        coverage_report = Mock()
        coverage_report.statistics = Mock()
        coverage_report.statistics.coverage_rate = 0.7  # 低覆盖率
        report.coverage_report = coverage_report
        
        alerts = self.manager._generate_quality_alerts(report)
        
        assert len(alerts) > 0
        
        # 检查警报类型
        alert_types = [alert['type'] for alert in alerts]
        assert 'quality_score_low' in alert_types
        assert 'data_quality_low' in alert_types
        assert 'coverage_rate_low' in alert_types
        assert 'data_quality_errors' in alert_types
    
    def test_comprehensive_report_serialization(self):
        """测试综合报告序列化"""
        report = ComprehensiveQualityReport(
            report_id='test',
            timestamp=datetime.now(),
            quality_score=85.0
        )
        
        # 测试JSON序列化
        json_str = report.to_json()
        assert isinstance(json_str, str)
        
        # 验证JSON可以解析
        json_data = json.loads(json_str)
        assert 'report_id' in json_data
        assert 'quality_score' in json_data
        assert json_data['quality_score'] == 85.0


def test_data_quality_integration():
    """集成测试：完整的数据质量检查流程"""
    # 创建测试文件
    go_content = """
[Term]
id: GO:0000001
name: DNA repair
namespace: biological_process
def: "Process of repairing DNA damage" [GOC:test]

[Term]
id: GO:0000002
name: immune response
namespace: biological_process
def: "Response to pathogen" [GOC:test]
"""
    
    kegg_content = """
AMetabolism
B  Carbohydrate metabolism
C    00010  Glycolysis / Gluconeogenesis
B  Lipid metabolism
C    00061  Fatty acid biosynthesis
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.obo', delete=False, encoding='utf-8') as go_file:
        go_file.write(go_content)
        go_file_path = go_file.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as kegg_file:
        kegg_file.write(kegg_content)
        kegg_file_path = kegg_file.name
    
    try:
        # 创建测试数据
        entries = [
            BiologicalEntry(
                id='GO:0000001',
                name='DNA repair',
                definition='Process of repairing DNA damage',
                source='GO',
                namespace='biological_process'
            ),
            BiologicalEntry(
                id='GO:0000002',
                name='immune response',
                definition='Response to pathogen',
                source='GO',
                namespace='biological_process'
            ),
            BiologicalEntry(
                id='KEGG:00010',
                name='Glycolysis / Gluconeogenesis',
                definition='Glucose metabolism pathway',
                source='KEGG',
                hierarchy=('Metabolism', 'Carbohydrate metabolism')
            )
        ]
        
        results = [
            Mock(
                entry_id='GO:0000001',
                primary_system='System A',
                subsystem='A1',
                all_systems=['System A'],
                confidence_score=0.9
            ),
            Mock(
                entry_id='KEGG:00010',
                primary_system='System C',
                subsystem='C1',
                all_systems=['System C'],
                confidence_score=0.8
            )
            # GO:0000002 未分类，用于测试覆盖率
        ]
        
        # 运行综合质量检查
        manager = DataQualityManager()
        report = manager.run_comprehensive_quality_check(
            go_file_path, kegg_file_path, results, entries
        )
        
        # 验证结果
        assert report is not None
        assert report.data_quality_report is not None
        assert report.coverage_report is not None
        assert report.quality_score > 0
        
        # 验证数据质量
        assert report.data_quality_report.total_entries == 4  # 2 GO + 2 KEGG
        assert report.data_quality_report.valid_entries > 0
        
        # 验证覆盖率
        assert report.coverage_report.statistics.total_entries == 3
        assert report.coverage_report.statistics.classified_entries == 2
        assert report.coverage_report.statistics.unclassified_entries == 1
        assert abs(report.coverage_report.statistics.coverage_rate - 2/3) < 0.01
        
        # 验证建议生成
        assert len(report.overall_recommendations) > 0
        
        # 验证集成分析
        assert 'quality_coverage_correlation' in report.integration_analysis
        assert 'issue_priorities' in report.integration_analysis
        
    finally:
        Path(go_file_path).unlink()
        Path(kegg_file_path).unlink()


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])