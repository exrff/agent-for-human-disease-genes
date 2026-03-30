# 五维生物系统分类与自动疾病分析

一个面向疾病转录组研究的自动化分析项目：以“五维功能系统分类”作为生物学解释框架，结合 GEO 数据获取、基因集映射、ssGSEA、可视化和 LLM 解读，形成从候选数据集选择到结果报告生成的端到端流程。

## 项目想解决什么问题

常见的 GO / KEGG 分析虽然能给出大量富集条目，但在疾病研究里经常有两个痛点：

- 条目很多，但难以形成系统层面的整体解释
- 富集结果偏“分子过程罗列”，不容易直接映射到疾病机制、系统失衡和功能转归

这个项目尝试用一个更高层的功能框架来组织生物学过程，把疾病样本的变化总结为五个核心系统的活性模式，再观察各个子类如何共同构成疾病表型。

## 核心创新点

### 1. 用“五维功能系统”重组生物过程解释

项目把复杂的 GO / KEGG 过程映射到五个功能系统：

- System A: 自愈与结构重建
- System B: 免疫防御
- System C: 能量与代谢稳态
- System D: 认知调控 / 神经-内分泌控制
- System E: 生殖与延续
- System 0: 通用分子机器层

同时进一步细分为 14 个功能子类，用于更精细地描述疾病的功能偏移模式。

### 2. 不只做富集，还做系统级活性画像

项目不是简单输出“哪些通路显著”，而是把表达矩阵映射到统一的子类基因集，再计算：

- 14 个子类的活性得分
- 5 大系统的聚合得分
- Top / Bottom 子类模式
- 疾病机制与系统失衡之间的对应关系

### 3. 把分析流程做成真正可运行的自动化 Agent

当前主链已经实现：

- 自动从白名单中选择尚未分析的数据集
- 自动下载 GEO 数据和 GPL 平台注释
- 自动完成预处理、基因映射、分类和 ssGSEA
- 自动生成图表、结构化日志和报告
- 在配置了 API Key 时，自动调用 LLM 做策略判断和结果解读

### 4. 结构化记录每个分析节点

项目不是只输出最终报告，还会为每次运行保留结构化运行记录，包括：

- 每个节点的开始时间、结束时间、耗时、状态
- 关键计算结果摘要
- LLM 调用 trace
- 最终报告与摘要文件

这让流程更适合复核、调试和方法学迭代。

## 当前能力

### 自动化分析能力

- 数据集选择：从 `data/geo_whitelist.csv` 中选择候选数据集
- 数据下载：自动获取 series matrix 和 GPL 注释
- 数据预处理：解析 GEO matrix，完成 probe-to-gene 映射
- 系统分类：将表达基因投射到 14 个功能子类
- ssGSEA：计算子类和系统活性得分
- 可视化：自动生成雷达图、热图、箱线图、条形图、相关性图
- 报告生成：输出 Markdown 报告、JSON 摘要和结构化日志

### LLM 增强能力

在配置 API Key 后，LLM 可参与：

- 分析策略决策
- 可视化策略决策
- 结果解释与报告文字生成
- 数据集选择辅助

当 LLM 不可用时，主流程会回退到规则引擎，保证分析仍可执行。

## 结果产物

每次分析完成后，会在 `results/agent_analysis/<GSE>/` 下输出：

- `<GSE>_report.md`
- `analysis_summary.json`
- `run_log.json`
- `node_events.jsonl`
- `llm_traces/`
- `figures/`

这意味着项目既能给出“人能读的报告”，也能给出“程序能继续消费的结构化结果”。

## 已完成的代表性结果

这套框架已经被用于多类疾病数据的系统级分析，包括：

- 乳腺癌
- 阿尔茨海默病 / 神经退行性疾病
- 糖尿病 / 代谢性疾病
- 戈谢病
- 创伤修复 / 伤口愈合
- 脓毒症 / 感染相关疾病

仓库中保留了两类结果：

