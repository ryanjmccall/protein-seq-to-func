import json
import os
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, Iterable, Optional, Set

import httpx


class EuropePMCHarvester:
    """
    Lightweight Europe PMC harvester focused on Open Access full text retrieval.

    The class wraps the original `/harvest/apoe` spike logic so it can be reused
    for arbitrary genes without duplicating the heavy inline function body inside
    the FastAPI route definition.
    """

    def __init__(
        self,
        search_url: str,
        fulltext_base_url: str,
        output_dir: str,
        *,
        timeout_secs: int = 60,
        save_xml: bool = True,
    ) -> None:
        self.search_url = search_url
        self.fulltext_base_url = fulltext_base_url.rstrip("/")
        self.output_dir = output_dir
        self.timeout_secs = timeout_secs
        self.save_xml = save_xml

    def harvest_gene(
        self,
        gene: str,
        *,
        page_size: int = 1000,
        max_harvest: int = 1000,
        include_synonyms: bool = True,
        restrict_to_human: bool = True,
        oa_only: bool = True,
    ) -> Dict[str, Any]:
        """
        Harvest Open Access Europe PMC articles that mention `gene`.

        Parameters mirror the previous hard-coded spike defaults but can now be
        supplied by the caller. Returns the same compact payload the FastAPI
        route used to emit.
        """
        gene = (gene or "").strip()
        if not gene:
            raise ValueError("gene must be a non-empty string")

        os.makedirs(self.output_dir, exist_ok=True)

        base_query = self._build_query(
            gene,
            oa_only=oa_only,
            restrict_to_human=restrict_to_human,
        )

        cursor_mark = "*"
        harvested = 0
        seen_ids: Set[str] = set()

        with httpx.Client(timeout=self.timeout_secs) as client:
            while True:
                params = {
                    "query": base_query,
                    "format": "json",
                    "resultType": "core",
                    "pageSize": str(page_size),
                    "cursorMark": cursor_mark,
                    "synonym": "Y" if include_synonyms else "N",
                    "sort": "CITED desc",
                }

                print(f"[HARVEST][SEARCH] GET {self.search_url} q={params['query']} cursor={cursor_mark}")
                response = client.get(self.search_url, params=params)
                response.raise_for_status()

                data = response.json()
                try:
                    print(f"[HARVEST][DEBUG] hitCount={data.get('hitCount', 0)}")
                except Exception:
                    pass

                results = (data.get("resultList") or {}).get("result") or []
                print(f"[HARVEST][SEARCH] hits={len(results)}")
                next_cursor = data.get("nextCursorMark")

                if not results:
                    self._log_empty_page(data)
                    break

                harvested = self._process_results(
                    results,
                    gene,
                    client,
                    seen_ids,
                    harvested,
                    max_harvest,
                )

                if harvested >= max_harvest:
                    print(f"[HARVEST] Reached MAX_HARVEST={max_harvest}. Stopping.")
                    return {"status": "ok", "harvested": harvested, "note": "max cap reached"}

                if not next_cursor or next_cursor == cursor_mark:
                    break

                cursor_mark = next_cursor

        print(f"[HARVEST] Done. harvested={harvested}")
        return {"status": "ok", "harvested": harvested}

    def _process_results(
        self,
        results: Iterable[dict],
        gene: str,
        client: httpx.Client,
        seen_ids: Set[str],
        harvested: int,
        max_harvest: int,
    ) -> int:
        for rec in results:
            rid = rec.get("pmcid") or rec.get("id") or rec.get("pmid") or rec.get("doi")
            if not rid or rid in seen_ids:
                continue
            seen_ids.add(rid)

            pmcid = (rec.get("pmcid") or "").strip()
            if not pmcid:
                continue

            obj = self._build_payload(rec, pmcid, gene, client)
            out_path = os.path.join(self.output_dir, f"{pmcid}.json")
            try:
                with open(out_path, "w", encoding="utf-8") as handle:
                    json.dump(obj, handle, ensure_ascii=False, indent=2)
                harvested += 1
            except Exception as exc:
                print(f"[HARVEST][error] write {out_path}: {exc}")

            if harvested >= max_harvest:
                return harvested

        return harvested

    def _build_payload(
        self,
        rec: dict,
        pmcid: str,
        gene: str,
        client: httpx.Client,
    ) -> Dict[str, Any]:
        doi = (rec.get("doi") or "").strip()
        title = (rec.get("title") or "").strip()
        year_raw = rec.get("pubYear")
        try:
            year = int(year_raw or 0)
        except ValueError:
            year = 0
        journal = (rec.get("journalTitle") or "").strip()

        source_url = f"https://europepmc.org/article/pmcid/{pmcid}"
        obj: Dict[str, Any] = {
            "pmcid": pmcid,
            "doi": doi,
            "title": title,
            "year": year,
            "journal": journal,
            "protein_hits": [gene],
            "xml": "",
            "plain_text": "",
            "source_url": source_url,
        }

        full_url = f"{self.fulltext_base_url}/{pmcid}/fullTextXML"
        print(f"[HARVEST][XML] GET {full_url}")

        xml_text = ""
        try:
            xml_resp = client.get(full_url)
            if xml_resp.status_code == 200:
                xml_text = xml_resp.text or ""
            else:
                print(f"[HARVEST][warn] fullTextXML {pmcid} -> HTTP {xml_resp.status_code}")
        except Exception as exc:
            print(f"[HARVEST][warn] XML fetch failed {pmcid}: {exc}")

        if xml_text:
            plain = self._jats_body_to_text(xml_text)
        else:
            abstr = (rec.get("abstractText") or "").strip()
            plain = self._normalize_ws(f"{title}. {abstr}")

        obj["xml"] = xml_text if self.save_xml else ""
        obj["plain_text"] = plain

        return obj

    @classmethod
    def _build_query(
        cls,
        gene: str,
        *,
        oa_only: bool,
        restrict_to_human: bool,
    ) -> str:
        gene_term = cls._escape_query_term(gene)
        clauses = [f'(TEXT:"{gene_term}")']
        if oa_only:
            clauses.append("OPEN_ACCESS:Y")
        if restrict_to_human:
            clauses.append("(TAXON_ID:9606 OR ORGANISM:\"Homo sapiens\")")
        return " AND ".join(clauses)

    @staticmethod
    def _escape_query_term(term: str) -> str:
        return term.replace('"', '\\"')

    @staticmethod
    def _log_empty_page(data: dict) -> None:
        try:
            print("[HARVEST][debug] Empty page. Response keys:", list(data.keys()))
            preview = str(data)
            if len(preview) > 1200:
                preview = preview[:1200] + "…"
            print("[HARVEST][debug] Payload preview:", preview)
        except Exception:
            pass

    @staticmethod
    def _normalize_ws(value: str) -> str:
        return re.sub(r"\s+", " ", (value or "")).strip()

    @classmethod
    def _jats_body_to_text(cls, xml_text: str) -> str:
        try:
            root = ET.fromstring(xml_text)
        except Exception:
            return cls._normalize_ws(xml_text)

        def _remove_all(tag_local: str) -> None:
            for element in list(root.iter()):
                if isinstance(element.tag, str) and element.tag.endswith(tag_local) and element is not root:
                    parent = cls._parent_of(root, element)
                    if parent is not None:
                        parent.remove(element)

        for tag in ("ref-list", "table-wrap", "fig", "supplementary-material"):
            _remove_all(tag)

        target = None
        for element in root.iter():
            if isinstance(element.tag, str) and element.tag.endswith("body"):
                target = element
                break

        if target is None:
            target = root

        texts = list(target.itertext())
        return cls._normalize_ws(" ".join(texts))

    @staticmethod
    def _parent_of(root: ET.Element, node: ET.Element) -> Optional[ET.Element]:
        for candidate in root.iter():
            for child in list(candidate):
                if child is node:
                    return candidate
        return None
