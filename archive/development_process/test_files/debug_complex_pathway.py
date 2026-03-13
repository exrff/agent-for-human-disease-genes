"""
复杂通路检测调试脚本
"""

import re
from ..models.biological_entry import BiologicalEntry
from .five_system_classifier import FiveSystemClassifier


def debug_complex_pathway_detection():
    """调试复杂通路检测"""
    
    classifier = FiveSystemClassifier()
    
    # 测试条目
    test_entry = BiologicalEntry(
        id="GO:0001234",
        name="apoptosis and tissue repair pathway",
        definition="A biological process involving both programmed cell death and subsequent tissue regeneration and healing",
        source="GO",
        namespace="biological_process"
    )
    
    print("调试复杂通路检测")
    print("=" * 50)
    print(f"条目: {test_entry.name}")
    print(f"定义: {test_entry.definition}")
    
    # 构建搜索文本
    search_text = f"{test_entry.name} {test_entry.definition or ''}".lower()
    print(f"搜索文本: {search_text}")
    
    # 检查破坏性模式
    destructive_patterns = [
        r'kill', r'destroy', r'eliminate', r'attack', r'cytotox',
        r'lysis', r'death', r'apoptosis', r'degradation', r'breakdown',
        r'clearance', r'removal', r'antimicrobial', r'bactericidal',
        r'destruction', r'elimination', r'pathogen.*elimination'
    ]
    
    print("\n破坏性模式匹配:")
    destructive_matches = []
    for pattern in destructive_patterns:
        if re.search(pattern, search_text, re.IGNORECASE):
            destructive_matches.append(pattern)
            print(f"  ✓ {pattern}")
    
    if not destructive_matches:
        print("  ○ 无匹配")
    
    # 检查建设性模式
    constructive_patterns = [
        r'repair', r'heal', r'regenerat', r'reconstruct', r'restore',
        r'maintain', r'homeostasis', r'synthesis', r'biosynthesis',
        r'formation', r'assembly', r'construction', r'development',
        r'tissue.*repair', r'wound.*healing', r'reconstruction'
    ]
    
    print("\n建设性模式匹配:")
    constructive_matches = []
    for pattern in constructive_patterns:
        if re.search(pattern, search_text, re.IGNORECASE):
            constructive_matches.append(pattern)
            print(f"  ✓ {pattern}")
    
    if not constructive_matches:
        print("  ○ 无匹配")
    
    # 检查是否为复杂通路
    is_complex = len(destructive_matches) > 0 and len(constructive_matches) > 0
    print(f"\n是否为复杂通路: {is_complex}")
    
    # 使用分类器检测
    classifier_result = classifier._is_complex_pathway(test_entry)
    print(f"分类器检测结果: {classifier_result}")
    
    # 执行完整分类
    result = classifier.classify_entry(test_entry)
    print(f"\n分类结果:")
    print(f"主系统: {result.primary_system}")
    print(f"复杂通路标记: {result.metadata.get('complex_pathway', False)}")


if __name__ == "__main__":
    debug_complex_pathway_detection()