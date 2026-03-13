#!/usr/bin/env python3
"""
智能体分析示例脚本
"""

import sys
sys.path.append('.')

from src.agent import run_disease_analysis
from src.agent.config import AgentConfig


def example_single_analysis():
    """示例1: 分析单个数据集"""
    print("="*80)
    print("示例1: 分析单个数据集 (GSE2034 - 乳腺癌)")
    print("="*80)
    
    # 确保目录存在
    AgentConfig.ensure_directories()
    
    # 运行分析
    result = run_disease_analysis("GSE2034")
    
    print("\n分析完成！")
    print(f"报告路径: {result.get('report_path')}")
    print(f"生成的图表: {len(result.get('figures', []))} 个")


def example_batch_analysis():
    """示例2: 批量分析多个数据集"""
    print("="*80)
    print("示例2: 批量分析")
    print("="*80)
    
    # 选择要分析的数据集
    datasets_to_analyze = ["GSE2034", "GSE26168", "GSE65682"]
    
    results = {}
    
    for dataset_id in datasets_to_analyze:
        print(f"\n{'='*80}")
        print(f"正在分析: {dataset_id} - {AgentConfig.DATASETS[dataset_id]['chinese_name']}")
        print(f"{'='*80}\n")
        
        try:
            result = run_disease_analysis(dataset_id)
            results[dataset_id] = {
                "status": "success",
                "report_path": result.get('report_path'),
                "figures": result.get('figures', [])
            }
            print(f"\n✅ {dataset_id} 分析成功")
        except Exception as e:
            results[dataset_id] = {
                "status": "failed",
                "error": str(e)
            }
            print(f"\n❌ {dataset_id} 分析失败: {e}")
    
    # 打印汇总
    print("\n" + "="*80)
    print("批量分析汇总")
    print("="*80)
    
    for dataset_id, result in results.items():
        status_icon = "✅" if result["status"] == "success" else "❌"
        print(f"{status_icon} {dataset_id}: {result['status']}")
        if result["status"] == "success":
            print(f"   报告: {result['report_path']}")
            print(f"   图表: {len(result['figures'])} 个")


def example_custom_config():
    """示例3: 使用自定义配置"""
    print("="*80)
    print("示例3: 自定义配置分析")
    print("="*80)
    
    from src.agent import create_disease_analysis_graph
    
    # 创建工作流
    app = create_disease_analysis_graph()
    
    # 自定义初始状态
    initial_state = {
        "dataset_id": "GSE2034",
        "dataset_info": AgentConfig.get_dataset_config("GSE2034"),
        "raw_data_path": None,
        "processed_data_path": None,
        "expression_matrix": None,
        "sample_metadata": None,
        "classification_results": None,
        "ssgsea_scores": None,
        "statistical_results": None,
        "disease_type": "cancer",  # 手动指定疾病类型
        "analysis_strategy": "subtype_comparison",  # 手动指定策略
        "visualization_plan": ["clustering", "heatmap", "network"],  # 手动指定可视化
        "figures": [],
        "interpretation": None,
        "report_path": None,
        "log_messages": [],
        "errors": [],
        "current_step": "init",
        "needs_human_review": False,
        "retry_count": 0
    }
    
    # 运行工作流
    thread_config = {"configurable": {"thread_id": "custom_analysis_GSE2034"}}
    
    print("开始自定义分析...")
    for output in app.stream(initial_state, thread_config):
        for node_name, node_output in output.items():
            print(f"[{node_name}] 完成")
    
    print("\n自定义分析完成！")


def example_with_logging():
    """示例4: 带详细日志的分析"""
    print("="*80)
    print("示例4: 带详细日志的分析")
    print("="*80)
    
    from src.agent.logger import AgentLogger
    
    # 创建日志记录器
    logger = AgentLogger()
    
    logger.log_step("initialization", "started")
    
    try:
        # 运行分析
        result = run_disease_analysis("GSE26168")
        
        logger.log_step("analysis", "completed", {
            "dataset": "GSE26168",
            "figures_generated": len(result.get('figures', []))
        })
        
        logger.log_metric("total_figures", len(result.get('figures', [])))
        
    except Exception as e:
        logger.log_error("AnalysisError", str(e))
    
    finally:
        # 保存日志
        logger.save_json_log()
        
        # 打印摘要
        summary = logger.get_summary()
        print("\n日志摘要:")
        print(f"  总步骤: {summary['total_steps']}")
        print(f"  完成: {summary['completed_steps']}")
        print(f"  失败: {summary['failed_steps']}")
        print(f"  错误: {summary['errors']}")
        print(f"  日志文件: {summary['log_file']}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="疾病分析智能体示例")
    parser.add_argument(
        "--example",
        type=int,
        choices=[1, 2, 3, 4],
        default=1,
        help="选择示例 (1: 单个分析, 2: 批量分析, 3: 自定义配置, 4: 详细日志)"
    )
    
    args = parser.parse_args()
    
    if args.example == 1:
        example_single_analysis()
    elif args.example == 2:
        example_batch_analysis()
    elif args.example == 3:
        example_custom_config()
    elif args.example == 4:
        example_with_logging()
