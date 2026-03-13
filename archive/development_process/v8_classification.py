import re
import sys
import json
from collections import defaultdict

class BioDataParser:
    """
    负责解析 go-basic.txt 和 br_br08901.txt 原始文件的类。
    保持不变，提供基础数据读取功能。
    """
    def __init__(self):
        self.go_terms = {}  # {go_id: {'name': name, 'namespace': namespace}}
        self.kegg_hierarchy = {} # {pathway_id: {'name': name, 'hierarchy': [A, B, C]}}

    def parse_go_basic(self, file_path):
        """解析 OBO 格式的 GO 文件"""
        print(f"正在加载 GO 数据库: {file_path} ...")
        current_term = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line == "[Term]":
                        if current_term and 'id' in current_term:
                            self.go_terms[current_term['id']] = current_term
                        current_term = {}
                    elif line.startswith("id: "):
                        current_term['id'] = line[4:]
                    elif line.startswith("name: "):
                        current_term['name'] = line[6:]
                    elif line.startswith("namespace: "):
                        current_term['namespace'] = line[11:]
            if current_term and 'id' in current_term:
                self.go_terms[current_term['id']] = current_term
            print(f"GO 数据加载完成，共 {len(self.go_terms)} 个条目。")
        except FileNotFoundError:
            print(f"错误: 找不到文件 {file_path}")

    def parse_kegg_brite(self, file_path):
        """解析 KEGG BRITE 层级文件 (br08901)"""
        print(f"正在加载 KEGG 数据库: {file_path} ...")
        hierarchy_stack = {'A': None, 'B': None, 'C': None}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('A'):
                        hierarchy_stack['A'] = line[1:].strip()
                    elif line.startswith('B'):
                        hierarchy_stack['B'] = line[1:].strip()
                    elif line.startswith('C'):
                        parts = line[1:].strip().split(maxsplit=1)
                        if len(parts) == 2:
                            path_id = parts[0]
                            path_name = parts[1]
                            if path_id.isdigit(): 
                                self.kegg_hierarchy[path_id] = {
                                    'name': path_name,
                                    'level_A': hierarchy_stack['A'],
                                    'level_B': hierarchy_stack['B']
                                }
            print(f"KEGG 数据加载完成，共 {len(self.kegg_hierarchy)} 个通路。")
        except FileNotFoundError:
            print(f"错误: 找不到文件 {file_path}")

