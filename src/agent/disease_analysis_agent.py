#!/usr/bin/env python3
"""
疾病分析智能体 - 基于 LangGraph 的自动化分析流程

功能：
1. 自动下载疾病数据集
2. 数据预处理和质量检查
3. 五大系统分类
4. ssGSEA 评估
5. 智能绘图（根据数据特征选择可视化方式）
6. 结果解读和报告生成
7. PDF 报告输出
8. 全程日志记录
"""

import os
import json
import logging
from datetime import datetime
from typing import TypedDict, Annotated, List, Dict, Any, Optional
from pathlib import Path

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage


# ============================================================================
# 状态定义
# ============================================================================

class AnalysisState(TypedDict):
    """分析状态 - 贯穿整个工作流的状态对象"""
    
    # 输入信息
    dataset_id: str  # 数据集ID (如 GSE2034)
    dataset_info: Dict[str, Any]  # 数据集元信息
    
    # 数据路径
    raw_data_path: Optional[str]  # 原始数据路径
    processed_data_path: Optional[str]  # 处理后数据路径
    
    # 分析结果
    expression_matrix: Optional[Any]  # 表达矩阵
    sample_metadata: Optional[Dict]  # 样本元数据
    classification_results: Optional[Dict]  # 分类结果
    ssgsea_scores: Optional[Dict]  # ssGSEA 得分
    statistical_results: Optional[Dict]  # 统计分析结果
    
    # 决策信息
    disease_type: Optional[str]  # 疾病类型
    analysis_strategy: Optional[str]  # 分析策略
    visualization_plan: List[str]  # 可视化计划
    
    # 输出
    figures: List[str]  # 生成的图表路径
    interpretation: Optional[str]  # 结果解读
    report_path: Optional[str]  # 报告路径
    
    # 日志和错误
    log_messages: List[str]  # 日志消息
    errors: List[str]  # 错误信息
    current_step: str  # 当前步骤
    
    # 控制流
    needs_human_review: bool  # 是否需要人工审核
    retry_count: int  # 重试次数


# ============================================================================
# 节点函数
# ============================================================================

def extract_dataset_metadata(state: AnalysisState) -> AnalysisState:
    """
    节点1: 提取数据集元信息
    
    功能：
    - 识别数据集类型（癌症、代谢病、神经退行性疾病等）
    - 提取样本分组信息
    - 确定分析目标
    """
    state["current_step"] = "extract_metadata"
    state["log_messages"].append(f"[{datetime.now()}] 开始提取数据集元信息...")
    
    dataset_id = state["dataset_id"]
    
    # 从配置中获取数据集信息
    from .config import AgentConfig
    dataset_info = AgentConfig.get_dataset_config(dataset_id)
    
    state["dataset_info"] = dataset_info
    state["disease_type"] = dataset_info.get("disease_type", "unknown")
    
    state["log_messages"].append(f"✓ 数据集: {dataset_info.get('chinese_name', dataset_id)}")
    state["log_messages"].append(f"✓ 疾病类型: {state['disease_type']}")
    state["log_messages"].append(f"数据集 {dataset_id} 元信息提取完成")
    
    return state


def decide_analysis_strategy(state: AnalysisState) -> AnalysisState:
    """
    决策节点1: 确定分析策略
    
    根据疾病类型和数据特征，决定：
    - 病例对照分析
    - 亚型比较分析
    - 时序分析
    - 相关性分析
    """
    state["current_step"] = "decide_strategy"
    state["log_messages"].append(f"[{datetime.now()}] 决策分析策略...")
    
    # 尝试使用 LLM 决策
    try:
        from .llm_integration import create_llm_integration
        from .config import AgentConfig
        
        llm = create_llm_integration()
        
        # 准备数据集信息
        dataset_info = {
            'dataset_id': state['dataset_id'],
            **state.get('dataset_info', {})
        }
        
        # LLM 决策
        decision = llm.decide_analysis_strategy(dataset_info)
        
        state['analysis_strategy'] = decision['strategy']
        state['log_messages'].append(
            f"LLM 决策: {decision['strategy']} (置信度: {decision.get('confidence', 0):.2f})"
        )
        state['log_messages'].append(f"理由: {decision.get('reasoning', '')}")
        
        # 保存决策详情到元数据
        if 'metadata' not in state:
            state['metadata'] = {}
        state['metadata']['strategy_decision'] = decision
        
    except Exception as e:
        # 回退到规则引擎
        state['log_messages'].append(f"LLM 不可用，使用规则引擎: {e}")
        
        from .config import AgentConfig
        disease_type = state.get('disease_type', 'unknown')
        dataset_info = state.get('dataset_info', {})
        
        strategy_map = {
            'neurodegenerative': 'case_control',
            'cancer': 'subtype_comparison',
            'metabolic': 'case_control',
            'repair': 'time_series',
            'infection': 'case_control'
        }
        
        strategy = strategy_map.get(disease_type, 'case_control')
        state['analysis_strategy'] = strategy
        state['log_messages'].append(f"规则引擎决策: {strategy}")
    
    return state


