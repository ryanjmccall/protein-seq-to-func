import { ProteinArticle } from '@/types/protein';

interface StructureProps {
  data: ProteinArticle['structure'];
}

export default function Structure({ data }: StructureProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-[var(--foreground)] mb-4">Structure</h2>
      </div>

      {/* Domains */}
      {data.domains && data.domains.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold text-[var(--foreground)] mb-3">
            Protein Domains
          </h3>
          <div className="flex flex-wrap gap-2">
            {data.domains.map((domain, index) => (
              <span
                key={index}
                className="px-3 py-1 bg-[var(--accent-secondary)] text-white rounded-full text-sm"
              >
                {domain}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Structural Levels */}
      <div className="grid md:grid-cols-2 gap-6">
        {data.primary && (
          <div className="border border-[var(--border-color)] rounded-lg p-4 bg-[var(--background-card)]">
            <h4 className="text-lg font-semibold text-[var(--foreground)] mb-2">
              Primary Structure
            </h4>
            <p className="text-[var(--foreground)] text-sm leading-relaxed">
              {data.primary}
            </p>
          </div>
        )}

        {data.secondary && (
          <div className="border border-[var(--border-color)] rounded-lg p-4 bg-[var(--background-card)]">
            <h4 className="text-lg font-semibold text-[var(--foreground)] mb-2">
              Secondary Structure
            </h4>
            <p className="text-[var(--foreground)] text-sm leading-relaxed">
              {data.secondary}
            </p>
          </div>
        )}

        {data.tertiary && (
          <div className="border border-[var(--border-color)] rounded-lg p-4 bg-[var(--background-card)]">
            <h4 className="text-lg font-semibold text-[var(--foreground)] mb-2">
              Tertiary Structure
            </h4>
            <p className="text-[var(--foreground)] text-sm leading-relaxed">
              {data.tertiary}
            </p>
          </div>
        )}

        {data.quaternary && (
          <div className="border border-[var(--border-color)] rounded-lg p-4 bg-[var(--background-card)]">
            <h4 className="text-lg font-semibold text-[var(--foreground)] mb-2">
              Quaternary Structure
            </h4>
            <p className="text-[var(--foreground)] text-sm leading-relaxed">
              {data.quaternary}
            </p>
          </div>
        )}
      </div>

      {/* Post-translational Modifications */}
      {data.post_translational_modifications &&
        data.post_translational_modifications.length > 0 && (
          <div>
            <h3 className="text-xl font-semibold text-[var(--foreground)] mb-3">
              Post-translational Modifications
            </h3>
            <ul className="list-disc list-inside space-y-2 text-[var(--foreground)]">
              {data.post_translational_modifications.map((mod, index) => (
                <li key={index} className="leading-relaxed">
                  {mod}
                </li>
              ))}
            </ul>
          </div>
        )}
    </div>
  );
}
