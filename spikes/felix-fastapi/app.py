import httpx
import os, json
from fastapi import FastAPI, HTTPException
from pydantic_settings import BaseSettings
from typing import List, Optional, Dict, Any
from llama_index.core import Document, Settings, VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding  # OpenAI-compatible; works with Nebius base_url
#from llama_index.embeddings.nebius import NebiusEmbedding
from llama_index.core.base.embeddings.base import BaseEmbedding
from openai import OpenAI
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb


class Settings(BaseSettings):
    nebius_api_key: str
    
    class Config:
        env_file = ".env"

settings = Settings()

class NebiusStudioEmbedding(BaseEmbedding):
    """Nebius AI Studio embeddings via OpenAI-compatible client.
    Akzeptiert Nebius-Modelle wie 'Qwen3-Embedding-8B', 'BGE-ICL', etc.
    """
    def __init__(self, api_key: str, base_url: str, model: str):
        super().__init__()
        self.client = OpenAI(api_key=api_key, base_url=base_url)  # base_url sollte auf /v1/ enden
        self.model = model

    # --- sync: text ---
    def _get_text_embedding(self, text: str) -> List[float]:
        r = self.client.embeddings.create(model=self.model, input=text)
        return r.data[0].embedding

    def _get_text_embedding_batch(self, texts: List[str]) -> List[List[float]]:
        r = self.client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in r.data]

    # --- sync: query -> delegiert auf text ---
    def _get_query_embedding(self, query: str) -> List[float]:
        return self._get_text_embedding(query)

    def _get_query_embedding_batch(self, queries: List[str]) -> List[List[float]]:
        return self._get_text_embedding_batch(queries)

    # --- async: delegiert auf die sync-Methoden ---
    async def _aget_text_embedding(self, text: str) -> List[float]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_text_embedding, text)

    async def _aget_text_embedding_batch(self, texts: List[str]) -> List[List[float]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_text_embedding_batch, texts)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return await self._aget_text_embedding(query)

    async def _aget_query_embedding_batch(self, queries: List[str]) -> List[List[float]]:
        return await self._aget_text_embedding_batch(queries)

app = FastAPI(title="Felix Spike", version="0.0.1")

# ------- Public, non-secret config (hard-coded) -------
PAPERS_DIR = "papers"
CHROMA_PATH = "./chroma_db"            # local on-disk store
CHROMA_COLLECTION = "longevity_s2f"    # name of the vector collection
# Configure a single, global splitter. We do not enable embeddings here.
# chunk_size ~800 tokens with ~120 overlap is a common default for scientific text.
#SPLITTER = SentenceSplitter(chunk_size=800, chunk_overlap=120)
# OpenAI-compatible base URL from Nebius Quickstart (documented).
# We keep this constant in code (not secret).
NEBIUS_BASE_URL = "https://api.studio.nebius.com/v1"  # docs: /v1/chat/completions
NEBIUS_MODEL = "openai/gpt-oss-120b"  # inexpensive, open-source model suitable for tests
NEBIUS_EMBED_MODEL = "Qwen3-Embedding-8B"
#NEBIUS_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct-fast"

os.environ["OPENAI_API_KEY"] = settings.nebius_api_key
os.environ["OPENAI_BASE_URL"] = NEBIUS_BASE_URL

