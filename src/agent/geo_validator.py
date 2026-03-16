#!/usr/bin/env python3
"""
GEO 数据集预验证工具

在下载之前通过 NCBI Entrez API 快速验证 GSE 数据集是否适合分析：
- 是否为人类数据
- 是否为基因表达谱（非 ChIP-seq / ATAC-seq 等）
- 是否为普通 Series（非 SuperSeries）
- 样本数是否足够
"""

import urllib.request
import json
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# 允许的表达谱类型关键词
VALID_EXPRESSION_TYPES = [
    'expression profiling by array',
    'expression profiling by high throughput sequencing',
    'expression profiling by genome tiling array',
    'expression profiling by snp array',
]

# 明确拒绝的数据类型
INVALID_TYPES = [
    'genome binding',
    'occupancy profiling',
    'chip-seq',
    'chip seq',
    'atac-seq',
    'atac seq',
    'methylation profiling',
    'bisulfite',
    'hi-c',
    'cut&run',
    'cut&tag',
    'snp genotyping',
    'cnv',
    'non-coding rna profiling',
]

MIN_SAMPLES = 10  # 最少样本数


def validate_gse(gse_id: str, timeout: int = 20) -> Dict[str, Any]:
    """
    通过 NCBI Entrez API 验证 GSE 数据集是否适合分析。

    Args:
        gse_id: GEO 数据集 ID，如 'GSE2034'
        timeout: 请求超时秒数

    Returns:
        {
            'valid': bool,          # 是否通过验证
            'reason': str,          # 拒绝原因（valid=False 时）或 'OK'
            'title': str,           # 数据集标题
            'gdstype': str,         # 数据类型
            'taxon': str,           # 物种
            'n_samples': int,       # 样本数
            'entrytype': str,       # GSE / GDS
            'gpl': str,             # 平台 ID
        }
    """
    result = {
        'valid': False,
        'reason': '',
        'title': '',
        'gdstype': '',
        'taxon': '',
        'n_samples': 0,
        'entrytype': '',
        'gpl': '',
    }

    try:
        # Step 1: esearch 拿 UID
        search_url = (
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            f"?db=gds&term={gse_id}[Accession]&retmode=json"
        )
        req = urllib.request.Request(
            search_url,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            search_data = json.loads(r.read())

        id_list = search_data.get('esearchresult', {}).get('idlist', [])
        if not id_list:
            result['reason'] = f'NCBI 中找不到 {gse_id}'
            return result

        uid = id_list[0]
        time.sleep(0.34)  # NCBI 限速：3 req/s

        # Step 2: esummary 拿元数据
        summary_url = (
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            f"?db=gds&id={uid}&retmode=json"
        )
        req2 = urllib.request.Request(
            summary_url,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req2, timeout=timeout) as r:
            summary_data = json.loads(r.read())

        summary = summary_data.get('result', {}).get(uid, {})
        if not summary:
            result['reason'] = f'无法获取 {gse_id} 的元数据'
            return result

        # 填充结果字段
        result['title'] = summary.get('title', '')
        result['gdstype'] = summary.get('gdstype', '')
        result['taxon'] = summary.get('taxon', '')
        result['n_samples'] = int(summary.get('n_samples', 0))
        result['entrytype'] = summary.get('entrytype', '')
        result['gpl'] = summary.get('gpl', '')

        gdstype_lower = result['gdstype'].lower()

        # 验证 1：物种必须是人类
        if result['taxon'] and 'homo sapiens' not in result['taxon'].lower():
            result['reason'] = f"非人类数据（物种: {result['taxon']}）"
            return result

        # 验证 2：必须是表达谱
        is_expression = any(t in gdstype_lower for t in VALID_EXPRESSION_TYPES)
        is_invalid = any(t in gdstype_lower for t in INVALID_TYPES)

        if is_invalid or not is_expression:
            result['reason'] = f"非基因表达谱数据（类型: {result['gdstype']}）"
            return result

        # 验证 3：样本数足够
        if result['n_samples'] < MIN_SAMPLES:
            result['reason'] = f"样本数不足（{result['n_samples']} < {MIN_SAMPLES}）"
            return result

        # 验证 4：不能是 SuperSeries（relations 里有 SubSeries 说明它是 SuperSeries）
        relations = summary.get('relations', [])
        subseries_count = sum(1 for r in relations if r.get('relationtype') == 'SubSeries')
        if subseries_count > 0 and result['n_samples'] == 0:
            result['reason'] = f"SuperSeries（包含 {subseries_count} 个子系列，无直接表达数据）"
            return result

        result['valid'] = True
        result['reason'] = 'OK'
        return result

    except urllib.error.URLError as e:
        result['reason'] = f'网络请求失败: {e}'
        return result
    except Exception as e:
        result['reason'] = f'验证异常: {e}'
        return result


def validate_and_report(gse_id: str) -> Dict[str, Any]:
    """
    验证并打印报告，供 disease_selector 调用。

    Returns:
        同 validate_gse，额外包含 'gse_id' 字段
    """
    logger.info(f"  预验证 {gse_id}...")
    result = validate_gse(gse_id)
    result['gse_id'] = gse_id

    if result['valid']:
        logger.info(
            f"  ✅ {gse_id} 通过验证: {result['gdstype']} | "
            f"{result['taxon']} | {result['n_samples']} 样本"
        )
    else:
        logger.warning(f"  ❌ {gse_id} 验证失败: {result['reason']}")

    return result
