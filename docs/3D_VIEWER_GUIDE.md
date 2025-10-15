# 3D Protein Structure Viewer Guide

The application now includes a fully functional 3D protein structure viewer using **Mol*** (Molstar), the same technology used by the RCSB Protein Data Bank.

## Features

### Interactive 3D Visualization
- **Rotate**: Click and drag
- **Zoom**: Scroll wheel or pinch
- **Pan**: Right-click and drag (or Ctrl+drag)
- **Auto-focus**: Automatically centers on the structure

### Display Options
- Automatic representation (cartoon, surface, etc.)
- High-quality rendering with anti-aliasing
- Responsive design that fits the sidebar

### Data Loading
- Loads structures directly from RCSB PDB
- Uses mmCIF format for accuracy
- Includes loading state and error handling
- Link to full PDB entry

## How It Works

### Component: ProteinViewer

Location: `/src/components/viewer/ProteinViewer.tsx`

```tsx
<ProteinViewer
  pdbId="5DKX"
  description="Crystal structure of glucosidase II alpha subunit"
/>
```

### Props

- **pdbId** (required): PDB identifier (e.g., "5DKX")
- **description** (optional): Text description shown below the viewer

### Implementation Details

1. **Dynamic Import**: Mol* is loaded client-side to avoid SSR issues
2. **Clean Up**: Properly disposes of viewer when component unmounts
3. **Error Handling**: Shows friendly error message if structure fails to load
4. **Loading State**: Displays spinner while fetching structure

### Data Source

Structures are loaded from:
```
https://files.rcsb.org/download/{pdbId}.cif
```

The mmCIF format is preferred over PDB format for:
- More complete data
- Better handling of large structures
- Modern standard

## Integration in Your Data

### Adding PDB IDs to Your Protein Data

In your protein JSON or database:

```json
{
  "protein": {
    "uniprot_id": "Q14697",
    "name": "GANAB",
    "structure_pdb_id": "5DKX",
    ...
  }
}
```

### Finding PDB Structures

1. **From UniProt**:
   - Visit protein page on UniProt
   - Look for "3D Structure" section
   - Lists all available PDB entries

2. **From RCSB PDB**:
   - Search by protein name or gene symbol
   - Search by UniProt ID
   - Example: https://www.rcsb.org/search?request={...}

3. **From AlphaFold** (predicted structures):
   - Visit https://alphafold.ebi.ac.uk/
   - Search by UniProt ID
   - Note: These use AF-{uniprot_id} format

### Supporting AlphaFold Structures

To add support for AlphaFold predicted structures, modify `ProteinViewer.tsx`:

```typescript
// Determine if it's an AlphaFold structure
const isAlphaFold = pdbId.startsWith('AF-');

// Use appropriate URL
const url = isAlphaFold
  ? `https://alphafold.ebi.ac.uk/files/${pdbId}-model_v4.cif`
  : `https://files.rcsb.org/download/${pdbId}.cif`;
```

## Customization Options

### Appearance

Modify the viewer configuration in `ProteinViewer.tsx`:

```typescript
const spec = DefaultPluginUISpec();

// Hide/show controls
spec.config.set(PluginConfig.Viewport.ShowExpand, false);
spec.config.set(PluginConfig.Viewport.ShowControls, true);  // Show controls
spec.config.set(PluginConfig.Viewport.ShowSettings, true);  // Show settings

// Background color
spec.layout = {
  initial: {
    showControls: true,
    controlsDisplay: 'reactive',
  },
};
```

### Representation Style

Change how the protein is displayed:

```typescript
// In applyPreset call:
representationPreset: 'auto'  // Default
// Options: 'auto', 'empty', 'illustrative', 'atomic-detail', 'polymer-cartoon', etc.
```

### Color Schemes

Add custom coloring:

```typescript
await plugin.builders.structure.representation.addRepresentation(trajectory, {
  type: 'cartoon',
  color: 'sequence-id',  // Color by sequence position
  // Options: 'atom-id', 'chain-id', 'element-symbol', 'molecule-type', etc.
});
```

## Performance Considerations

### Large Structures

For very large structures (>10,000 atoms):

1. **Reduce quality**:
```typescript
render: {
  preferWebGl1: false,
  multiSample: { mode: 'off' },  // Disable anti-aliasing
},
```

2. **Use simplified representations**:
```typescript
representationPreset: 'polymer-cartoon'  // Instead of 'auto'
```

3. **Lazy loading**: Only load when user clicks/scrolls to viewer

### Mobile Optimization

The current implementation works on mobile, but for better performance:

```typescript
// Detect mobile
const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