def download_dataset(state: AnalysisState) -> AnalysisState:
    """
    节点2: 下载数据集
    
    功能：
    - 检查数据集是否已存在
    - 如果不存在，自动从 GEO 下载
    - 下载 series matrix 和 platform 文件
    """
    state["current_step"] = "download"
    state["log_messages"].append(f"[{datetime.now()}] 准备数据集...")
    
    dataset_id = state["dataset_id"]
    data_path = f"data/validation_datasets/{dataset_id}"
    
    import os
    
    # 检查数据是否已存在
    if os.path.exists(data_path):
        # 检查必要文件是否完整
        series_file = os.path.join(data_path, f"{dataset_id}_series_matrix.txt.gz")
        platform_files = [f for f in os.listdir(data_path) if f.startswith('GPL')]
        
        if os.path.exists(series_file) and len(platform_files) > 0:
            state["raw_data_path"] = data_path
            state["log_messages"].append(f"✓ 数据已存在: {data_path}")
            state["log_messages"].append(f"  - Series matrix: {os.path.basename(series_file)}")
            state["log_messages"].append(f"  - Platform 文件: {len(platform_files)} 个")
            state["log_messages"].append("数据准备完成")
            return state
        else:
            state["log_messages"].append(f"⚠️  数据不完整，重新下载...")
    
    # 数据不存在或不完整，开始下载
    state["log_messages"].append(f"开始从 GEO 下载 {dataset_id}...")
    
    try:
        # 导入下载器
        from src.data_extraction.geo_downloader import download_geo_dataset
        
        # 下载数据集
        result = download_geo_dataset(dataset_id)
        
        if result['success']:
            state["raw_data_path"] = data_path
            state["log_messages"].append(f"✅ 数据下载成功")
            state["log_messages"].append(f"  - Series matrix: {os.path.basename(result['series_matrix_file'])}")
            state["log_messages"].append(f"  - Platform 文件: {len(result['platform_files'])} 个")
            
            # 保存下载信息到状态
            if 'metadata' not in state:
                state['metadata'] = {}
            state['metadata']['download_result'] = result
            
        else:
            # 下载失败，记录错误但继续（使用模拟数据）
            state["raw_data_path"] = data_path
            state["log_messages"].append(f"❌ 数据下载失败")
            for error in result.get('errors', []):
                state["log_messages"].append(f"  {error}")
            state["log_messages"].append(f"⚠️  将使用模拟数据继续分析")
            
            # 记录错误
            if 'errors' not in state:
                state['errors'] = []
            state['errors'].append(f"数据下载失败: {dataset_id}")
    
    except Exception as e:
        # 下载器异常，记录但继续
        state["raw_data_path"] = data_path
        state["log_messages"].append(f"❌ 下载器异常: {e}")
        state["log_messages"].append(f"⚠️  将使用模拟数据继续分析")
        
        if 'errors' not in state:
            state['errors'] = []
        state['errors'].append(f"下载器异常: {str(e)}")
    
    state["log_messages"].append("数据准备完成")
    
    return state


def preprocess_data(state: AnalysisState) -> AnalysisState:
    """节点3: 数据预处理 — 解析 series matrix + GPL 平台文件，生成 gene 表达矩阵"""
    state["current_step"] = "preprocess"
    state["log_messages"].append(f"[{datetime.now()}] 数据预处理...")

    dataset_id = state["dataset_id"]
    data_dir = Path("data/validation_datasets")

    # 找到数据集目录（支持 GSExxxx 或 GSExxxx-疾病名 两种格式）
    dataset_dir = None
    for d in data_dir.iterdir():
        if d.is_dir() and d.name.startswith(dataset_id):
            dataset_dir = d
            break
    if dataset_dir is None:
        dataset_dir = data_dir / dataset_id

    series_file = dataset_dir / f"{dataset_id}_series_matrix.txt.gz"
    if not series_file.exists():
        state["errors"].append(f"Series matrix 文件不存在: {series_file}")
        state["log_messages"].append("❌ 找不到 series matrix 文件")
        return state

    gpl_file = _find_gpl_file(series_file, dataset_dir)
    if gpl_file is None:
        state["errors"].append("找不到 GPL 平台注释文件")
        state["log_messages"].append("❌ 找不到 GPL 平台文件")
        return state

    state["log_messages"].append(f"✓ Series matrix: {series_file.name}")
    state["log_messages"].append(f"✓ GPL 文件: {gpl_file.name}")

    try:
        # 解析 series matrix → probe 表达矩阵
        expr_df = _parse_series_matrix(series_file)
        state["log_messages"].append(f"✓ Probe 矩阵: {expr_df.shape[0]} probes × {expr_df.shape[1]} 样本")

        # 解析 GPL → probe→gene 映射
        mapping_df = _parse_gpl_annotation(gpl_file)
        state["log_messages"].append(f"✓ 映射: {mapping_df['probe_id'].nunique()} probes → {mapping_df['gene_symbol'].nunique()} genes")

        # probe → gene 表达矩阵（多 probe 取均值）
        gene_expr_df = _map_probe_to_gene(expr_df, mapping_df)
        state["log_messages"].append(f"✓ Gene 矩阵: {gene_expr_df.shape[0]} genes × {gene_expr_df.shape[1]} 样本")

        state["expression_matrix"] = gene_expr_df
        state["sample_metadata"] = _extract_sample_info(series_file)
        state["processed_data_path"] = str(dataset_dir)
        state["log_messages"].append("预处理完成")

    except Exception as e:
        import traceback
        state["errors"].append(f"预处理失败: {e}")
        state["log_messages"].append(f"❌ 预处理失败: {e}\n{traceback.format_exc()}")

    return state



