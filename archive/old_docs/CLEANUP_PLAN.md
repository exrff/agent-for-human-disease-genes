# 项目清理计划

## 当前问题

1. **过多的说明文档** (15+ 个 MD 文件)
2. **重复的测试文件** (4 个测试脚本)
3. **过时的分析脚本** (24 个疾病分析脚本)
4. **多个启动脚本** (4 个启动文件)
5. **混乱的目录结构**

## 清理方案

### 📁 保留的核心文件

#### 根目录
```
├── README.md                          # 主文档（需更新）
├── requirements.txt                   # 依赖
├── .env                              # API Key
├── .gitignore                        # Git 配置
├── start.bat                         # 启动脚本（Conda版）
├── run_auto_analysis.py              # 自动分析主程序
└── gene_sets_14_subcategories.gmt    # 基因集数据
```

#### src/ 核心模块
```
src/
├── __init__.py
├── agent/                            # 智能体核心
│   ├── __init__.py
│   ├── disease_analysis_agent.py     # 主智能体
│   ├── disease_selector.py           # 疾病选择
│   ├── llm_integration.py            # LLM 集成
│   ├── analysis_strategies.py        # 分析策略
│   ├── config.py                     # 配置
│   └── logger.py                     # 日志
├── classification/                   # 分类模块
│   └── five_system_classifier.py
├── analysis/                         # 分析模块
│   ├── ssgsea_validator.py
│   └── semantic_similarity.py
├── models/                           # 数据模型
│   ├── biological_entry.py
│   └── classification_result.py
├── preprocessing/                    # 预处理
│   ├── go_parser.py
│   └── kegg_parser.py
├── visualization/                    # 可视化
│   └── chart_generator.py
└── config/                          # 全局配置
    └── settings.py
```

#### data/ 数据目录
```
data/
├── gene_sets/                        # 基因集
├── validation_datasets/              # 验证数据集
├── go_annotations/                   # GO 注释
└── kegg_mappings/                    # KEGG 映射
```

### 🗑️ 删除的文件

#### 1. 过多的说明文档（删除 13 个，保留 1 个）
- ❌ AGENT_ARCHITECTURE.md
- ❌ AGENT_QUICKSTART.md
- ❌ AGENT_SUMMARY.md
- ❌ DASHSCOPE_MIGRATION_SUMMARY.md
- ❌ DASHSCOPE_SETUP.md
- ❌ DISEASE_SELECTOR_GUIDE.md
- ❌ DISEASE_SELECTOR_SUMMARY.md
- ❌ GOOGLE_API_SETUP.md
- ❌ IMPLEMENTATION_ROADMAP.md
- ❌ LLM_FINAL_SUMMARY.md
- ❌ LLM_INTEGRATION_SUMMARY.md
- ❌ QUICK_IMPLEMENTATION_GUIDE.md
- ❌ QUICK_REFERENCE.md
- ❌ QUICK_START_DASHSCOPE.md
- ❌ QUICK_VERSION_COMPLETE.md
- ❌ START_SCRIPT_GUIDE.md
- ✅ README.md (保留并更新)

#### 2. 测试文件（删除 3 个，保留 1 个）
- ❌ test_dashscope_api.py
- ❌ test_google_api.py
- ❌ test_disease_selector.py
- ❌ test_quick_agent.py
- ✅ tests/test_agent_framework.py (保留)

#### 3. 启动脚本（删除 3 个，保留 1 个）
- ❌ start.ps1
- ❌ quick_start.bat
- ❌ quick_start_selector.bat
- ✅ start.bat (保留)

#### 4. 过时的分析脚本（移动到 archive/）
- src/disease_analysis/ 下所有 24 个脚本
  - 这些是单独的疾病分析脚本
  - 现在由智能体自动处理
  - 移动到 archive/legacy_analysis/

#### 5. 其他过时文件
- ❌ analyze_gse2034_heterogeneity.py (根目录)
- ❌ ssgsea_methods.md
- ❌ 项目STAR总结.md
- ❌ examples/run_agent_analysis.py (功能已集成)
- ❌ src/agent/visualize_graph.py (开发工具)
- ❌ src/agent/README.md (重复)

### 📦 归档目录
```
archive/
├── legacy_analysis/                  # 旧分析脚本
│   └── (24 个疾病分析脚本)
├── old_docs/                         # 旧文档
│   └── (16 个说明文档)
└── old_tests/                        # 旧测试
    └── (4 个测试脚本)
```

## 清理后的目录结构

```
五维分类/
├── README.md                         # 项目说明
├── requirements.txt                  # 依赖
├── .env                             # API Key
├── .gitignore                       # Git 配置
├── start.bat                        # 启动脚本
├── run_auto_analysis.py             # 自动分析
├── gene_sets_14_subcategories.gmt   # 基因集
│
├── src/                             # 源代码
│   ├── agent/                       # 智能体（核心）
│   ├── classification/              # 分类
│   ├── analysis/                    # 分析
│   ├── models/                      # 模型
│   ├── preprocessing/               # 预处理
│   ├── visualization/               # 可视化
│   └── config/                      # 配置
│
├── data/                            # 数据
│   ├── gene_sets/
│   ├── validation_datasets/
│   ├── go_annotations/
│   └── kegg_mappings/
│
├── results/                         # 结果输出
│   └── agent_analysis/
│
├── logs/                            # 日志
│
├── tests/                           # 测试
│   └── test_agent_framework.py
│
└── archive/                         # 归档
    ├── legacy_analysis/
    ├── old_docs/
    └── old_tests/
```

## 清理效果

### 文件数量对比
- **清理前**: 根目录 30+ 文件
- **清理后**: 根目录 7 文件
- **减少**: 77%

### 文档数量对比
- **清理前**: 16 个 MD 文件
- **清理后**: 1 个 README.md
- **减少**: 94%

### 优势
1. ✅ 结构清晰，一目了然
2. ✅ 核心功能突出
3. ✅ 易于维护和理解
4. ✅ 保留所有重要代码
5. ✅ 历史文件可追溯

## 执行步骤

1. 创建归档目录
2. 移动文档到 archive/old_docs/
3. 移动测试到 archive/old_tests/
4. 移动分析脚本到 archive/legacy_analysis/
5. 删除多余启动脚本
6. 更新 README.md
7. 验证核心功能
