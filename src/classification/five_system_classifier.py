"""
五大功能系统分类器

实现基于功能目标的五大系统分类引擎，包括主系统分类、子系统分类和炎症极性标注。
"""

from typing import Dict, List, Optional, Set, Tuple
import re
from dataclasses import dataclass
import logging

from ..models.biological_entry import BiologicalEntry
from ..models.classification_result import ClassificationResult, FunctionalSystem
from ..config.classification_rules import ClassificationRules, SystemType


logger = logging.getLogger(__name__)


def _get_system_enum_value(system_code: str) -> str:
    """将系统代码转换为枚举值"""
    system_mapping = {
        'A': FunctionalSystem.SYSTEM_A.value,
        'B': FunctionalSystem.SYSTEM_B.value,
        'C': FunctionalSystem.SYSTEM_C.value,
        'D': FunctionalSystem.SYSTEM_D.value,
        'E': FunctionalSystem.SYSTEM_E.value,
        '0': FunctionalSystem.SYSTEM_0.value,
        'U': FunctionalSystem.UNCLASSIFIED.value
    }
    return system_mapping.get(system_code, FunctionalSystem.UNCLASSIFIED.value)


@dataclass
class ClassificationDecision:
    """分类决策结果"""
    system: str
    confidence: float
    matched_patterns: List[str]
    decision_path: List[str]


