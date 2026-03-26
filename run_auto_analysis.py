#!/usr/bin/env python3
"""
自动化疾病分析主程序

功能：
1. 自动选择下一个最有价值的数据集
2. 运行完整分析流程
3. 支持单次或批量分析
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent))

# 加载 .env 文件（兼容不同运行方式）
_env_file = Path(__file__).parent / '.env'
if _env_file.exists():
    with open(_env_file, 'r', encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _, _v = _line.partition('=')
                os.environ.setdefault(_k.strip(), _v.strip())

from src.agent.dataset_selector_service import DiseaseSelector
from src.agent.disease_analysis_agent import run_disease_analysis


def setup_logging():
    """设置日志"""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"auto_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding='utf-8')
        ]
    )
    
    return logging.getLogger(__name__)


def run_single_analysis(use_llm: bool = True):
    """运行单次分析"""
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 70)
    logger.info("开始新一轮分析")
    logger.info("=" * 70)
    
    # 选择数据集
    logger.info("步骤 1: 选择下一个数据集...")
    selector = DiseaseSelector()
    selected = selector.run(use_llm=use_llm)
    
    if not selected:
        logger.info("没有可分析的数据集")
        return False
    
    dataset_id = selected['dataset_id']
    logger.info(f"选择了数据集: {dataset_id} - {selected['chinese_name']}")
    logger.info(f"选择理由: {selected.get('selection_reasoning', '无')}")
    
    # 运行分析
    logger.info("步骤 2: 运行分析...")
    try:
        run_disease_analysis(dataset_id, dataset_info=selected)
        # 这里把selected（选择器选择的理由作为信息传给了分析器，是很典型的“上游节点给下游节点传富上下文”的 Agent 设计。）
        logger.info(f"✅ {dataset_id} 分析完成")
        return True
    except Exception as e:
        logger.error(f"❌ {dataset_id} 分析失败: {e}", exc_info=True)
        return False


def run_batch_analysis(max_datasets: int = None, use_llm: bool = True):
    """批量分析多个数据集"""
    logger = logging.getLogger(__name__)
    
    logger.info("╔" + "=" * 68 + "╗")
    logger.info("║" + " " * 22 + "自动化批量分析" + " " * 26 + "║")
    logger.info("╚" + "=" * 68 + "╝")
    
    count = 0
    success_count = 0
    
    while True:
        if max_datasets and count >= max_datasets:
            logger.info(f"已达到最大分析数量: {max_datasets}")
            break
        
        success = run_single_analysis(use_llm=use_llm)
        
        if not success:
            break
        
        count += 1
        success_count += 1
        logger.info(f"进度: {count} 个数据集已分析")
        logger.info("")
    
    logger.info("=" * 70)
    logger.info(f"批量分析完成！总计: {count} 个，成功: {success_count} 个")
    logger.info("=" * 70)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='自动化疾病数据集分析')
    parser.add_argument('--mode', choices=['single', 'batch'], default='single',
                       help='运行模式: single=单次分析, batch=批量分析')
    parser.add_argument('--max', type=int, default=None,
                       help='批量模式下最多分析多少个数据集')
    parser.add_argument('--no-llm', action='store_true',
                       help='不使用 LLM，仅使用规则引擎')
    
    args = parser.parse_args()
    
    # 设置日志
    logger = setup_logging()
    
    # 检查 API Key
    use_llm = not args.no_llm
    if use_llm and not os.getenv('DASHSCOPE_API_KEY'):
        logger.warning("未设置 DASHSCOPE_API_KEY，将使用规则引擎")
        use_llm = False
    
    # 运行分析
    if args.mode == 'single':
        logger.info("运行模式: 单次分析")
        run_single_analysis(use_llm=use_llm)
    else:
        logger.info(f"运行模式: 批量分析 (最多 {args.max or '全部'} 个)")
        run_batch_analysis(max_datasets=args.max, use_llm=use_llm)


if __name__ == "__main__":
    main()
