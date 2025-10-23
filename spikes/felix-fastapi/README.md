# Felix FastAPI Spike

## Quick start (Windows/PowerShell)
- Prereqs: Python 3.11+ installed
- Get code and enter folder:
  - cd spikes\felix-fastapi
- Create and activate venv:
  - python -m venv venv_311
  - .\venv_311\Scripts\activate
- Install deps:
  - pip install -r requirements.txt
- Configure API key (Nebius):
  - Create a file `.env` in this folder with:
    - nebius_api_key=YOUR_API_KEY

## Run the server
- Start:
  - uvicorn app:app --host 127.0.0.1 --port 8000 --reload
- Swagger UI:
  - http://127.0.0.1:8000/docs


## Data locations
- Input JSON papers folder:
  - spikes\felix-fastapi\papers\
- Outputs:
  - FAISS index: spikes\felix-fastapi\faiss_store\index.faiss (+ meta.jsonl)
  - Articles (HTML): spikes\felix-fastapi\faiss_store\articles\

## Endpoints (use via Swagger)
- Optional: harvest APOE papers (creates JSONs in `papers/`)
  - GET /harvest/apoe
- Full pipeline (index all in batches, then generate article)
  - POST /index/run_all
  - Params: batch_size (e.g., 1000), protein_name (e.g., APOE), query (optional), top_k (e.g., 10)


## Notes
- Swagger usage: open /docs, expand the endpoint, set params, click “Try it out” → “Execute”.



Current workflow to get articles:
1. write the current protein in the harvest_apoe() funktion, save, run it via Swagger (the folder "papers" should be empty before the run)
or alternatively use the json files from corpus and put them in the "papers" folder
2. run "post index/run_all" via Swagger with the following parameters to get html (before starting the function remove existing "faiss_store" folder from the working directory):
batch_size: 500
protein name: <the name of the protein, e.g. CCR7>
query: e.g. "CCR7 polymorphisms affecting human lifespan or aging, not disease-specific"
top_k: 200
top_n: 500
for the rest of the parameters you can leave the default value