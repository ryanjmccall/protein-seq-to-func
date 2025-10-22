'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/layout/Sidebar';
import SectionTabs, { Section } from '@/components/layout/SectionTabs';
import Overview from '@/components/sections/Overview';
import Structure from '@/components/sections/Structure';
import Function from '@/components/sections/Function';
import ClinicalSignificance from '@/components/sections/ClinicalSignificance';
import Interactions from '@/components/sections/Interactions';
import References from '@/components/sections/References';
import { ProteinArticle, Publication } from '@/types/protein';

interface ParsedProteinArticle {
  article: ProteinArticle;
  relatedGenes: { symbol: string; name?: string; relationship?: string }[];
  title: string;
}

interface MarkdownSection {
  title: string;
  content: string;
}

type KeyValueMap = Map<string, string[]>;

const H1_REGEX = /^#\s+(.*)$/m;

function normalizeNewlines(text: string): string {
  return text.replace(/\r\n/g, '\n');
}

function splitIntoSections(markdown: string, headingLevel: number): MarkdownSection[] {
  const pattern = new RegExp(`^${'#'.repeat(headingLevel)}\\s+(.*)$`, 'gm');
  const sections: MarkdownSection[] = [];

  let match: RegExpExecArray | null;
  let currentTitle: string | null = null;
  let contentStart = 0;

  while ((match = pattern.exec(markdown)) !== null) {
    if (currentTitle !== null) {
      sections.push({
        title: currentTitle,
        content: markdown.slice(contentStart, match.index).trim(),
      });
    }

    currentTitle = match[1].trim();
    contentStart = pattern.lastIndex;
  }

  if (currentTitle !== null) {
    sections.push({
      title: currentTitle,
      content: markdown.slice(contentStart).trim(),
    });
  }

  return sections;
}

function parseKeyValueList(content: string): KeyValueMap {
  const entries = new Map<string, string[]>();
  const lines = content
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .map((line) => line.replace(/^[-*+\d.]+\s*/, '').trim())
    .filter((line) => line.includes(':'));

  for (const line of lines) {
    const [key, ...rest] = line.split(':');
    const normalizedKey = key.trim().toLowerCase();
    const value = rest.join(':').trim();

    if (!entries.has(normalizedKey)) {
      entries.set(normalizedKey, []);
    }

    entries.get(normalizedKey)?.push(value);
  }

  return entries;
}

function getFirstValue(map: KeyValueMap, key: string): string | undefined {
  const values = map.get(key.toLowerCase());
  if (!values || values.length === 0) {
    return undefined;
  }

  const [first] = values;
  return first.trim() || undefined;
}

function getAllValues(map: KeyValueMap, key: string): string[] {
  return map.get(key.toLowerCase())?.map((value) => value.trim()).filter(Boolean) ?? [];
}

function parseCsvList(value?: string): string[] {
  if (!value) {
    return [];
  }

  return value
    .split(/[,;]+/)
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function parseInteger(value?: string): number | undefined {
  if (!value) {
    return undefined;
  }

  const parsed = Number.parseInt(value.replace(/[, ]/g, ''), 10);
  return Number.isNaN(parsed) ? undefined : parsed;
}

function parseStrand(value?: string): '-1' | '1' | undefined {
  if (!value) {
    return undefined;
  }

  const normalized = value.replace(/\s+/g, '').toLowerCase();

  if (normalized === '-1' || normalized === 'minus' || normalized === 'negative') {
    return '-1';
  }

  if (normalized === '1' || normalized === '+1' || normalized === 'plus' || normalized === 'positive') {
    return '1';
  }

  return undefined;
}

function parseBoolean(value?: string): boolean | undefined {
  if (!value) {
    return undefined;
  }

  const normalized = value.trim().toLowerCase();

  if (['true', 'yes', 'y', '1'].includes(normalized)) {
    return true;
  }

  if (['false', 'no', 'n', '0'].includes(normalized)) {
    return false;
  }

  return undefined;
}

function normalizeParagraphs(content: string): string {
  return content
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim())
    .filter((paragraph) => paragraph.length > 0)
    .join('\n\n');
}

