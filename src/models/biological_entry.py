"""
生物学条目数据模型

定义了生物学条目的基础数据结构，支持GO本体和KEGG通路数据。
"""

from dataclasses import dataclass, field
from typing import Optional, Set, Tuple, Dict, Any
import json


@dataclass
class BiologicalEntry:
    """
    生物学条目的基础数据结构
    
    支持GO本体条目和KEGG通路条目的统一表示，包含分类所需的所有信息。
    
    Attributes:
        id: 条目的唯一标识符 (如 'GO:0008150' 或 'KEGG:00010')
        name: 条目名称
        definition: 条目定义或描述
        source: 数据来源 ('GO' 或 'KEGG')
        namespace: GO条目的命名空间 (仅GO条目使用)
        ancestors: GO条目的祖先节点集合 (仅GO条目使用)
        hierarchy: KEGG通路的层次信息 (Class A, Class B) (仅KEGG条目使用)
        metadata: 额外的元数据信息
    """
    
    id: str
    name: str
    definition: str
    source: str  # 'GO' or 'KEGG'
    namespace: Optional[str] = None  # for GO terms
    ancestors: Set[str] = field(default_factory=set)  # for GO terms
    hierarchy: Optional[Tuple[str, str]] = None  # for KEGG pathways (Class A, Class B)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """数据验证和后处理"""
        # 验证必需字段
        if not self.id or not self.name or not self.source:
            raise ValueError("id, name, and source are required fields")
        
        # 验证数据来源
        if self.source not in ['GO', 'KEGG']:
            raise ValueError(f"source must be 'GO' or 'KEGG', got '{self.source}'")
        
        # GO条目特定验证
        if self.source == 'GO':
            if not self.id.startswith('GO:'):
                raise ValueError(f"GO term ID must start with 'GO:', got '{self.id}'")
            if self.namespace and self.namespace not in ['biological_process', 'molecular_function', 'cellular_component']:
                raise ValueError(f"Invalid GO namespace: {self.namespace}")
        
        # KEGG条目特定验证
        if self.source == 'KEGG':
            if not self.id.startswith('KEGG:'):
                raise ValueError(f"KEGG pathway ID must start with 'KEGG:', got '{self.id}'")
    
    def is_go_biological_process(self) -> bool:
        """检查是否为GO生物过程条目"""
        return self.source == 'GO' and self.namespace == 'biological_process'
    
    def is_obsolete(self) -> bool:
        """检查条目是否已过时"""
        return 'obsolete' in self.name.lower() or 'obsolete' in self.definition.lower()
    
    def get_text_for_classification(self) -> str:
        """获取用于分类的文本内容"""
        text_parts = [self.name, self.definition]
        
        # 添加层次信息 (KEGG)
        if self.hierarchy:
            text_parts.extend(self.hierarchy)
        
        # 添加祖先信息 (GO)
        if self.ancestors:
            # 只添加直接祖先的名称，避免文本过长
            # 这里假设祖先信息在metadata中有名称映射
            ancestor_names = self.metadata.get('ancestor_names', [])
            text_parts.extend(ancestor_names[:5])  # 限制数量
        
        return ' '.join(filter(None, text_parts))
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'definition': self.definition,
            'source': self.source,
            'namespace': self.namespace,
            'ancestors': list(self.ancestors) if self.ancestors else [],
            'hierarchy': list(self.hierarchy) if self.hierarchy else None,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BiologicalEntry':
        """从字典创建实例"""
        # 处理ancestors字段
        ancestors = set(data.get('ancestors', []))
        
        # 处理hierarchy字段
        hierarchy = data.get('hierarchy')
        if hierarchy and isinstance(hierarchy, list) and len(hierarchy) == 2:
            hierarchy = tuple(hierarchy)
        
        return cls(
            id=data['id'],
            name=data['name'],
            definition=data['definition'],
            source=data['source'],
            namespace=data.get('namespace'),
            ancestors=ancestors,
            hierarchy=hierarchy,
            metadata=data.get('metadata', {})
        )
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BiologicalEntry':
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.source}:{self.id} - {self.name}"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"BiologicalEntry(id='{self.id}', name='{self.name}', source='{self.source}')"