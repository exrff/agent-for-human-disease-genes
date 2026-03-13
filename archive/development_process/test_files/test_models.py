"""
数据模型属性测试

使用Hypothesis库进行基于属性的测试，验证数据模型的正确性。
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.strategies import composite
import json
from datetime import datetime
from typing import Dict, Any
import sys
from pathlib import Path

# 添加当前目录到Python路径以支持相对导入
sys.path.insert(0, str(Path(__file__).parent))

from biological_entry import BiologicalEntry
from classification_result import ClassificationResult, FunctionalSystem, InflammationPolarity
from validation_result import ValidationResult


# 测试数据生成策略
@composite
def go_id_strategy(draw):
    """生成GO ID策略"""
    number = draw(st.integers(min_value=1, max_value=9999999))
    return f"GO:{number:07d}"


@composite
def kegg_id_strategy(draw):
    """生成KEGG ID策略"""
    number = draw(st.integers(min_value=1, max_value=99999))
    return f"KEGG:{number:05d}"


@composite
def biological_entry_strategy(draw):
    """生成BiologicalEntry实例的策略"""
    source = draw(st.sampled_from(['GO', 'KEGG']))
    
    if source == 'GO':
        entry_id = draw(go_id_strategy())
        namespace = draw(st.sampled_from(['biological_process', 'molecular_function', 'cellular_component']))
        ancestors = draw(st.sets(go_id_strategy(), max_size=10))
        hierarchy = None
    else:
        entry_id = draw(kegg_id_strategy())
        namespace = None
        ancestors = set()
        class_a = draw(st.text(min_size=1, max_size=50))
        class_b = draw(st.text(min_size=1, max_size=50))
        hierarchy = (class_a, class_b)
    
    name = draw(st.text(min_size=1, max_size=200))
    definition = draw(st.text(min_size=1, max_size=500))
    metadata = draw(st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.one_of(st.text(), st.integers(), st.floats(), st.booleans()),
        max_size=5
    ))
    
    return BiologicalEntry(
        id=entry_id,
        name=name,
        definition=definition,
        source=source,
        namespace=namespace,
        ancestors=ancestors,
        hierarchy=hierarchy,
        metadata=metadata
    )


@composite
def classification_result_strategy(draw):
    """生成ClassificationResult实例的策略"""
    entry_id = draw(st.one_of(go_id_strategy(), kegg_id_strategy()))
    
    # 选择主要系统
    primary_system = draw(st.sampled_from([system.value for system in FunctionalSystem]))
    
    # 生成子系统
    subsystem_map = {
        FunctionalSystem.SYSTEM_A.value: ['A1', 'A2', 'A3', 'A4'],
        FunctionalSystem.SYSTEM_B.value: ['B1', 'B2', 'B3'],
        FunctionalSystem.SYSTEM_C.value: ['C1', 'C2', 'C3'],
        FunctionalSystem.SYSTEM_D.value: ['D1', 'D2'],
        FunctionalSystem.SYSTEM_E.value: ['E1', 'E2']
    }
    
    subsystem = None
    if primary_system in subsystem_map:
        subsystem = draw(st.one_of(
            st.none(),
            st.sampled_from(subsystem_map[primary_system])
        ))
    
    # 生成所有系统列表
    all_systems = draw(st.lists(
        st.sampled_from([system.value for system in FunctionalSystem]),
        min_size=1,
        max_size=3,
        unique=True
    ))
    
    # 确保主系统在列表中
    if primary_system not in all_systems:
        all_systems.insert(0, primary_system)
    
    # 炎症极性
    inflammation_polarity = draw(st.one_of(
        st.none(),
        st.sampled_from([polarity.value for polarity in InflammationPolarity])
    ))
    
    confidence_score = draw(st.floats(min_value=0.0, max_value=1.0))
    decision_path = draw(st.lists(st.text(min_size=1, max_size=100), max_size=10))
    metadata = draw(st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.one_of(st.text(), st.integers(), st.floats()),
        max_size=5
    ))
    
    return ClassificationResult(
        entry_id=entry_id,
        primary_system=primary_system,
        subsystem=subsystem,
        all_systems=all_systems,
        inflammation_polarity=inflammation_polarity,
        confidence_score=confidence_score,
        decision_path=decision_path,
        metadata=metadata
    )


@composite
def validation_result_strategy(draw):
    """生成ValidationResult实例的策略"""
    validation_type = draw(st.sampled_from([
        'semantic_coherence', 'ssgsea', 'baseline_comparison', 'integration_test'
    ]))
    
    # 生成系统相似度数据
    systems = ['System A', 'System B', 'System C', 'System D', 'System E']
    
    intra_system_similarity = draw(st.dictionaries(
        st.sampled_from(systems),
        st.floats(min_value=0.0, max_value=1.0),
        min_size=1,
        max_size=5
    ))
    
    # 生成系统间相似度
    inter_system_pairs = [(s1, s2) for s1 in systems for s2 in systems if s1 < s2]
    inter_system_similarity = draw(st.dictionaries(
        st.sampled_from(inter_system_pairs),
        st.floats(min_value=0.0, max_value=1.0),
        max_size=10
    ))
    
    clustering_quality_score = draw(st.floats(min_value=0.0, max_value=10.0))
    
    statistical_significance = draw(st.dictionaries(
        st.text(min_size=1, max_size=50),
        st.floats(min_value=0.0, max_value=1.0),
        max_size=5
    ))
    
    performance_metrics = draw(st.dictionaries(
        st.text(min_size=1, max_size=50),
        st.floats(min_value=0.0, max_value=1.0),
        max_size=5
    ))
    
    metadata = draw(st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.one_of(st.text(), st.integers(), st.floats()),
        max_size=5
    ))
    
    return ValidationResult(
        validation_type=validation_type,
        intra_system_similarity=intra_system_similarity,
        inter_system_similarity=inter_system_similarity,
        clustering_quality_score=clustering_quality_score,
        statistical_significance=statistical_significance,
        performance_metrics=performance_metrics,
        metadata=metadata
    )


class TestBiologicalEntry:
    """BiologicalEntry模型测试"""
    
    @given(biological_entry_strategy())
    @settings(max_examples=100)
    def test_biological_entry_creation(self, entry):
        """测试BiologicalEntry创建的基本属性"""
        # 验证必需字段存在
        assert entry.id is not None
        assert entry.name is not None
        assert entry.source in ['GO', 'KEGG']
        
        # 验证GO条目特定属性
        if entry.source == 'GO':
            assert entry.id.startswith('GO:')
            if entry.namespace:
                assert entry.namespace in ['biological_process', 'molecular_function', 'cellular_component']
        
        # 验证KEGG条目特定属性
        if entry.source == 'KEGG':
            assert entry.id.startswith('KEGG:')
    
    @given(biological_entry_strategy())
    @settings(max_examples=100)
    def test_biological_entry_serialization_round_trip(self, entry):
        """测试BiologicalEntry序列化往返一致性"""
        # 转换为字典
        entry_dict = entry.to_dict()
        
        # 从字典重建
        reconstructed = BiologicalEntry.from_dict(entry_dict)
        
        # 验证关键字段一致性
        assert reconstructed.id == entry.id
        assert reconstructed.name == entry.name
        assert reconstructed.definition == entry.definition
        assert reconstructed.source == entry.source
        assert reconstructed.namespace == entry.namespace
        assert reconstructed.ancestors == entry.ancestors
        assert reconstructed.hierarchy == entry.hierarchy
        assert reconstructed.metadata == entry.metadata
    
    @given(biological_entry_strategy())
    @settings(max_examples=100)
    def test_biological_entry_json_round_trip(self, entry):
        """测试BiologicalEntry JSON序列化往返一致性"""
        # 转换为JSON
        json_str = entry.to_json()
        
        # 验证JSON格式有效
        json_data = json.loads(json_str)
        assert isinstance(json_data, dict)
        
        # 从JSON重建
        reconstructed = BiologicalEntry.from_json(json_str)
        
        # 验证关键字段一致性
        assert reconstructed.id == entry.id
        assert reconstructed.name == entry.name
        assert reconstructed.source == entry.source


class TestClassificationResult:
    """ClassificationResult模型测试"""
    
    @given(classification_result_strategy())
    @settings(max_examples=100)
    def test_classification_result_creation(self, result):
        """测试ClassificationResult创建的基本属性"""
        # 验证必需字段
        assert result.entry_id is not None
        assert result.primary_system is not None
        assert 0 <= result.confidence_score <= 1
        
        # 验证主系统在所有系统列表中
        assert result.primary_system in result.all_systems
        
        # 验证系统有效性
        valid_systems = [system.value for system in FunctionalSystem]
        assert result.primary_system in valid_systems
        for system in result.all_systems:
            assert system in valid_systems
    
    @given(classification_result_strategy())
    @settings(max_examples=100)
    def test_classification_result_serialization_round_trip(self, result):
        """测试ClassificationResult序列化往返一致性"""
        # 转换为字典
        result_dict = result.to_dict()
        
        # 从字典重建
        reconstructed = ClassificationResult.from_dict(result_dict)
        
        # 验证关键字段一致性
        assert reconstructed.entry_id == result.entry_id
        assert reconstructed.primary_system == result.primary_system
        assert reconstructed.subsystem == result.subsystem
        assert reconstructed.all_systems == result.all_systems
        assert reconstructed.inflammation_polarity == result.inflammation_polarity
        assert abs(reconstructed.confidence_score - result.confidence_score) < 1e-10
    
    @given(classification_result_strategy())
    @settings(max_examples=100)
    def test_classification_result_csv_output_format(self, result):
        """
        **Feature: five-system-classification, Property 12: 输出格式完整性**
        **Validates: Requirements 8.1**
        
        测试分类结果CSV输出格式包含所有必需字段
        """
        csv_row = result.to_csv_row()
        
        # 验证必需字段存在
        required_fields = [
            'ID', 'Primary_System', 'Subsystem', 'All_Systems',
            'Inflammation_Polarity', 'Confidence_Score', 'Decision_Path'
        ]
        
        for field in required_fields:
            assert field in csv_row, f"Missing required field: {field}"
            assert csv_row[field] is not None, f"Field {field} should not be None"
        
        # 验证字段内容格式
        assert csv_row['ID'] == result.entry_id
        assert csv_row['Primary_System'] == result.primary_system
        assert csv_row['Confidence_Score'] == str(result.confidence_score)
        
        # 验证列表字段格式
        if result.all_systems:
            assert '; '.join(result.all_systems) == csv_row['All_Systems']
        
        if result.decision_path:
            assert ' -> '.join(result.decision_path) == csv_row['Decision_Path']


class TestValidationResult:
    """ValidationResult模型测试"""
    
    @given(validation_result_strategy())
    @settings(max_examples=100)
    def test_validation_result_creation(self, result):
        """测试ValidationResult创建的基本属性"""
        # 验证必需字段
        assert result.validation_type is not None
        valid_types = ['semantic_coherence', 'ssgsea', 'baseline_comparison', 'integration_test']
        assert result.validation_type in valid_types
        
        # 验证相似度分数范围
        for score in result.intra_system_similarity.values():
            assert 0 <= score <= 1
        
        for score in result.inter_system_similarity.values():
            assert 0 <= score <= 1
    
    @given(validation_result_strategy())
    @settings(max_examples=100)
    def test_validation_result_serialization_round_trip(self, result):
        """测试ValidationResult序列化往返一致性"""
        # 转换为字典
        result_dict = result.to_dict()
        
        # 从字典重建
        reconstructed = ValidationResult.from_dict(result_dict)
        
        # 验证关键字段一致性
        assert reconstructed.validation_type == result.validation_type
        assert reconstructed.intra_system_similarity == result.intra_system_similarity
        assert abs(reconstructed.clustering_quality_score - result.clustering_quality_score) < 1e-10
    
    @given(validation_result_strategy())
    @settings(max_examples=100)
    def test_validation_result_clustering_quality_calculation(self, result):
        """测试聚类质量计算的数学正确性"""
        if result.intra_system_similarity and result.inter_system_similarity:
            calculated_quality = result.calculate_clustering_quality()
            
            # 验证计算结果合理性
            assert calculated_quality >= 0
            
            # 如果系统间相似度为0，质量分数应该很高
            avg_inter = sum(result.inter_system_similarity.values()) / len(result.inter_system_similarity)
            if avg_inter == 0:
                avg_intra = sum(result.intra_system_similarity.values()) / len(result.intra_system_similarity)
                if avg_intra > 0:
                    assert calculated_quality == float('inf')
                else:
                    assert calculated_quality == 1.0


class TestModelIntegration:
    """模型集成测试"""
    
    @given(
        biological_entry_strategy(),
        classification_result_strategy(),
        validation_result_strategy()
    )
    @settings(max_examples=50)
    def test_model_integration_workflow(self, entry, classification, validation):
        """测试模型间的集成工作流"""
        # 模拟完整的分类和验证流程
        
        # 1. 生物学条目应该能够提供分类文本
        classification_text = entry.get_text_for_classification()
        assert isinstance(classification_text, str)
        assert len(classification_text) > 0
        
        # 2. 分类结果应该能够转换为多种格式
        csv_row = classification.to_csv_row()
        json_str = classification.to_json()
        
        assert isinstance(csv_row, dict)
        assert isinstance(json_str, str)
        
        # 3. 验证结果应该能够生成报告
        summary_report = validation.generate_summary_report()
        assert isinstance(summary_report, str)
        assert validation.validation_type in summary_report
    
    @given(st.lists(classification_result_strategy(), min_size=1, max_size=10))
    @settings(max_examples=20)
    def test_batch_processing_consistency(self, results):
        """测试批量处理的一致性"""
        # 验证批量处理不会改变单个结果的属性
        for result in results:
            # 每个结果都应该有有效的系统分类
            assert result.primary_system is not None
            assert result.entry_id is not None
            
            # CSV输出应该包含所有必需字段
            csv_row = result.to_csv_row()
            required_fields = ['ID', 'Primary_System', 'All_Systems']
            for field in required_fields:
                assert field in csv_row


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])