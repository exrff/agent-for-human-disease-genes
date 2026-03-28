#!/usr/bin/env python3
"""Runtime configuration for the active agent pipeline."""

from pathlib import Path
from typing import Any, Dict

from .whitelist_repository import get_dataset_info, load_whitelist_datasets


class AgentConfig:
    """Active configuration surface used by the current pipeline."""

    @classmethod
    def get_all_datasets(cls) -> Dict[str, Any]:
        return load_whitelist_datasets()

    STRATEGY_RULES = {
        "neurodegenerative": {
            "primary_strategy": "case_control",
            "secondary_analyses": ["correlation"],
            "key_systems": ["D", "A"],
            "visualization": ["heatmap", "boxplot", "volcano"],
        },
        "cancer": {
            "primary_strategy": "subtype_comparison",
            "secondary_analyses": ["correlation", "survival"],
            "key_systems": ["A", "B", "E"],
            "visualization": ["clustering", "heatmap", "network"],
        },
        "metabolic": {
            "primary_strategy": "case_control",
            "secondary_analyses": ["correlation"],
            "key_systems": ["C", "D"],
            "visualization": ["heatmap", "boxplot", "pathway"],
        },
        "repair": {
            "primary_strategy": "time_series",
            "secondary_analyses": ["correlation"],
            "key_systems": ["A", "B"],
            "visualization": ["time_series", "heatmap", "trajectory"],
        },
        "infection": {
            "primary_strategy": "case_control",
            "secondary_analyses": ["time_series"],
            "key_systems": ["B", "C"],
            "visualization": ["heatmap", "boxplot", "immune_profile"],
        },
        "autoimmune": {
            "primary_strategy": "case_control",
            "secondary_analyses": ["correlation"],
            "key_systems": ["B", "A"],
            "visualization": ["heatmap", "boxplot", "immune_profile"],
        },
        "cardiovascular": {
            "primary_strategy": "case_control",
            "secondary_analyses": ["correlation"],
            "key_systems": ["C", "A", "D"],
            "visualization": ["heatmap", "boxplot", "pathway"],
        },
        "psychiatric": {
            "primary_strategy": "case_control",
            "secondary_analyses": ["correlation"],
            "key_systems": ["D", "B"],
            "visualization": ["heatmap", "boxplot"],
        },
        "respiratory": {
            "primary_strategy": "case_control",
            "secondary_analyses": ["correlation"],
            "key_systems": ["B", "C"],
            "visualization": ["heatmap", "boxplot"],
        },
        "liver": {
            "primary_strategy": "case_control",
            "secondary_analyses": ["correlation"],
            "key_systems": ["C", "A"],
            "visualization": ["heatmap", "boxplot", "pathway"],
        },
    }

    DATA_DIR = Path("data/validation_datasets")
    RESULTS_DIR = Path("results/agent_analysis")
    FIGURES_DIR = Path("results/agent_analysis/figures")
    REPORTS_DIR = Path("results/agent_analysis/reports")
    LOGS_DIR = Path("logs/agent")

    SSGSEA_PARAMS = {
        "alpha": 0.25,
        "min_gene_overlap": 5,
        "normalize": True,
    }

    STATISTICAL_PARAMS = {
        "alpha": 0.05,
        "fdr_method": "fdr_bh",
        "min_fold_change": 1.5,
    }

    LLM_CONFIG = {
        "provider": "dashscope",
        "model": "qwen3.5-122b-a10b",
        "temperature": 0.3,
        "max_tokens": 2000,
        "api_key_env": "DASHSCOPE_API_KEY",
    }

    LLM_FALLBACK_CONFIG = {
        "provider": "google",
        "model": "gemini-pro",
        "api_key_env": "GOOGLE_API_KEY",
    }

    @classmethod
    def get_dataset_config(cls, dataset_id: str) -> Dict[str, Any]:
        return get_dataset_info(dataset_id) or {}

    @classmethod
    def get_strategy_config(cls, disease_type: str) -> Dict[str, Any]:
        return cls.STRATEGY_RULES.get(disease_type, cls.STRATEGY_RULES["metabolic"])

    @classmethod
    def ensure_directories(cls):
        for dir_path in [cls.RESULTS_DIR, cls.FIGURES_DIR, cls.REPORTS_DIR, cls.LOGS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
