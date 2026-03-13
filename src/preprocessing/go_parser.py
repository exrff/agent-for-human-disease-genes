"""
GO本体解析器

解析GO本体文件，构建DAG图结构，实现祖先节点查询功能。
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Iterator
from pathlib import Path
import networkx as nx
from collections import defaultdict
import logging

# 设置日志
logger = logging.getLogger(__name__)


@dataclass
class GOTerm:
    """
    GO条目数据结构
    
    表示单个GO条目的完整信息。
    """
    
    id: str
    name: str
    namespace: str
    definition: str = ""
    synonyms: List[str] = field(default_factory=list)
    is_a: List[str] = field(default_factory=list)  # 父节点列表
    part_of: List[str] = field(default_factory=list)  # part_of关系
    regulates: List[str] = field(default_factory=list)  # regulates关系
    is_obsolete: bool = False
    alt_ids: List[str] = field(default_factory=list)  # 替代ID
    subsets: List[str] = field(default_factory=list)  # 子集信息
    xrefs: List[str] = field(default_factory=list)  # 交叉引用
    
    def __post_init__(self):
        """后处理验证"""
        if not self.id.startswith('GO:'):
            raise ValueError(f"Invalid GO ID: {self.id}")
        
        if self.namespace not in ['biological_process', 'molecular_function', 'cellular_component']:
            raise ValueError(f"Invalid namespace: {self.namespace}")
    
    def is_biological_process(self) -> bool:
        """检查是否为生物过程"""
        return self.namespace == 'biological_process'
    
    def get_all_parents(self) -> Set[str]:
        """获取所有父节点（包括is_a, part_of, regulates）"""
        parents = set()
        parents.update(self.is_a)
        parents.update(self.part_of)
        parents.update(self.regulates)
        return parents
    
    def to_biological_entry(self):
        """转换为BiologicalEntry格式"""
        # 延迟导入避免循环依赖
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from models.biological_entry import BiologicalEntry
        
        return BiologicalEntry(
            id=self.id,
            name=self.name,
            definition=self.definition,
            source='GO',
            namespace=self.namespace,
            ancestors=set(),  # 将在解析完成后填充
            metadata={
                'synonyms': self.synonyms,
                'is_obsolete': self.is_obsolete,
                'alt_ids': self.alt_ids,
                'subsets': self.subsets,
                'xrefs': self.xrefs,
                'is_a': self.is_a,
                'part_of': self.part_of,
                'regulates': self.regulates
            }
        )


class GOParser:
    """
    GO本体解析器
    
    解析GO OBO格式文件，构建DAG图结构，提供祖先节点查询功能。
    """
    
    def __init__(self, go_file_path: str):
        """
        初始化GO解析器
        
        Args:
            go_file_path: GO OBO文件路径
        """
        self.go_file_path = Path(go_file_path)
        self.terms: Dict[str, GOTerm] = {}
        self.dag: Optional[nx.DiGraph] = None
        self.namespace_terms: Dict[str, Set[str]] = defaultdict(set)
        self.obsolete_terms: Set[str] = set()
        
        if not self.go_file_path.exists():
            raise FileNotFoundError(f"GO file not found: {go_file_path}")
    
    def parse_go_terms(self) -> Dict[str, GOTerm]:
        """
        解析GO条目
        
        Returns:
            GO条目字典，键为GO ID，值为GOTerm对象
        """
        logger.info(f"开始解析GO文件: {self.go_file_path}")
        
        self.terms = {}
        current_term = None
        
        with open(self.go_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # 跳过空行和注释
                if not line or line.startswith('!'):
                    continue
                
                try:
                    # 开始新的条目
                    if line == '[Term]':
                        if current_term:
                            self._add_term(current_term)
                        current_term = self._create_empty_term()
                        continue
                    
                    # 结束条目部分
                    if line.startswith('[') and line.endswith(']') and line != '[Term]':
                        if current_term:
                            self._add_term(current_term)
                            current_term = None
                        continue
                    
                    # 解析条目属性
                    if current_term and ':' in line:
                        self._parse_term_line(current_term, line)
                
                except Exception as e:
                    logger.warning(f"解析第{line_num}行时出错: {line}, 错误: {e}")
                    continue
        
        # 添加最后一个条目
        if current_term:
            self._add_term(current_term)
        
        logger.info(f"解析完成，共解析{len(self.terms)}个GO条目")
        self._build_namespace_index()
        
        return self.terms
    
    def _create_empty_term(self) -> Dict:
        """创建空的条目字典"""
        return {
            'id': '',
            'name': '',
            'namespace': '',
            'definition': '',
            'synonyms': [],
            'is_a': [],
            'part_of': [],
            'regulates': [],
            'is_obsolete': False,
            'alt_ids': [],
            'subsets': [],
            'xrefs': []
        }
    
    def _parse_term_line(self, term_dict: Dict, line: str):
        """解析条目行"""
        if ':' not in line:
            return
        
        key, value = line.split(':', 1)
        key = key.strip()
        value = value.strip()
        
        # 解析不同的属性
        if key == 'id':
            term_dict['id'] = value
        elif key == 'name':
            term_dict['name'] = value
        elif key == 'namespace':
            term_dict['namespace'] = value
        elif key == 'def':
            # 定义格式: "definition text" [references]
            match = re.match(r'"([^"]*)"', value)
            if match:
                term_dict['definition'] = match.group(1)
        elif key == 'synonym':
            # 同义词格式: "synonym text" SCOPE [references]
            match = re.match(r'"([^"]*)"', value)
            if match:
                term_dict['synonyms'].append(match.group(1))
        elif key == 'is_a':
            # is_a格式: GO:0000001 ! term name
            go_id = value.split('!')[0].strip()
            if go_id.startswith('GO:'):
                term_dict['is_a'].append(go_id)
        elif key == 'relationship':
            # relationship格式: part_of GO:0000001 ! term name
            parts = value.split()
            if len(parts) >= 2:
                rel_type = parts[0]
                go_id = parts[1]
                if go_id.startswith('GO:'):
                    if rel_type == 'part_of':
                        term_dict['part_of'].append(go_id)
                    elif rel_type == 'regulates':
                        term_dict['regulates'].append(go_id)
        elif key == 'is_obsolete':
            term_dict['is_obsolete'] = value.lower() == 'true'
        elif key == 'alt_id':
            if value.startswith('GO:'):
                term_dict['alt_ids'].append(value)
        elif key == 'subset':
            term_dict['subsets'].append(value)
        elif key == 'xref':
            term_dict['xrefs'].append(value)
    
    def _add_term(self, term_dict: Dict):
        """添加条目到字典"""
        if not term_dict.get('id') or not term_dict.get('name'):
            return
        
        try:
            term = GOTerm(
                id=term_dict['id'],
                name=term_dict['name'],
                namespace=term_dict['namespace'],
                definition=term_dict['definition'],
                synonyms=term_dict['synonyms'],
                is_a=term_dict['is_a'],
                part_of=term_dict['part_of'],
                regulates=term_dict['regulates'],
                is_obsolete=term_dict['is_obsolete'],
                alt_ids=term_dict['alt_ids'],
                subsets=term_dict['subsets'],
                xrefs=term_dict['xrefs']
            )
            
            self.terms[term.id] = term
            
            # 索引过时条目
            if term.is_obsolete:
                self.obsolete_terms.add(term.id)
                
        except ValueError as e:
            logger.warning(f"跳过无效条目 {term_dict.get('id', 'unknown')}: {e}")
    
    def _build_namespace_index(self):
        """构建命名空间索引"""
        for term_id, term in self.terms.items():
            self.namespace_terms[term.namespace].add(term_id)
        
        logger.info(f"命名空间统计:")
        for namespace, term_ids in self.namespace_terms.items():
            logger.info(f"  {namespace}: {len(term_ids)} 个条目")
    
    def build_dag(self) -> nx.DiGraph:
        """
        构建GO DAG图结构
        
        Returns:
            NetworkX有向图对象
        """
        if not self.terms:
            self.parse_go_terms()
        
        logger.info("构建GO DAG图...")
        
        self.dag = nx.DiGraph()
        
        # 添加所有节点
        for term_id, term in self.terms.items():
            self.dag.add_node(term_id, **{
                'name': term.name,
                'namespace': term.namespace,
                'definition': term.definition,
                'is_obsolete': term.is_obsolete
            })
        
        # 添加边（关系）- 注意边的方向：从子节点指向父节点
        edge_count = 0
        for term_id, term in self.terms.items():
            # is_a关系
            for parent_id in term.is_a:
                if parent_id in self.terms:
                    self.dag.add_edge(parent_id, term_id, relation='is_a')  # 父->子
                    edge_count += 1
            
            # part_of关系
            for parent_id in term.part_of:
                if parent_id in self.terms:
                    self.dag.add_edge(parent_id, term_id, relation='part_of')  # 父->子
                    edge_count += 1
            
            # regulates关系
            for parent_id in term.regulates:
                if parent_id in self.terms:
                    self.dag.add_edge(parent_id, term_id, relation='regulates')  # 父->子
                    edge_count += 1
        
        logger.info(f"DAG构建完成: {len(self.dag.nodes)} 个节点, {edge_count} 条边")
        
        # 检查循环
        if not nx.is_directed_acyclic_graph(self.dag):
            logger.warning("检测到循环依赖！")
            cycles = list(nx.simple_cycles(self.dag))
            logger.warning(f"发现 {len(cycles)} 个循环")
        
        return self.dag
    
    def get_ancestors(self, term_id: str, include_self: bool = False) -> Set[str]:
        """
        获取条目的所有祖先节点
        
        Args:
            term_id: GO条目ID
            include_self: 是否包含自身
            
        Returns:
            祖先节点ID集合
        """
        if self.dag is None:
            self.build_dag()
        
        if term_id not in self.dag:
            return set()
        
        # 使用NetworkX的ancestors方法
        ancestors = nx.ancestors(self.dag, term_id)
        
        if include_self:
            ancestors.add(term_id)
        
        return ancestors
    
    def get_descendants(self, term_id: str, include_self: bool = False) -> Set[str]:
        """
        获取条目的所有后代节点
        
        Args:
            term_id: GO条目ID
            include_self: 是否包含自身
            
        Returns:
            后代节点ID集合
        """
        if self.dag is None:
            self.build_dag()
        
        if term_id not in self.dag:
            return set()
        
        descendants = nx.descendants(self.dag, term_id)
        
        if include_self:
            descendants.add(term_id)
        
        return descendants
    
    def get_biological_process_terms(self, exclude_obsolete: bool = True) -> Dict[str, GOTerm]:
        """
        获取所有生物过程条目
        
        Args:
            exclude_obsolete: 是否排除过时条目
            
        Returns:
            生物过程条目字典
        """
        if not self.terms:
            self.parse_go_terms()
        
        bp_terms = {}
        for term_id in self.namespace_terms.get('biological_process', set()):
            term = self.terms[term_id]
            if exclude_obsolete and term.is_obsolete:
                continue
            bp_terms[term_id] = term
        
        logger.info(f"获取到 {len(bp_terms)} 个生物过程条目")
        return bp_terms
    
    def filter_terms(self, 
                     namespaces: Optional[Set[str]] = None,
                     exclude_obsolete: bool = True,
                     exclude_general: bool = True,
                     general_patterns: Optional[List[str]] = None) -> Dict[str, GOTerm]:
        """
        过滤GO条目
        
        Args:
            namespaces: 要包含的命名空间集合
            exclude_obsolete: 是否排除过时条目
            exclude_general: 是否排除通用条目
            general_patterns: 通用条目的正则表达式模式
            
        Returns:
            过滤后的条目字典
        """
        if not self.terms:
            self.parse_go_terms()
        
        if namespaces is None:
            namespaces = {'biological_process'}
        
        if general_patterns is None:
            general_patterns = [
                r'^biological_process$',
                r'^cellular_process$',
                r'^metabolic_process$',
                r'^regulation of',
                r'^positive regulation of',
                r'^negative regulation of'
            ]
        
        # 编译正则表达式
        compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in general_patterns]
        
        filtered_terms = {}
        excluded_count = {'obsolete': 0, 'namespace': 0, 'general': 0}
        
        for term_id, term in self.terms.items():
            # 检查命名空间
            if term.namespace not in namespaces:
                excluded_count['namespace'] += 1
                continue
            
            # 检查是否过时
            if exclude_obsolete and term.is_obsolete:
                excluded_count['obsolete'] += 1
                continue
            
            # 检查是否为通用条目
            if exclude_general:
                is_general = False
                for pattern in compiled_patterns:
                    if pattern.search(term.name):
                        is_general = True
                        break
                
                if is_general:
                    excluded_count['general'] += 1
                    continue
            
            filtered_terms[term_id] = term
        
        logger.info(f"过滤结果: 保留 {len(filtered_terms)} 个条目")
        logger.info(f"排除统计: 过时条目 {excluded_count['obsolete']}, "
                   f"命名空间不匹配 {excluded_count['namespace']}, "
                   f"通用条目 {excluded_count['general']}")
        
        return filtered_terms
    
    def get_term_depth(self, term_id: str) -> int:
        """
        获取条目在DAG中的深度（到根节点的最短路径）
        
        Args:
            term_id: GO条目ID
            
        Returns:
            深度值，如果条目不存在返回-1
        """
        if self.dag is None:
            self.build_dag()
        
        if term_id not in self.dag:
            return -1
        
        # GO的根节点
        root_nodes = {
            'GO:0008150',  # biological_process
            'GO:0003674',  # molecular_function
            'GO:0005575'   # cellular_component
        }
        
        min_depth = float('inf')
        for root in root_nodes:
            if root in self.dag:
                try:
                    depth = nx.shortest_path_length(self.dag, term_id, root)
                    min_depth = min(min_depth, depth)
                except nx.NetworkXNoPath:
                    continue
        
        return min_depth if min_depth != float('inf') else -1
    
    def get_statistics(self) -> Dict:
        """
        获取解析统计信息
        
        Returns:
            统计信息字典
        """
        if not self.terms:
            self.parse_go_terms()
        
        stats = {
            'total_terms': len(self.terms),
            'obsolete_terms': len(self.obsolete_terms),
            'namespaces': {}
        }
        
        for namespace, term_ids in self.namespace_terms.items():
            stats['namespaces'][namespace] = len(term_ids)
        
        if self.dag:
            stats['dag_nodes'] = len(self.dag.nodes)
            stats['dag_edges'] = len(self.dag.edges)
            stats['is_acyclic'] = nx.is_directed_acyclic_graph(self.dag)
        
        return stats
    
    def to_biological_entries(self, filtered_terms: Optional[Dict[str, GOTerm]] = None) -> List:
        """
        转换为BiologicalEntry列表
        
        Args:
            filtered_terms: 要转换的条目字典，如果为None则使用所有条目
            
        Returns:
            BiologicalEntry对象列表
        """
        if filtered_terms is None:
            filtered_terms = self.terms
        
        if self.dag is None:
            self.build_dag()
        
        entries = []
        for term_id, term in filtered_terms.items():
            entry = term.to_biological_entry()
            
            # 填充祖先信息
            ancestors = self.get_ancestors(term_id)
            entry.ancestors = ancestors
            
            # 添加祖先名称到元数据
            ancestor_names = []
            for ancestor_id in list(ancestors)[:5]:  # 限制数量
                if ancestor_id in self.terms:
                    ancestor_names.append(self.terms[ancestor_id].name)
            entry.metadata['ancestor_names'] = ancestor_names
            
            entries.append(entry)
        
        return entries