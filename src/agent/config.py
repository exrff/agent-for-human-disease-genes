#!/usr/bin/env python3
"""
智能体配置
"""

from typing import Dict, Any
from pathlib import Path


class AgentConfig:
    """智能体配置类"""
    
    # 数据集配置
    DATASETS = {
        'GSE122063': {
            'name': 'Alzheimer Disease',
            'chinese_name': '阿尔兹海默症',
            'disease_type': 'neurodegenerative',
            'expected_strategy': 'case_control',
            'expected_systems': ['System D', 'System A'],
            'description': '神经退行性疾病，预期激活神经调节和修复系统'
        },
        'GSE2034': {
            'name': 'Breast Cancer',
            'chinese_name': '乳腺癌',
            'disease_type': 'cancer',
            'expected_strategy': 'subtype_comparison',
            'expected_systems': ['System A', 'System B', 'System E'],
            'description': '癌症，预期激活修复、免疫和发育系统'
        },
        'GSE26168': {
            'name': 'Diabetes',
            'chinese_name': '糖尿病',
            'disease_type': 'metabolic',
            'expected_strategy': 'case_control',
            'expected_systems': ['System C', 'System D'],
            'description': '代谢疾病，预期激活代谢和调节系统'
        },
        'GSE21899': {
            'name': 'Gaucher Disease',
            'chinese_name': '戈谢病',
            'disease_type': 'metabolic',
            'expected_strategy': 'case_control',
            'expected_systems': ['System C', 'System D'],
            'description': '溶酶体贮积病，预期激活代谢系统'
        },
        'GSE28914': {
            'name': 'Wound Healing',
            'chinese_name': '伤口愈合',
            'disease_type': 'repair',
            'expected_strategy': 'time_series',
            'expected_systems': ['System A', 'System B'],
            'description': '伤口愈合，预期激活修复和免疫系统'
        },
        'GSE50425': {
            'name': 'Wound Healing Extended',
            'chinese_name': '伤口愈合扩展',
            'disease_type': 'repair',
            'expected_strategy': 'time_series',
            'expected_systems': ['System A', 'System B'],
            'description': '扩展伤口愈合研究'
        },
        'GSE65682': {
            'name': 'Sepsis',
            'chinese_name': '脓毒症',
            'disease_type': 'infection',
            'expected_strategy': 'case_control',
            'expected_systems': ['System B', 'System C'],
            'description': '脓毒症，预期激活免疫和代谢系统'
        }
    }
    
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
        }
    }
    
    # 可视化配置
    VISUALIZATION_TEMPLATES = {
        'heatmap': {
            'function': 'generate_heatmap',
            'params': {'figsize': (12, 8), 'cmap': 'RdBu_r'}
        },
        'boxplot': {
            'function': 'generate_comparison_boxplot',
            'params': {'figsize': (12, 8)}
        },
        'volcano': {
            'function': 'generate_volcano_plot',
            'params': {'figsize': (10, 8)}
        },
        'time_series': {
            'function': 'generate_time_series_plot',
            'params': {'figsize': (12, 8)}
        },
        'clustering': {
            'function': 'generate_clustering_plot',
            'params': {'figsize': (12, 10)}
        },
        'network': {
            'function': 'generate_network_plot',
            'params': {'figsize': (14, 14)}
        }
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
    
    # LLM 配置（用于结果解读）
    LLM_CONFIG = {
        'provider': 'dashscope',  # 使用阿里云百炼 DashScope
        'model': 'qwen-plus',  # 可选: qwen-plus, qwen-turbo, qwen-max, qwen2.5-72b-instruct
        'temperature': 0.3,
        'max_tokens': 2000,
        'api_key_env': 'DASHSCOPE_API_KEY'  # 环境变量名
    }
    
    # 备用 LLM 配置（如果主要的失败）
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
