"""
Core data access helpers for external biological datasets.
"""

from __future__ import annotations

import io
import time
import zipfile

from collections.abc import Iterable

import pandas as pd
import requests


def _ensure_iterable(item: str | Iterable[str]) -> list[str]:
    """
    Normalize a single string or iterable of strings into a list of strings.
    """
    if isinstance(item, str):
        return [item]
    return list(item)


def fetch_uniprot_data(genes: str | Iterable[str]) -> pd.DataFrame:
    """
    Fetch protein ID, name, and sequence information from UniProt for each gene symbol.

    Args:
        genes (str | Iterable[str]): One or more official human gene symbols (e.g., 'CCR2' or ['CCR2', 'KCNB1']).

    Returns:
        pandas.DataFrame: A DataFrame containing the fetched protein data.
    """
    base_url = "https://rest.uniprot.org/uniprotkb/search"
    protein_data = []
    gene_list = _ensure_iterable(genes)

    print(f"Fetching data for {len(gene_list)} gene(s) from UniProt...")

    for gene in gene_list:
        query = f'(gene:"{gene}") AND (organism_id:9606)'  # 9606 is Homo sapiens
        params = {
            "query": query,
            "fields": "accession,protein_name,sequence",
            "format": "json",
            "size": 1,  # Only request the primary result
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()

            data = response.json()
            if data and "results" in data and data["results"]:
                result = data["results"][0]
                protein_info = {
                    "gene_symbol": gene,
                    "uniprot_id": result.get("primaryAccession"),
                    "protein_name": result.get("proteinDescription", {}).get("fullName", {}).get("value"),
                    "sequence": result.get("sequence", {}).get("value"),
                }
                protein_data.append(protein_info)
                print(f"  Found data for {gene}")
            else:
                print(f"  No result found for {gene}")

            time.sleep(0.1)  # Small delay to respect the API

        except requests.exceptions.RequestException as exc:
            print(f"  Error occurred for gene {gene}: {exc}")

    print("\nUniProt fetching complete.")
    return pd.DataFrame(protein_data)


def fetch_genage_data(
    genes: str | Iterable[str] | None = None,
    zip_url: str = "https://genomics.senescence.info/genes/human_genes.zip",
) -> pd.DataFrame | None:
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
