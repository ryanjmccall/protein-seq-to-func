import os
import json
from pipeline.config import CORPUS_DIR

def build_corpus():
    """
    SKELETON: Instead of calling Europe PMC, this creates fake JSON files
    to simulate the output of the corpus building step.

    FUNCTION: Calls hard-coded databases and dumps the response to local disk.
    """
    print("Step 1: Building corpus (skeleton)...")
    os.makedirs(CORPUS_DIR, exist_ok=True)
    
    # Create a fake paper for SIRT6
    fake_paper = {
        "pmcid": "PMC123456",
        "title": "A study on SIRT6",
        "plain_text": "The SIRT6-cen variant, characterized by an Asn308Lys substitution, showed increased deacetylase activity."
    }
    with open(f"{CORPUS_DIR}/PMC123456.json", 'w') as f:
        json.dump(fake_paper, f)
    print(" -> Created 1 fake paper JSON.")