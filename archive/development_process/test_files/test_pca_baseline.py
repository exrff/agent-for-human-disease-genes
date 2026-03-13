"""
PCA基线方法测试

测试PCA基线方法的核心功能。

作者: AI Assistant
日期: 2025-12-24
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import shutil

from .pca_baseline import PCABaseline, PerformanceMetrics, ComparisonReport


class TestPCABaseline:
    """PCA基线方法测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.pca_baseline = PCABaseline(n_components=3, random_state=42)
        
        # 创建测试数据
        np.random.seed(42)
        n_samples = 100
        n_go_terms = 50
        
        # GO分数矩阵
        self.go_scores = pd.DataFrame(
            np.random.randn(n_samples, n_go_terms),
            columns=[f'GO_{i:04d}' for i in range(n_go_terms)]
        )
        self.go_scores['sample_id'] = [f'sample_{i}' for i in range(n_samples)]
        
        # 五大系统分数
        self.system_scores = pd.DataFrame({
            'sample_id': [f'sample_{i}' for i in range(n_samples)],
            'System_A': np.random.uniform(0, 1, n_samples),
            'System_B': np.random.uniform(0, 1, n_samples),
            'System_C': np.random.uniform(0, 1, n_samples),
            'System_D': np.random.uniform(0, 1, n_samples),
            'System_E': np.random.uniform(0, 1, n_samples)
        })
        
        # 标签（二分类）
        self.labels = np.random.choice(['control', 'disease'], n_samples)
    
    def test_fit_transform(self):
        """测试PCA拟合和转换"""
        # 执行PCA降维
        pca_scores = self.pca_baseline.fit_transform(self.go_scores)
        
        # 验证结果
        assert isinstance(pca_scores, pd.DataFrame)
        assert pca_scores.shape[0] == self.go_scores.shape[0]  # 样本数不变
        assert pca_scores.shape[1] == 4  # 3个PC + sample_id
        assert 'sample_id' in pca_scores.columns
        assert all(col in pca_scores.columns for col in ['PC1', 'PC2', 'PC3'])
        
        # 验证PCA已拟合
        assert self.pca_baseline.is_fitted
        assert self.pca_baseline.pca is not None
        assert self.pca_baseline.scaler is not None
    
    def test_transform(self):
        """测试使用已拟合模型转换新数据"""
        # 先拟合
        self.pca_baseline.fit_transform(self.go_scores)
        
        # 创建新数据
        new_go_scores = self.go_scores.iloc[:10].copy()
        
        # 转换新数据
        new_pca_scores = self.pca_baseline.transform(new_go_scores)
        
        # 验证结果
        assert isinstance(new_pca_scores, pd.DataFrame)
        assert new_pca_scores.shape[0] == 10
        assert new_pca_scores.shape[1] == 4
        assert 'sample_id' in new_pca_scores.columns
    
    def test_transform_without_fit(self):
        """测试未拟合时转换数据应该报错"""
        with pytest.raises(ValueError, match="PCA模型尚未拟合"):
            self.pca_baseline.transform(self.go_scores)
    
    def test_compare_performance(self):
        """测试性能对比功能"""
        # 先进行PCA降维
        pca_scores = self.pca_baseline.fit_transform(self.go_scores)
        
        # 执行性能对比
        report = self.pca_baseline.compare_performance(
            five_system_scores=self.system_scores,
            pca_scores=pca_scores,
            labels=self.labels,
            dataset_name="Test Dataset"
        )
        
        # 验证报告结构
        assert isinstance(report, ComparisonReport)
        assert report.dataset_name == "Test Dataset"
        assert report.n_samples == len(self.labels)
        assert report.n_classes == 2  # 二分类
        
        # 验证性能指标
        assert isinstance(report.five_system_metrics, PerformanceMetrics)
        assert isinstance(report.pca_metrics, PerformanceMetrics)
        
        # 验证指标范围
        assert 0 <= report.five_system_metrics.accuracy_mean <= 1
        assert 0 <= report.five_system_metrics.f1_macro_mean <= 1
        assert 0 <= report.pca_metrics.accuracy_mean <= 1
        assert 0 <= report.pca_metrics.f1_macro_mean <= 1
        
        # 验证AUC（二分类应该有AUC）
        assert report.five_system_metrics.auc_mean is not None
        assert report.pca_metrics.auc_mean is not None
        assert 0 <= report.five_system_metrics.auc_mean <= 1
        assert 0 <= report.pca_metrics.auc_mean <= 1
        
        # 验证统计检验
        assert 'accuracy' in report.statistical_tests
        assert 'f1_macro' in report.statistical_tests
        assert 'p_value' in report.statistical_tests['accuracy']
        assert 'effect_size' in report.statistical_tests['accuracy']
    
    def test_generate_visualization(self):
        """测试可视化生成"""
        # 先进行PCA降维和性能对比
        pca_scores = self.pca_baseline.fit_transform(self.go_scores)
        report = self.pca_baseline.compare_performance(
            five_system_scores=self.system_scores,
            pca_scores=pca_scores,
            labels=self.labels,
            dataset_name="Test Dataset"
        )
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_comparison.png"
            
            # 生成可视化（不应该报错）
            self.pca_baseline.generate_comparison_visualization(report, output_path)
            
            # 验证文件已生成
            assert output_path.exists()
            assert output_path.stat().st_size > 0
    
    def test_performance_metrics_to_dict(self):
        """测试性能指标转换为字典"""
        metrics = PerformanceMetrics(
            accuracy_mean=0.85,
            accuracy_std=0.05,
            f1_macro_mean=0.80,
            f1_macro_std=0.06,
            auc_mean=0.90,
            auc_std=0.04
        )
        
        result_dict = metrics.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['accuracy_mean'] == 0.85
        assert result_dict['accuracy_std'] == 0.05
        assert result_dict['f1_macro_mean'] == 0.80
        assert result_dict['f1_macro_std'] == 0.06
        assert result_dict['auc_mean'] == 0.90
        assert result_dict['auc_std'] == 0.04
    
    def test_comparison_report_to_dict(self):
        """测试对比报告转换为字典"""
        # 创建测试报告
        five_system_metrics = PerformanceMetrics(0.85, 0.05, 0.80, 0.06, 0.90, 0.04)
        pca_metrics = PerformanceMetrics(0.75, 0.08, 0.70, 0.09, 0.80, 0.07)
        
        report = ComparisonReport(
            dataset_name="Test",
            five_system_metrics=five_system_metrics,
            pca_metrics=pca_metrics,
            statistical_tests={
                'accuracy': {'p_value': 0.05, 'effect_size': 0.5},
                'f1_macro': {'p_value': 0.03, 'effect_size': 0.7}
            },
            n_samples=100,
            n_classes=2,
            pca_explained_variance=0.75
        )
        
        result_dict = report.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['dataset_name'] == "Test"
        assert result_dict['n_samples'] == 100
        assert result_dict['n_classes'] == 2
        assert result_dict['pca_explained_variance'] == 0.75
        assert 'five_system_metrics' in result_dict
        assert 'pca_metrics' in result_dict
        assert 'statistical_tests' in result_dict