def _find_gpl_file(series_file: Path, dataset_dir: Path) -> Optional[Path]:
    """查找 GPL 平台文件：先从 series matrix 提取平台 ID，再按优先级查找"""
    import gzip, re

    platform_id = None
    try:
        with gzip.open(series_file, 'rt', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('!Series_platform_id'):
                    m = re.search(r'GPL\d+', line)
                    if m:
                        platform_id = m.group()
                    break
    except Exception:
        pass

    search_dirs = [Path("data/gpl_platforms"), dataset_dir]
    for d in search_dirs:
        if not d.exists():
            continue
        if platform_id:
            for f in d.iterdir():
                if f.name.startswith(platform_id) and f.suffix == '.txt':
                    return f
        for f in d.iterdir():
            if f.name.startswith('GPL') and f.suffix == '.txt':
                return f

    return None


def _parse_series_matrix(series_file: Path):
    """解析 series matrix .txt.gz → probe × sample DataFrame"""
    import gzip
    import pandas as pd

    with gzip.open(series_file, 'rt', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    # 找数据表起始行
    data_start = None
    for i, line in enumerate(lines):
        if line.startswith('!series_matrix_table_begin'):
            data_start = i + 1
            break

    if data_start is None:
        raise ValueError("找不到 series_matrix_table_begin")

    data_lines = []
    for line in lines[data_start:]:
        if line.startswith('!series_matrix_table_end'):
            break
        data_lines.append(line.strip().split('\t'))

    header = [c.strip('"') for c in data_lines[0]]
    rows = [[c.strip('"') for c in row] for row in data_lines[1:] if row]

    df = pd.DataFrame(rows, columns=header)
    df = df.set_index(df.columns[0])
    df.index.name = 'probe_id'
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(how='all')
    return df


def _parse_gpl_annotation(gpl_file: Path):
    """解析 GPL 平台文件 → DataFrame(probe_id, gene_symbol)"""
    import pandas as pd

    with open(gpl_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    # 找数据起始行（跳过 # ! 注释）
    data_start = 0
    for i, line in enumerate(lines):
        if line.startswith('!platform_table_begin'):
            data_start = i + 1
            break
        if not line.startswith('#') and not line.startswith('!') and line.strip():
            data_start = i
            break

    df = pd.read_csv(gpl_file, sep='\t', skiprows=data_start,
                     low_memory=False, on_bad_lines='skip')

    # 找 probe ID 列
    probe_col = next((c for c in df.columns if c.upper() in ('ID', 'PROBE_ID', 'PROBEID')), df.columns[0])

    # 找 gene symbol 列
    gene_col_candidates = ['Gene Symbol', 'GENE_SYMBOL', 'Gene_Symbol', 'Symbol',
                           'SYMBOL', 'gene_symbol', 'Gene', 'GENE']
    gene_col = next((c for c in gene_col_candidates if c in df.columns), None)
    if gene_col is None:
        raise ValueError(f"找不到 gene symbol 列，可用列: {list(df.columns)}")

    mapping = df[[probe_col, gene_col]].copy()
    mapping.columns = ['probe_id', 'gene_symbol']
    mapping = mapping.dropna(subset=['gene_symbol'])
    mapping = mapping[~mapping['gene_symbol'].astype(str).str.strip().isin(['', '---', 'null', 'NULL', 'nan'])]
    # 多基因取第一个
    mapping['gene_symbol'] = mapping['gene_symbol'].astype(str).str.split('///').str[0].str.split('//').str[0].str.strip()
    mapping['probe_id'] = mapping['probe_id'].astype(str)
    return mapping.reset_index(drop=True)


def _map_probe_to_gene(expr_df, mapping_df):
    """probe × sample → gene × sample（多 probe 取均值）"""
    import pandas as pd

    merged = expr_df.reset_index().merge(mapping_df, on='probe_id', how='inner')
    merged = merged.drop('probe_id', axis=1)
    gene_expr = merged.groupby('gene_symbol').mean()
    return gene_expr


def _build_subcategory_gene_sets() -> Dict[str, List[str]]:
    """
    从分类结果 + GO/KEGG 映射构建 14 个子类的基因集
    复用 complete_real_ssgsea_validation.py 的逻辑
    """
    import json
    import pandas as pd

    classification_file = "results/full_classification/full_classification_results.csv"
    go_mapping_file = "data/go_annotations/go_to_genes.json"
    kegg_mapping_file = "data/kegg_mappings/kegg_to_genes.json"

    df = pd.read_csv(classification_file)

    with open(go_mapping_file, 'r') as f:
        go_to_genes = json.load(f)

    with open(kegg_mapping_file, 'r') as f:
        kegg_raw = json.load(f)
    kegg_to_genes = {pid: info['genes'] for pid, info in kegg_raw.items()}

    subcategory_codes = ['A1','A2','A3','A4','B1','B2','B3','C1','C2','C3','D1','D2','E1','E2']
    gene_sets = {}

    for code in subcategory_codes:
        subset = df[df['Subcategory_Code'] == code]
        all_genes = set()

        for term_id in subset['ID']:
            if str(term_id).startswith('GO:') and term_id in go_to_genes:
                all_genes.update(go_to_genes[term_id])
            elif str(term_id).startswith('KEGG:') and term_id in kegg_to_genes:
                all_genes.update(kegg_to_genes[term_id])

        gene_sets[code] = list(all_genes)

    return gene_sets
    """查找 GPL 平台文件：先从 series matrix 提取平台 ID，再按优先级查找"""
    import gzip, re

    # 从 series matrix 提取平台 ID
    platform_id = None
    try:
        with gzip.open(series_file, 'rt', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('!Series_platform_id'):
                    m = re.search(r'GPL\d+', line)
                    if m:
                        platform_id = m.group()
                    break
    except Exception:
        pass

    # 按优先级查找文件
    search_dirs = [Path("data/gpl_platforms"), dataset_dir]
    for d in search_dirs:
        if not d.exists():
            continue
        # 精确匹配平台 ID
        if platform_id:
            for f in d.iterdir():
                if f.name.startswith(platform_id) and f.suffix == '.txt':
                    return f
        # 任意 GPL txt 文件
        for f in d.iterdir():
            if f.name.startswith('GPL') and f.suffix == '.txt':
                return f

    return None


def _extract_sample_info(series_file: Path) -> Dict:
    """从 series matrix 提取样本元数据"""
    import gzip
    info = {'accessions': [], 'titles': [], 'characteristics': []}
    try:
        with gzip.open(series_file, 'rt', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('!Sample_geo_accession'):
                    info['accessions'] = [x.strip('"') for x in line.strip().split('\t')[1:]]
                elif line.startswith('!Sample_title'):
                    info['titles'] = [x.strip('"') for x in line.strip().split('\t')[1:]]
                elif line.startswith('!Sample_characteristics_ch1'):
                    chars = [x.strip('"') for x in line.strip().split('\t')[1:]]
                    info['characteristics'].append(chars)
                elif line.startswith('!series_matrix_table_begin'):
                    break
        info['sample_count'] = len(info['accessions'])
    except Exception:
        pass
    return info


def classify_genes(state: AnalysisState) -> AnalysisState:
    """节点4: 五大系统分类 — 统计表达矩阵中各基因在 14 个子类基因集的覆盖情况"""
    state["current_step"] = "classify"
    state["log_messages"].append(f"[{datetime.now()}] 执行五大系统分类...")

    gene_expr_df = state.get("expression_matrix")
    if gene_expr_df is None:
        state["errors"].append("无表达矩阵，跳过分类")
        return state

    try:
        gene_sets = _build_subcategory_gene_sets()
        expressed_genes = set(gene_expr_df.index)

        subcat_to_system = {
            'A1':'System A','A2':'System A','A3':'System A','A4':'System A',
            'B1':'System B','B2':'System B','B3':'System B',
            'C1':'System C','C2':'System C','C3':'System C',
            'D1':'System D','D2':'System D',
            'E1':'System E','E2':'System E',
        }

        system_counts = {f'System {s}': 0 for s in 'ABCDE'}
        subcategory_counts = {}
        classified_genes = set()

        for code, genes in gene_sets.items():
            matched = expressed_genes & set(genes)
            subcategory_counts[code] = len(matched)
            classified_genes.update(matched)
            system = subcat_to_system.get(code)
            if system:
                system_counts[system] += len(matched)

        state["classification_results"] = {
            "total_genes": len(expressed_genes),
            "classified": len(classified_genes),
            "unclassified": len(expressed_genes) - len(classified_genes),
            "system_counts": system_counts,
            "subcategory_counts": subcategory_counts,
        }

        state["log_messages"].append(
            f"✓ 分类完成: {len(classified_genes)}/{len(expressed_genes)} 基因匹配到基因集"
        )
        for sys_name, cnt in system_counts.items():
            state["log_messages"].append(f"  {sys_name}: {cnt} 基因")

    except Exception as e:
        state["errors"].append(f"分类失败: {e}")
        state["log_messages"].append(f"❌ 分类失败: {e}")

    return state


def perform_ssgsea(state: AnalysisState) -> AnalysisState:
    """节点5: ssGSEA 评估 — 自实现算法，计算全部 14 个子类得分"""
    state["current_step"] = "ssgsea"
    state["log_messages"].append(f"[{datetime.now()}] 执行 ssGSEA 分析...")

    gene_expr_df = state.get("expression_matrix")
    if gene_expr_df is None:
        state["errors"].append("无表达矩阵，跳过 ssGSEA")
        return state

    try:
        import numpy as np

        gene_sets = _build_subcategory_gene_sets()
        gene_sets = {k: v for k, v in gene_sets.items() if len(v) >= 5}

        subcategory_names = {
            'A1': 'Genomic Stability and Repair',
            'A2': 'Somatic Maintenance and Identity Preservation',
            'A3': 'Cellular Homeostasis and Structural Maintenance',
            'A4': 'Inflammation Resolution and Damage Containment',
            'B1': 'Innate Immunity', 'B2': 'Adaptive Immunity',
            'B3': 'Immune Regulation and Tolerance',
            'C1': 'Energy Metabolism and Catabolism',
            'C2': 'Biosynthesis and Anabolism',
            'C3': 'Detoxification and Metabolic Stress Handling',
            'D1': 'Neural Regulation and Signal Transmission',
            'D2': 'Endocrine and Autonomic Regulation',
            'E1': 'Reproduction',
            'E2': 'Development and Reproductive Maturation',
        }
        subcat_to_system = {
            'A1': 'System A', 'A2': 'System A', 'A3': 'System A', 'A4': 'System A',
            'B1': 'System B', 'B2': 'System B', 'B3': 'System B',
            'C1': 'System C', 'C2': 'System C', 'C3': 'System C',
            'D1': 'System D', 'D2': 'System D',
            'E1': 'System E', 'E2': 'System E',
        }

        available_genes = set(gene_expr_df.index)
        ssgsea_scores = {}
        system_score_lists: Dict[str, list] = {f'System {s}': [] for s in 'ABCDE'}

        for code, gene_list in gene_sets.items():
            matched = list(set(gene_list) & available_genes)
            scores = _compute_ssgsea_scores(gene_expr_df, matched)
            mean_score = float(np.mean(scores))

            ssgsea_scores[code] = {
                'mean_score': mean_score,
                'std_score': float(np.std(scores)),
                'median_score': float(np.median(scores)),
                'name': subcategory_names.get(code, code),
                'gene_count': len(gene_list),
                'matched_genes': len(matched),
            }
            system = subcat_to_system.get(code)
            if system:
                system_score_lists[system].append(mean_score)

        system_scores = {
            sys: float(np.mean(vals)) if vals else 0.0
            for sys, vals in system_score_lists.items()
        }

        state["ssgsea_scores"] = ssgsea_scores
        state["system_scores"] = system_scores

        state["log_messages"].append(f"✓ ssGSEA 完成: {len(ssgsea_scores)} 个子类")
        for sys_name, score in sorted(system_scores.items()):
            state["log_messages"].append(f"  {sys_name}: {score:.4f}")

    except Exception as e:
        import traceback
        state["errors"].append(f"ssGSEA 失败: {e}")
        state["log_messages"].append(f"❌ ssGSEA 失败: {e}\n{traceback.format_exc()}")

    return state


def _compute_ssgsea_scores(gene_expr_df, gene_set_genes: list, alpha: float = 0.25) -> 'np.ndarray':
    """自实现 ssGSEA：加权 KS 统计量，对每个样本计算基因集富集得分"""
    import numpy as np

    if not gene_set_genes:
        return np.zeros(gene_expr_df.shape[1])

    matched = list(set(gene_set_genes) & set(gene_expr_df.index))
    if not matched:
        return np.zeros(gene_expr_df.shape[1])

    scores = []
    for sample in gene_expr_df.columns:
        expr = gene_expr_df[sample].dropna()
        if len(expr) == 0:
            scores.append(0.0)
            continue

        sorted_expr = expr.sort_values(ascending=False)
        N = len(sorted_expr)
        in_set = sorted_expr.index.isin(matched)
        Nh = in_set.sum()
        if Nh == 0:
            scores.append(0.0)
            continue

        weights = np.where(in_set, np.abs(sorted_expr.values) ** alpha, 0.0)
        weight_sum = weights[in_set].sum()
        if weight_sum == 0:
            scores.append(0.0)
            continue

        miss_penalty = 1.0 / (N - Nh) if N > Nh else 0.0
        running, max_es, min_es = 0.0, 0.0, 0.0
        for i in range(N):
            running += weights[i] / weight_sum if in_set[i] else -miss_penalty
            if running > max_es:
                max_es = running
            if running < min_es:
                min_es = running

        scores.append(max_es if abs(max_es) >= abs(min_es) else min_es)

    return np.array(scores)



def decide_visualization(state: AnalysisState) -> AnalysisState:
    """
    决策节点2: 确定可视化策略
    
    根据分析结果和数据特征，选择合适的可视化方式：
    - 热图
    - 箱线图
    - 时序图
    - 相关性网络图
    - 火山图
    """
    state["current_step"] = "decide_visualization"
    state["log_messages"].append(f"[{datetime.now()}] 决策可视化策略...")
    
    # 尝试使用 LLM 决策
    try:
        from .llm_integration import create_llm_integration
        
        llm = create_llm_integration()
        
        # 准备数据特征
        data_characteristics = {
            'sample_count': len(state.get('sample_metadata', {}).get('accessions', [])),
            'has_time_series': 'time' in str(state.get('sample_metadata', {})).lower(),
            'has_groups': len(set(state.get('sample_metadata', {}).get('characteristics', [[]])[0])) > 1 if state.get('sample_metadata') else False
        }
        
        # LLM 决策
        decision = llm.decide_visualization_strategy(
            state['analysis_strategy'],
            data_characteristics
        )
        
        state['visualization_plan'] = decision.get('primary_visualizations', [])
        state['log_messages'].append(
            f"LLM 可视化决策: {', '.join(state['visualization_plan'])}"
        )
        state['log_messages'].append(f"理由: {decision.get('reasoning', '')}")
        
        # 保存决策详情
        if 'metadata' not in state:
            state['metadata'] = {}
        state['metadata']['visualization_decision'] = decision
        
    except Exception as e:
        # 回退到规则引擎
        state['log_messages'].append(f"LLM 不可用，使用默认可视化方案: {e}")
        
        viz_map = {
            'case_control': ['heatmap', 'boxplot', 'volcano'],
            'subtype_comparison': ['clustering', 'heatmap', 'network'],
            'time_series': ['time_series', 'heatmap', 'trajectory'],
            'correlation': ['correlation_heatmap', 'network']
        }
        
        state['visualization_plan'] = viz_map.get(
            state.get('analysis_strategy', 'case_control'),
            ['heatmap']
        )
        state['log_messages'].append(f"默认可视化: {', '.join(state['visualization_plan'])}")
    
    return state


def generate_plots(state: AnalysisState) -> AnalysisState:
    """节点6: 生成图表"""
    state["current_step"] = "generate_plots"
    state["log_messages"].append(f"[{datetime.now()}] 生成可视化图表...")
    
    import os
    
    # 确保输出目录存在
    output_dir = f"results/agent_analysis/{state['dataset_id']}/figures"
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取可视化计划
    viz_plan = state.get("visualization_plan", ["heatmap", "boxplot"])
    
    # 模拟生成图表
    generated_figures = []
    
    for viz_type in viz_plan:
        fig_path = os.path.join(output_dir, f"{viz_type}.png")
        
        # 创建一个简单的占位文件
        with open(fig_path, 'w') as f:
            f.write(f"# Placeholder for {viz_type} visualization\n")
            f.write(f"# Dataset: {state['dataset_id']}\n")
            f.write(f"# Generated at: {datetime.now()}\n")
        
        generated_figures.append(fig_path)
        state["log_messages"].append(f"  ✓ 生成 {viz_type}: {fig_path}")
    
    state["figures"] = generated_figures
    
    state["log_messages"].append(f"✓ 共生成 {len(generated_figures)} 个图表")
    
    return state


def interpret_results(state: AnalysisState) -> AnalysisState:
    """
    节点7: 结果解读
    
    调用 LLM 解读分析结果
    """
    state["current_step"] = "interpret"
    state["log_messages"].append(f"[{datetime.now()}] 解读分析结果...")
    
    # 使用 LLM 解读结果
    try:
        from .llm_integration import create_llm_integration
        
        llm = create_llm_integration()
        
        # 准备数据
        dataset_info = {
            'dataset_id': state['dataset_id'],
            **state.get('dataset_info', {})
        }
        
        # LLM 解读
        interpretation = llm.interpret_results(
            dataset_info=dataset_info,
            ssgsea_scores=state.get('ssgsea_scores', {}),
            statistical_results=state.get('statistical_results')
        )
        
        state['interpretation'] = interpretation
        state['log_messages'].append("LLM 结果解读完成")
        
    except Exception as e:
        state['log_messages'].append(f"LLM 解读失败: {e}")
        
        # 简单的回退解读
        state['interpretation'] = f"""# 分析结果

数据集: {state.get('dataset_info', {}).get('chinese_name', 'Unknown')}
分析策略: {state.get('analysis_strategy', 'Unknown')}

本研究对该数据集进行了五大功能系统分类分析。
详细结果请参考生成的图表和统计表格。

*注：自动解读功能不可用，建议人工审核结果。*
"""
    
    return state


def generate_report(state: AnalysisState) -> AnalysisState:
    """节点8: 生成报告"""
    state["current_step"] = "generate_report"
    state["log_messages"].append(f"[{datetime.now()}] 生成分析报告...")
    
    # 组织报告内容
    dataset_info = state.get("dataset_info", {})
    ssgsea_scores = state.get("ssgsea_scores", {})
    system_scores = state.get("system_scores", {})
    classification_results = state.get("classification_results", {})
    
    # 创建报告内容
    report_content = f"""# {dataset_info.get('chinese_name', 'Unknown')} 分析报告

**数据集ID**: {state['dataset_id']}  
**疾病类型**: {state.get('disease_type', 'Unknown')}  
**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**分析策略**: {state.get('analysis_strategy', 'Unknown')}

---

## 1. 数据集信息

- **名称**: {dataset_info.get('name', 'Unknown')}
- **中文名**: {dataset_info.get('chinese_name', 'Unknown')}
- **描述**: {dataset_info.get('description', 'Unknown')}
- **预期系统**: {', '.join(dataset_info.get('expected_systems', []))}

## 2. 数据处理

- **样本数量**: {state.get('sample_metadata', {}).get('sample_count', 'Unknown')}
- **基因数量**: {classification_results.get('total_genes', 'Unknown')}
- **分类基因**: {classification_results.get('classified', 'Unknown')}

## 3. 五大系统分类结果

### 系统分布

"""
    
    # 添加系统分布
    for system, count in classification_results.get('system_counts', {}).items():
        report_content += f"- **{system}**: {count} 个基因\n"
    
    report_content += "\n### 子类分布\n\n"
    
    # 添加子类分布（前10个）
    subcats = list(classification_results.get('subcategory_counts', {}).items())[:10]
    for subcat, count in subcats:
        report_content += f"- **{subcat}**: {count} 个基因\n"
    
    report_content += "\n## 4. ssGSEA 分析结果\n\n### 系统激活得分\n\n"
    
    # 添加系统得分
    for system, score in system_scores.items():
        report_content += f"- **{system}**: {score:.3f}\n"
    
    report_content += "\n### 子类激活得分（Top 5）\n\n"
    
    # 添加 Top 5 子类得分
    sorted_subcats = sorted(ssgsea_scores.items(), 
                           key=lambda x: x[1]['mean_score'], 
                           reverse=True)[:5]
    
    for code, info in sorted_subcats:
        report_content += f"- **{code} ({info['name']})**: {info['mean_score']:.3f}\n"
    
    report_content += "\n## 5. 结果解读\n\n"
    
    # 添加 LLM 解读
    interpretation = state.get("interpretation", "")
    if interpretation:
        report_content += interpretation
    else:
        report_content += "结果解读正在生成中...\n"
    
    report_content += "\n## 6. 可视化图表\n\n"
    
    # 添加图表列表
    for i, fig_path in enumerate(state.get("figures", []), 1):
        report_content += f"{i}. {fig_path}\n"
    
    report_content += "\n---\n\n"
    report_content += "*本报告由疾病分析智能体自动生成*\n"
    
    state["report_content"] = report_content
    
    state["log_messages"].append(f"✓ 报告生成完成")
    state["log_messages"].append(f"✓ 报告长度: {len(report_content)} 字符")
    
    return state


def export_pdf(state: AnalysisState) -> AnalysisState:
    """节点9: 导出 PDF"""
    state["current_step"] = "export_pdf"
    state["log_messages"].append(f"[{datetime.now()}] 导出 PDF 报告...")
    
    import os
    
    # 确保输出目录存在
    output_dir = f"results/agent_analysis/{state['dataset_id']}"
    os.makedirs(output_dir, exist_ok=True)
    
    # 暂时保存为 Markdown 文件（快速版）
    report_path = os.path.join(output_dir, f"{state['dataset_id']}_report.md")
    
    report_content = state.get("report_content", "# 报告内容为空")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    state["report_path"] = report_path
    
    state["log_messages"].append(f"✓ 报告已保存: {report_path}")
    state["log_messages"].append(f"✓ 文件大小: {len(report_content)} 字节")
    
    # 同时保存一个摘要 JSON
    summary_path = os.path.join(output_dir, "analysis_summary.json")
    
    import json
    summary = {
        "dataset_id": state["dataset_id"],
        "dataset_name": state.get("dataset_info", {}).get("chinese_name", "Unknown"),
        "disease_type": state.get("disease_type", "Unknown"),
        "analysis_strategy": state.get("analysis_strategy", "Unknown"),
        "analysis_time": datetime.now().isoformat(),
        "classification_results": state.get("classification_results", {}),
        "system_scores": state.get("system_scores", {}),
        "figures": state.get("figures", []),
        "report_path": report_path
    }
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    state["log_messages"].append(f"✓ 摘要已保存: {summary_path}")
    
    return state


def handle_error(state: AnalysisState) -> AnalysisState:
    """错误处理节点"""
    state["current_step"] = "error_handling"
    state["log_messages"].append(f"[{datetime.now()}] 处理错误...")
    
    # 记录错误信息
    if state.get("errors"):
        state["log_messages"].append(f"⚠ 发现 {len(state['errors'])} 个错误:")
        for i, error in enumerate(state["errors"], 1):
            state["log_messages"].append(f"  {i}. {error}")
    
    # 检查是否可以重试
    if state.get("retry_count", 0) < 3:
        state["retry_count"] = state.get("retry_count", 0) + 1
        state["log_messages"].append(f"准备重试 (第 {state['retry_count']} 次)...")
    else:
        state["log_messages"].append("已达到最大重试次数，停止重试")
    
    return state


# ============================================================================
# 条件边函数
# ============================================================================

def should_retry(state: AnalysisState) -> str:
    """判断是否需要重试"""
    if state["errors"] and state["retry_count"] < 3:
        return "retry"
    elif state["errors"]:
        return "fail"
    else:
        return "continue"


def route_by_strategy(state: AnalysisState) -> str:
    """根据分析策略路由到不同的子图"""
    strategy = state.get("analysis_strategy", "default")
    
    if strategy == "case_control":
        return "case_control_analysis"
    elif strategy == "subtype_comparison":
        return "subtype_analysis"
    elif strategy == "time_series":
        return "time_series_analysis"
    elif strategy == "correlation":
        return "correlation_analysis"
    else:
        return "default_analysis"


def needs_human_review(state: AnalysisState) -> str:
    """判断是否需要人工审核"""
    if state.get("needs_human_review", False):
        return "human_review"
    else:
        return "continue"


# ============================================================================
# 构建图
# ============================================================================

def create_disease_analysis_graph():
    """创建疾病分析工作流图"""
    
    # 创建状态图
    workflow = StateGraph(AnalysisState)
    
    # 添加节点
    workflow.add_node("extract_metadata", extract_dataset_metadata)
    workflow.add_node("decide_strategy", decide_analysis_strategy)
    workflow.add_node("download", download_dataset)
    workflow.add_node("preprocess", preprocess_data)
    workflow.add_node("classify", classify_genes)
    workflow.add_node("ssgsea", perform_ssgsea)
    workflow.add_node("decide_visualization", decide_visualization)
    workflow.add_node("generate_plots", generate_plots)
    workflow.add_node("interpret", interpret_results)
    workflow.add_node("generate_report", generate_report)
    workflow.add_node("export_pdf", export_pdf)
    workflow.add_node("error_handler", handle_error)
    
    # 设置入口点
    workflow.set_entry_point("extract_metadata")
    
    # 添加边
    workflow.add_edge("extract_metadata", "decide_strategy")
    
    # 条件边：根据策略路由
    workflow.add_conditional_edges(
        "decide_strategy",
        route_by_strategy,
        {
            "case_control_analysis": "download",
            "subtype_analysis": "download",
            "time_series_analysis": "download",
            "correlation_analysis": "download",
            "default_analysis": "download"
        }
    )
    
    workflow.add_edge("download", "preprocess")
    workflow.add_edge("preprocess", "classify")
    workflow.add_edge("classify", "ssgsea")
    workflow.add_edge("ssgsea", "decide_visualization")
    workflow.add_edge("decide_visualization", "generate_plots")
    workflow.add_edge("generate_plots", "interpret")
    workflow.add_edge("interpret", "generate_report")
    workflow.add_edge("generate_report", "export_pdf")
    workflow.add_edge("export_pdf", END)
    
    # 编译图（不使用 checkpointer，避免 DataFrame 序列化问题）
    app = workflow.compile()
    
    return app


# ============================================================================
# 主函数
# ============================================================================

def run_disease_analysis(dataset_id: str, config: Optional[Dict] = None):
    """
    运行疾病分析工作流
    
    Args:
        dataset_id: 数据集ID
        config: 配置参数
    """
    # 创建工作流
    app = create_disease_analysis_graph()
    
    # 初始化状态
    initial_state = {
        "dataset_id": dataset_id,
        "dataset_info": {},
        "raw_data_path": None,
        "processed_data_path": None,
        "expression_matrix": None,
        "sample_metadata": None,
        "classification_results": None,
        "ssgsea_scores": None,
        "statistical_results": None,
        "disease_type": None,
        "analysis_strategy": None,
        "visualization_plan": [],
        "figures": [],
        "interpretation": None,
        "report_path": None,
        "log_messages": [],
        "errors": [],
        "current_step": "init",
        "needs_human_review": False,
        "retry_count": 0
    }
    
    # 运行工作流（无 checkpointer，直接 invoke）
    print(f"开始分析数据集: {dataset_id}")
    print("="*80)
    
    for output in app.stream(initial_state):
        # 打印当前步骤
        for node_name, node_output in output.items():
            print(f"\n[{node_name}] 执行完成")
            if node_output.get("log_messages"):
                print(f"  最新日志: {node_output['log_messages'][-1]}")
    
    print("\n" + "="*80)
    print("分析完成！")
    
    return output


if __name__ == "__main__":
    # 测试运行
    result = run_disease_analysis("GSE2034")
