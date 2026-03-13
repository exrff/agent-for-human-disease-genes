"""
五大功能系统分类器演示

展示分类器的基本功能和使用方法。
"""

from ..models.biological_entry import BiologicalEntry
from .five_system_classifier import FiveSystemClassifier


def demo_classification():
    """演示分类器功能"""
    
    # 创建分类器实例
    classifier = FiveSystemClassifier()
    
    # 创建一些示例生物学条目
    test_entries = [
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
            definition="Any immune system process that functions in the calibrated response of an organism to a potential internal or invasive threat",
            source="GO",
            namespace="biological_process"
        ),
        BiologicalEntry(
            id="GO:0006096",
            name="glycolysis",
            definition="The chemical reactions and pathways resulting in the breakdown of glucose",
            source="GO",
            namespace="biological_process"
        ),
        BiologicalEntry(
            id="GO:0007399",
            name="nervous system development",
            definition="The process whose specific outcome is the progression of nervous tissue",
            source="GO",
            namespace="biological_process"
        ),
        BiologicalEntry(
            id="GO:0000003",
            name="reproduction",
            definition="The production of new individuals that contain some portion of genetic material inherited from one or more parent organisms",
            source="GO",
            namespace="biological_process"
        ),
        BiologicalEntry(
            id="GO:0006412",
            name="translation",
            definition="The cellular metabolic process in which a protein is formed",
            source="GO",
            namespace="biological_process"
        ),
        BiologicalEntry(
            id="GO:0006954",
            name="inflammatory response",
            definition="The immediate defensive reaction by vertebrate tissue to infection or injury",
            source="GO",
            namespace="biological_process"
        )
    ]
    
    print("五大功能系统分类器演示")
    print("=" * 50)
    
    for entry in test_entries:
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
        print(f"所有匹配系统: {', '.join(result.all_systems)}")
        print(f"决策路径: {' -> '.join(result.decision_path)}")
        
        # 显示匹配的模式（如果有）
        if 'matched_patterns' in result.metadata:
            patterns = result.metadata['matched_patterns']
            if patterns:
                print(f"匹配模式: {', '.join(patterns)}")
        
        print("-" * 30)
    
    # 显示分类统计
    stats = classifier.get_classification_stats()
    print(f"\n分类统计:")
    print(f"总分类数: {stats['total_classified']}")
    print("各系统分布:")
    for system, count in stats['system_counts'].items():
        if count > 0:
            print(f"  {system}: {count}")


if __name__ == "__main__":
    demo_classification()