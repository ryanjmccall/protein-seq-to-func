import { Protein } from '@/types/protein';
import InfoCard from '@/components/cards/InfoCard';
import GenePositionTable from '@/components/cards/GenePositionTable';
import RelatedGenesCard from '@/components/cards/RelatedGenesCard';
import ProteinViewer from '@/components/viewer/ProteinViewer';

interface SidebarProps {
  protein: Protein;
  relatedGenes?: { symbol: string; name?: string; relationship?: string }[];
}

export default function Sidebar({ protein, relatedGenes = [] }: SidebarProps) {
  const infoItems = [
    {
      label: 'gene names',
      value: protein.gene?.aliases || [protein.gene?.symbol || 'N/A'],
    },
    {
      label: 'type',
      value: 'protein-coding',
    },
    {
      label: 'n_exons',
      value: protein.gene ? 'Loading...' : 'N/A',
    },
  ];

  return (
    <aside className="w-80 space-y-6">
      {/* Protein Structure Visualization with Mol* */}
      {protein.structure_pdb_id ? (
        <ProteinViewer
          pdbId={protein.structure_pdb_id}
          description="Crystal structure of glucosidase II alpha subunit"
        />
      ) : (
        <div className="border border-[var(--border-color)] rounded-lg overflow-hidden">
          <div className="bg-[var(--background-card)] p-4">
            <div className="aspect-square bg-[var(--background)] rounded flex items-center justify-center">
              <p className="text-[var(--foreground-muted)] text-sm">No structure available</p>
            </div>
          </div>
        </div>
      )}

      {/* Info Card */}
      <InfoCard title="Info" items={infoItems} />

      {/* Gene Position Table */}
      {protein.gene && <GenePositionTable gene={protein.gene} />}

      {/* Related Genes */}
      {relatedGenes.length > 0 && <RelatedGenesCard genes={relatedGenes} />}
    </aside>
  );
}