@app.get("/nebius-hello")
def nebius_hello():
    """
    Tiny test against Nebius Chat Completions.
    - Reads ONLY the API key from .env (no other secrets).
    - Sends a very short prompt.
    - Prints raw response to the server terminal for inspection.
    - Returns only {"status": "ok"} to the client (no extra payload).
    """
    api_key = settings.nebius_api_key

    url = f"{NEBIUS_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Short, harmless test prompt (no internet access assumed).
    prompt = (
        "Return a JSON object with fields 'name', 'url', 'notes' for 3 public databases "
        "that provide free APIs for human proteins that are related to longevity. No markdown, JSON only."
    )

    # Payload follows Nebius' OpenAI-compatible schema (messages[], model, etc.).
    # Reference: Nebius Quickstart /v1/chat/completions. :contentReference[oaicite:1]{index=1}
    payload = {
        "model": NEBIUS_MODEL,
        "messages": [
            {"role": "system", "content": "You are a concise scientific assistant."},
            {"role": "user", "content": prompt}
        ],
        
        "max_tokens": 500,
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }

    print("[Nebius HELLO] POST", url, "model=", NEBIUS_MODEL)
    with httpx.Client(timeout=60) as client:
        resp = client.post(url, json=payload, headers=headers)

    print("[Nebius HELLO] HTTP:", resp.status_code)
    try:
        data = resp.json()
        print("[Nebius HELLO] JSON:", data)  # full raw JSON from Nebius
        
        # Extract and parse the JSON response from the model
        if "choices" in data and len(data["choices"]) > 0:
            msg = data["choices"][0]["message"]["content"]
            print("[Nebius HELLO] Model response:", msg)
            
            # Try to parse the JSON response from the model
            import json
            try:
                parsed_response = json.loads(msg)
                print("[Nebius HELLO] Parsed JSON:", parsed_response)
            except json.JSONDecodeError as e:
                print("[Nebius HELLO] JSON parse error:", e)
                
    except Exception:
        print("[Nebius HELLO] TEXT:", resp.text[:1000])

    
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}


# --- Europe PMC spike endpoints ---
# NOTE: Hard-coded protein/ID for first smoke tests. We'll parameterize later.

EPMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EPMC_FULLTEXT_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"

@app.get("/europepmc-search")
def europepmc_search():
    """
    Smoke-test Europe PMC SEARCH for a single protein, Open Access only.
    - Hard-coded 'PROTEIN' for now (no query params).
    - Prints a compact table to server terminal so you can inspect results.
    - Returns only {"status":"ok"} to the client.
    """
    PROTEIN = "SIRT6"  # <-- change this to the protein you want to test

    # Build a conservative, high-recall query:
    # - OPEN_ACCESS:Y restricts to OA
    # - synonym=Y lets Europe PMC expand common gene synonyms
    params = {
        "query": f'(TEXT:"{PROTEIN}") AND OPEN_ACCESS:Y',
        "resultType": "core",     # return the standard metadata fields (title, abstract, authors, IDs, OA flag, etc.)
        "format": "json",         # response format: could also be 'xml', but JSON is easiest for Python
        "pageSize": "25",         # number of results per page (max 1000)
        "sort": "CITED desc",     # sort by number of citations, descending (most cited papers first)
        "synonym": "Y",           # expand gene/protein synonyms automatically (Europe PMC has a built-in synonym dictionary)
    }

    print(f"[EPMC SEARCH] GET {EPMC_SEARCH_URL} q={params['query']}")
    with httpx.Client(timeout=60) as client:
        r = client.get(EPMC_SEARCH_URL, params=params)
    print("[EPMC SEARCH] HTTP:", r.status_code)

    try:
        data = r.json()
    except Exception:
        print("[EPMC SEARCH] Non-JSON response head:", r.text[:500])
        return {"status": "ok"}

    results = (data.get("resultList") or {}).get("result") or []
    print(f"[EPMC SEARCH] hits={len(results)}  (showing up to 10)")
    for i, rec in enumerate(results[:10], start=1):
        title = rec.get("title") or ""
        year = rec.get("pubYear")
        doi = rec.get("doi")
        pmcid = rec.get("pmcid")
        pmid = rec.get("pmid")
        is_oa = rec.get("isOpenAccess")
        journal = rec.get("journalTitle")
        print(f"  {i:02d}. {year} | OA={is_oa} | DOI={doi} | PMCID={pmcid} | PMID={pmid} | {journal}")
        print(f"      {title}")

    # Tip for your next manual step:
    # - Pick one PMCID from the list above and paste it into the fulltext endpoint below.
    return {"status": "ok"}