- `results/disease_analysis/`
  历史手工疾病分析结果
- `results/agent_analysis/`
  当前自动 Agent 主链生成的结果

## 当前主链架构

主流程入口：

- `run_auto_analysis.py`

Agent 侧核心模块：

- `src/agent/dataset_selector_service.py`
- `src/agent/disease_analysis_agent.py`
- `src/agent/analysis_nodes_data.py`
- `src/agent/analysis_nodes_scoring.py`
- `src/agent/analysis_nodes_reporting.py`
- `src/agent/geo_parsing.py`
- `src/agent/scoring_core.py`
- `src/agent/llm_client.py`
- `src/agent/prompts.py`
- `src/agent/plot_generator.py`
- `src/agent/runtime_config.py`
- `src/agent/whitelist_repository.py`

数据获取模块：

- `src/data_extraction/geo_downloader.py`

## 工作流程

```text
白名单候选数据集
  -> 选择下一个待分析数据集
  -> 下载 GEO 原始数据与 GPL 注释
  -> 预处理并构建 gene-level expression matrix
  -> 五维子类 / 系统分类
  -> ssGSEA 活性计算
  -> 生成可视化
  -> LLM / 规则引擎解释结果
  -> 导出报告与结构化日志
```

## 快速开始

```bash
conda create -n thesis_env python=3.11
conda activate thesis_env
pip install -r requirements.txt
python run_auto_analysis.py --mode single
```

Windows 下也可以：

```bash
start.bat
python run_auto_analysis.py --mode single
```

## 白名单机制

- 唯一白名单来源：`data/geo_whitelist.csv`
- 自动分析当前只会从白名单中选择数据集
- 不再依赖代码内静态 `DATASETS` 列表

更新白名单：

```bash
python scripts/fetch_geo_whitelist.py
```

定向扩充（按 GPL 平台自动筛选并与现有白名单合并）：

```bash
python scripts/fetch_geo_whitelist.py --mode expand --platforms GPL570,GPL13158 --max-results 80 --min-samples 20 --check-series-matrix --merge
```

## Prompt 设计

Prompt 模板位于：

- `data/prompts/`

加载入口位于：

- `src/agent/prompts.py`

目前 prompt 主要用于：

- 数据集选择
- 分析策略决策
- 可视化策略决策
- 结果解读
- 报告摘要生成

## 仓库结构

```text
src/
  agent/
    disease_analysis_agent.py      # LangGraph 编排器
    analysis_nodes_data.py         # 元信息、下载、预处理
    analysis_nodes_scoring.py      # 分类与 ssGSEA
    analysis_nodes_reporting.py    # 解读、报告、导出
    geo_parsing.py                 # GEO / GPL 解析辅助
    scoring_core.py                # 共享打分核心
    dataset_selector_service.py
    llm_client.py
    runtime_config.py
    whitelist_repository.py
    prompts.py
    plot_generator.py
    geo_validator.py
  data_extraction/
    geo_downloader.py

scripts/
  fetch_geo_whitelist.py          # 刷新统一 GEO 白名单

data/
  geo_whitelist.csv
  prompts/
  validation_datasets/
  gpl_platforms/

results/
  disease_analysis/
  agent_analysis/

archive/
  src_legacy/
    scripts/
      download_gpl_platforms.py   # 旧 GPL 批量下载脚本，已归档
```

## 已归档的旧实现

以下旧模块已迁移到 `archive/src_legacy/agent/`：

- `config.py`
- `disease_selector.py`
- `llm_integration.py`
- `analysis_strategies.py`
- `logger.py`

以下历史目录也已迁移到 `archive/src_legacy/`：

- `analysis/`
- `classification/`
- `visualization/`
- `models/`
- `preprocessing/`
- `config/`

## 说明

- `src/agent/geo_validator.py` 目前仍保留，作为 GEO 预验证辅助工具
- 当前主链已经切换到新的分层 Agent 结构
- 结构化日志是当前版本的重要组成部分，便于调试、复核和后续扩展
