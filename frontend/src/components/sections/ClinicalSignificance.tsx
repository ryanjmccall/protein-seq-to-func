import { ProteinArticle } from '@/types/protein';
import PublicationCell from '@/components/tables/PublicationCell';

interface ClinicalSignificanceProps {
  data: ProteinArticle['clinical_significance'];
}

export default function ClinicalSignificance({ data }: ClinicalSignificanceProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-[var(--foreground)] mb-4">
          Clinical Significance & Role in Aging
        </h2>
        <p className="text-[var(--foreground)] leading-relaxed whitespace-pre-wrap">
          {data.description}
        </p>
      </div>

      {data.conditions && data.conditions.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold text-[var(--foreground)] mb-4">
            Associated Conditions
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full border border-[var(--table-border)] rounded-lg overflow-hidden">
              <thead>
                <tr className="bg-[var(--table-header-bg)]">
                  <th className="px-4 py-3 text-left text-sm font-semibold text-[var(--foreground-muted)] border-b border-[var(--table-border)]">
                    Condition
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-[var(--foreground-muted)] border-b border-[var(--table-border)]">
                    Variant
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-[var(--foreground-muted)] border-b border-[var(--table-border)]">
                    Phenotype
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-[var(--foreground-muted)] border-b border-[var(--table-border)]">
                    Age-Related
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-[var(--foreground-muted)] border-b border-[var(--table-border)]">
                    Publications
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.conditions.map((condition, index) => (
                  <tr
                    key={index}
                    className="hover:bg-[var(--table-row-hover)] transition-colors border-b border-[var(--table-border)] last:border-b-0"
                  >
                    <td className="px-4 py-3 text-sm font-semibold text-[var(--foreground)]">
                      {condition.condition}
                    </td>
                    <td className="px-4 py-3 text-sm font-mono text-[var(--foreground)]">
                      {condition.variant_location && condition.variant_type ? (
                        <div>
                          <div>{condition.variant_location}</div>
                          <div className="text-xs text-[var(--foreground-muted)]">
                            {condition.variant_type}
                          </div>
                        </div>
                      ) : (
                        <span className="text-[var(--foreground-muted)]">N/A</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-[var(--foreground)]">
                      {condition.phenotype}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {condition.age_related ? (
                        <span className="px-2 py-1 bg-[var(--warning)] text-black rounded text-xs font-medium">
                          Yes
                          {condition.onset_age && ` (${condition.onset_age})`}
                        </span>
                      ) : (
                        <span className="text-[var(--foreground-muted)]">No</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <PublicationCell publications={condition.publications} />
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