class FiveSystemClassifier:
    """
    五大功能系统分类器
    
    基于功能目标的分类策略，将生物学过程按照主要生命任务分类到五个核心系统中。
    """
    
    def __init__(self, classification_rules: Optional[ClassificationRules] = None):
        """
        初始化分类器
        
        Args:
            classification_rules: 分类规则配置，如果为None则使用默认规则
        """
        self.rules = classification_rules or ClassificationRules()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 分类统计
        self.classification_stats = {
            'total_classified': 0,
            'system_counts': {system.value: 0 for system in SystemType},
            'unclassified_count': 0
        }
    
    def classify_entry(self, entry: BiologicalEntry) -> ClassificationResult:
        """
        对生物学条目进行完整分类
        
        Args:
            entry: 待分类的生物学条目
            
        Returns:
            ClassificationResult: 完整的分类结果
        """
        try:
            # 1. 检查是否为排除的通用术语
            if self._is_excluded_entry(entry):
                return self._create_system_0_result(entry, "excluded_general_term")
            
            # 2. 检查是否为复杂通路，如果是则使用特殊处理逻辑
            if self._is_complex_pathway(entry):
                return self._handle_complex_pathway(entry)
            
            # 3. 检查是否为炎症相关过程，应用特殊决策规则
            if self._is_inflammation_related(entry):
                return self._handle_inflammation_process(entry)
            
            # 4. 标准分类流程
            return self._standard_classification(entry)
            
        except Exception as e:
            self.logger.error(f"分类条目 {entry.id} 时发生错误: {e}")
            return self._create_error_result(entry, str(e))
    
    def _standard_classification(self, entry: BiologicalEntry) -> ClassificationResult:
        """
        标准分类流程
        
        Args:
            entry: 待分类的生物学条目
            
        Returns:
            ClassificationResult: 分类结果
        """
        # 1. 主系统分类
        primary_decision = self.classify_primary_system(entry)
        
        # 2. 子系统分类
        subsystem = None
        if primary_decision.system in [FunctionalSystem.SYSTEM_A.value, FunctionalSystem.SYSTEM_B.value,
                                     FunctionalSystem.SYSTEM_C.value, FunctionalSystem.SYSTEM_D.value,
                                     FunctionalSystem.SYSTEM_E.value]:
            subsystem = self.classify_subsystem(entry, primary_decision.system)
        
        # 3. 炎症极性标注
        inflammation_polarity = self.annotate_inflammation_polarity(entry)
        
        # 4. 获取所有匹配的系统
        all_systems = self._get_all_matching_systems(entry)
        
        # 5. 创建分类结果
        result = ClassificationResult(
            entry_id=entry.id,
            primary_system=primary_decision.system,
            subsystem=subsystem,
            all_systems=all_systems,
            inflammation_polarity=inflammation_polarity,
            confidence_score=primary_decision.confidence,
            decision_path=primary_decision.decision_path
        )
        
        # 将匹配的模式添加到元数据中
        result.metadata['matched_patterns'] = primary_decision.matched_patterns
        
        # 6. 更新统计
        self._update_stats(result)
        
        return result
    
    def classify_primary_system(self, entry: BiologicalEntry) -> ClassificationDecision:
        """
        主系统分类
        
        基于功能目标进行分类，按照优先级规则决定主要系统归属。
        
        Args:
            entry: 待分类的生物学条目
            
        Returns:
            ClassificationDecision: 主系统分类决策
        """
        # 构建用于匹配的文本
        search_text = self._build_search_text(entry)
        
        # 收集所有系统的匹配结果
        system_matches = {}
        
        for system in ['A', 'B', 'C', 'D', 'E', '0']:
            matches = self.rules.match_system_patterns(search_text, system)
            if matches:
                system_matches[system] = matches
        
        # 如果没有任何匹配，返回System 0
        if not system_matches:
            return ClassificationDecision(
                system=_get_system_enum_value('0'),
                confidence=0.1,
                matched_patterns=[],
                decision_path=['no_pattern_match', 'default_to_system_0']
            )
        
        # 应用决策规则
        return self._apply_decision_rules(system_matches, entry)
    
    def classify_subsystem(self, entry: BiologicalEntry, primary_system: str) -> Optional[str]:
        """
        子系统分类
        
        Args:
            entry: 待分类的生物学条目
            primary_system: 主系统分类结果
            
        Returns:
            Optional[str]: 子系统分类结果，如果无法确定则返回None
        """
        # 将系统枚举值转换回字母代码
        system_letter = None
        for code, enum_value in [('A', FunctionalSystem.SYSTEM_A.value),
                                ('B', FunctionalSystem.SYSTEM_B.value),
                                ('C', FunctionalSystem.SYSTEM_C.value),
                                ('D', FunctionalSystem.SYSTEM_D.value),
                                ('E', FunctionalSystem.SYSTEM_E.value)]:
            if primary_system == enum_value:
                system_letter = code
                break
        
        if system_letter is None:
            return None
        
        search_text = self._build_search_text(entry)
        subsystem_matches = self.rules.match_subsystem_patterns(search_text, system_letter)
        
        if not subsystem_matches:
            return None
        
        # 选择匹配模式最多的子系统
        best_subsystem = max(subsystem_matches.keys(), 
                           key=lambda x: len(subsystem_matches[x]))
        
        return best_subsystem
    
    def annotate_inflammation_polarity(self, entry: BiologicalEntry) -> Optional[str]:
        """
        炎症极性标注
        
        为炎症相关过程标注极性属性：促炎、抗炎、促消解
        
        Args:
            entry: 待分类的生物学条目
            
        Returns:
            Optional[str]: 炎症极性，如果不是炎症相关过程则返回None
        """
        search_text = self._build_search_text(entry)
        inflammation_matches = self.rules.match_inflammation_patterns(search_text)
        
        if not inflammation_matches:
            return None
        
        # 按优先级选择极性：促消解 > 抗炎 > 促炎
        polarity_priority = ['pro-resolving', 'anti-inflammatory', 'pro-inflammatory']
        
        for polarity in polarity_priority:
            if polarity in inflammation_matches:
                return polarity
        
        return None
    
    def apply_decision_rules(self, entry: BiologicalEntry) -> ClassificationResult:
        """
        应用完整的决策规则
        
        实现复杂通路拆分和炎症过程的特殊决策逻辑。
        
        Args:
            entry: 待分类的生物学条目
            
        Returns:
            ClassificationResult: 完整的分类结果
        """
        # 检查是否为复杂通路（包含破坏性和建设性组分）
        if self._is_complex_pathway(entry):
            return self._handle_complex_pathway(entry)
        
        # 检查是否为炎症相关过程，应用特殊决策规则
        if self._is_inflammation_related(entry):
            return self._handle_inflammation_process(entry)
        
        # 标准分类流程
        return self.classify_entry(entry)
    
    def _build_search_text(self, entry: BiologicalEntry) -> str:
        """构建用于模式匹配的搜索文本"""
        parts = [entry.name]
        
        if entry.definition:
            parts.append(entry.definition)
        
        # 对于GO条目，包含祖先节点信息
        if entry.source == 'GO' and entry.ancestors:
            # 这里可以添加祖先节点的名称信息
            pass
        
        return ' '.join(parts).lower()
    
    def _is_excluded_entry(self, entry: BiologicalEntry) -> bool:
        """检查是否为排除的通用术语"""
        search_text = self._build_search_text(entry)
        return self.rules.is_excluded_term(search_text)
    
    def _apply_decision_rules(self, system_matches: Dict[str, List[str]], 
                           entry: BiologicalEntry) -> ClassificationDecision:
        """
        应用决策规则选择主系统
        
        基于优先级和匹配强度进行决策。
        """
        decision_path = ['pattern_matching']
        
        # 1. 如果只有一个系统匹配，直接返回
        if len(system_matches) == 1:
            system = list(system_matches.keys())[0]
            decision_path.append(f'single_match_{system}')
            return ClassificationDecision(
                system=_get_system_enum_value(system),
                confidence=0.9,
                matched_patterns=system_matches[system],
                decision_path=decision_path
            )
        
        # 2. 多系统匹配，应用优先级规则
        systems_by_priority = self.rules.sort_systems_by_priority(list(system_matches.keys()))
        
        # 3. 检查是否有明显的优先级差异
        top_system = systems_by_priority[0]
        top_priority = self.rules.get_system_priority(top_system)
        
        # 如果最高优先级系统是唯一的，选择它
        same_priority_systems = [s for s in systems_by_priority 
                               if self.rules.get_system_priority(s) == top_priority]
        
        if len(same_priority_systems) == 1:
            decision_path.append(f'priority_rule_{top_system}')
            return ClassificationDecision(
                system=_get_system_enum_value(top_system),
                confidence=0.8,
                matched_patterns=system_matches[top_system],
                decision_path=decision_path
            )
        
        # 4. 相同优先级的系统，选择匹配模式最多的
        best_system = max(same_priority_systems, 
                         key=lambda x: len(system_matches[x]))
        
        decision_path.append(f'pattern_count_{best_system}')
        return ClassificationDecision(
            system=_get_system_enum_value(best_system),
            confidence=0.7,
            matched_patterns=system_matches[best_system],
            decision_path=decision_path
        )
    
    def _get_all_matching_systems(self, entry: BiologicalEntry) -> List[str]:
        """获取所有匹配的系统列表"""
        search_text = self._build_search_text(entry)
        matching_systems = []
        
        for system in ['A', 'B', 'C', 'D', 'E', '0']:
            matches = self.rules.match_system_patterns(search_text, system)
            if matches:
                matching_systems.append(_get_system_enum_value(system))
        
        return matching_systems
    
    def _is_complex_pathway(self, entry: BiologicalEntry) -> bool:
        """检查是否为包含混合组分的复杂通路"""
        search_text = self._build_search_text(entry)
        
        # 检查是否同时包含破坏性和建设性关键词
        destructive_patterns = [
            r'kill', r'destroy', r'eliminate', r'attack', r'cytotox',
            r'lysis', r'death', r'apoptosis', r'degradation', r'breakdown',
            r'clearance', r'removal', r'antimicrobial', r'bactericidal',
            r'destruction', r'elimination', r'pathogen.*elimination'
        ]
        
        constructive_patterns = [
            r'repair', r'heal', r'regenerat', r'reconstruct', r'restore',
            r'maintain', r'homeostasis', r'synthesis', r'biosynthesis',
            r'formation', r'assembly', r'construction', r'development',
            r'tissue.*repair', r'wound.*healing', r'reconstruction'
        ]
        
        has_destructive = any(re.search(pattern, search_text, re.IGNORECASE) 
                            for pattern in destructive_patterns)
        has_constructive = any(re.search(pattern, search_text, re.IGNORECASE) 
                             for pattern in constructive_patterns)
        
        return has_destructive and has_constructive
    
    def _is_inflammation_related(self, entry: BiologicalEntry) -> bool:
        """检查是否为炎症相关过程"""
        search_text = self._build_search_text(entry)
        inflammation_matches = self.rules.match_inflammation_patterns(search_text)
        return bool(inflammation_matches)
    
    def _handle_complex_pathway(self, entry: BiologicalEntry) -> ClassificationResult:
        """
        处理复杂通路的拆分逻辑
        
        对于包含破坏性和建设性组分的复杂通路，分析其主要功能目标
        并进行组分级别的分类。
        """
        search_text = self._build_search_text(entry)
        
        # 分析破坏性和建设性组分的强度
        destructive_score = self._calculate_destructive_score(search_text)
        constructive_score = self._calculate_constructive_score(search_text)
        
        # 检查是否有明确的功能目标指示
        functional_objectives = self._analyze_functional_objectives(search_text)
        
        # 基于组分分析决定主要分类
        if destructive_score > constructive_score * 1.5:
            # 破坏性组分占主导 -> 倾向于System B
            primary_decision = self._classify_as_destructive_dominant(entry, functional_objectives)
        elif constructive_score > destructive_score * 1.5:
            # 建设性组分占主导 -> 倾向于System A
            primary_decision = self._classify_as_constructive_dominant(entry, functional_objectives)
        else:
            # 组分平衡 -> 需要更细致的分析
            primary_decision = self._classify_balanced_pathway(entry, functional_objectives)
        
        # 创建分类结果
        result = ClassificationResult(
            entry_id=entry.id,
            primary_system=primary_decision.system,
            subsystem=self.classify_subsystem(entry, primary_decision.system),
            all_systems=self._get_all_matching_systems(entry),
            inflammation_polarity=self.annotate_inflammation_polarity(entry),
            confidence_score=primary_decision.confidence * 0.8,  # 复杂通路置信度降低
            decision_path=primary_decision.decision_path + ['complex_pathway_analysis']
        )
        
        # 添加复杂通路的元数据
        result.metadata['complex_pathway'] = True
        result.metadata['destructive_score'] = destructive_score
        result.metadata['constructive_score'] = constructive_score
        result.metadata['functional_objectives'] = functional_objectives
        result.metadata['matched_patterns'] = primary_decision.matched_patterns
        
        # 更新统计
        self._update_stats(result)
        
        return result
    
    def _calculate_destructive_score(self, text: str) -> float:
        """计算破坏性组分得分"""
        destructive_patterns = {
            r'kill|killing': 3.0,
            r'destroy|destruction': 3.0,
            r'eliminate|elimination': 2.5,
            r'attack|attacking': 2.5,
            r'cytotox|cytotoxic': 3.0,
            r'lysis|lytic': 2.5,
            r'death|dying': 2.0,
            r'apoptosis|apoptotic': 2.0,
            r'degradation|degrade': 2.0,
            r'breakdown|break down': 2.0,
            r'clearance|clear': 1.5,
            r'removal|remove': 1.5,
            r'antimicrobial': 2.5,
            r'bactericidal': 2.5
        }
        
        score = 0.0
        for pattern, weight in destructive_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                score += weight
        
        return score
    
    def _calculate_constructive_score(self, text: str) -> float:
        """计算建设性组分得分"""
        constructive_patterns = {
            r'repair|repairing': 3.0,
            r'heal|healing': 3.0,
            r'regenerat|regeneration': 3.0,
            r'reconstruct|reconstruction': 2.5,
            r'restore|restoration': 2.5,
            r'maintain|maintenance': 2.0,
            r'homeostasis|homeostatic': 2.5,
            r'synthesis|synthesize': 2.0,
            r'biosynthesis|biosynthetic': 2.0,
            r'formation|form': 1.5,
            r'assembly|assemble': 1.5,
            r'construction|construct': 2.0,
            r'development|develop': 1.5
        }
        
        score = 0.0
        for pattern, weight in constructive_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                score += weight
        
        return score
    
    def _analyze_functional_objectives(self, text: str) -> Dict[str, float]:
        """分析功能目标指示"""
        objectives = {
            'threat_elimination': 0.0,
            'tissue_repair': 0.0,
            'immune_defense': 0.0,
            'structural_maintenance': 0.0,
            'metabolic_support': 0.0
        }
        
        # 威胁消除指示
        threat_patterns = [r'pathogen', r'infection', r'invader', r'foreign', r'threat']
        for pattern in threat_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                objectives['threat_elimination'] += 1.0
        
        # 组织修复指示
        repair_patterns = [r'wound', r'injury', r'damage', r'tissue repair', r'recovery']
        for pattern in repair_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                objectives['tissue_repair'] += 1.0
        
        # 免疫防御指示
        immune_patterns = [r'immune', r'defense', r'protection', r'surveillance']
        for pattern in immune_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                objectives['immune_defense'] += 1.0
        
        # 结构维护指示
        maintenance_patterns = [r'maintenance', r'stability', r'integrity', r'preservation']
        for pattern in maintenance_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                objectives['structural_maintenance'] += 1.0
        
        # 代谢支持指示
        metabolic_patterns = [r'energy', r'metabolism', r'nutrient', r'resource']
        for pattern in metabolic_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                objectives['metabolic_support'] += 1.0
        
        return objectives
    
    def _classify_as_destructive_dominant(self, entry: BiologicalEntry, 
                                        objectives: Dict[str, float]) -> ClassificationDecision:
        """分类破坏性组分占主导的复杂通路"""
        # 检查是否有明确的威胁消除或免疫防御目标
        if objectives['threat_elimination'] > 0 or objectives['immune_defense'] > 0:
            return ClassificationDecision(
                system=_get_system_enum_value('B'),
                confidence=0.8,
                matched_patterns=['destructive_dominant', 'threat_elimination'],
                decision_path=['complex_pathway', 'destructive_dominant', 'system_B']
            )
        else:
            # 可能是细胞死亡相关的System A过程
            return ClassificationDecision(
                system=_get_system_enum_value('A'),
                confidence=0.6,
                matched_patterns=['destructive_dominant', 'cellular_death'],
                decision_path=['complex_pathway', 'destructive_dominant', 'system_A']
            )
    
    def _classify_as_constructive_dominant(self, entry: BiologicalEntry,
                                         objectives: Dict[str, float]) -> ClassificationDecision:
        """分类建设性组分占主导的复杂通路"""
        # 检查具体的建设性目标
        if objectives['tissue_repair'] > 0 or objectives['structural_maintenance'] > 0:
            return ClassificationDecision(
                system=_get_system_enum_value('A'),
                confidence=0.8,
                matched_patterns=['constructive_dominant', 'tissue_repair'],
                decision_path=['complex_pathway', 'constructive_dominant', 'system_A']
            )
        elif objectives['metabolic_support'] > 0:
            return ClassificationDecision(
                system=_get_system_enum_value('C'),
                confidence=0.7,
                matched_patterns=['constructive_dominant', 'metabolic_support'],
                decision_path=['complex_pathway', 'constructive_dominant', 'system_C']
            )
        else:
            # 默认为System A
            return ClassificationDecision(
                system=_get_system_enum_value('A'),
                confidence=0.6,
                matched_patterns=['constructive_dominant', 'default'],
                decision_path=['complex_pathway', 'constructive_dominant', 'system_A_default']
            )
    
    def _classify_balanced_pathway(self, entry: BiologicalEntry,
                                 objectives: Dict[str, float]) -> ClassificationDecision:
        """分类组分平衡的复杂通路"""
        # 基于功能目标的优先级进行决策
        max_objective = max(objectives.items(), key=lambda x: x[1])
        
        if max_objective[1] == 0:
            # 没有明确的功能目标指示，使用标准分类
            standard_result = self.classify_primary_system(entry)
            standard_result.decision_path.append('balanced_pathway_standard_classification')
            return standard_result
        
        objective_name, score = max_objective
        
        if objective_name in ['threat_elimination', 'immune_defense']:
            return ClassificationDecision(
                system=_get_system_enum_value('B'),
                confidence=0.7,
                matched_patterns=['balanced_pathway', objective_name],
                decision_path=['complex_pathway', 'balanced', 'objective_based', 'system_B']
            )
        elif objective_name in ['tissue_repair', 'structural_maintenance']:
            return ClassificationDecision(
                system=_get_system_enum_value('A'),
                confidence=0.7,
                matched_patterns=['balanced_pathway', objective_name],
                decision_path=['complex_pathway', 'balanced', 'objective_based', 'system_A']
            )
        elif objective_name == 'metabolic_support':
            return ClassificationDecision(
                system=_get_system_enum_value('C'),
                confidence=0.7,
                matched_patterns=['balanced_pathway', objective_name],
                decision_path=['complex_pathway', 'balanced', 'objective_based', 'system_C']
            )
        else:
            # 回退到标准分类
            standard_result = self.classify_primary_system(entry)
            standard_result.decision_path.append('balanced_pathway_fallback')
            return standard_result
    
    def _handle_inflammation_process(self, entry: BiologicalEntry) -> ClassificationResult:
        """
        处理炎症过程的特殊决策规则
        
        根据主要功能目标分配：
        - 威胁识别和清除 → System B (B1/B2)
        - 免疫自限/耐受 → System B3
        - 炎症消解和损伤控制结合修复 → System A4
        - 结构修复 → System A (A1-A3)
        """
        search_text = self._build_search_text(entry)
        
        # 威胁识别和清除模式
        threat_patterns = [
            r'pathogen', r'recognition', r'clearance', r'killing', r'cytotox',
            r'antimicrobial', r'bactericidal', r'antiviral'
        ]
        
        # 免疫自限/耐受模式
        tolerance_patterns = [
            r'tolerance', r'regulatory', r'suppression', r'checkpoint',
            r'self-limitation', r'immune regulation'
        ]
        
        # 炎症消解模式
        resolution_patterns = [
            r'resolution', r'resolving', r'efferocytosis', r'lipoxin',
            r'resolvin', r'protectin', r'maresins'
        ]
        
        # 结构修复模式
        repair_patterns = [
            r'repair', r'healing', r'regeneration', r'reconstruction',
            r'tissue repair', r'wound healing'
        ]
        
        # 应用决策规则
        if any(re.search(pattern, search_text, re.IGNORECASE) for pattern in threat_patterns):
            # 威胁清除 → System B
            result = self._standard_classification(entry)
            if result.primary_system not in [FunctionalSystem.SYSTEM_B.value]:
                result.primary_system = FunctionalSystem.SYSTEM_B.value
                result.decision_path.append('inflammation_threat_clearance_rule')
        
        elif any(re.search(pattern, search_text, re.IGNORECASE) for pattern in tolerance_patterns):
            # 免疫自限 → System B3
            result = self._standard_classification(entry)
            result.primary_system = FunctionalSystem.SYSTEM_B.value
            result.subsystem = 'B3'
            result.decision_path.append('inflammation_tolerance_rule')
        
        elif any(re.search(pattern, search_text, re.IGNORECASE) for pattern in resolution_patterns):
            # 炎症消解 → System A4
            result = self._standard_classification(entry)
            result.primary_system = FunctionalSystem.SYSTEM_A.value
            result.subsystem = 'A4'
            result.decision_path.append('inflammation_resolution_rule')
        
        elif any(re.search(pattern, search_text, re.IGNORECASE) for pattern in repair_patterns):
            # 结构修复 → System A
            result = self._standard_classification(entry)
            if result.primary_system not in [FunctionalSystem.SYSTEM_A.value]:
                result.primary_system = FunctionalSystem.SYSTEM_A.value
                result.decision_path.append('inflammation_repair_rule')
        
        else:
            # 标准分类
            result = self._standard_classification(entry)
        
        return result
    
    def _create_system_0_result(self, entry: BiologicalEntry, reason: str) -> ClassificationResult:
        """创建System 0分类结果"""
        return ClassificationResult(
            entry_id=entry.id,
            primary_system=_get_system_enum_value('0'),
            subsystem=None,
            all_systems=[_get_system_enum_value('0')],
            inflammation_polarity=None,
            confidence_score=0.9,
            decision_path=[reason]
        )
    
    def _create_error_result(self, entry: BiologicalEntry, error_msg: str) -> ClassificationResult:
        """创建错误分类结果"""
        return ClassificationResult(
            entry_id=entry.id,
            primary_system=_get_system_enum_value('0'),
            subsystem=None,
            all_systems=[],
            inflammation_polarity=None,
            confidence_score=0.0,
            decision_path=[f'error: {error_msg}']
        )
    
    def _update_stats(self, result: ClassificationResult):
        """更新分类统计"""
        self.classification_stats['total_classified'] += 1
        
        if result.primary_system in self.classification_stats['system_counts']:
            self.classification_stats['system_counts'][result.primary_system] += 1
        else:
            self.classification_stats['unclassified_count'] += 1
    
    def get_classification_stats(self) -> Dict:
        """获取分类统计信息"""
        return self.classification_stats.copy()
    
    def reset_stats(self):
        """重置分类统计"""
        self.classification_stats = {
            'total_classified': 0,
            'system_counts': {system.value: 0 for system in SystemType},
            'unclassified_count': 0
        }


