"""
数据解析一致性属性测试

使用Hypothesis库进行基于属性的测试，验证数据解析的一致性。
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.strategies import composite
import sys
from pathlib import Path
import tempfile
import os

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from preprocessing.go_parser import GOParser, GOTerm
from preprocessing.kegg_parser import KEGGParser, KEGGPathway


# 测试数据生成策略
@composite
def go_obo_content_strategy(draw):
    """生成GO OBO文件内容的策略"""
    # 生成文件头
    header = """format-version: 1.2
data-version: releases/2024-01-01
default-namespace: gene_ontology
ontology: go

"""
    
    # 生成条目
    terms = []
    num_terms = draw(st.integers(min_value=1, max_value=10))
    
    for i in range(num_terms):
        term_id = f"GO:{i+1000000:07d}"
        name = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Zs'))))
        namespace = draw(st.sampled_from(['biological_process', 'molecular_function', 'cellular_component']))
        definition = draw(st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Zs'))))
        is_obsolete = draw(st.booleans())
        
        term_content = f"""[Term]
id: {term_id}
name: {name}
namespace: {namespace}
def: "{definition}" [GOC:test]
"""
        if is_obsolete:
            term_content += "is_obsolete: true\n"
        
        terms.append(term_content)
    
    return header + "\n".join(terms)


@composite
def kegg_hierarchy_content_strategy(draw):
    """生成KEGG层次文件内容的策略"""
    # 生成文件头
    header = """+C	Map number
