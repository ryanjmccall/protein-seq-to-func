# epmc_utils.py
# Europe PMC utilities: robust resolution + references/citations listing
# Accepts DOI / PMID / PMCID / title, returns tidy dicts/DataFrames.

from __future__ import annotations

import re
import time
import requests
import pandas as pd
from typing import Optional, Iterable

# ---------- Europe PMC endpoints ----------
EPMC_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
EPMC_SEARCH = f"{EPMC_BASE}/search"
EPMC_ARTICLE = "https://europepmc.org/article"  # /SRC/ID

# ---------- ID parsing ----------
_DOI_RE   = re.compile(r"^\s*(?:doi:)?\s*(10\.\d{4,9}/\S+)\s*$", re.I)
_PMID_RE  = re.compile(r"^\s*(?:pmid:)?\s*(\d{1,12})\s*$", re.I)
_PMCID_RE = re.compile(r"^\s*(?:pmcid:)?\s*(PMC\d+)\s*$", re.I)

# ---------- Helpers ----------
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

def _src_url(source: str, id_: str) -> str:
    from urllib.parse import quote
    return f"{EPMC_ARTICLE}/{source}/{quote(id_, safe='')}"

def _source_url_from_ids(pmcid: Optional[str], pmid: Optional[str], doi: Optional[str]) -> Optional[str]:
    if pmcid:
        return _src_url("PMC", pmcid)
    if pmid:
        return _src_url("MED", pmid)
    if doi:
        return _src_url("DOI", doi)
    return None

def _search_epmc(query: str, page_size: int = 25, result_type: str = "core") -> list[dict]:
    r = requests.get(
        EPMC_SEARCH,
        params={"query": query, "format": "json", "pageSize": page_size, "resultType": result_type},
        timeout=30
    )
    r.raise_for_status()
    return (r.json().get("resultList", {}) or {}).get("result", []) or []

def _multi_try_search(kind: str, val: str) -> list[dict]:
    """
    Try multiple query formulations to be resilient to incomplete/rough inputs.
    """
    tries: list[str] = []
    if kind == "pmcid":
        tries = [f'EXT_ID:{val} AND SRC:PMC', f'PMCID:{val}', val]
    elif kind == "pmid":
        tries = [f'EXT_ID:{val} AND SRC:MED', f'P_MID:{val}', val]
    elif kind == "doi":
        tries = [f'DOI:"{val}"', f'"{val}"', val]
    else:  # title
        tries = [f'"{val}"', val, f'TITLE:"{val}"']

    for q in tries:
        try:
            results = _search_epmc(q, page_size=25, result_type="core")
            if results:
                return results
        except requests.RequestException:
            # try next fallback
            pass
    return []

def _score_and_pick(results: list[dict]) -> dict:
    """
    Pick the 'best' hit:
      1) Prefer items with PMCID (OA richer)
      2) Then PubMed-source items (MED/MEDLINE/PUBMED) for stable PMIDs
      3) Highest relevance score
    """
    def key(r):
        has_pmcid = 1 if r.get("pmcid") else 0
        is_pubmed = 1 if r.get("source") in {"MED", "MEDLINE", "PUBMED"} else 0
        score = float(r.get("score", 0.0))
        return (has_pmcid, is_pubmed, score)
    return sorted(results, key=key, reverse=True)[0]

def _normalize_row(r: dict) -> dict:
    pmid = r.get("id") if r.get("source") in {"MED","MEDLINE","PUBMED"} else r.get("pmid")
    return {
        "PMID": pmid,
        "PMCID": r.get("pmcid"),
        "DOI": r.get("doi"),
        "title": r.get("title"),
        "journal": r.get("journalTitle"),
        "year": int(r["pubYear"]) if str(r.get("pubYear","")).isdigit() else r.get("pubYear"),
        "source_url": _source_url_from_ids(r.get("pmcid"), pmid, r.get("doi")),
    }

