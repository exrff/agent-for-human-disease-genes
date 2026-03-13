# Archive - 开发过程文件

本文件夹包含项目开发过程中的所有中间文件、测试文件和历史版本。

## 文件夹结构

### `development_process/`
包含开发过程中的各种文件：

- **测试文件** (`test_files/`): 所有单元测试、集成测试和演示文件
- **中间结果** (`intermediate_results/`): 开发过程中生成的临时结果和报告
- **历史版本**: 分类器的早期版本 (v7, v8等)
- **工具脚本**: 数据分析和处理的辅助脚本

### 主要归档内容

#### 测试文件
- `test_*.py` - 所有单元测试文件
- `demo_*.py` - 演示和调试脚本
- `debug_*.py` - 调试工具

#### 历史版本
- `v7_classification.py` - 第7版分类器
- `v8_classification.py` - 第8版分类器
- `v8_probabilistic_classification.py` - 概率版本分类器

#### 中间结果
- `demo_clustering_quality/` - 聚类质量评估结果
- `data_quality_demo/` - 数据质量检查结果
- `demo_reports/` - 开发过程报告
- `pca_analysis/` - PCA分析结果
- `ssgsea_results/` - ssGSEA分析结果
- `validation_tests/` - 验证测试结果

#### 开发工具
- `analyze_timeseries.py` - 时间序列分析工具
- `compute_ssgsea.py` - ssGSEA计算工具
- `validate_coherence.py` - 一致性验证工具
- `compare_methods.py` - 方法对比工具
- `optimize_pca.py` - PCA优化工具

#### 数据文件
- `annotations/` - 标注数据
- `comparison/` - 对比数据
- 原始定义文档

## 注意事项

这些文件对于：
- 理解项目开发历程
- 复现实验结果
- 调试和改进算法
- 学术研究和论文写作

具有重要价值，但不是运行最终系统所必需的。

如需使用这些文件，请参考各文件的注释和文档。