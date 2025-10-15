import { ProteinArticle } from '@/types/protein';

interface OverviewProps {
  data: ProteinArticle['overview'];
}

export default function Overview({ data }: OverviewProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-[var(--foreground)] mb-4">Overview</h2>
        <p className="text-[var(--foreground)] leading-relaxed whitespace-pre-wrap">
          {data.summary}
        </p>
      </div>

      {data.key_functions && data.key_functions.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold text-[var(--foreground)] mb-3">
            Key Functions
          </h3>
          <ul className="list-disc list-inside space-y-2 text-[var(--foreground)]">
            {data.key_functions.map((func, index) => (
              <li key={index} className="leading-relaxed">
                {func}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
