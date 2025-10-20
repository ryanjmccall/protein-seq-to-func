# build_index.py
from pipeline.config import TARGET_PROTEINS
from pipeline.s1_corpus_builder import build_corpus
from pipeline.s2_corpus_manager import manage_corpus_index
from pipeline.s3_vector_indexer import create_vector_index
from pipeline.s4_knowledge_extractor import extract_and_synthesize


def main():
    """Runs the entire offline pipeline from start to finish."""
    print("--- Starting Offline Pipeline Skeleton ---")
    
    # Step 1: Fetch all source data and store as json files.
    build_corpus()
    
    # Step 2: Index json files in SQLite
    manage_corpus_index()
    
    # Step 3: Create a vector index with LlamaIndex and ChromaDB
    vector_index = create_vector_index()
    
    # Step 4 & 5: Extract and synthesize an html article for each protein. 
    # this involves two LLM calls to Nebius
    for prot in TARGET_PROTEINS:
        extract_and_synthesize(vector_index, prot)

    print("\n--- Offline Pipeline Skeleton Finished Successfully ---")

if __name__ == "__main__":
    main()