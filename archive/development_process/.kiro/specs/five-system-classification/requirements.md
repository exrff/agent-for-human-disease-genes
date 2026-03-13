# 五大功能系统分类研究 - 需求文档

## 简介

本研究旨在建立一个基于生物学功能的五大系统分类框架，用于对GO本体和KEGG通路数据进行系统性分类，并通过真实的基因表达数据集进行验证。该分类系统将为生物医学研究提供一个新的功能注释和分析框架。

## 术语表

- **GO (Gene Ontology)**: 基因本体，描述基因产物功能的标准化词汇体系
- **KEGG (Kyoto Encyclopedia of Genes and Genomes)**: 京都基因与基因组百科全书，包含生物通路信息
- **ssGSEA (single sample Gene Set Enrichment Analysis)**: 单样本基因集富集分析方法
- **五大功能系统**: 基于功能目标的生物学过程分类框架，包含System A-E
- **功能目标 (Functional Objective)**: 生物过程在有机体中服务的主要生命任务
- **System A**: Self-Healing & Structural Reconstruction System (自愈与结构重建系统)
- **System B**: Immune Defense System (免疫防御系统)
- **System C**: Energy & Metabolic Homeostasis System (能量与代谢稳态系统)
- **System D**: Cognitive-Regulatory System (认知调节系统)
- **System E**: Reproduction & Continuity System (生殖与延续系统)
- **System 0**: General Molecular Machinery Layer (通用分子机制层)
- **分类器 (Classifier)**: 用于将生物学条目分配到五大系统的算法
- **验证数据集 (Validation Dataset)**: 用于验证分类系统有效性的真实基因表达数据
- **炎症极性 (Inflammation Polarity)**: 炎症相关过程的正交属性标注

## 需求

### 需求 1: 五大功能系统定义

**用户故事**: 作为生物医学研究者，我希望有一个基于功能目标的五大功能系统分类框架，以便能够系统性地理解和分析生物学过程的核心功能。

#### 验收标准

1. WHEN 定义分类原则 THEN 系统 SHALL 采用面向功能的分类策略，按照生物过程在有机体中服务的主要生命任务进行分类，而非按器官、信号通路或分子实体分类

2. WHEN 定义五大功能系统 THEN 系统 SHALL 包含以下明确定义的功能系统：
   - System A: Self-Healing & Structural Reconstruction (自愈与结构重建系统)
   - System B: Immune Defense (免疫防御系统)
   - System C: Energy & Metabolic Homeostasis (能量与代谢稳态系统)
   - System D: Cognitive-Regulatory (认知调节系统)
   - System E: Reproduction & Continuity (生殖与延续系统)

3. WHEN 定义System A THEN 系统 SHALL 包含保护或恢复细胞和组织完整性的建设性生物过程，包括基因组稳定性修复(A1)、体细胞维护(A2)、细胞稳态(A3)、炎症消解(A4)四个子类别

4. WHEN 定义System B THEN 系统 SHALL 包含检测、靶向和消除外部病原体及异常内源性元素的生物过程，包括先天免疫(B1)、适应性免疫(B2)、免疫调节(B3)三个子类别

5. WHEN 定义System C THEN 系统 SHALL 包含获取、转化、储存和分配能量及生化底物的生物过程，包括能量代谢(C1)、生物合成(C2)、解毒(C3)三个子类别

6. WHEN 定义System D THEN 系统 SHALL 包含感知内外状态、整合信号、设定优先级并协调其他功能系统的生物过程，包括神经调节(D1)、内分泌调节(D2)两个子类别

7. WHEN 定义System E THEN 系统 SHALL 包含生殖细胞产生、遗传传递和发育的生物过程，包括生殖(E1)、发育成熟(E2)两个子类别

8. WHEN 处理炎症相关过程 THEN 系统 SHALL 标注炎症极性属性为{促炎、抗炎、促消解}之一，并根据主要功能目标分配到System B或System A

9. WHEN 处理共享分子机制 THEN 系统 SHALL 将无法明确分配的通用分子机制归类为System 0 (General Molecular Machinery Layer)

### 需求 2: GO本体数据分类

**用户故事**: 作为研究者，我希望能够将GO本体中的生物学过程条目准确分类到五大功能系统中，以便进行功能分析。

#### 验收标准

1. WHEN 处理GO条目 THEN 系统 SHALL 仅处理biological_process命名空间的条目

2. WHEN 遇到过时条目 THEN 系统 SHALL 排除标记为"obsolete"的GO条目

3. WHEN 分类GO条目 THEN 系统 SHALL 基于条目名称、定义和祖先节点信息进行分类

4. WHEN 利用GO层次结构 THEN 系统 SHALL 考虑GO DAG中的is_a关系进行祖先节点分析

5. WHEN 生成分类结果 THEN 系统 SHALL 为每个条目提供主要系统分类和所有匹配系统列表

### 需求 3: KEGG通路数据分类