@app.get("/europe-pmc-fulltext-xml")
def europe_pmc_fulltext_xml():
    """
    Smoke-test Europe PMC FULLTEXT (XML) download for a single OA article.
    - Hard-coded 'EPMC_ID' (e.g., 'PMC1234567') for now.
    - Prints a short header + first 1000 chars of XML to the terminal for inspection.
    - Returns only {"status":"ok"} to the client.
    """
    EPMC_ID = "PMC3439153"  # <-- replace with a real PMCID from the search above, e.g. 'PMC1234567'
    if EPMC_ID == "PMC0000000":
        print("[EPMC FULLTEXT] Please set EPMC_ID to a real PMCID (e.g., 'PMC1234567').")
        return {"status": "ok"}

    url = f"{EPMC_FULLTEXT_BASE}/{EPMC_ID}/fullTextXML"
    print(f"[EPMC FULLTEXT] GET {url}")
    with httpx.Client(timeout=60) as client:
        r = client.get(url)
    print("[EPMC FULLTEXT] HTTP:", r.status_code)

    if r.status_code != 200:
        print("[EPMC FULLTEXT] Response head:", r.text[:500])
        return {"status": "ok"}

    xml_text = r.text or ""
    # Lightweight visibility: show total size + snippet so you can see structure (JATS tags).
    print(f"[EPMC FULLTEXT] XML bytes: {len(xml_text.encode('utf-8'))}")
    print("[EPMC FULLTEXT] XML snippet (first 1000 chars):")
    print(xml_text[:10000])

    # (Later) You'll parse JATS here: drop <ref-list>, keep body <sec> text, create clean chunks.
    return {"status": "ok"}


