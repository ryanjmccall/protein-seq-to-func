# filename: fetch_uniprot.py
# Description: Fetches protein data from UniProt for a given list of gene names.

import requests
import pandas as pd
import time

def fetch_uniprot_data(gene_list: list):
    """
    Fetches protein ID, name, and sequence from UniProt for a list of human gene names.

    Args:
        gene_list (list): A list of official human gene symbols (e.g., ['CCR2', 'KCNB1']).

    Returns:
        pandas.DataFrame: A DataFrame containing the fetched protein data.
    """
    base_url = "https://rest.uniprot.org/uniprotkb/search"
    protein_data = []

    print(f"Fetching data for {len(gene_list)} genes from UniProt...")

    for gene in gene_list:
        query = f'(gene:"{gene}") AND (organism_id:9606)' # 9606 is the taxon ID for Homo sapiens
        params = {
            "query": query,
            "fields": "accession,protein_name,sequence",
            "format": "json",
            "size": 1 # We only want the primary result
        }
        
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            
            data = response.json()
            if data and "results" in data and len(data["results"]) > 0:
                result = data["results"][0]
                protein_info = {
                    "gene_symbol": gene,
                    "uniprot_id": result.get("primaryAccession"),
                    "protein_name": result.get("proteinDescription", {}).get("fullName", {}).get("value"),
                    "sequence": result.get("sequence", {}).get("value")
                }
                protein_data.append(protein_info)
                print(f"  ✅ Found data for {gene}")
            else:
                print(f"  ❌ No result found for {gene}")
            
            time.sleep(0.1) # Be respectful to the API by adding a small delay

        except requests.exceptions.RequestException as e:
            print(f"  An error occurred for gene {gene}: {e}")

    print("\n✅ UniProt fetching complete!")
    return pd.DataFrame(protein_data)

if __name__ == "__main__":
    # --- How to use the script ---
    # Uniprot is the comprehensive and list every protein that exists, 
    # regardless of its function. If a protein is known, it's in UniProt

    # example_genes = ["CCR2", "KCNB1", "GLP1R", "SIRT6", "FOXO3"]

    # C-C Chemokine Receptor Family, implicated in inflammation and immune response
    example_genes = ["CCR1", "CCR2", "CCR5", "CCR7"]

    uniprot_data = fetch_uniprot_data(example_genes)

    if not uniprot_data.empty:
        # Display the results
        print("\n--- Fetched UniProt Data ---")
        print(uniprot_data)

        # Save the data to a CSV file for your notebooks
        output_filename = "data/raw/uniprot_sequences.csv"
        uniprot_data.to_csv(output_filename, index=False)
        print(f"\nData saved to {output_filename}")
