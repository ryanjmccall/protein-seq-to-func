# epmc_utils.py
# Europe PMC utilities: robust resolution + references/citations listing
# Accepts DOI / PMID / PMCID / title, returns tidy dicts/DataFrames.

from __future__ import annotations

import re
import time
import json
import hashlib
import requests
import pandas as pd
from pathlib import Path
from xml.etree import ElementTree as ET
from collections import deque
from typing import Optional, Iterable, Mapping, Any, Tuple

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

def _json_safe(value: Any) -> Any:
    """
    Convert pandas/numpy scalars into plain Python types that json can handle.
    """
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        # Likely a list/dict/str that pd.isna cannot interpret.
        pass
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value

def _search_epmc(query: str, page_size: int = 25, result_type: str = "core") -> list[dict]:
    r = requests.get(
        EPMC_SEARCH,
        params={"query": query, "format": "json", "pageSize": page_size, "resultType": result_type},
        timeout=30
    )
    r.raise_for_status()
    return (r.json().get("resultList", {}) or {}).get("result", []) or []

_DETAIL_CACHE: dict[tuple[str, str, bool], dict] = {}
_FULLTEXT_CACHE: dict[str, dict[str, Optional[str]]] = {}

_PMCID_CLEAN_RE = re.compile(r"PMC(\d+)", re.I)


def _normalize_pmcid(value: Any) -> Optional[str]:
    """
    Return an uppercase PMCID string (e.g., 'PMC1234567') if value looks like one.
    """
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    match = _PMCID_CLEAN_RE.search(text)
    if match:
        return f"PMC{match.group(1)}"
    if text.upper().startswith("PMC"):
        return text.upper()
    return None


def _fetch_epmc_search_abstract(source: str, identifier: str, delay: float = 0.1) -> Optional[str]:
    """
    Use the search endpoint to fetch a core record and return abstractText if present.
    """
    if not source or not identifier:
        return None

    source = source.upper()

    query_id = identifier if source != "DOI" else identifier.strip()
    query = f'EXT_ID:"{query_id}" AND SRC:{source}'

    try:
        resp = requests.get(
            EPMC_SEARCH,
            params={"query": query, "format": "json", "resultType": "core"},
            timeout=30,
        )
        resp.raise_for_status()
        results = (resp.json().get("resultList", {}) or {}).get("result", []) or []
    except requests.RequestException:
        return None

    time.sleep(max(0.0, delay))
    if not results:
        return None

    abstract = results[0].get("abstractText")
    if isinstance(abstract, str) and abstract.strip():
        return abstract.strip()
    return None

def _coerce_structured_abstract(data: Any) -> str:
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        parts = []
        for item in data:
            if isinstance(item, Mapping):
                text = item.get("text") or item.get("label")
                if text:
                    parts.append(str(text))
        return " ".join(parts)
    return ""

