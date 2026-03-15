# 五大功能系统分类与智能分析系统

## 项目简介

本项目实现了基于功能目标的五大系统分类框架，并构建了自动化疾病数据集分析智能体。

### 五大功能系统

- **System A**: 稳态与修复 (Self-Healing & Structural Reconstruction)
- **System B**: 免疫防御 (Immune Defense)
- **System C**: 代谢调节 (Energy & Metabolic Homeostasis)
- **System D**: 调节协调 (Cognitive-Regulatory)
- **System E**: 生殖发育 (Reproduction & Continuity)

### 核心功能

1. **五大系统分类**: 对 GO 本体和 KEGG 通路进行功能分类
2. **ssGSEA 分析**: 计算 14 个功能子类的激活得分
3. **智能体自动化**: 自动选择数据集、分析、生成报告
4. **LLM 集成**: 使用阿里云 DashScope (qwen-plus) 进行智能决策

## 快速开始

### 1. 环境准备

```bash
# 激活 Conda 环境
conda activate thesis_env

# 安装依赖
pip install -r requirements.txt

# 设置 API Key
echo "DASHSCOPE_API_KEY=your_key" > .env
```

### 2. 使用启动脚本

```bash
# Windows: 双击或运行
start.bat

# 这会自动：
# - 激活 Conda 环境
# - 加载 API Key
# - 打开配置好的命令行
```

### 3. 下载 GPL 平台文件（推荐，一次性）

```bash
# 批量下载所有常用 GPL 平台文件
python download_gpl_platforms.py --action download

# 这会下载 17 个常用平台到 data/gpl_platforms/
# 以后分析时会自动使用本地文件，不需要重复下载
```

### 4. 测试数据下载（可选）

```bash
# 测试下载单个数据集
python test_geo_downloader.py --test single --gse GSE2034

# 检查已有数据集
python test_geo_downloader.py --test check

# 批量下载测试
python test_geo_downloader.py --test batch
```

### 5. 运行分析

```bash
# 单次自动分析（智能体自动选择数据集并下载）
python run_auto_analysis.py --mode single

# 批量分析所有数据集
python run_auto_analysis.py --mode batch

# 批量分析最多 3 个数据集
python run_auto_analysis.py --mode batch --max 3

# 不使用 LLM（仅规则引擎）
python run_auto_analysis.py --mode single --no-llm
```

**注意**: 智能体会自动检查数据集是否存在，如果不存在会自动从 GEO 数据库下载。

## 项目结构

```
五维分类/
├── src/                          # 源代码
│   ├── agent/                    # 智能体（核心）
│   │   ├── disease_analysis_agent.py   # 主智能体
│   │   ├── disease_selector.py         # 疾病选择
│   │   ├── llm_integration.py          # LLM 集成
│   │   ├── analysis_strategies.py      # 分析策略
│   │   ├── config.py                   # 配置
│   │   └── logger.py                   # 日志
│   ├── classification/           # 分类引擎
│   │   └── five_system_classifier.py
│   ├── analysis/                 # 分析模块
│   │   ├── ssgsea_validator.py
│   │   ├── semantic_similarity.py
│   │   └── clustering_quality_evaluator.py
│   ├── models/                   # 数据模型
│   ├── preprocessing/            # 数据预处理
│   ├── visualization/            # 可视化
│   └── config/                   # 全局配置
│
├── data/                         # 数据
│   ├── gene_sets/                # 基因集
│   ├── validation_datasets/      # 验证数据集
│   ├── go_annotations/           # GO 注释
│   └── kegg_mappings/            # KEGG 映射
│
├── results/                      # 结果输出
│   └── agent_analysis/           # 智能体分析结果
│
├── logs/                         # 日志文件
│
├── archive/                      # 归档文件
│   ├── old_docs/                 # 旧文档
│   ├── old_tests/                # 旧测试
│   └── legacy_analysis/          # 旧分析脚本
│
├── README.md                     # 本文档
├── requirements.txt              # 依赖
├── start.bat                     # 启动脚本
└── run_auto_analysis.py          # 自动分析主程序
```

