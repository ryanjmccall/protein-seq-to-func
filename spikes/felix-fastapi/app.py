import httpx
from fastapi import FastAPI
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    nebius_api_key: str
    
    class Config:
        env_file = ".env"

settings = Settings()

app = FastAPI(title="Felix Spike", version="0.0.1")

# OpenAI-compatible base URL from Nebius Quickstart (documented).
# We keep this constant in code (not secret).
NEBIUS_BASE_URL = "https://api.studio.nebius.com/v1"  # docs: /v1/chat/completions
NEBIUS_MODEL = "openai/gpt-oss-120b"  # inexpensive, open-source model suitable for tests

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