def fetch_epmc_article_details(
    item_or_dict: ResolvedInput,
    *,
    include_fulltext: bool = False,
    delay: float = 0.1
) -> dict:
    """
    Retrieve detailed metadata (title, abstract, keywords, etc.) for an article.
    """
    source, id_ = _resolve_source_and_id(item_or_dict, delay=delay)
    if not source or not id_:
        return {}

    cache_key = (source, str(id_), bool(include_fulltext))
    cached = _DETAIL_CACHE.get(cache_key)
    if cached is not None:
        return dict(cached)

    params = {"format": "json"}
    if include_fulltext:
        params["resultType"] = "core"

    try:
        resp = requests.get(f"{EPMC_BASE}/{source}/{id_}", params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json() or {}
    except requests.RequestException:
        return {}

    # Some responses nest the result under "result".
    result = payload.get("result") if isinstance(payload, Mapping) else None
    if not result and isinstance(payload, Mapping):
        result = payload

    if not isinstance(result, Mapping):
        result = {}

    # Normalize structured abstract if present.
    structured = result.get("structuredAbstract")
    if structured and not result.get("abstractText"):
        result["abstractText"] = _coerce_structured_abstract(structured)

    _DETAIL_CACHE[cache_key] = dict(result)
    return dict(result)

def _element_to_plaintext(node: ET.Element | None) -> Optional[str]:
    if node is None:
        return None
    pieces: list[str] = []
    for chunk in node.itertext():
        if chunk and chunk.strip():
            pieces.append(chunk.strip())
    if not pieces:
        return None
    return re.sub(r"\s+", " ", " ".join(pieces)).strip()

def _collect_abstract_from_root(root: ET.Element) -> Optional[str]:
    abstract_texts: list[str] = []
    # Common placements for abstracts in JATS/PMC XML
    abstract_paths = [
        ".//{*}abstract",
        ".//{*}sec[@sec-type='abstract']",
        ".//{*}sec[@sec-type='summary']",
    ]
    for path in abstract_paths:
        for node in root.findall(path):
            text_val = _element_to_plaintext(node)
            if text_val:
                abstract_texts.append(text_val)

    if not abstract_texts:
        return None

    seen: set[str] = set()
    ordered: list[str] = []
    for text_val in abstract_texts:
        if text_val not in seen:
            seen.add(text_val)
            ordered.append(text_val)
    return "\n\n".join(ordered) if ordered else None

def _parse_fulltext_xml(xml_text: str | None) -> tuple[Optional[str], Optional[str]]:
    if not xml_text:
        return None, None
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None, None
    full_text = _element_to_plaintext(root)
    abstract_text = _collect_abstract_from_root(root)
    return full_text, abstract_text

def fetch_epmc_full_text(
    item_or_dict: ResolvedInput,
    *,
    delay: float = 0.1,
    include_xml: bool = True,
) -> dict[str, Optional[str]]:
    """
    Retrieve full-text XML (if available) and extract plain-text plus abstract snippets.
    Europe PMC exposes full text via PMCID-specific endpoints, so we need a PMCID to succeed.
    Returns a dict containing "text", "abstract", and (optionally) "xml". When full text XML is
    unavailable, attempts to recover the abstract via search/metadata endpoints.
    """

    def _add_candidate(value: Any, collector: list[str]) -> None:
        pmcid_norm = _normalize_pmcid(value)
        if pmcid_norm and pmcid_norm not in collector:
            collector.append(pmcid_norm)

    pmcid_candidates: list[str] = []
    fallback_abs: Optional[str] = None
    search_source: Optional[str] = None
    search_identifier: Optional[str] = None

    if isinstance(item_or_dict, Mapping):
        for key in ("PMCID", "pmcid", "PMC", "pmc"):
            _add_candidate(item_or_dict.get(key), pmcid_candidates)
        fallback_abs = (
            item_or_dict.get("abstract_text")
            or item_or_dict.get("abstractText")
            or item_or_dict.get("abstract")
        )
        source_hint = item_or_dict.get("source")
        if isinstance(source_hint, str) and source_hint:
            search_source = source_hint.upper()

        if item_or_dict.get("PMCID"):
            search_identifier = str(item_or_dict["PMCID"])
        elif item_or_dict.get("PMID"):
            search_identifier = str(item_or_dict["PMID"])
        elif item_or_dict.get("DOI"):
            search_identifier = str(item_or_dict["DOI"])
    else:
        _add_candidate(item_or_dict, pmcid_candidates)

    resolved_source, resolved_id = _resolve_source_and_id(item_or_dict, delay=delay)
    if resolved_source == "PMC":
        _add_candidate(resolved_id, pmcid_candidates)
    if resolved_source and resolved_id and not search_identifier:
        search_source = resolved_source.upper()
        search_identifier = str(resolved_id)

    if not pmcid_candidates:
        lookup_values: list[Any] = []
        if isinstance(item_or_dict, Mapping):
            for key in ("PMID", "pmid", "DOI", "doi", "title"):
                val = item_or_dict.get(key)
                if val:
                    lookup_values.append(val)
        else:
            lookup_values.append(item_or_dict)

        for candidate in lookup_values:
            meta = _fetch_epmc_metadata(str(candidate), delay=delay)
            _add_candidate(meta.get("PMCID"), pmcid_candidates)
            if not fallback_abs and isinstance(meta.get("abstract_text"), str):
                fallback_abs = meta["abstract_text"]
            if meta.get("PMCID"):
                search_source, search_identifier = "PMC", str(meta["PMCID"])
            elif meta.get("PMID"):
                search_source, search_identifier = "MED", str(meta["PMID"])
            elif meta.get("DOI"):
                search_source, search_identifier = "DOI", str(meta["DOI"])
            elif meta.get("source"):
                source_val = meta.get("source")
                if isinstance(source_val, str) and source_val:
                    search_source = source_val.upper()
            if pmcid_candidates:
                break

    if not pmcid_candidates:
        result = {"xml": None, "text": None, "abstract": None}
        if isinstance(fallback_abs, str) and fallback_abs.strip():
            result["abstract"] = fallback_abs.strip()
        elif search_source and search_identifier:
            alt_abs = _fetch_epmc_search_abstract(str(search_source), str(search_identifier), delay=delay)
            if alt_abs:
                result["abstract"] = alt_abs
        if not include_xml:
            result.pop("xml", None)
        return result

    payload: dict[str, Optional[str]] | None = None
    last_cache_key: Optional[str] = None

    for pmcid in pmcid_candidates:
        cache_key = pmcid
        cached = _FULLTEXT_CACHE.get(cache_key)
        if cached is not None:
            current = dict(cached)
            if "abstract" not in current or (current.get("text") is None and current.get("xml")):
                text_blob, abstract_blob = _parse_fulltext_xml(current.get("xml"))
                if current.get("text") is None:
                    current["text"] = text_blob
                if current.get("abstract") is None:
                    current["abstract"] = abstract_blob
                _FULLTEXT_CACHE[cache_key] = dict(current)
        else:
            url = f"{EPMC_BASE}/{pmcid}/fullTextXML"
            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                xml_blob = resp.text or None
            except requests.RequestException:
                xml_blob = None

            text_blob, abstract_blob = _parse_fulltext_xml(xml_blob)
            current = {"xml": xml_blob, "text": text_blob, "abstract": abstract_blob}
            _FULLTEXT_CACHE[cache_key] = dict(current)
            time.sleep(max(0.0, delay))

        payload = current
        last_cache_key = cache_key
        if payload.get("xml") or payload.get("text") or payload.get("abstract"):
            break

    if payload is None:
        payload = {"xml": None, "text": None, "abstract": None}

    result = dict(payload)

    if not result.get("abstract"):
        if isinstance(fallback_abs, str) and fallback_abs.strip():
            result["abstract"] = fallback_abs.strip()
        elif search_source and search_identifier:
            alt_abs = _fetch_epmc_search_abstract(str(search_source), str(search_identifier), delay=delay)
            if alt_abs:
                result["abstract"] = alt_abs

    if last_cache_key:
        _FULLTEXT_CACHE[last_cache_key] = dict(result)

    if not include_xml:
        result.pop("xml", None)
    return result

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
def _fetch_epmc_metadata(item: str, delay: float = 0.1) -> dict:
    """
    Internal helper to query Europe PMC by DOI, PMID, PMCID, or title.
    Returns core bibliographic metadata without fetching full text.
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
    abstract = hit.get("abstractText")
    source = hit.get("source")

    out = {
        "PMC": _pmc_numeric(pmcid),
        "DOI": doi,
        "PMID": pmid,
        "PMCID": pmcid,
        "title": title if title else (item if kind == "title" else None),
        "journal": journal,
        "year": int(year) if year and str(year).isdigit() else year,
        "source_url": _source_url_from_ids(pmcid, pmid, doi),
        "source": source,
    }

    if isinstance(abstract, str) and abstract.strip():
        out["abstract_text"] = abstract.strip()

    time.sleep(max(0.0, delay))
    return out

def fetch_epmc(
    item: str,
    delay: float = 0.1,
    *,
    include_full_text: bool = True,
    include_xml: bool = False,
) -> dict:
    """
    Query Europe PMC and return bibliographic metadata along with optional full text.

    Args:
        item: DOI, PMID, PMCID, or title string.
        delay: Courtesy delay applied to network calls.
        include_full_text: If True (default), fetch plain-text/XML full text immediately.
        include_xml: When include_full_text is True, include raw XML alongside parsed text.

    Returns:
        Dict of bibliographic fields plus:
            - full_text: plain-text body (if available)
            - full_text_abstract: abstract extracted from XML (if available)
            - full_text_xml: raw XML (only when include_xml=True)
            - abstract_text: abstract retrieved via XML, metadata, or search fallback
    """
    print("Fetching EPMC metadata for:", item)
    meta = _fetch_epmc_metadata(item, delay=delay)

    def _ensure_abstract(target: dict[str, Any]) -> None:
        if target.get("abstract_text"):
            return
        source, identifier = _resolve_source_and_id(target, delay=delay)
        if source and identifier:
            abstract = _fetch_epmc_search_abstract(str(source), str(identifier), delay=delay)
            if abstract:
                target["abstract_text"] = abstract
                return
        detail = fetch_epmc_article_details(target, include_fulltext=False, delay=delay)
        if isinstance(detail, Mapping):
            detail_abstract = detail.get("abstractText")
            if isinstance(detail_abstract, str) and detail_abstract.strip():
                target["abstract_text"] = detail_abstract.strip()

    if not include_full_text:
        _ensure_abstract(meta)
        return meta

    payload = fetch_epmc_full_text(meta, delay=delay, include_xml=include_xml)
    meta["full_text"] = payload.get("text")
    meta["full_text_abstract"] = payload.get("abstract")
    if include_xml:
        meta["full_text_xml"] = payload.get("xml")
    elif "full_text_xml" in meta:
        meta.pop("full_text_xml", None)

    if payload.get("abstract") and not meta.get("abstract_text"):
        meta["abstract_text"] = payload["abstract"]
    _ensure_abstract(meta)

    return meta

def fetch_epmc_batch(
    items: Iterable[str],
    delay: float = 0.1,
    *,
    include_full_text: bool = True,
    include_xml: bool = False,
) -> list[dict]:
    """
    Batch wrapper for fetch_epmc.
    """
    return [
        fetch_epmc(
            it,
            delay=delay,
            include_full_text=include_full_text,
            include_xml=include_xml,
        )
        for it in items
    ]

ResolvedInput = str | Mapping[str, Any]

def _resolve_source_and_id(inp: ResolvedInput, delay: float = 0.1) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve to a Europe PMC (source, id):
      - If a dict (output of fetch_epmc), prefer PMID (MED) then PMCID (PMC).
      - If a string, call fetch_epmc on it.
      - If dict lacks PMID/PMCID but has DOI/title, try a second-pass resolve using those.
    Returns (source, id) or (None, None).
    """
    # Case 1: already a dict (json_id-like)
    if isinstance(inp, Mapping):
        pmid  = inp.get("PMID")
        pmcid = inp.get("PMCID")
        if pmid:
            return "MED", str(pmid)
        if pmcid:
            return "PMC", str(pmcid)
        # Fallback via DOI or title if provided
        fallback_key = inp.get("DOI") or inp.get("title")
        if fallback_key:
            resolved = _fetch_epmc_metadata(str(fallback_key), delay=delay)
            if resolved.get("PMID"):
                return "MED", str(resolved["PMID"])
            if resolved.get("PMCID"):
                return "PMC", str(resolved["PMCID"])
        return None, None

    # Case 2: raw string
    meta = _fetch_epmc_metadata(inp, delay=delay)
    if meta.get("PMID"):
        return "MED", str(meta["PMID"])
    if meta.get("PMCID"):
        return "PMC", str(meta["PMCID"])
    return None, None


def list_references_epmc(item_or_dict: ResolvedInput, page_size: int = 100, delay: float = 0.05) -> pd.DataFrame:
    """
    List all papers that THIS paper CITES.
    Accepts:
      - DOI/PMID/PMCID/title string, or
      - dict from fetch_epmc(...)
    Returns DataFrame: PMID, PMCID, DOI, title, journal, year, source_url
    """
    source, id_ = _resolve_source_and_id(item_or_dict, delay=delay)
    if not source or not id_:
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


def list_citations_epmc(item_or_dict: ResolvedInput, page_size: int = 100, delay: float = 0.05) -> pd.DataFrame:
    """
    List all papers that CITE THIS paper.
    Accepts:
      - DOI/PMID/PMCID/title string, or
      - dict from fetch_epmc(...)
    Returns DataFrame: PMID, PMCID, DOI, title, journal, year, source_url
    """
    source, id_ = _resolve_source_and_id(item_or_dict, delay=delay)
    if not source or not id_:
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


def save_dataframe_rows_as_json(
    df: pd.DataFrame,
    directory: str | Path,
    *,
    id_column: str = "PMID",
    filename_prefix: str = "",
    indent: int = 2,
    drop_missing: bool = False,
) -> list[Path]:
    """
    Persist each row of a DataFrame as an individual JSON file.

    Args:
        df: DataFrame to export.
        directory: Folder where JSON files should be written.
        id_column: Column used to derive the identifier portion of the filename.
        filename_prefix: Optional string prefixed to each filename.
        indent: JSON indentation level.
        drop_missing: If True, omit keys with null/NA values from the output.

    Returns:
        list[pathlib.Path]: Paths to the files that were written.
    """
    if df is None or df.empty:
        return []

    target_dir = Path(directory)
    target_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[Path] = []
    for idx, row in df.reset_index(drop=True).iterrows():
        identifier: Optional[str] = None
        if id_column and id_column in row and pd.notna(row[id_column]):
            identifier = str(row[id_column]).strip()
        if not identifier:
            identifier = f"row{idx:04d}"

        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", identifier)
        if filename_prefix:
            safe_name = f"{filename_prefix}{safe_name}"

        filepath = target_dir / f"{safe_name}.json"

        payload = {
            str(col): _json_safe(val)
            for col, val in row.items()
        }
        if drop_missing:
            payload = {k: v for k, v in payload.items() if v is not None}

        # json.dump already defaults to ASCII-only output, which keeps filenames portable.
        with filepath.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=indent)

        saved_paths.append(filepath)

    return saved_paths


