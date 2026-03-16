#!/usr/bin/env python3
"""
智能体配置
"""

from typing import Dict, Any
from pathlib import Path


class AgentConfig:
    """智能体配置类"""

    # -----------------------------------------------------------------------
    # 数据集白名单
    # 所有条目均为人类(Homo sapiens)基因表达谱、非SuperSeries、样本数≥20。
    # LLM 只能从此列表中选择，不允许自由推荐 GEO 编号。
    # -----------------------------------------------------------------------
    DATASETS = {

        # ── 已完成手动分析（7个）──────────────────────────────────────────
        'GSE122063': {
            'name': 'Alzheimer Disease',
            'chinese_name': '阿尔兹海默症',
            'disease_type': 'neurodegenerative',
            'expected_strategy': 'case_control',
            'expected_systems': ['System D', 'System A'],
            'description': '神经退行性疾病，预期激活神经调节和修复系统',
            'platform': 'GPL570', 'n_samples': 84,
        },
        'GSE2034': {
            'name': 'Breast Cancer',
            'chinese_name': '乳腺癌',
            'disease_type': 'cancer',
            'expected_strategy': 'subtype_comparison',
            'expected_systems': ['System A', 'System B', 'System E'],
            'description': '乳腺癌预后研究，286例淋巴结阴性患者',
            'platform': 'GPL96', 'n_samples': 286,
        },
        'GSE26168': {
            'name': 'Type 2 Diabetes',
            'chinese_name': '2型糖尿病',
            'disease_type': 'metabolic',
            'expected_strategy': 'case_control',
            'expected_systems': ['System C', 'System D'],
            'description': '2型糖尿病骨骼肌基因表达，代谢和调节系统',
            'platform': 'GPL570', 'n_samples': 40,
        },
        'GSE21899': {
            'name': 'Gaucher Disease',
            'chinese_name': '戈谢病',
            'disease_type': 'metabolic',
            'expected_strategy': 'case_control',
            'expected_systems': ['System C', 'System D'],
            'description': '溶酶体贮积病，预期激活代谢系统',
            'platform': 'GPL570', 'n_samples': 30,
        },
        'GSE28914': {
            'name': 'Wound Healing',
            'chinese_name': '伤口愈合',
            'disease_type': 'repair',
            'expected_strategy': 'time_series',
            'expected_systems': ['System A', 'System B'],
            'description': '皮肤伤口愈合时序研究，修复和免疫系统',
            'platform': 'GPL570', 'n_samples': 46,
        },
        'GSE50425': {
            'name': 'Wound Healing Extended',
            'chinese_name': '伤口愈合扩展',
            'disease_type': 'repair',
            'expected_strategy': 'time_series',
            'expected_systems': ['System A', 'System B'],
            'description': '扩展伤口愈合研究，多时间点采样',
            'platform': 'GPL4133', 'n_samples': 60,
        },
        'GSE65682': {
            'name': 'Sepsis',
            'chinese_name': '脓毒症',
            'disease_type': 'infection',
            'expected_strategy': 'case_control',
            'expected_systems': ['System B', 'System C'],
            'description': '脓毒症全血基因表达，免疫和代谢系统',
            'platform': 'GPL570', 'n_samples': 479,
        },

        # ── 自身免疫性疾病 ────────────────────────────────────────────────
        'GSE10325': {
            'name': 'Systemic Lupus Erythematosus',
            'chinese_name': '系统性红斑狼疮',
            'disease_type': 'autoimmune',
            'expected_strategy': 'case_control',
            'expected_systems': ['System B', 'System A'],
            'description': 'SLE外周血单核细胞，免疫失调与炎症',
            'platform': 'GPL570', 'n_samples': 62,
        },
        'GSE93272': {
            'name': 'Rheumatoid Arthritis',
            'chinese_name': '类风湿关节炎',
            'disease_type': 'autoimmune',
            'expected_strategy': 'case_control',
            'expected_systems': ['System B', 'System A', 'System C'],
            'description': '类风湿关节炎滑膜组织，免疫激活与代谢重编程',
            'platform': 'GPL570', 'n_samples': 80,
        },
        'GSE37463': {
            'name': 'Multiple Sclerosis',
            'chinese_name': '多发性硬化症',
            'disease_type': 'autoimmune',
            'expected_strategy': 'case_control',
            'expected_systems': ['System B', 'System D', 'System A'],
            'description': '多发性硬化症外周血，神经免疫轴',
            'platform': 'GPL6244', 'n_samples': 140,
        },

        # ── 心血管疾病 ────────────────────────────────────────────────────
        'GSE57338': {
            'name': 'Heart Failure',
            'chinese_name': '心力衰竭',
            'disease_type': 'cardiovascular',
            'expected_strategy': 'case_control',
            'expected_systems': ['System C', 'System A', 'System D'],
            'description': '终末期心力衰竭心肌组织，能量代谢与修复',
            'platform': 'GPL570', 'n_samples': 177,
        },
        'GSE12288': {
            'name': 'Coronary Artery Disease',
            'chinese_name': '冠状动脉疾病',
            'disease_type': 'cardiovascular',
            'expected_strategy': 'case_control',
            'expected_systems': ['System C', 'System B', 'System A'],
            'description': '冠心病外周血，炎症与代谢失调',
            'platform': 'GPL96', 'n_samples': 196,
        },

        # ── 神经退行性疾病 ────────────────────────────────────────────────
        'GSE5281': {
            'name': 'Alzheimer Disease Brain Regions',
            'chinese_name': '阿尔兹海默症脑区',
            'disease_type': 'neurodegenerative',
            'expected_strategy': 'case_control',
            'expected_systems': ['System D', 'System A', 'System C'],
            'description': '阿尔兹海默症六个脑区基因表达，神经退行机制',
            'platform': 'GPL570', 'n_samples': 161,
        },
        'GSE8397': {
            'name': 'Parkinson Disease',
            'chinese_name': '帕金森病',
            'disease_type': 'neurodegenerative',
            'expected_strategy': 'case_control',
            'expected_systems': ['System D', 'System A'],
            'description': '帕金森病黑质基因表达，神经调节与修复',
            'platform': 'GPL570', 'n_samples': 47,
        },

        # ── 代谢性疾病 ────────────────────────────────────────────────────
        'GSE15653': {
            'name': 'Non-alcoholic Fatty Liver Disease',
            'chinese_name': '非酒精性脂肪肝',
            'disease_type': 'metabolic',
            'expected_strategy': 'case_control',
            'expected_systems': ['System C', 'System A'],
            'description': 'NAFLD肝脏活检，脂质代谢与氧化应激',
            'platform': 'GPL570', 'n_samples': 40,
        },
        'GSE23343': {
            'name': 'Chronic Kidney Disease',
            'chinese_name': '慢性肾病',
            'disease_type': 'metabolic',
            'expected_strategy': 'case_control',
            'expected_systems': ['System C', 'System D', 'System A'],
            'description': '慢性肾病肾小管，代谢紊乱与纤维化',
            'platform': 'GPL570', 'n_samples': 51,
        },

        # ── 呼吸系统疾病 ──────────────────────────────────────────────────
        'GSE47460': {
            'name': 'Chronic Obstructive Pulmonary Disease',
            'chinese_name': '慢性阻塞性肺病',
            'disease_type': 'respiratory',
            'expected_strategy': 'case_control',
            'expected_systems': ['System B', 'System C', 'System A'],
            'description': 'COPD肺组织，炎症与代谢重塑',
            'platform': 'GPL14550', 'n_samples': 136,
        },
        'GSE41861': {
            'name': 'Asthma',
            'chinese_name': '哮喘',
            'disease_type': 'respiratory',
            'expected_strategy': 'case_control',
            'expected_systems': ['System B', 'System A'],
            'description': '哮喘支气管活检，免疫激活与气道炎症',
            'platform': 'GPL6244', 'n_samples': 43,
        },

        # ── 精神疾病 ──────────────────────────────────────────────────────
        'GSE53987': {
            'name': 'Schizophrenia',
            'chinese_name': '精神分裂症',
            'disease_type': 'psychiatric',
            'expected_strategy': 'case_control',
            'expected_systems': ['System D', 'System C'],
            'description': '精神分裂症前额叶皮层，神经信号与代谢',
            'platform': 'GPL570', 'n_samples': 99,
        },
        'GSE98793': {
            'name': 'Major Depressive Disorder',
            'chinese_name': '重度抑郁症',
            'disease_type': 'psychiatric',
            'expected_strategy': 'case_control',
            'expected_systems': ['System D', 'System B'],
            'description': '重度抑郁症外周血，神经内分泌与免疫轴',
            'platform': 'GPL10558', 'n_samples': 128,
        },

        # ── 癌症 ──────────────────────────────────────────────────────────
        'GSE19804': {
            'name': 'Lung Cancer',
            'chinese_name': '肺癌',
            'disease_type': 'cancer',
            'expected_strategy': 'subtype_comparison',
            'expected_systems': ['System A', 'System B', 'System C'],
            'description': '非小细胞肺癌，修复缺陷与免疫逃逸',
            'platform': 'GPL570', 'n_samples': 120,
        },
        'GSE14520': {
            'name': 'Hepatocellular Carcinoma',
            'chinese_name': '肝细胞癌',
            'disease_type': 'cancer',
            'expected_strategy': 'subtype_comparison',
            'expected_systems': ['System A', 'System C', 'System B'],
            'description': '肝细胞癌配对癌与癌旁组织，代谢重编程',
            'platform': 'GPL571', 'n_samples': 445,
        },
        'GSE9891': {
            'name': 'Ovarian Cancer',
            'chinese_name': '卵巢癌',
            'disease_type': 'cancer',
            'expected_strategy': 'subtype_comparison',
            'expected_systems': ['System A', 'System E', 'System B'],
            'description': '卵巢癌分子亚型，生殖发育与修复系统',
            'platform': 'GPL570', 'n_samples': 285,
        },

        # ── 感染性疾病 ────────────────────────────────────────────────────
        'GSE42026': {
            'name': 'Tuberculosis',
            'chinese_name': '结核病',
            'disease_type': 'infection',
            'expected_strategy': 'case_control',
            'expected_systems': ['System B', 'System A'],
            'description': '活动性结核病外周血，先天免疫与适应性免疫',
            'platform': 'GPL96', 'n_samples': 94,
        },
        'GSE73072': {
            'name': 'Influenza Infection',
            'chinese_name': '流感病毒感染',
            'disease_type': 'infection',
            'expected_strategy': 'time_series',
            'expected_systems': ['System B', 'System A', 'System C'],
            'description': '流感病毒感染时序，先天免疫应答动态',
            'platform': 'GPL10558', 'n_samples': 131,
        },

        # ── 肝脏疾病 ──────────────────────────────────────────────────────
        'GSE84044': {
            'name': 'Liver Cirrhosis',
            'chinese_name': '肝硬化',
            'disease_type': 'liver',
            'expected_strategy': 'case_control',
            'expected_systems': ['System C', 'System A', 'System B'],
            'description': '肝硬化肝组织，纤维化与代谢失调',
            'platform': 'GPL570', 'n_samples': 60,
        },

    }  # end DATASETS

    @classmethod
    def get_all_datasets(cls) -> Dict[str, Any]:
        """
        返回完整数据集字典：核心白名单 + data/geo_whitelist.csv 中的条目。
        CSV 中已存在于 DATASETS 的条目会被跳过（核心白名单优先）。
        """
        import ast
        import csv as _csv

        merged = dict(cls.DATASETS)  # 核心白名单优先

        csv_path = Path("data/geo_whitelist.csv")
        if not csv_path.exists():
            return merged

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = _csv.DictReader(f)
                for row in reader:
                    gse_id = row.get('dataset_id', '').strip()
                    if not gse_id or gse_id in merged:
                        continue
                    # expected_systems 存储为 Python list repr，需要解析
                    try:
                        systems = ast.literal_eval(row.get('expected_systems', "[]"))
                    except Exception:
                        systems = ['System A', 'System B']
                    try:
                        n_samples = int(row.get('n_samples') or 0)
                    except ValueError:
                        n_samples = 0
                    merged[gse_id] = {
                        'name':              row.get('name', ''),
                        'chinese_name':      row.get('chinese_name', row.get('name', '')),
                        'disease_type':      row.get('disease_type', 'other'),
                        'expected_strategy': row.get('expected_strategy', 'case_control'),
                        'expected_systems':  systems,
                        'description':       row.get('description', ''),
                        'platform':          row.get('platform', ''),
                        'n_samples':         n_samples,
                    }
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"读取 geo_whitelist.csv 失败: {e}")

        return merged

    # 分析策略映射
    STRATEGY_RULES = {
        'neurodegenerative': {
            'primary_strategy': 'case_control',
            'secondary_analyses': ['correlation'],
            'key_systems': ['D', 'A'],
            'visualization': ['heatmap', 'boxplot', 'volcano']
        },
        'cancer': {
            'primary_strategy': 'subtype_comparison',
            'secondary_analyses': ['correlation', 'survival'],
            'key_systems': ['A', 'B', 'E'],
            'visualization': ['clustering', 'heatmap', 'network']
        },
        'metabolic': {
            'primary_strategy': 'case_control',
            'secondary_analyses': ['correlation'],
            'key_systems': ['C', 'D'],
            'visualization': ['heatmap', 'boxplot', 'pathway']
        },
        'repair': {
            'primary_strategy': 'time_series',
            'secondary_analyses': ['correlation'],
            'key_systems': ['A', 'B'],
            'visualization': ['time_series', 'heatmap', 'trajectory']
        },
        'infection': {
            'primary_strategy': 'case_control',
            'secondary_analyses': ['time_series'],
            'key_systems': ['B', 'C'],
            'visualization': ['heatmap', 'boxplot', 'immune_profile']
        },
        'autoimmune': {
            'primary_strategy': 'case_control',
            'secondary_analyses': ['correlation'],
            'key_systems': ['B', 'A'],
            'visualization': ['heatmap', 'boxplot', 'immune_profile']
        },
        'cardiovascular': {
            'primary_strategy': 'case_control',
            'secondary_analyses': ['correlation'],
            'key_systems': ['C', 'A', 'D'],
            'visualization': ['heatmap', 'boxplot', 'pathway']
        },
        'psychiatric': {
            'primary_strategy': 'case_control',
            'secondary_analyses': ['correlation'],
            'key_systems': ['D', 'B'],
            'visualization': ['heatmap', 'boxplot']
        },
        'respiratory': {
            'primary_strategy': 'case_control',
            'secondary_analyses': ['correlation'],
            'key_systems': ['B', 'C'],
            'visualization': ['heatmap', 'boxplot']
        },
        'liver': {
            'primary_strategy': 'case_control',
            'secondary_analyses': ['correlation'],
            'key_systems': ['C', 'A'],
            'visualization': ['heatmap', 'boxplot', 'pathway']
        },
    }

    # 路径配置
    DATA_DIR = Path("data/validation_datasets")
    RESULTS_DIR = Path("results/agent_analysis")
    FIGURES_DIR = Path("results/agent_analysis/figures")
    REPORTS_DIR = Path("results/agent_analysis/reports")
    LOGS_DIR = Path("logs/agent")

    # 分析参数
    SSGSEA_PARAMS = {
        'alpha': 0.25,
        'min_gene_overlap': 5,
        'normalize': True
    }

    STATISTICAL_PARAMS = {
        'alpha': 0.05,
        'fdr_method': 'fdr_bh',
        'min_fold_change': 1.5
    }

    # LLM 配置
    LLM_CONFIG = {
        'provider': 'dashscope',
        'model': 'qwen3.5-122b-a10b',
        'temperature': 0.3,
        'max_tokens': 2000,
        'api_key_env': 'DASHSCOPE_API_KEY'
    }

    LLM_FALLBACK_CONFIG = {
        'provider': 'google',
        'model': 'gemini-pro',
        'api_key_env': 'GOOGLE_API_KEY'
    }

    @classmethod
    def get_dataset_config(cls, dataset_id: str) -> Dict[str, Any]:
        """获取数据集配置"""
        return cls.DATASETS.get(dataset_id, {})

    @classmethod
    def get_strategy_config(cls, disease_type: str) -> Dict[str, Any]:
        """获取分析策略配置"""
        return cls.STRATEGY_RULES.get(disease_type, cls.STRATEGY_RULES['metabolic'])

    @classmethod
    def ensure_directories(cls):
        """确保所有必要的目录存在"""
        for dir_path in [cls.RESULTS_DIR, cls.FIGURES_DIR, cls.REPORTS_DIR, cls.LOGS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
