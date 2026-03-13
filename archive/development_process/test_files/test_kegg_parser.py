"""
KEGG解析器测试

测试KEGG通路解析器的基本功能。
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from preprocessing.kegg_parser import KEGGParser, KEGGPathway
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)


def test_kegg_parser():
    """测试KEGG解析器基本功能"""
    print("=" * 50)
    print("KEGG解析器测试")
    print("=" * 50)
    
    # 初始化解析器
    kegg_file = "data/ontology/br_br08901.txt"
    if not Path(kegg_file).exists():
        print(f"KEGG文件不存在: {kegg_file}")
        return
    
    parser = KEGGParser(kegg_file)
    
    # 解析KEGG通路
    print("\n1. 解析KEGG通路...")
    pathways = parser.parse_pathways()
    print(f"解析完成，共 {len(pathways)} 个通路")
    
    # 显示统计信息
    print("\n2. 统计信息:")
    stats = parser.get_statistics()
    print(f"总通路数: {stats['total_pathways']}")
    print(f"Class A数量: {stats['class_a_count']}")
    print(f"Class B数量: {stats['class_b_count']}")
    
    print("\nClass A分布:")
    for class_a, count in sorted(stats['class_a_distribution'].items()):
        print(f"  {class_a}: {count}")
    
    print(f"\nClass B分布 (前10个):")
    sorted_class_b = sorted(stats['class_b_distribution'].items(), key=lambda x: x[1], reverse=True)
    for class_b, count in sorted_class_b[:10]:
        print(f"  {class_b}: {count}")
    
    # 测试层次信息提取
    print("\n3. 测试层次信息提取...")
    hierarchy = parser.extract_hierarchy()
    print(f"层次映射数量: {len(hierarchy)}")
    
    # 显示前5个层次映射
    print("前5个层次映射:")
    for i, (pathway_id, (class_a, class_b)) in enumerate(list(hierarchy.items())[:5]):
        print(f"  {pathway_id}: {class_a} > {class_b}")
    
    # 测试按Class A获取通路
    print("\n4. 测试按Class A获取通路...")
    metabolism_pathways = parser.get_pathways_by_class_a("Metabolism")
    print(f"代谢相关通路数: {len(metabolism_pathways)}")
    
    # 显示前5个代谢通路
    print("前5个代谢通路:")
    for pathway in metabolism_pathways[:5]:
        print(f"  {pathway.id}: {pathway.name}")
    
    # 测试按Class B获取通路
    print("\n5. 测试按Class B获取通路...")
    carb_pathways = parser.get_pathways_by_class_b("Carbohydrate metabolism")
    print(f"碳水化合物代谢通路数: {len(carb_pathways)}")
    
    # 显示碳水化合物代谢通路
    print("碳水化合物代谢通路:")
    for pathway in carb_pathways:
        print(f"  {pathway.id}: {pathway.name}")
    
    # 测试免疫相关通路
    print("\n6. 测试免疫相关通路...")
    immune_pathways = parser.get_immune_related_pathways()
    print(f"免疫相关通路数: {len(immune_pathways)}")
    
    if immune_pathways:
        print("免疫相关通路:")
        for pathway in immune_pathways[:5]:
            print(f"  {pathway.id}: {pathway.name}")
    
    # 测试通路过滤
    print("\n7. 测试通路过滤...")
    filtered_pathways = parser.filter_pathways(
        class_a_filter={"Metabolism"},
        name_patterns=[r"metabolism", r"biosynthesis"]
    )
    print(f"过滤后通路数: {len(filtered_pathways)}")
    
    # 测试搜索功能
    print("\n8. 测试搜索功能...")
    search_results = parser.search_pathways("glycolysis")
    print(f"搜索'glycolysis'结果数: {len(search_results)}")
    
    for pathway in search_results:
        print(f"  {pathway.id}: {pathway.name}")
    
    # 转换为BiologicalEntry
    print("\n9. 转换为BiologicalEntry...")
    # 只转换前10个通路以节省时间
    sample_pathways = pathways[:10]
    entries = parser.to_biological_entries(sample_pathways)
    print(f"转换完成，共 {len(entries)} 个条目")
    
    # 显示第一个条目的详细信息
    if entries:
        entry = entries[0]
        print(f"\n示例条目:")
        print(f"  ID: {entry.id}")
        print(f"  名称: {entry.name}")
        print(f"  定义: {entry.definition}")
        print(f"  来源: {entry.source}")
        print(f"  层次: {entry.hierarchy}")
        print(f"  元数据键: {list(entry.metadata.keys())}")
    
    print("\n" + "=" * 50)
    print("KEGG解析器测试完成！")
    print("=" * 50)


if __name__ == "__main__":
    test_kegg_parser()