def test_pca_baseline_integration():
    """集成测试：完整的PCA基线方法流程"""
    # 创建更真实的测试数据
    np.random.seed(42)
    n_samples = 200
    n_go_terms = 100
    
    # 创建有一定结构的GO分数数据
    # 模拟两个组别有不同的表达模式
    group1_size = n_samples // 2
    group2_size = n_samples - group1_size
    
    # 组1：前50个GO terms高表达
    group1_data = np.random.normal(1, 0.5, (group1_size, n_go_terms))
    group1_data[:, :50] += 2  # 前50个GO terms额外增强
    
    # 组2：后50个GO terms高表达
    group2_data = np.random.normal(1, 0.5, (group2_size, n_go_terms))
    group2_data[:, 50:] += 2  # 后50个GO terms额外增强
    
    # 合并数据
    go_data = np.vstack([group1_data, group2_data])
    go_scores = pd.DataFrame(
        go_data,
        columns=[f'GO_{i:04d}' for i in range(n_go_terms)]
    )
    go_scores['sample_id'] = [f'sample_{i}' for i in range(n_samples)]
    
    # 创建对应的五大系统分数（基于GO分数的简单聚合）
    system_scores = pd.DataFrame({
        'sample_id': go_scores['sample_id'],
        'System_A': go_scores.iloc[:, :20].mean(axis=1),  # 前20个GO terms
        'System_B': go_scores.iloc[:, 20:40].mean(axis=1),  # 20-40
        'System_C': go_scores.iloc[:, 40:60].mean(axis=1),  # 40-60
        'System_D': go_scores.iloc[:, 60:80].mean(axis=1),  # 60-80
        'System_E': go_scores.iloc[:, 80:100].mean(axis=1)  # 80-100
    })
    
    # 标签
    labels = ['group1'] * group1_size + ['group2'] * group2_size
    
    # 执行完整流程
    pca_baseline = PCABaseline(n_components=5, random_state=42)
    
    # PCA降维
    pca_scores = pca_baseline.fit_transform(go_scores)
    
    # 性能对比
    report = pca_baseline.compare_performance(
        five_system_scores=system_scores,
        pca_scores=pca_scores,
        labels=labels,
        dataset_name="Integration Test"
    )
    
    # 验证结果合理性
    assert report.dataset_name == "Integration Test"
    assert report.n_samples == n_samples
    assert report.n_classes == 2
    assert 0.5 <= report.pca_explained_variance <= 1.0  # PCA应该能解释相当比例的方差
    
    # 由于数据有结构，分类性能应该不会太差
    assert report.five_system_metrics.accuracy_mean > 0.5
    assert report.pca_metrics.accuracy_mean > 0.5
    
    print(f"集成测试完成:")
    print(f"  五大系统 Accuracy: {report.five_system_metrics.accuracy_mean:.3f}")
    print(f"  PCA基线 Accuracy: {report.pca_metrics.accuracy_mean:.3f}")
    print(f"  PCA解释方差: {report.pca_explained_variance:.3f}")


if __name__ == "__main__":
    # 运行集成测试
    test_pca_baseline_integration()
    print("所有测试通过！")