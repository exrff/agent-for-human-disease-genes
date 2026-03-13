"""
语义一致性验证模块演示

演示如何使用语义一致性验证器来评估五大系统分类的质量。
"""

import sys
from pathlib import Path
import networkx as nx
import logging

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.semantic_coherence_validator import SemanticCoherenceValidator
from src.analysis.clustering_quality_evaluator import ClusteringQualityEvaluator
from src.preprocessing.go_parser import GOParser

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_demo_go_dag() -> nx.DiGraph:
    """创建演示用的GO DAG"""
    dag = nx.DiGraph()
    
    # 添加根节点
    dag.add_node('GO:0008150', name='biological_process', namespace='biological_process', depth=0)
    
    # 添加系统级节点
    system_nodes = {
        'GO:0001000': ('system_a_root', 'Self-healing processes'),
        'GO:0002000': ('system_b_root', 'Immune defense processes'),
        'GO:0003000': ('system_c_root', 'Energy metabolism processes'),
        'GO:0004000': ('system_d_root', 'Cognitive regulation processes'),
        'GO:0005000': ('system_e_root', 'Reproduction processes'),
    }
    
    for node_id, (name, definition) in system_nodes.items():
        dag.add_node(node_id, name=name, definition=definition, 
                    namespace='biological_process', depth=1)
        dag.add_edge('GO:0008150', node_id, relation='is_a')
    
    # 为每个系统添加具体的过程节点
    system_processes = {
        # System A: Self-healing
        'GO:0001000': [
            ('GO:0001001', 'DNA repair process', 'DNA damage repair'),
            ('GO:0001002', 'wound healing process', 'Tissue repair and regeneration'),
            ('GO:0001003', 'autophagy process', 'Cellular cleanup and recycling'),
            ('GO:0001004', 'protein folding process', 'Protein quality control'),
            ('GO:0001005', 'cell cycle checkpoint', 'Cell division quality control'),
        ],
        
        # System B: Immune defense
        'GO:0002000': [
            ('GO:0002001', 'innate immune response', 'First line immune defense'),
            ('GO:0002002', 'adaptive immune response', 'Specific immune response'),
            ('GO:0002003', 'inflammatory response', 'Immune-mediated inflammation'),
            ('GO:0002004', 'phagocytosis process', 'Pathogen engulfment'),
            ('GO:0002005', 'antigen presentation', 'Immune recognition'),
        ],
        
        # System C: Energy metabolism
        'GO:0003000': [
            ('GO:0003001', 'glycolysis process', 'Glucose breakdown'),
            ('GO:0003002', 'oxidative phosphorylation', 'ATP synthesis'),
            ('GO:0003003', 'fatty acid oxidation', 'Fat metabolism'),
            ('GO:0003004', 'gluconeogenesis process', 'Glucose synthesis'),
            ('GO:0003005', 'lipid biosynthesis', 'Fat synthesis'),
        ],
        
        # System D: Cognitive regulation
        'GO:0004000': [
            ('GO:0004001', 'synaptic transmission', 'Neural communication'),
            ('GO:0004002', 'hormone secretion', 'Endocrine signaling'),
            ('GO:0004003', 'circadian rhythm', 'Biological clock'),
            ('GO:0004004', 'stress response', 'Physiological adaptation'),
            ('GO:0004005', 'memory formation', 'Learning and memory'),
        ],
        
        # System E: Reproduction
        'GO:0005000': [
            ('GO:0005001', 'gametogenesis process', 'Gamete formation'),
            ('GO:0005002', 'fertilization process', 'Reproductive fusion'),
            ('GO:0005003', 'embryonic development', 'Early development'),
            ('GO:0005004', 'sexual maturation', 'Reproductive maturity'),
            ('GO:0005005', 'reproductive behavior', 'Mating behavior'),
        ],
    }
    
    # 添加具体过程节点
    for parent_id, processes in system_processes.items():
        for process_id, name, definition in processes:
            dag.add_node(process_id, name=name, definition=definition,
                        namespace='biological_process', depth=2)
            dag.add_edge(parent_id, process_id, relation='is_a')
    
    logger.info(f"创建演示GO DAG: {len(dag.nodes)} 个节点, {len(dag.edges)} 条边")
    return dag


