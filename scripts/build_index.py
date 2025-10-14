# filename: data_ingestion_tool.py
# Description: A comprehensive data ingestion tool that builds ChromaDB indexes from multiple sources.

import os
import csv
import httpx
import json
import re
from typing import List, Dict, Any, Optional
from llama_index.core import Document, VectorStoreIndex, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb
from chromadb.config import Settings

# --- 1. SETUP ---
if "OPENAI_API_KEY" not in os.environ:
    raise EnvironmentError("OPENAI_API_KEY environment variable not set.")

# Europe PMC API endpoints
EPMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EPMC_FULLTEXT_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"

# ChromaDB setup
CHROMA_PERSIST_DIR = "./chroma_db"
COLLECTION_NAME = "protein_research_index"

def setup_chromadb():
    """Initialize ChromaDB client and collection."""
    chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
    return collection

def load_genage_data(csv_file_path: str) -> List[Document]:
    """Load GenAge human data from CSV file."""
    documents = []
    
    if not os.path.exists(csv_file_path):
        print(f"⚠️  File not found: {csv_file_path}")
        return documents
    
    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        csv_reader = csv.reader(file)
        header = next(csv_reader)  # Skip the header row
        
        for row in csv_reader:
            if len(row) < 6:  # Ensure we have enough columns
                continue
                
            text_content = (
                f"Gene Symbol: {row[1]}, "
                f"Full Name: {row[2]}, "
                f"Reason for Inclusion: {row[5]}"
            )
            
            doc = Document(
                text=text_content,
                metadata={
                    "gene_symbol": row[1],
                    "genage_id": row[0],
                    "source": "genage",
                    "full_name": row[2],
                    "reason": row[5]
                }
            )
            documents.append(doc)
    
    print(f"✅ Loaded {len(documents)} GenAge documents")
    return documents

def load_uniprot_data(csv_file_path: str) -> List[Document]:
    """Load UniProt sequence data from CSV file."""
    documents = []
    
    if not os.path.exists(csv_file_path):
        print(f"⚠️  File not found: {csv_file_path}")
        return documents
    
    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        csv_reader = csv.reader(file)
        header = next(csv_reader)  # Skip the header row
        
        for row in csv_reader:
            if len(row) < 3:  # Ensure we have enough columns
                continue
                
            # Truncate sequence for display (keep first 100 chars)
            sequence_preview = row[2][:100] + "..." if len(row[2]) > 100 else row[2]
            
            text_content = (
                f"UniProt ID: {row[0]}, "
                f"Protein Name: {row[1]}, "
                f"Sequence (preview): {sequence_preview}"
            )
            
            doc = Document(
                text=text_content,
                metadata={
                    "uniprot_id": row[0],
                    "protein_name": row[1],
                    "source": "uniprot",
                    "sequence_length": len(row[2]),
                    "full_sequence": row[2]  # Store full sequence in metadata
                }
            )
            documents.append(doc)
    
    print(f"✅ Loaded {len(documents)} UniProt documents")
    return documents

def search_europepmc(protein: str, page_size: int = 25, open_access_only: bool = True) -> List[Dict[str, Any]]:
    """Search Europe PMC for articles related to a protein."""
    try:
        # Build query with optional open access restriction
        query_parts = [f'TEXT:"{protein}"']
        if open_access_only:
            query_parts.append("OPEN_ACCESS:Y")
        
        query = " AND ".join(query_parts)
        
        params = {
            "query": query,
            "resultType": "core",
            "format": "json",
            "pageSize": str(page_size),
            "sort": "CITED desc",
            "synonym": "Y",
        }

        print(f"[EPMC SEARCH] Searching for: {protein}")
        with httpx.Client(timeout=60) as client:
            r = client.get(EPMC_SEARCH_URL, params=params)
        
        if r.status_code != 200:
            print(f"[EPMC SEARCH] Error: HTTP {r.status_code}")
            return []

        data = r.json()
        results = (data.get("resultList") or {}).get("result") or []
        
        print(f"✅ Found {len(results)} Europe PMC articles for {protein}")
        return results
        
    except Exception as e:
        print(f"[EPMC SEARCH] Error: {e}")
        return []

