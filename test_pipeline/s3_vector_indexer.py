from llama_index.core import SimpleDirectoryReader
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
import chromadb
from config import CORPUS_DIR, CHROMA_DB_PATH

def create_vector_index() -> VectorStoreIndex:
    """
    SKELETON: Loads documents and indexes them in ChromaDB. It uses a default,
    local embedding model instead of calling the Nebius API to save time and cost.
    """
    print("Step 3: Creating vector index (skeleton)...")
    documents = SimpleDirectoryReader(CORPUS_DIR).load_data()
    
    db = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    chroma_collection = db.get_or_create_collection("main_collection")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # This will use a default, fast, local embedding model
    index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)

    # TODO: Configure LlamaIndex to use the Nebius API endpoint
    # TODO: use OpenAI instead of Nebius?
    # embed_model = OpenAIEmbedding(
    #     model="BAAI/bge-en-icl",  # The specific model slug from Nebius
    #     api_base="https://api.studio.nebius.com/v1",
    #     api_key="YOUR_NEBIUS_API_KEY"
    # )
    # index = VectorStoreIndex.from_documents(
    #     documents,
    #     storage_context=storage_context,
    #     embed_model=embed_model # <-- Explicitly use the Nebius model
    # )
    # An embedding model is an AI that acts as a translator, converting 
    # unstructured text into a structured list of numbers called a vector. 
    # This vector captures the text's semantic meaning as a coordinate in a 
    # high-dimensional space, where concepts with similar meanings are located 
    # close to one another. Under the hood, this is a neural network (typically 
    # a Transformer) that has been trained on vast amounts of text. By learning 
    # to predict words in context, it creates a lookup table where each word or 
    # phrase can be mapped to a dense vector, allowing for mathematical comparisons 
    # of meaning using techniques like cosine similarity.

    # When you execute the from_documents step, a specific process unfolds between 
    # your local machine and the Nebius API. First, LlamaIndex breaks your documents 
    # into smaller text chunks on your machine. Then, for each chunk, it makes an API 
    # call to Nebius, where the heavy computation of turning that text into a vector 
    # happens on their powerful servers. Nebius then sends back only the resulting small 
    # vector, and LlamaIndex takes this vector and the original text chunk and stores 
    # them in your local ChromaDB database. The final, searchable index is built and 
    # resides entirely on your machine; Nebius's role is simply to act as a remote 
    # "vector factory," performing the intensive calculations for you

    print(f" -> Indexed documents in ChromaDB at {CHROMA_DB_PATH}")
    return index
