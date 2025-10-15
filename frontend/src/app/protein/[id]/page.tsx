'use client';

import { useState } from 'react';
// import { useParams } from 'next/navigation';
import Sidebar from '@/components/layout/Sidebar';
import SectionTabs, { Section } from '@/components/layout/SectionTabs';
import Overview from '@/components/sections/Overview';
import Structure from '@/components/sections/Structure';
import Function from '@/components/sections/Function';
import ClinicalSignificance from '@/components/sections/ClinicalSignificance';
import Interactions from '@/components/sections/Interactions';
import References from '@/components/sections/References';
import { ProteinArticle } from '@/types/protein';

// Mock data for demonstration - will be replaced with API call
const mockProteinData: ProteinArticle = {
  protein: {
    uniprot_id: 'Q14697',
    name: 'GANAB',
    sequence: 'MKKL...',
    family: 'Glucosidase II alpha subunit',
    gene: {
      gene_id: 'ENSG00000089597',
      symbol: 'GANAB',
      organism: 'Homo sapiens',
      aliases: ['G2AN', 'GIIA', 'GIIalpha', 'GLUII', 'PKD3'],
      chromosome: '11',
      start: 62414104,
      end: 62392298,
      strand: '-1',
    },
    structure_pdb_id: '5DKX',
  },
  overview: {
    summary: `The GANAB gene encodes the glucosidase II alpha subunit (GIIα), a critical component of the glucosidase II enzyme complex, which is involved in the processing of N-linked glycoproteins within the endoplasmic reticulum. This enzyme plays a pivotal role in the N-glycan processing pathway, facilitating the proper folding and quality control of glycoproteins by trimming glucose residues from high-mannose N-glycans. The GIIα subunit, characterized by its β α δ barrel domain and C-terminal domain, interacts with the beta subunit encoded by the PRKCSH gene to form a functional enzyme complex. Additionally, GIIα is involved in calcium signaling through its interaction with the STIM1 protein. Mutations in GANAB are associated with genetic disorders such as autosomal dominant polycystic kidney disease (ADPKD) and polycystic liver disease, underscoring its significance in human physiology and disease.`,
    key_functions: [
      'N-glycan processing and trimming of glucose residues from glycoproteins',
      'Protein quality control in the endoplasmic reticulum',
      'Calcium signaling regulation through STIM1 interaction',
      'Formation of functional glucosidase II complex with PRKCSH beta subunit',
    ],
  },
  structure: {
    primary: 'The GIIα protein consists of a sequence of amino acids that form specific domains essential for its function.',
    secondary: 'The protein contains alpha helices and beta sheets that contribute to its structural stability and function.',
    tertiary: 'The three-dimensional folding necessary for the protein\'s activity and interaction with other subunits involves formation of a β α δ barrel domain.',
    quaternary: 'GIIα forms a complex with the GIIβ subunit (PRKCSH), which is critical for its regulatory functions and enzymatic activity.',
    domains: ['β α δ barrel domain', 'C-terminal domain'],
    post_translational_modifications: [
      'Glycosylation - affects interaction with other proteins like STIM1',
      'Phosphorylation sites that may regulate enzyme activity',
    ],
  },
  functions: {
    general_description: `GANAB encodes the alpha subunit of glucosidase II, an enzyme located in the endoplasmic reticulum (ER) that plays a critical role in the N-glycan processing pathway. This enzyme is involved in the initial trimming of high-mannose N-glycans, a crucial step in the maturation and quality control of glycoproteins. The trimming process ensures that only properly folded glycoproteins proceed through the secretory pathway, while misfolded ones are targeted for degradation. The enzyme's activity involves the removal of glucose residues from N-linked glycans, which is a necessary step for the correct folding and function of glycoproteins.`,
    modifications_to_functions: [
      {
        modification: {
          id: '1',
          location: 'Position 123',
          type: 'Glycosylation',
          description: 'N-linked glycosylation site',
        },
        function: {
          id: 'f1',
          description: 'Enhanced protein stability and proper folding',
          type: 'Structural',
          pathway: 'N-glycan processing',
        },
        publications: [
          {
            pmid: '22022391',
            title: 'Expanding the phenotype of GANAB mutations',
            year: 2021,
          },
        ],
      },
      {
        modification: {
          id: '2',
          location: 'Residue Ser456',
          type: 'Phosphorylation',
          description: 'Phosphorylation regulates activity',
        },
        function: {
          id: 'f2',
          description: 'Modulates glucosidase II enzymatic activity',
          type: 'Enzymatic Activity',
          pathway: 'Protein quality control',
        },
        publications: [
          {
            pmid: '20204020',
            title: 'Novel regulation of glucosidase II',
            year: 2020,
          },
        ],
      },
    ],
  },
  clinical_significance: {
    description: `Mutations in GANAB are associated with genetic disorders such as autosomal dominant polycystic kidney disease (ADPKD) and polycystic liver disease. These conditions are characterized by the development of fluid-filled cysts in the kidneys and liver, which can lead to organ dysfunction over time. GANAB mutations disrupt proper glycoprotein processing, affecting cellular homeostasis and contributing to cyst formation. The age of onset and severity of symptoms can vary depending on the specific mutation.`,
    conditions: [
      {
        condition: 'Autosomal Dominant Polycystic Kidney Disease (ADPKD)',
        variant_location: 'Exon 15',
        variant_type: 'Missense mutation',
        phenotype: 'Progressive kidney cyst formation leading to renal failure',
        age_related: true,
        onset_age: '30-50 years',
        publications: [
          {
            pmid: '22022391',
            title: 'GANAB mutations in polycystic kidney disease',
            year: 2022,
          },
        ],
      },
      {
        condition: 'Polycystic Liver Disease',
        variant_location: 'Multiple locations',
        variant_type: 'Loss of function',
        phenotype: 'Liver cyst development and hepatomegaly',
        age_related: true,
        onset_age: '40-60 years',
        publications: [
          {
            pmid: '21845821',
            title: 'Genetic basis of polycystic liver disease',
            year: 2021,
          },
        ],
      },
    ],
  },
  interactions: {
    small_molecules: [
      {
        small_molecule: {
          name: 'Deoxynojirimycin (DNJ)',
          pubchem_id: '193690',
        },
        interaction_type: 'Inhibitor',
        binding_site: 'Active site',
        ic50_value: '5.2 μM',
        effect_on_function: 'Inhibits glucosidase II activity',
        publications: [
          {
            pmid: '12345678',
            title: 'DNJ inhibition of glucosidase II',
            year: 2019,
          },
        ],
      },
      {
        small_molecule: {
          name: 'Castanospermine',
          pubchem_id: '54445',
        },
        interaction_type: 'Inhibitor',
        binding_site: 'Catalytic domain',
        ic50_value: '0.7 μM',
        effect_on_function: 'Potent inhibition of N-glycan processing',
        publications: [
          {
            pmid: '87654321',
            title: 'Castanospermine effects on ER glycoprotein processing',
            year: 2018,
          },
        ],
      },
    ],
    protein_partners: [
      {
        partner_protein: {
          uniprot_id: 'P14314',
          name: 'PRKCSH',
          sequence: '',
        },
        interaction_type: 'Binding partner',
        complex_name: 'Glucosidase II complex',
        publications: [
          {
            pmid: '11111111',
            title: 'Structure of glucosidase II complex',
            year: 2020,
          },
        ],
      },
      {
        partner_protein: {
          uniprot_id: 'Q13586',
          name: 'STIM1',
          sequence: '',
        },
        interaction_type: 'Regulator',
        complex_name: 'STIM1-GANAB complex',
        publications: [
          {
            pmid: '22222222',
            title: 'STIM1 interaction with glucosidase II alpha',
            year: 2022,
          },
        ],
      },
    ],
  },
  references: [
    {
      pmid: '22022391',
      title: 'Expanding: The phenotype and molecular genetics of GANAB-related polycystic kidney disease',
      doi: '10.1093/ndt/gfab291',
      year: 2022,
    },
    {
      pmid: '20204020',
      title: 'Novel: Glucosidase II regulation in the endoplasmic reticulum',
      doi: '10.1016/j.jbc.2020.01.001',
      year: 2020,
    },
  ],
};

