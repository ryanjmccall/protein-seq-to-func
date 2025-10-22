# FastAPI

## Quick start (Windows/PowerShell)
- Prereqs: Python 3.11+ installed
- Get code and enter folder:
  - cd backend
- Create and activate venv:
  - python -m venv venv_311
  - .\venv_311\Scripts\activate
- Install deps:
  - pip install -r requirements.txt
- Configure API key (Nebius):
  - Create a file `.env` in this folder with:
    - nebius_api_key=YOUR_API_KEY

## Quick Start (macOS)

This project's dependencies are managed with `conda` via the `environment.yml` file, which is located in the repository root.

1.  **Create the Environment**
    This command builds the environment specified in the file.
    ```bash
    conda env create -f environment.yml
    ```
    *Pro-tip: For a much faster installation, use `mamba`: `mamba env create -f environment.yml`*

2.  **Activate the Environment**
    You must activate the environment to use the installed packages.
    ```bash
    conda activate <environment_name>
    ```
    *(Note: The `<environment_name>` is defined by the `name:` key inside the `environment.yml` file. You must use that specific name here.)*

## Run the server
- Start:
  - uvicorn app:app --host 127.0.0.1 --port 8000 --reload
- Swagger UI:
  - http://127.0.0.1:8000/docs

## Data locations
- Input JSON papers folder:
  - backend\papers\
- Outputs:
  - FAISS index: backend\faiss_store\index.faiss (+ meta.jsonl)
  - Articles (HTML): backend\faiss_store\articles\

## Endpoints (use via Swagger)
- Optional: harvest protein papers (creates JSONs in `papers/`)
  - GET /harvest/{protein_name}
- Full pipeline (index all in batches, then generate article)
  - POST /index/run_all
  - Params: batch_size (e.g., 1000), protein_name (e.g., APOE), query (optional), top_k (e.g., 10)

## Notes
- Swagger usage: open /docs, expand the endpoint, set params, click “Try it out” → “Execute”.
