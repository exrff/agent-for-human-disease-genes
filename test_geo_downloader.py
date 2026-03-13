#!/usr/bin/env python3
"""
测试 GEO 数据下载器

功能：
1. 测试单个数据集下载
2. 测试批量下载
3. 验证下载的文件
"""

import sys
import logging
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.data_extraction.geo_downloader import GEODownloader, download_geo_dataset, check_dataset_exists


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def test_single_download(gse_id: str = "GSE2034"):
    """测试单个数据集下载"""
    print("=" * 70)
    print(f"测试 1: 下载单个数据集 ({gse_id})")
    print("=" * 70)
    print()
    
    # 检查是否已存在
    if check_dataset_exists(gse_id):
        print(f"✓ 数据集 {gse_id} 已存在")
        print()
        return True
    
    # 下载
    print(f"开始下载 {gse_id}...")
    result = download_geo_dataset(gse_id)
    
    print()
    print("=" * 70)
    if result['success']:
        print("✅ 下载成功！")
        print(f"Series matrix: {Path(result['series_matrix_file']).name}")
        print(f"Platform 文件: {len(result['platform_files'])} 个")
        for pf in result['platform_files']:
            print(f"  - {Path(pf).name}")
    else:
        print("❌ 下载失败")
        for error in result['errors']:
            print(f"  {error}")
    print("=" * 70)
    print()
    
    return result['success']


def test_check_exists():
    """测试检查数据集是否存在"""
    print("=" * 70)
    print("测试 2: 检查数据集是否存在")
    print("=" * 70)
    print()
    
    test_datasets = [
        "GSE2034",
        "GSE26168",
        "GSE122063",
        "GSE99999"  # 不存在的
    ]
    
    for gse_id in test_datasets:
        exists = check_dataset_exists(gse_id)
        status = "✓ 存在" if exists else "✗ 不存在"
        print(f"{gse_id}: {status}")
    
    print()


def test_batch_download():
    """测试批量下载"""
    print("=" * 70)
    print("测试 3: 批量下载数据集")
    print("=" * 70)
    print()
    
    # 选择几个小数据集测试
    test_datasets = [
        "GSE2034",    # 乳腺癌
        "GSE26168",   # 糖尿病
    ]
    
    downloader = GEODownloader()
    
    results = []
    for gse_id in test_datasets:
        print(f"\n{'=' * 70}")
        print(f"下载 {gse_id}...")
        print('=' * 70)
        
        # 检查是否已存在
        if downloader.check_dataset_exists(gse_id):
            print(f"✓ {gse_id} 已存在，跳过")
            results.append({'gse_id': gse_id, 'success': True, 'skipped': True})
            continue
        
        # 下载
        result = downloader.download_dataset(gse_id)
        results.append(result)
    
    # 汇总结果
    print("\n" + "=" * 70)
    print("批量下载结果汇总")
    print("=" * 70)
    
    success_count = sum(1 for r in results if r['success'])
    total_count = len(results)
    
    print(f"总计: {total_count} 个数据集")
    print(f"成功: {success_count} 个")
    print(f"失败: {total_count - success_count} 个")
    print()
    
    for result in results:
        status = "✅" if result['success'] else "❌"
        skipped = " (已存在)" if result.get('skipped') else ""
        print(f"{status} {result['gse_id']}{skipped}")
    
    print("=" * 70)


def test_with_agent():
    """测试与智能体集成"""
    print("=" * 70)
    print("测试 4: 与智能体集成测试")
    print("=" * 70)
    print()
    
    from src.agent.disease_analysis_agent import run_disease_analysis
    
    # 选择一个数据集
    gse_id = "GSE2034"
    
    print(f"使用智能体分析 {gse_id}...")
    print("（智能体会自动检查并下载数据）")
    print()
    
    try:
        run_disease_analysis(gse_id)
        print()
        print("✅ 智能体分析完成")
    except Exception as e:
        print()
        print(f"❌ 智能体分析失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='测试 GEO 数据下载器')
    parser.add_argument('--test', choices=['single', 'check', 'batch', 'agent', 'all'],
                       default='all', help='测试类型')
    parser.add_argument('--gse', type=str, default='GSE2034',
                       help='数据集 ID（用于 single 测试）')
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging()
    
    print()
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 22 + "GEO 数据下载器测试" + " " * 24 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    if args.test == 'single' or args.test == 'all':
        test_single_download(args.gse)
    
    if args.test == 'check' or args.test == 'all':
        test_check_exists()
    
    if args.test == 'batch' or args.test == 'all':
        print("是否要测试批量下载？（会下载多个数据集）")
        print("输入 'y' 继续，其他键跳过")
        choice = input("请选择: ").strip().lower()
        if choice == 'y':
            test_batch_download()
        else:
            print("跳过批量下载测试")
            print()
    
    if args.test == 'agent':
        test_with_agent()
    
    print()
    print("=" * 70)
    print("所有测试完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