function extractListItems(content: string): string[] {
  return content
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .map((line) => line.replace(/^[-*+\d.]+\s*/, '').trim())
    .filter((line) => line.length > 0);
}

function parseInlineKeyValue(value: string): Map<string, string> {
  const map = new Map<string, string>();

  value
    .split('|')
    .map((segment) => segment.trim())
    .filter((segment) => segment.length > 0)
    .forEach((segment) => {
      const colonIndex = segment.indexOf(':');
      if (colonIndex === -1) {
        return;
      }

      const key = segment.slice(0, colonIndex).trim().toLowerCase();
      const val = segment.slice(colonIndex + 1).trim();
      map.set(key, val);
    });

  return map;
}

function parsePublicationEntries(entries: string[]): Publication[] {
  return entries.reduce<Publication[]>((accumulator, entry) => {
    const fields = parseInlineKeyValue(entry);
    const pmid = fields.get('pmid');
    const title = fields.get('title');

    if (!pmid || !title) {
      return accumulator;
    }

    const doi = fields.get('doi');
    const yearValue = fields.get('year');
    const year = yearValue ? Number.parseInt(yearValue, 10) || undefined : undefined;

    accumulator.push({
      pmid: pmid.trim(),
      title: title.trim(),
      doi: doi?.trim(),
      year,
    });

    return accumulator;
  }, []);
}

function parseRelatedGenes(content: string): { symbol: string; name?: string; relationship?: string }[] {
  return extractListItems(content).map((line, index) => {
    const fields = parseInlineKeyValue(line);
    const symbol = fields.get('symbol') ?? '';

    if (!symbol) {
      throw new Error(`Related gene entry ${index + 1} is missing a symbol`);
    }

    const name = fields.get('name');
    const relationship = fields.get('relationship');

    return {
      symbol: symbol.trim(),
      name: name?.trim(),
      relationship: relationship?.trim(),
    };
  });
}

