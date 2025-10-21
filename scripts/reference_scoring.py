"""
Utilities to assemble and score Europe PMC articles connected to UniProt entries.
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Iterable, Mapping, Sequence

import pandas as pd

from .fetch_data import fetch_uniprot_data, split_colon_list
from .epmc_utils import (
    expand_literature_network_epmc,
    fetch_epmc,
    fetch_epmc_article_details,
    fetch_epmc_full_text,
)

NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
LONGEVITY_KEYWORDS = [
    "longevity",
    "lifespan",
    "life span",
    "aging",
    "ageing",
    "senescence",
    "geroprotect",
    "pro-longevity",
    "anti-aging",
    "lifespan extension",
    "calorie restriction",
    "healthspan",
]

DEFAULT_WEIGHTS = {"year": 0.4, "function": 0.35, "longevity": 0.25}


def _ensure_gene_iterable(genes: str | Iterable[str]) -> list[str]:
    if isinstance(genes, str):
        return [genes]
    return [g for g in genes]


def _normalize_weights(weights: Mapping[str, float] | None) -> dict[str, float]:
    if not weights:
        weights = DEFAULT_WEIGHTS
    total = sum(weights.values())
    if total <= 0:
        return DEFAULT_WEIGHTS
    return {k: v / total for k, v in weights.items()}


def _primary_relation(relations: str | None) -> str | None:
    if not relations:
        return None
    parts = [p.strip().lower() for p in relations.split(";") if p.strip()]
    if "reference" in parts:
        return "reference"
    if "citation" in parts:
        return "citation"
    if "seed" in parts:
        return "seed"
    return parts[0] if parts else None


def collect_reference_network_for_genes(
    genes: str | Iterable[str] | None = None,
    *,
    uniprot_df: pd.DataFrame | None = None,
    include: Sequence[str] | None = ("references", "citations"),
    max_depth: int = 1,
    delay: float = 0.1,
) -> pd.DataFrame:
    """
    Gather UniProt-linked seed articles plus their references/citations in one DataFrame.
    """
    source_df: pd.DataFrame | None
    if uniprot_df is not None:
        source_df = uniprot_df.copy()
    else:
        gene_list = _ensure_gene_iterable(genes) if genes is not None else []
        if not gene_list:
            return pd.DataFrame()
        source_df = fetch_uniprot_data(gene_list)

    if source_df is None or source_df.empty:
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []
    for _, row in source_df.iterrows():
        gene_symbol = row.get("gene_symbol")
        uniprot_id = row.get("uniprot_id")
        title_list = split_colon_list(row.get("citation_titles"))

        seeds = []
        for title in title_list:
            meta = fetch_epmc(title, delay=delay)
            if meta:
                meta = dict(meta)
                meta["seed_source_title"] = title
                seeds.append(meta)

        if not seeds:
            continue

        network = expand_literature_network_epmc(
            seeds,
            include=include,
            max_depth=max_depth,
            delay=delay,
        )
        if network is None or network.empty:
            continue

        network = network.assign(
            gene_symbol=gene_symbol,
            uniprot_id=uniprot_id,
            seed_titles="; ".join(title_list) if title_list else None,
        )
        network["relation_primary"] = network["relations"].apply(_primary_relation)
        frames.append(network)

    if not frames:
        columns = [
            "node_key",
            "depth",
            "relations",
            "relation_primary",
            "n_parents",
            "parent_keys",
            "PMC",
            "PMID",
            "PMCID",
            "DOI",
            "title",
            "journal",
            "year",
            "source_url",
            "gene_symbol",
            "uniprot_id",
            "seed_titles",
        ]
        return pd.DataFrame(columns=columns)

    combined = pd.concat(frames, ignore_index=True)
    return combined


def _combine_article_text(row: Mapping[str, object], detail: Mapping[str, object]) -> str:
    parts: list[str] = []

    for key in ("title",):
        value = row.get(key)
        if isinstance(value, str):
            parts.append(value)

    for key in ("title", "abstractText", "fullText", "introduction"):
        value = detail.get(key) if isinstance(detail, Mapping) else None
        if isinstance(value, str):
            parts.append(value)

    keywords = detail.get("keywordList") if isinstance(detail, Mapping) else None
    if isinstance(keywords, list):
        parts.extend(str(item) for item in keywords if item)

    return " ".join(parts)


def _function_signal(text: str) -> float:
    if not text:
        return 0.0
    score = 0.0
    for sentence in SENTENCE_SPLIT_RE.split(text):
        lower_sentence = sentence.lower()
        if "function" in lower_sentence:
            numbers = NUMBER_RE.findall(sentence)
            score += 1.0
            score += min(2.0, 0.25 * len(numbers))
    return score


def _longevity_signal(text: str) -> float:
    if not text:
        return 0.0
    lower = text.lower()
    return sum(1.0 for kw in LONGEVITY_KEYWORDS if kw in lower)


def score_reference_dataframe(
    df: pd.DataFrame,
    *,
    weights: Mapping[str, float] | None = None,
    delay: float = 0.1,
    include_fulltext: bool = False,
) -> pd.DataFrame:
    """
    Enrich and score a reference network DataFrame.
    """
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()

    weights = _normalize_weights(weights)
    scored = df.copy()
    current_year = datetime.utcnow().year

    detail_cache: dict[str, dict] = {}
    text_cache: dict[str, str] = {}
    function_raw: list[float] = []
    longevity_raw: list[float] = []
    year_scores: list[float] = []
    abstracts: list[str | None] = []

    for _, row in scored.iterrows():
        node_key = row.get("node_key") or row.get("PMID") or row.get("DOI") or row.get("title")
        node_key = str(node_key) if node_key is not None else None

        if node_key and node_key in detail_cache:
            detail = detail_cache[node_key]
        else:
            lookup = {
                "PMID": row.get("PMID"),
                "PMCID": row.get("PMCID"),
                "DOI": row.get("DOI"),
                "title": row.get("title"),
            }
            detail = fetch_epmc_article_details(
                lookup,
                include_fulltext=include_fulltext,
                delay=delay,
            )
            if node_key:
                detail_cache[node_key] = detail

        abstract_text = detail.get("abstractText") if isinstance(detail, Mapping) else None
        abstracts.append(abstract_text if isinstance(abstract_text, str) else None)

        if node_key and node_key in text_cache:
            combined_text = text_cache[node_key]
        else:
            combined_text = _combine_article_text(row, detail)
            if node_key:
                text_cache[node_key] = combined_text

        function_raw.append(_function_signal(combined_text))
        longevity_raw.append(_longevity_signal(combined_text))

        year_value = row.get("year")
        try:
            year_int = int(year_value) if pd.notna(year_value) else None
        except Exception:
            year_int = None

        if year_int:
            age = max(0, current_year - year_int)
            year_scores.append(1.0 / (1.0 + age))
        else:
            year_scores.append(0.0)

    scored["abstract_text"] = abstracts
    scored["function_signal"] = function_raw
    scored["longevity_signal"] = longevity_raw
    scored["year_score"] = year_scores
    scored["functionality_score"] = [math.tanh(val) for val in function_raw]
    scored["longevity_score"] = [math.tanh(val / 2.0) for val in longevity_raw]

    scored["composite_score"] = (
        scored["year_score"] * weights["year"]
        + scored["functionality_score"] * weights["function"]
        + scored["longevity_score"] * weights["longevity"]
    )

    return scored.sort_values("composite_score", ascending=False, ignore_index=True)


def attach_full_text_columns(
    df: pd.DataFrame,
    *,
    delay: float = 0.1,
    include_xml: bool = True,
) -> pd.DataFrame:
    """
    Ensure the DataFrame contains abstract and full-text content for each row.

    Args:
        df: DataFrame of Europe PMC articles.
        delay: Courtesy delay between API calls.
        include_xml: If True, include the raw full-text XML alongside extracted text.
    """
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()

    enriched = df.copy()
    abstracts: list[str | None] = []
    full_texts: list[str | None] = []
    plain_texts: list[str | None] = []
    full_text_xmls: list[str | None] = []

    for _, row in enriched.iterrows():
        lookup = {
            "PMID": row.get("PMID"),
            "PMCID": row.get("PMCID"),
            "DOI": row.get("DOI"),
            "title": row.get("title"),
        }

        abstract_value = row.get("abstract_text")
        text_payload = fetch_epmc_full_text(lookup, delay=delay, include_xml=include_xml)
        xml_abstract = text_payload.get("abstract")
        if not abstract_value and isinstance(xml_abstract, str) and xml_abstract.strip():
            abstract_value = xml_abstract.strip()

        if not abstract_value:
            detail = fetch_epmc_article_details(lookup, include_fulltext=False, delay=delay)
            detail_abstract = None
            if isinstance(detail, Mapping):
                detail_abstract = detail.get("abstractText")
            if isinstance(detail_abstract, str) and detail_abstract.strip():
                abstract_value = detail_abstract.strip()

        full_text = text_payload.get("text")
        full_texts.append(full_text)
        abstracts.append(abstract_value)
        plain_val = full_text or abstract_value or ""
        plain_texts.append(plain_val)
        if include_xml:
            full_text_xmls.append(text_payload.get("xml"))

    enriched["abstract_text"] = abstracts
    enriched["full_text"] = full_texts
    enriched["plain_text"] = plain_texts
    enriched["Full text"] = enriched["plain_text"].fillna("")
    if include_xml:
        enriched["full_text_xml"] = full_text_xmls

    return enriched


def select_top_scoring_articles(
    df: pd.DataFrame,
    *,
    n_per_gene: int = 5,
    relation_filter: Sequence[str] | None = ("reference", "citation"),
) -> pd.DataFrame:
    """
    Keep the top-N scoring articles per gene/uniprot pair.
    """
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()

    if relation_filter:
        relation_filter = tuple(r.lower() for r in relation_filter)
        filtered = df[df["relation_primary"].str.lower().isin(relation_filter)].copy()
    else:
        filtered = df.copy()

    if filtered.empty:
        return filtered

    sort_cols = ["gene_symbol", "uniprot_id", "composite_score", "year"]
    sort_ascending = [True, True, False, False]
    filtered = filtered.sort_values(sort_cols, ascending=sort_ascending)
    grouped = filtered.groupby(["gene_symbol", "uniprot_id"], dropna=False, sort=False)
    top = grouped.head(n_per_gene).reset_index(drop=True)
    return top