export default function ProteinPage() {
  // const params = useParams();
  const [activeSection, setActiveSection] = useState<Section>('overview');

  // In production, fetch data based on params.id
  // const proteinData = await fetchProteinData(params.id);
  const proteinData = mockProteinData;

  const relatedGenes = [
    {
      symbol: 'GANC',
      name: 'Glucosidase II subunit C',
      relationship: 'Paralog',
    },
  ];

  return (
    <div className="min-h-screen bg-[var(--background)]">
      {/* Header */}
      <header className="border-b border-[var(--border-color)] bg-[var(--background-elevated)]">
        <div className="max-w-[1600px] mx-auto px-8 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-bold text-[var(--foreground)]">
              WCVikiCrow
            </h1>
            <div className="text-[var(--foreground-muted)] text-sm">
              Protein Sequence-to-Function Explorer
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1600px] mx-auto px-8 py-8">
        {/* Protein Title */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-[var(--foreground)] mb-2">
            {proteinData.protein.gene?.symbol || proteinData.protein.name}
          </h1>
          <p className="text-[var(--foreground-muted)] font-mono">
            UniProt: {proteinData.protein.uniprot_id} | Gene: {proteinData.protein.gene?.symbol}
          </p>
        </div>

        {/* Layout: Sidebar + Content */}
        <div className="flex gap-8">
          {/* Sidebar */}
          <Sidebar protein={proteinData.protein} relatedGenes={relatedGenes} />

          {/* Main Content Area */}
          <div className="flex-1 min-w-0">
            {/* Section Tabs */}
            <SectionTabs
              activeSection={activeSection}
              onSectionChange={setActiveSection}
            />

            {/* Section Content */}
            <div className="bg-[var(--background-elevated)] rounded-lg p-8 border border-[var(--border-color)]">
              {activeSection === 'overview' && <Overview data={proteinData.overview} />}
              {activeSection === 'structure' && <Structure data={proteinData.structure} />}
              {activeSection === 'function' && <Function data={proteinData.functions} />}
              {activeSection === 'clinical' && (
                <ClinicalSignificance data={proteinData.clinical_significance} />
              )}
              {activeSection === 'interactions' && (
                <Interactions data={proteinData.interactions} />
              )}
              {activeSection === 'references' && (
                <References publications={proteinData.references} />
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
