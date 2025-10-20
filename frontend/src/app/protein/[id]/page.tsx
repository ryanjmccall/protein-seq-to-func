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
import { ProteinArticle } from '@/types/protein';

const FRONT_MATTER_REGEX = /^---\n([\s\S]*?)\n---/;

function parseProteinMarkdown(markdown: string): ProteinArticle {
  const match = markdown.match(FRONT_MATTER_REGEX);

  if (!match) {
    throw new Error('Missing front matter in protein markdown file');
  }

  try {
    const frontMatter = match[1].trim();
    return JSON.parse(frontMatter) as ProteinArticle;
  } catch (error) {
    throw new Error(
      `Unable to parse protein front matter: ${(error as Error).message}`,
    );
  }
}

export default function ProteinPage() {
  const params = useParams<{ id?: string }>();
  const [activeSection, setActiveSection] = useState<Section>('overview');
  const [proteinData, setProteinData] = useState<ProteinArticle | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const proteinId = params?.id ?? 'ganab';

  useEffect(() => {
    async function loadProteinArticle() {
      setIsLoading(true);
      setLoadError(null);

      try {
        const articlePath = `/data/${encodeURIComponent(proteinId)}.md`;
        const response = await fetch(articlePath);

        if (!response.ok) {
          throw new Error(`Failed fetching mock article for "${proteinId}"`);
        }

        const markdown = await response.text();
        const article = parseProteinMarkdown(markdown);
        setProteinData(article);
      } catch (error) {
        setLoadError((error as Error).message);
        setProteinData(null);
      } finally {
        setIsLoading(false);
      }
    }

    void loadProteinArticle();
  }, [proteinId]);

  const relatedGenes = [
    {
      symbol: 'GANC',
      name: 'Glucosidase II subunit C',
      relationship: 'Paralog',
    },
  ];

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