@app.post("/index/batch")
def index_batch(limit: int = 200, offset: int = 0):
# call e.g.: POST http://localhost:8000/index/batch?limit=300&offset=600

    """
    One-step indexing:
    - Load ALL JSON files from 'papers/' (no filtering), sliced by offset/limit.
    - Convert to LlamaIndex Documents.
    - Split into ~800-token chunks (with overlap).
    - Create embeddings via Nebius (OpenAI-compatible).
    - Persist vectors+metadata into a local Chroma DB.
    Prints detailed stats to the terminal; returns only {"status": "ok"}.
    """

    # --- Read secret key from your existing Pydantic Settings (you already have this in your file) ---
    api_key = settings.nebius_api_key

    # --- Gather JSON files (no filtering) ---
    # We slice by offset/limit so you can index in small, safe batches and keep RAM steady.
    if not os.path.isdir(PAPERS_DIR):
        print(f"[INDEX] Folder '{PAPERS_DIR}' does not exist. Create it and drop JSON files inside.")
        return {"status": "ok"}

    all_files = [os.path.join(PAPERS_DIR, fn) for fn in os.listdir(PAPERS_DIR) if fn.endswith(".json")]
    all_files.sort()
    files = all_files[offset: offset + limit]

    print(f"[INDEX] files_seen_total={len(all_files)} | batch_offset={offset} | batch_limit={limit} | batch_files={len(files)}")
    if not files:
        print("[INDEX] Nothing to do for this batch.")
        return {"status": "ok"}

    # --- Build Documents (we only require 'plain_text'; everything else is metadata and may be null) ---
    docs: List[Document] = []
    skipped_empty = 0
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                paper: Dict[str, Any] = json.load(f)
            text = (paper.get("plain_text") or "").strip()
            if not text:
                skipped_empty += 1
                continue
            metadata = {
                "pmcid": paper.get("pmcid"),
                "doi": paper.get("doi"),
                "title": paper.get("title"),
                "year": paper.get("year"),
                "journal": paper.get("journal"),
                "protein_hits": paper.get("protein_hits"),
                "source_url": paper.get("source_url"),
            }
            # Stable doc_id: pmcid or filename (without .json extension)
            pmcid = paper.get("pmcid")
            if pmcid and isinstance(pmcid, str) and pmcid.strip():
                doc_id = pmcid.strip()
            else:
                base = os.path.basename(path)
                doc_id = os.path.splitext(base)[0]
            
            docs.append(Document(text=text, metadata=metadata, doc_id=doc_id))
        except Exception as e:
            print(f"[INDEX][skip broken] {os.path.basename(path)}: {e}")

    print(f"[INDEX] docs_used={len(docs)} | docs_skipped_empty={skipped_empty}")
    if not docs:
        print("[INDEX] No usable documents in this batch (all had empty 'plain_text' or failed to load).")
        return {"status": "ok"}

    # --- Chunking (no embeddings yet) ---
    # Explanation:
    # - chunk_size ~800 tokens is a common sweet spot for scientific text.
    # - chunk_overlap retains context and helps retrieval across chunk boundaries.
    splitter = SentenceSplitter(chunk_size=800, chunk_overlap=120)
    nodes = splitter.get_nodes_from_documents(docs)
    print(f"[INDEX] chunks_created={len(nodes)}")

    # Set stable node IDs: <ref_doc_id>::chunk-<counter>
    from collections import defaultdict
    per_doc_counter = defaultdict(int)
    for node in nodes:
        ref = node.ref_doc_id or "NO_DOC_ID"
        k = per_doc_counter[ref]
        node.id_ = f"{ref}::chunk-{k}"
        per_doc_counter[ref] += 1

    if not nodes:
        print("[INDEX] No chunks created (unexpected if plain_text had content).")
        return {"status": "ok"}

    # --- Configure the embedding model (OpenAI-compatible call to Nebius) ---
    # Why this and not a chat model?
    # - Embeddings require a dedicated embedding model; chat models (like gpt-oss-120b) are for generation/extraction later.
    Settings.embed_model = NebiusStudioEmbedding(
        model=NEBIUS_EMBED_MODEL,
        api_key=api_key,
        base_url=NEBIUS_BASE_URL,   # OpenAI-compatible endpoint at Nebius
    )

    # NebiusEmbedding talks directly to Nebius AI Studio; model is a Nebius model id.
    #Settings.embed_model = NebiusEmbedding(
    #    api_key=api_key,
    #    model=NEBIUS_EMBED_MODEL,  # explicit + well-supported on Nebius
    #)


    # --- Set up persistent Chroma (on-disk) and wrap it with LlamaIndex VectorStore ---
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    chroma_collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

# >>>>>>> ADD THIS PRE-DELETE BLOCK (ensures true upsert-by-id) <<<<<<<
    try:
        ids_to_replace = [n.id_ for n in nodes]
        chroma_collection.delete(ids=ids_to_replace)
        print(f"[INDEX] predelete: removed up to {len(ids_to_replace)} existing ids (if they existed).")
    except Exception as e:
        print(f"[INDEX] predelete warning: {e}")
    # >>>>>>> END PRE-DELETE BLOCK <<<<<<<

    # --- Build/merge the index: this step computes embeddings and upserts to Chroma ---
    # Note: VectorStoreIndex(nodes, ...) will call the embed model under the hood and persist into Chroma.
    print(f"[INDEX] Embedding with model='{NEBIUS_EMBED_MODEL}' at base_url='{NEBIUS_BASE_URL}' ...")
    _index = VectorStoreIndex(nodes, storage_context=storage_context)

    # --- Optional: show current vector count in the collection for visibility ---
    try:
        current_count = chroma_collection.count()
        print(f"[INDEX] chroma_collection='{CHROMA_COLLECTION}' count={current_count}")
    except Exception as e:
        print(f"[INDEX] Could not read Chroma count: {e}")

    print("[INDEX] Batch done.")
    return {"status": "ok"}
