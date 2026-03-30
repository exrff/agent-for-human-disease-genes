#!/usr/bin/env python3
"""Automated disease dataset analysis entrypoint."""

from __future__ import annotations

import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))

_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    with open(_env_file, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

from src.agent.dataset_selector_service import DiseaseSelector
from src.agent.disease_analysis_agent import run_disease_analysis
from src.agent.whitelist_repository import remove_dataset_from_whitelist


def setup_logging() -> logging.Logger:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"auto_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file, encoding="utf-8")],
    )
    return logging.getLogger(__name__)


def _remove_tree(path: Path, logger: logging.Logger) -> None:
    if not path.exists():
        return
    shutil.rmtree(path, ignore_errors=False)
    logger.info("已清理残留目录: %s", path)


def cleanup_failed_artifacts(dataset_id: str, logger: logging.Logger) -> None:
    result_dir = Path("results/agent_analysis") / dataset_id
    validation_root = Path("data/validation_datasets")

    try:
        _remove_tree(result_dir, logger)
    except Exception as exc:
        logger.warning("清理结果目录失败 %s: %s", result_dir, exc)

    for folder in validation_root.glob(f"{dataset_id}*"):
        if not folder.is_dir():
            continue
        try:
            _remove_tree(folder, logger)
        except Exception as exc:
            logger.warning("清理数据目录失败 %s: %s", folder, exc)


def purge_existing_failed_artifacts(logger: logging.Logger) -> None:
    results_root = Path("results/agent_analysis")
    if not results_root.exists():
        return
    purged = 0
    for dataset_dir in results_root.iterdir():
        if not dataset_dir.is_dir():
            continue
        summary_file = dataset_dir / "analysis_summary.json"
        if not summary_file.exists():
            continue
        try:
            import json

            with open(summary_file, "r", encoding="utf-8") as fh:
                summary = json.load(fh)
        except Exception as exc:
            logger.warning("读取摘要失败，跳过 %s: %s", summary_file, exc)
            continue

        if summary.get("errors"):
            dataset_id = dataset_dir.name
            logger.info("发现历史失败数据集，执行清理: %s", dataset_id)
            cleanup_failed_artifacts(dataset_id, logger)
            purged += 1

    if purged:
        logger.info("已清理历史失败数据集 %d 个", purged)


def _remove_failed_from_whitelist(dataset_id: str, reason: str, logger: logging.Logger) -> None:
    try:
        removed = remove_dataset_from_whitelist(dataset_id, reason=reason)
        if removed:
            logger.warning("已从白名单移除失败数据集: %s", dataset_id)
    except Exception as exc:
        logger.warning("移除白名单失败（将继续批处理）%s: %s", dataset_id, exc)


def run_single_analysis(use_llm: bool = True) -> Dict[str, Optional[str]]:
    """Run one analysis round.

    Returns:
      {"status": "success"|"failed"|"empty", "dataset_id": str|None}
    """
    logger = logging.getLogger(__name__)
    logger.info("=" * 70)
    logger.info("开始新一轮分析")
    logger.info("=" * 70)

    logger.info("步骤 1: 选择下一个数据集...")
    selector = DiseaseSelector()
    selected = selector.run(use_llm=use_llm)
    if not selected:
        logger.info("没有可分析的数据集")
        return {"status": "empty", "dataset_id": None}

    dataset_id = selected["dataset_id"]
    logger.info("选择了数据集: %s - %s", dataset_id, selected.get("chinese_name", dataset_id))
    logger.info("选择理由: %s", selected.get("selection_reasoning", "无"))

    logger.info("步骤 2: 运行分析...")
    try:
        final_state = run_disease_analysis(dataset_id, dataset_info=selected)
        errors = final_state.get("errors") or []
        if errors:
            reason = "; ".join(errors)
            logger.warning("⚠️ %s 分析失败，开始清理残留目录", dataset_id)
            cleanup_failed_artifacts(dataset_id, logger)
            _remove_failed_from_whitelist(dataset_id, reason, logger)
            logger.warning("❌ %s 分析失败: %s", dataset_id, reason)
            return {"status": "failed", "dataset_id": dataset_id}
        logger.info("✅ %s 分析完成", dataset_id)
        return {"status": "success", "dataset_id": dataset_id}
    except Exception as exc:
        cleanup_failed_artifacts(dataset_id, logger)
        _remove_failed_from_whitelist(dataset_id, str(exc), logger)
        logger.error("❌ %s 分析异常: %s", dataset_id, exc, exc_info=True)
        return {"status": "failed", "dataset_id": dataset_id}


def run_batch_analysis(max_datasets: int = None, use_llm: bool = True) -> None:
    logger = logging.getLogger(__name__)
    logger.info("╔" + "=" * 68 + "╗")
    logger.info("║" + " " * 22 + "自动化批量分析" + " " * 26 + "║")
    logger.info("╚" + "=" * 68 + "╝")

    attempted = 0
    success_count = 0
    failed_count = 0

    while True:
        if max_datasets and attempted >= max_datasets:
            logger.info("已达到最大分析轮数: %s", max_datasets)
            break

        result = run_single_analysis(use_llm=use_llm)
        status = result.get("status")

        if status == "empty":
            logger.info("白名单中没有可继续分析的数据集，批处理结束")
            break

        attempted += 1
        if status == "success":
            success_count += 1
        else:
            failed_count += 1
            logger.info("本轮失败已自动剔除白名单，继续下一轮")

        logger.info(
            "进度: 尝试 %d | 成功 %d | 失败 %d",
            attempted,
            success_count,
            failed_count,
        )
        logger.info("")

    logger.info("=" * 70)
    logger.info(
        "批量分析完成！尝试: %d 个，成功: %d 个，失败: %d 个",
        attempted,
        success_count,
        failed_count,
    )
    logger.info("=" * 70)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="自动化疾病数据集分析")
    parser.add_argument(
        "--mode",
        choices=["single", "batch"],
        default="single",
        help="运行模式: single=单次分析, batch=批量分析",
    )
    parser.add_argument("--max", type=int, default=None, help="批量模式最大轮数")
    parser.add_argument("--no-llm", action="store_true", help="不使用 LLM，仅规则引擎")
    args = parser.parse_args()

    logger = setup_logging()
    purge_existing_failed_artifacts(logger)

    use_llm = not args.no_llm
    if use_llm and not os.getenv("DASHSCOPE_API_KEY"):
        logger.warning("未设置 DASHSCOPE_API_KEY，将使用规则引擎")
        use_llm = False

    if args.mode == "single":
        logger.info("运行模式: 单次分析")
        run_single_analysis(use_llm=use_llm)
    else:
        logger.info("运行模式: 批量分析 (最大 %s 轮)", args.max or "全部")
        run_batch_analysis(max_datasets=args.max, use_llm=use_llm)


if __name__ == "__main__":
    main()