class SubsystemClassifier:
    """
    子系统分类器
    
    实现A1-A4, B1-B3, C1-C3, D1-D2, E1-E2子系统的详细分类。
    """
    
    def __init__(self, classification_rules: Optional[ClassificationRules] = None):
        self.rules = classification_rules or ClassificationRules()
    
    def classify_subsystem_detailed(self, entry: BiologicalEntry, 
                                 primary_system: str) -> Optional[str]:
        """
        详细的子系统分类
        
        Args:
            entry: 待分类的生物学条目
            primary_system: 主系统分类结果
            
        Returns:
            Optional[str]: 详细的子系统分类结果
        """
        if primary_system not in ['A', 'B', 'C', 'D', 'E']:
            return None
        
        search_text = f"{entry.name} {entry.definition or ''}".lower()
        
        # 获取该系统的所有子系统匹配结果
        subsystem_matches = self.rules.match_subsystem_patterns(search_text, primary_system)
        
        if not subsystem_matches:
            return None
        
        # 计算每个子系统的匹配得分
        subsystem_scores = {}
        for subsystem, matches in subsystem_matches.items():
            # 基础得分：匹配模式数量
            base_score = len(matches)
            
            # 特异性加权：某些子系统的模式更具特异性
            specificity_weight = self._get_subsystem_specificity_weight(
                primary_system, subsystem)
            
            subsystem_scores[subsystem] = base_score * specificity_weight
        
        # 返回得分最高的子系统
        best_subsystem = max(subsystem_scores.keys(), 
                           key=lambda x: subsystem_scores[x])
        
        return best_subsystem
    
    def _get_subsystem_specificity_weight(self, system: str, subsystem: str) -> float:
        """获取子系统特异性权重"""
        # 定义特异性权重，某些子系统的关键词更具特异性
        specificity_weights = {
            'A': {
                'A1': 1.2,  # DNA修复相关关键词特异性较高
                'A2': 1.0,  # 细胞命运相关
                'A3': 0.9,  # 细胞稳态相关，可能与其他系统重叠
                'A4': 1.1   # 炎症消解相关
            },
            'B': {
                'B1': 1.0,  # 先天免疫
                'B2': 1.1,  # 适应性免疫，特异性较高
                'B3': 1.2   # 免疫调节，特异性最高
            },
            'C': {
                'C1': 1.0,  # 能量代谢
                'C2': 1.0,  # 生物合成
                'C3': 1.1   # 解毒，特异性较高
            },
            'D': {
                'D1': 1.0,  # 神经调节
                'D2': 1.1   # 内分泌调节，特异性较高
            },
            'E': {
                'E1': 1.1,  # 生殖，特异性较高
                'E2': 1.0   # 发育
            }
        }
        
        return specificity_weights.get(system, {}).get(subsystem, 1.0)


