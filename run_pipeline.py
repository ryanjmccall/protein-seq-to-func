# build_index.py
from pipeline.config import TARGET_PROTEINS
from pipeline.s1_corpus_builder import build_corpus
from pipeline.s2_corpus_manager import manage_corpus_index
from pipeline.s3_vector_indexer import create_vector_index
from pipeline.s4_knowledge_extractor import extract_and_synthesize


def main():
    """Runs the entire offline pipeline from start to finish."""
    print("--- Starting Offline Pipeline Skeleton ---")
    
    # Step 1: Create fake paper files
    build_corpus()
    
    # Step 2: Index those files in SQLite
    manage_corpus_index()
    
    # Step 3: Create a vector index in ChromaDB
    vector_index = create_vector_index()
    
    # Step 4 & 5: Extract and synthesize an article for the first target protein
    # We only run for one protein to keep the demo simple
    if TARGET_PROTEINS:
        article = extract_and_synthesize(vector_index, TARGET_PROTEINS[0])
        print("\n--- Final Generated Article ---")
        print(article)

    print("\n--- Offline Pipeline Skeleton Finished Successfully ---")

if __name__ == "__main__":
    main()