def get_europepmc_fulltext(pmcid: str) -> Optional[Dict[str, Any]]:
    """Download full-text XML from Europe PMC."""
    try:
        if not pmcid.startswith("PMC"):
            print(f"[EPMC FULLTEXT] Invalid PMCID format: {pmcid}")
            return None
        
        url = f"{EPMC_FULLTEXT_BASE}/{pmcid}/fullTextXML"
        
        with httpx.Client(timeout=60) as client:
            r = client.get(url)
        
        if r.status_code == 404:
            print(f"[EPMC FULLTEXT] Article not found: {pmcid}")
            return None
        elif r.status_code != 200:
            print(f"[EPMC FULLTEXT] Error: HTTP {r.status_code}")
            return None

        xml_text = r.text or ""
        
        # Basic XML parsing to extract key information
        title_match = re.search(r'<article-title[^>]*>(.*?)</article-title>', xml_text, re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""
        
        # Extract abstract
        abstract_match = re.search(r'<abstract[^>]*>(.*?)</abstract>', xml_text, re.DOTALL)
        abstract = ""
        if abstract_match:
            abstract_text = abstract_match.group(1)
            abstract = re.sub(r'<[^>]+>', '', abstract_text).strip()
        
        # Extract authors
        authors = []
        author_matches = re.findall(r'<contrib[^>]*contrib-type="author"[^>]*>.*?<string-name[^>]*>(.*?)</string-name>', xml_text, re.DOTALL)
        for author in author_matches:
            clean_author = re.sub(r'<[^>]+>', '', author).strip()
            if clean_author:
                authors.append(clean_author)
        
        return {
            "pmcid": pmcid,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "xml_content": xml_text
        }
        
    except Exception as e:
        print(f"[EPMC FULLTEXT] Error: {e}")
        return None

def load_europepmc_data(proteins: List[str], max_articles_per_protein: int = 5) -> List[Document]:
    """Load Europe PMC data for multiple proteins."""
    documents = []
    
    for protein in proteins:
        print(f"\n🔍 Searching Europe PMC for {protein}...")
        articles = search_europepmc(protein, page_size=max_articles_per_protein)
        
        for article in articles:
            # Create document from article metadata
            text_content = f"Title: {article.get('title', '')}\n"
            text_content += f"Abstract: {article.get('abstractText', '')}\n"
            text_content += f"Authors: {article.get('authorString', '')}\n"
            text_content += f"Journal: {article.get('journalTitle', '')} ({article.get('pubYear', '')})\n"
            
            doc = Document(
                text=text_content,
                metadata={
                    "source": "europepmc",
                    "protein": protein,
                    "title": article.get('title', ''),
                    "authors": article.get('authorString', ''),
                    "journal": article.get('journalTitle', ''),
                    "year": article.get('pubYear'),
                    "doi": article.get('doi'),
                    "pmcid": article.get('pmcid'),
                    "pmid": article.get('pmid'),
                    "is_open_access": article.get('isOpenAccess', False),
                    "citation_count": article.get('citedByCount', 0)
                }
            )
            documents.append(doc)
            
            # Optionally get full text for high-impact articles
            if (article.get('citedByCount', 0) > 50 and 
                article.get('pmcid') and 
                article.get('isOpenAccess')):
                
                print(f"  📄 Getting full text for highly cited article: {article.get('pmcid')}")
                fulltext = get_europepmc_fulltext(article.get('pmcid'))
                if fulltext:
                    # Create additional document with full text
                    fulltext_doc = Document(
                        text=f"Full Text - {fulltext['title']}\n\n{fulltext['abstract']}",
                        metadata={
                            "source": "europepmc_fulltext",
                            "protein": protein,
                            "pmcid": fulltext['pmcid'],
                            "title": fulltext['title'],
                            "authors": ", ".join(fulltext['authors']) if fulltext['authors'] else "",
                            "content_type": "full_text"
                        }
                    )
                    documents.append(fulltext_doc)
    
    print(f"✅ Loaded {len(documents)} Europe PMC documents")
    return documents

def build_index(documents: List[Document], use_chromadb: bool = True) -> VectorStoreIndex:
    """Build vector index from documents, optionally using ChromaDB."""
    if use_chromadb:
        print("\n🗄️  Building index with ChromaDB persistence...")
        collection = setup_chromadb()
        vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
        print("✅ Index built and stored in ChromaDB")
    else:
        print("\n🔨 Building in-memory index...")
        index = VectorStoreIndex.from_documents(documents)
        print("✅ In-memory index built")
    
    return index

def load_index_from_chromadb() -> Optional[VectorStoreIndex]:
    """Load existing index from ChromaDB."""
    try:
        collection = setup_chromadb()
        vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)
        print("✅ Index loaded from ChromaDB")
        return index
    except Exception as e:
        print(f"⚠️  Could not load index from ChromaDB: {e}")
        return None