## 智能体工作流

```
疾病选择智能体
    ↓
扫描已分析数据集 → 分析覆盖度 → LLM/规则引擎决策
    ↓
推荐下一个数据集
    ↓
疾病分析智能体 (11 节点工作流)
    ↓
1. 提取元数据 → 2. 决策策略 → 3. 下载数据 (自动从 GEO 下载)
    ↓
4. 预处理 → 5. 基因分类 → 6. ssGSEA 分析
    ↓
7. 决策可视化 → 8. 生成图表 → 9. 结果解读
    ↓
10. 生成报告 → 11. 导出 PDF
```

### 数据下载说明

智能体在第 3 步会自动处理数据：

1. **检查本地**: 首先检查 `data/validation_datasets/` 是否已有数据
2. **自动下载**: 如果数据不存在，自动从 NCBI GEO 数据库下载
   - Series matrix 文件 (表达数据)
   - Platform 注释文件 (基因注释)
3. **验证完整性**: 确保下载的文件完整可用
4. **继续分析**: 下载完成后自动进入预处理步骤

**下载来源**: https://ftp.ncbi.nlm.nih.gov/geo/

## 可用数据集

| 数据集 ID | 疾病名称 | 类型 | 预期系统 |
|-----------|----------|------|----------|
| GSE122063 | 阿尔兹海默症 | neurodegenerative | D, A |
| GSE2034 | 乳腺癌 | cancer | A, B, E |
| GSE26168 | 糖尿病 | metabolic | C, D |
| GSE21899 | 戈谢病 | metabolic | C, D |
| GSE28914 | 伤口愈合 | repair | A, B |
| GSE50425 | 伤口愈合扩展 | repair | A, B |
| GSE65682 | 脓毒症 | infection | B, C |

## 输出结果

### 分析报告
```
results/agent_analysis/GSE2034/
├── GSE2034_report.md             # Markdown 报告
├── summary.json                  # 分析摘要
└── figures/                      # 图表
    ├── heatmap.png
    ├── boxplot.png
    └── volcano.png
```

### 日志文件
```
logs/
├── auto_analysis_20240313_143022.log
└── agent_execution.log
```

## 技术栈

- **Python 3.9+**
- **LangGraph**: 智能体工作流框架
- **DashScope**: 阿里云百炼 LLM (qwen-plus)
- **NumPy/Pandas**: 数据处理
- **Matplotlib/Seaborn**: 可视化

## 开发说明

### 添加新数据集

编辑 `src/agent/config.py`:

```python
DATASETS = {
    'GSE_NEW': {
        'name': 'Disease Name',
        'chinese_name': '疾病名称',
        'disease_type': 'cancer',  # 或 metabolic, neurodegenerative 等
        'expected_systems': ['System A', 'System B'],
        'description': '疾病描述'
    }
}
```

### 自定义分析策略

编辑 `src/agent/analysis_strategies.py` 添加新的分析子图。

### 修改 LLM 配置

编辑 `src/agent/config.py`:

```python
LLM_CONFIG = {
    'provider': 'dashscope',
    'model': 'qwen-plus',  # 或 qwen-turbo, qwen-max
    'temperature': 0.3,
    'max_tokens': 2000
}
```

## 故障排查

### 问题 1: API Key 未设置

```bash
# 检查
echo $env:DASHSCOPE_API_KEY

# 设置
echo "DASHSCOPE_API_KEY=your_key" > .env
```

### 问题 2: 依赖缺失

```bash
pip install -r requirements.txt
```

### 问题 3: 数据文件不存在

检查 `data/validation_datasets/` 目录是否包含数据集文件。

## 许可证

本项目用于学术研究。

## 联系方式

如有问题，请查看 `archive/old_docs/` 中的详细文档。