function parseOverviewSection(section?: MarkdownSection): {
  summary: string;
  keyFunctions: string[];
} {
  if (!section) {
    return { summary: '', keyFunctions: [] };
  }

  const headingIndex = section.content.search(/^###\s+/m);
  const summaryContent =
    headingIndex >= 0 ? section.content.slice(0, headingIndex).trim() : section.content.trim();

  const subsections = splitIntoSections(section.content, 3);
  const subsectionsMap = new Map(subsections.map((sub) => [sub.title, sub]));
  const keyFunctionsSection = subsectionsMap.get('Key Functions');

  return {
    summary: normalizeParagraphs(summaryContent),
    keyFunctions: keyFunctionsSection ? extractListItems(keyFunctionsSection.content) : [],
  };
}

function parseStructureSection(section?: MarkdownSection): ProteinArticle['structure'] {
  const defaults: ProteinArticle['structure'] = {
    primary: undefined,
    secondary: undefined,
    tertiary: undefined,
    quaternary: undefined,
    domains: [],
    post_translational_modifications: [],
  };

  if (!section) {
    return defaults;
  }

  const subsections = splitIntoSections(section.content, 3);
  const map = new Map(subsections.map((sub) => [sub.title, sub]));

  return {
    primary: map.get('Primary Structure')?.content.trim(),
    secondary: map.get('Secondary Structure')?.content.trim(),
    tertiary: map.get('Tertiary Architecture')?.content.trim(),
    quaternary: map.get('Quaternary Assembly')?.content.trim(),
    domains: map.get('Domains') ? extractListItems(map.get('Domains')!.content) : [],
    post_translational_modifications: map.get('Post-translational Modifications')
      ? extractListItems(map.get('Post-translational Modifications')!.content)
      : [],
  };
}

function parseModulationHotspots(
  section?: MarkdownSection,
): ProteinArticle['functions']['modifications_to_functions'] {
  if (!section) {
    return [];
  }

  const subsections = splitIntoSections(section.content, 4);

  return subsections.map((subsection, index) => {
    const fields = parseKeyValueList(subsection.content);

    const modificationId = getFirstValue(fields, 'modification id') ?? `mod-${index + 1}`;
    const functionId = getFirstValue(fields, 'function id') ?? `func-${index + 1}`;
    const location = getFirstValue(fields, 'location') ?? '';
    const type = getFirstValue(fields, 'type') ?? '';

    if (!location || !type) {
      throw new Error(`Modulation hotspot "${subsection.title}" is missing required fields`);
    }

    const modification = {
      id: modificationId,
      location,
      type,
      description: getFirstValue(fields, 'description'),
    };

    const functionData = {
      id: functionId,
      description: getFirstValue(fields, 'function description') ?? '',
      type: getFirstValue(fields, 'function type') ?? '',
      pathway: getFirstValue(fields, 'function pathway'),
    };

    const publications = parsePublicationEntries(getAllValues(fields, 'publication'));
    const evidenceLevel = getFirstValue(fields, 'notes');

    return {
      modification,
      function: functionData,
      publications,
      evidence_level: evidenceLevel,
    };
  });
}

function parseClinicalConditions(
  section?: MarkdownSection,
): ProteinArticle['clinical_significance']['conditions'] {
  if (!section) {
    return [];
  }

  const conditionSections = splitIntoSections(section.content, 4);

  return conditionSections.map((conditionSection, index) => {
    const fields = parseKeyValueList(conditionSection.content);
    const rawTitle = conditionSection.title.replace(/^Condition:\s*/i, '').trim();
    const conditionName = rawTitle || `Condition ${index + 1}`;

    return {
      condition: conditionName,
      variant_location: getFirstValue(fields, 'variant location'),
      variant_type: getFirstValue(fields, 'variant type'),
      phenotype: getFirstValue(fields, 'phenotype') ?? '',
      age_related: parseBoolean(getFirstValue(fields, 'age related')),
      onset_age: getFirstValue(fields, 'onset age'),
      publications: parsePublicationEntries(getAllValues(fields, 'publication')),
    };
  });
}

function parseSmallMoleculeInteractions(
  section?: MarkdownSection,
): ProteinArticle['interactions']['small_molecules'] {
  if (!section) {
    return [];
  }

  const molecules = splitIntoSections(section.content, 4);

  return molecules.map((moleculeSection) => {
    const fields = parseKeyValueList(moleculeSection.content);
    const name = moleculeSection.title.trim() || 'Unknown molecule';

    return {
      small_molecule: {
        name,
        pubchem_id: getFirstValue(fields, 'pubchem id'),
        chembl_id: getFirstValue(fields, 'chembl id'),
        smiles: getFirstValue(fields, 'smiles'),
      },
      interaction_type: getFirstValue(fields, 'interaction type') ?? '',
      binding_site: getFirstValue(fields, 'binding site'),
      kd_value: getFirstValue(fields, 'kd'),
      ic50_value: getFirstValue(fields, 'ic50'),
      effect_on_function: getFirstValue(fields, 'effect'),
      publications: parsePublicationEntries(getAllValues(fields, 'publication')),
    };
  });
}

function parseProteinPartners(
  section?: MarkdownSection,
): ProteinArticle['interactions']['protein_partners'] {
  if (!section) {
    return [];
  }

  const partners = splitIntoSections(section.content, 4);

  return partners.map((partnerSection) => {
    const fields = parseKeyValueList(partnerSection.content);
    const partnerName = partnerSection.title.trim() || 'Unknown partner';

    return {
      partner_protein: {
        uniprot_id: getFirstValue(fields, 'uniprot id') ?? '',
        name: partnerName,
        sequence: getFirstValue(fields, 'sequence') ?? '',
      },
      interaction_type: getFirstValue(fields, 'interaction type') ?? '',
      complex_name: getFirstValue(fields, 'complex'),
      publications: parsePublicationEntries(getAllValues(fields, 'publication')),
    };
  });
}

function parseReferenceList(section?: MarkdownSection): Publication[] {
  if (!section) {
    return [];
  }

  return parsePublicationEntries(extractListItems(section.content));
}

function parseMetadataSection(section?: MarkdownSection): {
  protein: ProteinArticle['protein'];
  relatedGenes: { symbol: string; name?: string; relationship?: string }[];
} {
  if (!section) {
    throw new Error('Metadata section is missing from the article');
  }

  const subsections = splitIntoSections(section.content, 3);
  const map = new Map(subsections.map((sub) => [sub.title, sub]));

  const proteinSnapshot = map.get('Protein Snapshot');
  if (!proteinSnapshot) {
    throw new Error('Protein Snapshot metadata is missing');
  }

  const proteinFields = parseKeyValueList(proteinSnapshot.content);
  const uniprotId = getFirstValue(proteinFields, 'uniprot id');
  const proteinName = getFirstValue(proteinFields, 'protein name');
  const sequence = getFirstValue(proteinFields, 'amino acid sequence') ?? '';

  if (!uniprotId || !proteinName || !sequence) {
    throw new Error('Protein metadata is missing required fields');
  }

  const geneProfile = map.get('Gene Profile');
  if (!geneProfile) {
    throw new Error('Gene Profile metadata is missing');
  }

  const geneFields = parseKeyValueList(geneProfile.content);
  const geneId = getFirstValue(geneFields, 'gene id');
  const geneSymbol = getFirstValue(geneFields, 'gene symbol');
  const organism = getFirstValue(geneFields, 'organism');

  if (!geneId || !geneSymbol || !organism) {
    throw new Error('Gene metadata is missing required fields');
  }

  const protein: ProteinArticle['protein'] = {
    uniprot_id: uniprotId,
    name: proteinName,
    sequence,
    family: getFirstValue(proteinFields, 'protein family'),
    structure_pdb_id: getFirstValue(proteinFields, 'structure pdb id'),
    gene: {
      gene_id: geneId,
      symbol: geneSymbol,
      organism,
      aliases: parseCsvList(getFirstValue(geneFields, 'aliases')),
      chromosome: getFirstValue(geneFields, 'chromosome'),
      start: parseInteger(getFirstValue(geneFields, 'start')),
      end: parseInteger(getFirstValue(geneFields, 'end')),
      strand: parseStrand(getFirstValue(geneFields, 'strand')),
    },
  };

  const relatedGenesSection = map.get('Related Genes');
  const relatedGenes = relatedGenesSection ? parseRelatedGenes(relatedGenesSection.content) : [];

  return { protein, relatedGenes };
}

function parseProteinMarkdown(markdown: string): ParsedProteinArticle {
  const normalized = normalizeNewlines(markdown).trim();
  const titleMatch = normalized.match(H1_REGEX);

  if (!titleMatch) {
    throw new Error('Article is missing a top-level title');
  }

  const title = titleMatch[1].trim();
  const titleLineIndex = normalized.indexOf(titleMatch[0]);
  const bodyStartIndex = titleLineIndex + titleMatch[0].length;
  const bodyContent = normalized.slice(bodyStartIndex).trim();

  const topLevelSections = splitIntoSections(bodyContent, 2);
  const sectionMap = new Map(topLevelSections.map((section) => [section.title, section]));

  const { protein, relatedGenes } = parseMetadataSection(sectionMap.get('Metadata'));
  const overview = parseOverviewSection(sectionMap.get('Overview'));
  const structure = parseStructureSection(sectionMap.get('Structure'));

  const functionalSection = sectionMap.get('Functional Biology');
  const functionalHeadingIndex = functionalSection?.content.search(/^###\s+/m) ?? -1;
  const functionalNarrative =
    functionalSection && functionalHeadingIndex >= 0
      ? functionalSection.content.slice(0, functionalHeadingIndex).trim()
      : functionalSection?.content.trim() ?? '';

  const clinicalSection = sectionMap.get('Clinical Significance');
  const clinicalHeadingIndex = clinicalSection?.content.search(/^###\s+/m) ?? -1;
  const clinicalNarrative =
    clinicalSection && clinicalHeadingIndex >= 0
      ? clinicalSection.content.slice(0, clinicalHeadingIndex).trim()
      : clinicalSection?.content.trim() ?? '';

  const interactionsSection = sectionMap.get('Interaction Landscape');
  const interactionSubsections = interactionsSection
    ? splitIntoSections(interactionsSection.content, 3)
    : [];
  const interactionMap = new Map(interactionSubsections.map((section) => [section.title, section]));

  const referenceSection = sectionMap.get('Reference Corpus');

  const article: ProteinArticle = {
    protein,
    overview: {
      summary: overview.summary,
      key_functions: overview.keyFunctions,
    },
    structure,
    functions: {
      general_description: normalizeParagraphs(functionalNarrative),
      modifications_to_functions: parseModulationHotspots(
        functionalSection
          ? splitIntoSections(functionalSection.content, 3).find(
              (sub) => sub.title === 'Modulation Hotspots',
            )
          : undefined,
      ),
    },
    clinical_significance: {
      description: normalizeParagraphs(clinicalNarrative),
      conditions: parseClinicalConditions(
        clinicalSection
          ? splitIntoSections(clinicalSection.content, 3).find(
              (sub) => sub.title === 'Conditions',
            )
          : undefined,
      ),
    },
    interactions: {
      small_molecules: parseSmallMoleculeInteractions(interactionMap.get('Small Molecules')),
      protein_partners: parseProteinPartners(interactionMap.get('Protein Partners')),
    },
    references: parseReferenceList(referenceSection),
  };

  return {
    article,
    relatedGenes,
    title,
  };
}

export default function ProteinPage() {
  const params = useParams<{ id?: string }>();
  const [activeSection, setActiveSection] = useState<Section>('overview');
  const [proteinData, setProteinData] = useState<ProteinArticle | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [relatedGenes, setRelatedGenes] = useState<
    { symbol: string; name?: string; relationship?: string }[]
  >([]);
  const proteinId = params?.id ?? 'ganab';

  useEffect(() => {
    async function loadProteinArticle() {
      setIsLoading(true);
      setLoadError(null);

      try {
        const articlePath = `/data/${encodeURIComponent(proteinId)}.md`;
        const response = await fetch(articlePath);

        if (!response.ok) {
          throw new Error(`Failed fetching protein article for "${proteinId}"`);
        }

        const markdown = await response.text();
        const { article, relatedGenes: parsedRelatedGenes } = parseProteinMarkdown(markdown);
        setProteinData(article);
        setRelatedGenes(parsedRelatedGenes);
      } catch (error) {
        setLoadError((error as Error).message);
        setProteinData(null);
        setRelatedGenes([]);
      } finally {
        setIsLoading(false);
      }
    }

    void loadProteinArticle();
  }, [proteinId]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[var(--background)] flex items-center justify-center">
        <p className="text-[var(--foreground-muted)]">Loading protein article…</p>
      </div>
    );
  }

  if (!proteinData) {
    return (
      <div className="min-h-screen bg-[var(--background)] flex items-center justify-center">
        <div className="text-center space-y-2">
          <p className="text-[var(--foreground)] font-semibold">
            Unable to load protein article.
          </p>
          {loadError && (
            <p className="text-sm text-[var(--foreground-muted)] whitespace-pre-line">
              {loadError}
            </p>
          )}
        </div>
      </div>
    );
  }

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