**用户故事**: 作为研究者，我希望能够将KEGG通路数据分类到五大功能系统中，以便与GO分类结果进行整合分析。

#### 验收标准

1. WHEN 处理KEGG通路 THEN 系统 SHALL 基于通路的层次分类信息（Class A, Class B）和通路名称进行分类

2. WHEN 解析KEGG文件 THEN 系统 SHALL 正确解析br_br08901.txt格式的KEGG层次结构文件

3. WHEN 分类KEGG条目 THEN 系统 SHALL 使用与GO分类一致的规则和优先级

4. WHEN 处理代谢通路 THEN 系统 SHALL 将所有metabolism相关的通路归类为System C

5. WHEN 处理免疫相关通路 THEN 系统 SHALL 识别免疫系统、药物抗性等相关通路归类为System B

### 需求 4: 分类算法实现

**用户故事**: 作为开发者，我希望有一个基于功能目标的分类算法，能够准确地将生物学条目按照其主要功能目标分类到正确的功能系统中。

#### 验收标准

1. WHEN 实现分类逻辑 THEN 系统 SHALL 基于主要功能目标进行分类，而非基于共享分子、细胞类型或解剖位置

2. WHEN 处理包含破坏性和建设性组分的通路 THEN 系统 SHALL 将通路拆分为组分并分别标注，共享实现机制分配到System 0

3. WHEN 处理炎症相关过程 THEN 系统 SHALL 根据以下决策规则分配：
   - 威胁识别和清除为主要目标时分配到System B (B1/B2)
   - 免疫自限/耐受为主要目标时分配到System B3
   - 炎症消解和损伤控制结合修复程序时分配到System A4
   - 结构修复为主要目标时分配到System A (A1-A3)

4. WHEN 应用分类规则 THEN 系统 SHALL 使用基于正则表达式和关键词匹配的规则引擎，进行大小写不敏感的匹配

5. WHEN 记录分类结果 THEN 系统 SHALL 保存主要系统分类、所有匹配系统和炎症极性属性的完整信息

6. WHEN 处理边界情况 THEN 系统 SHALL 正确处理多系统匹配情况，并将无法明确分配的通用机制归类为System 0

### 需求 5: 验证数据集处理

**用户故事**: 作为研究者，我希望能够使用真实的基因表达数据集来验证五大分类系统的生物学有效性。

#### 验收标准

1. WHEN 处理验证数据集 THEN 系统 SHALL 支持处理GEO数据集格式（series_matrix.txt.gz）

2. WHEN 计算功能得分 THEN 系统 SHALL 使用ssGSEA方法计算每个样本在五大系统上的富集得分

3. WHEN 进行时间序列分析 THEN 系统 SHALL 支持分析伤口愈合等时间序列数据的系统得分变化

4. WHEN 进行疾病对比分析 THEN 系统 SHALL 支持比较疾病组与对照组之间的系统得分差异

5. WHEN 生成验证报告 THEN 系统 SHALL 提供统计显著性检验和可视化结果

### 需求 6: 语义一致性验证

**用户故事**: 作为研究者，我希望验证五大分类系统具有良好的语义聚类一致性，确保分类的科学合理性。

#### 验收标准

1. WHEN 计算语义相似度 THEN 系统 SHALL 基于GO本体结构计算条目间的语义相似度

2. WHEN 评估系统内一致性 THEN 系统 SHALL 计算每个系统内部条目的平均语义相似度

3. WHEN 评估系统间差异性 THEN 系统 SHALL 计算不同系统间条目的平均语义相似度

4. WHEN 验证聚类质量 THEN 系统 SHALL 确保系统内相似度显著高于系统间相似度

5. WHEN 生成验证报告 THEN 系统 SHALL 提供语义一致性的定量评估结果

### 需求 7: 基线方法对比

**用户故事**: 作为研究者，我希望将五大分类系统与现有的基线方法进行对比，证明其优越性。

#### 验收标准

1. WHEN 实现PCA基线 THEN 系统 SHALL 使用主成分分析作为降维基线方法

2. WHEN 进行分类性能对比 THEN 系统 SHALL 在相同的验证数据集上比较五大系统与PCA的分类性能

3. WHEN 评估分类准确性 THEN 系统 SHALL 使用准确率、F1分数、AUC等指标评估性能

4. WHEN 处理高维数据 THEN 系统 SHALL 支持处理包含数千个GO条目的高维特征空间

5. WHEN 生成对比报告 THEN 系统 SHALL 提供详细的性能对比分析和统计检验结果

### 需求 8: 结果输出和可视化

**用户故事**: 作为研究者，我希望获得清晰的分类结果和可视化图表，用于论文发表和学术交流。

#### 验收标准

1. WHEN 输出分类结果 THEN 系统 SHALL 生成包含ID、名称、定义、来源、主要系统、所有系统的CSV格式文件

2. WHEN 生成统计报告 THEN 系统 SHALL 提供每个系统的条目数量和百分比分布