# ---------- Public API ----------
def fetch_europe_pmc_best(item: str, delay: float = 0.1) -> dict:
    """
    Query Europe PMC by DOI, PMID, PMCID, or title and return:
    {
      "PMC", "DOI", "PMID", "PMCID", "title", "journal", "year", "source_url"
    }
    All keys are present; unknowns are None.
    - PMC is the numeric part of PMCID (e.g., 'PMC1234567' -> '1234567').
    - If the input was a title and no match is found, 'title' echoes the input.
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

    pmcid  = hit.get("pmcid")
    pmid   = hit.get("id") if hit.get("source") in {"MED","MEDLINE","PUBMED"} else hit.get("pmid")
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
        "source_url": _source_url_from_ids(pmcid, pmid, doi),
    }

    time.sleep(max(0.0, delay))
    return out

def fetch_europe_pmc_best_batch(items: Iterable[str], delay: float = 0.1) -> list[dict]:
    """
    Batch wrapper for fetch_europe_pmc_best.
    """
    return [fetch_europe_pmc_best(it, delay=delay) for it in items]

def list_references_epmc(item: str, page_size: int = 100, delay: float = 0.05) -> pd.DataFrame:
    """
    List all papers that THIS paper CITES (its reference list).
    Accepts DOI/PMID/PMCID/title.
    Returns DataFrame with columns: PMID, PMCID, DOI, title, journal, year, source_url
    """
    resolved = fetch_europe_pmc_best(item, delay=delay)
    # We need a MED/PMCID context for the /references endpoint
    source = None
    id_ = None
    if resolved.get("PMID"):
        source, id_ = "MED", resolved["PMID"]
    elif resolved.get("PMCID"):
        source, id_ = "PMC", resolved["PMCID"]
    else:
        return pd.DataFrame(columns=["PMID","PMCID","DOI","title","journal","year","source_url"])

    rows, page = [], 1
    while True:
        url = f"{EPMC_BASE}/{source}/{id_}/references"
        try:
            resp = requests.get(url, params={"format":"json","pageSize":page_size,"page":page}, timeout=30)
            resp.raise_for_status()
            res = (resp.json().get("referenceList", {}) or {}).get("reference", []) or []
        except requests.RequestException:
            break

        if not res:
            break

        rows.extend(_normalize_row(r) for r in res)
        if len(res) < page_size:
            break
        page += 1
        time.sleep(max(0.0, delay))

    return pd.DataFrame(rows, columns=["PMID","PMCID","DOI","title","journal","year","source_url"])

def list_citations_epmc(item: str, page_size: int = 100, delay: float = 0.05) -> pd.DataFrame:
    """
    List all papers that CITE THIS paper (downstream citations).
    Accepts DOI/PMID/PMCID/title.
    Returns DataFrame with columns: PMID, PMCID, DOI, title, journal, year, source_url
    """
    resolved = fetch_europe_pmc_best(item, delay=delay)
    source = None
    id_ = None
    if resolved.get("PMID"):
        source, id_ = "MED", resolved["PMID"]
    elif resolved.get("PMCID"):
        source, id_ = "PMC", resolved["PMCID"]
    else:
        return pd.DataFrame(columns=["PMID","PMCID","DOI","title","journal","year","source_url"])

    rows, page = [], 1
    while True:
        url = f"{EPMC_BASE}/{source}/{id_}/citations"
        try:
            resp = requests.get(url, params={"format":"json","pageSize":page_size,"page":page}, timeout=30)
            resp.raise_for_status()
            res = (resp.json().get("citationList", {}) or {}).get("citation", []) or []
        except requests.RequestException:
            break

        if not res:
            break

        rows.extend(_normalize_row(r) for r in res)
        if len(res) < page_size:
            break
        page += 1
        time.sleep(max(0.0, delay))

    return pd.DataFrame(rows, columns=["PMID","PMCID","DOI","title","journal","year","source_url"])
