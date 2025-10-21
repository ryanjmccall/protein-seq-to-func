import httpx
import os, json, shutil
import re
import xml.etree.ElementTree as ET
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


    if not nodes:
        print("[INDEX] No chunks created (unexpected if plain_text had content).")
        return {"status": "ok"}

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
        # ALT (Single-Batch, vorher):
        # emb_resp = client.embeddings.create(model=NEBIUS_EMBED_MODEL, input=node_texts)
        # print("[INDEX][DEBUG] Received response from Nebius, extracting embeddings...")
        # embeddings = [d.embedding for d in emb_resp.data]  # extract embedding vectors
        # print(f"[INDEX][DEBUG] Extracted {len(embeddings)} embeddings")

        # --- simples Batching für Embeddings (keine Retries, kein Backoff) ---
        BATCH_SIZE = 96  # z.B. 64–128; 96 ist ein guter Start
        embeddings = []
        for start in range(0, len(node_texts), BATCH_SIZE):
            batch = node_texts[start:start + BATCH_SIZE]
            print(f"[INDEX][DEBUG] Embedding batch {start//BATCH_SIZE + 1} ({len(batch)} texts, {start}..{start+len(batch)-1})")
            resp = client.embeddings.create(model=NEBIUS_EMBED_MODEL, input=batch)
            # Reihenfolge bleibt wie Input; wir hängen nur an
            embeddings.extend([item.embedding for item in resp.data])

        print(f"[INDEX][DEBUG] Total embeddings: {len(embeddings)}")
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
    # Ensure the FAISS storage directory exists (append-only; do not delete between batches)
    try:
        os.makedirs(FAISS_DIR, exist_ok=True)  # create the directory if missing; no error if it already exists
    except Exception as e:
        print(f"[INDEX][FAISS dir error] {e}")
        raise HTTPException(status_code=500, detail="Failed to create FAISS directory")

    # Convert embeddings to a contiguous float32 matrix that FAISS expects: shape [num_vectors, embedding_dim]
    # FAISS operates on float32 arrays; this makes dtype and memory layout compatible and fast.
    X = np.array(embeddings, dtype="float32")
    if X.ndim != 2 or X.shape[0] == 0:
        raise HTTPException(status_code=500, detail="No embeddings to index")
    # L2-normalize each vector so that inner product (IP) behaves like cosine similarity (IP of unit vectors = cosine)
    faiss.normalize_L2(X)

    # Embedding dimensionality (number of features per vector). Must stay constant across all batches for the same index.
    dim = int(X.shape[1])
    # Build file paths:
    # - faiss_path is the persisted index file; os.path.join safely constructs the path for the current OS.
    #   The file may or may not exist yet; existence is handled below.
    # - dim_path is a tiny helper file storing the embedding dimension for consistency checks across batches.
    faiss_path = os.path.join(FAISS_DIR, "index.faiss")
    dim_path = os.path.join(FAISS_DIR, "dim.txt")

    # If an index exists, load and validate dimension; else create new
    # Load existing index (resume) if it exists and its dimension matches; otherwise create a fresh IndexFlatIP.
    # IndexFlatIP uses inner product; combined with L2 normalization this yields cosine-like retrieval.
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
                # 'with' is a Python context manager: it opens the file and guarantees it will be closed automatically.
                with open(dim_path, "r", encoding="utf-8") as g:
                    prev_dim = int((g.read() or "").strip() or "0")
                if prev_dim != dim:
                    raise HTTPException(status_code=400, detail=f"FAISS dim mismatch: stored dim.txt={prev_dim}, new vectors have {dim}")
            except ValueError:
                print("[INDEX][FAISS dim warn] dim.txt is not an integer; rewriting")
                with open(dim_path, "w", encoding="utf-8") as g:  # context manager ensures the file is closed properly
                    g.write(str(dim))
        else:
            with open(dim_path, "w", encoding="utf-8") as g:  # first-time write of the embedding dimension
                g.write(str(dim))
    except HTTPException:
        raise
    except Exception as e:
        print(f"[INDEX][FAISS dim write warn] {e}")

    # Append new vectors
    index.add(X)
    faiss.write_index(index, faiss_path)
    print(f"[INDEX][FAISS] Saved index: {faiss_path} (ntotal={index.ntotal})")

    # Append metadata aligned with vector order: each new JSONL line corresponds to a newly added vector
    # JSONL (JSON Lines) = one JSON object per line; ideal for append-only writes and easy streaming reads
    meta_path = os.path.join(FAISS_DIR, "meta.jsonl")  # target metadata file (append-only across batches)
    try:
        # 'a' = append mode; preserves previous content and adds new lines for the current batch
        # 'f' is the opened writable file handle; the context manager ensures it is closed automatically
        with open(meta_path, "a", encoding="utf-8") as f:
            # zip iterates the three equal-length lists in lockstep: (node_id, node_text, node_meta) per vector
            # Fields:
            #   - id: the node identifier (string)
            #   - text: the chunk text associated with the vector (string)
            #   - meta: cleaned metadata dict for the node (dict of primitive/JSON-serializable values)
            for _id, _txt, _meta in zip(node_ids, node_texts, node_metas):
                # ensure_ascii=False preserves non-ASCII characters as UTF-8 instead of escaping
                # the trailing "\n" ensures exactly one JSON object per line (JSONL format)
                f.write(json.dumps({"id": _id, "text": _txt, "meta": _meta}, ensure_ascii=False) + "\n")
        print(f"[INDEX][FAISS] Appended metadata JSONL: {meta_path} (+{len(node_ids)} lines)")
    except Exception as e:
        print(f"[INDEX][FAISS meta write error] {e}")
        raise HTTPException(status_code=500, detail="Failed to write FAISS metadata JSONL")

    print("[INDEX] Batch done (FAISS append).")
    # ----------------------------------------------------------------------
    # SIMPLE FAISS QUERY (inline, for quick smoke-testing)
    # ----------------------------------------------------------------------
    # Fixed test query string (you can replace this later or make it a parameter)
    QUERY = "APOE variant longevity lifespan"

    # Number of top semantic matches to retrieve for the test query
    query_top_k = 10  # you can change this to any integer you like

    try:
        # -- 1) Create a query embedding using the same model as indexing --
        #    Reuse the Nebius OpenAI-compatible client created above.
        q_emb_resp = client.embeddings.create(model=NEBIUS_EMBED_MODEL, input=[QUERY])

        # -- 2) Convert the returned Python list (embedding) into a float32 NumPy array --
        #    FAISS expects float32; shape must be (1, dim) for a single query vector.
        qvec = np.array(q_emb_resp.data[0].embedding, dtype="float32").reshape(1, -1)

        # -- 3) L2-normalize the query vector --
        #    Because we used IndexFlatIP and normalized stored vectors, we normalize the query as well
        #    so that inner product ≈ cosine similarity.
        faiss.normalize_L2(qvec)

        # -- 4) Load the FAISS index that we just persisted (or appended to) in this batch --
        faiss_path = os.path.join(FAISS_DIR, "index.faiss")
        q_index = faiss.read_index(faiss_path)

        # -- 5) Run the similarity search: returns scores (D) and indices (I) --
        #    D: similarity scores (higher is more similar for IP/cosine)
        #    I: integer indices into the vector store (aligned with meta.jsonl line order)
        D, I = q_index.search(qvec, query_top_k)

        # -- 6) Load metadata lines so we can map FAISS indices back to texts and paper info --
        meta_path = os.path.join(FAISS_DIR, "meta.jsonl")
        with open(meta_path, "r", encoding="utf-8") as f:
            meta_lines = [json.loads(l) for l in f]

        # -- 7) Build a lightweight result list of the top-k chunks --
        #    We attach score and a small preview of the text for quick debugging.
        #
        #    Notes on FAISS outputs and variables used below:
        #    - D: shape [1, top_k] similarity scores; higher means more similar for IP/cosine.
        #    - I: shape [1, top_k] integer indices; each index points to a vector we added earlier.
        #      The indices align 1:1 with lines in meta.jsonl because we wrote metadata in the
        #      exact same order we appended vectors to the FAISS index.
        #    - enumerate(zip(...), start=1) yields (rank, (score, idx)) per hit:
        #      * rank: 1-based position in the ranked list (1 = best match).
        #      * score: similarity for this hit (float).
        #      * idx: integer position used to look up meta_lines[idx].
        #    This loop materializes a compact list of hit dicts for easy printing/inspection.
        query_hits = []
        for rank, (score, idx) in enumerate(zip(D[0].tolist(), I[0].tolist()), start=1):
            if 0 <= idx < len(meta_lines):
                # Map FAISS index -> metadata record; same order ensures stable alignment.
                rec = meta_lines[idx]
                # Optional: shorten the text for terminal readability
                preview_text = rec.get("text", "")
                if len(preview_text) > 300:
                    preview_text = preview_text[:300] + "…"

                # Prepare a compact result object
                hit = {
                    "rank": rank,
                    "score": float(score),
                    "id": rec.get("id"),
                    "pmcid": (rec.get("meta") or {}).get("pmcid", ""),
                    "doi": (rec.get("meta") or {}).get("doi", ""),
                    "title": (rec.get("meta") or {}).get("title", ""),
                    "year": (rec.get("meta") or {}).get("year", 0),
                    "journal": (rec.get("meta") or {}).get("journal", ""),
                    "source_url": (rec.get("meta") or {}).get("source_url", ""),
                    "text_preview": preview_text,
                }
                query_hits.append(hit)

        # -- 8) Print a human-readable preview to the server console for inspection --
        print(f"[QUERY] text='{QUERY}' | top_k={query_top_k}")
        for h in query_hits:
            print(f"  #{h['rank']:02d} score={h['score']:.4f} | {h['pmcid']} | {h['doi']} | {h['title']}")
            print(f"      {h['text_preview']}")
    except Exception as e:
        # If anything goes wrong during the query phase, keep indexing result intact and log the error only.
        print(f"[QUERY][error] {e}")

    # ----------------------------------------------------------------------
    # PER-CHUNK LLM EXTRACTION (Nebius Chat Completions)
    # ----------------------------------------------------------------------
    # We now send each retrieved chunk to the Nebius LLM and ask it to extract
    # "sequence-to-function" facts relevant to longevity. This is a first-pass
    # extractor: JSON-only, chunk-scoped, no cross-chunk aggregation yet.
    #
    # Notes:
    # - Uses the same NEBIUS_MODEL as in /nebius-hello (OpenAI-compatible).
    # - Keeps temperature low for determinism.
    # - Enforces JSON response via response_format (json_schema).
    # - Prints results to terminal; also stores in 'extractions' list in RAM.
    #
    # Later:
    # - You can add cross-paper expansion (load all chunks of a PMCID).
    # - You can add deduplication/reranking/aggregation.
    # - You can add a second LLM pass to write full Wiki-style articles.
    # ----------------------------------------------------------------------

    # Limit how many chunks to extract from in this first pass (cost control).
    # You can later make this a parameter; we default to using all current hits.
    max_chunks_for_extraction = len(query_hits)

    # Prepare a strict JSON schema so the model must return structured fields.
    extraction_schema = {
        "name": "s2f_extraction",
        "schema": {
            "type": "object",
            "properties": {
                "protein": {"type": "string", "description": "Canonical protein/gene name if explicitly mentioned; otherwise empty."},
                "organism": {"type": "string", "description": "Species/organism context if stated; otherwise empty."},
                "sequence_interval": {"type": "string", "description": "Residue or nucleotide interval (e.g., 'aa 120-145', or motif/domain) if inferable; otherwise empty."},
                "modification": {"type": "string", "description": "Exact sequence change (e.g., 'E4 (Arg112/Arg158)', 'Cys->Ser at pos 151)', 'domain deletion') if present; otherwise empty."},
                "functional_effect": {"type": "string", "description": "Functional change on the protein/gene (e.g., binding, stability, transcriptional activity)."},
                "longevity_effect": {"type": "string", "description": "Effect on lifespan/healthspan if present (e.g., increased lifespan in C.elegans)."},
                "evidence_type": {"type": "string", "description": "Type of evidence (e.g., genetic manipulation, mutant strain, CRISPR edit, overexpression, knockdown)."},
                "figure_or_panel": {"type": "string", "description": "Figure/panel if explicitly cited (e.g., 'Fig. 2B'); otherwise empty."},
                "citation_hint": {"type": "string", "description": "Any DOI/PMCID/PMID text in the chunk; empty if none. Do not invent IDs."},
                "confidence": {"type": "number", "description": "0.0–1.0 subjective confidence derived from the chunk only."}
            },
            "required": ["protein", "modification", "functional_effect", "longevity_effect", "confidence"],
            "additionalProperties": False
        },
        "strict": True
    }

    # System and user prompts. We keep the user prompt short and inject the chunk verbatim.
    SYSTEM_PROMPT = (
        "You are a careful scientific text-miner for protein/gene sequence-to-function relationships in the context of longevity. "
        "Extract only what is explicitly supported by the provided chunk. Do not hallucinate unknown IDs or effects. "
        "If a field is not present in the text, return an empty string for that field (or 0.0 for confidence)."
    )

    USER_INSTRUCTION_PREFIX = (
        "From the following paper chunk, extract ONLY facts about sequence modifications (mutations, domain edits, variants) "
        "and their functional outcomes, especially any lifespan/healthspan associations. "
        "Work strictly chunk-local: do not infer from general knowledge. "
        "Return a single JSON object that conforms to the provided schema."
        "\n\n--- BEGIN CHUNK ---\n"
    )
    USER_INSTRUCTION_SUFFIX = "\n--- END CHUNK ---"

    # We'll reuse the same Nebius HTTP style as in nebius_hello()
    neb_url = f"{NEBIUS_BASE_URL}chat/completions"
    neb_headers = {
        "Authorization": f"Bearer {settings.nebius_api_key}",
        "Content-Type": "application/json",
    }

    # Ensure 'meta_lines' is available (loaded earlier in the query phase). Reload if missing.
    if "meta_lines" not in locals():
        meta_path = os.path.join(FAISS_DIR, "meta.jsonl")
        with open(meta_path, "r", encoding="utf-8") as f:
            meta_lines = [json.loads(l) for l in f]

    # Collect extraction outputs here
    extractions = []

    # Iterate over each hit (chunk) and call the LLM once per chunk.
    for i, hit in enumerate(query_hits[:max_chunks_for_extraction], start=1):
        # Find the full text by 'id' (unique node id created by LlamaIndex SentenceSplitter)
        node_id = hit.get("id")
        full_text = ""
        for rec in meta_lines:
            if rec.get("id") == node_id:
                full_text = rec.get("text", "")
                break

        # Safety: if for some reason we didn't find it, fall back to preview.
        if not full_text:
            full_text = hit.get("text_preview", "")

        # Compose the user content with chunk text
        user_content = USER_INSTRUCTION_PREFIX + full_text + USER_INSTRUCTION_SUFFIX

        # Build the payload enforcing JSON schema
        payload = {
            "model": NEBIUS_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.1,
            "max_tokens": 600,
            "response_format": {
                "type": "json_schema",
                "json_schema": extraction_schema
            }
        }

        print(f"[EXTRACT] Calling Nebius LLM for chunk #{i} | PMCID={hit.get('pmcid','')} | title='{hit.get('title','')[:80]}'")
        try:
            with httpx.Client(timeout=90) as neb_client:
                resp = neb_client.post(neb_url, json=payload, headers=neb_headers)
            print(f"[EXTRACT] HTTP {resp.status_code}")

            # Try to parse model's JSON response
            data = resp.json()
            # Defensive parsing: choices → message → content (JSON as string)
            content = ""
            if isinstance(data, dict) and "choices" in data and data["choices"]:
                content = data["choices"][0]["message"]["content"] or ""

            extracted_obj = {}
            if content:
                try:
                    extracted_obj = json.loads(content)
                except json.JSONDecodeError:
                    # If schema mode was not obeyed due to model drift, keep raw content for debugging.
                    extracted_obj = {"_raw": content}

            # Attach hit metadata for provenance
            extracted_obj["_provenance"] = {
                "pmcid": hit.get("pmcid", ""),
                "doi": hit.get("doi", ""),
                "title": hit.get("title", ""),
                "year": hit.get("year", 0),
                "journal": hit.get("journal", ""),
                "source_url": hit.get("source_url", ""),
                "rank": hit.get("rank", i),
                "score": hit.get("score", None),
                "node_id": node_id,
            }

            # Store in RAM list
            extractions.append(extracted_obj)

            # Pretty-print a compact summary to terminal
            try:
                print(
                    "[EXTRACT][OK]",
                    f"protein={extracted_obj.get('protein','')!r}",
                    f"mod={extracted_obj.get('modification','')!r}",
                    f"fx={extracted_obj.get('functional_effect','')!r}",
                    f"longevity={extracted_obj.get('longevity_effect','')!r}",
                    f"conf={extracted_obj.get('confidence', 0.0)}",
                )
            except Exception:
                print("[EXTRACT][OK] (unprintable chars)")

        except Exception as e:
            print(f"[EXTRACT][error] {e}")
            # Keep going; append minimal error record for visibility
            extractions.append({
                "_error": str(e),
                "_provenance": {
                    "pmcid": hit.get("pmcid", ""),
                    "title": hit.get("title", ""),
                    "rank": hit.get("rank", i),
                    "node_id": node_id,
                }
            })

    # Final log: how many extractions we collected
    print(f"[EXTRACT] Completed {len(extractions)}/{max_chunks_for_extraction} chunk extractions.")

    # ----------------------------------------------------------------------
    # SECOND LLM CALL: GENERATE HTML ARTICLE (NO RETURN PAYLOAD)
    # ----------------------------------------------------------------------
    # This block takes the JSON extractions created above and calls Nebius LLM
    # to synthesize a WikiCrow-style HTML article. The HTML is saved locally
    # and a console preview is printed. Nothing is returned to the browser
    # except {"status": "ok"}.
    # ----------------------------------------------------------------------

    protein_name = "APOE"  # hard-coded test target; replace later with variable

    # Compact extractions (filter only fields relevant for composing)
    compact_extractions = []
    for ex in extractions:
        if not isinstance(ex, dict):
            continue
        compact_extractions.append({
            "protein": ex.get("protein", ""),
            "organism": ex.get("organism", ""),
            "sequence_interval": ex.get("sequence_interval", ""),
            "modification": ex.get("modification", ""),
            "functional_effect": ex.get("functional_effect", ""),
            "longevity_effect": ex.get("longevity_effect", ""),
            "evidence_type": ex.get("evidence_type", ""),
            "figure_or_panel": ex.get("figure_or_panel", ""),
            "citation_hint": ex.get("citation_hint", ""),
            "confidence": ex.get("confidence", 0.0),
            "_provenance": ex.get("_provenance", {}),
        })

    # Define output JSON schema (LLM must return {title, html})
    article_schema = {
        "name": "wikicrow_article",
        "schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "html": {"type": "string"}
            },
            "required": ["title", "html"],
            "additionalProperties": False
        },
        "strict": True
    }

    ARTICLE_SYSTEM = (
        "You are a senior scientific editor. Write concise HTML articles "
        "summarizing protein sequence-to-function relationships related to longevity. "
        "Use the provided extraction data only; do not invent facts or citations. "
        "Return the article as clean, minimal HTML suitable for web display."
    )

    article_user_instruction = (
        "Compose a WikiCrow-style HTML article for the protein '"
        + protein_name
        + "'. Use these extraction objects as factual input. "
        "Include sections for Overview, Sequence→Function Table, and Notes. "
        "Use semantic HTML tags only (<h1>, <h2>, <table>, <tr>, <td>, <ul>, <li>, <p>). "
        "The table must have columns: Interval, Modification, Functional Effect, "
        "Longevity Effect, Evidence, Citation. Do not include external CSS or scripts. "
        "\n\nExtraction data:\n"
        + json.dumps({"protein": protein_name, "extractions": compact_extractions}, ensure_ascii=False)
    )

    # Build the Nebius payload for chat completion
    article_payload = {
        "model": NEBIUS_MODEL,
        "messages": [
            {"role": "system", "content": ARTICLE_SYSTEM},
            {"role": "user", "content": article_user_instruction}
        ],
        "temperature": 0.2,
        "max_tokens": 1800,
        "response_format": {
            "type": "json_schema",
            "json_schema": article_schema
        }
    }

    print(f"[ARTICLE] Generating HTML article for protein={protein_name!r} using {NEBIUS_MODEL}")

    try:
        with httpx.Client(timeout=120) as neb_client:
            aresp = neb_client.post(
                f"{NEBIUS_BASE_URL}chat/completions",
                json=article_payload,
                headers={
                    "Authorization": f"Bearer {settings.nebius_api_key}",
                    "Content-Type": "application/json",
                },
            )
        print(f"[ARTICLE] HTTP {aresp.status_code}")

        article_title = f"{protein_name} — Sequence-to-Function & Longevity"
        article_html = "<h1>Draft</h1><p>No content returned.</p>"

        adata = aresp.json()
        if isinstance(adata, dict) and adata.get("choices"):
            acontent = adata["choices"][0]["message"]["content"] or ""
            try:
                aobj = json.loads(acontent)
                article_title = aobj.get("title") or article_title
                article_html = aobj.get("html") or article_html
            except json.JSONDecodeError:
                # Fallback: model returned plain text instead of JSON
                article_html = f"<h1>{article_title}</h1><pre>{acontent}</pre>"

        # Save HTML locally
        out_dir = os.path.join(FAISS_DIR, "articles")
        os.makedirs(out_dir, exist_ok=True)  # create directory if missing
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", protein_name)
        out_path = os.path.join(out_dir, f"{safe_name}.html")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(article_html)
        print(f"[ARTICLE] Saved article HTML: {out_path}")

        # Optional console preview (first 800 chars)
        preview = article_html[:800] + ("…" if len(article_html) > 800 else "")
        print("[ARTICLE][preview]\n", preview)

    except Exception as e:
        print(f"[ARTICLE][error] {e}")

    


    return {"status": "ok"}



