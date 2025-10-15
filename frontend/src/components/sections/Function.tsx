import { ProteinArticle } from '@/types/protein';
import ModificationTable from '@/components/tables/ModificationTable';

interface FunctionProps {
  data: ProteinArticle['functions'];
}

export default function Function({ data }: FunctionProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-[var(--foreground)] mb-4">Functions</h2>
        <p className="text-[var(--foreground)] leading-relaxed whitespace-pre-wrap">
          {data.general_description}
        </p>
      </div>

      <div>
        <h3 className="text-xl font-semibold text-[var(--foreground)] mb-4">
          Sequence-to-Function Relationships
        </h3>
        <p className="text-[var(--foreground-muted)] text-sm mb-4">
          This table shows how specific protein modifications at particular locations affect
          protein function, based on experimental evidence from published research.
        </p>
        <ModificationTable data={data.modifications_to_functions} />
      </div>
    </div>
  );
}
