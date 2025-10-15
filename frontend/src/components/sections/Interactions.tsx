import { ProteinArticle } from '@/types/protein';
import SmallMoleculeTable from '@/components/tables/SmallMoleculeTable';
import PublicationCell from '@/components/tables/PublicationCell';

interface InteractionsProps {
  data: ProteinArticle['interactions'];
}

export default function Interactions({ data }: InteractionsProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-[var(--foreground)] mb-4">Interactions</h2>
      </div>

      {/* Small Molecule Interactions */}
      <div>
        <h3 className="text-xl font-semibold text-[var(--foreground)] mb-4">
          Small Molecule Interactions
        </h3>
        <p className="text-[var(--foreground-muted)] text-sm mb-4">
          Compounds and drugs that interact with this protein, including inhibitors, activators,
          and substrates.
        </p>
        <SmallMoleculeTable data={data.small_molecules} />
      </div>

      {/* Protein-Protein Interactions */}
      {data.protein_partners && data.protein_partners.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold text-[var(--foreground)] mb-4">
            Protein-Protein Interactions
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full border border-[var(--table-border)] rounded-lg overflow-hidden">
              <thead>
                <tr className="bg-[var(--table-header-bg)]">
                  <th className="px-4 py-3 text-left text-sm font-semibold text-[var(--foreground-muted)] border-b border-[var(--table-border)]">
                    Partner Protein
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-[var(--foreground-muted)] border-b border-[var(--table-border)]">
                    Interaction Type
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-[var(--foreground-muted)] border-b border-[var(--table-border)]">
                    Complex
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-[var(--foreground-muted)] border-b border-[var(--table-border)]">
                    Publications
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.protein_partners.map((partner, index) => (
                  <tr
                    key={index}
                    className="hover:bg-[var(--table-row-hover)] transition-colors border-b border-[var(--table-border)] last:border-b-0"
                  >
                    <td className="px-4 py-3 text-sm">
                      <a
                        href={`/protein/${partner.partner_protein.uniprot_id}`}
                        className="font-semibold text-[var(--info)] hover:text-[var(--accent-primary-hover)]"
                      >
                        {partner.partner_protein.name}
                      </a>
                      <div className="text-xs text-[var(--foreground-muted)] font-mono">
                        {partner.partner_protein.uniprot_id}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span className="px-2 py-1 bg-[var(--accent-secondary)] text-white rounded text-xs font-medium">
                        {partner.interaction_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-[var(--foreground)]">
                      {partner.complex_name || (
                        <span className="text-[var(--foreground-muted)]">N/A</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <PublicationCell publications={partner.publications} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
