'use client';

export type Section = 'overview' | 'structure' | 'function' | 'clinical' | 'interactions' | 'references';

interface SectionTabsProps {
  activeSection: Section;
  onSectionChange: (section: Section) => void;
}

const sections: { id: Section; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'structure', label: 'Structure' },
  { id: 'function', label: 'Function' },
  { id: 'clinical', label: 'Clinical Significance' },
  { id: 'interactions', label: 'Interactions' },
  { id: 'references', label: 'References' },
];

export default function SectionTabs({ activeSection, onSectionChange }: SectionTabsProps) {
  return (
    <div className="border-b border-[var(--border-color)] mb-6">
      <nav className="flex gap-1 -mb-px">
        {sections.map((section) => (
          <button
            key={section.id}
            onClick={() => onSectionChange(section.id)}
            className={`
              px-6 py-3 text-sm font-medium border-b-2 transition-colors
              ${
                activeSection === section.id
                  ? 'border-[var(--accent-primary)] text-[var(--foreground)]'
                  : 'border-transparent text-[var(--foreground-muted)] hover:text-[var(--foreground)] hover:border-[var(--foreground-subtle)]'
              }
            `}
          >
            {section.label}
          </button>
        ))}
      </nav>
    </div>
  );
}
