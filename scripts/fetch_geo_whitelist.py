#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refresh or expand GEO whitelist datasets with configurable auto-screening."""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


EMAIL = "researcher@example.com"
DEFAULT_OUTPUT_CSV = "data/geo_whitelist.csv"
DEFAULT_MAX_RESULTS = 200
DEFAULT_MIN_SAMPLES = 20

DEFAULT_REFRESH_SEARCH_TERM = (
    "Homo sapiens[Organism] "
    "AND expression profiling by array[DataSet Type] "
    "AND gse[Entry Type]"
)

DEFAULT_DISEASE_TITLE_KEYWORDS = [
    "disease",
    "cancer",
    "syndrome",
    "alzheimer",
    "parkinson",
    "diabetes",
    "autoimmune",
    "infection",
]

EXCLUDED_DISEASE_DATASET_KEYWORDS = [
    "mirna",
    "micro rna",
    "micro-rna",
    "microrna",
    "non-coding",
    "non coding",
    "lncrna",
    "long non-coding",
]

INVALID_GDSTYPE_KEYWORDS = [
    "genome binding",
    "occupancy profiling",
    "chip-seq",
    "chip seq",
    "atac-seq",
    "atac seq",
    "methylation profiling",
    "bisulfite",
    "hi-c",
    "cut&run",
    "cut&tag",
    "snp genotyping",
    "cnv",
    "non-coding rna profiling",
]

VALID_GDSTYPE_KEYWORDS = [
    "expression profiling by array",
    "expression profiling by high throughput sequencing",
    "expression profiling by genome tiling array",
]

CSV_HEADERS = [
    "dataset_id",
    "name",
    "chinese_name",
    "disease_type",
    "expected_strategy",
    "expected_systems",
    "description",
    "platform",
    "n_samples",
    "pub_date",
    "gdstype",
]

PLATFORM_AVAILABILITY_CACHE: Dict[str, bool] = {}


