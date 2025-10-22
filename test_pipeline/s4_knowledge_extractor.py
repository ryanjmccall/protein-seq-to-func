import markdown
import os
from types import SimpleNamespace
from pathlib import Path

import os
import json
from llama_index.llms.nebius import NebiusLLM
from llama_index.core.llms import ChatMessage

from dotenv import load_dotenv


MODEL = "openai/gpt-oss-120b"

# Assumed input chunks from chromadb
STUB_CONTEXT_CHUNKS = [
    "A rare human centenarian variant of SIRT6 (SIRT6-cen) enhances genome stability...",
    "The SIRT6-cen variant, characterized by an Asn308Lys substitution, showed increased deacetylase activity...",
    "Furthermore, SIRT6-cen demonstrated a stronger interaction with Lamin A, a key component of the nuclear lamina.",
]

STUB_STUCTURED_DATA = {
    "protein_info": {
        "symbol": "GANAB",
        "full_name": "Glucosidase II Alpha Subunit",
        "uniprot_id": "Q14697",
        "family": "Glucosidase II alpha subunit",
    },
    "gene_info": {
        "symbol": "GANAB",
        "gene_id": "ENSG00000089597",
        "organism": "Homo sapiens",
        "chromosome": "11",
    },
    "overview": "GANAB encodes the catalytic alpha subunit...",
    "key_functions": [
        "Catalytic trimming...",
        "Coordination of the calnexin/calreticulin cycle...",
    ],
    "modifications": [
        {
            "modification_id": "mod-1",
            "location": "Asn123",
            "type": "Glycosylation",
            "description": "N-linked glycan addition stabilizes luminal folding intermediates",
            "function_description": "Stabilizes the catalytic core...",
            "publication_pmid": "22022391",
        },
        {
            "modification_id": "mod-2",
            "location": "Ser456",
            "type": "Phosphorylation",
            "description": "Casein kinase phosphorylation reported during ER stress",
            "function_description": "Tunes catalytic turnover...",
            "publication_pmid": "20204020",
        },
    ],
    "clinical_significance": [
        {
            "condition_name": "Autosomal Dominant Polycystic Kidney Disease (ADPKD)",
            "variant_info": "Exon 15 Missense mutation",
            "phenotype": "Progressive kidney cyst formation...",
            "publication_pmid": "22022391",
        }
    ],
    "small_molecule_interactions": [
        {
            "molecule_name": "Deoxynojirimycin (DNJ)",
            "interaction_type": "Inhibitor",
            "effect": "Competitive inhibition...",
            "publication_pmid": "12345678",
        }
    ],
    "protein_partners": [
        {
            "partner_symbol": "PRKCSH",
            "interaction_type": "Binding partner",
            "publication_pmid": "11111111",
        }
    ],
}

SCIENTIST_TEMPLATE = """You are a highly specialized scientific data extraction assistant. Based ONLY on the following text context from scientific literature, extract comprehensive information about the specified protein. Return the data as a single, valid JSON object following this exact schema:

    {
    "protein_info": {"symbol": "...", "full_name": "...", "uniprot_id": "...", "family": "..."},
    "gene_info": {"symbol": "...", "gene_id": "...", "organism": "...", "chromosome": "..."},
    "overview": "...",
    "key_functions": ["...", "..."],
    "modifications": [{"modification_id": "...", "location": "...", "type": "...", "description": "...", "function_description": "...", "publication_pmid": "..."}, ...],
    "clinical_significance": [{"condition_name": "...", "variant_info": "...", "phenotype": "...", "publication_pmid": "..."}, ...],
    "small_molecule_interactions": [{"molecule_name": "...", "interaction_type": "...", "effect": "...", "publication_pmid": "..."}, ...],
    "protein_partners": [{"partner_symbol": "...", "interaction_type": "...", "publication_pmid": "..."}, ...]
    }

    Fill in all fields based *strictly* on the provided context. If information for a field is not present, use `null` or an empty list/object as appropriate for the schema. Do not infer information not present in the text.

    Context:
    ---
    {context_chunks}
    ---

    JSON Output:
    """


def extract_and_synthesize(index, protein_name: str) -> str:
    """
    SKELETON: Simulates the two-step Nebius LLM call.
    1. Retrieves context from the vector index.
    2. Returns a hardcoded JSON for the extraction step.
    3. Uses a simple f-string for the synthesis step.
    """
    print("Step 4 & 5: Extracting and synthesizing knowledge (skeleton)...")

    # Step 1: Retrieve context (this part is real)
    try:
        query_engine = index.as_query_engine()
        retrieved = query_engine.query(f"What is the function of {protein_name}?")
        print(f" -> Retrieved context: '{retrieved.source_nodes[0].text[:50]}...'")
    except AttributeError:
        print(" -> (Skipped retrieval for mock index)")

    # Step 2: Fake the first LLM call (extraction)
    # structured_data = {
    #     "modification_name": "Asn308Lys",
    #     "functional_outcome": "Increases deacetylase activity.",
    # }
    # print(f" -> Simulated structured data extraction: {structured_data}")


    # The "Scientist"
    # TODO: using the context_chunks, and template, query the LLM to produce structured_data.

    final_article = write_article(STUB_STUCTURED_DATA)

    # (In a real implementation, you would store this article in the SQLite DB)
    save_article_as_md(protein_name=protein_name, final_article=final_article)


def save_article_as_md(protein_name: str, final_article: str):
    """
    Saves the article Markdown string to a .md file.
    """
    print(f"Saving article to Markdown file...")
    output_path = f"data/processed/{protein_name}_article.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(str(final_article))

    print(f" -> Generated {output_path}")

TEMPLATE_PATH = "test_pipeline/templates/article.md"

def load_markdown_template() -> str:
    # Define the path to your template file using pathlib for cross-platform compatibility
    template_path = Path(TEMPLATE_PATH)
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            markdown_template_string = f.read()
        # print(markdown_template_string[:100]) # Print the first 100 characters to check
        return markdown_template_string
    except FileNotFoundError:
        print(f"Error: Template file not found at {template_path}")
    except Exception as e:
        print(f"An error occurred: {e}")


def write_article(structured_data: dict) ->str:
    load_dotenv()  # best practice: store the API key in .env file at repo root
    llm = NebiusLLM(model=MODEL, api_key=os.getenv("NEBIUS_API_KEY"))

    WRITER_SYSTEM_CONTENT = """You are a scientific writer creating a detailed 
    wiki article in Markdown format about a specific protein, based ONLY on 
    the structured JSON information provided. Follow the specified Markdown 
    structure precisely. Generate complete sections based on the template."""

    structured_data_json_string = json.dumps(structured_data, indent=2)
    markdown_template_string = load_markdown_template()
    user_content = f"""JSON Information:
    ```json
    {structured_data_json_string}
    ```

    Markdown Output Structure:

    ```markdown {markdown_template_string}
    ```
    """

    messages = [
        ChatMessage(role="system", content=WRITER_SYSTEM_CONTENT),
        ChatMessage(role="user", content=user_content),
    ]

    print(">>> Sending Writer chat to LLM...")
    response = llm.chat(messages)  # OpenAI api
    content = response.message.content
    print("\n>>> Got LLM Article Response content\n", str(content))
    return content


if __name__ == "__main__":
    write_article(STUB_STUCTURED_DATA)