!
"""
    
    # 生成Class A
    class_a_names = ['Metabolism', 'Genetic Information Processing', 'Environmental Information Processing']
    class_a = draw(st.sampled_from(class_a_names))
    
    content = header + f"A{class_a}\n"
    
    # 生成Class B
    class_b_name = draw(st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Zs'))))
    content += f"B  {class_b_name}\n"
    
    # 生成通路
    num_pathways = draw(st.integers(min_value=1, max_value=5))
    for i in range(num_pathways):
        pathway_id = f"{i+1000:04d}"
        pathway_name = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Zs'))))
        content += f"C    {pathway_id}  {pathway_name}\n"
    
    return content


class TestParsingConsistency:
    """数据解析一致性属性测试"""
    
    @given(go_obo_content_strategy())
    @settings(max_examples=20)
    def test_go_parsing_consistency_property(self, obo_content):
        """
        **Feature: five-system-classification, Property 3: 分类一致性**
        **Validates: Requirements 2.3**
        
        测试GO解析的一致性：相同的输入应该产生相同的输出
        """
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.obo', delete=False, encoding='utf-8') as f:
            f.write(obo_content)
            temp_file = f.name
        
        try:
            # 第一次解析
            parser1 = GOParser(temp_file)
            terms1 = parser1.parse_go_terms()
            
            # 第二次解析
            parser2 = GOParser(temp_file)
            terms2 = parser2.parse_go_terms()
            
            # 验证：两次解析的结果应该完全相同
            assert len(terms1) == len(terms2), "Two parsing results should have same number of terms"
            assert set(terms1.keys()) == set(terms2.keys()), "Two parsing results should have same term IDs"
            
            for term_id in terms1.keys():
                term1 = terms1[term_id]
                term2 = terms2[term_id]
                
                assert term1.id == term2.id, f"Term ID mismatch for {term_id}"
                assert term1.name == term2.name, f"Term name mismatch for {term_id}"
                assert term1.namespace == term2.namespace, f"Term namespace mismatch for {term_id}"
                assert term1.definition == term2.definition, f"Term definition mismatch for {term_id}"
                assert term1.is_obsolete == term2.is_obsolete, f"Term obsolete status mismatch for {term_id}"
        
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    @given(kegg_hierarchy_content_strategy())
    @settings(max_examples=20)
    def test_kegg_parsing_consistency_property(self, hierarchy_content):
        """
        **Feature: five-system-classification, Property 3: 分类一致性**
        **Validates: Requirements 2.3**
        
        测试KEGG解析的一致性：相同的输入应该产生相同的输出
        """
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(hierarchy_content)
            temp_file = f.name
        
        try:
            # 第一次解析
            parser1 = KEGGParser(temp_file)
            pathways1 = parser1.parse_pathways()
            
            # 第二次解析
            parser2 = KEGGParser(temp_file)
            pathways2 = parser2.parse_pathways()
            
            # 验证：两次解析的结果应该完全相同
            assert len(pathways1) == len(pathways2), "Two parsing results should have same number of pathways"
            
            # 转换为字典以便比较
            pathways1_dict = {p.id: p for p in pathways1}
            pathways2_dict = {p.id: p for p in pathways2}
            
            assert set(pathways1_dict.keys()) == set(pathways2_dict.keys()), "Two parsing results should have same pathway IDs"
            
            for pathway_id in pathways1_dict.keys():
                pathway1 = pathways1_dict[pathway_id]
                pathway2 = pathways2_dict[pathway_id]
                
                assert pathway1.id == pathway2.id, f"Pathway ID mismatch for {pathway_id}"
                assert pathway1.name == pathway2.name, f"Pathway name mismatch for {pathway_id}"
                assert pathway1.class_a == pathway2.class_a, f"Pathway class_a mismatch for {pathway_id}"
                assert pathway1.class_b == pathway2.class_b, f"Pathway class_b mismatch for {pathway_id}"
        
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    @given(go_obo_content_strategy())
    @settings(max_examples=15)
    def test_go_statistics_consistency_property(self, obo_content):
        """
        **Feature: five-system-classification, Property 3: 分类一致性**
        **Validates: Requirements 2.3**
        
        测试GO统计信息的一致性：多次计算应该产生相同的统计结果
        """
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.obo', delete=False, encoding='utf-8') as f:
            f.write(obo_content)
            temp_file = f.name
        
        try:
            parser = GOParser(temp_file)
            parser.parse_go_terms()
            
            # 多次获取统计信息
            stats1 = parser.get_statistics()
            stats2 = parser.get_statistics()
            stats3 = parser.get_statistics()
            
            # 验证：统计信息应该完全一致
            assert stats1['total_terms'] == stats2['total_terms'] == stats3['total_terms']
            assert stats1['obsolete_terms'] == stats2['obsolete_terms'] == stats3['obsolete_terms']
            assert stats1['namespaces'] == stats2['namespaces'] == stats3['namespaces']
        
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    @given(kegg_hierarchy_content_strategy())
    @settings(max_examples=15)
    def test_kegg_hierarchy_mapping_consistency_property(self, hierarchy_content):
        """
        **Feature: five-system-classification, Property 3: 分类一致性**
        **Validates: Requirements 2.3**
        
        测试KEGG层次映射的一致性：多次提取应该产生相同的映射结果
        """
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(hierarchy_content)
            temp_file = f.name
        
        try:
            parser = KEGGParser(temp_file)
            
            # 多次提取层次映射
            hierarchy1 = parser.extract_hierarchy()
            hierarchy2 = parser.extract_hierarchy()
            hierarchy3 = parser.extract_hierarchy()
            
            # 验证：层次映射应该完全一致
            assert hierarchy1 == hierarchy2 == hierarchy3
            assert len(hierarchy1) == len(hierarchy2) == len(hierarchy3)
            
            for pathway_id in hierarchy1.keys():
                assert hierarchy1[pathway_id] == hierarchy2[pathway_id] == hierarchy3[pathway_id]
        
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    @given(go_obo_content_strategy())
    @settings(max_examples=10)
    def test_go_filtering_determinism_property(self, obo_content):
        """
        **Feature: five-system-classification, Property 3: 分类一致性**
        **Validates: Requirements 2.3**
        
        测试GO过滤的确定性：相同的过滤参数应该产生相同的结果
        """
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.obo', delete=False, encoding='utf-8') as f:
            f.write(obo_content)
            temp_file = f.name
        
        try:
            parser = GOParser(temp_file)
            parser.parse_go_terms()
            
            # 使用相同参数进行多次过滤
            filter_params = {
                'namespaces': {'biological_process'},
                'exclude_obsolete': True,
                'exclude_general': False
            }
            
            filtered1 = parser.filter_terms(**filter_params)
            filtered2 = parser.filter_terms(**filter_params)
            filtered3 = parser.filter_terms(**filter_params)
            
            # 验证：过滤结果应该完全一致
            assert len(filtered1) == len(filtered2) == len(filtered3)
            assert set(filtered1.keys()) == set(filtered2.keys()) == set(filtered3.keys())
            
            for term_id in filtered1.keys():
                assert filtered1[term_id].id == filtered2[term_id].id == filtered3[term_id].id
                assert filtered1[term_id].name == filtered2[term_id].name == filtered3[term_id].name
        
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    @given(kegg_hierarchy_content_strategy())
    @settings(max_examples=10)
    def test_kegg_search_determinism_property(self, hierarchy_content):
        """
        **Feature: five-system-classification, Property 3: 分类一致性**
        **Validates: Requirements 2.3**
        
        测试KEGG搜索的确定性：相同的搜索查询应该产生相同的结果
        """
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(hierarchy_content)
            temp_file = f.name
        
        try:
            parser = KEGGParser(temp_file)
            parser.parse_pathways()
            
            # 使用相同查询进行多次搜索
            search_query = "metabolism"
            
            results1 = parser.search_pathways(search_query)
            results2 = parser.search_pathways(search_query)
            results3 = parser.search_pathways(search_query)
            
            # 验证：搜索结果应该完全一致
            assert len(results1) == len(results2) == len(results3)
            
            # 转换为ID集合进行比较
            ids1 = {p.id for p in results1}
            ids2 = {p.id for p in results2}
            ids3 = {p.id for p in results3}
            
            assert ids1 == ids2 == ids3
        
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])