class DetailedClassifier:
    """
    基于用户'细分功能分类体系构建.docx'的高级分类器。
    包含第0类 + 5大系统 + 14个子类。
    """
    def __init__(self):
        # ---------------------------------------------------------------------
        # 第0类：通用基础/分子机器 (General/Housekeeping Machinery)
        # 严格限制为分子机器和最底层的维持功能，避免覆盖有调节意义的代谢或修复通路
        # ---------------------------------------------------------------------
        self.cat0_keywords = [
            "ribosome", "ribosomal", "translation", "trna processing", # 翻译机器
            "proteasome", "ubiquitin", "protein folding", # 蛋白质量控制基础
            "spliceosome", "rna splicing", "mrna processing", # RNA加工基础
            "basal transcription", "rna polymerase", # 基础转录机器
            "dna replication", "chromosome segregation" # 基础复制 (区分于 DNA Repair)
        ]

        # ---------------------------------------------------------------------
        # 细分分类规则 (Hierarchical Rules)
        # 结构: Main_System -> { Sub_System_ID: { 'name': str, 'keywords': [list] } }
        # ---------------------------------------------------------------------
        self.classification_rules = {
            "B": { # 免疫优先判断，因为特异性高
                "description": "免疫与防御系统 (Immunity & Defense)",
                "subclasses": {
                    "B1": {"name": "固有免疫 (Innate)", "keywords": ["innate immune", "inflammation", "inflammatory", "toll-like", "nod-like", "rig-i", "phagocytosis", "complement activation", "neutrophil", "macrophage", "cytokine production", "interferon", "interleukin", "nf-kappa b", "pattern recognition", "cytokine-cytokine"]},
                    "B2": {"name": "适应性免疫 (Adaptive)", "keywords": ["adaptive immune", "t cell", "b cell", "antigen", "antibody", "mhc", "lymphocyte", "th1", "th2", "th17", "immunoglobulin", "hematopoietic", "immune response", "immunological", "cd4", "cd8", "tcr"]}
                }
            },
            "D": { # 神经内分泌次之
                "description": "神经内分泌调节 (Neuro-Endocrine)",
                "subclasses": {
                    "D1": {"name": "神经调节 (Neural)", "keywords": ["nervous system", "synapse", "synaptic", "neurotransmitter", "axon", "neuron", "neuronal", "brain", "cholinergic", "dopaminergic", "serotonergic", "glutamatergic", "neurotrophin", "neuroactive", "ligand-receptor", "feeding behavior", "behavior"]},
                    "D2": {"name": "内分泌调节 (Endocrine)", "keywords": ["endocrine", "hormone", "insulin", "glucagon", "cortisol", "thyroid", "estrogen", "androgen", "steroid hormone", "adipocytokine", "ppar signaling", "renin-angiotensin"]}
                }
            },
            "E": { # 生殖发育
                "description": "生殖与发育 (Reproduction & Development)",
                "subclasses": {
                    "E1": {"name": "生殖 (Reproduction)", "keywords": ["reproduction", "reproductive", "meiosis", "meiotic", "gamete", "sperm", "oocyte", "fertilization", "ovarian", "progesterone"]},
                    "E2": {"name": "发育与分化 (Development)", "keywords": ["development", "differentiation", "morphogenesis", "embryo", "organogenesis", "aging", "senescence", "longevity", "maturation"]}
                }
            },
            "C": { # 代谢 (细分)
                "description": "代谢韧性 (Metabolic Resilience)",
                "subclasses": {
                    "C3": {"name": "解毒与异物代谢 (Detoxification)", "keywords": ["xenobiotics", "xenobiotic", "drug metabolism", "cytochrome p450", "glutathione", "detoxification", "antioxidant", "peroxisome", "phase i", "phase ii", "oxidative stress", "reactive oxygen"]},
                    "C1": {"name": "能量代谢 (Energy)", "keywords": ["glycolysis", "glycolytic", "tca cycle", "citrate cycle", "oxidative phosphorylation", "mitochondria", "mitochondrial", "atp synthesis", "respiration", "energy metabolism", "thermogenesis", "glucose metabolism", "lipid metabolic", "fatty acid oxidation", "metabolic process"]},
                    "C2": {"name": "生物合成 (Biosynthesis)", "keywords": ["biosynthesis", "biosynthetic", "anabolism", "fatty acid biosynthesis", "amino acid biosynthesis", "nucleotide biosynthesis", "starch", "sucrose", "protein synthesis", "lipogenesis", "cholesterol biosynthesis", "steroid biosynthesis"]}
                }
            },
            "A": { # 细胞韧性与稳态 (作为基础层的特异性部分)
                "description": "基础稳态与细胞韧性 (Cellular Resilience)",
                "subclasses": {
                    "A1": {"name": "基因组稳定性与修复 (Genome Stability)", "keywords": ["dna repair", "excision repair", "mismatch repair", "homologous recombination", "non-homologous", "dna damage", "p53", "telomere", "checkpoint", "dna integrity", "mutation repair"]},
                    "A2": {"name": "细胞命运：增殖与死亡 (Proliferation & Death)", "keywords": ["apoptosis", "apoptotic", "necrosis", "autophagy", "cell death", "cell cycle", "mitosis", "cell division", "proliferation", "growth", "programmed cell death", "caspase", "bcl-2"]},
                    "A3": {"name": "细胞稳态与运输 (Homeostasis & Transport)", "keywords": ["homeostasis", "transport", "membrane transport", "ion channel", "cytoskeleton", "motility", "junction", "adhesion", "lysosome", "endocytosis", "exocytosis", "vesicle", "trafficking"]}
                }
            }
        }

    def classify_term(self, term_id, description, source_type="GO"):
        """
        核心分类逻辑：返回 (Main_Cat, Sub_Cat, Main_Name, Sub_Name)
        """
        desc_lower = description.lower()

        # ---------------------------------------------------------
        # 1. 优先判断第0类 (通用基础类)
        # ---------------------------------------------------------
        for kw in self.cat0_keywords:
            if kw in desc_lower:
                return ("0", "0", "通用基础类 (General)", "通用分子机器 (Molecular Machinery)")

        # ---------------------------------------------------------
        # 2. 遍历五大系统 (按照 B->D->E->C->A 的优先级顺序)
        # ---------------------------------------------------------
        priority_order = ["B", "D", "E", "C", "A"]
        
        for main_code in priority_order:
            system_info = self.classification_rules[main_code]
            # 遍历该系统下的所有子类
            for sub_code, sub_info in system_info["subclasses"].items():
                for kw in sub_info["keywords"]:
                    if kw in desc_lower:
                        return (main_code, sub_code, system_info["description"], sub_info["name"])
        
        # ---------------------------------------------------------
        # 3. 兜底逻辑
        # ---------------------------------------------------------
        # 如果是 KEGG 且没有任何匹配，尝试利用 KEGG 自带的 Level A 辅助判断 (可选)
        # 这里为了保持严格性，暂时归为 未分类
        return ("U", "U", "未分类 (Unclassified)", "其他 (Others)")

