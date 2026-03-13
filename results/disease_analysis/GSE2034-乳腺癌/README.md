# GSE2034 - 乳腺癌 分析结果

## 数据集信息
- **GEO编号**: GSE2034
- **疾病类型**: 乳腺癌
- **分析框架**: 五系统分类框架
- **分析方法**: ssGSEA功能富集分析

## 文件结构

### 📊 干净数据 (clean_data/)
标准化的分析就绪数据文件：

- **GSE2034_clinical_features.csv**: 临床特征信息
- **GSE2034_sample_info.csv**: 样本元数据信息
- **GSE2034_subcategory_scores.csv**: 14个子分类ssGSEA得分
- **GSE2034_system_scores.csv**: 五大系统ssGSEA得分

### 📈 分析结果 (analysis_results/)
深入分析和可视化结果：

- **GSE2034_clinical_clusters.csv**: 分析结果数据
- **GSE2034_cluster_analysis.csv**: 分析结果数据
- **GSE2034_cluster_analysis_report.md**: 分析报告文档
- **GSE2034_cluster_comparison.png**: 可视化图表
- **GSE2034_FINAL_HETEROGENEITY_SUMMARY.md**: 分析报告文档
- **GSE2034_heterogeneity_analysis.png**: 可视化图表
- **GSE2034_heterogeneity_report.md**: 分析报告文档
- **GSE2034_sample_info_enhanced.csv**: 分析结果数据
- **GSE2034_subcategory_heatmap.png**: 可视化图表

## 主要发现

- **患者异质性**: 识别出2个不同的患者亚群
- **临床相关性**: 高激活亚群骨转移风险高56%
- **统计显著性**: 所有系统差异极显著 (p < 1e-50)
- **效应量**: 大效应量 (Cohen's d > 2.0)

## 使用建议

### 对于数据分析师
- 使用 `clean_data/` 中的标准化数据进行进一步分析
- 参考 `analysis_results/` 中的方法和结果

### 对于临床研究者
- 重点关注 `analysis_results/` 中的临床意义解释
- 查看可视化图表了解数据模式

### 对于生物信息学研究
- 标准化数据格式便于整合分析
- 可复现的分析流程和参数

---
*数据集分析完成时间: 2026年1月*
*五系统分类框架验证: ✅ 成功*
