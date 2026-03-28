"""
KEGG通路解析器

解析KEGG层次结构文件，提取Class A、Class B和通路名称信息。
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path
import logging

# 设置日志
logger = logging.getLogger(__name__)


@dataclass
class KEGGPathway:
    """
    KEGG通路数据结构
    
    表示单个KEGG通路的完整信息。
    """
    
    id: str  # 通路ID，如 "00010"
    name: str  # 通路名称
    class_a: str  # Class A分类，如 "Metabolism"
    class_b: str  # Class B分类，如 "Carbohydrate metabolism"
    full_id: str = ""  # 完整ID，如 "KEGG:00010"
    description: str = ""  # 详细描述
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """后处理验证"""
        if not self.id:
            raise ValueError("KEGG pathway ID is required")
        
        if not self.name:
            raise ValueError("KEGG pathway name is required")
        
        # 生成完整ID
        if not self.full_id:
            self.full_id = f"KEGG:{self.id}"
        
        # 验证ID格式
        if not re.match(r'^\d{4,5}$', self.id):
            raise ValueError(f"Invalid KEGG pathway ID format: {self.id}")
    
    def get_hierarchy_tuple(self) -> Tuple[str, str]:
        """获取层次信息元组"""
        return (self.class_a, self.class_b)
    
    def to_biological_entry(self):
        """转换为BiologicalEntry格式"""
        # 延迟导入避免循环依赖
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from models.biological_entry import BiologicalEntry
        
        return BiologicalEntry(
            id=self.full_id,
            name=self.name,
            definition=self.description,
            source='KEGG',
            namespace=None,
            ancestors=set(),
            hierarchy=self.get_hierarchy_tuple(),
            metadata={
                'class_a': self.class_a,
                'class_b': self.class_b,
                'pathway_id': self.id,
                **self.metadata
            }
        )


class KEGGParser:
    """
    KEGG通路解析器
    
    解析KEGG层次结构文件，提取通路信息和层次关系。
    """
    
    def __init__(self, kegg_file_path: str):
        """
        初始化KEGG解析器
        
        Args:
            kegg_file_path: KEGG层次结构文件路径
        """
        self.kegg_file_path = Path(kegg_file_path)
        self.pathways: Dict[str, KEGGPathway] = {}
        self.class_a_pathways: Dict[str, Set[str]] = {}
        self.class_b_pathways: Dict[str, Set[str]] = {}
        self.hierarchy_mapping: Dict[str, Tuple[str, str]] = {}
        
        if not self.kegg_file_path.exists():
            raise FileNotFoundError(f"KEGG file not found: {kegg_file_path}")
    
    def parse_pathways(self) -> List[KEGGPathway]:
        """
        解析KEGG通路
        
        Returns:
            KEGG通路对象列表
        """
        logger.info(f"开始解析KEGG文件: {self.kegg_file_path}")
        
        self.pathways = {}
        current_class_a = ""
        current_class_b = ""
        
        with open(self.kegg_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.rstrip()
                
                # 跳过空行和注释
                if not line or line.startswith('!') or line.startswith('+'):
                    continue
                
                try:
                    # 解析不同层级的行
                    if line.startswith('A'):
                        # Class A级别
                        current_class_a = line[1:].strip()
                        current_class_b = ""
                        logger.debug(f"Class A: {current_class_a}")
                        
                    elif line.startswith('B  '):
                        # Class B级别
                        current_class_b = line[3:].strip()
                        logger.debug(f"Class B: {current_class_b}")
                        
                    elif line.startswith('C    '):
                        # 通路级别
                        pathway_info = line[6:].strip()
                        pathway = self._parse_pathway_line(
                            pathway_info, current_class_a, current_class_b
                        )
                        
                        if pathway:
                            self.pathways[pathway.id] = pathway
                            self._index_pathway(pathway)
                
                except Exception as e:
                    logger.warning(f"解析第{line_num}行时出错: {line}, 错误: {e}")
                    continue
        
        logger.info(f"解析完成，共解析{len(self.pathways)}个KEGG通路")
        self._build_hierarchy_mapping()
        
        return list(self.pathways.values())
    
    def _parse_pathway_line(self, pathway_info: str, class_a: str, class_b: str) -> Optional[KEGGPathway]:
        """
        解析通路行
        
        Args:
            pathway_info: 通路信息字符串，如 "00010  Glycolysis / Gluconeogenesis"
            class_a: Class A分类
            class_b: Class B分类
            
        Returns:
            KEGGPathway对象或None
        """
        # 解析通路ID和名称
        match = re.match(r'^(\d{4,5})\s+(.+)$', pathway_info)
        if not match:
            logger.warning(f"无法解析通路信息: {pathway_info}")
            return None
        
        pathway_id = match.group(1)
        pathway_name = match.group(2).strip()
        
        try:
            pathway = KEGGPathway(
                id=pathway_id,
                name=pathway_name,
                class_a=class_a,
                class_b=class_b,
                description=f"{class_a} > {class_b} > {pathway_name}"
            )
            
            return pathway
            
        except ValueError as e:
            logger.warning(f"创建通路对象失败: {e}")
            return None
    
    def _index_pathway(self, pathway: KEGGPathway):
        """为通路建立索引"""
        # Class A索引
        if pathway.class_a not in self.class_a_pathways:
            self.class_a_pathways[pathway.class_a] = set()
        self.class_a_pathways[pathway.class_a].add(pathway.id)
        
        # Class B索引
        if pathway.class_b not in self.class_b_pathways:
            self.class_b_pathways[pathway.class_b] = set()
        self.class_b_pathways[pathway.class_b].add(pathway.id)
    
    def _build_hierarchy_mapping(self):
        """构建层次映射关系"""
        for pathway_id, pathway in self.pathways.items():
            self.hierarchy_mapping[pathway_id] = (pathway.class_a, pathway.class_b)
        
        logger.info(f"层次映射构建完成，共{len(self.hierarchy_mapping)}个映射")
    
    def extract_hierarchy(self) -> Dict[str, Tuple[str, str]]:
        """
        提取层次信息
        
        Returns:
            层次映射字典，键为通路ID，值为(Class A, Class B)元组
        """
        if not self.hierarchy_mapping:
            self.parse_pathways()
        
        return self.hierarchy_mapping.copy()
    
    def get_pathways_by_class_a(self, class_a: str) -> List[KEGGPathway]:
        """
        根据Class A获取通路
        
        Args:
            class_a: Class A分类名称
            
        Returns:
            通路对象列表
        """
        if not self.pathways:
            self.parse_pathways()
        
        pathway_ids = self.class_a_pathways.get(class_a, set())
        return [self.pathways[pid] for pid in pathway_ids if pid in self.pathways]
    
    def get_pathways_by_class_b(self, class_b: str) -> List[KEGGPathway]:
        """
        根据Class B获取通路
        
        Args:
            class_b: Class B分类名称
            
        Returns:
            通路对象列表
        """
        if not self.pathways:
            self.parse_pathways()
        
        pathway_ids = self.class_b_pathways.get(class_b, set())
        return [self.pathways[pid] for pid in pathway_ids if pid in self.pathways]
    
    def get_metabolism_pathways(self) -> List[KEGGPathway]:
        """
        获取所有代谢相关通路
        
        Returns:
            代谢通路列表
        """
        return self.get_pathways_by_class_a("Metabolism")
    
    def get_immune_related_pathways(self) -> List[KEGGPathway]:
        """
        获取免疫相关通路
        
        Returns:
            免疫相关通路列表
        """
        immune_keywords = [
            "immune", "immunity", "immunodeficiency", "complement",
            "antigen", "antibody", "cytokine", "chemokine",
            "toll-like", "nf-kappa", "inflammatory"
        ]
        
        immune_pathways = []
        for pathway in self.pathways.values():
            pathway_text = f"{pathway.name} {pathway.class_b}".lower()
            
            for keyword in immune_keywords:
                if keyword in pathway_text:
                    immune_pathways.append(pathway)
                    break
        
        return immune_pathways
    
    def filter_pathways(self, 
                       class_a_filter: Optional[Set[str]] = None,
                       class_b_filter: Optional[Set[str]] = None,
                       name_patterns: Optional[List[str]] = None,
                       exclude_patterns: Optional[List[str]] = None) -> List[KEGGPathway]:
        """
        过滤KEGG通路
        
        Args:
            class_a_filter: Class A过滤集合
            class_b_filter: Class B过滤集合
            name_patterns: 名称包含模式列表
            exclude_patterns: 排除模式列表
            
        Returns:
            过滤后的通路列表
        """
        if not self.pathways:
            self.parse_pathways()
        
        filtered_pathways = []
        
        # 编译正则表达式
        name_regexes = []
        if name_patterns:
            name_regexes = [re.compile(pattern, re.IGNORECASE) for pattern in name_patterns]
        
        exclude_regexes = []
        if exclude_patterns:
            exclude_regexes = [re.compile(pattern, re.IGNORECASE) for pattern in exclude_patterns]
        
        for pathway in self.pathways.values():
            # Class A过滤
            if class_a_filter and pathway.class_a not in class_a_filter:
                continue
            
            # Class B过滤
            if class_b_filter and pathway.class_b not in class_b_filter:
                continue
            
            # 名称模式过滤
            if name_regexes:
                match_found = False
                for regex in name_regexes:
                    if regex.search(pathway.name):
                        match_found = True
                        break
                if not match_found:
                    continue
            
            # 排除模式过滤
            if exclude_regexes:
                exclude_found = False
                for regex in exclude_regexes:
                    if regex.search(pathway.name):
                        exclude_found = True
                        break
                if exclude_found:
                    continue
            
            filtered_pathways.append(pathway)
        
        logger.info(f"过滤结果: 保留 {len(filtered_pathways)} 个通路")
        return filtered_pathways
    
    def get_statistics(self) -> Dict:
        """
        获取解析统计信息
        
        Returns:
            统计信息字典
        """
        if not self.pathways:
            self.parse_pathways()
        
        stats = {
            'total_pathways': len(self.pathways),
            'class_a_count': len(self.class_a_pathways),
            'class_b_count': len(self.class_b_pathways),
            'class_a_distribution': {},
            'class_b_distribution': {}
        }
        
        # Class A分布
        for class_a, pathway_ids in self.class_a_pathways.items():
            stats['class_a_distribution'][class_a] = len(pathway_ids)
        
        # Class B分布
        for class_b, pathway_ids in self.class_b_pathways.items():
            stats['class_b_distribution'][class_b] = len(pathway_ids)
        
        return stats
    
    def to_biological_entries(self, filtered_pathways: Optional[List[KEGGPathway]] = None) -> List:
        """
        转换为BiologicalEntry列表
        
        Args:
            filtered_pathways: 要转换的通路列表，如果为None则使用所有通路
            
        Returns:
            BiologicalEntry对象列表
        """
        if filtered_pathways is None:
            if not self.pathways:
                self.parse_pathways()
            filtered_pathways = list(self.pathways.values())
        
        entries = []
        for pathway in filtered_pathways:
            entry = pathway.to_biological_entry()
            entries.append(entry)
        
        return entries
    
    def search_pathways(self, query: str, search_fields: Optional[List[str]] = None) -> List[KEGGPathway]:
        """
        搜索通路
        
        Args:
            query: 搜索查询字符串
            search_fields: 搜索字段列表，默认为['name', 'class_a', 'class_b']
            
        Returns:
            匹配的通路列表
        """
        if not self.pathways:
            self.parse_pathways()
        
        if search_fields is None:
            search_fields = ['name', 'class_a', 'class_b']
        
        query_lower = query.lower()
        matching_pathways = []
        
        for pathway in self.pathways.values():
            for field in search_fields:
                field_value = getattr(pathway, field, "").lower()
                if query_lower in field_value:
                    matching_pathways.append(pathway)
                    break
        
        return matching_pathways