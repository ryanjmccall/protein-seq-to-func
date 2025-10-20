import httpx
import os, json, shutil
from fastapi import FastAPI, HTTPException
from pydantic_settings import BaseSettings
from typing import List, Optional, Dict, Any
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from openai import OpenAI
import chromadb
import numpy as np
import faiss


class Settings(BaseSettings):
    nebius_api_key: str
    
    class Config:
        env_file = ".env"

settings = Settings()

app = FastAPI(title="Felix Spike", version="0.0.1")

# ------- Public, non-secret config (hard-coded) -------
PAPERS_DIR = "papers"
CHROMA_PATH = "./chroma_db"            # local on-disk store
CHROMA_COLLECTION = "longevity_s2f"    # name of the vector collection
# Separate test DB (for debugging Chroma without touching the main DB)
CHROMA_TEST_PATH = "./chroma_db_test"
CHROMA_TEST_COLLECTION = "test_basic"
# FAISS storage directory (index + metadata JSONL)
FAISS_DIR = "./faiss_store"
# Configure a single, global splitter. We do not enable embeddings here.
# chunk_size ~800 tokens with ~120 overlap is a common default for scientific text.
#SPLITTER = SentenceSplitter(chunk_size=800, chunk_overlap=120)
# OpenAI-compatible base URL from Nebius Quickstart (documented).
# We keep this constant in code (not secret).
NEBIUS_BASE_URL = "https://api.studio.nebius.com/v1/"  # docs: /v1/chat/completions
NEBIUS_MODEL = "openai/gpt-oss-120b"  # inexpensive, open-source model suitable for tests
NEBIUS_EMBED_MODEL = "Qwen/Qwen3-Embedding-8B"
#NEBIUS_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct-fast"

os.environ["OPENAI_API_KEY"] = settings.nebius_api_key
os.environ["OPENAI_BASE_URL"] = NEBIUS_BASE_URL


@app.get("/nebius-embed-hello")
def nebius_embed_hello():
    from openai import OpenAI
    client = OpenAI(api_key=settings.nebius_api_key, base_url=NEBIUS_BASE_URL)
    r = client.embeddings.create(model=NEBIUS_EMBED_MODEL, input=["hello", "protein longevity"])
    print("[EMBED HELLO] dims:", len(r.data[0].embedding), len(r.data[1].embedding))
    return {"status": "ok"}



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

    url = f"{NEBIUS_BASE_URL}chat/completions"
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


