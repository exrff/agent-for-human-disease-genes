#!/usr/bin/env python3
"""
GEO 数据集自动下载器

功能：
1. 自动下载 GEO 数据集（series matrix 和 platform 文件）
2. 支持多种数据格式
3. 自动解压和验证
"""

import os
import gzip
import urllib.request
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict
import time


class GEODownloader:
    """GEO 数据集下载器"""
    
    def __init__(self, output_base_dir: str = "data/validation_datasets"):
        """
        初始化下载器
        
        Args:
            output_base_dir: 输出基础目录
        """
        self.output_base_dir = Path(output_base_dir)
        self.logger = logging.getLogger(__name__)
        
        # GEO FTP 基础 URL
        self.geo_ftp_base = "https://ftp.ncbi.nlm.nih.gov/geo"
        
        # 初始化 GPL 管理器
        try:
            try:
                from .gpl_manager import GPLManager
            except ImportError:
                from src.data_extraction.gpl_manager import GPLManager
            self.gpl_manager = GPLManager()
        except Exception as e:
            self.logger.warning(f"GPL 管理器初始化失败: {e}")
            self.gpl_manager = None
        
    def download_dataset(self, gse_id: str) -> Dict[str, any]:
        """
        下载完整的 GEO 数据集
        
        Args:
            gse_id: GEO 数据集 ID (如 GSE2034)
        
        Returns:
            下载结果字典
        """
        self.logger.info(f"=" * 70)
        self.logger.info(f"开始下载数据集: {gse_id}")
        self.logger.info(f"=" * 70)
        
        # 创建输出目录
        output_dir = self.output_base_dir / gse_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        result = {
            'gse_id': gse_id,
            'success': False,
            'series_matrix_file': None,
            'platform_files': [],
            'errors': []
        }
        
        # 1. 下载 series matrix 文件
        self.logger.info("步骤 1: 下载 series matrix 文件...")
        series_file = self._download_series_matrix(gse_id, output_dir)
        
        if series_file:
            result['series_matrix_file'] = str(series_file)
            self.logger.info(f"✅ Series matrix 下载成功: {series_file.name}")
        else:
            error_msg = f"❌ Series matrix 下载失败"
            self.logger.error(error_msg)
            result['errors'].append(error_msg)
            return result
        
        # 2. 提取平台信息
        self.logger.info("步骤 2: 提取平台信息...")
        platform_ids = self._extract_platform_ids(series_file)
        
        if not platform_ids:
            error_msg = "⚠️  无法提取平台信息，将尝试常见平台"
            self.logger.warning(error_msg)
            result['errors'].append(error_msg)
            # 尝试常见平台
            platform_ids = self._guess_platform(gse_id)
        
        self.logger.info(f"找到平台: {', '.join(platform_ids)}")
        
        # 3. 下载平台注释文件
        self.logger.info("步骤 3: 下载平台注释文件...")
        for platform_id in platform_ids:
            # 优先从本地 GPL 数据库查找
            platform_file = self._get_platform_file(platform_id, output_dir)
            
            if platform_file:
                result['platform_files'].append(str(platform_file))
                self.logger.info(f"✅ 平台文件: {platform_file.name}")
            else:
                error_msg = f"⚠️  平台 {platform_id} 获取失败"
                self.logger.warning(error_msg)
                result['errors'].append(error_msg)
        
        # 4. 验证下载
        if result['series_matrix_file'] and len(result['platform_files']) > 0:
            result['success'] = True
            self.logger.info("=" * 70)
            self.logger.info(f"✅ {gse_id} 下载完成！")
            self.logger.info(f"   Series matrix: {Path(result['series_matrix_file']).name}")
            self.logger.info(f"   Platform 文件: {len(result['platform_files'])} 个")
            self.logger.info("=" * 70)
        else:
            self.logger.error("=" * 70)
            self.logger.error(f"❌ {gse_id} 下载不完整")
            self.logger.error("=" * 70)
        
        return result
    
    def _download_series_matrix(self, gse_id: str, output_dir: Path) -> Optional[Path]:
        """下载 series matrix 文件"""
        
        # 构建 URL
        # 例如: GSE2034 -> GSE2nnn/GSE2034/matrix/
        gse_num = gse_id.replace('GSE', '')
        gse_dir = f"GSE{gse_num[:-3]}nnn"  # GSE2034 -> GSE2nnn
        
        url = f"{self.geo_ftp_base}/series/{gse_dir}/{gse_id}/matrix/{gse_id}_series_matrix.txt.gz"
        
        output_file = output_dir / f"{gse_id}_series_matrix.txt.gz"
        
        try:
            self.logger.info(f"  下载 URL: {url}")
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=300) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                self.logger.info(f"  文件大小: {total_size / 1024 / 1024:.2f} MB")
                
                with open(output_file, 'wb') as f:
                    while True:
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
            
            if self._validate_gzip_file(output_file):
                return output_file
            else:
                self.logger.error("  文件验证失败")
                output_file.unlink(missing_ok=True)
                return None
                
        except Exception as e:
            self.logger.error(f"  下载失败: {e}")
            return None
    
    def _get_platform_file(self, platform_id: str, output_dir: Path) -> Optional[Path]:
        """
        获取平台文件（优先使用本地 GPL 数据库）
        
        Args:
            platform_id: 平台 ID
            output_dir: 输出目录
        
        Returns:
            平台文件路径
        """
        # 方法 1: 从本地 GPL 数据库获取
        if self.gpl_manager:
            local_file = self.gpl_manager.get_platform_file(platform_id)
            if local_file:
                self.logger.info(f"  ✓ 从本地 GPL 数据库获取: {platform_id}")
                
                # 复制到数据集目录（可选）
                import shutil
                dest_file = output_dir / local_file.name
                if not dest_file.exists():
                    shutil.copy2(local_file, dest_file)
                
                return dest_file
        
        # 方法 2: 在线下载
        self.logger.info(f"  本地未找到 {platform_id}，尝试在线下载...")
        return self._download_platform(platform_id, output_dir)
    
    def _download_platform(self, platform_id: str, output_dir: Path) -> Optional[Path]:
        """下载平台注释文件"""
        
        # 构建平台目录名: GPL96 -> GPL0nnn, GPL17988 -> GPL17nnn
        num = platform_id.replace('GPL', '')
        prefix_len = max(1, len(num) - 3)
        platform_dir = f"GPL{num[:prefix_len]}nnn"
        
        # 方法 1: 尝试 annot 目录下的常见格式
        possible_files = [
            f"{platform_id}.annot.gz",
            f"{platform_id}.txt",
        ]
        
        for filename in possible_files:
            url = f"{self.geo_ftp_base}/platforms/{platform_dir}/{platform_id}/annot/{filename}"
            output_file = output_dir / filename
            
            try:
                self.logger.info(f"  尝试下载: {filename}")
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=60) as response:
                    with open(output_file, 'wb') as f:
                        while True:
                            chunk = response.read(65536)
                            if not chunk:
                                break
                            f.write(chunk)
                
                self.logger.info(f"  ✓ 下载成功: {filename}")
                return output_file
                    
            except Exception as e:
                self.logger.debug(f"  下载失败 ({filename}): {e}")
                if output_file.exists():
                    output_file.unlink()
                continue
        
        # 方法 2: 尝试下载 GPL soft 文件（许多新平台只有 soft 格式）
        self.logger.info(f"  尝试下载 GPL soft 文件...")
        soft_files = [
            f"{platform_id}_family.soft.gz",
            f"{platform_id}.soft.gz",
        ]
        for filename in soft_files:
            url = f"{self.geo_ftp_base}/platforms/{platform_dir}/{platform_id}/soft/{filename}"
            output_file = output_dir / filename
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=120) as response:
                    with open(output_file, 'wb') as f:
                        while True:
                            chunk = response.read(65536)
                            if not chunk:
                                break
                            f.write(chunk)
                self.logger.info(f"  ✓ 下载 soft 文件成功: {filename}")
                # 转换 soft.gz → txt 格式供后续解析
                converted = self._convert_soft_to_txt(output_file, platform_id, output_dir)
                if converted:
                    return converted
                return output_file
            except Exception as e:
                self.logger.debug(f"  soft 下载失败 ({filename}): {e}")
                if output_file.exists():
                    output_file.unlink()
                continue
        
        # 方法 3: 从 GEO 网页找到正确文件名
        self.logger.info(f"  尝试查找平台目录中的文件...")
        try:
            platform_page_url = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={platform_id}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            req = urllib.request.Request(platform_page_url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                page_content = resp.read().decode('utf-8', errors='ignore')
            
            import re
            pattern = rf'{platform_id}-\d+\.txt'
            matches = re.findall(pattern, page_content)
            
            if matches:
                filename = matches[0]
                self.logger.info(f"  找到文件: {filename}")
                url = f"{self.geo_ftp_base}/platforms/{platform_dir}/{platform_id}/annot/{filename}"
                output_file = output_dir / filename
                
                req2 = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req2, timeout=60) as response:
                    with open(output_file, 'wb') as f:
                        while True:
                            chunk = response.read(65536)
                            if not chunk:
                                break
                            f.write(chunk)
                
                self.logger.info(f"  ✓ 下载成功: {filename}")
                return output_file
        
        except Exception as e:
            self.logger.debug(f"  查找文件失败: {e}")
        
        return None

    def _convert_soft_to_txt(self, soft_gz_file: Path, platform_id: str, output_dir: Path) -> Optional[Path]:
        """将 GPL soft.gz 文件转换为简单的 probe→gene txt 格式"""
        import gzip, re
        output_file = output_dir / f"{platform_id}.txt"
        try:
            rows = []
            with gzip.open(soft_gz_file, 'rt', encoding='utf-8', errors='ignore') as f:
                in_table = False
                header = None
                id_col = gene_col = None
                for line in f:
                    line = line.rstrip('\n')
                    if line.startswith('!platform_table_begin'):
                        in_table = True
                        continue
                    if line.startswith('!platform_table_end'):
                        break
                    if in_table:
                        if header is None:
                            header = line.split('\t')
                            # 找 ID 列和 gene symbol 列
                            for i, h in enumerate(header):
                                h_lower = h.lower()
                                if h_lower == 'id':
                                    id_col = i
                                if 'gene_assignment' in h_lower or 'gene symbol' in h_lower or 'gene_symbol' in h_lower or 'symbol' in h_lower:
                                    gene_col = i
                            if id_col is None:
                                id_col = 0
                            if gene_col is None:
                                # 找包含 gene 的列
                                for i, h in enumerate(header):
                                    if 'gene' in h.lower():
                                        gene_col = i
                                        break
                            rows.append('ID\tGene Symbol')
                        else:
                            parts = line.split('\t')
                            if len(parts) > max(id_col or 0, gene_col or 0):
                                probe = parts[id_col] if id_col is not None else parts[0]
                                gene_raw = parts[gene_col] if gene_col is not None else ''
                                # gene_assignment 格式: "NM_xxx // GENE // ..." 取第二个 //
                                if '//' in gene_raw:
                                    gene = gene_raw.split('//')[1].strip()
                                else:
                                    gene = gene_raw.strip()
                                rows.append(f"{probe}\t{gene}")
            
            if len(rows) > 1:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(rows))
                self.logger.info(f"  ✓ soft 转换完成: {output_file.name} ({len(rows)-1} probes)")
                return output_file
        except Exception as e:
            self.logger.debug(f"  soft 转换失败: {e}")
        return None
        
        return None

    
    def _extract_platform_ids(self, series_file: Path) -> list:
        """从 series matrix 文件中提取平台 ID"""
        
        platform_ids = []
        
        try:
            with gzip.open(series_file, 'rt', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.startswith('!Series_platform_id'):
                        # 格式: !Series_platform_id	"GPL96"
                        parts = line.strip().split('\t')
                        if len(parts) > 1:
                            platform_id = parts[1].strip('"')
                            if platform_id.startswith('GPL'):
                                platform_ids.append(platform_id)
                    
                    # 只读取前 100 行（元数据部分）
                    if line.startswith('!series_matrix_table_begin'):
                        break
        
        except Exception as e:
            self.logger.error(f"提取平台 ID 失败: {e}")
        
        return list(set(platform_ids))  # 去重
    
    def _guess_platform(self, gse_id: str) -> list:
        """根据 GSE ID 猜测可能的平台"""
        
        # 常见平台映射
        common_platforms = {
            'GPL96': 'Affymetrix Human Genome U133A',
            'GPL570': 'Affymetrix Human Genome U133 Plus 2.0',
            'GPL6480': 'Agilent-014850 Whole Human Genome',
            'GPL10558': 'Illumina HumanHT-12 V4.0',
        }
        
        # 返回最常见的平台
        return ['GPL96', 'GPL570']
    
    def _validate_gzip_file(self, file_path: Path) -> bool:
        """验证 gzip 文件是否有效"""
        
        try:
            with gzip.open(file_path, 'rt', encoding='utf-8', errors='ignore') as f:
                # 尝试读取前几行
                for i, line in enumerate(f):
                    if i >= 5:
                        break
            return True
        except Exception as e:
            self.logger.error(f"文件验证失败: {e}")
            return False
    
    def check_dataset_exists(self, gse_id: str) -> bool:
        """检查数据集是否已下载"""
        
        dataset_dir = self.output_base_dir / gse_id
        
        if not dataset_dir.exists():
            return False
        
        # 检查必要文件
        series_file = dataset_dir / f"{gse_id}_series_matrix.txt.gz"
        
        if not series_file.exists():
            return False
        
        # 检查是否有平台文件
        platform_files = list(dataset_dir.glob("GPL*.annot.gz")) + \
                        list(dataset_dir.glob("GPL*.txt"))
        
        return len(platform_files) > 0


# ============================================================================
# 便捷函数
# ============================================================================

def download_geo_dataset(gse_id: str, output_dir: str = "data/validation_datasets") -> Dict:
    """
    下载 GEO 数据集（便捷函数）
    
    Args:
        gse_id: GEO 数据集 ID
        output_dir: 输出目录
    
    Returns:
        下载结果字典
    
    Example:
        result = download_geo_dataset('GSE2034')
        if result['success']:
            print(f"下载成功: {result['series_matrix_file']}")
    """
    downloader = GEODownloader(output_dir)
    return downloader.download_dataset(gse_id)


def check_dataset_exists(gse_id: str, data_dir: str = "data/validation_datasets") -> bool:
    """
    检查数据集是否已存在
    
    Args:
        gse_id: GEO 数据集 ID
        data_dir: 数据目录
    
    Returns:
        是否存在
    """
    downloader = GEODownloader(data_dir)
    return downloader.check_dataset_exists(gse_id)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) > 1:
        gse_id = sys.argv[1]
    else:
        gse_id = "GSE2034"
    
    print(f"\n测试下载: {gse_id}\n")
    
    result = download_geo_dataset(gse_id)
    
    print("\n" + "=" * 70)
    if result['success']:
        print("✅ 下载成功！")
        print(f"Series matrix: {result['series_matrix_file']}")
        print(f"Platform 文件: {len(result['platform_files'])} 个")
        for pf in result['platform_files']:
            print(f"  - {Path(pf).name}")
    else:
        print("❌ 下载失败")
        for error in result['errors']:
            print(f"  {error}")
    print("=" * 70)
