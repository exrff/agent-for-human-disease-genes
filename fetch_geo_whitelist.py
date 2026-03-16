#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GEO 精准筛选脚本
================
筛选条件：
  1. 人类 (Homo sapiens)
  2. 纯基因表达谱 (expression profiling by array / by high throughput sequencing)
  3. 排除 SuperSeries（通过 relations 字段检测）
  4. 排除 ChIP-seq / ATAC-seq / methylation 等非表达数据
  5. 样本数 >= MIN_SAMPLES
  6. 仅 GSE 类型（排除 GDS/GPL）

输出：
  - 打印筛选结果表格
  - 保存 data/geo_whitelist.csv
  - 可选：自动更新 src/agent/config.py 的 DATASETS 白名单
"""

import urllib.request
import urllib.parse
import json
import time
import csv
import sys
from pathlib import Path
from typing import List, Dict, Any

# ====================== 【可配置参数】 ======================
EMAIL        = "researcher@example.com"   # NCBI 要求填邮箱（不验证）
MAX_RESULTS  = 200                         # 每次搜索最多返回条数
MIN_SAMPLES  = 20                          # 最少样本数
OUTPUT_CSV   = "data/geo_whitelist.csv"    # 输出文件路径
UPDATE_CONFIG = False                       # 白名单已改为从 CSV 动态加载，无需更新 config.py

# 搜索词：人类 + 基因表达谱 + GSE 类型
SEARCH_TERM = (
    "Homo sapiens[Organism] "
    "AND expression profiling by array[DataSet Type] "
    "AND gse[Entry Type]"
)

# 明确拒绝的数据类型关键词（在 gdstype 字段中匹配）
INVALID_GDSTYPE_KEYWORDS = [
    'genome binding', 'occupancy profiling',
    'chip-seq', 'chip seq',
    'atac-seq', 'atac seq',
    'methylation profiling', 'bisulfite',
    'hi-c', 'cut&run', 'cut&tag',
    'snp genotyping', 'cnv',
    'non-coding rna profiling',
]

# 有效的表达谱类型
VALID_GDSTYPE_KEYWORDS = [
    'expression profiling by array',
    'expression profiling by high throughput sequencing',
    'expression profiling by genome tiling array',
]
# ============================================================


def _get(url: str, timeout: int = 30) -> dict:
    """发送 GET 请求，返回 JSON 解析结果"""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def esearch(term: str, retmax: int = 200) -> List[str]:
    """NCBI esearch：返回 UID 列表"""
    params = urllib.parse.urlencode({
        'db': 'gds',
        'term': term,
        'retmax': retmax,
        'retmode': 'json',
        'email': EMAIL,
    })
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{params}"
    data = _get(url)
    ids = data.get('esearchresult', {}).get('idlist', [])
    print(f"  esearch 返回 {len(ids)} 个 UID")
    return ids


def esummary_batch(uid_list: List[str], batch_size: int = 50) -> List[Dict[str, Any]]:
    """NCBI esummary：分批获取元数据，返回 summary 列表"""
    results = []
    for i in range(0, len(uid_list), batch_size):
        batch = uid_list[i:i + batch_size]
        ids_str = ','.join(batch)
        params = urllib.parse.urlencode({
            'db': 'gds',
            'id': ids_str,
            'retmode': 'json',
            'email': EMAIL,
        })
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?{params}"
        data = _get(url)
        result_map = data.get('result', {})
        for uid in batch:
            if uid in result_map:
                results.append(result_map[uid])
        time.sleep(0.4)  # NCBI 限速：≤3 req/s
        print(f"  已获取 {min(i + batch_size, len(uid_list))}/{len(uid_list)} 条元数据...")
    return results


def is_valid(summary: Dict[str, Any]) -> tuple[bool, str]:
    """
    验证一条 esummary 记录是否符合筛选条件。
    返回 (valid: bool, reason: str)
    """
    gdstype = summary.get('gdstype', '').lower()
    taxon   = summary.get('taxon', '').lower()
    n_samples = int(summary.get('n_samples') or 0)
    entrytype = summary.get('entrytype', '').upper()
    accession = summary.get('accession', '')
    relations = summary.get('relations', [])

    # 必须是 GSE
    if entrytype != 'GSE' or not accession.startswith('GSE'):
        return False, f"非GSE类型 ({entrytype})"

    # 必须是人类
    if 'homo sapiens' not in taxon:
        return False, f"非人类 ({summary.get('taxon', '?')})"

    # 必须是表达谱
    is_expression = any(k in gdstype for k in VALID_GDSTYPE_KEYWORDS)
    is_invalid_type = any(k in gdstype for k in INVALID_GDSTYPE_KEYWORDS)
    if is_invalid_type or not is_expression:
        return False, f"非表达谱 ({summary.get('gdstype', '?')})"

    # 样本数足够
    if n_samples < MIN_SAMPLES:
        return False, f"样本数不足 ({n_samples} < {MIN_SAMPLES})"

    # 排除 SuperSeries：relations 里有 SubSeries 条目
    subseries_count = sum(1 for r in relations if r.get('relationtype') == 'SubSeries')
    if subseries_count > 0:
        return False, f"SuperSeries (含 {subseries_count} 个子系列)"

    return True, "OK"


def infer_disease_type(title: str, summary_text: str) -> str:
    """根据标题和摘要推断疾病类型（简单关键词匹配）"""
    text = (title + ' ' + summary_text).lower()
    rules = [
        ('cancer',          ['cancer', 'carcinoma', 'tumor', 'tumour', 'leukemia', 'lymphoma', 'melanoma', 'glioma']),
        ('neurodegenerative', ['alzheimer', 'parkinson', 'huntington', 'als ', 'amyotrophic', 'neurodegenerat']),
        ('autoimmune',      ['lupus', 'rheumatoid', 'multiple sclerosis', 'autoimmune', 'sjogren', 'psoriasis', 'crohn']),
        ('cardiovascular',  ['heart failure', 'cardiac', 'myocardial', 'atherosclerosis', 'coronary', 'cardiomyopathy']),
        ('metabolic',       ['diabetes', 'obesity', 'fatty liver', 'nafld', 'nash', 'metabolic syndrome', 'kidney', 'renal']),
        ('infection',       ['sepsis', 'influenza', 'tuberculosis', 'hiv', 'covid', 'sars', 'bacterial', 'viral infection']),
        ('psychiatric',     ['schizophrenia', 'depression', 'bipolar', 'autism', 'adhd', 'anxiety']),
        ('respiratory',     ['asthma', 'copd', 'pulmonary', 'lung disease', 'fibrosis']),
        ('repair',          ['wound healing', 'regeneration', 'tissue repair']),
        ('liver',           ['cirrhosis', 'hepatitis', 'liver fibrosis', 'hepatocellular']),
    ]
    for disease_type, keywords in rules:
        if any(kw in text for kw in keywords):
            return disease_type
    return 'other'


def infer_strategy(disease_type: str) -> str:
    return {
        'cancer': 'subtype_comparison',
        'repair': 'time_series',
    }.get(disease_type, 'case_control')


def infer_systems(disease_type: str) -> List[str]:
    return {
        'cancer':           ['System A', 'System B'],
        'neurodegenerative':['System D', 'System A'],
        'autoimmune':       ['System B', 'System A'],
        'cardiovascular':   ['System C', 'System A', 'System D'],
        'metabolic':        ['System C', 'System D'],
        'infection':        ['System B', 'System C'],
        'psychiatric':      ['System D', 'System B'],
        'respiratory':      ['System B', 'System C'],
        'repair':           ['System A', 'System B'],
        'liver':            ['System C', 'System A'],
    }.get(disease_type, ['System A', 'System B'])


def fetch_and_filter() -> List[Dict[str, Any]]:
    """主筛选流程，返回通过验证的数据集列表"""
    print("=" * 60)
    print("GEO 精准筛选")
    print(f"搜索词: {SEARCH_TERM}")
    print(f"最少样本数: {MIN_SAMPLES}")
    print("=" * 60)

    print("\n步骤 1: 搜索 GEO...")
    uid_list = esearch(SEARCH_TERM, retmax=MAX_RESULTS)
    if not uid_list:
        print("未找到任何结果")
        return []

    print(f"\n步骤 2: 获取元数据 ({len(uid_list)} 条)...")
    summaries = esummary_batch(uid_list)

    print(f"\n步骤 3: 过滤验证...")
    valid_datasets = []
    rejected = 0
    for s in summaries:
        ok, reason = is_valid(s)
        if ok:
            disease_type = infer_disease_type(
                s.get('title', ''),
                s.get('summary', '')
            )
            valid_datasets.append({
                'dataset_id':       s.get('accession', ''),
                'name':             s.get('title', '')[:80],
                'chinese_name':     s.get('title', '')[:40],  # 占位，人工翻译
                'disease_type':     disease_type,
                'expected_strategy': infer_strategy(disease_type),
                'expected_systems': infer_systems(disease_type),
                'description':      s.get('summary', '')[:120],
                'platform':         s.get('gpl', ''),
                'n_samples':        int(s.get('n_samples') or 0),
                'pub_date':         s.get('pubdate', ''),
                'gdstype':          s.get('gdstype', ''),
            })
        else:
            rejected += 1

    print(f"  通过: {len(valid_datasets)} 个  |  拒绝: {rejected} 个")
    return valid_datasets


def save_csv(datasets: List[Dict[str, Any]], path: str):
    """保存为 CSV"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not datasets:
        return
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=datasets[0].keys())
        writer.writeheader()
        writer.writerows(datasets)
    print(f"\n已保存: {path}")


