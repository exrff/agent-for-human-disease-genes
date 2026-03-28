#!/usr/bin/env python3
"""Shared GEO parsing helpers for the active analysis pipeline."""

from pathlib import Path
from typing import Dict, Optional


def validate_series_matrix(series_file) -> dict:
    """Validate that a GEO series matrix contains usable human expression data."""
    import gzip

    result = {"has_data": False, "reason": "", "organism": None, "sample_count": 0}
    non_expression_types = [
        "chip-seq",
        "atac-seq",
        "chip seq",
        "genome binding",
        "occupancy profiling",
        "hi-c",
        "cut&run",
        "cut&tag",
        "bisulfite",
        "methylation",
        "snp array",
        "cnv",
    ]

    try:
        path = Path(series_file)
        opener = (
            gzip.open(path, "rt", encoding="utf-8", errors="ignore")
            if path.suffix == ".gz"
            else open(path, "r", encoding="utf-8", errors="ignore")
        )
        has_table = False
        organism = None
        is_super = False
        sample_count = 0
        series_types = []

        with opener as f:
            for line in f:
                lower = line.lower()
                if "!series_matrix_table_begin" in lower:
                    has_table = True
                if "!Series_platform_taxid" in line or "!Series_sample_taxid" in line:
                    if "10090" in line:
                        organism = "mouse"
                    elif "9606" in line:
                        organism = "human"
                if "SuperSeries" in line or "This SuperSeries" in line:
                    is_super = True
                if "!Series_sample_id" in line:
                    sample_count = len(line.split()) - 1
                if "!Series_type" in line:
                    series_types.append(lower)

        result["organism"] = organism
        result["sample_count"] = sample_count

        if is_super and not has_table:
            result["reason"] = "SuperSeries without a usable expression matrix"
            return result
        if not has_table:
            result["reason"] = "Missing !series_matrix_table_begin"
            return result

        all_types = " ".join(series_types)
        for bad_type in non_expression_types:
            if bad_type in all_types:
                result["reason"] = f"Non-expression dataset type: {bad_type}"
                return result

        if organism == "mouse":
            result["reason"] = "Mouse dataset is not used in the human-disease pipeline"
            return result

        if sample_count < 6:
            result["reason"] = f"Too few samples for comparison: {sample_count}"
            return result

        result["has_data"] = True
        result["reason"] = "OK"
    except Exception as exc:
        result["reason"] = f"Validation failed: {exc}"

    return result


