#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch and refresh the unified GEO whitelist CSV."""

import csv
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

EMAIL = "researcher@example.com"
MAX_RESULTS = 200
MIN_SAMPLES = 20
OUTPUT_CSV = "data/geo_whitelist.csv"

SEARCH_TERM = (
    "Homo sapiens[Organism] "
    "AND expression profiling by array[DataSet Type] "
    "AND gse[Entry Type]"
)

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


def _get(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def esearch(term: str, retmax: int = 200) -> List[str]:
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


def esummary_batch(uid_list: List[str], batch_size: int = 50) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for start in range(0, len(uid_list), batch_size):
        batch = uid_list[start : start + batch_size]
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
        time.sleep(0.4)
        print(f"  fetched {min(start + batch_size, len(uid_list))}/{len(uid_list)} summaries...")
    return results


def is_valid(summary: Dict[str, Any]) -> tuple[bool, str]:
    gdstype = summary.get("gdstype", "").lower()
    taxon = summary.get("taxon", "").lower()
    n_samples = int(summary.get("n_samples") or 0)
    entrytype = summary.get("entrytype", "").upper()
    accession = summary.get("accession", "")
    relations = summary.get("relations", [])

    if entrytype != "GSE" or not accession.startswith("GSE"):
        return False, f"not a GSE entry ({entrytype})"

    if "homo sapiens" not in taxon:
        return False, f"not human ({summary.get('taxon', '?')})"

    is_expression = any(keyword in gdstype for keyword in VALID_GDSTYPE_KEYWORDS)
    is_invalid_type = any(keyword in gdstype for keyword in INVALID_GDSTYPE_KEYWORDS)
    if is_invalid_type or not is_expression:
        return False, f"not an expression dataset ({summary.get('gdstype', '?')})"

    if n_samples < MIN_SAMPLES:
        return False, f"too few samples ({n_samples} < {MIN_SAMPLES})"

    subseries_count = sum(
        1 for relation in relations if relation.get("relationtype") == "SubSeries"
    )
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
        if any(keyword in text for keyword in keywords):
            return disease_type
    return "other"


def infer_strategy(disease_type: str) -> str:
    return {"cancer": "subtype_comparison", "repair": "time_series"}.get(
        disease_type, "case_control"
    )


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


def fetch_and_filter() -> List[Dict[str, Any]]:
    print("=" * 60)
    print("Refreshing GEO whitelist")
    print(f"Search term: {SEARCH_TERM}")
    print(f"Minimum samples: {MIN_SAMPLES}")
    print("=" * 60)

    print("\nStep 1: searching GEO...")
    uid_list = esearch(SEARCH_TERM, retmax=MAX_RESULTS)
    if not uid_list:
        print("No results found.")
        return []

    print(f"\nStep 2: fetching metadata for {len(uid_list)} entries...")
    summaries = esummary_batch(uid_list)

    print("\nStep 3: filtering datasets...")
    valid_datasets: List[Dict[str, Any]] = []
    rejected = 0
    for summary in summaries:
        ok, _reason = is_valid(summary)
        if ok:
            disease_type = infer_disease_type(
                summary.get("title", ""),
                summary.get("summary", ""),
            )
            valid_datasets.append(
                {
                    "dataset_id": summary.get("accession", ""),
                    "name": summary.get("title", "")[:80],
                    "chinese_name": summary.get("title", "")[:40],
                    "disease_type": disease_type,
                    "expected_strategy": infer_strategy(disease_type),
                    "expected_systems": ";".join(infer_systems(disease_type)),
                    "description": summary.get("summary", "")[:120],
                    "platform": summary.get("gpl", ""),
                    "n_samples": int(summary.get("n_samples") or 0),
                    "pub_date": summary.get("pubdate", ""),
                    "gdstype": summary.get("gdstype", ""),
                }
            )
        else:
            rejected += 1

    print(f"  accepted: {len(valid_datasets)} | rejected: {rejected}")
    return valid_datasets


def save_csv(datasets: List[Dict[str, Any]], path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not datasets:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=datasets[0].keys())
        writer.writeheader()
        writer.writerows(datasets)
    print(f"\nSaved: {path}")


def print_table(datasets: List[Dict[str, Any]]) -> None:
    if not datasets:
        print("No results.")
        return
    print(f"\n{'GSE':<12} {'Samples':>7} {'Disease Type':<18} {'Platform':<12} Title")
    print("-" * 100)
    for dataset in sorted(datasets, key=lambda item: item["disease_type"]):
        print(
            f"{dataset['dataset_id']:<12} "
            f"{dataset['n_samples']:>7} "
            f"{dataset['disease_type']:<18} "
            f"{dataset['platform']:<12} "
            f"{dataset['name'][:55]}"
        )


if __name__ == "__main__":
    datasets = fetch_and_filter()
    if datasets:
        print_table(datasets)
        save_csv(datasets, OUTPUT_CSV)
    else:
        print("No dataset matched the current whitelist criteria.")
