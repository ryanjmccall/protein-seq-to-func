import httpx
from fastapi import FastAPI
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    nebius_api_key: str
    
    class Config:
        env_file = ".env"

settings = Settings()

# If you already declared `app = FastAPI(...)` above, do NOT duplicate this line.
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
