"""
复杂通路拆分功能演示

展示复杂通路拆分和分析的功能。
"""

from ..models.biological_entry import BiologicalEntry
from .five_system_classifier import FiveSystemClassifier


def demo_complex_pathway_splitting():
    """演示复杂通路拆分功能"""
    
    # 创建分类器实例
    classifier = FiveSystemClassifier()
    
    # 创建一些复杂通路示例
    complex_pathways = [
        BiologicalEntry(
            id="GO:0001234",
            name="apoptosis and tissue repair pathway",
            definition="A biological process involving both programmed cell death and subsequent tissue regeneration and healing",
            source="GO",
            namespace="biological_process"
        ),
        BiologicalEntry(
            id="GO:0005678",
            name="pathogen elimination and wound healing response",
            definition="The coordinated response involving antimicrobial killing of pathogens and repair of tissue damage",
            source="GO",
            namespace="biological_process"
        ),
        BiologicalEntry(
            id="KEGG:01234",
            name="immune attack and homeostasis maintenance",
            definition="Cellular processes involving cytotoxic elimination of threats while maintaining structural integrity",
            source="KEGG",
            hierarchy=("Cellular Processes", "Cell growth and death")
        ),
        BiologicalEntry(
            id="GO:0009876",
            name="inflammatory destruction and regenerative reconstruction",
            definition="Complex pathway involving inflammatory tissue destruction followed by regenerative reconstruction and restoration",
            source="GO",
            namespace="biological_process"
        ),
        BiologicalEntry(
            id="GO:0011111",
            name="balanced clearance and synthesis pathway",
            definition="A metabolic process involving both breakdown of damaged components and biosynthesis of replacement structures",
            source="GO",
            namespace="biological_process"
        )
    ]
    
    # 对比：简单通路示例
    simple_pathways = [
        BiologicalEntry(
            id="GO:0006281",
            name="DNA repair",
            definition="The process of restoring DNA after damage",
            source="GO",
            namespace="biological_process"
        ),
        BiologicalEntry(
            id="GO:0006955",
            name="immune response",
            definition="Any immune system process that functions in the calibrated response to a threat",
            source="GO",
            namespace="biological_process"
        )
    ]
    
    print("复杂通路拆分功能演示")
    print("=" * 60)
    
    print("\n【复杂通路分析】")
    print("-" * 40)
    
    for entry in complex_pathways:
        print(f"\n条目: {entry.id}")
        print(f"名称: {entry.name}")
        print(f"定义: {entry.definition}")
        
        # 执行分类
        result = classifier.classify_entry(entry)
        
        print(f"主系统: {result.primary_system}")
        if result.subsystem:
            print(f"子系统: {result.subsystem}")
        if result.inflammation_polarity:
            print(f"炎症极性: {result.inflammation_polarity}")
        print(f"置信度: {result.confidence_score:.2f}")
        
        # 检查是否为复杂通路
        if result.metadata.get('complex_pathway', False):
            print("✓ 识别为复杂通路")
            print(f"  破坏性得分: {result.metadata['destructive_score']:.2f}")
            print(f"  建设性得分: {result.metadata['constructive_score']:.2f}")
            
            # 显示功能目标分析
            objectives = result.metadata['functional_objectives']
            print("  功能目标分析:")
            for obj_name, score in objectives.items():
                if score > 0:
                    print(f"    {obj_name}: {score:.1f}")
            
            # 显示决策路径
            print(f"  决策路径: {' -> '.join(result.decision_path)}")
        else:
            print("○ 未识别为复杂通路")
        
        print("-" * 30)
    
    print("\n【简单通路对比】")
    print("-" * 40)
    
    for entry in simple_pathways:
        print(f"\n条目: {entry.id}")
        print(f"名称: {entry.name}")
        
        # 执行分类
        result = classifier.classify_entry(entry)
        
        print(f"主系统: {result.primary_system}")
        print(f"置信度: {result.confidence_score:.2f}")
        
        # 检查是否为复杂通路
        if result.metadata.get('complex_pathway', False):
            print("✓ 识别为复杂通路（意外）")
        else:
            print("○ 正确识别为简单通路")
        
        print("-" * 30)
    
    print("\n【复杂通路拆分策略总结】")
    print("-" * 40)
    print("1. 破坏性组分占主导 → 倾向于 System B (免疫防御)")
    print("2. 建设性组分占主导 → 倾向于 System A (自愈重建)")
    print("3. 组分平衡 → 基于功能目标分析决策")
    print("4. 复杂通路置信度相对较低（反映其复杂性）")
    print("5. 提供详细的组分分析和功能目标评估")


if __name__ == "__main__":
    demo_complex_pathway_splitting()