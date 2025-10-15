import { Gene } from '@/types/protein';

interface GenePositionTableProps {
  gene: Gene;
}

export default function GenePositionTable({ gene }: GenePositionTableProps) {
  if (!gene.chromosome) {
    return null;
  }

  return (
    <div className="border border-[var(--border-color)] rounded-lg overflow-hidden">
      {/* Red header */}
      <div className="bg-[var(--accent-primary)] text-white px-4 py-2 font-semibold">
        Gene Position (hg19)
      </div>

      {/* Table */}
      <div className="bg-[var(--background-card)]">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[var(--table-header-bg)] border-b border-[var(--table-border)]">
              <th className="px-4 py-2 text-left text-[var(--foreground-muted)] font-semibold">CHR</th>
              <th className="px-4 py-2 text-left text-[var(--foreground-muted)] font-semibold">END</th>
              <th className="px-4 py-2 text-left text-[var(--foreground-muted)] font-semibold">START</th>
              <th className="px-4 py-2 text-left text-[var(--foreground-muted)] font-semibold">STRAND</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-[var(--table-border)] hover:bg-[var(--table-row-hover)]">
              <td className="px-4 py-2 font-mono text-[var(--foreground)]">{gene.chromosome}</td>
              <td className="px-4 py-2 font-mono text-[var(--foreground)]">
                {gene.end?.toLocaleString()}
              </td>
              <td className="px-4 py-2 font-mono text-[var(--foreground)]">
                {gene.start?.toLocaleString()}
              </td>
              <td className="px-4 py-2 font-mono text-[var(--foreground)]">{gene.strand}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