def find_gpl_file(series_file: Path, dataset_dir: Path) -> Optional[Path]:
    """Find the platform annotation file for a GEO series matrix."""
    import gzip
    import re

    platform_id = None
    try:
        with gzip.open(series_file, "rt", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("!Series_platform_id"):
                    match = re.search(r"GPL\d+", line)
                    if match:
                        platform_id = match.group()
                    break
    except Exception:
        pass

    for search_dir in [Path("data/gpl_platforms"), dataset_dir]:
        if not search_dir.exists():
            continue
        if platform_id:
            for file in search_dir.iterdir():
                if file.name.startswith(platform_id) and file.suffix in (".txt", ".gz"):
                    return file
        for file in search_dir.iterdir():
            if file.name.startswith("GPL") and file.suffix in (".txt", ".gz"):
                return file

    return None


def parse_series_matrix(series_file: Path):
    """Parse a GEO series matrix into a probe-by-sample DataFrame."""
    import gzip
    import pandas as pd

    with gzip.open(series_file, "rt", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    data_start = None
    for i, line in enumerate(lines):
        if line.startswith("!series_matrix_table_begin"):
            data_start = i + 1
            break

    if data_start is None:
        raise ValueError("Missing !series_matrix_table_begin")

    data_lines = []
    for line in lines[data_start:]:
        if line.startswith("!series_matrix_table_end"):
            break
        data_lines.append(line.strip().split("\t"))

    header = [cell.strip('"') for cell in data_lines[0]]
    rows = [[cell.strip('"') for cell in row] for row in data_lines[1:] if row]

    df = pd.DataFrame(rows, columns=header)
    df = df.set_index(df.columns[0])
    df.index.name = "probe_id"
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(how="all")


def parse_gpl_annotation(gpl_file: Path):
    """Parse a GPL annotation file into probe-to-gene mappings."""
    import gzip
    import re
    from io import StringIO

    import pandas as pd

    name = gpl_file.name.lower()
    if name.endswith(".gz"):
        opener = lambda: gzip.open(gpl_file, "rt", encoding="utf-8", errors="ignore")
    else:
        opener = lambda: open(gpl_file, "r", encoding="utf-8", errors="ignore")

    with opener() as f:
        lines = f.readlines()

    data_start = None
    for i, line in enumerate(lines):
        if line.startswith("!platform_table_begin"):
            data_start = i + 1
            break
    if data_start is None:
        for i, line in enumerate(lines):
            if (
                not line.startswith("#")
                and not line.startswith("!")
                and not line.startswith("^")
                and line.strip()
            ):
                data_start = i
                break

    if data_start is None:
        raise ValueError("Cannot locate platform annotation table in GPL file")

    data_end = len(lines)
    for i in range(data_start, len(lines)):
        if lines[i].startswith("!platform_table_end"):
            data_end = i
            break

    content = "".join(lines[data_start:data_end])
    df = pd.read_csv(StringIO(content), sep="\t", low_memory=False, on_bad_lines="skip")

    probe_col = next(
        (c for c in df.columns if c.upper() in ("ID", "PROBE_ID", "PROBEID")),
        df.columns[0],
    )

    gene_col_candidates = [
        "Gene Symbol",
        "GENE_SYMBOL",
        "Gene_Symbol",
        "Symbol",
        "SYMBOL",
        "gene_symbol",
        "Gene",
        "GENE",
        "gene_assignment",
        "Gene Assignment",
        "GENE_ASSIGNMENT",
    ]
    gene_col = next((c for c in gene_col_candidates if c in df.columns), None)
    if gene_col is None:
        gene_col = next((c for c in df.columns if "gene" in c.lower()), None)

    # Some GEO family.soft platform tables store Ensembl IDs in `ID` while
    # `SPOT_ID` holds the actual gene symbol (for example GPL33988).
    if "SPOT_ID" in df.columns:
        probe_is_ensembl = (
            df[probe_col].astype(str).str.match(r"^ENS[A-Z]*G", na=False).mean() > 0.6
        )
        spot_looks_like_symbol = (
            df["SPOT_ID"]
            .astype(str)
            .str.match(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,19}$", na=False)
            .mean()
            > 0.6
        )
        gene_col_is_ensembl = False
        if gene_col is not None:
            gene_col_is_ensembl = (
                df[gene_col].astype(str).str.contains(r"^ENS[A-Z]*G", regex=True, na=False).mean()
                > 0.6
            )

        if probe_is_ensembl and spot_looks_like_symbol and (gene_col is None or gene_col_is_ensembl):
            gene_col = "SPOT_ID"

    if gene_col is not None:
        mapping = df[[probe_col, gene_col]].copy()
        mapping.columns = ["probe_id", "gene_symbol"]
    else:
        annotation_candidates = [
            c
            for c in df.columns
            if c.upper().startswith("SPOT_ID")
            or "description" in c.lower()
            or "transcript" in c.lower()
        ]
        annotation_col = None
        if annotation_candidates:
            annotation_col = max(
                annotation_candidates,
                key=lambda col: df[col].astype(str).str.len().mean(),
            )
        if annotation_col is None:
            raise ValueError(f"Cannot find gene symbol column. Available columns: {list(df.columns)}")
        mapping = df[[probe_col, annotation_col]].copy()
        mapping.columns = ["probe_id", "gene_symbol"]
        mapping["gene_symbol"] = (
            mapping["gene_symbol"].astype(str).apply(extract_gene_symbol_from_annotation)
        )

    mapping = mapping.dropna(subset=["gene_symbol"])
    mapping = mapping[
        ~mapping["gene_symbol"].astype(str).str.strip().isin(["", "---", "null", "NULL", "nan"])
    ]
    mapping["gene_symbol"] = (
        mapping["gene_symbol"]
        .astype(str)
        .str.split("///")
        .str[0]
        .str.split("//")
        .str[0]
        .str.strip()
    )
    mapping["probe_id"] = mapping["probe_id"].astype(str)
    return mapping.reset_index(drop=True)


def extract_gene_symbol_from_annotation(annotation: str) -> str:
    """Extract a plausible gene symbol from free-form GPL annotation text."""
    import re

    text = str(annotation)
    patterns = [
        r"Homo sapiens [^(]+\(([A-Za-z0-9\-]+)\),",
        r"\(([A-Za-z0-9\-]+)\)\[gene_biotype:",
        r"\b([A-Z0-9\-]{2,15})\b(?= \[Source:HGNC Symbol;Acc:HGNC:)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return ""


def map_probe_to_gene(expr_df, mapping_df):
    """Aggregate probe-level expression into gene-level expression by mean."""
    merged = expr_df.reset_index().merge(mapping_df, on="probe_id", how="inner")
    merged = merged.drop("probe_id", axis=1)
    return merged.groupby("gene_symbol").mean()


def extract_sample_info(series_file: Path) -> Dict:
    """Extract sample metadata from a GEO series matrix file."""
    import gzip

    info = {"accessions": [], "titles": [], "characteristics": []}
    try:
        with gzip.open(series_file, "rt", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("!Sample_geo_accession"):
                    info["accessions"] = [x.strip('"') for x in line.strip().split("\t")[1:]]
                elif line.startswith("!Sample_title"):
                    info["titles"] = [x.strip('"') for x in line.strip().split("\t")[1:]]
                elif line.startswith("!Sample_characteristics_ch1"):
                    chars = [x.strip('"') for x in line.strip().split("\t")[1:]]
                    info["characteristics"].append(chars)
                elif line.startswith("!series_matrix_table_begin"):
                    break
        info["sample_count"] = len(info["accessions"])
    except Exception:
        pass
    return info
