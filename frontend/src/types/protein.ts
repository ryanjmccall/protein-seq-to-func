// Core protein and gene types based on the graph database schema

export interface Publication {
  pmid: string;
  title: string;
  doi?: string;
  year?: number;
}

export interface Gene {
  gene_id: string;
  symbol: string;
  organism: string;
  aliases?: string[];
  chromosome?: string;
  start?: number;
  end?: number;
  strand?: '-1' | '1';
}

export interface Protein {
  uniprot_id: string;
  name: string;
  sequence: string;
  family?: string;
  gene?: Gene;
  structure_pdb_id?: string;
}

export interface Modification {
  id: string;
  location: string; // e.g., "Position 123" or "Residue Ser456"
  type: string; // e.g., "Phosphorylation", "Glycosylation", "Acetylation"
  description?: string;
}

export interface Function {
  id: string;
  description: string;
  type: string; // e.g., "Enzymatic Activity", "Binding", "Signaling"
  pathway?: string;
}

export interface SmallMolecule {
  name: string;
  pubchem_id?: string;
  chembl_id?: string;
  smiles?: string;
  interaction_type?: string;
  effect?: string;
}

// Relationship types that connect the nodes
export interface ModificationToFunction {
  modification: Modification;
  function: Function;
  publications: Publication[];
  evidence_level?: string;
}

export interface ProteinSmallMoleculeInteraction {
  small_molecule: SmallMolecule;
  interaction_type: string; // "Inhibitor", "Activator", "Substrate", etc.
  binding_site?: string;
  kd_value?: string; // Dissociation constant
  ic50_value?: string; // Half maximal inhibitory concentration
  effect_on_function?: string;
  publications: Publication[];
}

export interface ProteinProteinInteraction {
  partner_protein: Protein;
  interaction_type: string; // "Binding partner", "Substrate", "Regulator"
  complex_name?: string;
  publications: Publication[];
}

export interface ClinicalSignificance {
  condition: string;
  variant_location?: string;
  variant_type?: string;
  phenotype: string;
  age_related?: boolean;
  onset_age?: string;
  publications: Publication[];
}

// Complete protein article structure
export interface ProteinArticle {
  protein: Protein;
  overview: {
    summary: string;
    key_functions: string[];
  };
  structure: {
    primary?: string;
    secondary?: string;
    tertiary?: string;
    quaternary?: string;
    domains: string[];
    post_translational_modifications?: string[];
  };
  functions: {
    modifications_to_functions: ModificationToFunction[];
    general_description: string;
  };
  clinical_significance: {
    description: string;
    conditions: ClinicalSignificance[];
  };
  interactions: {
    small_molecules: ProteinSmallMoleculeInteraction[];
    protein_partners: ProteinProteinInteraction[];
  };
  references: Publication[];
}
