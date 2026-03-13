#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v8概率分类器 - 支持多标签概率分布的分类方式

不再使用排他性分类，而是：
1. 计算每个系统的匹配得分
2. 根据关键词匹配情况分配概率
3. 支持多系统同时激活
4. 提供更全面的分类覆盖
"""

import re
import sys
import json
import math
from collections import defaultdict, Counter

class ProbabilisticClassifier:
    """
    概率分类器：支持多标签概率分布
    """
    def __init__(self):
        # 系统权重：不同系统的基础权重
        self.system_weights = {
            "0": 0.8,   # 通用基础类权重较低，避免过度分类
            "A": 1.0,   # 细胞韧性
            "B": 1.2,   # 免疫系统权重稍高（中药特点）
            "C": 1.0,   # 代谢系统
            "D": 1.0,   # 神经内分泌
            "E": 1.0    # 生殖发育
        }
        
        # 关键词权重：不同重要性的关键词有不同权重
        self.keyword_weights = {
            "high": 3.0,    # 高权重关键词
            "medium": 2.0,  # 中权重关键词
            "low": 1.0      # 低权重关键词
        }
        
        # 第0类关键词（通用基础）- 权重较低，避免过度分类
        self.cat0_keywords = {
            "high": ["ribosome", "ribosomal", "proteasome", "spliceosome"],
            "medium": ["translation", "rna polymerase", "dna replication"],
            "low": ["ubiquitin", "protein folding", "rna splicing"]
        }
        
        # 五大系统分类规则（按权重分级）
        self.classification_rules = {
            "A": {
                "description": "基础稳态与细胞韧性 (Cellular Resilience)",
                "subclasses": {
                    "A1": {
                        "name": "基因组稳定性与修复 (Genome Stability)",
                        "keywords": {
                            "high": ["dna repair", "dna damage", "homologous recombination"],
                            "medium": ["excision repair", "mismatch repair", "p53", "telomere"],
                            "low": ["checkpoint", "dna integrity", "mutation repair"]
                        }
                    },
                    "A2": {
                        "name": "细胞命运：增殖与死亡 (Proliferation & Death)",
                        "keywords": {
                            "high": ["apoptosis", "cell cycle", "cell death"],
                            "medium": ["apoptotic", "necrosis", "autophagy", "mitosis"],
                            "low": ["proliferation", "growth", "caspase", "bcl-2"]
                        }
                    },
                    "A3": {
                        "name": "细胞稳态与运输 (Homeostasis & Transport)",
                        "keywords": {
                            "high": ["transport", "membrane transport", "homeostasis"],
                            "medium": ["ion channel", "cytoskeleton", "endocytosis"],
                            "low": ["motility", "junction", "adhesion", "vesicle", "trafficking"]
                        }
                    }
                }
            },
            "B": {
                "description": "免疫与防御系统 (Immunity & Defense)",
                "subclasses": {
                    "B1": {
                        "name": "固有免疫 (Innate)",
                        "keywords": {
                            "high": ["innate immune", "inflammation", "inflammatory"],
                            "medium": ["toll-like", "complement", "phagocytosis", "interferon"],
                            "low": ["neutrophil", "macrophage", "nf-kappa b", "cytokine-cytokine"]
                        }
                    },
                    "B2": {
                        "name": "适应性免疫 (Adaptive)",
                        "keywords": {
                            "high": ["adaptive immune", "immune response", "antibody"],
                            "medium": ["t cell", "b cell", "antigen", "mhc", "lymphocyte"],
                            "low": ["immunoglobulin", "immunological", "cd4", "cd8", "tcr"]
                        }
                    }
                }
            },
            "C": {
                "description": "代谢韧性 (Metabolic Resilience)",
                "subclasses": {
                    "C1": {
                        "name": "能量代谢 (Energy)",
                        "keywords": {
                            "high": ["glycolysis", "glycolytic", "energy metabolism", "mitochondrial"],
                            "medium": ["tca cycle", "oxidative phosphorylation", "atp synthesis"],
                            "low": ["glucose metabolism", "fatty acid oxidation", "respiration", "metabolic process"]
                        }
                    },
                    "C2": {
                        "name": "生物合成 (Biosynthesis)",
                        "keywords": {
                            "high": ["biosynthesis", "biosynthetic", "anabolism"],
                            "medium": ["fatty acid biosynthesis", "amino acid biosynthesis"],
                            "low": ["protein synthesis", "lipogenesis", "steroid biosynthesis"]
                        }
                    },
                    "C3": {
                        "name": "解毒与异物代谢 (Detoxification)",
                        "keywords": {
                            "high": ["xenobiotics", "detoxification", "drug metabolism"],
                            "medium": ["cytochrome p450", "glutathione", "oxidative stress"],
                            "low": ["antioxidant", "peroxisome", "reactive oxygen"]
                        }
                    }
                }
            },
            "D": {
                "description": "神经内分泌调节 (Neuro-Endocrine)",
                "subclasses": {
                    "D1": {
                        "name": "神经调节 (Neural)",
                        "keywords": {
                            "high": ["nervous system", "synaptic", "neurotransmitter"],
                            "medium": ["synapse", "neuron", "neuronal", "neuroactive"],
                            "low": ["brain", "axon", "dopaminergic", "serotonergic", "behavior"]
                        }
                    },
                    "D2": {
                        "name": "内分泌调节 (Endocrine)",
                        "keywords": {
                            "high": ["endocrine", "hormone", "steroid hormone"],
                            "medium": ["insulin", "glucagon", "thyroid", "estrogen"],
                            "low": ["cortisol", "androgen", "ppar signaling", "adipocytokine"]
                        }
                    }
                }
            },
            "E": {
                "description": "生殖与发育 (Reproduction & Development)",
                "subclasses": {
                    "E1": {
                        "name": "生殖 (Reproduction)",
                        "keywords": {
                            "high": ["reproduction", "reproductive", "meiosis"],
                            "medium": ["meiotic", "gamete", "fertilization"],
                            "low": ["sperm", "oocyte", "ovarian", "progesterone"]
                        }
                    },
                    "E2": {
                        "name": "发育与分化 (Development)",
                        "keywords": {
                            "high": ["development", "differentiation", "morphogenesis"],
                            "medium": ["embryo", "organogenesis", "maturation"],
                            "low": ["aging", "senescence", "longevity"]
                        }
                    }
                }
            }
        }
    
    def calculate_system_scores(self, term_id, description, source_type="GO"):
        """
        计算每个系统的匹配得分
        返回: {system_code: {subsystem_code: score}}
        """
        desc_lower = description.lower()
        system_scores = defaultdict(lambda: defaultdict(float))
        
        # 1. 计算第0类得分
        cat0_score = 0.0
        for weight_level, keywords in self.cat0_keywords.items():
            weight = self.keyword_weights[weight_level]
            for keyword in keywords:
                if keyword in desc_lower:
                    cat0_score += weight
        
        if cat0_score > 0:
            system_scores["0"]["0"] = cat0_score * self.system_weights["0"]
        
        # 2. 计算五大系统得分
        for main_code, system_info in self.classification_rules.items():
            for sub_code, sub_info in system_info["subclasses"].items():
                sub_score = 0.0
                
                for weight_level, keywords in sub_info["keywords"].items():
                    weight = self.keyword_weights[weight_level]
                    for keyword in keywords:
                        if keyword in desc_lower:
                            sub_score += weight
                
                if sub_score > 0:
                    # 应用系统权重
                    final_score = sub_score * self.system_weights[main_code]
                    system_scores[main_code][sub_code] = final_score
        
        return system_scores
    
    def scores_to_probabilities(self, system_scores, min_threshold=0.1):
        """
        将得分转换为概率分布
        """
        # 收集所有非零得分
        all_scores = []
        score_mapping = {}  # {(main, sub): score}
        
        for main_code, sub_scores in system_scores.items():
            for sub_code, score in sub_scores.items():
                if score > 0:
                    all_scores.append(score)
                    score_mapping[(main_code, sub_code)] = score
        
        if not all_scores:
            return {}
        
        # 计算总得分
        total_score = sum(all_scores)
        
        # 转换为概率
        probabilities = {}
        for (main_code, sub_code), score in score_mapping.items():
            prob = score / total_score
            if prob >= min_threshold:  # 只保留超过阈值的概率
                probabilities[f"{main_code}{sub_code}"] = prob
        
        # 重新归一化
        if probabilities:
            total_prob = sum(probabilities.values())
            probabilities = {k: v/total_prob for k, v in probabilities.items()}
        
        return probabilities
    
    def classify_term_probabilistic(self, term_id, description, source_type="GO", min_threshold=0.1):
        """
        概率分类：返回多个可能的分类及其概率
        """
        # 计算系统得分
        system_scores = self.calculate_system_scores(term_id, description, source_type)
        
        # 转换为概率分布
        probabilities = self.scores_to_probabilities(system_scores, min_threshold)
        
        return probabilities
    
    def get_top_classification(self, probabilities, threshold=0.3):
        """
        获取最高概率的分类（用于兼容原有接口）
        """
        if not probabilities:
            return ("U", "U", "未分类 (Unclassified)", "其他 (Others)")
        
        # 找到最高概率的分类
        top_category = max(probabilities.items(), key=lambda x: x[1])[0]
        
        if len(top_category) >= 2:
            main_cat = top_category[0]
            sub_cat = top_category[:2]
            
            # 获取名称
            if main_cat == "0":
                main_name = "通用基础类 (General)"
                sub_name = "通用分子机器 (Molecular Machinery)"
            elif main_cat in self.classification_rules:
                main_name = self.classification_rules[main_cat]["description"]
                if sub_cat in self.classification_rules[main_cat]["subclasses"]:
                    sub_name = self.classification_rules[main_cat]["subclasses"][sub_cat]["name"]
                else:
                    sub_name = "未知子类"
            else:
                main_name = "未分类 (Unclassified)"
                sub_name = "其他 (Others)"
            
            return (main_cat, sub_cat, main_name, sub_name)
        
        return ("U", "U", "未分类 (Unclassified)", "其他 (Others)")
    
    def classify_term(self, term_id, description, source_type="GO"):
        """
        兼容原有接口的分类方法
        """
        probabilities = self.classify_term_probabilistic(term_id, description, source_type)
        return self.get_top_classification(probabilities)

class EnhancedClassificationAnalyzer:
    """
    增强的分类分析器，支持概率分布分析
    """
    def __init__(self):
        self.classifier = ProbabilisticClassifier()
        self.kg_path = Path("data/03_integrated/knowledge_graphs")
        self.output_path = Path("data/06_probabilistic_classification")
        self.output_path.mkdir(parents=True, exist_ok=True)
    
    def analyze_probabilistic_coverage(self):
        """
        分析概率分类的覆盖情况
        """
        print("🔍 分析概率分类覆盖情况...")
        
        # 加载知识图谱数据
        nodes_df = pd.read_csv(self.kg_path / "enhanced_kg_nodes.csv")
        
        # 分析GO术语
        go_terms = nodes_df[nodes_df['type'] == 'go_term']
        go_coverage_stats = self.analyze_term_coverage(go_terms, "GO")
        
        # 分析KEGG通路
        kegg_pathways = nodes_df[nodes_df['type'] == 'kegg_pathway']
        kegg_coverage_stats = self.analyze_term_coverage(kegg_pathways, "KEGG")
        
        return go_coverage_stats, kegg_coverage_stats
    
    def analyze_term_coverage(self, terms_df, term_type):
        """
        分析术语的分类覆盖情况
        """
        print(f"\n📊 分析{term_type}术语覆盖情况...")
        
        coverage_stats = {
            "total": len(terms_df),
            "classified": 0,
            "multi_label": 0,
            "system_distribution": defaultdict(int),
            "probability_distribution": []
        }
        
        for _, term in terms_df.iterrows():
            term_id = term['id']
            term_name = term['name']
            
            # 获取概率分布
            probabilities = self.classifier.classify_term_probabilistic(term_id, term_name, term_type)
            
            if probabilities:
                coverage_stats["classified"] += 1
                
                # 检查是否为多标签
                if len(probabilities) > 1:
                    coverage_stats["multi_label"] += 1
                
                # 统计系统分布
                for category, prob in probabilities.items():
                    main_system = category[0] if len(category) > 0 else 'U'
                    coverage_stats["system_distribution"][main_system] += prob
                
                # 记录概率分布
                coverage_stats["probability_distribution"].append({
                    "term_id": term_id,
                    "term_name": term_name,
                    "probabilities": probabilities
                })
        
        # 计算覆盖率
        coverage_rate = coverage_stats["classified"] / coverage_stats["total"] * 100
        multi_label_rate = coverage_stats["multi_label"] / coverage_stats["classified"] * 100 if coverage_stats["classified"] > 0 else 0
        
        print(f"   总术语数: {coverage_stats['total']:,}")
        print(f"   成功分类: {coverage_stats['classified']:,} ({coverage_rate:.1f}%)")
        print(f"   多标签分类: {coverage_stats['multi_label']:,} ({multi_label_rate:.1f}%)")
        
        print(f"   系统分布:")
        system_names = {
            '0': '通用基础类', 'A': '细胞韧性', 'B': '免疫防御',
            'C': '代谢韧性', 'D': '神经内分泌', 'E': '生殖发育'
        }
        
        for system, count in sorted(coverage_stats["system_distribution"].items()):
            system_name = system_names.get(system, system)
            print(f"     {system}: {system_name} - {count:.1f}")
        
        return coverage_stats

def main():
    """测试概率分类器"""
    print("🚀 测试概率分类器")
    print("=" * 50)
    
    classifier = ProbabilisticClassifier()
    
    # 测试用例
    test_cases = [
        ("GO:0006955", "immune response", "应该同时匹配B1和B2"),
        ("GO:0006096", "glycolytic process", "应该匹配C1"),
        ("GO:0006281", "DNA repair", "应该匹配A1"),
        ("GO:0007268", "synaptic transmission", "应该匹配D1"),
        ("GO:0000003", "reproduction", "应该匹配E1"),
        ("hsa04110", "Cell cycle", "应该匹配A2"),
        ("test", "immune system development", "应该同时匹配B和E系统"),
        ("test", "metabolic immune response", "应该同时匹配C和B系统"),
    ]
    
    print("🧪 概率分类测试:")
    for term_id, description, expected in test_cases:
        print(f"\n📋 {term_id}: {description}")
        print(f"   预期: {expected}")
        
        # 获取概率分布
        probabilities = classifier.classify_term_probabilistic(term_id, description)
        
        if probabilities:
            print(f"   概率分布:")
            for category, prob in sorted(probabilities.items(), key=lambda x: x[1], reverse=True):
                print(f"     {category}: {prob:.3f}")
        else:
            print(f"   结果: 未分类")
        
        # 获取最高概率分类（兼容性）
        top_class = classifier.get_top_classification(probabilities)
        print(f"   最高概率: {top_class[0]}{top_class[1]} - {top_class[3]}")

if __name__ == "__main__":
    main()