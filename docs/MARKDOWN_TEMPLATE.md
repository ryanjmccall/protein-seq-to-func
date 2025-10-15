# Protein Article Markdown Template

This document provides the markdown template format for generating protein articles from the backend. The frontend will parse this markdown and render it in the WikiCrow-style interface.

## File Format

Each protein article should be a JSON file with markdown content embedded. The structure follows the `ProteinArticle` TypeScript type.

## JSON Structure

```json
{
  "protein": {
    "uniprot_id": "Q14697",
    "name": "GANAB",
    "sequence": "MKKL...",
    "family": "Glucosidase II alpha subunit",
    "gene": {
      "gene_id": "ENSG00000089597",
      "symbol": "GANAB",
      "organism": "Homo sapiens",
      "aliases": ["G2AN", "GIIA", "GIIalpha", "GLUII", "PKD3"],
      "chromosome": "11",
      "start": 62414104,
      "end": 62392298,
      "strand": "-1"
    },
    "structure_pdb_id": "7DBA"
  },
  "overview": {
    "summary": "Long-form description of the protein...",
    "key_functions": [
      "Function 1",
      "Function 2"
    ]
  },
  "structure": {
    "primary": "Description of primary structure...",
    "secondary": "Description of secondary structure...",
    "tertiary": "Description of tertiary structure...",
    "quaternary": "Description of quaternary structure...",
    "domains": ["Domain 1", "Domain 2"],
    "post_translational_modifications": [
      "PTM description 1",
      "PTM description 2"
    ]
  },
  "functions": {
    "general_description": "Overall functional description...",
    "modifications_to_functions": [
      {
        "modification": {
          "id": "mod1",
          "location": "Position 123",
          "type": "Phosphorylation",
          "description": "Optional description"
        },
        "function": {
          "id": "func1",
          "description": "Enhanced catalytic activity",
          "type": "Enzymatic Activity",
          "pathway": "N-glycan processing"
        },
        "publications": [
          {
            "pmid": "12345678",
            "title": "Study title",
            "doi": "10.1234/example",
            "year": 2023
          }
        ],
        "evidence_level": "Strong"
      }
    ]
  },
  "clinical_significance": {
    "description": "Clinical relevance and aging context...",
    "conditions": [
      {
        "condition": "Disease name",
        "variant_location": "Exon 5",
        "variant_type": "Missense",
        "phenotype": "Disease phenotype description",
        "age_related": true,
        "onset_age": "30-50 years",
        "publications": [
          {
            "pmid": "87654321",
            "title": "Clinical study title"
          }
        ]
      }
    ]
  },
  "interactions": {
    "small_molecules": [
      {
        "small_molecule": {
          "name": "Compound Name",
          "pubchem_id": "12345",
          "chembl_id": "CHEMBL123",
          "smiles": "C1=CC=CC=C1"
        },
        "interaction_type": "Inhibitor",
        "binding_site": "Active site",
        "kd_value": "5.2 nM",
        "ic50_value": "10.3 μM",
        "effect_on_function": "Reduces enzymatic activity",
        "publications": [
          {
            "pmid": "11111111",
            "title": "Drug interaction study"
          }
        ]
      }
    ],
    "protein_partners": [
      {
        "partner_protein": {
          "uniprot_id": "P12345",
          "name": "Partner protein name",
          "sequence": ""
        },
        "interaction_type": "Binding partner",
        "complex_name": "Protein complex name",
        "publications": [
          {
            "pmid": "22222222",
            "title": "Protein interaction study"
          }
        ]
      }
    ]
  },
  "references": [
    {
      "pmid": "12345678",
      "title": "Full reference title",
      "doi": "10.1234/example",
      "year": 2023
    }
  ]
}
```

## Field Descriptions

### Protein Information
- **uniprot_id**: UniProt accession (required)
- **name**: Protein name (required)
- **sequence**: Full amino acid sequence (optional for display)
- **family**: Protein family classification
- **gene**: Gene information object (optional)
  - **gene_id**: Ensembl gene ID
  - **symbol**: Official gene symbol
  - **organism**: Species name
  - **aliases**: Array of alternative gene names
  - **chromosome**: Chromosome number
  - **start/end**: Genomic coordinates
  - **strand**: "1" or "-1"