def create_demo_system_terms() -> dict:
    """创建演示用的系统条目映射"""
    return {
        'System A': [
            'GO:0001001', 'GO:0001002', 'GO:0001003', 'GO:0001004', 'GO:0001005'
        ],
        'System B': [
            'GO:0002001', 'GO:0002002', 'GO:0002003', 'GO:0002004', 'GO:0002005'
        ],
        'System C': [
            'GO:0003001', 'GO:0003002', 'GO:0003003', 'GO:0003004', 'GO:0003005'
        ],
        'System D': [
            'GO:0004001', 'GO:0004002', 'GO:0004003', 'GO:0004004', 'GO:0004005'
        ],
        'System E': [
            'GO:0005001', 'GO:0005002', 'GO:0005003', 'GO:0005004', 'GO:0005005'
        ]
    }


def demo_semantic_coherence_validation():
    """演示语义一致性验证"""
    print("=" * 80)
    print("语义一致性验证模块演示")
    print("=" * 80)
    
    # 1. 创建演示数据
    print("\n1. 创建演示数据...")
    go_dag = create_demo_go_dag()
    system_terms = create_demo_system_terms()
    
    print(f"   GO DAG: {len(go_dag.nodes)} 个节点")
    print(f"   系统数量: {len(system_terms)}")
    for system, terms in system_terms.items():
        print(f"   {system}: {len(terms)} 个条目")
    
    # 2. 初始化语义一致性验证器
    print("\n2. 初始化语义一致性验证器...")
    validator = SemanticCoherenceValidator(
        go_dag=go_dag,
        similarity_method='depth',
        sample_size=50,
        random_seed=42
    )
    
    # 3. 测试单个相似度计算
    print("\n3. 测试语义相似度计算...")
    
    # 同系统内的相似度
    sim_intra = validator.calculate_semantic_similarity('GO:0001001', 'GO:0001002')
    print(f"   系统内相似度 (GO:0001001 vs GO:0001002): {sim_intra:.4f}")
    
    # 不同系统间的相似度
    sim_inter = validator.calculate_semantic_similarity('GO:0001001', 'GO:0002001')
    print(f"   系统间相似度 (GO:0001001 vs GO:0002001): {sim_inter:.4f}")
    
    # 验证系统内相似度是否高于系统间相似度
    print(f"   系统内相似度 {'>' if sim_intra > sim_inter else '<='} 系统间相似度: {sim_intra > sim_inter}")
    
    # 4. 执行完整的聚类质量验证
    print("\n4. 执行聚类质量验证...")
    coherence_report = validator.validate_clustering_quality(
        system_terms, 
        coherence_threshold=1.5
    )
    
    print(f"   验证结果: {'✅ 通过' if coherence_report.validation_passed else '⚠️ 未通过'}")
    print(f"   平均系统内相似度: {coherence_report.avg_intra_similarity:.4f}")
    print(f"   平均系统间相似度: {coherence_report.avg_inter_similarity:.4f}")
    print(f"   一致性比值: {coherence_report.coherence_ratio:.2f}x")
    print(f"   聚类质量得分: {coherence_report.clustering_quality_score:.4f}")
    
    # 5. 生成验证报告
    print("\n5. 生成验证报告...")
    report_text = validator.generate_validation_report(
        coherence_report,
        output_path="results/demo_semantic_coherence_report.md"
    )
    
    print("   报告已保存到: results/demo_semantic_coherence_report.md")
    
    # 6. 初始化聚类质量评估器
    print("\n6. 执行综合聚类质量评估...")
    evaluator = ClusteringQualityEvaluator(
        semantic_validator=validator,
        output_dir="results/demo_clustering_quality"
    )
    
    # 执行完整评估
    quality_report = evaluator.evaluate_clustering_quality(
        system_terms,
        generate_visualizations=True,
        save_detailed_report=True
    )
    
    print(f"   聚类指标:")
    print(f"     轮廓系数: {quality_report.clustering_metrics.silhouette_score:.4f}")
    print(f"     Calinski-Harabasz指数: {quality_report.clustering_metrics.calinski_harabasz_score:.4f}")
    print(f"     Davies-Bouldin指数: {quality_report.clustering_metrics.davies_bouldin_score:.4f}")
    
    print(f"\n   生成的可视化文件:")
    for viz_path in quality_report.visualization_paths:
        print(f"     - {Path(viz_path).name}")
    
    print(f"\n   改进建议:")
    for i, recommendation in enumerate(quality_report.recommendations, 1):
        print(f"     {i}. {recommendation}")
    
    # 7. 测试不同相似度方法的比较
    print("\n7. 测试不同相似度方法...")
    methods = ['depth', 'jaccard', 'simple']
    method_results = {}
    
    for method in methods:
        method_validator = SemanticCoherenceValidator(
            go_dag=go_dag,
            similarity_method=method,
            sample_size=20,
            random_seed=42
        )
        
        method_report = method_validator.validate_clustering_quality(system_terms)
        method_results[method] = method_report
        
        print(f"   {method.upper()} 方法:")
        print(f"     一致性比值: {method_report.coherence_ratio:.2f}x")
        print(f"     验证通过: {'✅' if method_report.validation_passed else '⚠️'}")
    
    # 8. 比较不同方法
    print("\n8. 比较不同相似度方法...")
    method_classifications = {}
    for method in methods:
        method_classifications[f"method_{method}"] = system_terms
    
    comparison_reports = evaluator.compare_multiple_classifications(
        method_classifications,
        output_prefix="method_comparison"
    )
    
    print("   方法比较报告已生成到: results/demo_clustering_quality/method_comparison_*.csv")
    
    print("\n" + "=" * 80)
    print("演示完成！")
    print("=" * 80)
    
    print("\n生成的文件:")
    print("  - results/demo_semantic_coherence_report.md")
    print("  - results/demo_clustering_quality/quality_assessment_report.json")
    print("  - results/demo_clustering_quality/quality_assessment_report.md")
    print("  - results/demo_clustering_quality/*.png (可视化图表)")
    
    return coherence_report, quality_report


