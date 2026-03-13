# 基线方法对比模块

本模块实现了五大功能系统分类方法与PCA基线方法的性能对比分析。

## 模块概述

### 核心功能

1. **PCA基线方法** (`pca_baseline.py`)
   - 使用scikit-learn实现PCA降维
   - 提取指定数量的主成分作为特征
   - 支持分类性能评估和统计显著性检验

2. **性能对比分析** (`performance_comparison.py`)
   - 在相同数据集上比较两种方法的分类性能
   - 计算准确率、F1分数、AUC等指标
   - 进行统计显著性检验和效应量分析

3. **可视化和报告** 
   - 生成对比分析图表
   - 输出详细的性能对比报告
   - 支持Markdown和JSON格式输出

## 主要类和方法

### PCABaseline类

```python
from src.comparison.pca_baseline import PCABaseline

# 创建PCA基线方法
pca_baseline = PCABaseline(n_components=5, random_state=42)

# PCA降维
pca_scores = pca_baseline.fit_transform(go_scores_df)

# 性能对比
report = pca_baseline.compare_performance(
    five_system_scores=system_scores_df,
    pca_scores=pca_scores,
    labels=labels,
    dataset_name="My Dataset"
)

# 生成可视化
pca_baseline.generate_comparison_visualization(report, "comparison.png")
```

### PerformanceComparator类

```python
from src.comparison.performance_comparison import PerformanceComparator

# 创建性能对比分析器
comparator = PerformanceComparator(output_dir="results/comparison")

# 数据集配置
datasets_config = {
    'dataset1': {
        'name': 'Dataset 1',
        'sample_info_path': 'data/dataset1_sample_info.csv',
        'system_scores_path': 'data/dataset1_system_scores.csv',
        'go_scores_path': 'data/dataset1_go_scores.csv'
    }
}

# 运行全面对比分析
results = comparator.run_comprehensive_comparison(datasets_config)
```

## 数据格式要求

### 输入数据格式

1. **样本信息文件** (`*_sample_info.csv`)
   ```csv
   sample_id,group
   sample_001,control
   sample_002,treatment
   ```

2. **五大系统分数文件** (`*_system_scores.csv`)
   ```csv
   sample_id,System_A,System_B,System_C,System_D,System_E
   sample_001,0.75,0.23,0.45,0.67,0.89
   sample_002,0.34,0.78,0.56,0.23,0.45
   ```

3. **GO分数文件** (`*_go_scores.csv`)
   ```csv
   sample_id,GO_0001,GO_0002,GO_0003,...
   sample_001,1.23,-0.45,0.67,...
   sample_002,-0.34,1.78,0.23,...
   ```

### 输出文件格式

1. **性能对比摘要** (`performance_comparison_summary.csv`)
   - 包含所有数据集的性能指标对比
   - 统计显著性检验结果
   - 效应量分析

2. **详细报告** (`performance_comparison_report.md`)
   - Markdown格式的完整对比报告
   - 包含数据集概览、性能对比、统计分析

3. **可视化图表** (`*.png`)
   - 各数据集的详细对比图
   - 摘要对比图表
   - 统计显著性热图

## 使用示例

### 基本使用

```python
import pandas as pd
import numpy as np
from src.comparison.pca_baseline import PCABaseline

# 加载数据
go_scores = pd.read_csv("go_scores.csv")
system_scores = pd.read_csv("system_scores.csv")
sample_info = pd.read_csv("sample_info.csv")

# 创建PCA基线方法
pca_baseline = PCABaseline(n_components=5)

# PCA降维
pca_scores = pca_baseline.fit_transform(go_scores)

# 性能对比
report = pca_baseline.compare_performance(
    five_system_scores=system_scores,
    pca_scores=pca_scores,
    labels=sample_info['group'].values,
    dataset_name="My Analysis"
)

print(f"五大系统 Accuracy: {report.five_system_metrics.accuracy_mean:.3f}")
print(f"PCA基线 Accuracy: {report.pca_metrics.accuracy_mean:.3f}")
```

### 批量对比分析

```python
from src.comparison.performance_comparison import PerformanceComparator

# 配置多个数据集
datasets = {
    'wound_healing': {
        'name': 'Wound Healing',
        'sample_info_path': 'data/wound_healing_sample_info.csv',
        'system_scores_path': 'data/wound_healing_system_scores.csv',
        'go_scores_path': 'data/wound_healing_go_scores.csv'
    },
    'sepsis': {
        'name': 'Sepsis',
        'sample_info_path': 'data/sepsis_sample_info.csv',
        'system_scores_path': 'data/sepsis_system_scores.csv',
        'go_scores_path': 'data/sepsis_go_scores.csv'
    }
}

# 运行批量对比
comparator = PerformanceComparator()
results = comparator.run_comprehensive_comparison(datasets)

print(f"处理了 {len(results['reports'])} 个数据集")
```

## 演示脚本

运行演示脚本查看完整的使用示例：

```bash
python src/comparison/demo_baseline_comparison.py
```

演示脚本包含：
1. 单个数据集的对比分析
2. 多数据集的全面对比
3. 不同PCA成分数的影响分析

## 性能指标说明

### 分类性能指标

- **Accuracy**: 分类准确率
- **Macro F1**: 宏平均F1分数
- **AUC**: 受试者工作特征曲线下面积（仅二分类）

### 统计检验

- **配对t检验**: 比较两种方法在相同数据集上的性能差异
- **Cohen's d**: 效应量，衡量差异的实际意义
  - 小效应: |d| ≈ 0.2
  - 中效应: |d| ≈ 0.5  
  - 大效应: |d| ≈ 0.8

### 显著性标记

- `***`: p < 0.001 (极显著)
- `**`: p < 0.01 (高度显著)
- `*`: p < 0.05 (显著)
- `ns`: p ≥ 0.05 (不显著)

## 技术细节

### PCA实现

- 使用scikit-learn的PCA类
- 数据预处理包括标准化
- 支持自定义主成分数量
- 记录解释方差比例

### 交叉验证

- 使用分层K折交叉验证
- 默认5折，根据最小类别样本数自动调整
- 确保每折中类别分布平衡

### 可视化

- 使用matplotlib和seaborn
- 支持多种图表类型：条形图、热图、雷达图
- 高分辨率输出，适合论文发表

## 依赖包

```
pandas>=1.3.0
numpy>=1.21.0
scikit-learn>=1.0.0
matplotlib>=3.5.0
seaborn>=0.11.0
scipy>=1.7.0
```

## 注意事项

1. **数据质量**: 确保输入数据无缺失值或已适当处理
2. **样本数量**: 建议每个类别至少有10个样本用于交叉验证
3. **特征数量**: GO条目数量应大于PCA成分数
4. **内存使用**: 大规模数据集可能需要较多内存
5. **随机性**: 设置random_state确保结果可重现

## 故障排除

### 常见错误

1. **ImportError**: 检查依赖包是否正确安装
2. **FileNotFoundError**: 确认数据文件路径正确
3. **ValueError**: 检查数据格式和列名是否符合要求
4. **MemoryError**: 减少数据规模或增加系统内存

### 性能优化

1. 使用较少的PCA成分数减少计算量
2. 对大数据集进行采样
3. 使用并行计算（如果支持）
4. 优化数据加载和预处理流程

## 更新日志

- v1.0.0: 初始版本，实现基本的PCA基线对比功能
- 支持多数据集批量分析
- 集成统计显著性检验
- 完善的可视化和报告生成