- **structure_pdb_id**: PDB ID for 3D structure (optional)

### Overview Section
- **summary**: Rich text description of the protein (can be multiple paragraphs)
- **key_functions**: Array of main functional bullet points

### Structure Section
- **primary**: Primary structure description
- **secondary**: Secondary structure (alpha helices, beta sheets)
- **tertiary**: 3D folding description
- **quaternary**: Complex formation description
- **domains**: Array of domain names
- **post_translational_modifications**: Array of PTM descriptions

### Functions Section (KEY for sequence-to-function)
- **general_description**: Overview of protein function
- **modifications_to_functions**: Array of modification-to-function relationships
  - Each entry represents: MODIFICATION → FUNCTION relationship
  - **modification.location**: Where the modification occurs (e.g., "Position 123", "Residue Ser456")
  - **modification.type**: Type of modification (e.g., "Phosphorylation", "Glycosylation", "Acetylation")
  - **function.description**: What functional change results from this modification
  - **function.type**: Category of function (e.g., "Enzymatic Activity", "Binding", "Signaling")
  - **function.pathway**: Related biological pathway
  - **publications**: Array of supporting publications (PMID required)

### Clinical Significance Section
- **description**: Overview of clinical relevance and aging
- **conditions**: Array of disease/condition associations
  - **condition**: Disease name
  - **variant_location**: Genomic/protein location of variant
  - **variant_type**: Type of mutation
  - **phenotype**: Clinical presentation
  - **age_related**: Boolean - is this age-related?
  - **onset_age**: When symptoms typically appear
  - **publications**: Supporting publications

### Interactions Section (KEY for small molecules)
- **small_molecules**: Array of compound interactions
  - **small_molecule.name**: Compound name
  - **small_molecule.pubchem_id**: PubChem CID (for linking)
  - **interaction_type**: "Inhibitor", "Activator", "Substrate", etc.
  - **binding_site**: Where the compound binds
  - **kd_value**: Dissociation constant (with units)
  - **ic50_value**: Half-maximal inhibitory concentration (with units)
  - **effect_on_function**: Functional consequence
  - **publications**: Supporting publications

- **protein_partners**: Array of protein-protein interactions
  - Similar structure to small molecules but for protein partners

### References
Complete list of all publications cited in the article, with PMID, title, DOI, and year.

## Graph Database Query Mapping

### To generate the Functions section from Neo4j:

```cypher
MATCH (p:Protein {uniprot_id: $uniprot_id})-[:HAS_MODIFICATION]->(m:Modification)
MATCH (m)-[:RESULTS_IN]->(f:Function)
MATCH (m)-[:CITED_IN]->(pub:Publication)
RETURN m.location, m.type, f.description, f.type, f.pathway,
       collect({pmid: pub.pmid, title: pub.title}) as publications
```

### To generate the Interactions section from Neo4j:

```cypher
MATCH (p:Protein {uniprot_id: $uniprot_id})<-[:TARGETS]-(sm:SmallMolecule)
MATCH (sm)-[:CITED_IN]->(pub:Publication)
RETURN sm.name, sm.pubchem_id, sm.interaction_type,
       sm.effect, sm.ic50, sm.kd,
       collect({pmid: pub.pmid, title: pub.title}) as publications
```

## File Naming Convention

Save each protein article as: `{uniprot_id}.json`
Example: `Q14697.json`

## Notes for Backend Team

1. **Always include PMIDs** for citations - the frontend will automatically link to PubMed
2. **Be specific with locations** - Use formats like "Position 123" or "Residue Ser456"
3. **Include units** - For IC50, Kd values, always include units (μM, nM, etc.)
4. **Rich text formatting** - The summary fields support line breaks and paragraphs
5. **Sequence-to-function is key** - The modifications_to_functions array is the core feature
6. **Small molecules need IDs** - PubChem IDs enable automatic linking
7. **Age-related data** - Flag conditions as age_related when relevant for the aging challenge

## Example API Endpoint

The frontend will fetch data from:
```
GET /api/protein/{uniprot_id}
```

Returns the JSON structure described above.
