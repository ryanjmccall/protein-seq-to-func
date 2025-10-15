interface RelatedGene {
  symbol: string;
  name?: string;
  relationship?: string;
}

interface RelatedGenesCardProps {
  genes: RelatedGene[];
}

export default function RelatedGenesCard({ genes }: RelatedGenesCardProps) {
  if (genes.length === 0) {
    return null;
  }

  return (
    <div className="border border-[var(--border-color)] rounded-lg overflow-hidden">
      {/* Red header */}
      <div className="bg-[var(--accent-primary)] text-white px-4 py-2 font-semibold">
        Related Genes
      </div>

      {/* Card content */}
      <div className="bg-[var(--background-card)] p-4">
        <div className="space-y-3">
          {genes.map((gene, index) => (
            <div
              key={index}
              className="flex items-start gap-3 p-2 rounded hover:bg-[var(--table-row-hover)] transition-colors"
            >
              {/* Gene icon placeholder - could be replaced with actual visualization */}
              <div className="w-8 h-8 rounded-full bg-[var(--accent-secondary)] flex items-center justify-center text-xs text-white font-bold">
                {gene.symbol.charAt(0)}
              </div>

              <div className="flex-1">
                <a href={`/protein/${gene.symbol}`} className="font-semibold text-[var(--info)] hover:text-[var(--accent-primary-hover)]">
                  {gene.symbol}
                </a>
                {gene.name && (
                  <p className="text-xs text-[var(--foreground-muted)] mt-1">{gene.name}</p>
                )}
                {gene.relationship && (
                  <p className="text-xs text-[var(--foreground-subtle)] mt-1 italic">
                    {gene.relationship}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