@app.get("/chroma-test-basic")
def chroma_test_basic():
    """
    Minimal Chroma smoke test:
    - Creates/opens a SEPARATE test DB folder (CHROMA_TEST_PATH).
    - Creates/opens collection CHROMA_TEST_COLLECTION.
    - Adds two tiny 2D vectors with simple metadata.
    - Returns count and sample query results.
    """
    try:
        # Ensure a fresh test directory
        if os.path.exists(CHROMA_TEST_PATH):
            print(f"[TEST] Removing test DB dir: {CHROMA_TEST_PATH}")
            shutil.rmtree(CHROMA_TEST_PATH, ignore_errors=True)
        os.makedirs(CHROMA_TEST_PATH, exist_ok=True)
        print("[TEST] Fresh test DB dir ready")

        # Open test client and collection
        client = chromadb.PersistentClient(path=CHROMA_TEST_PATH)
        coll = client.get_or_create_collection(CHROMA_TEST_COLLECTION)
        print(f"[TEST] Opened collection '{CHROMA_TEST_COLLECTION}'")

        # Prepare tiny demo data
        ids = ["v1", "v2"]
        docs = ["alpha", "beta"]
        metas = [{"label": "A"}, {"label": "B"}]
        vecs = [[0.1, 0.2], [0.2, 0.3]]

        # Add to Chroma
        print("[TEST] Adding 2 vectors to test collection...")
        coll.add(ids=ids, documents=docs, metadatas=metas, embeddings=vecs)
        print("[TEST] Add completed")

        # Count
        count = coll.count()
        print(f"[TEST] Count after add: {count}")

        # Simple query
        print("[TEST] Running query for 'alpha'...")
        q = coll.query(query_texts=["alpha"], n_results=2)
        print("[TEST] Query result:", q)

        return {
            "status": "ok",
            "count": count,
            "query": q,
        }
    except Exception as e:
        print(f"[TEST][error] {e}")
        raise HTTPException(status_code=500, detail=f"chroma-test-basic failed: {str(e)}")

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
    - Persist vectors+metadata into a local FAISS index (index.faiss) + JSONL metadata (meta.jsonl) under FAISS_DIR.
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

    # Verbose dump of Documents for full transparency
    print("[INDEX][DEBUG] Dumping Documents...")
    for d in docs:
        try:
            print(f"--- Document doc_id={d.doc_id}")
            print(f"metadata={json.dumps(d.metadata, ensure_ascii=False)}")
            print("text:")
            print(d.text)
        except Exception as e:
            print(f"[INDEX][DEBUG][doc dump error] {e}")

    # --- Chunking (no embeddings yet) ---
    # Explanation:
    # - chunk_size ~800 tokens is a common sweet spot for scientific text.
    # - chunk_overlap retains context and helps retrieval across chunk boundaries.
    splitter = SentenceSplitter(chunk_size=800, chunk_overlap=120)
    nodes = splitter.get_nodes_from_documents(docs)
    print(f"[INDEX] chunks_created={len(nodes)}")

    # Verbose dump of Nodes (post-splitting)
    print("[INDEX][DEBUG] Dumping Nodes...")
    for i, n in enumerate(nodes):
        try:
            print(f"--- Node {i} id={n.id_} ref_doc_id={n.ref_doc_id}")
            print(f"metadata={json.dumps(n.metadata or {}, ensure_ascii=False)}")
            content = n.get_content(metadata_mode="none")
            print("content:")
            print(content)
        except Exception as e:
            print(f"[INDEX][DEBUG][node dump error] {e}")

    # Set stable node IDs: <ref_doc_id>::chunk-<counter>
    # NOTE: Disabled because we perform a full DB reset each run; stable IDs are not required.
    # from collections import defaultdict
    # per_doc_counter = defaultdict(int)
    # for node in nodes:
    #     ref = node.ref_doc_id or "NO_DOC_ID"
    #     k = per_doc_counter[ref]
    #     node.id_ = f"{ref}::chunk-{k}"
    #     per_doc_counter[ref] += 1

    if not nodes:
        print("[INDEX] No chunks created (unexpected if plain_text had content).")
        return {"status": "ok"}

    # # --- CHROMA FULL RESET: Delete and recreate the entire DB ---
    # try:
    #     if os.path.exists(CHROMA_PATH):
    #         print(f"[INDEX][RESET] Removing Chroma directory: {CHROMA_PATH}")
    #         shutil.rmtree(CHROMA_PATH, ignore_errors=True)
    #     os.makedirs(CHROMA_PATH, exist_ok=True)
    #     print("[INDEX][RESET] Fresh Chroma directory ready.")
    # except Exception as e:
    #     print(f"[INDEX][RESET error] {e}")
    #     raise HTTPException(status_code=500, detail="Failed to reset Chroma directory")

    # # --- Set up persistent Chroma (on-disk) ---
    # print("[INDEX][DEBUG] Setting up Chroma client...")
    # chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    # print("[INDEX][DEBUG] Getting or creating Chroma collection...")
    # chroma_collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION)
    # print(f"[INDEX][DEBUG] Chroma collection ready: {CHROMA_COLLECTION}")

    # --- Embeddings directly via Nebius (OpenAI-compatible) and upsert to Chroma ---
    print("[INDEX][DEBUG] Creating OpenAI client for Nebius...")
    client = OpenAI(api_key=settings.nebius_api_key, base_url=NEBIUS_BASE_URL)

    # Prepare texts for embedding (one embedding per node)
    print("[INDEX][DEBUG] Preparing node IDs and texts...")
    node_ids = [n.id_ for n in nodes]
    node_texts = [n.get_content(metadata_mode="none") for n in nodes]   # extract text content only
    print(f"[INDEX][DEBUG] Prepared {len(node_ids)} node IDs and {len(node_texts)} texts")
    
    # Clean metadata for Chroma (convert lists to JSON strings, keep only simple types)
    def clean_metadata_for_chroma(meta: Dict[str, Any]) -> Dict[str, Any]:
        """Convert metadata to Chroma-compatible format (str, int, float, bool only - NO None!)."""
        cleaned = {}
        for key, value in (meta or {}).items():
            if value is None:
                # Use type-appropriate defaults for known fields to maintain consistent types
                # Based on actual JSON structure: pmcid, doi, title, year, journal, protein_hits, source_url
                if key == "year":
                    cleaned[key] = 0  # year is numeric field, default to 0
                else:
                    cleaned[key] = ""  # all other fields (pmcid, doi, title, journal, source_url, protein_hits) get empty string
            elif isinstance(value, (str, int, float, bool)):
                cleaned[key] = value  # keep simple types as-is
            elif isinstance(value, list):
                cleaned[key] = json.dumps(value)  # convert lists to JSON string (e.g., protein_hits)
            elif isinstance(value, dict):
                cleaned[key] = json.dumps(value)  # convert dicts to JSON string
            else:
                cleaned[key] = str(value)  # fallback: convert to string
        return cleaned
    
    print("[INDEX][DEBUG] Cleaning metadata for Chroma...")
    node_metas = [clean_metadata_for_chroma(n.metadata) for n in nodes]  # extract and clean metadata
    print(f"[INDEX][DEBUG] Cleaned {len(node_metas)} metadata entries")

    # Request embeddings in a single batch from Nebius
    try:
        print(f"[INDEX] Embedding with model='{NEBIUS_EMBED_MODEL}' at base_url='{NEBIUS_BASE_URL}' ...")
        print(f"[INDEX][DEBUG] Sending {len(node_texts)} texts to Nebius for embedding...")
        emb_resp = client.embeddings.create(model=NEBIUS_EMBED_MODEL, input=node_texts)
        print("[INDEX][DEBUG] Received response from Nebius, extracting embeddings...")
        embeddings = [d.embedding for d in emb_resp.data]  # extract embedding vectors
        print(f"[INDEX][DEBUG] Extracted {len(embeddings)} embeddings")
    except Exception as e:
        print(f"[INDEX][embed error] {e}")
        raise HTTPException(status_code=500, detail="Nebius embedding request failed")

    # Sanity check: ensure we got one embedding per node
    if len(embeddings) != len(node_ids):
        print(f"[INDEX][embed mismatch] ids={len(node_ids)} vs embeds={len(embeddings)}")
        raise HTTPException(status_code=500, detail="Embedding count mismatch")

    # Debug: Check embedding dimensions
    if embeddings:
        emb_dim = len(embeddings[0])
        print(f"[INDEX][DEBUG] Embedding dimensions: {emb_dim} (first vector)")

    # === FAISS: Minimalpersistenz (ein Index + eine JSONL mit Metadaten), APPEND-ONLY ===
    # Ensure target directory exists (no deletion between batches)
    try:
        os.makedirs(FAISS_DIR, exist_ok=True)
    except Exception as e:
        print(f"[INDEX][FAISS dir error] {e}")
        raise HTTPException(status_code=500, detail="Failed to create FAISS directory")

    # Embeddings -> numpy array (float32); normalize for cosine-like IP search
    X = np.array(embeddings, dtype="float32")
    if X.ndim != 2 or X.shape[0] == 0:
        raise HTTPException(status_code=500, detail="No embeddings to index")
    faiss.normalize_L2(X)

    dim = int(X.shape[1])
    faiss_path = os.path.join(FAISS_DIR, "index.faiss")
    dim_path = os.path.join(FAISS_DIR, "dim.txt")

    # If an index exists, load and validate dimension; else create new
    if os.path.isfile(faiss_path):
        index = faiss.read_index(faiss_path)
        if int(index.d) != dim:
            raise HTTPException(status_code=400, detail=f"FAISS dim mismatch: index has {int(index.d)}, new vectors have {dim}")
        print(f"[INDEX][FAISS] Loaded existing index: {faiss_path} (ntotal={index.ntotal}, dim={int(index.d)})")
    else:
        index = faiss.IndexFlatIP(dim)
        print(f"[INDEX][FAISS] Created new IndexFlatIP dim={dim}")

    # Persist/verify dimension helper file
    try:
        if os.path.isfile(dim_path):
            try:
                with open(dim_path, "r", encoding="utf-8") as g:
                    prev_dim = int((g.read() or "").strip() or "0")
                if prev_dim != dim:
                    raise HTTPException(status_code=400, detail=f"FAISS dim mismatch: stored dim.txt={prev_dim}, new vectors have {dim}")
            except ValueError:
                print("[INDEX][FAISS dim warn] dim.txt is not an integer; rewriting")
                with open(dim_path, "w", encoding="utf-8") as g:
                    g.write(str(dim))
        else:
            with open(dim_path, "w", encoding="utf-8") as g:
                g.write(str(dim))
    except HTTPException:
        raise
    except Exception as e:
        print(f"[INDEX][FAISS dim write warn] {e}")

    # Append new vectors
    index.add(X)
    faiss.write_index(index, faiss_path)
    print(f"[INDEX][FAISS] Saved index: {faiss_path} (ntotal={index.ntotal})")

    # Append metadata aligned with vector order: lines correspond to new appended vectors
    meta_path = os.path.join(FAISS_DIR, "meta.jsonl")
    try:
        with open(meta_path, "a", encoding="utf-8") as f:
            for _id, _txt, _meta in zip(node_ids, node_texts, node_metas):
                f.write(json.dumps({"id": _id, "text": _txt, "meta": _meta}, ensure_ascii=False) + "\n")
        print(f"[INDEX][FAISS] Appended metadata JSONL: {meta_path} (+{len(node_ids)} lines)")
    except Exception as e:
        print(f"[INDEX][FAISS meta write error] {e}")
        raise HTTPException(status_code=500, detail="Failed to write FAISS metadata JSONL")

    print("[INDEX] Batch done (FAISS append).")
    return {"status": "ok"}