def _get(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def esearch(term: str, retmax: int) -> List[str]:
    params = urllib.parse.urlencode(
        {
            "db": "gds",
            "term": term,
            "retmax": retmax,
            "retmode": "json",
            "email": EMAIL,
        }
    )
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{params}"
    data = _get(url)
    ids = data.get("esearchresult", {}).get("idlist", [])
    print(f"  esearch returned {len(ids)} UIDs")
    return ids


def esummary_batch(uid_list: Sequence[str], batch_size: int = 50, delay_s: float = 0.35) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for start in range(0, len(uid_list), batch_size):
        batch = list(uid_list[start : start + batch_size])
        params = urllib.parse.urlencode(
            {
                "db": "gds",
                "id": ",".join(batch),
                "retmode": "json",
                "email": EMAIL,
            }
        )
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?{params}"
        data = _get(url)
        result_map = data.get("result", {})
        for uid in batch:
            if uid in result_map:
                results.append(result_map[uid])
        print(f"  fetched {min(start + batch_size, len(uid_list))}/{len(uid_list)} summaries...")
        time.sleep(delay_s)
    return results


def get_geo_ftp_folder(gse_id: str) -> str:
    """Map GSE accession to GEO ftp directory shard."""
    num_part = gse_id[3:]
    if len(num_part) <= 3:
        return "GSEnnn"
    return gse_id[:-3] + "nnn"


def check_series_matrix_exists(gse_id: str, timeout: int = 12) -> bool:
    ftp_dir = get_geo_ftp_folder(gse_id)
    url = (
        "https://ftp.ncbi.nlm.nih.gov/geo/series/"
        f"{ftp_dir}/{gse_id}/matrix/{gse_id}_series_matrix.txt.gz"
    )
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.getcode() == 200
    except Exception:
        return False


def normalize_platform(raw: str) -> str:
    if not raw:
        return ""
    parts = [item.strip() for item in str(raw).split(";") if item.strip()]
    normalized = []
    for item in parts:
        item = item.upper()
        if item.startswith("GPL"):
            item = item[3:]
        normalized.append(item)
    return ";".join(normalized)


def split_platform_ids(raw: str) -> List[str]:
    values = []
    for item in str(raw or "").split(";"):
        item = item.strip().upper()
        if not item:
            continue
        if not item.startswith("GPL"):
            item = f"GPL{item}"
        values.append(item)
    return values


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    lower = text.lower()
    return any(k.lower() in lower for k in keywords)


def is_valid(summary: Dict[str, Any], min_samples: int) -> tuple[bool, str]:
    gdstype = str(summary.get("gdstype", "")).lower()
    taxon = str(summary.get("taxon", "")).lower()
    n_samples = int(summary.get("n_samples") or 0)
    entrytype = str(summary.get("entrytype", "")).upper()
    accession = str(summary.get("accession", ""))
    relations = summary.get("relations", [])

    if entrytype != "GSE" or not accession.startswith("GSE"):
        return False, f"not a GSE entry ({entrytype})"

    if "homo sapiens" not in taxon:
        return False, f"not human ({summary.get('taxon', '?')})"

    is_expression = _contains_any(gdstype, VALID_GDSTYPE_KEYWORDS)
    is_invalid_type = _contains_any(gdstype, INVALID_GDSTYPE_KEYWORDS)
    if is_invalid_type or not is_expression:
        return False, f"not an expression dataset ({summary.get('gdstype', '?')})"

    if n_samples < min_samples:
        return False, f"too few samples ({n_samples} < {min_samples})"

    subseries_count = sum(1 for relation in relations if relation.get("relationtype") == "SubSeries")
    if subseries_count > 0:
        return False, f"superseries ({subseries_count} subseries)"

    return True, "OK"


def infer_disease_type(title: str, summary_text: str) -> str:
    text = (title + " " + summary_text).lower()
    rules = [
        ("cancer", ["cancer", "carcinoma", "tumor", "tumour", "leukemia", "lymphoma", "melanoma", "glioma"]),
        ("neurodegenerative", ["alzheimer", "parkinson", "huntington", "als ", "amyotrophic", "neurodegenerat"]),
        ("autoimmune", ["lupus", "rheumatoid", "multiple sclerosis", "autoimmune", "sjogren", "psoriasis", "crohn"]),
        ("cardiovascular", ["heart failure", "cardiac", "myocardial", "atherosclerosis", "coronary", "cardiomyopathy"]),
        ("metabolic", ["diabetes", "obesity", "fatty liver", "nafld", "nash", "metabolic syndrome", "kidney", "renal"]),
        ("infection", ["sepsis", "influenza", "tuberculosis", "hiv", "covid", "sars", "bacterial", "viral infection"]),
        ("psychiatric", ["schizophrenia", "depression", "bipolar", "autism", "adhd", "anxiety"]),
        ("respiratory", ["asthma", "copd", "pulmonary", "lung disease", "fibrosis"]),
        ("repair", ["wound healing", "regeneration", "tissue repair"]),
        ("liver", ["cirrhosis", "hepatitis", "liver fibrosis", "hepatocellular"]),
    ]
    for disease_type, keywords in rules:
        if _contains_any(text, keywords):
            return disease_type
    return "other"


def infer_strategy(disease_type: str) -> str:
    return {"cancer": "subtype_comparison", "repair": "time_series"}.get(disease_type, "case_control")


def infer_systems(disease_type: str) -> List[str]:
    return {
        "cancer": ["System A", "System B"],
        "neurodegenerative": ["System D", "System A"],
        "autoimmune": ["System B", "System A"],
        "cardiovascular": ["System C", "System A", "System D"],
        "metabolic": ["System C", "System D"],
        "infection": ["System B", "System C"],
        "psychiatric": ["System D", "System B"],
        "respiratory": ["System B", "System C"],
        "repair": ["System A", "System B"],
        "liver": ["System C", "System A"],
    }.get(disease_type, ["System A", "System B"])


def summary_to_row(summary: Dict[str, Any]) -> Dict[str, Any]:
    disease_type = infer_disease_type(summary.get("title", ""), summary.get("summary", ""))
    return {
        "dataset_id": summary.get("accession", ""),
        "name": str(summary.get("title", ""))[:120],
        "chinese_name": str(summary.get("title", ""))[:40],
        "disease_type": disease_type,
        "expected_strategy": infer_strategy(disease_type),
        "expected_systems": ";".join(infer_systems(disease_type)),
        "description": str(summary.get("summary", ""))[:300],
        "platform": normalize_platform(summary.get("gpl", "")),
        "n_samples": int(summary.get("n_samples") or 0),
        "pub_date": summary.get("pubdate", "") or "",
        "gdstype": summary.get("gdstype", "") or "",
    }


def looks_disease_relevant_text(title: str, summary_text: str, keywords: Sequence[str]) -> bool:
    blob = f"{title} {summary_text}".lower()
    return any(keyword.lower() in blob for keyword in keywords)


def has_excluded_dataset_keywords(title: str, summary_text: str) -> bool:
    blob = f"{title} {summary_text}".lower()
    return any(keyword in blob for keyword in EXCLUDED_DISEASE_DATASET_KEYWORDS)


def _http_exists(url: str, timeout: int) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.getcode() == 200
    except Exception:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.getcode() == 200
        except Exception:
            return False


def is_platform_available(platform_id: str, timeout: int = 8, cache_dir: str = "data/gpl_platforms") -> bool:
    platform_id = platform_id.strip().upper()
    if not platform_id:
        return False
    if platform_id in PLATFORM_AVAILABILITY_CACHE:
        return PLATFORM_AVAILABILITY_CACHE[platform_id]

    # 1) local cache
    local_dir = Path(cache_dir)
    if local_dir.exists():
        for file in local_dir.iterdir():
            if file.name.upper().startswith(platform_id):
                PLATFORM_AVAILABILITY_CACHE[platform_id] = True
                return True

    # 2) remote ftp candidates (annot + soft)
    num = platform_id.replace("GPL", "")
    shard = f"GPL{num[:-3]}nnn" if len(num) > 3 else "GPLnnn"
    urls = [
        f"https://ftp.ncbi.nlm.nih.gov/geo/platforms/{shard}/{platform_id}/annot/{platform_id}.annot.gz",
        f"https://ftp.ncbi.nlm.nih.gov/geo/platforms/{shard}/{platform_id}/annot/{platform_id}.txt",
        f"https://ftp.ncbi.nlm.nih.gov/geo/platforms/{shard}/{platform_id}/annot/{platform_id}_annot.txt.gz",
        f"https://ftp.ncbi.nlm.nih.gov/geo/platforms/{shard}/{platform_id}/soft/{platform_id}_family.soft.gz",
        f"https://ftp.ncbi.nlm.nih.gov/geo/platforms/{shard}/{platform_id}/soft/{platform_id}.soft.gz",
    ]
    for url in urls:
        if _http_exists(url, timeout=timeout):
            PLATFORM_AVAILABILITY_CACHE[platform_id] = True
            return True

    PLATFORM_AVAILABILITY_CACHE[platform_id] = False
    return False


def all_platforms_available(platform_field: str, timeout: int = 8, cache_dir: str = "data/gpl_platforms") -> bool:
    platforms = split_platform_ids(platform_field)
    if not platforms:
        return False
    return all(is_platform_available(pid, timeout=timeout, cache_dir=cache_dir) for pid in platforms)


def _parse_platforms(raw: str) -> List[str]:
    if not raw.strip():
        return []
    out = []
    for token in raw.split(","):
        token = token.strip().upper()
        if not token:
            continue
        if not token.startswith("GPL"):
            token = f"GPL{token}"
        out.append(token)
    return out


def build_expand_term(platform: str, disease_keywords: Sequence[str]) -> str:
    disease_clause = " OR ".join([f"{kw}[Title]" for kw in disease_keywords]) if disease_keywords else ""
    if disease_clause:
        disease_clause = f" AND ({disease_clause})"
    return (
        f"\"{platform}\"[Accession] "
        "AND Homo sapiens[Organism] "
        "AND gse[Entry Type] "
        "AND expression profiling by array[DataSet Type]"
        f"{disease_clause}"
    )


def fetch_refresh(
    max_results: int,
    min_samples: int,
    check_matrix: bool,
    require_disease_text: bool,
    disease_keywords: Sequence[str],
    require_platform_available: bool,
    platform_check_timeout: int,
    platform_cache_dir: str,
) -> List[Dict[str, Any]]:
    print("=" * 60)
    print("Mode: refresh whitelist")
    print(f"Search term: {DEFAULT_REFRESH_SEARCH_TERM}")
    print(f"Minimum samples: {min_samples}")
    print("=" * 60)

    ids = esearch(DEFAULT_REFRESH_SEARCH_TERM, retmax=max_results)
    if not ids:
        return []
    summaries = esummary_batch(ids)
    rows: List[Dict[str, Any]] = []
    rejected = {
        "invalid_metadata": 0,
        "excluded_keywords": 0,
        "non_disease_text": 0,
        "missing_matrix": 0,
        "platform_unavailable": 0,
    }
    for summary in summaries:
        ok, _ = is_valid(summary, min_samples=min_samples)
        if not ok:
            rejected["invalid_metadata"] += 1
            continue
        title = str(summary.get("title", ""))
        summary_text = str(summary.get("summary", ""))
        if has_excluded_dataset_keywords(title, summary_text):
            rejected["excluded_keywords"] += 1
            continue
        if require_disease_text and not looks_disease_relevant_text(title, summary_text, disease_keywords):
            rejected["non_disease_text"] += 1
            continue
        row = summary_to_row(summary)
        if check_matrix and row["dataset_id"] and not check_series_matrix_exists(row["dataset_id"]):
            rejected["missing_matrix"] += 1
            continue
        if require_platform_available and not all_platforms_available(
            row.get("platform", ""),
            timeout=platform_check_timeout,
            cache_dir=platform_cache_dir,
        ):
            rejected["platform_unavailable"] += 1
            continue
        rows.append(row)
    print("refresh accepted:", len(rows))
    print("refresh rejected:", rejected)
    return rows


def fetch_expand(
    platforms: Sequence[str],
    max_results_per_platform: int,
    min_samples: int,
    disease_keywords: Sequence[str],
    check_matrix: bool,
    api_delay_s: float,
    require_disease_text: bool,
    require_platform_available: bool,
    platform_check_timeout: int,
    platform_cache_dir: str,
) -> List[Dict[str, Any]]:
    print("=" * 60)
    print("Mode: expand whitelist")
    print(f"Platforms: {', '.join(platforms)}")
    print(f"Disease keywords: {', '.join(disease_keywords) if disease_keywords else 'none'}")
    print(f"Minimum samples: {min_samples}")
    print("=" * 60)

    merged_by_accession: Dict[str, Dict[str, Any]] = {}
    for platform in platforms:
        print(f"\nSearching platform {platform}...")
        term = build_expand_term(platform, disease_keywords)
        ids = esearch(term, retmax=max_results_per_platform)
        if not ids:
            continue
        summaries = esummary_batch(ids)
        accepted = 0
        rejected = {
            "invalid_metadata": 0,
            "excluded_keywords": 0,
            "non_disease_text": 0,
            "missing_matrix": 0,
            "platform_unavailable": 0,
        }
        for summary in summaries:
            ok, _ = is_valid(summary, min_samples=min_samples)
            if not ok:
                rejected["invalid_metadata"] += 1
                continue
            title = str(summary.get("title", ""))
            summary_text = str(summary.get("summary", ""))
            if has_excluded_dataset_keywords(title, summary_text):
                rejected["excluded_keywords"] += 1
                continue
            if require_disease_text and not looks_disease_relevant_text(title, summary_text, disease_keywords):
                rejected["non_disease_text"] += 1
                continue
            row = summary_to_row(summary)
            # Keep platform target if summary lacks platform info.
            if not row["platform"]:
                row["platform"] = normalize_platform(platform)
            if check_matrix and row["dataset_id"] and not check_series_matrix_exists(row["dataset_id"]):
                rejected["missing_matrix"] += 1
                continue
            if require_platform_available and not all_platforms_available(
                row.get("platform", ""),
                timeout=platform_check_timeout,
                cache_dir=platform_cache_dir,
            ):
                rejected["platform_unavailable"] += 1
                continue
            merged_by_accession[row["dataset_id"]] = row
            accepted += 1
            time.sleep(api_delay_s)
        print(f"  accepted for {platform}: {accepted}")
        print(f"  rejected for {platform}: {rejected}")
    return list(merged_by_accession.values())


def load_existing(path: str) -> Dict[str, Dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    with open(file_path, "r", newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            dataset_id = (row.get("dataset_id") or "").strip()
            if not dataset_id:
                continue
            out[dataset_id] = {key: row.get(key, "") for key in CSV_HEADERS}
    return out


def merge_rows(existing: Dict[str, Dict[str, Any]], new_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged = dict(existing)
    for row in new_rows:
        dataset_id = row.get("dataset_id", "")
        if not dataset_id:
            continue
        normalized = {key: row.get(key, "") for key in CSV_HEADERS}
        merged[dataset_id] = normalized
    return list(merged.values())


def save_csv(rows: Sequence[Dict[str, Any]], path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sorted_rows = sorted(rows, key=lambda item: str(item.get("dataset_id", "")))
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(sorted_rows)
    print(f"\nSaved: {path} ({len(sorted_rows)} rows)")


def print_table(rows: Sequence[Dict[str, Any]]) -> None:
    if not rows:
        print("No results.")
        return
    print(f"\n{'GSE':<12} {'Samples':>7} {'Disease Type':<18} {'Platform':<12} Title")
    print("-" * 100)
    for row in rows[:80]:
        print(
            f"{str(row.get('dataset_id', '')):<12} "
            f"{int(row.get('n_samples', 0)):>7} "
            f"{str(row.get('disease_type', '')):<18} "
            f"{str(row.get('platform', '')):<12} "
            f"{str(row.get('name', ''))[:55]}"
        )
    if len(rows) > 80:
        print(f"... ({len(rows) - 80} more rows omitted)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh or expand GEO whitelist automatically.")
    parser.add_argument("--email", default=EMAIL, help="NCBI email for E-utilities requests")
    parser.add_argument("--mode", choices=["refresh", "expand"], default="refresh")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_CSV, help="CSV output path")
    parser.add_argument("--min-samples", type=int, default=DEFAULT_MIN_SAMPLES)
    parser.add_argument("--max-results", type=int, default=DEFAULT_MAX_RESULTS)
    parser.add_argument("--check-series-matrix", action="store_true", help="HEAD-check series_matrix.txt.gz")
    parser.add_argument("--merge", action="store_true", help="merge with existing output csv")
    parser.add_argument(
        "--platforms",
        default="",
        help="comma-separated GPL ids for expand mode, e.g. GPL570,GPL13158",
    )
    parser.add_argument(
        "--disease-keywords",
        default=",".join(DEFAULT_DISEASE_TITLE_KEYWORDS),
        help="comma-separated title keywords used in expand mode query",
    )
    parser.add_argument("--api-delay", type=float, default=0.35, help="delay seconds between accepted items")
    parser.add_argument(
        "--allow-non-disease",
        action="store_true",
        help="do not enforce disease-text keyword filter",
    )
    parser.add_argument(
        "--skip-platform-check",
        action="store_true",
        help="skip platform availability pre-check",
    )
    parser.add_argument(
        "--platform-check-timeout",
        type=int,
        default=8,
        help="timeout (s) for each platform availability check",
    )
    parser.add_argument(
        "--platform-cache-dir",
        default="data/gpl_platforms",
        help="local GPL cache directory used for pre-check",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    global EMAIL
    EMAIL = args.email

    if args.mode == "refresh":
        disease_keywords = [item.strip() for item in args.disease_keywords.split(",") if item.strip()]
        rows = fetch_refresh(
            max_results=args.max_results,
            min_samples=args.min_samples,
            check_matrix=args.check_series_matrix,
            require_disease_text=not args.allow_non_disease,
            disease_keywords=disease_keywords,
            require_platform_available=not args.skip_platform_check,
            platform_check_timeout=args.platform_check_timeout,
            platform_cache_dir=args.platform_cache_dir,
        )
    else:
        platforms = _parse_platforms(args.platforms)
        if not platforms:
            raise SystemExit("expand mode requires --platforms")
        disease_keywords = [item.strip() for item in args.disease_keywords.split(",") if item.strip()]
        rows = fetch_expand(
            platforms=platforms,
            max_results_per_platform=args.max_results,
            min_samples=args.min_samples,
            disease_keywords=disease_keywords,
            check_matrix=args.check_series_matrix,
            api_delay_s=args.api_delay,
            require_disease_text=not args.allow_non_disease,
            require_platform_available=not args.skip_platform_check,
            platform_check_timeout=args.platform_check_timeout,
            platform_cache_dir=args.platform_cache_dir,
        )

    print_table(rows)

    if args.merge:
        existing = load_existing(args.output)
        merged = merge_rows(existing, rows)
        print(f"\nMerging: existing={len(existing)}, new={len(rows)}, merged={len(merged)}")
        save_csv(merged, args.output)
    else:
        save_csv(rows, args.output)


if __name__ == "__main__":
    main()