render: {
  multiSample: { mode: isMobile ? 'off' : 'on' },
},
```

## Troubleshooting

### Common Issues

**Structure doesn't load:**
- Check that PDB ID is correct
- Verify structure exists: https://www.rcsb.org/structure/{pdbId}
- Check browser console for errors

**Viewer is blank:**
- Ensure Mol* CSS is imported correctly
- Check that viewport has minimum height
- Verify WebGL is supported in browser

**Performance is slow:**
- Reduce rendering quality (see above)
- Check structure size (very large structures may be slow)
- Ensure hardware acceleration is enabled in browser

### Browser Compatibility

Mol* requires:
- WebGL 2.0 support (or WebGL 1.0 as fallback)
- Modern JavaScript (ES6+)
- Supported browsers: Chrome, Firefox, Safari, Edge (latest versions)

## Advanced Features

### Highlighting Specific Residues

To highlight mutation sites or binding regions:

```typescript
// After structure loads
const selection = Script.getStructureSelection(
  Q => Q.struct.generator.atomGroups({
    'residue-test': Q.core.rel.eq([Q.struct.atomProperty.macromolecular.label_seq_id(), 123]),
  }),
  structure
);

await plugin.managers.structure.selection.fromSelectionQuery('add', selection);
```

### Loading Local Structures

For custom or unpublished structures:

```typescript
// Instead of download from URL
const data = await plugin.builders.data.rawData({
  data: cifFileContent,  // String content of CIF file
});
```

### Multiple Structures

To show multiple structures or compare:

1. Load second structure into different model
2. Use assembly builder to arrange
3. Color by source

## Resources

- **Mol* Documentation**: https://molstar.org/
- **Mol* GitHub**: https://github.com/molstar/molstar
- **PDB Format Docs**: https://www.wwpdb.org/documentation/file-format
- **RCSB PDB**: https://www.rcsb.org/
- **AlphaFold Database**: https://alphafold.ebi.ac.uk/

## Example Usage

### Basic Usage (Current Implementation)

```tsx
import ProteinViewer from '@/components/viewer/ProteinViewer';

<ProteinViewer
  pdbId="5DKX"
  description="Crystal structure of glucosidase II alpha subunit"
/>
```

### With Conditional Rendering

```tsx
{protein.structure_pdb_id ? (
  <ProteinViewer
    pdbId={protein.structure_pdb_id}
    description={`Structure of ${protein.name}`}
  />
) : (
  <div>No structure available</div>
)}
```

### With Error Boundary

```tsx
<ErrorBoundary fallback={<div>Failed to load structure</div>}>
  <ProteinViewer pdbId="5DKX" />
</ErrorBoundary>
```

## Future Enhancements

Potential additions:

1. **Sequence-Structure Mapping**: Click on amino acid in sequence to highlight in 3D
2. **Mutation Visualization**: Show disease-associated mutations in structure
3. **Binding Site Highlighting**: Highlight small molecule binding sites
4. **Download Options**: Export images or structure files
5. **Multiple Views**: Show different representations side-by-side
6. **Animation**: Morph between conformations or show dynamics

## Summary

The 3D viewer integration provides:
- ✅ Professional, interactive 3D visualization
- ✅ Direct loading from RCSB PDB
- ✅ Automatic structure rendering
- ✅ Error handling and loading states
- ✅ Mobile-friendly design
- ✅ Easy to customize and extend

The viewer enhances the protein explorer by allowing users to visualize the actual molecular structure, making the sequence-to-function relationships more tangible and understandable.
