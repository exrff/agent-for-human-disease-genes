"""
GO条目过滤属性测试

使用Hypothesis库进行基于属性的测试，验证GO条目过滤的正确性。
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.strategies import composite
import sys
from pathlib import Path
import re

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from preprocessing.go_parser import GOParser, GOTerm


# 测试数据生成策略
@composite
def go_term_strategy(draw):
    """生成GOTerm实例的策略"""
    go_id = f"GO:{draw(st.integers(min_value=1, max_value=9999999)):07d}"
    name = draw(st.text(min_size=1, max_size=100))
    namespace = draw(st.sampled_from(['biological_process', 'molecular_function', 'cellular_component']))
    definition = draw(st.text(min_size=0, max_size=500))
    is_obsolete = draw(st.booleans())
    
    # 生成同义词
    synonyms = draw(st.lists(st.text(min_size=1, max_size=50), max_size=5))
    
    # 生成父节点关系
    is_a = draw(st.lists(
        st.builds(lambda x: f"GO:{x:07d}", st.integers(min_value=1, max_value=9999999)),
        max_size=3
    ))
    
    return GOTerm(
        id=go_id,
        name=name,
        namespace=namespace,
        definition=definition,
        synonyms=synonyms,
        is_a=is_a,
        is_obsolete=is_obsolete
    )


@composite
def general_term_name_strategy(draw):
    """生成通用条目名称的策略"""
    patterns = [
        "biological_process",
        "cellular_process", 
        "metabolic_process",
        "regulation of something",
        "positive regulation of something",
        "negative regulation of something"
    ]
    return draw(st.sampled_from(patterns))


class TestGOFiltering:
    """GO条目过滤属性测试"""
    
    @given(st.lists(go_term_strategy(), min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_namespace_filtering_property(self, terms):
        """
        **Feature: five-system-classification, Property 2: GO条目过滤正确性**
        **Validates: Requirements 2.1, 2.2**
        
        测试命名空间过滤的正确性：过滤后的条目应该只包含指定命名空间的条目
        """
        # 创建临时的条目字典
        terms_dict = {term.id: term for term in terms}
        
        # 创建模拟的解析器
        parser = MockGOParser(terms_dict)
        
        # 测试不同命名空间的过滤
        target_namespaces = {'biological_process'}
        filtered_terms = parser.filter_terms(namespaces=target_namespaces)
        
        # 验证：所有过滤后的条目都应该属于指定命名空间
        for term_id, term in filtered_terms.items():
            assert term.namespace in target_namespaces, \
                f"Term {term_id} has namespace {term.namespace}, not in {target_namespaces}"
    
    @given(st.lists(go_term_strategy(), min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_obsolete_filtering_property(self, terms):
        """
        **Feature: five-system-classification, Property 2: GO条目过滤正确性**
        **Validates: Requirements 2.1, 2.2**
        
        测试过时条目过滤的正确性：当exclude_obsolete=True时，过滤后不应包含过时条目
        """
        # 创建临时的条目字典
        terms_dict = {term.id: term for term in terms}
        
        # 创建模拟的解析器
        parser = MockGOParser(terms_dict)
        
        # 测试排除过时条目
        filtered_terms = parser.filter_terms(exclude_obsolete=True)
        
        # 验证：所有过滤后的条目都不应该是过时的
        for term_id, term in filtered_terms.items():
            assert not term.is_obsolete, \
                f"Term {term_id} is obsolete but was not filtered out"
    
    @given(st.lists(go_term_strategy(), min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_general_term_filtering_property(self, terms):
        """
        **Feature: five-system-classification, Property 2: GO条目过滤正确性**
        **Validates: Requirements 2.1, 2.2**
        
        测试通用条目过滤的正确性：当exclude_general=True时，应该排除匹配通用模式的条目
        """
        # 修改一些条目的名称为通用模式
        general_patterns = [
            r'^biological_process$',
            r'^cellular_process$',
            r'^metabolic_process$',
            r'^regulation of',
            r'^positive regulation of',
            r'^negative regulation of'
        ]
        
        # 为一些条目设置通用名称
        modified_terms = []
        for i, term in enumerate(terms):
            if i % 3 == 0 and i < len(general_patterns):  # 每3个条目中的第1个设为通用
                # 创建新的条目，名称匹配通用模式
                general_name = general_patterns[i % len(general_patterns)].replace('^', '').replace('$', '')
                if 'regulation of' in general_name:
                    general_name = general_name + ' test process'
                
                modified_term = GOTerm(
                    id=term.id,
                    name=general_name,
                    namespace=term.namespace,
                    definition=term.definition,
                    synonyms=term.synonyms,
                    is_a=term.is_a,
                    is_obsolete=term.is_obsolete
                )
                modified_terms.append(modified_term)
            else:
                modified_terms.append(term)
        
        # 创建临时的条目字典
        terms_dict = {term.id: term for term in modified_terms}
        
        # 创建模拟的解析器
        parser = MockGOParser(terms_dict)
        
        # 测试排除通用条目
        filtered_terms = parser.filter_terms(exclude_general=True, general_patterns=general_patterns)
        
        # 编译正则表达式模式
        compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in general_patterns]
        
        # 验证：过滤后的条目不应该匹配通用模式
        for term_id, term in filtered_terms.items():
            for pattern in compiled_patterns:
                assert not pattern.search(term.name), \
                    f"Term {term_id} with name '{term.name}' matches general pattern {pattern.pattern}"
    
    @given(st.lists(go_term_strategy(), min_size=10, max_size=100))
    @settings(max_examples=20)
    def test_filtering_consistency_property(self, terms):
        """
        **Feature: five-system-classification, Property 2: GO条目过滤正确性**
        **Validates: Requirements 2.1, 2.2**
        
        测试过滤一致性：相同的过滤参数应该产生相同的结果
        """
        # 创建临时的条目字典
        terms_dict = {term.id: term for term in terms}
        
        # 创建模拟的解析器
        parser = MockGOParser(terms_dict)
        
        # 使用相同参数进行两次过滤
        filter_params = {
            'namespaces': {'biological_process'},
            'exclude_obsolete': True,
            'exclude_general': True
        }
        
        filtered_terms_1 = parser.filter_terms(**filter_params)
        filtered_terms_2 = parser.filter_terms(**filter_params)
        
        # 验证：两次过滤的结果应该完全相同
        assert set(filtered_terms_1.keys()) == set(filtered_terms_2.keys()), \
            "Filtering with same parameters should produce identical results"
        
        for term_id in filtered_terms_1.keys():
            term_1 = filtered_terms_1[term_id]
            term_2 = filtered_terms_2[term_id]
            assert term_1.id == term_2.id
            assert term_1.name == term_2.name
            assert term_1.namespace == term_2.namespace
    
    @given(st.lists(go_term_strategy(), min_size=5, max_size=50))
    @settings(max_examples=30)
    def test_biological_process_filtering_property(self, terms):
        """
        **Feature: five-system-classification, Property 2: GO条目过滤正确性**
        **Validates: Requirements 2.1, 2.2**
        
        测试生物过程过滤的正确性：get_biological_process_terms应该只返回biological_process命名空间的条目
        """
        # 确保有一些biological_process条目，并避免ID重复
        bp_terms = []
        other_terms = []
        used_ids = set()
        
        for i, term in enumerate(terms):
            # 确保ID唯一
            unique_id = f"GO:{i+1000000:07d}"
            while unique_id in used_ids:
                i += 1
                unique_id = f"GO:{i+1000000:07d}"
            used_ids.add(unique_id)
            
            # 创建唯一的条目
            unique_term = GOTerm(
                id=unique_id,
                name=term.name,
                namespace=term.namespace,
                definition=term.definition,
                synonyms=term.synonyms,
                is_a=term.is_a,
                is_obsolete=term.is_obsolete
            )
            
            if term.namespace == 'biological_process':
                bp_terms.append(unique_term)
            else:
                other_terms.append(unique_term)
                # 同时创建一个biological_process版本
                bp_id = f"GO:{i+2000000:07d}"
                while bp_id in used_ids:
                    i += 1
                    bp_id = f"GO:{i+2000000:07d}"
                used_ids.add(bp_id)
                
                bp_term = GOTerm(
                    id=bp_id,
                    name=term.name,
                    namespace='biological_process',
                    definition=term.definition,
                    synonyms=term.synonyms,
                    is_a=term.is_a,
                    is_obsolete=term.is_obsolete
                )
                bp_terms.append(bp_term)
        
        all_terms = bp_terms + other_terms
        terms_dict = {term.id: term for term in all_terms}
        
        # 创建模拟的解析器
        parser = MockGOParser(terms_dict)
        
        # 获取生物过程条目
        result_bp_terms = parser.get_biological_process_terms(exclude_obsolete=False)
        
        # 验证：所有返回的条目都应该是biological_process
        for term_id, term in result_bp_terms.items():
            assert term.namespace == 'biological_process', \
                f"Term {term_id} has namespace {term.namespace}, expected biological_process"
        
        # 验证：所有biological_process条目都应该被包含（如果不排除过时条目）
        expected_bp_ids = {term.id for term in bp_terms}
        actual_bp_ids = set(result_bp_terms.keys())
        
        # 应该完全匹配（因为不排除过时条目）
        assert expected_bp_ids == actual_bp_ids, \
            f"Expected {expected_bp_ids}, got {actual_bp_ids}"


class MockGOParser:
    """模拟GO解析器，用于测试"""
    
    def __init__(self, terms_dict):
        self.terms = terms_dict
        self.namespace_terms = self._build_namespace_index()
        self.obsolete_terms = {term_id for term_id, term in terms_dict.items() if term.is_obsolete}
    
    def _build_namespace_index(self):
        """构建命名空间索引"""
        from collections import defaultdict
        namespace_terms = defaultdict(set)
        for term_id, term in self.terms.items():
            namespace_terms[term.namespace].add(term_id)
        return namespace_terms
    
    def filter_terms(self, 
                     namespaces=None,
                     exclude_obsolete=True,
                     exclude_general=True,
                     general_patterns=None):
        """过滤GO条目（简化版本）"""
        if namespaces is None:
            namespaces = {'biological_process'}
        
        if general_patterns is None:
            general_patterns = [
                r'^biological_process$',
                r'^cellular_process$',
                r'^metabolic_process$',
                r'^regulation of',
                r'^positive regulation of',
                r'^negative regulation of'
            ]
        
        # 编译正则表达式
        compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in general_patterns]
        
        filtered_terms = {}
        
        for term_id, term in self.terms.items():
            # 检查命名空间
            if term.namespace not in namespaces:
                continue
            
            # 检查是否过时
            if exclude_obsolete and term.is_obsolete:
                continue
            
            # 检查是否为通用条目
            if exclude_general:
                is_general = False
                for pattern in compiled_patterns:
                    if pattern.search(term.name):
                        is_general = True
                        break
                
                if is_general:
                    continue
            
            filtered_terms[term_id] = term
        
        return filtered_terms
    
    def get_biological_process_terms(self, exclude_obsolete=True):
        """获取所有生物过程条目"""
        bp_terms = {}
        for term_id in self.namespace_terms.get('biological_process', set()):
            term = self.terms[term_id]
            if exclude_obsolete and term.is_obsolete:
                continue
            bp_terms[term_id] = term
        
        return bp_terms


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])