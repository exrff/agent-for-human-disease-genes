#!/usr/bin/env python3
"""GEO dataset downloader for series matrix and GPL annotation files."""

from __future__ import annotations

import gzip
import html
import logging
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional


class GEODownloader:
    """Download GEO series matrix files and matching GPL annotations."""

    def __init__(self, output_base_dir: str = "data/validation_datasets"):
        self.output_base_dir = Path(output_base_dir)
        self.logger = logging.getLogger(__name__)
        self.geo_ftp_base = "https://ftp.ncbi.nlm.nih.gov/geo"

    def download_dataset(self, gse_id: str) -> Dict[str, object]:
        self.logger.info("=" * 70)
        self.logger.info(f"开始下载数据集: {gse_id}")
        self.logger.info("=" * 70)

        output_dir = self.output_base_dir / gse_id
        output_dir.mkdir(parents=True, exist_ok=True)

        result: Dict[str, object] = {
            "gse_id": gse_id,
            "success": False,
            "series_matrix_file": None,
            "platform_files": [],
            "errors": [],
        }

        self.logger.info("步骤 1: 下载 series matrix 文件...")
        series_file = self._download_series_matrix(gse_id, output_dir)
        if not series_file:
            error_msg = "❌ Series matrix 下载失败"
            self.logger.error(error_msg)
            result["errors"].append(error_msg)
            return result

        result["series_matrix_file"] = str(series_file)
        self.logger.info(f"✅ Series matrix 下载成功: {series_file.name}")

        self.logger.info("步骤 2: 提取平台信息...")
        platform_ids = self._extract_platform_ids(series_file)
        if not platform_ids:
            error_msg = "⚠️  无法提取平台信息，将尝试常见平台"
            self.logger.warning(error_msg)
            result["errors"].append(error_msg)
            platform_ids = self._guess_platform(gse_id)

        self.logger.info(f"找到平台: {', '.join(platform_ids)}")

        self.logger.info("步骤 3: 获取平台注释文件...")
        for platform_id in platform_ids:
            platform_file = self._get_platform_file(platform_id, output_dir)
            if platform_file:
                result["platform_files"].append(str(platform_file))
                self.logger.info(f"✅ 平台文件: {platform_file.name}")
            else:
                error_msg = f"⚠️  平台 {platform_id} 获取失败"
                self.logger.warning(error_msg)
                result["errors"].append(error_msg)

        if result["series_matrix_file"] and result["platform_files"]:
            result["success"] = True
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
        gse_num = gse_id.replace("GSE", "")
        gse_dir = f"GSE{gse_num[:-3]}nnn"
        url = f"{self.geo_ftp_base}/series/{gse_dir}/{gse_id}/matrix/{gse_id}_series_matrix.txt.gz"
        output_file = output_dir / f"{gse_id}_series_matrix.txt.gz"

        try:
            self.logger.info(f"  下载 URL: {url}")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=300) as response:
                total_size = int(response.headers.get("Content-Length", 0))
                self.logger.info(f"  文件大小: {total_size / 1024 / 1024:.2f} MB")
                with open(output_file, "wb") as fh:
                    while True:
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        fh.write(chunk)

            if self._validate_gzip_file(output_file):
                return output_file

            self.logger.error("  文件验证失败")
            output_file.unlink(missing_ok=True)
            return None
        except Exception as exc:
            self.logger.error(f"  下载失败: {exc}")
            return None

    def _get_platform_file(self, platform_id: str, output_dir: Path) -> Optional[Path]:
        _ = output_dir
        cache_dir = Path("data/gpl_platforms")
        cache_dir.mkdir(parents=True, exist_ok=True)

        cached_file = self._copy_cached_platform_file(platform_id)
        if cached_file:
            return cached_file

        downloaded_file = self._download_platform_file(platform_id, cache_dir)
        if downloaded_file:
            return downloaded_file

        self.logger.error(f"  ❌ 本地未找到 {platform_id} 平台文件，且在线下载失败")
        return None

    def _copy_cached_platform_file(self, platform_id: str) -> Optional[Path]:
        gpl_dir = Path("data/gpl_platforms")
        if not gpl_dir.exists():
            return None

        for platform_file in gpl_dir.iterdir():
            if platform_file.name.startswith(platform_id) and (
                platform_file.suffix in (".txt", ".gz")
                or platform_file.name.endswith(".soft")
                or platform_file.name.endswith(".soft.gz")
            ):
                self.logger.info(f"  ✓ 找到本地平台文件: {platform_file.name}")
                return platform_file
        return None

    def _download_platform_file(self, platform_id: str, output_dir: Path) -> Optional[Path]:
        full_table_file = self._download_platform_full_table(platform_id, output_dir)
        if full_table_file:
            return full_table_file
        annot_file = self._download_platform_from_ftp(platform_id, output_dir)
        if annot_file:
            return annot_file
        return self._download_platform_soft_from_ftp(platform_id, output_dir)

    def _download_platform_full_table(self, platform_id: str, output_dir: Path) -> Optional[Path]:
        page_url = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={platform_id}"
        try:
            req = urllib.request.Request(page_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as response:
                page_html = response.read().decode("utf-8", errors="ignore")

            match = re.search(
                rf"OpenLink\('([^']*mode=raw[^']*acc={platform_id}[^']*)'",
                page_html,
            )
            if not match:
                self.logger.warning(f"  未找到 GPL 完整表格下载链接: {platform_id}")
                return None

            raw_path = html.unescape(match.group(1))
            raw_url = urllib.parse.urljoin("https://www.ncbi.nlm.nih.gov", raw_path)
            self.logger.info(f"  下载 GPL 完整表格: {raw_url}")

            req = urllib.request.Request(raw_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=300) as response:
                disposition = response.headers.get("Content-Disposition", "")
                filename_match = re.search(r'filename="?([^";]+)"?', disposition)
                filename = filename_match.group(1) if filename_match else f"{platform_id}.txt"
                output_file = output_dir / filename
                with open(output_file, "wb") as fh:
                    while True:
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        fh.write(chunk)

            if output_file.exists() and output_file.stat().st_size > 0:
                return output_file
        except Exception as exc:
            self.logger.warning(f"  GPL 完整表格下载失败 {platform_id}: {exc}")
        return None

    def _download_platform_from_ftp(self, platform_id: str, output_dir: Path) -> Optional[Path]:
        platform_num = platform_id.replace("GPL", "")
        platform_dir = f"GPL{platform_num[:-3]}nnn"
        base_url = f"{self.geo_ftp_base}/platforms/{platform_dir}/{platform_id}/annot"
        candidate_filenames = [
            f"{platform_id}.annot.gz",
            f"{platform_id}.txt",
            f"{platform_id}_annot.txt.gz",
        ]

        for filename in candidate_filenames:
            file_url = f"{base_url}/{filename}"
            output_file = output_dir / filename
            try:
                self.logger.info(f"  尝试 FTP 平台文件: {file_url}")
                req = urllib.request.Request(file_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=300) as response:
                    with open(output_file, "wb") as fh:
                        while True:
                            chunk = response.read(65536)
                            if not chunk:
                                break
                            fh.write(chunk)
                if output_file.exists() and output_file.stat().st_size > 0:
                    return output_file
            except Exception:
                output_file.unlink(missing_ok=True)
                continue
        return None

    def _download_platform_soft_from_ftp(self, platform_id: str, output_dir: Path) -> Optional[Path]:
        platform_num = platform_id.replace("GPL", "")
        platform_dir = f"GPL{platform_num[:-3]}nnn"
        base_url = f"{self.geo_ftp_base}/platforms/{platform_dir}/{platform_id}/soft"
        candidate_filenames = [
            f"{platform_id}_family.soft.gz",
            f"{platform_id}.soft.gz",
            f"{platform_id}_family.soft",
            f"{platform_id}.soft",
        ]

        for filename in candidate_filenames:
            file_url = f"{base_url}/{filename}"
            output_file = output_dir / filename
            try:
                self.logger.info(f"  尝试 FTP SOFT 平台文件: {file_url}")
                req = urllib.request.Request(file_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=300) as response:
                    with open(output_file, "wb") as fh:
                        while True:
                            chunk = response.read(65536)
                            if not chunk:
                                break
                            fh.write(chunk)
                if output_file.exists() and output_file.stat().st_size > 0:
                    return output_file
            except Exception:
                output_file.unlink(missing_ok=True)
                continue
        return None

    def _extract_platform_ids(self, series_file: Path) -> List[str]:
        platform_ids: List[str] = []
        try:
            with gzip.open(series_file, "rt", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if line.startswith("!Series_platform_id"):
                        parts = line.strip().split("\t")
                        if len(parts) > 1:
                            platform_id = parts[1].strip('"')
                            if platform_id.startswith("GPL"):
                                platform_ids.append(platform_id)
                    if line.startswith("!series_matrix_table_begin"):
                        break
        except Exception as exc:
            self.logger.error(f"提取平台 ID 失败: {exc}")
        return list(dict.fromkeys(platform_ids))

    def _guess_platform(self, gse_id: str) -> List[str]:
        _ = gse_id
        return ["GPL96", "GPL570"]

    def _validate_gzip_file(self, file_path: Path) -> bool:
        try:
            with gzip.open(file_path, "rt", encoding="utf-8", errors="ignore") as fh:
                for idx, _line in enumerate(fh):
                    if idx >= 5:
                        break
            return True
        except Exception as exc:
            self.logger.error(f"文件验证失败: {exc}")
            return False

    def check_dataset_exists(self, gse_id: str) -> bool:
        dataset_dir = self.output_base_dir / gse_id
        if not dataset_dir.exists():
            return False

        series_file = dataset_dir / f"{gse_id}_series_matrix.txt.gz"
        if not series_file.exists():
            return False

        return True


def download_geo_dataset(gse_id: str, output_dir: str = "data/validation_datasets") -> Dict[str, object]:
    downloader = GEODownloader(output_dir)
    return downloader.download_dataset(gse_id)


def check_dataset_exists(gse_id: str, data_dir: str = "data/validation_datasets") -> bool:
    downloader = GEODownloader(data_dir)
    return downloader.check_dataset_exists(gse_id)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    gse_id = sys.argv[1] if len(sys.argv) > 1 else "GSE2034"
    print(f"\n测试下载: {gse_id}\n")
    result = download_geo_dataset(gse_id)

    print("\n" + "=" * 70)
    if result["success"]:
        print("✅ 下载成功！")
        print(f"Series matrix: {result['series_matrix_file']}")
        print(f"Platform 文件: {len(result['platform_files'])} 个")
        for platform_file in result["platform_files"]:
            print(f"  - {Path(platform_file).name}")
    else:
        print("❌ 下载失败")
        for error in result["errors"]:
            print(f"  {error}")
    print("=" * 70)