def test_query_engine(query_engine, test_questions: List[str]):
    """Test the query engine with multiple questions."""
    print("\n🧪 Testing Query Engine:")
    print("=" * 50)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n❓ Question {i}: {question}")
        try:
            response = query_engine.query(question)
            print(f"💡 Answer: {response}")
        except Exception as e:
            print(f"❌ Error: {e}")
        print("-" * 30)

def main():
    """Main function to orchestrate the data ingestion and indexing process."""
    print("🚀 Starting Protein Research Data Ingestion Tool")
    print("=" * 60)
    
    # Step 1: Load data from multiple sources
    all_documents = []
    
    # Load GenAge data
    print("\n📊 Loading GenAge data...")
    genage_docs = load_genage_data("data/raw/genage_human.csv")
    all_documents.extend(genage_docs)
    
    # Load UniProt data
    print("\n🧬 Loading UniProt data...")
    uniprot_docs = load_uniprot_data("data/raw/uniprot_sequences.csv")
    all_documents.extend(uniprot_docs)
    
    # Load Europe PMC data for key proteins
    print("\n📚 Loading Europe PMC data...")
    key_proteins = ["CCR1", "CCR2", "CCR5", "CCR7", "NRF2", "APOE", "SOX2", "OCT4"]  # Example proteins
    europepmc_docs = load_europepmc_data(key_proteins, max_articles_per_protein=3)
    all_documents.extend(europepmc_docs)
    
    print(f"\n📈 Total documents loaded: {len(all_documents)}")
    
    if not all_documents:
        print("❌ No documents loaded. Exiting.")
        return
    
    # Step 2: Test in-memory index first
    print("\n" + "="*60)
    print("🧪 PHASE 1: Testing in-memory index")
    print("="*60)
    
    in_memory_index = build_index(all_documents, use_chromadb=False)
    in_memory_query_engine = in_memory_index.as_query_engine()
    
    test_questions = [
        "What are the full names of the genes with symbols NRF2, SOX2, APOE, OCT4?",
        "What proteins are related to longevity and aging?",
        "What are the most cited research findings about CCR5?",
        "What are the functions of CCR5 protein?",
        "What research has been done on transcription factors like SOX2 and OCT4?"
    ]
    
    test_query_engine(in_memory_query_engine, test_questions)
    
    # Step 3: Build persistent ChromaDB index
    print("\n" + "="*60)
    print("💾 PHASE 2: Building persistent ChromaDB index")
    print("="*60)
    
    chromadb_index = build_index(all_documents, use_chromadb=True)
    chromadb_query_engine = chromadb_index.as_query_engine()
    
    # Step 4: Test ChromaDB index
    print("\n" + "="*60)
    print("🔄 PHASE 3: Testing ChromaDB index")
    print("="*60)
    
    test_query_engine(chromadb_query_engine, test_questions)
    
    # Step 5: Verify persistence by loading from ChromaDB
    print("\n" + "="*60)
    print("🔄 PHASE 4: Verifying ChromaDB persistence")
    print("="*60)
    
    loaded_index = load_index_from_chromadb()
    if loaded_index:
        loaded_query_engine = loaded_index.as_query_engine()
        print("\n🧪 Testing loaded index with same questions...")
        test_query_engine(loaded_query_engine, test_questions[:2])  # Test with subset
    
    print("\n✅ Data ingestion and indexing complete!")
    print(f"📊 Total documents indexed: {len(all_documents)}")
    print(f"💾 ChromaDB collection: {COLLECTION_NAME}")
    print(f"📁 ChromaDB location: {CHROMA_PERSIST_DIR}")

if __name__ == "__main__":
    main()
