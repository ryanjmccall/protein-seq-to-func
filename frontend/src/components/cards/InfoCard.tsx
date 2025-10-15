interface InfoCardProps {
  title: string;
  items: { label: string; value: string | string[] }[];
}

export default function InfoCard({ title, items }: InfoCardProps) {
  return (
    <div className="border border-[var(--border-color)] rounded-lg overflow-hidden">
      {/* Red header like WikiCrow */}
      <div className="bg-[var(--accent-primary)] text-white px-4 py-2 font-semibold">
        {title}
      </div>

      {/* Card content */}
      <div className="bg-[var(--background-card)] p-4">
        <dl className="space-y-2">
          {items.map((item, index) => (
            <div key={index} className="text-sm">
              <dt className="text-[var(--foreground-muted)] mb-1">{item.label}</dt>
              <dd className="text-[var(--foreground)] font-mono">
                {Array.isArray(item.value)
                  ? item.value.join(', ')
                  : item.value}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
