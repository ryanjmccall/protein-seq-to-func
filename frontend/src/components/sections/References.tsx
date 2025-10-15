import { Publication } from '@/types/protein';

interface ReferencesProps {
  publications: Publication[];
}

export default function References({ publications }: ReferencesProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-[var(--foreground)] mb-4">References</h2>
      </div>

      {publications.length === 0 ? (
        <p className="text-[var(--foreground-muted)] italic">No references available.</p>
      ) : (
        <div className="space-y-4">
          {publications.map((pub, index) => (
            <div
              key={index}
              className="border border-[var(--border-color)] rounded-lg p-4 bg-[var(--background-card)] hover:bg-[var(--table-row-hover)] transition-colors"
            >
              <div className="flex items-start gap-3">
                <span className="text-[var(--foreground-muted)] font-mono text-sm mt-1">
                  [{index + 1}]
                </span>
                <div className="flex-1">
                  <h3 className="text-[var(--foreground)] font-semibold mb-2">
                    {pub.title}
                  </h3>
                  <div className="flex flex-wrap gap-4 text-sm">
                    <a
                      href={`https://pubmed.ncbi.nlm.nih.gov/${pub.pmid}/`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[var(--info)] hover:text-[var(--accent-primary-hover)] font-mono"
                    >
                      PMID: {pub.pmid}
                    </a>
                    {pub.doi && (
                      <a
                        href={`https://doi.org/${pub.doi}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[var(--info)] hover:text-[var(--accent-primary-hover)] font-mono"
                      >
                        DOI: {pub.doi}
                      </a>
                    )}
                    {pub.year && (
                      <span className="text-[var(--foreground-muted)]">
                        Year: {pub.year}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