@app.get("/harvest/apoe")
def harvest_apoe():
    """
    Harvests *Open Access only* Europe PMC papers that mention APOE (incl. synonyms),
    downloads JATS XML for fulltext, converts to plain text, and saves one JSON per paper
    into the local 'papers/' directory so your /index/batch can ingest them.

    All parameters are hard-coded (no URL params).
    """

    # ------------------------- Hard-coded settings -------------------------
    PROTEIN = "APOE"          # search term (Europe PMC search is case-insensitive)
    PAGE_SIZE = 1000          # Europe PMC maximum per page
    TIMEOUT_SECS = 60         # HTTP client timeout
    OA_ONLY = True            # we only collect Open Access; OA -> PMCID should be present
    SAVE_XML = True           # include raw JATS XML in JSON (can be set to False to save space)
    MAX_HARVEST = 1000        # cap for test runs; raise/remove later
    # ----------------------------------------------------------------------

    # Ensure output directory exists (uses the global PAPERS_DIR defined at top of file)
    os.makedirs(PAPERS_DIR, exist_ok=True)

    # Build Europe PMC query.
    # TEXT: searches title, abstract, AND full text (if available).
    # synonym=Y: expand common gene/protein synonyms on EPMC side.
    # OPEN_ACCESS:Y: restricts to OA articles so we can fetch full JATS XML.
    base_query = f'(TEXT:"{PROTEIN}") AND OPEN_ACCESS:Y'

    # -------------------- Small helpers (pure stdlib) ----------------------
    def _normalize_ws(s: str) -> str:
        """Collapse multiple whitespace to single spaces and trim."""
        return re.sub(r"\s+", " ", (s or "")).strip()

    def _parent_of(root: ET.Element, node: ET.Element):
        """Naive parent lookup for ElementTree (used to prune branches)."""
        for p in root.iter():
            for c in list(p):
                if c is node:
                    return p
        return None

    def jats_body_to_text(xml_text: str) -> str:
        """
        Convert JATS XML to a readable plain text:
        - Removes reference lists, figures, tables, and supplementary material (noise for embeddings).
        - Extracts <body> text if present, else falls back to whole tree text.
        - Normalizes whitespace.
        This is intentionally simple/robust rather than perfect formatting.
        """
        try:
            root = ET.fromstring(xml_text)
        except Exception:
            # If parsing fails, return normalized raw XML string (last-resort).
            return _normalize_ws(xml_text)

        # Drop typical non-content sections to declutter embeddings.
        def _remove_all(tag_local: str):
            for el in list(root.iter()):
                if isinstance(el.tag, str) and el.tag.endswith(tag_local) and el is not root:
                    parent = _parent_of(root, el)
                    if parent is not None:
                        parent.remove(el)

        for tag in ("ref-list", "table-wrap", "fig", "supplementary-material"):
            _remove_all(tag)

        # Prefer article body if present.
        target = None
        for el in root.iter():
            if isinstance(el.tag, str) and el.tag.endswith("body"):
                target = el
                break
        if target is None:
            target = root

        texts = []
        for t in target.itertext():
            texts.append(t)
        return _normalize_ws(" ".join(texts))
    # ----------------------------------------------------------------------

    # ----------------------------- Harvest loop ----------------------------
    # CursorMark (aka deep paging): Europe PMC returns a "nextCursorMark" token that you
    # pass back to retrieve the next page *without skipping* results even if the index changes.
    # We iterate until there are no more results or (optionally) a limit would be reached.
    cursor_mark = "*"
    harvested = 0
    seen_ids = set()

    with httpx.Client(timeout=TIMEOUT_SECS) as client:
        while True:
            # Prepare search request parameters (hard-coded strategy).
            params = {
                "query": base_query,
                "format": "json",        # ask for JSON so we can parse quickly
                "resultType": "core",    # standard metadata fields (title, abstract, IDs, OA flag, etc.)
                "pageSize": str(PAGE_SIZE),
                "cursorMark": cursor_mark,  # deep paging handle (see comment above)
                "synonym": "Y",             # activate Europe PMC synonym expansion
                # Align sort with working example in europepmc_search() to avoid API quirks with cursorMark
                # Europe PMC docs note stable sorts are recommended for cursor-based paging.
                "sort": "CITED desc",
            }

            # Visibility for server logs: which page are we fetching?
            print(f"[HARVEST][SEARCH] GET {EPMC_SEARCH_URL} q={params['query']} cursor={cursor_mark}")

            # Fire the search request and raise if HTTP status != 200.
            r = client.get(EPMC_SEARCH_URL, params=params)
            r.raise_for_status()

            # Parse the JSON payload and extract the "result" list and the next cursor.
            data = r.json()
            # Log total hit count reported by Europe PMC (useful to see scope upfront)
            try:
                print(f"[HARVEST][DEBUG] hitCount={data.get('hitCount', 0)}")
            except Exception:
                pass
            results = (data.get("resultList") or {}).get("result") or []
            print(f"[HARVEST][SEARCH] hits={len(results)}")
            next_cursor = data.get("nextCursorMark")

            # If no results, log a compact debug snippet and finish.
            if not results:
                try:
                    print("[HARVEST][debug] Empty page. Response keys:", list(data.keys()))
                    # Print a compact preview of payload to inspect structure differences
                    preview = str(data)
                    if len(preview) > 1200:
                        preview = preview[:1200] + "…"
                    print("[HARVEST][debug] Payload preview:", preview)
                except Exception:
                    pass
                break

            for rec in results:
                # Deduplicate across pages using a stable identifier preference.
                rid = rec.get("pmcid") or rec.get("id") or rec.get("pmid") or rec.get("doi")
                if not rid or rid in seen_ids:
                    continue
                seen_ids.add(rid)

                # OA-only is enforced by the query; OA entries should have a PMCID.
                pmcid = (rec.get("pmcid") or "").strip()
                if not pmcid:
                    # Extremely rare corner case; skip if no PMCID (we rely on PMCID for fullTextXML).
                    continue

                # Build the JSON skeleton expected by /index/batch.
                doi = (rec.get("doi") or "").strip()
                title = (rec.get("title") or "").strip()
                year = int(rec.get("pubYear") or 0)
                journal = (rec.get("journalTitle") or "").strip()

                # For OA items with PMCID, a canonical Europe PMC article URL is stable.
                source_url = f"https://europepmc.org/article/pmcid/{pmcid}"

                obj = {
                    "pmcid": pmcid,
                    "doi": doi,
                    "title": title,
                    "year": year,
                    "journal": journal,
                    "protein_hits": [PROTEIN],
                    "xml": "",
                    "plain_text": "",
                    "source_url": source_url,
                }

                # ---------------------- Fetch full JATS XML ----------------------
                # Europe PMC full-text endpoint pattern: /{PMCID}/fullTextXML
                full_url = f"{EPMC_FULLTEXT_BASE}/{pmcid}/fullTextXML"
                print(f"[HARVEST][XML] GET {full_url}")

                xml_text = ""
                try:
                    fr = client.get(full_url)
                    if fr.status_code == 200:
                        xml_text = fr.text or ""
                    else:
                        print(f"[HARVEST][warn] fullTextXML {pmcid} -> HTTP {fr.status_code}")
                except Exception as e:
                    print(f"[HARVEST][warn] XML fetch failed {pmcid}: {e}")

                # Convert JATS to plain text; if XML is missing, fall back to title+abstract.
                if xml_text:
                    plain = jats_body_to_text(xml_text)
                else:
                    abstr = (rec.get("abstractText") or "").strip()
                    plain = _normalize_ws(f"{title}. {abstr}")

                obj["xml"] = xml_text if SAVE_XML else ""
                obj["plain_text"] = plain

                # ----------------------- Write out JSON file ----------------------
                # File name policy: use PMCID (stable) so /index/batch will also use it as doc_id.
                out_path = os.path.join(PAPERS_DIR, f"{pmcid}.json")
                try:
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(obj, f, ensure_ascii=False, indent=2)
                    harvested += 1
                except Exception as e:
                    print(f"[HARVEST][error] write {out_path}: {e}")

                # Stop immediately when cap is reached
                if harvested >= MAX_HARVEST:
                    print(f"[HARVEST] Reached MAX_HARVEST={MAX_HARVEST}. Stopping.")
                    return {"status": "ok", "harvested": harvested, "note": "max cap reached"}

            # Stop when the cursor doesn't advance anymore (no further pages).
            if not next_cursor or next_cursor == cursor_mark:
                break
            cursor_mark = next_cursor
    # ----------------------------------------------------------------------

    print(f"[HARVEST] Done. harvested={harvested}")
    return {"status": "ok", "harvested": harvested}
