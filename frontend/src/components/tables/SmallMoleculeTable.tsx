import { ProteinSmallMoleculeInteraction } from '@/types/protein';
import PublicationCell from './PublicationCell';

interface SmallMoleculeTableProps {
  data: ProteinSmallMoleculeInteraction[];
}

export default function SmallMoleculeTable({ data }: SmallMoleculeTableProps) {
  if (data.length === 0) {
    return (
      <p className="text-[var(--foreground-muted)] italic">
        No small molecule interaction data available.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border border-[var(--table-border)] rounded-lg overflow-hidden">
        <thead>
          <tr className="bg-[var(--table-header-bg)]">
            <th className="px-4 py-3 text-left text-sm font-semibold text-[var(--foreground-muted)] border-b border-[var(--table-border)]">
              Molecule Name
            </th>
            <th className="px-4 py-3 text-left text-sm font-semibold text-[var(--foreground-muted)] border-b border-[var(--table-border)]">
              PubChem ID
            </th>
            <th className="px-4 py-3 text-left text-sm font-semibold text-[var(--foreground-muted)] border-b border-[var(--table-border)]">
              Interaction Type
            </th>
            <th className="px-4 py-3 text-left text-sm font-semibold text-[var(--foreground-muted)] border-b border-[var(--table-border)]">
              Effect on Function
            </th>
            <th className="px-4 py-3 text-left text-sm font-semibold text-[var(--foreground-muted)] border-b border-[var(--table-border)]">
              Activity
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
              <td className="px-4 py-3 text-sm font-semibold text-[var(--foreground)]">
                {item.small_molecule.name}
              </td>
              <td className="px-4 py-3 text-sm font-mono">
                {item.small_molecule.pubchem_id ? (
                  <a
                    href={`https://pubchem.ncbi.nlm.nih.gov/compound/${item.small_molecule.pubchem_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[var(--info)] hover:text-[var(--accent-primary-hover)]"
                  >
                    CID:{item.small_molecule.pubchem_id}
                  </a>
                ) : (
                  <span className="text-[var(--foreground-muted)]">N/A</span>
                )}
              </td>
              <td className="px-4 py-3 text-sm">
                <span className="px-2 py-1 bg-[var(--accent-secondary)] text-white rounded text-xs font-medium">
                  {item.interaction_type}
                </span>
                {item.binding_site && (
                  <span className="block text-xs text-[var(--foreground-muted)] mt-1">
                    Site: {item.binding_site}
                  </span>
                )}
              </td>
              <td className="px-4 py-3 text-sm text-[var(--foreground)]">
                {item.effect_on_function || 'N/A'}
              </td>
              <td className="px-4 py-3 text-sm font-mono text-[var(--foreground)]">
                {item.ic50_value && (
                  <div className="text-xs">
                    <span className="text-[var(--foreground-muted)]">IC50:</span> {item.ic50_value}
                  </div>
                )}
                {item.kd_value && (
                  <div className="text-xs">
                    <span className="text-[var(--foreground-muted)]">Kd:</span> {item.kd_value}
                  </div>
                )}
                {!item.ic50_value && !item.kd_value && (
                  <span className="text-[var(--foreground-muted)]">N/A</span>
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
