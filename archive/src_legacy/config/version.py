"""
版本信息和项目元数据

定义了五大功能系统分类研究的版本信息。
"""

from dataclasses import dataclass
from typing import Dict, Any
import sys
from datetime import datetime


@dataclass
class VersionInfo:
    """版本信息类"""
    
    major: int = 1
    minor: int = 0
    patch: int = 0
    pre_release: str = ""
    build_metadata: str = ""
    
    def __str__(self) -> str:
        """版本字符串表示"""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre_release:
            version += f"-{self.pre_release}"
        if self.build_metadata:
            version += f"+{self.build_metadata}"
        return version
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'version': str(self),
            'major': self.major,
            'minor': self.minor,
            'patch': self.patch,
            'pre_release': self.pre_release,
            'build_metadata': self.build_metadata
        }


# 项目版本信息
VERSION = VersionInfo(
    major=1,
    minor=0,
    patch=0,
    pre_release="alpha",
    build_metadata=""
)

# 项目元数据
PROJECT_METADATA = {
    'name': 'Five Functional Systems Classification',
    'description': '基于功能目标的五大生物系统分类研究',
    'version': str(VERSION),
    'author': 'Research Team',
    'license': 'MIT',
    'python_requires': '>=3.8',
    'created_date': '2024-12-24',
    'last_updated': datetime.now().strftime('%Y-%m-%d'),
    'repository': '',
    'documentation': '',
    'keywords': [
        'bioinformatics',
        'systems biology', 
        'functional classification',
        'GO ontology',
        'KEGG pathways',
        'biological systems'
    ]
}

# 系统要求
SYSTEM_REQUIREMENTS = {
    'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    'minimum_python': '3.8.0',
    'recommended_python': '3.9.0',
    'platform': sys.platform,
    'architecture': sys.maxsize > 2**32 and '64-bit' or '32-bit'
}

# 依赖版本要求
DEPENDENCY_REQUIREMENTS = {
    'core': {
        'pandas': '>=1.3.0',
        'numpy': '>=1.20.0',
        'scipy': '>=1.7.0',
        'scikit-learn': '>=1.0.0'
    },
    'bioinformatics': {
        'gseapy': '>=0.10.0',
        'goatools': '>=1.2.0',
        'biopython': '>=1.79'
    },
    'testing': {
        'pytest': '>=6.0.0',
        'hypothesis': '>=6.0.0',
        'pytest-cov': '>=2.12.0'
    },
    'visualization': {
        'matplotlib': '>=3.4.0',
        'seaborn': '>=0.11.0',
        'wordcloud': '>=1.8.0'
    },
    'development': {
        'black': '>=21.0.0',
        'flake8': '>=3.9.0',
        'mypy': '>=0.910'
    }
}

# 功能特性标志
FEATURE_FLAGS = {
    'enable_parallel_processing': True,
    'enable_caching': True,
    'enable_logging': True,
    'enable_progress_bars': True,
    'enable_validation': True,
    'enable_visualization': True,
    'experimental_features': False,
    'debug_mode': False
}

# 分类系统版本信息
CLASSIFICATION_SYSTEM_VERSION = {
    'version': '7.5',
    'description': '五大功能系统分类 v7.5',
    'release_date': '2024-12-24',
    'changes': [
        '完善了System A的自愈重建分类规则',
        '优化了炎症极性标注逻辑',
        '增强了子系统分类准确性',
        '改进了复杂通路拆分算法'
    ],
    'validation_datasets': [
        'GSE28914 (伤口愈合)',
        'GSE65682 (脓毒症)',
        'GSE21899 (戈谢病)'
    ]
}


def get_version_info() -> Dict[str, Any]:
    """获取完整版本信息"""
    return {
        'project': PROJECT_METADATA,
        'version': VERSION.to_dict(),
        'system': SYSTEM_REQUIREMENTS,
        'dependencies': DEPENDENCY_REQUIREMENTS,
        'features': FEATURE_FLAGS,
        'classification_system': CLASSIFICATION_SYSTEM_VERSION
    }


def check_python_version() -> bool:
    """检查Python版本是否满足要求"""
    import sys
    from packaging import version
    
    current_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    minimum_version = SYSTEM_REQUIREMENTS['minimum_python']
    
    return version.parse(current_version) >= version.parse(minimum_version)


def get_system_info() -> Dict[str, str]:
    """获取系统信息"""
    import platform
    
    return {
        'platform': platform.platform(),
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'python_version': platform.python_version(),
        'python_implementation': platform.python_implementation()
    }


if __name__ == "__main__":
    # 打印版本信息
    print(f"Five Functional Systems Classification v{VERSION}")
    print(f"Python {SYSTEM_REQUIREMENTS['python_version']}")
    print(f"Platform: {SYSTEM_REQUIREMENTS['platform']}")
    print(f"Architecture: {SYSTEM_REQUIREMENTS['architecture']}")
    
    # 检查Python版本
    if not check_python_version():
        print(f"Warning: Python {SYSTEM_REQUIREMENTS['minimum_python']} or higher is required")
    else:
        print("Python version check: OK")