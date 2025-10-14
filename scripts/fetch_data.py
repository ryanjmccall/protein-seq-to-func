"""
Core data access helpers for external biological datasets.
"""

from __future__ import annotations

import io, re
import zipfile
import time
import requests
import pandas as pd
from collections.abc import Iterable

BASE_SEARCH = "https://rest.uniprot.org/uniprotkb/search"
BASE_ENTRY  = "https://rest.uniprot.org/uniprotkb"  # /{accession}

def _ensure_iterable(x):
    if isinstance(x, str):
        return [x]
    if isinstance(x, Iterable):
        return list(x)
    return [x]

def _best_hit(results):
    """
    Prefer reviewed Swiss-Prot hits first; otherwise take the first.
    """
    if not results:
        return None
    reviewed = [r for r in results if r.get("entryType") == "Swiss-Prot" or r.get("reviewed") is True]
    return (reviewed or results)[0]

def split_colon_list(value: str | None) -> list[str]:
    """
    Split a colon/semicolon/comma-separated string into a list of clean items.

    Examples:
        "10.1038/nature01215; 10.1073/pnas.0606143103"
        -> ["10.1038/nature01215", "10.1073/pnas.0606143103"]

        None -> []
        "" -> []
    """
    if not value:
        return []
    parts = re.split(r"[;]", value)
    return [p.strip() for p in parts if p.strip()]


def fetch_uniprot_data(genes: str | Iterable[str]) -> pd.DataFrame:
    """
    Fetch UniProt protein data for human genes, including DOIs & PMIDs from references.
    """
    genes = _ensure_iterable(genes)
    rows = []

    for gene in genes:
        # 1) Search: get the best accession for Homo sapiens
        params = {
            "query": f'gene_exact:{gene} AND organism_id:9606',
            "format": "json",
            "size": 5,  # get a few, we'll choose reviewed if available
            # keep fields minimal; we just need accession & a name for logging
            "fields": "accession,reviewed,protein_name"
        }
        try:
            s = requests.get(BASE_SEARCH, params=params, timeout=30)
            s.raise_for_status()
            hits = s.json().get("results", [])
            hit = _best_hit(hits)
            if not hit:
                print(f"✗ No UniProt result for {gene}")
                continue

            acc = hit["primaryAccession"]

            # 2) Retrieve full entry JSON by accession (rich, includes references)
            e = requests.get(f"{BASE_ENTRY}/{acc}.json", timeout=30)
            e.raise_for_status()
            entry = e.json()

            # basic protein info (be tolerant to missing nested keys)
            protein_name = (
                entry.get("proteinDescription", {})
                     .get("recommendedName", {})
                     .get("fullName", {})
                     .get("value")
            )
            sequence = entry.get("sequence", {}).get("value")

            # 3) Extract references → PMIDs, DOIs, Titles
            dois, pmids, titles = [], [], []
            for ref in entry.get("references", []):
                c = ref.get("citation", {}) or {}
                if (d := c.get("doi")):
                    dois.append(d)
                if (pm := c.get("pubMedId")):
                    pmids.append(pm)
                if (t := c.get("title")):
                    titles.append(t)

            rows.append({
                "gene_symbol": gene,
                "uniprot_id": acc,
                "protein_name": protein_name,
                "sequence": sequence,
                "pmids": "; ".join(pmids) if pmids else None,
                "dois": "; ".join(dois) if dois else None,
                "citation_titles": "; ".join(titles) if titles else None,
                "reviewed": entry.get("entryType") == "Swiss-Prot"
            })

            time.sleep(0.1)  # courtesy delay

        except requests.RequestException as exc:
            print(f"⚠ UniProt request failed for {gene}: {exc}")

    return pd.DataFrame(rows)

def fetch_genage_data(genes: str | Iterable[str] | None = None, zip_url: str = "https://genomics.senescence.info/genes/human_genes.zip") -> pd.DataFrame | None:
    """
    Fetch the GenAge human dataset and optionally filter for one or more gene queries.

    Args:
        genes (str | Iterable[str] | None): Gene symbol(s) or keyword(s) to filter by.
        zip_url (str): URL to the GenAge human genes zip archive.

    Returns:
        pandas.DataFrame | None: DataFrame of GenAge data (filtered if genes provided).
    """
    print(f"Downloading GenAge data from: {zip_url}")

    try:
        # Download and extract CSV
        response = requests.get(zip_url)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            target_csv = "genage_human.csv"
            with archive.open(target_csv) as csv_file:
                df = pd.read_csv(csv_file)

        # If gene queries were provided, filter for them (logical OR across queries)
        if genes:
            gene_queries = _ensure_iterable(genes)

            def row_matches(row: pd.Series) -> bool:
                row_strs = row.astype(str)
                return any(row_strs.str.contains(query, case=False, na=False).any() for query in gene_queries)

            mask = df.apply(row_matches, axis=1)
            df = df.loc[mask]

            if df.empty:
                queries = ", ".join(gene_queries)
                print(f"No results found for gene query: {queries!r}")
                return None

            print(f"Found {len(df)} entries matching query set: {gene_queries}")

        return df

    except Exception as e:
        print(f"Error fetching GenAge data: {e}")
        return None
