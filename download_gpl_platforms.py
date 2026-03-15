#!/usr/bin/env python3
"""
GPL 平台批量下载脚本

一次性下载所有常用的 GPL 平台文件，建立本地数据库
"""

import sys
import logging
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.data_extraction.gpl_manager import GPLManager


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GPL 平台批量下载')
    parser.add_argument('--action', choices=['download', 'list', 'check'],
                       default='download',
                       help='操作: download=下载, list=列表, check=检查')
    parser.add_argument('--platform', type=str,
                       help='指定平台 ID（用于 check）')
    
    args = parser.parse_args()
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    manager = GPLManager()
    
    print()
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 22 + "GPL 平台管理器" + " " * 28 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    if args.action == 'download':
        print("准备下载所有常用 GPL 平台文件...")
        print()
        print("这将下载以下平台:")
        for platform_id, desc in manager.COMMON_PLATFORMS.items():
            exists = "✓" if manager.check_platform_exists(platform_id) else "✗"
            print(f"  {exists} {platform_id}: {desc}")
        print()
        
        choice = input("是否继续？(y/n): ").strip().lower()
        
        if choice == 'y':
            print()
            manager.download_common_platforms()
            print()
            print("=" * 70)
            print("✅ 下载完成！")
            print("=" * 70)
            print()
            print("现在可以运行分析，平台文件会自动从本地获取")
        else:
            print("已取消")
    
    elif args.action == 'list':
        manager.list_platforms()
    
    elif args.action == 'check':
        if args.platform:
            exists = manager.check_platform_exists(args.platform)
            file_path = manager.get_platform_file(args.platform)
            
            if exists:
                print(f"✓ {args.platform} 已下载")
                print(f"  路径: {file_path}")
            else:
                print(f"✗ {args.platform} 未下载")
                print(f"  运行 'python {sys.argv[0]} --action download' 下载")
        else:
            print("请指定平台 ID: --platform GPL96")


if __name__ == "__main__":
    main()
