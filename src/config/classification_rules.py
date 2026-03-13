"""
分类规则配置

定义了五大功能系统分类的具体规则和模式。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Pattern, Set
import re
from enum import Enum


class SystemType(Enum):
    """系统类型枚举"""
    SYSTEM_A = "A"
    SYSTEM_B = "B" 
    SYSTEM_C = "C"
    SYSTEM_D = "D"
    SYSTEM_E = "E"
    SYSTEM_0 = "0"


@dataclass
class ClassificationRules:
    """
    分类规则配置类
    
    包含五大功能系统的分类规则、关键词模式、子系统规则等。
    """
    
    # System A: Self-Healing & Structural Reconstruction
    system_a_patterns: List[str] = field(default_factory=lambda: [
        # A1: Genomic Stability and Repair
        r"DNA repair", r"DNA damage", r"genome stability", r"chromosome", r"telomere",
        r"DNA replication", r"DNA recombination", r"mismatch repair", r"base excision repair",
        r"nucleotide excision repair", r"homologous recombination", r"non-homologous end joining",
        
        # A2: Somatic Maintenance, Turnover, and Identity Preservation  
        r"stem cell", r"progenitor", r"differentiation", r"cell fate", r"lineage",
        r"senescence", r"apoptosis", r"programmed cell death", r"tissue homeostasis",
        r"cell cycle", r"proliferation", r"regeneration", r"wound healing",
        
        # A3: Cellular Homeostasis and Structural Maintenance
        r"protein folding", r"proteostasis", r"autophagy", r"mitophagy", r"lysosome",
        r"endoplasmic reticulum", r"organelle", r"cytoskeleton", r"membrane",
        r"ion transport", r"ion homeostasis", r"osmotic", r"pH regulation",
        r"extracellular matrix", r"ECM", r"collagen", r"angiogenesis",
        
        # A4: Inflammation Resolution and Damage Containment
        r"resolution", r"efferocytosis", r"pro-resolving", r"lipoxin", r"resolvin",
        r"protectin", r"maresins", r"tissue repair", r"barrier function"
    ])
    
    # System B: Immune Defense
    system_b_patterns: List[str] = field(default_factory=lambda: [
        # B1: Innate Immunity
        r"innate immun", r"pattern recognition", r"PRR", r"TLR", r"toll-like receptor",
        r"inflammasome", r"complement", r"phagocytosis", r"neutrophil", r"macrophage",
        r"dendritic cell", r"natural killer", r"NK cell", r"interferon", r"cytokine",
        r"immune response", r"inflammatory response", r"inflammation",
        
        # B2: Adaptive Immunity
        r"adaptive immun", r"T cell", r"B cell", r"antibody", r"immunoglobulin",
        r"antigen presentation", r"MHC", r"TCR", r"BCR", r"clonal selection",
        r"immune memory", r"vaccination", r"cytotoxic", r"helper T cell",
        
        # B3: Immune Regulation and Tolerance
        r"immune regulation", r"tolerance", r"regulatory T cell", r"Treg",
        r"immune checkpoint", r"PD-1", r"CTLA-4", r"immunosuppression",
        r"self-tolerance", r"peripheral tolerance", r"anergy"
    ])
    
    # System C: Energy & Metabolic Homeostasis
    system_c_patterns: List[str] = field(default_factory=lambda: [
        # C1: Energy Metabolism and Catabolism
        r"glycolysis", r"gluconeogenesis", r"citric acid cycle", r"TCA cycle",
        r"oxidative phosphorylation", r"electron transport", r"ATP synthesis",
        r"fatty acid oxidation", r"beta-oxidation", r"amino acid catabolism",
        
        # C2: Biosynthesis and Anabolism
        r"biosynthesis", r"anabolism", r"fatty acid synthesis", r"cholesterol synthesis",
        r"protein synthesis", r"amino acid synthesis", r"nucleotide synthesis",
        r"glycogen synthesis", r"lipogenesis", r"steroid synthesis",
        
        # C3: Detoxification and Metabolic Stress Handling
        r"detoxification", r"xenobiotic", r"drug metabolism", r"cytochrome P450",
        r"glutathione", r"oxidative stress", r"antioxidant", r"reactive oxygen species",
        r"ROS", r"peroxisome", r"phase I metabolism", r"phase II metabolism"
    ])
    
    # System D: Cognitive-Regulatory (Neuro-Endocrine Control)
    system_d_patterns: List[str] = field(default_factory=lambda: [
        # D1: Neural Regulation and Signal Transmission
        r"neural", r"neuron", r"synapse", r"neurotransmitter", r"action potential",
        r"signal transduction", r"sensory", r"motor", r"reflex", r"nervous system",
        r"brain", r"spinal cord", r"peripheral nerve", r"axon", r"dendrite",
        r"nervous system development", r"neural development",
        
        # D2: Endocrine and Autonomic Regulation
        r"hormone", r"endocrine", r"hypothalamus", r"pituitary", r"adrenal",
        r"thyroid", r"insulin", r"glucagon", r"cortisol", r"growth hormone",
        r"autonomic", r"sympathetic", r"parasympathetic", r"circadian", r"rhythm"
    ])
    
    # System E: Reproduction & Continuity
    system_e_patterns: List[str] = field(default_factory=lambda: [
        # E1: Reproduction
        r"reproduction", r"reproductive", r"gamete", r"sperm", r"egg", r"oocyte",
        r"fertilization", r"mating", r"sexual", r"gonad", r"testis", r"ovary",
        r"pregnancy", r"gestation", r"embryo", r"fetus", r"placenta", r"lactation",
        
        # E2: Development and Reproductive Maturation
        r"development", r"embryonic", r"morphogenesis", r"organogenesis",
        r"pattern formation", r"cell migration", r"gastrulation", r"neurulation",
        r"limb development", r"sex determination", r"puberty", r"maturation"
    ])
    
    # System 0: General Molecular Machinery
    system_0_patterns: List[str] = field(default_factory=lambda: [
        r"transcription", r"translation", r"ribosome", r"RNA processing",
        r"splicing", r"mRNA", r"tRNA", r"rRNA", r"protein transport",
        r"vesicle transport", r"endocytosis", r"exocytosis", r"secretion",
        r"cell division", r"mitosis", r"meiosis", r"chromosome segregation"
    ])
    
    # 炎症相关模式
    inflammation_patterns: Dict[str, List[str]] = field(default_factory=lambda: {
        "pro-inflammatory": [
            r"pro-inflammatory", r"inflammatory", r"IL-1", r"TNF", r"IL-6",
            r"NF-kB", r"inflammasome", r"pyroptosis", r"inflammatory response"
        ],
        "anti-inflammatory": [
            r"anti-inflammatory", r"IL-10", r"TGF-beta", r"regulatory",
            r"suppression", r"tolerance", r"resolution", r"dampening"
        ],
        "pro-resolving": [
            r"pro-resolving", r"resolution", r"lipoxin", r"resolvin", r"protectin",
            r"maresins", r"efferocytosis", r"tissue repair"
        ]
    })
    
    # 子系统分类规则
    subsystem_rules: Dict[str, Dict[str, List[str]]] = field(default_factory=lambda: {
        "A": {
            "A1": [r"DNA", r"genome", r"chromosome", r"telomere", r"repair"],
            "A2": [r"stem", r"differentiation", r"senescence", r"apoptosis", r"regeneration"],
            "A3": [r"protein folding", r"autophagy", r"organelle", r"homeostasis", r"cytoskeleton"],
            "A4": [r"resolution", r"efferocytosis", r"pro-resolving", r"tissue repair"]
        },
        "B": {
            "B1": [r"innate", r"pattern recognition", r"TLR", r"complement", r"phagocytosis"],
            "B2": [r"adaptive", r"T cell", r"B cell", r"antibody", r"antigen"],
            "B3": [r"regulation", r"tolerance", r"regulatory", r"checkpoint", r"suppression"]
        },
        "C": {
            "C1": [r"glycolysis", r"oxidation", r"catabolism", r"ATP", r"energy"],
            "C2": [r"biosynthesis", r"anabolism", r"synthesis", r"lipogenesis"],
            "C3": [r"detoxification", r"xenobiotic", r"cytochrome P450", r"antioxidant"]
        },
        "D": {
            "D1": [r"neural", r"neuron", r"synapse", r"neurotransmitter", r"nervous"],
            "D2": [r"hormone", r"endocrine", r"autonomic", r"circadian"]
        },
        "E": {
            "E1": [r"reproduction", r"gamete", r"fertilization", r"pregnancy", r"lactation"],
            "E2": [r"development", r"embryonic", r"morphogenesis", r"maturation"]
        }
    })
    
    # 排除模式（通用生物过程）
    exclusion_patterns: List[str] = field(default_factory=lambda: [
        r"^biological_process$",
        r"^cellular_process$", 
        r"^metabolic_process$",
        r"^regulation of biological_process$",
        r"^positive regulation of biological_process$",
        r"^negative regulation of biological_process$",
        r"^cellular component organization$",
        r"^biological regulation$"
    ])
    
    # 优先级规则（数字越小优先级越高）
    system_priority: Dict[str, int] = field(default_factory=lambda: {
        "B": 1,  # 免疫防御优先级最高
        "A": 2,  # 自愈重建次之
        "D": 3,  # 认知调节
        "E": 4,  # 繁殖延续
        "C": 5,  # 能量代谢
        "0": 6   # 通用机制优先级最低
    })
    
    def __post_init__(self):
        """编译正则表达式模式"""
        self._compiled_patterns = {}
        
        # 编译系统模式
        for system in ['A', 'B', 'C', 'D', 'E', '0']:
            patterns = getattr(self, f'system_{system.lower()}_patterns')
            self._compiled_patterns[system] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
        
        # 编译炎症模式
        self._compiled_inflammation_patterns = {}
        for polarity, patterns in self.inflammation_patterns.items():
            self._compiled_inflammation_patterns[polarity] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
        
        # 编译子系统模式
        self._compiled_subsystem_patterns = {}
        for system, subsystems in self.subsystem_rules.items():
            self._compiled_subsystem_patterns[system] = {}
            for subsystem, patterns in subsystems.items():
                self._compiled_subsystem_patterns[system][subsystem] = [
                    re.compile(pattern, re.IGNORECASE) for pattern in patterns
                ]
        
        # 编译排除模式
        self._compiled_exclusion_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.exclusion_patterns
        ]
    
    def get_compiled_patterns(self, system: str) -> List[Pattern]:
        """获取编译后的系统模式"""
        return self._compiled_patterns.get(system, [])
    
    def get_compiled_inflammation_patterns(self, polarity: str) -> List[Pattern]:
        """获取编译后的炎症模式"""
        return self._compiled_inflammation_patterns.get(polarity, [])
    
    def get_compiled_subsystem_patterns(self, system: str, subsystem: str) -> List[Pattern]:
        """获取编译后的子系统模式"""
        return self._compiled_subsystem_patterns.get(system, {}).get(subsystem, [])
    
    def get_compiled_exclusion_patterns(self) -> List[Pattern]:
        """获取编译后的排除模式"""
        return self._compiled_exclusion_patterns
    
    def is_excluded_term(self, text: str) -> bool:
        """检查是否为排除的通用术语"""
        for pattern in self.get_compiled_exclusion_patterns():
            if pattern.search(text):
                return True
        return False
    
    def match_system_patterns(self, text: str, system: str) -> List[str]:
        """匹配系统模式，返回匹配的模式列表"""
        matches = []
        patterns = self.get_compiled_patterns(system)
        for pattern in patterns:
            if pattern.search(text):
                matches.append(pattern.pattern)
        return matches
    
    def match_inflammation_patterns(self, text: str) -> Dict[str, List[str]]:
        """匹配炎症模式，返回各极性的匹配结果"""
        matches = {}
        for polarity in self.inflammation_patterns.keys():
            polarity_matches = []
            patterns = self.get_compiled_inflammation_patterns(polarity)
            for pattern in patterns:
                if pattern.search(text):
                    polarity_matches.append(pattern.pattern)
            if polarity_matches:
                matches[polarity] = polarity_matches
        return matches
    
    def match_subsystem_patterns(self, text: str, system: str) -> Dict[str, List[str]]:
        """匹配子系统模式，返回各子系统的匹配结果"""
        matches = {}
        if system not in self.subsystem_rules:
            return matches
        
        for subsystem in self.subsystem_rules[system].keys():
            subsystem_matches = []
            patterns = self.get_compiled_subsystem_patterns(system, subsystem)
            for pattern in patterns:
                if pattern.search(text):
                    subsystem_matches.append(pattern.pattern)
            if subsystem_matches:
                matches[subsystem] = subsystem_matches
        return matches
    
    def get_system_priority(self, system: str) -> int:
        """获取系统优先级"""
        return self.system_priority.get(system, 999)
    
    def sort_systems_by_priority(self, systems: List[str]) -> List[str]:
        """按优先级排序系统列表"""
        return sorted(systems, key=self.get_system_priority)
    
    def add_custom_pattern(self, system: str, pattern: str):
        """添加自定义模式"""
        if system in ['A', 'B', 'C', 'D', 'E', '0']:
            patterns_attr = f'system_{system.lower()}_patterns'
            current_patterns = getattr(self, patterns_attr)
            current_patterns.append(pattern)
            
            # 重新编译模式
            self._compiled_patterns[system].append(re.compile(pattern, re.IGNORECASE))
    
    def add_custom_subsystem_pattern(self, system: str, subsystem: str, pattern: str):
        """添加自定义子系统模式"""
        if system in self.subsystem_rules and subsystem in self.subsystem_rules[system]:
            self.subsystem_rules[system][subsystem].append(pattern)
            
            # 重新编译模式
            if system not in self._compiled_subsystem_patterns:
                self._compiled_subsystem_patterns[system] = {}
            if subsystem not in self._compiled_subsystem_patterns[system]:
                self._compiled_subsystem_patterns[system][subsystem] = []
            
            self._compiled_subsystem_patterns[system][subsystem].append(
                re.compile(pattern, re.IGNORECASE)
            )


# 默认分类规则实例
default_classification_rules = ClassificationRules()