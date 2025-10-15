# Protein Sequence-to-Function Explorer - Frontend

A WikiCrow-inspired web application for exploring protein sequence-to-function relationships, built with Next.js 15, React 19, and Tailwind CSS.

## Overview

This frontend provides a comprehensive interface for visualizing protein data with a focus on:
- **Sequence-to-function relationships**: How protein modifications affect function
- **Small molecule interactions**: Drug/compound targeting information
- **Clinical significance**: Disease associations and aging-related phenotypes
- **Publication citations**: All claims linked to PubMed articles

## Tech Stack

- **Framework**: Next.js 15 with App Router
- **React**: Version 19
- **Styling**: Tailwind CSS 4 with custom dark theme
- **TypeScript**: Full type safety
- **Fonts**: Geist Sans & Geist Mono

## Getting Started

### Prerequisites
- Node.js 20+
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

Visit [http://localhost:3000/protein/GANAB](http://localhost:3000/protein/GANAB) to see the example protein page.

### Build for Production

```bash
npm run build
npm start
```

## Project Structure

```
frontend/src/
├── app/
│   ├── protein/[id]/
│   │   └── page.tsx          # Dynamic protein page
│   ├── layout.tsx             # Root layout with fonts
│   ├── page.tsx               # Homepage
│   └── globals.css            # Global styles & dark theme
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx        # Left sidebar with protein info
│   │   └── SectionTabs.tsx    # Navigation tabs
│   ├── viewer/
│   │   └── ProteinViewer.tsx  # 3D structure viewer with Mol*
│   ├── cards/
│   │   ├── InfoCard.tsx       # Red-header info cards
│   │   ├── GenePositionTable.tsx  # Genomic coordinates
│   │   └── RelatedGenesCard.tsx   # Gene network
│   ├── sections/
│   │   ├── Overview.tsx       # Overview section
│   │   ├── Structure.tsx      # Protein structure
│   │   ├── Function.tsx       # Sequence-to-function tables
│   │   ├── ClinicalSignificance.tsx  # Disease & aging
│   │   ├── Interactions.tsx   # Small molecules & partners
│   │   └── References.tsx     # Publications
│   └── tables/
│       ├── ModificationTable.tsx      # Modification→Function
│       ├── SmallMoleculeTable.tsx     # Compound interactions
│       └── PublicationCell.tsx        # PMID links
├── types/
│   └── protein.ts             # TypeScript type definitions
└── lib/
    └── (future API client code)
```

## Key Features

### 1. WikiCrow-Style Dark Theme

The application features a professional dark theme inspired by WikiCrow:
- Dark charcoal backgrounds (#1a1a1a)
- Deep burgundy/red accent colors (#8B2D2D)
- Monospace fonts for technical data
- Color-coded section headers

### 2. Comprehensive Protein Pages

Each protein page includes:

#### Left Sidebar
- **Interactive 3D structure viewer** with Mol* (fully integrated!)
  - Loads structures directly from RCSB PDB
  - Rotate, zoom, and pan controls
  - Links to full PDB entry
  - See `/docs/3D_VIEWER_GUIDE.md` for details
- Info card with gene names and metadata
- Gene position table (chromosome, coordinates, strand)
- Related genes with network visualization

#### Main Content (Tabbed Sections)
- **Overview**: Rich text summary and key functions
- **Structure**: Domains, structural levels (1°-4°), PTMs
- **Function**: Sequence-to-function table showing modification→function relationships
- **Clinical Significance**: Disease associations and age-related phenotypes
- **Interactions**: Small molecule and protein-protein interactions
- **References**: Complete publication list

### 3. Sequence-to-Function Tables

The core feature: tables showing how protein modifications affect function.

Columns:
- **Location**: Where the modification occurs (e.g., "Position 123")
- **Modification Type**: Phosphorylation, Glycosylation, etc.
- **Resulting Function**: Functional consequence
- **Publications**: Linked PMIDs

### 4. Small Molecule Interactions

Comprehensive drug/compound targeting information:
- Molecule name with PubChem links
- Interaction type (Inhibitor, Activator, etc.)
- Binding site and activity data (IC50, Kd)
- Effect on function
- Supporting publications

### 5. Clinical Significance & Aging

Disease associations with emphasis on age-related conditions:
- Condition name
- Genetic variant information
- Phenotype description
- Age-related flag with onset age
- Supporting publications

## Data Format

The application expects JSON data following the `ProteinArticle` type defined in `src/types/protein.ts`.

See `/docs/MARKDOWN_TEMPLATE.md` for complete data format specification.

### Example API Integration

To connect to a backend API:

1. Create `/src/lib/api.ts`:
```typescript
export async function fetchProteinData(id: string) {
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/protein/${id}`);
  if (!response.ok) throw new Error('Protein not found');
  return response.json();
}
```

2. Update `/src/app/protein/[id]/page.tsx`:
```typescript
// Replace mock data with:
const proteinData = await fetchProteinData(params.id);
```

## Styling System

### CSS Variables

All colors are defined as CSS variables in `globals.css`:
- `--background`: Main background
- `--foreground`: Text color
- `--accent-primary`: Burgundy red for headers/buttons
- `--border-color`: Border color
- `--table-*`: Table-specific colors

### Component Styling

Components use Tailwind utility classes with CSS variable references:
```tsx
className="bg-[var(--accent-primary)] text-white"
```

## Responsive Design

- Desktop-first design with responsive breakpoints
- Tables scroll horizontally on small screens
- Sidebar collapses on mobile (future enhancement)

## Future Enhancements

### Immediate Next Steps
1. ✅ **3D Protein Visualization**: Mol* viewer fully integrated!
2. **Search Functionality**: Global search across proteins
3. **API Integration**: Connect to backend Neo4j database
4. **Server-Side Rendering**: Fetch data at build time for static generation

### Advanced Features
1. **Interactive Sequence Viewer**: Click on amino acid positions
2. **Pathway Visualization**: Interactive pathway diagrams
3. **Comparison Tool**: Compare multiple proteins side-by-side
4. **Export Functionality**: Download data as PDF/CSV
5. **User Annotations**: Allow community contributions

## Backend Integration

The backend should provide a REST or GraphQL API with endpoints:

```
GET /api/protein/:id          # Get full protein article
GET /api/proteins             # List all proteins
GET /api/search?q=...         # Search proteins
```

Example Neo4j Cypher queries are provided in `/docs/MARKDOWN_TEMPLATE.md`.

## Contributing

When adding new components or features:
1. Follow the existing component structure
2. Use TypeScript for all new code
3. Maintain the WikiCrow dark theme aesthetic
4. Add proper type definitions
5. Include publication citations where applicable

## License

See main project LICENSE file.

## Acknowledgments

- Design inspired by [WikiCrow](https://wikicrow.ai)
- Built for HackAging 2025 Sequence-to-Function Challenge
- Data sources: UniProt, GenAge, PubChem, PubMed
