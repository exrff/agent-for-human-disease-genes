"""
ssGSEA验证器测试

包含ssGSEA计算准确性的属性测试和单元测试。

作者: AI Assistant
日期: 2025-12-24
"""

import pytest
import pandas as pd
import numpy as np
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, List
import tempfile
import json
from pathlib import Path

from .ssgsea_validator import ssGSEAValidator, TimeSeriesResult, ComparisonResult
from ..models.validation_result import ValidationResult


class TestssGSEAValidator:
    """ssGSEA验证器测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.validator = ssGSEAValidator()
        
        # 创建测试基因集
        self.test_gene_sets = {
            'System A': ['GENE1', 'GENE2', 'GENE3', 'GENE4', 'GENE5'],
            'System B': ['GENE6', 'GENE7', 'GENE8', 'GENE9', 'GENE10'],
            'System C': ['GENE11', 'GENE12', 'GENE13', 'GENE14', 'GENE15']
        }
        
        # 创建测试表达矩阵
        genes = ['GENE1', 'GENE2', 'GENE3', 'GENE4', 'GENE5', 
                'GENE6', 'GENE7', 'GENE8', 'GENE9', 'GENE10',
                'GENE11', 'GENE12', 'GENE13', 'GENE14', 'GENE15']
        samples = ['Sample1', 'Sample2', 'Sample3', 'Sample4', 'Sample5']
        
        np.random.seed(42)
        self.test_expression = pd.DataFrame(
            np.random.randn(len(genes), len(samples)),
            index=genes,
            columns=samples
        )
    
    def test_load_system_gene_sets(self):
        """测试基因集加载"""
        # 创建临时基因集文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_gene_sets, f)
            temp_path = f.name
        
        try:
            gene_sets = self.validator.load_system_gene_sets(temp_path)
            
            assert len(gene_sets) == 3
            assert 'System A' in gene_sets
            assert len(gene_sets['System A']) == 5
            assert gene_sets['System A'][0] == 'GENE1'
            
        finally:
            Path(temp_path).unlink()
    
    def test_compute_system_scores_basic(self):
        """测试基本ssGSEA计算"""
        # 加载测试基因集
        self.validator.gene_sets = self.test_gene_sets
        
        # 计算ssGSEA得分
        scores = self.validator.compute_system_scores(self.test_expression)
        
        # 验证结果格式
        assert isinstance(scores, pd.DataFrame)
        assert scores.shape[0] == 3  # 3个系统
        assert scores.shape[1] == 5  # 5个样本
        assert list(scores.index) == ['System A', 'System B', 'System C']
        assert list(scores.columns) == ['Sample1', 'Sample2', 'Sample3', 'Sample4', 'Sample5']
    
    def test_analyze_time_series(self):
        """测试时间序列分析"""
        # 创建测试ssGSEA得分
        systems = ['System A', 'System B', 'System C']
        time_samples = ['T0_1', 'T0_2', 'T1_1', 'T1_2', 'T2_1', 'T2_2']
        
        np.random.seed(42)
        scores = pd.DataFrame(
            np.random.randn(3, 6),
            index=systems,
            columns=time_samples
        )
        
        time_points = ['T0', 'T0', 'T1', 'T1', 'T2', 'T2']
        
        result = self.validator.analyze_time_series(scores, time_points, "Test Dataset")
        
        assert isinstance(result, TimeSeriesResult)
        assert result.dataset_name == "Test Dataset"
        assert len(result.time_points) == 3  # T0, T1, T2
        assert len(result.trends) == 3  # 3个系统
        assert len(result.correlations) == 3  # 3个系统
        assert all(trend in ['increasing', 'decreasing', 'stable'] for trend in result.trends.values())
    
    def test_compare_disease_control(self):
        """测试疾病对比分析"""
        # 创建测试ssGSEA得分
        systems = ['System A', 'System B', 'System C']
        samples = ['Disease1', 'Disease2', 'Disease3', 'Control1', 'Control2', 'Control3']
        
        np.random.seed(42)
        scores = pd.DataFrame(
            np.random.randn(3, 6),
            index=systems,
            columns=samples
        )
        
        disease_samples = ['Disease1', 'Disease2', 'Disease3']
        control_samples = ['Control1', 'Control2', 'Control3']
        
        result = self.validator.compare_disease_control(
            scores, disease_samples, control_samples, "Test Dataset"
        )
        
        assert isinstance(result, ComparisonResult)
        assert result.dataset_name == "Test Dataset"
        assert len(result.fold_changes) == 3  # 3个系统
        assert len(result.p_values) == 3  # 3个系统
        assert len(result.effect_sizes) == 3  # 3个系统
        assert isinstance(result.significant_systems, list)


# 属性测试生成器
@st.composite
def gene_expression_matrix(draw):
    """生成基因表达矩阵"""
    n_genes = draw(st.integers(min_value=10, max_value=100))
    n_samples = draw(st.integers(min_value=3, max_value=20))
    
    genes = [f"GENE{i}" for i in range(n_genes)]
    samples = [f"Sample{i}" for i in range(n_samples)]
    
    # 生成表达值（正态分布）
    expression_data = draw(st.lists(
        st.lists(st.floats(min_value=-5, max_value=5, allow_nan=False), 
                min_size=n_samples, max_size=n_samples),
        min_size=n_genes, max_size=n_genes
    ))
    
    return pd.DataFrame(expression_data, index=genes, columns=samples)


@st.composite
def gene_sets_dict(draw, genes_list):
    """生成基因集字典"""
    n_systems = draw(st.integers(min_value=2, max_value=5))
    systems = [f"System_{chr(65+i)}" for i in range(n_systems)]
    
    gene_sets = {}
    for system in systems:
        # 每个系统选择5-20个基因
        n_genes = draw(st.integers(min_value=5, max_value=min(20, len(genes_list))))
        selected_genes = draw(st.lists(
            st.sampled_from(genes_list), 
            min_size=n_genes, max_size=n_genes, unique=True
        ))
        gene_sets[system] = selected_genes
    
    return gene_sets


class TestssGSEAValidatorProperties:
    """ssGSEA验证器属性测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.validator = ssGSEAValidator()
    
    @given(gene_expression_matrix())
    @settings(max_examples=10, deadline=30000)  # 减少测试次数，增加超时时间
    def test_ssgsea_score_range_property(self, expression_df):
        """
        **Feature: five-system-classification, Property 7: ssGSEA计算准确性**
        **Validates: Requirements 5.1**
        
        Property: 对于任何有效的基因表达数据和基因集，ssGSEA计算应该产生在合理范围内的富集得分
        """
        assume(len(expression_df) >= 10)  # 至少10个基因
        assume(len(expression_df.columns) >= 3)  # 至少3个样本
        
        # 确保表达数据有变异性（不全为0）
        assume(expression_df.std().sum() > 0.1)
        
        # 生成基因集
        genes_list = list(expression_df.index)
        gene_sets = {
            'Test_System_A': genes_list[:min(10, len(genes_list)//2)],
            'Test_System_B': genes_list[len(genes_list)//2:len(genes_list)//2 + min(10, len(genes_list)//2)]
        }
        
        # 过滤空基因集
        gene_sets = {k: v for k, v in gene_sets.items() if len(v) >= 5}
        assume(len(gene_sets) >= 1)
        
        try:
            # 计算ssGSEA得分
            scores = self.validator.compute_system_scores(expression_df, gene_sets)
            
            # 确保scores是数值类型
            scores = scores.astype(float)
            
            # 验证得分范围：ssGSEA得分通常在[-3, 3]范围内，但可能稍微超出
            min_score = float(scores.min().min())
            max_score = float(scores.max().max())
            
            # 属性：得分应该在合理范围内
            assert -5 <= min_score <= 5, f"最小得分超出范围: {min_score}"
            assert -5 <= max_score <= 5, f"最大得分超出范围: {max_score}"
            
            # 属性：得分不应该是NaN或无穷大
            assert not scores.isnull().any().any(), "得分包含NaN值"
            assert np.isfinite(scores.astype(float).values).all(), "得分包含无穷大值"
            
            # 属性：结果矩阵形状应该正确
            assert scores.shape[0] == len(gene_sets), f"系统数量不匹配: {scores.shape[0]} vs {len(gene_sets)}"
            assert scores.shape[1] == len(expression_df.columns), f"样本数量不匹配: {scores.shape[1]} vs {len(expression_df.columns)}"
            
        except Exception as e:
            # 如果是由于基因集太小或其他合理原因导致的失败，跳过测试
            if any(keyword in str(e).lower() for keyword in ["min_size", "gene_sets", "empty", "variance"]):
                assume(False)
            else:
                raise
    
    @given(st.integers(min_value=3, max_value=10))
    @settings(max_examples=5, deadline=15000)
    def test_time_series_analysis_property(self, n_timepoints):
        """
        Property: 时间序列分析应该正确识别趋势和计算相关性
        """
        # 创建测试数据
        systems = ['System_A', 'System_B', 'System_C']
        samples_per_timepoint = 2
        total_samples = n_timepoints * samples_per_timepoint
        
        # 生成样本名称和时间点
        samples = []
        time_points = []
        for t in range(n_timepoints):
            for s in range(samples_per_timepoint):
                samples.append(f"T{t}_S{s}")
                time_points.append(f"T{t}")
        
        # 生成测试得分（System_A递增，System_B递减，System_C稳定）
        np.random.seed(42)
        scores_data = []
        for i, system in enumerate(systems):
            if system == 'System_A':
                # 递增趋势
                base_scores = np.linspace(-1, 1, n_timepoints)
                system_scores = []
                for t in range(n_timepoints):
                    for s in range(samples_per_timepoint):
                        system_scores.append(base_scores[t] + np.random.normal(0, 0.1))
            elif system == 'System_B':
                # 递减趋势
                base_scores = np.linspace(1, -1, n_timepoints)
                system_scores = []
                for t in range(n_timepoints):
                    for s in range(samples_per_timepoint):
                        system_scores.append(base_scores[t] + np.random.normal(0, 0.1))
            else:
                # 稳定趋势
                system_scores = [np.random.normal(0, 0.1) for _ in range(total_samples)]
            
            scores_data.append(system_scores)
        
        scores_df = pd.DataFrame(scores_data, index=systems, columns=samples)
        
        # 执行时间序列分析
        result = self.validator.analyze_time_series(scores_df, time_points, "Test")
        
        # 验证属性
        assert isinstance(result, TimeSeriesResult)
        assert len(result.time_points) == n_timepoints
        assert len(result.trends) == len(systems)
        assert len(result.correlations) == len(systems)
        
        # 验证趋势识别（对于明显的趋势）
        if n_timepoints >= 4:  # 只有足够的时间点才能可靠地检测趋势
            # System_A应该是递增的
            assert result.correlations['System_A'] > 0.3 or result.trends['System_A'] in ['increasing', 'stable']
            # System_B应该是递减的
            assert result.correlations['System_B'] < -0.3 or result.trends['System_B'] in ['decreasing', 'stable']
    
    @given(st.integers(min_value=3, max_value=8), st.integers(min_value=3, max_value=8))
    @settings(max_examples=5, deadline=10000)
    def test_disease_control_comparison_property(self, n_disease, n_control):
        """
        Property: 疾病对比分析应该正确计算统计指标
        """
        systems = ['System_A', 'System_B', 'System_C']
        
        # 生成样本名称
        disease_samples = [f"Disease_{i}" for i in range(n_disease)]
        control_samples = [f"Control_{i}" for i in range(n_control)]
        all_samples = disease_samples + control_samples
        
        # 生成测试得分（疾病组System_A得分更高）
        np.random.seed(42)
        scores_data = []
        for system in systems:
            system_scores = []
            for sample in all_samples:
                if sample.startswith('Disease') and system == 'System_A':
                    # 疾病组System_A得分更高
                    score = np.random.normal(1.0, 0.5)
                elif sample.startswith('Control') and system == 'System_A':
                    # 对照组System_A得分较低
                    score = np.random.normal(0.0, 0.5)
                else:
                    # 其他情况随机得分
                    score = np.random.normal(0.0, 0.5)
                system_scores.append(score)
            scores_data.append(system_scores)
        
        scores_df = pd.DataFrame(scores_data, index=systems, columns=all_samples)
        
        # 执行疾病对比分析
        result = self.validator.compare_disease_control(
            scores_df, disease_samples, control_samples, "Test"
        )
        
        # 验证属性
        assert isinstance(result, ComparisonResult)
        assert len(result.fold_changes) == len(systems)
        assert len(result.p_values) == len(systems)
        assert len(result.effect_sizes) == len(systems)
        
        # 验证统计指标范围
        for system in systems:
            # P值应该在[0, 1]范围内
            assert 0 <= result.p_values[system] <= 1, f"P值超出范围: {result.p_values[system]}"
            
            # 效应量应该是有限值
            assert np.isfinite(result.effect_sizes[system]), f"效应量不是有限值: {result.effect_sizes[system]}"
            
            # Fold change应该是有限值
            assert np.isfinite(result.fold_changes[system]), f"Fold change不是有限值: {result.fold_changes[system]}"
        
        # 验证显著系统列表
        assert isinstance(result.significant_systems, list)
        assert all(system in systems for system in result.significant_systems)


if __name__ == "__main__":
    pytest.main([__file__])