import markdown
import os
from types import SimpleNamespace

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
    structured_data = {
        "modification_name": "Asn308Lys",
        "functional_outcome": "Increases deacetylase activity."
    }
    print(f" -> Simulated structured data extraction: {structured_data}")
    
    # Step 3: Fake the second LLM call (synthesis)
    final_article = f"# {protein_name}\n\nA key modification for {protein_name} is " \
                    f"{structured_data['modification_name']}, which is known to " \
                    f"{structured_data['functional_outcome'].lower()}"
    print(" -> Synthesized fake article.")
    print(final_article)
    
    # (In a real implementation, you would store this article in the SQLite DB)
    save_article_as_html(
        protein_name=protein_name, 
        final_article=final_article
    )
    
def save_article_as_html(protein_name: str, final_article: str):
    """
    Converts a Markdown article string into a styled HTML file.
    """
    print(f"Step 6: Converting article to HTML...")
    
    # --- 1. Convert Markdown String to HTML Fragment ---
    html_content = markdown.markdown(final_article)

    # --- 2. Create a Full HTML Page Template ---
    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{protein_name} Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, 
                         Helvetica, Arial, sans-serif;
            line-height: 1.6;
            background-color: #f4f4f4;
            color: #333;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 800px;
            margin: 2rem auto; /* 'auto' centers the block */
            padding: 2rem;
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }}
        h1 {{
            color: #222;
            border-bottom: 2px solid #eee;
            padding-bottom: 0.5rem;
        }}
        p {{
            font-size: 1.1rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        {html_content}
    </div>
</body>
</html>
"""

    # --- 3. Save the Final HTML to a File ---
    output_path = f'data/processed/{protein_name}_article.html'
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_template)
        
    print(f" -> Generated {output_path}")