def demo_with_real_data():
    """使用真实GO数据进行演示（如果可用）"""
    print("\n" + "=" * 80)
    print("尝试使用真实GO数据进行演示")
    print("=" * 80)
    
    # 检查是否有真实的GO文件
    go_file_paths = [
        "data/ontology/go-basic.obo",
        "data/ontology/go-basic.txt",
        "data/go-basic.obo",
        "go-basic.obo"
    ]
    
    go_file_path = None
    for path in go_file_paths:
        if Path(path).exists():
            go_file_path = path
            break
    
    if go_file_path is None:
        print("未找到GO本体文件，跳过真实数据演示")
        return None
    
    try:
        print(f"使用GO文件: {go_file_path}")
        
        # 解析GO文件
        parser = GOParser(go_file_path)
        go_terms = parser.parse_go_terms()
        go_dag = parser.build_dag()
        
        print(f"解析完成: {len(go_terms)} 个GO条目")
        
        # 过滤生物过程条目
        bp_terms = parser.get_biological_process_terms(exclude_obsolete=True)
        print(f"生物过程条目: {len(bp_terms)} 个")
        
        # 创建小规模测试集
        test_terms = {}
        term_ids = list(bp_terms.keys())
        
        # 随机选择一些条目作为测试
        import random
        random.seed(42)
        
        for i, system in enumerate(['System A', 'System B', 'System C']):
            start_idx = i * 10
            end_idx = start_idx + 10
            if end_idx <= len(term_ids):
                test_terms[system] = term_ids[start_idx:end_idx]
        
        if len(test_terms) >= 2:
            print(f"创建测试集: {len(test_terms)} 个系统")
            
            # 执行验证
            validator = SemanticCoherenceValidator(
                go_dag=go_dag,
                similarity_method='depth',
                sample_size=20,
                random_seed=42
            )
            
            report = validator.validate_clustering_quality(test_terms)
            
            print(f"真实数据验证结果:")
            print(f"  一致性比值: {report.coherence_ratio:.2f}x")
            print(f"  验证通过: {'✅' if report.validation_passed else '⚠️'}")
            
            return report
        else:
            print("测试集条目不足，跳过验证")
            return None
            
    except Exception as e:
        print(f"真实数据演示失败: {e}")
        return None


if __name__ == "__main__":
    # 创建结果目录
    Path("results").mkdir(exist_ok=True)
    
    # 运行演示
    try:
        coherence_report, quality_report = demo_semantic_coherence_validation()
        
        # 尝试真实数据演示
        real_data_report = demo_with_real_data()
        
        print(f"\n🎉 语义一致性验证模块演示成功完成！")
        
    except Exception as e:
        logger.error(f"演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()