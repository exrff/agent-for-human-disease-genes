"""
系统设置和配置管理

定义了五大功能系统分类研究的全局配置参数。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from pathlib import Path
import os


@dataclass
class Settings:
    """
    系统全局设置
    
    包含数据路径、分类参数、验证设置等配置信息。
    """
    
    # 数据路径配置
    data_dir: Path = field(default_factory=lambda: Path("data"))
    ontology_dir: Path = field(default_factory=lambda: Path("data/ontology"))
    validation_dir: Path = field(default_factory=lambda: Path("data/validation_datasets"))
    results_dir: Path = field(default_factory=lambda: Path("results"))
    
    # GO本体文件配置
    go_basic_file: str = "go-basic.txt"
    go_obo_file: str = "go-basic.obo"
    
    # KEGG层次文件配置
    kegg_hierarchy_file: str = "br_br08901.txt"
    
    # 分类参数配置
    min_confidence_threshold: float = 0.5
    enable_subsystem_classification: bool = True
    enable_inflammation_annotation: bool = True
    
    # GO条目过滤配置
    go_namespaces: Set[str] = field(default_factory=lambda: {"biological_process"})
    exclude_obsolete_terms: bool = True
    exclude_general_terms: bool = True
    general_term_patterns: List[str] = field(default_factory=lambda: [
        r"biological_process",
        r"cellular_process", 
        r"metabolic_process",
        r"regulation of",
        r"positive regulation of",
        r"negative regulation of"
    ])
    
    # 语义相似度计算配置
    semantic_similarity_method: str = "resnik"  # resnik, lin, jiang_conrath
    similarity_cache_size: int = 10000
    
    # ssGSEA验证配置
    ssgsea_min_gene_set_size: int = 5
    ssgsea_max_gene_set_size: int = 500
    ssgsea_permutations: int = 1000
    
    # 统计检验配置
    statistical_alpha: float = 0.05
    multiple_testing_correction: str = "fdr_bh"  # bonferroni, fdr_bh, fdr_by
    
    # 性能配置
    enable_parallel_processing: bool = True
    max_workers: Optional[int] = None  # None表示使用CPU核心数
    batch_size: int = 1000
    
    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = "classification.log"
    
    # 输出格式配置
    output_formats: List[str] = field(default_factory=lambda: ["csv", "json"])
    include_decision_path: bool = True
    include_metadata: bool = True
    
    def __post_init__(self):
        """配置验证和后处理"""
        # 确保路径是Path对象
        if isinstance(self.data_dir, str):
            self.data_dir = Path(self.data_dir)
        if isinstance(self.ontology_dir, str):
            self.ontology_dir = Path(self.ontology_dir)
        if isinstance(self.validation_dir, str):
            self.validation_dir = Path(self.validation_dir)
        if isinstance(self.results_dir, str):
            self.results_dir = Path(self.results_dir)
        
        # 验证置信度阈值
        if not 0 <= self.min_confidence_threshold <= 1:
            raise ValueError("min_confidence_threshold must be between 0 and 1")
        
        # 验证统计显著性水平
        if not 0 < self.statistical_alpha < 1:
            raise ValueError("statistical_alpha must be between 0 and 1")
        
        # 验证语义相似度方法
        valid_methods = ["resnik", "lin", "jiang_conrath", "path"]
        if self.semantic_similarity_method not in valid_methods:
            raise ValueError(f"semantic_similarity_method must be one of {valid_methods}")
        
        # 验证多重检验校正方法
        valid_corrections = ["bonferroni", "fdr_bh", "fdr_by", "none"]
        if self.multiple_testing_correction not in valid_corrections:
            raise ValueError(f"multiple_testing_correction must be one of {valid_corrections}")
    
    def get_go_basic_path(self) -> Path:
        """获取GO基础文件路径"""
        return self.ontology_dir / self.go_basic_file
    
    def get_go_obo_path(self) -> Path:
        """获取GO OBO文件路径"""
        return self.ontology_dir / self.go_obo_file
    
    def get_kegg_hierarchy_path(self) -> Path:
        """获取KEGG层次文件路径"""
        return self.ontology_dir / self.kegg_hierarchy_file
    
    def get_validation_dataset_path(self, dataset_name: str) -> Path:
        """获取验证数据集路径"""
        return self.validation_dir / dataset_name
    
    def get_results_path(self, subdir: str = "") -> Path:
        """获取结果输出路径"""
        if subdir:
            return self.results_dir / subdir
        return self.results_dir
    
    def create_directories(self):
        """创建必要的目录"""
        directories = [
            self.data_dir,
            self.ontology_dir,
            self.validation_dir,
            self.results_dir,
            self.results_dir / "classification",
            self.results_dir / "validation",
            self.results_dir / "reports",
            self.results_dir / "figures"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'data_dir': str(self.data_dir),
            'ontology_dir': str(self.ontology_dir),
            'validation_dir': str(self.validation_dir),
            'results_dir': str(self.results_dir),
            'go_basic_file': self.go_basic_file,
            'go_obo_file': self.go_obo_file,
            'kegg_hierarchy_file': self.kegg_hierarchy_file,
            'min_confidence_threshold': self.min_confidence_threshold,
            'enable_subsystem_classification': self.enable_subsystem_classification,
            'enable_inflammation_annotation': self.enable_inflammation_annotation,
            'go_namespaces': list(self.go_namespaces),
            'exclude_obsolete_terms': self.exclude_obsolete_terms,
            'exclude_general_terms': self.exclude_general_terms,
            'general_term_patterns': self.general_term_patterns,
            'semantic_similarity_method': self.semantic_similarity_method,
            'similarity_cache_size': self.similarity_cache_size,
            'ssgsea_min_gene_set_size': self.ssgsea_min_gene_set_size,
            'ssgsea_max_gene_set_size': self.ssgsea_max_gene_set_size,
            'ssgsea_permutations': self.ssgsea_permutations,
            'statistical_alpha': self.statistical_alpha,
            'multiple_testing_correction': self.multiple_testing_correction,
            'enable_parallel_processing': self.enable_parallel_processing,
            'max_workers': self.max_workers,
            'batch_size': self.batch_size,
            'log_level': self.log_level,
            'log_file': self.log_file,
            'output_formats': self.output_formats,
            'include_decision_path': self.include_decision_path,
            'include_metadata': self.include_metadata
        }


# 全局设置实例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局设置实例"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def update_settings(**kwargs) -> Settings:
    """更新全局设置"""
    global _settings
    current_settings = get_settings()
    
    # 创建新的设置实例
    settings_dict = current_settings.to_dict()
    settings_dict.update(kwargs)
    
    # 处理路径参数
    for key in ['data_dir', 'ontology_dir', 'validation_dir', 'results_dir']:
        if key in settings_dict:
            settings_dict[key] = Path(settings_dict[key])
    
    # 处理集合参数
    if 'go_namespaces' in settings_dict:
        settings_dict['go_namespaces'] = set(settings_dict['go_namespaces'])
    
    _settings = Settings(**{k: v for k, v in settings_dict.items() 
                           if k in Settings.__dataclass_fields__})
    return _settings


def load_settings_from_env():
    """从环境变量加载设置"""
    env_settings = {}
    
    # 路径配置
    if os.getenv('DATA_DIR'):
        env_settings['data_dir'] = Path(os.getenv('DATA_DIR'))
    if os.getenv('RESULTS_DIR'):
        env_settings['results_dir'] = Path(os.getenv('RESULTS_DIR'))
    
    # 分类参数
    if os.getenv('MIN_CONFIDENCE_THRESHOLD'):
        env_settings['min_confidence_threshold'] = float(os.getenv('MIN_CONFIDENCE_THRESHOLD'))
    
    # 性能配置
    if os.getenv('MAX_WORKERS'):
        env_settings['max_workers'] = int(os.getenv('MAX_WORKERS'))
    if os.getenv('BATCH_SIZE'):
        env_settings['batch_size'] = int(os.getenv('BATCH_SIZE'))
    
    # 日志配置
    if os.getenv('LOG_LEVEL'):
        env_settings['log_level'] = os.getenv('LOG_LEVEL')
    if os.getenv('LOG_FILE'):
        env_settings['log_file'] = os.getenv('LOG_FILE')
    
    if env_settings:
        return update_settings(**env_settings)
    return get_settings()