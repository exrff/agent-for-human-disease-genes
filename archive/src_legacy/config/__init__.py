"""
配置管理模块

管理五大功能系统分类研究的配置参数。
"""

from .settings import Settings, get_settings, update_settings, load_settings_from_env
from .classification_rules import ClassificationRules, default_classification_rules
from .version import (
    VERSION, 
    PROJECT_METADATA, 
    SYSTEM_REQUIREMENTS,
    DEPENDENCY_REQUIREMENTS,
    FEATURE_FLAGS,
    CLASSIFICATION_SYSTEM_VERSION,
    get_version_info,
    check_python_version,
    get_system_info
)

__all__ = [
    # Settings
    'Settings',
    'get_settings',
    'update_settings', 
    'load_settings_from_env',
    
    # Classification Rules
    'ClassificationRules',
    'default_classification_rules',
    
    # Version Info
    'VERSION',
    'PROJECT_METADATA',
    'SYSTEM_REQUIREMENTS',
    'DEPENDENCY_REQUIREMENTS', 
    'FEATURE_FLAGS',
    'CLASSIFICATION_SYSTEM_VERSION',
    'get_version_info',
    'check_python_version',
    'get_system_info'
]