def main():
    parser = BioDataParser()
    go_file = "go-basic.txt"
    kegg_file = "br_br08901.txt"
    
    # 1. 加载数据
    parser.parse_go_basic(go_file)
    parser.parse_kegg_brite(kegg_file)
    
    # 实例化细分分类器
    classifier = DetailedClassifier()
    
    print("\n" + "="*60)
    print("执行详细分类程序 (依据细分功能体系构建.docx)")
    print("="*60 + "\n")

    results = []
    # 统计字典: {Main_Cat: {Sub_Cat: count}}
    stats = defaultdict(lambda: defaultdict(int))

    # 2. 处理 KEGG 数据
    print("正在处理 KEGG 数据...")
    for pid, info in parser.kegg_hierarchy.items():
        name = info['name']
        main_cat, sub_cat, main_name, sub_name = classifier.classify_term(pid, name, "KEGG")
        
        results.append({
            "ID": f"KEGG:{pid}",
            "Description": name,
            "Main_Category": main_cat,
            "Sub_Category": sub_cat,
            "Main_Name": main_name,
            "Sub_Name": sub_name
        })
        stats[main_cat][sub_cat] += 1

    # 3. 处理 GO 数据
    print("正在处理 GO 数据...")
    for gid, info in parser.go_terms.items():
        name = info['name']
        main_cat, sub_cat, main_name, sub_name = classifier.classify_term(gid, name, "GO")
        
        results.append({
            "ID": gid,
            "Description": name,
            "Main_Category": main_cat,
            "Sub_Category": sub_cat,
            "Main_Name": main_name,
            "Sub_Name": sub_name
        })
        stats[main_cat][sub_cat] += 1

    # 4. 输出分层统计摘要
    print("\n" + "="*30)
    print("分类统计报告 (Hierarchical Stats)")
    print("="*30)
    
    # 排序输出 0, A, B, C, D, E, U
    main_order = ['0', 'A', 'B', 'C', 'D', 'E', 'U']
    
    for m_code in main_order:
        if m_code in stats:
            total_main = sum(stats[m_code].values())
            # 获取主类名称
            m_name_display = "未知"
            if m_code == '0': m_name_display = "通用基础类"
            elif m_code == 'U': m_name_display = "未分类"
            elif m_code in classifier.classification_rules:
                m_name_display = classifier.classification_rules[m_code]['description']
            
            print(f"\n【{m_code}】{m_name_display} (总计: {total_main})")
            
            # 输出子类统计
            sorted_subs = sorted(stats[m_code].items())
            for s_code, count in sorted_subs:
                # 获取子类名称
                s_name = "Default"
                if m_code == '0': s_name = "分子机器"
                elif m_code == 'U': s_name = "其他"
                elif m_code in classifier.classification_rules and s_code in classifier.classification_rules[m_code]['subclasses']:
                    s_name = classifier.classification_rules[m_code]['subclasses'][s_code]['name']
                
                print(f"  ├── {s_code}: {s_name:<30} ... {count}")

    # 5. 保存结果
    output_file = "detailed_classification_results.csv"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("ID,Description,Main_Code,Sub_Code,Main_Name,Sub_Name\n")
            for item in results:
                clean_desc = item['Description'].replace(',', ';')
                f.write(f"{item['ID']},{clean_desc},{item['Main_Category']},{item['Sub_Category']},{item['Main_Name']},{item['Sub_Name']}\n")
        print(f"\n详细结果已保存至: {output_file}")
    except IOError as e:
        print(f"保存文件失败: {e}")

if __name__ == "__main__":
    main()