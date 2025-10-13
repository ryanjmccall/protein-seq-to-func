# filename: simple_llamaindex_demo.py
# Description: A minimal LlamaIndex script demonstrating RAG without using pandas.

import os
import csv
from llama_index.core import Document, VectorStoreIndex

# --- 1. SETUP ---
if "OPENAI_API_KEY" not in os.environ:
    raise EnvironmentError("OPENAI_API_KEY environment variable not set.")

csv_file_path = "data/raw/genage_human.csv"

if not os.path.exists(csv_file_path):
    raise FileNotFoundError(f"File not found: {csv_file_path}")

# --- 2. LOAD DATA (Manually) ---
# Here we read the CSV row by row and create Document objects ourselves.
documents = []
with open(csv_file_path, mode='r', encoding='utf-8') as file:
    # Use Python's built-in CSV reader
    csv_reader = csv.reader(file)
    header = next(csv_reader)  # Skip the header row

    for row in csv_reader:
        # For each row, combine the relevant columns into a single text string.
        # This string is what the LLM will actually "read".
        text_content = (
            f"Gene Symbol: {row[1]}, "
            f"Full Name: {row[2]}, "
            f"Reason for Inclusion: {row[5]}"
        )

        # Create a LlamaIndex Document object. This is the fundamental unit.
        # We can also add the original row data as metadata for later use.
        doc = Document(
            text=text_content,
            metadata={"gene_symbol": row[1], "genage_id": row[0]}
        )
        documents.append(doc)

print(f"✅ Manually loaded and created {len(documents)} Document objects.")

# --- 3. INDEX DATA ---
# This part is the same. LlamaIndex takes our list of Document objects
# and builds the searchable vector index.
print("\nBuilding the index...")
index = VectorStoreIndex.from_documents(documents)
print("✅ Index created successfully.")

# --- 4. CREATE QUERY ENGINE & ASK A QUESTION ---
query_engine = index.as_query_engine()
question = "What is the full name of the gene with the symbol SIRT6?"

print(f"\n❓ Asking question: {question}")
response = query_engine.query(question)

print("\n💡 Answer:")
print(response)