def update_config(datasets: List[Dict[str, Any]]):
    """
    将筛选结果追加到 src/agent/config.py 的 DATASETS 白名单中。
    已存在的 dataset_id 不会重复添加。
    """
    config_path = Path("src/agent/config.py")
    if not config_path.exists():
        print("找不到 config.py，跳过自动更新")
        return

    # 读取现有白名单
    sys.path.insert(0, '.')
    try:
        # 直接解析文件，避免 import 触发 langgraph 依赖
        content = config_path.read_text(encoding='utf-8')
        existing_ids = set()
        import re
        for m in re.finditer(r"'(GSE\d+)'\s*:", content):
            existing_ids.add(m.group(1))
    except Exception as e:
        print(f"读取 config.py 失败: {e}")
        return

    new_entries = [d for d in datasets if d['dataset_id'] not in existing_ids]
    if not new_entries:
        print("白名单无需更新（所有数据集已存在）")
        return

    # 生成新条目的 Python 代码
    lines = [f"\n        # ── 自动筛选添加 ({time.strftime('%Y-%m-%d')}) ──────────────────────────────────────\n"]
    for d in new_entries:
        systems_repr = repr(d['expected_systems'])
        lines.append(
            f"        '{d['dataset_id']}': {{\n"
            f"            'name': {repr(d['name'])},\n"
            f"            'chinese_name': {repr(d['chinese_name'])},\n"
            f"            'disease_type': {repr(d['disease_type'])},\n"
            f"            'expected_strategy': {repr(d['expected_strategy'])},\n"
            f"            'expected_systems': {systems_repr},\n"
            f"            'description': {repr(d['description'])},\n"
            f"            'platform': {repr(d['platform'])},\n"
            f"            'n_samples': {d['n_samples']},\n"
            f"        }},\n"
        )

    # 插入到 DATASETS 字典的末尾（找专用标记行）
    insert_marker = "        # ── 自动筛选添加（fetch_geo_whitelist.py）"
    insert_pos = content.find(insert_marker)
    if insert_pos == -1:
        # 标记不存在时，找 DATASETS 结束的 },\n    } 模式
        # 在 STRATEGY_RULES 之前插入
        insert_marker2 = "\n    # 分析策略映射\n    STRATEGY_RULES"
        insert_pos = content.find(insert_marker2)
        if insert_pos == -1:
            print("找不到插入位置，跳过自动更新")
            return
        # 插入到 STRATEGY_RULES 注释行之前
        new_content = (
            content[:insert_pos]
            + f"\n        # ── 自动筛选添加 ({time.strftime('%Y-%m-%d')}) ──────────────────────────────────────\n"
            + ''.join(lines)
            + content[insert_pos:]
        )
    else:
        # 找到标记行的末尾，在其后插入
        insert_end = content.find('\n', insert_pos) + 1
        new_content = (
            content[:insert_end]
            + ''.join(lines)
            + content[insert_end:]
        )
    config_path.write_text(new_content, encoding='utf-8')
    print(f"\n✅ 已向 config.py 白名单追加 {len(new_entries)} 个新数据集:")
    for d in new_entries:
        print(f"   {d['dataset_id']} | {d['disease_type']} | n={d['n_samples']} | {d['name'][:50]}")


def print_table(datasets: List[Dict[str, Any]]):
    """打印结果表格"""
    if not datasets:
        print("无结果")
        return
    print(f"\n{'GSE编号':<12} {'样本数':>6} {'疾病类型':<18} {'平台':<12} {'标题'}")
    print("-" * 100)
    for d in sorted(datasets, key=lambda x: x['disease_type']):
        print(
            f"{d['dataset_id']:<12} "
            f"{d['n_samples']:>6} "
            f"{d['disease_type']:<18} "
            f"{d['platform']:<12} "
            f"{d['name'][:55]}"
        )


if __name__ == "__main__":
    datasets = fetch_and_filter()

    if datasets:
        print_table(datasets)
        save_csv(datasets, OUTPUT_CSV)
    else:
        print("没有符合条件的数据集")