class InflammationPolarityAnnotator:
    """
    炎症极性标注器
    
    专门用于识别和标注炎症相关过程的极性属性。
    """
    
    def __init__(self, classification_rules: Optional[ClassificationRules] = None):
        self.rules = classification_rules or ClassificationRules()
    
    def annotate_polarity(self, entry: BiologicalEntry) -> Optional[str]:
        """
        标注炎症极性
        
        Args:
            entry: 待标注的生物学条目
            
        Returns:
            Optional[str]: 炎症极性标注结果
        """
        search_text = f"{entry.name} {entry.definition or ''}".lower()
        
        # 获取炎症模式匹配结果
        inflammation_matches = self.rules.match_inflammation_patterns(search_text)
        
        if not inflammation_matches:
            return None
        
        # 计算各极性的得分
        polarity_scores = {}
        
        for polarity, matches in inflammation_matches.items():
            # 基础得分
            base_score = len(matches)
            
            # 特异性权重
            specificity_weight = self._get_polarity_specificity_weight(polarity)
            
            polarity_scores[polarity] = base_score * specificity_weight
        
        # 返回得分最高的极性
        best_polarity = max(polarity_scores.keys(), 
                          key=lambda x: polarity_scores[x])
        
        return best_polarity
    
    def _get_polarity_specificity_weight(self, polarity: str) -> float:
        """获取极性特异性权重"""
        # 促消解 > 抗炎 > 促炎 的特异性权重
        weights = {
            'pro-resolving': 1.3,    # 最高特异性
            'anti-inflammatory': 1.1, # 中等特异性
            'pro-inflammatory': 1.0   # 基础特异性
        }
        
        return weights.get(polarity, 1.0)
    
    def is_inflammation_related(self, entry: BiologicalEntry) -> bool:
        """检查条目是否与炎症相关"""
        search_text = f"{entry.name} {entry.definition or ''}".lower()
        inflammation_matches = self.rules.match_inflammation_patterns(search_text)
        return bool(inflammation_matches)