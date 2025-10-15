import { Publication } from '@/types/protein';

interface PublicationCellProps {
  publications: Publication[];
}

export default function PublicationCell({ publications }: PublicationCellProps) {
  if (publications.length === 0) {
    return <span className="text-[var(--foreground-muted)]">No citations</span>;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {publications.map((pub, index) => (
        <a
          key={index}
          href={`https://pubmed.ncbi.nlm.nih.gov/${pub.pmid}/`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[var(--info)] hover:text-[var(--accent-primary-hover)] text-xs font-mono"
          title={pub.title}
        >
          PMID:{pub.pmid}
        </a>
      ))}
    </div>
  );
}
