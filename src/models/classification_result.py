"""
分类结果数据模型

定义了五大功能系统分类结果的数据结构。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import json


class FunctionalSystem(Enum):
    """五大功能系统枚举"""
    SYSTEM_A = "System A: Self-Healing & Structural Reconstruction"
    SYSTEM_B = "System B: Immune Defense"
    SYSTEM_C = "System C: Energy & Metabolic Homeostasis"
    SYSTEM_D = "System D: Cognitive-Regulatory"
    SYSTEM_E = "System E: Reproduction & Continuity"
    SYSTEM_0 = "System 0: General Molecular Machinery"
    UNCLASSIFIED = "Unclassified"
    GENERAL_BIOLOGICAL_PROCESS = "General Biological Process"


class InflammationPolarity(Enum):
    """炎症极性枚举"""
    PRO_INFLAMMATORY = "pro-inflammatory"
    ANTI_INFLAMMATORY = "anti-inflammatory"
    PRO_RESOLVING = "pro-resolving"


@dataclass
class ClassificationResult:
    """
    分类结果的数据结构
    
    包含生物学条目的完整分类信息，包括主系统、子系统、炎症极性等。
    
    Attributes:
        entry_id: 被分类条目的ID
        primary_system: 主要功能系统
        subsystem: 子系统分类 (如 A1, A2, B1, B2等)
        all_systems: 所有匹配的系统列表
        inflammation_polarity: 炎症极性标注 (如果适用)
        confidence_score: 分类置信度分数 (0-1)
        decision_path: 决策路径，记录分类过程
        metadata: 额外的分类元数据
    """
    
    entry_id: str
    primary_system: str
    subsystem: Optional[str] = None
    all_systems: List[str] = field(default_factory=list)
    inflammation_polarity: Optional[str] = None
    confidence_score: float = 1.0
    decision_path: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """数据验证和后处理"""
        # 验证必需字段
        if not self.entry_id or not self.primary_system:
            raise ValueError("entry_id and primary_system are required")
        
        # 验证置信度分数
        if not 0 <= self.confidence_score <= 1:
            raise ValueError("confidence_score must be between 0 and 1")
        
        # 验证主系统是否在有效系统列表中
        valid_systems = [system.value for system in FunctionalSystem]
        if self.primary_system not in valid_systems:
            raise ValueError(f"Invalid primary_system: {self.primary_system}")
        
        # 验证炎症极性
        if self.inflammation_polarity:
            valid_polarities = [polarity.value for polarity in InflammationPolarity]
            if self.inflammation_polarity not in valid_polarities:
                raise ValueError(f"Invalid inflammation_polarity: {self.inflammation_polarity}")
        
        # 确保主系统在所有系统列表中
        if self.primary_system not in self.all_systems:
            self.all_systems.insert(0, self.primary_system)
    
    def is_system_a(self) -> bool:
        """检查是否分类为System A"""
        return self.primary_system == FunctionalSystem.SYSTEM_A.value
    
    def is_system_b(self) -> bool:
        """检查是否分类为System B"""
        return self.primary_system == FunctionalSystem.SYSTEM_B.value
    
    def is_system_c(self) -> bool:
        """检查是否分类为System C"""
        return self.primary_system == FunctionalSystem.SYSTEM_C.value
    
    def is_system_d(self) -> bool:
        """检查是否分类为System D"""
        return self.primary_system == FunctionalSystem.SYSTEM_D.value
    
    def is_system_e(self) -> bool:
        """检查是否分类为System E"""
        return self.primary_system == FunctionalSystem.SYSTEM_E.value
    
    def is_system_0(self) -> bool:
        """检查是否分类为System 0"""
        return self.primary_system == FunctionalSystem.SYSTEM_0.value
    
    def is_unclassified(self) -> bool:
        """检查是否未分类"""
        return self.primary_system in [
            FunctionalSystem.UNCLASSIFIED.value,
            FunctionalSystem.GENERAL_BIOLOGICAL_PROCESS.value
        ]
    
    def has_inflammation_annotation(self) -> bool:
        """检查是否有炎症极性标注"""
        return self.inflammation_polarity is not None
    
    def get_system_letter(self) -> str:
        """获取系统字母标识"""
        system_mapping = {
            FunctionalSystem.SYSTEM_A.value: 'A',
            FunctionalSystem.SYSTEM_B.value: 'B',
            FunctionalSystem.SYSTEM_C.value: 'C',
            FunctionalSystem.SYSTEM_D.value: 'D',
            FunctionalSystem.SYSTEM_E.value: 'E',
            FunctionalSystem.SYSTEM_0.value: '0',
        }
        return system_mapping.get(self.primary_system, 'U')  # U for Unclassified
    
    def add_decision_step(self, step: str):
        """添加决策步骤"""
        self.decision_path.append(step)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'entry_id': self.entry_id,
            'primary_system': self.primary_system,
            'subsystem': self.subsystem,
            'all_systems': self.all_systems,
            'inflammation_polarity': self.inflammation_polarity,
            'confidence_score': self.confidence_score,
            'decision_path': self.decision_path,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClassificationResult':
        """从字典创建实例"""
        return cls(
            entry_id=data['entry_id'],
            primary_system=data['primary_system'],
            subsystem=data.get('subsystem'),
            all_systems=data.get('all_systems', []),
            inflammation_polarity=data.get('inflammation_polarity'),
            confidence_score=data.get('confidence_score', 1.0),
            decision_path=data.get('decision_path', []),
            metadata=data.get('metadata', {})
        )
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ClassificationResult':
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def to_csv_row(self) -> Dict[str, str]:
        """转换为CSV行格式"""
        return {
            'ID': self.entry_id,
            'Primary_System': self.primary_system,
            'Subsystem': self.subsystem or '',
            'All_Systems': '; '.join(self.all_systems),
            'Inflammation_Polarity': self.inflammation_polarity or '',
            'Confidence_Score': str(self.confidence_score),
            'Decision_Path': ' -> '.join(self.decision_path)
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.entry_id} -> {self.primary_system}"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"ClassificationResult(entry_id='{self.entry_id}', primary_system='{self.primary_system}')"