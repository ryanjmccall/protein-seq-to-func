# pipeline/02_corpus_manager.py
import sqlite3
import os
from pipeline.config import CORPUS_DIR, SQLITE_DB_PATH

def manage_corpus_index():
    """
    Scans the corpus directory for data and upserts into the SQLite index.
    """
    print("Step 2: Managing corpus index...")
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS papers (pmcid TEXT PRIMARY KEY, path TEXT)")
    
    for filename in os.listdir(CORPUS_DIR):
        if filename.endswith(".json"):
            pmcid = filename.split('.')[0]
            path = os.path.join(CORPUS_DIR, filename)
            cursor.execute("INSERT OR REPLACE INTO papers (pmcid, path) VALUES (?, ?)", (pmcid, path))

    conn.commit()
    conn.close()
    print(f" -> Updated SQLite index at {SQLITE_DB_PATH}")
    