def _standardize_meta(meta_like: Mapping[str, Any]) -> dict:
    """
    Coerce varied Europe PMC payloads (JSON dicts or DataFrame rows) into a uniform dict.
    """
    def _clean(value: Any) -> Any:
        if value is None:
            return None
        # Handle pandas NA/NaN values gracefully
        try:
            if pd.isna(value):
                return None
        except Exception:
            pass
        return value

    pmcid = _clean(meta_like.get("PMCID") or meta_like.get("pmcid"))
    pmid = _clean(meta_like.get("PMID") or meta_like.get("pmid"))
    doi = _clean(meta_like.get("DOI") or meta_like.get("doi"))
    title = _clean(meta_like.get("title"))
    journal = _clean(meta_like.get("journal") or meta_like.get("journalTitle"))
    year = _clean(meta_like.get("year") or meta_like.get("pubYear"))
    source_url = _clean(meta_like.get("source_url"))

    if isinstance(year, (int, float)) and not isinstance(year, bool):
        if float(year).is_integer():
            year = int(year)
    elif isinstance(year, str) and year.isdigit():
        year = int(year)

    return {
        "PMC": _pmc_numeric(pmcid) if pmcid else None,
        "PMID": str(pmid) if pmid is not None else None,
        "PMCID": str(pmcid) if pmcid is not None else None,
        "DOI": str(doi) if doi is not None else None,
        "title": title,
        "journal": journal,
        "year": year,
        "source_url": source_url,
    }


