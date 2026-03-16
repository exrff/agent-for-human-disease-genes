# 五维生物系统分类 · 疾病分析 Agent

基于 **LangGraph** 构建的自主疾病基因组分析智能体。Agent 能够自动选择 GEO 数据集、执行 ssGSEA 分析、生成可视化报告，并通过 LLM 解读生物学意义。

## 项目亮点

- **LangGraph 多节点工作流**：11 个节点的有向图，涵盖数据下载 → 预处理 → 分类 → ssGSEA → 可视化 → LLM 解读 → 报告导出全流程
- **自主数据集选择**：LLM 从 90+ 个人类疾病 GEO 数据集白名单中，根据已分析疾病的覆盖度和系统多样性，智能推荐下一个最有价值的数据集
- **五大生物系统分类**：基于 GO/KEGG 注释，将基因组分类为修复(A)、免疫(B)、代谢(C)、神经调节(D)、生殖发育(E) 五大系统
- **自实现 ssGSEA**：不依赖 gseapy，自行实现 single-sample GSEA 算法，对每个样本计算系统激活分数
- **DashScope LLM 集成**：通过 OpenAI 兼容接口调用 Qwen 模型，完成数据集推荐、分析策略制定、结果解读三个环节

## 架构

```
run_auto_analysis.py          # 主入口
│
├── DiseaseSelector           # 疾病选择 Agent
│   ├── 扫描已分析数据集
│   ├── 从白名单(DATASETS + geo_whitelist.csv)获取候选
│   └── LLM 推荐 / 规则引擎兜底
│
└── LangGraph 分析工作流
    ├── extract_metadata      # 提取数据集元信息
    ├── download_data         # 下载 series matrix（本地 GPL 优先）
    ├── preprocess_data       # probe → gene 表达矩阵
    ├── classify_genes        # 五大系统分类
    ├── run_ssgsea            # ssGSEA 系统激活分数
    ├── determine_strategy    # LLM 制定分析策略
    ├── generate_visualizations # 雷达图/箱线图/热图等
    ├── interpret_results     # LLM 生物学解读
    ├── generate_report       # Markdown 报告
    └── export_pdf            # 保存结果 + analysis_summary.json
```

## 快速开始

**环境要求**：Python 3.11，conda

```bash
# 1. 克隆项目
git clone https://github.com/your-username/five-system-disease-agent.git
cd five-system-disease-agent

# 2. 创建环境
conda create -n thesis_env python=3.11
conda activate thesis_env
pip install -r requirements.txt

# 3. 配置 API Key
cp .env.example .env
# 编辑 .env，填入你的 DASHSCOPE_API_KEY

# 4. 运行（Windows）
start.bat          # 激活环境并加载 .env
python run_auto_analysis.py
```

## 数据集白名单扩充

```bash
# 从 NCBI GEO 自动筛选人类表达谱数据集，追加到 data/geo_whitelist.csv
python fetch_geo_whitelist.py
```

## 项目结构

```
src/
├── agent/                    # ★ 核心 Agent 逻辑
│   ├── disease_analysis_agent.py  # LangGraph 工作流定义（11节点）
│   ├── disease_selector.py        # 疾病选择 Agent
│   ├── llm_integration.py         # DashScope LLM 封装
│   ├── plot_generator.py          # matplotlib/seaborn 可视化
│   ├── config.py                  # 数据集白名单 + 参数配置
│   ├── analysis_strategies.py     # 分析策略定义
│   ├── geo_validator.py           # GEO 数据集预验证
│   └── logger.py                  # 日志配置
├── classification/           # 五大系统基因分类器
├── analysis/                 # ssGSEA 实现、语义分析
├── preprocessing/            # GO/KEGG 注释解析
├── visualization/            # 报告导出
└── data_extraction/          # GEO 数据下载器

data/
├── gpl_platforms/            # 本地 GPL 平台注释文件
├── geo_whitelist.csv         # 自动筛选的 GEO 数据集白名单
└── validation_datasets/      # 已下载的数据集

tests/                        # 调试脚本
results/agent_analysis/       # 分析输出（报告、图表、JSON）
```

## 技术栈

| 组件 | 技术 |
|------|------|
| Agent 框架 | LangGraph |
| LLM | Qwen3.5-122B (DashScope) |
| 基因分析 | 自实现 ssGSEA |
| 数据来源 | NCBI GEO |
| 可视化 | matplotlib / seaborn |
| 基因注释 | GO / KEGG |

## 许可证

MIT
