"""
This function parses a database (PMC, Europe PMC, ets.), and extracrs the following default JSON file. 

{
  "pmcid": "PMC123456",
  "doi": "10.xxxx/yyy",
  "title": "Example study",
  "year": 2020,
  "journal": "J Aging",
  "protein_hits": ["APOE"],
  "xml": "<full PMC XML ...>",   
  "plain_text": "Full plain text here...",
  "source_url": "https://europepmc.org/.../PMC123456"
}

"""

import re
import time
import html
import requests
from typing import Iterable, Optional

EPMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EPMC_ARTICLE_URL = "https://europepmc.org/article"  # /SRC/ID

# ----- Patterns -----
_DOI_RE   = re.compile(r"^\s*(?:doi:)?\s*(10\.\d{4,9}/\S+)\s*$", re.I)
_PMID_RE  = re.compile(r"^\s*(?:pmid:)?\s*(\d{1,12})\s*$", re.I)
_PMCID_RE = re.compile(r"^\s*(?:pmcid:)?\s*(PMC\d+)\s*$", re.I)

def _classify(q: str) -> tuple[str, str]:
    """Return ('doi'|'pmid'|'pmcid'|'title', normalized_value)."""
    s = q.strip()
    if (m := _PMCID_RE.match(s)): return "pmcid", m.group(1).upper()
    if (m := _PMID_RE.match(s)):  return "pmid",  m.group(1)
    if (m := _DOI_RE.match(s)):   return "doi",   m.group(1)
    return "title", s

def _pmc_numeric(pmcid: Optional[str]) -> Optional[str]:
    if not pmcid:
        return None
    m = re.match(r"PMC(\d+)", pmcid, re.I)
    return m.group(1) if m else None

def _source_url(pmcid: Optional[str], pmid: Optional[str], doi: Optional[str]) -> Optional[str]:
    if pmcid:
        return f"{EPMC_ARTICLE_URL}/PMC/{pmcid}"
    if pmid:
        return f"{EPMC_ARTICLE_URL}/MED/{pmid}"
    if doi:
        from urllib.parse import quote
        return f"{EPMC_ARTICLE_URL}/DOI/{quote(doi, safe='')}"
    return None

def _score_and_pick(results: list[dict]) -> dict:
    """
    Pick the 'best' hit:
      1) Prefer items with PMCID (open access often richer)
      2) Then prefer PubMed-source (MED/MEDLINE/PUBMED) for stable PMIDs
      3) Highest relevance score as tie-breaker
    """
    def key(r):
        has_pmcid = 1 if r.get("pmcid") else 0
        is_pubmed = 1 if r.get("source") in {"MED", "MEDLINE", "PUBMED"} else 0
        score = float(r.get("score", 0.0))
        return (has_pmcid, is_pubmed, score)
    return sorted(results, key=key, reverse=True)[0]

def _search_epmc(query: str, page_size: int = 25, result_type: str = "core") -> list[dict]:
    params = {"query": query, "format": "json", "pageSize": page_size, "resultType": result_type}
    r = requests.get(EPMC_SEARCH_URL, params=params, timeout=30)
    r.raise_for_status()
    return (r.json().get("resultList", {}) or {}).get("result", []) or []

def _multi_try_search(kind: str, val: str) -> list[dict]:
    """
    Try multiple query formulations to be resilient to incomplete/rough inputs.
    """
    tries = []
    if kind == "pmcid":
        tries = [
            f'EXT_ID:{val} AND SRC:PMC',
            f'PMCID:{val}',
            val,  # raw fallback
        ]
    elif kind == "pmid":
        tries = [
            f'EXT_ID:{val} AND SRC:MED',
            f'P_MID:{val}',  # older alias sometimes seen
            val,
        ]
    elif kind == "doi":
        tries = [
            f'DOI:"{val}"',
            f'"{val}"',
            val,
        ]
    else:  # title
        # Phrase, then unquoted (tokenized), then TITLE field
        tries = [
            f'"{val}"',
            val,
            f'TITLE:"{val}"',
        ]

    for q in tries:
        try:
            results = _search_epmc(q, page_size=25, result_type="core")
            if results:
                return results
        except requests.RequestException:
            # try next fallback
            pass
    return []

def fetch_europe_pmc_best(item: str, delay: float = 0.1) -> dict:
    """
    Query Europe PMC by DOI, PMID, PMCID, or title and return:
    {
      "PMC", "DOI", "PMID", "PMCID", "title", "journal", "year", "source_url"
    }
    All keys are present; unknowns are None.
    """
    kind, norm = _classify(item)
    results = _multi_try_search(kind, norm)

    if not results:
        time.sleep(max(0.0, delay))
        return {
            "PMC": None,
            "DOI": None,
            "PMID": None,
            "PMCID": None,
            "title": item if kind == "title" else None,
            "journal": None,
            "year": None,
            "source_url": None,
        }

    hit = _score_and_pick(results)

    pmcid  = hit.get("pmcid")  # e.g., "PMC1234567"
    # PMID lives in 'id' for PubMed sources; otherwise may be absent
    pmid   = hit.get("id") if hit.get("source") in {"MED", "MEDLINE", "PUBMED"} else hit.get("pmid")
    doi    = hit.get("doi")
    title  = hit.get("title")
    year   = hit.get("pubYear")
    journal= hit.get("journalTitle")

    out = {
        "PMC": _pmc_numeric(pmcid),
        "DOI": doi,
        "PMID": pmid,
        "PMCID": pmcid,
        "title": title if title else (item if kind == "title" else None),
        "journal": journal,
        "year": int(year) if year and str(year).isdigit() else year,
        "source_url": _source_url(pmcid, pmid, doi),
    }

    time.sleep(max(0.0, delay))
    return out

def fetch_europe_pmc_best_batch(items: Iterable[str], delay: float = 0.1) -> list[dict]:
    return [fetch_europe_pmc_best(it, delay=delay) for it in items]