def _make_node_key(meta: Mapping[str, Any]) -> str:
    """
    Generate a stable key for a paper using available identifiers.
    """
    parts: list[str] = []
    for field in ("PMID", "PMCID", "DOI"):
        value = meta.get(field)
        if value:
            parts.append(str(value).strip().lower())

    title = meta.get("title")
    if title and not parts:
        parts.append(re.sub(r"\s+", " ", str(title)).strip().lower())

    source_url = meta.get("source_url")
    if source_url and not parts:
        parts.append(str(source_url).strip().lower())

    if parts:
        return "|".join(parts)

    # Last resort: stable hash of sorted items
    digest = hashlib.sha1(repr(sorted(meta.items())).encode("utf-8", "ignore")).hexdigest()
    return f"anon:{digest}"


def expand_literature_network_epmc(
    seeds: Iterable[ResolvedInput] | ResolvedInput,
    *,
    max_depth: int = 1,
    include: Iterable[str] | None = None,
    delay: float = 0.05
) -> pd.DataFrame:
    """
    Explore references and/or citations starting from one or more seed papers.

    Args:
        seeds: A single seed (string or fetch_epmc dict) or an iterable of seeds.
        max_depth: How many hops to follow beyond the seeds (depth 0 = seeds).
            max_depth=1 collects direct references/citations; >1 continues breadth-first.
        include: Iterable subset of {"references", "citations"} to control which edges to follow.
        delay: Courtesy sleep between API calls.

    Returns:
        pandas.DataFrame with one row per unique paper encountered. Columns include
        Europe PMC identifiers plus:
            - node_key: internal stable key
            - depth: minimum hop count from any seed
            - relations: semicolon-joined labels ("seed", "reference", "citation")
            - parent_keys: semicolon-joined parent node keys (if any)
            - n_parents: count of distinct parents
    """
    if isinstance(seeds, (str, Mapping)):
        seed_items = [seeds]
    else:
        seed_items = list(seeds)

    if not seed_items:
        return pd.DataFrame(columns=[
            "node_key","depth","relations","n_parents","parent_keys",
            "PMC","PMID","PMCID","DOI","title","journal","year","source_url"
        ])

    include_set = {"references", "citations"}
    if include is not None:
        include_filtered = {opt.lower() for opt in include if opt and isinstance(opt, str)}
        include_set &= include_filtered
        if not include_set:
            # Nothing to expand, just return seed metadata
            include_set = set()

    max_depth = max(0, int(max_depth))

    nodes: dict[str, dict[str, Any]] = {}

    def register(meta_like: Mapping[str, Any], relation: str, depth: int, parent_key: Optional[str]) -> tuple[str, dict[str, Any]]:
        base_meta = _standardize_meta(meta_like)
        node_key = _make_node_key(base_meta)
        node = nodes.get(node_key)
        if node is None:
            node = dict(base_meta)
            node["node_key"] = node_key
            node["depth"] = depth
            node["relations"] = {relation}
            node["parent_keys"] = set([parent_key] if parent_key else [])
            nodes[node_key] = node
        else:
            node["depth"] = min(node["depth"], depth)
            node["relations"].add(relation)
            if parent_key:
                node["parent_keys"].add(parent_key)
        return node_key, node

    queue: deque[tuple[str, dict[str, Any]]] = deque()
    queued_depth: dict[str, int] = {}

    for seed in seed_items:
        if isinstance(seed, Mapping):
            seed_meta = seed
        else:
            seed_meta = fetch_epmc(str(seed), delay=delay, include_full_text=False)
        key, node = register(seed_meta, "seed", 0, None)
        if max_depth > 0:
            queue.append((key, node))
            queued_depth[key] = 0

    while queue:
        current_key, current_node = queue.popleft()
        current_depth = current_node.get("depth", 0)
        if current_depth >= max_depth:
            continue

        if "references" in include_set:
            refs_df = list_references_epmc(current_node, delay=delay)
            for _, row in refs_df.iterrows():
                ref_dict = row.to_dict()
                child_key, child_node = register(ref_dict, "reference", current_depth + 1, current_key)
                if (current_depth + 1) < max_depth:
                    prior_depth = queued_depth.get(child_key)
                    if prior_depth is None or prior_depth > current_depth + 1:
                        queue.append((child_key, child_node))
                        queued_depth[child_key] = current_depth + 1

        if "citations" in include_set:
            cites_df = list_citations_epmc(current_node, delay=delay)
            for _, row in cites_df.iterrows():
                cite_dict = row.to_dict()
                child_key, child_node = register(cite_dict, "citation", current_depth + 1, current_key)
                if (current_depth + 1) < max_depth:
                    prior_depth = queued_depth.get(child_key)
                    if prior_depth is None or prior_depth > current_depth + 1:
                        queue.append((child_key, child_node))
                        queued_depth[child_key] = current_depth + 1

    records: list[dict[str, Any]] = []
    for node in nodes.values():
        rec = dict(node)
        relations = sorted(rec.pop("relations", []))
        parents = sorted(pk for pk in rec.pop("parent_keys", set()) if pk)
        rec["relations"] = ";".join(relations) if relations else None
        rec["parent_keys"] = ";".join(parents) if parents else None
        rec["n_parents"] = len(parents)
        records.append(rec)

    df = pd.DataFrame.from_records(records)
    if not df.empty:
        df = df.sort_values(["depth", "title"], na_position="last").reset_index(drop=True)

    return df[[
        "node_key","depth","relations","n_parents","parent_keys",
        "PMC","PMID","PMCID","DOI","title","journal","year","source_url"
    ]]
