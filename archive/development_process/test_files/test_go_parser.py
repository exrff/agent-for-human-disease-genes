"""
GO解析器测试

测试GO本体解析器的基本功能。
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from preprocessing.go_parser import GOParser, GOTerm
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)


def test_go_parser():
    """测试GO解析器基本功能"""
    print("=" * 50)
    print("GO解析器测试")
    print("=" * 50)
    
    # 初始化解析器
    go_file = "data/ontology/go-basic.obo"
    if not Path(go_file).exists():
        print(f"GO文件不存在: {go_file}")
        return
    
    parser = GOParser(go_file)
    
    # 解析GO条目
    print("\n1. 解析GO条目...")
    terms = parser.parse_go_terms()
    print(f"解析完成，共 {len(terms)} 个条目")
    
    # 显示统计信息
    print("\n2. 统计信息:")
    stats = parser.get_statistics()
    print(f"总条目数: {stats['total_terms']}")
    print(f"过时条目数: {stats['obsolete_terms']}")
    print("命名空间分布:")
    for namespace, count in stats['namespaces'].items():
        print(f"  {namespace}: {count}")
    
    # 构建DAG
    print("\n3. 构建DAG图...")
    dag = parser.build_dag()
    print(f"DAG节点数: {len(dag.nodes)}")
    print(f"DAG边数: {len(dag.edges)}")
    print(f"是否为DAG: {stats.get('is_acyclic', 'Unknown')}")
    
    # 测试祖先查询
    print("\n4. 测试祖先查询...")
    test_terms = ['GO:0000001', 'GO:0000002', 'GO:0000003']
    for term_id in test_terms:
        if term_id in terms:
            ancestors = parser.get_ancestors(term_id)
            print(f"{term_id} ({terms[term_id].name}): {len(ancestors)} 个祖先")
            
            # 显示前5个祖先
            for i, ancestor_id in enumerate(list(ancestors)[:5]):
                if ancestor_id in terms:
                    print(f"  - {ancestor_id}: {terms[ancestor_id].name}")
        else:
            print(f"{term_id}: 条目不存在")
    
    # 测试生物过程过滤
    print("\n5. 测试生物过程过滤...")
    bp_terms = parser.get_biological_process_terms()
    print(f"生物过程条目数: {len(bp_terms)}")
    
    # 显示前5个生物过程条目
    print("前5个生物过程条目:")
    for i, (term_id, term) in enumerate(list(bp_terms.items())[:5]):
        print(f"  {term_id}: {term.name}")
    
    # 测试条目过滤
    print("\n6. 测试条目过滤...")
    filtered_terms = parser.filter_terms(
        namespaces={'biological_process'},
        exclude_obsolete=True,
        exclude_general=True
    )
    print(f"过滤后条目数: {len(filtered_terms)}")
    
    # 转换为BiologicalEntry
    print("\n7. 转换为BiologicalEntry...")
    # 只转换前100个条目以节省时间
    sample_terms = dict(list(filtered_terms.items())[:100])
    entries = parser.to_biological_entries(sample_terms)
    print(f"转换完成，共 {len(entries)} 个条目")
    
    # 显示第一个条目的详细信息
    if entries:
        entry = entries[0]
        print(f"\n示例条目:")
        print(f"  ID: {entry.id}")
        print(f"  名称: {entry.name}")
        print(f"  定义: {entry.definition[:100]}...")
        print(f"  命名空间: {entry.namespace}")
        print(f"  祖先数量: {len(entry.ancestors)}")
        print(f"  元数据键: {list(entry.metadata.keys())}")
    
    print("\n" + "=" * 50)
    print("GO解析器测试完成！")
    print("=" * 50)


if __name__ == "__main__":
    test_go_parser()