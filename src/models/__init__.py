"""
五大功能系统分类研究 - 核心数据模型

本模块定义了分类系统中使用的核心数据结构，包括：
- BiologicalEntry: 生物学条目的基础数据结构
- ClassificationResult: 分类结果的数据结构
- ValidationResult: 验证结果的数据结构
"""

from .biological_entry import BiologicalEntry
from .classification_result import ClassificationResult
from .validation_result import ValidationResult

__all__ = [
    'BiologicalEntry',
    'ClassificationResult', 
    'ValidationResult'
]