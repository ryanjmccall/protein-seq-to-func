import { ModificationToFunction } from '@/types/protein';
import PublicationCell from './PublicationCell';

interface ModificationTableProps {
  data: ModificationToFunction[];
}

export default function ModificationTable({ data }: ModificationTableProps) {
  if (data.length === 0) {
    return (
      <p className="text-[var(--foreground-muted)] italic">
        No modification data available.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border border-[var(--table-border)] rounded-lg overflow-hidden">
        <thead>
          <tr className="bg-[var(--table-header-bg)]">
            <th className="px-4 py-3 text-left text-sm font-semibold text-[var(--foreground-muted)] border-b border-[var(--table-border)]">
              Location
            </th>
            <th className="px-4 py-3 text-left text-sm font-semibold text-[var(--foreground-muted)] border-b border-[var(--table-border)]">
              Modification Type
            </th>
            <th className="px-4 py-3 text-left text-sm font-semibold text-[var(--foreground-muted)] border-b border-[var(--table-border)]">
              Resulting Function
            </th>
            <th className="px-4 py-3 text-left text-sm font-semibold text-[var(--foreground-muted)] border-b border-[var(--table-border)]">
              Publications
            </th>
          </tr>
        </thead>
        <tbody>
          {data.map((item, index) => (
            <tr
              key={index}
              className="hover:bg-[var(--table-row-hover)] transition-colors border-b border-[var(--table-border)] last:border-b-0"
            >
              <td className="px-4 py-3 text-sm font-mono text-[var(--foreground)]">
                {item.modification.location}
              </td>
              <td className="px-4 py-3 text-sm text-[var(--foreground)]">
                <span className="px-2 py-1 bg-[var(--accent-secondary)] text-white rounded text-xs font-medium">
                  {item.modification.type}
                </span>
              </td>
              <td className="px-4 py-3 text-sm text-[var(--foreground)]">
                {item.function.description}
                {item.function.pathway && (
                  <span className="block text-xs text-[var(--foreground-muted)] mt-1">
                    Pathway: {item.function.pathway}
                  </span>
                )}
              </td>
              <td className="px-4 py-3 text-sm">
                <PublicationCell publications={item.publications} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