3. WHEN 创建可视化图表 THEN 系统 SHALL 生成词云图、热图、箱线图等可视化结果

4. WHEN 进行时间序列可视化 THEN 系统 SHALL 生成时间序列数据的系统得分变化图

5. WHEN 输出论文图表 THEN 系统 SHALL 生成符合学术发表标准的高质量图表文件

### 需求 9: 数据质量和完整性

**用户故事**: 作为研究者，我希望确保输入数据的质量和分类结果的完整性，避免数据错误影响研究结论。

#### 验收标准

1. WHEN 验证输入数据 THEN 系统 SHALL 检查GO和KEGG数据文件的格式和完整性

2. WHEN 处理缺失数据 THEN 系统 SHALL 正确处理缺失的名称、定义或层次信息

3. WHEN 检查分类覆盖率 THEN 系统 SHALL 报告未分类条目的数量和比例

4. WHEN 验证分类一致性 THEN 系统 SHALL 确保相同条目在不同运行中得到一致的分类结果

5. WHEN 记录处理日志 THEN 系统 SHALL 提供详细的处理日志和错误报告

### 需求 11: 子系统分类和炎症极性标注

**用户故事**: 作为研究者，我希望能够将生物学过程进一步分类到具体的子系统中，并对炎症相关过程进行极性标注，以便进行更精细的功能分析。

#### 验收标准

1. WHEN 分类到System A THEN 系统 SHALL 进一步分类到子系统：
   - A1: 基因组稳定性和修复 (DNA损伤修复、染色质维护、端粒维护)
   - A2: 体细胞维护和身份保持 (干细胞维护、分化、衰老程序)
   - A3: 细胞稳态和结构维护 (蛋白稳态、自噬、细胞器修复)
   - A4: 炎症消解和损伤控制 (胞吞清除、促消解介质、屏障恢复)

2. WHEN 分类到System B THEN 系统 SHALL 进一步分类到子系统：
   - B1: 先天免疫 (屏障监视、模式识别、炎症信号、吞噬)
   - B2: 适应性免疫 (抗原特异性反应、克隆选择、免疫记忆)
   - B3: 免疫调节和耐受 (负反馈控制、检查点调节、耐受机制)

3. WHEN 分类到System C THEN 系统 SHALL 进一步分类到子系统：
   - C1: 能量代谢和分解代谢 (营养分解、氧化还原平衡、ATP生成)
   - C2: 生物合成和合成代谢 (大分子构建块合成、生长维护需求)
   - C3: 解毒和代谢应激处理 (异生物质转化、有害代谢物消除)

4. WHEN 分类到System D THEN 系统 SHALL 进一步分类到子系统：
   - D1: 神经调节和信号传递 (神经信号、突触通讯、感觉运动整合)
   - D2: 内分泌和自主调节 (激素信号、自主神经、生理设定点)

5. WHEN 分类到System E THEN 系统 SHALL 进一步分类到子系统：
   - E1: 生殖 (配子发生、生殖内分泌、受精、妊娠)
   - E2: 发育和生殖成熟 (胚胎发育、性分化、生殖能力建立)

6. WHEN 处理炎症相关过程 THEN 系统 SHALL 标注炎症极性属性：
   - 促炎 (pro-inflammatory): 激活炎症效应子
   - 抗炎 (anti-inflammatory): 通过免疫自限/耐受抑制炎症效应子
   - 促消解 (pro-resolving): 主动终止炎症并促进组织稳态恢复

7. WHEN 记录子系统分类 THEN 系统 SHALL 保存主系统、子系统和炎症极性的完整标注信息

### 需求 10: 可重现性和版本控制

**用户故事**: 作为研究者，我希望研究结果具有良好的可重现性，并能够追踪分类规则的演进历史。

#### 验收标准

1. WHEN 保存分类规则 THEN 系统 SHALL 维护分类规则的版本历史（v6, v7, v7.5等）

2. WHEN 记录参数设置 THEN 系统 SHALL 保存所有关键参数和配置信息

3. WHEN 提供重现脚本 THEN 系统 SHALL 提供完整的数据处理和分析脚本

4. WHEN 管理依赖环境 THEN 系统 SHALL 提供requirements.txt和环境配置信息

5. WHEN 验证可重现性 THEN 系统 SHALL 确保在相同环境下能够重现所有结果

**用户故事**: 作为研究者，我希望研究结果具有良好的可重现性，并能够追踪分类规则的演进历史。

#### 验收标准

1. WHEN 保存分类规则 THEN 系统 SHALL 维护分类规则的版本历史（v6, v7, v7.5等）

2. WHEN 记录参数设置 THEN 系统 SHALL 保存所有关键参数和配置信息

3. WHEN 提供重现脚本 THEN 系统 SHALL 提供完整的数据处理和分析脚本

4. WHEN 管理依赖环境 THEN 系统 SHALL 提供requirements.txt和环境配置信息

5. WHEN 验证可重现性 THEN 系统 SHALL 确保在相同环境下能够重现所有结果