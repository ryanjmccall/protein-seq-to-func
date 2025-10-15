'use client';

import { useEffect, useRef, useState } from 'react';
import { renderReact18 } from 'molstar/lib/mol-plugin-ui/react18';

interface ProteinViewerProps {
  pdbId: string;
  description?: string;
}

export default function ProteinViewer({ pdbId, description }: ProteinViewerProps) {
  const viewerRef = useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const viewerInstanceRef = useRef<{ dispose: () => void } | null>(null);

  useEffect(() => {
    if (!viewerRef.current || !pdbId) return;

    let mounted = true;

    const initViewer = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Dynamic import of Mol* core components to avoid SSR issues and mp4-export
        const { createPluginUI } = await import('molstar/lib/mol-plugin-ui');
        const { DefaultPluginUISpec } = await import('molstar/lib/mol-plugin-ui/spec');
        const { PluginCommands } = await import('molstar/lib/mol-plugin/commands');

        // Import Mol* CSS
        await import('molstar/build/viewer/molstar.css');

        if (!mounted || !viewerRef.current) return;

        // Clear previous viewer if exists
        if (viewerInstanceRef.current) {
          viewerInstanceRef.current.dispose();
        }

        // Create plugin spec without extensions that require Node.js modules
        const spec = {
          ...DefaultPluginUISpec(),
          layout: {
            initial: {
              isExpanded: false,
              showControls: false,
              controlsDisplay: 'reactive' as const,
            },
          },
          components: {
            remoteState: 'none' as const,
          },
        };

        // Create the plugin
        const plugin = await createPluginUI({
          target: viewerRef.current,
          render: renderReact18,
          spec,
        });

        viewerInstanceRef.current = plugin;

        // Load structure from PDB
        const data = await plugin.builders.data.download(
          { url: `https://files.rcsb.org/download/${pdbId}.cif` },
          { state: { isGhost: false } }
        );

        const trajectory = await plugin.builders.structure.parseTrajectory(data, 'mmcif');
        await plugin.builders.structure.hierarchy.applyPreset(trajectory, 'default');

        // Center camera on structure
        PluginCommands.Camera.Reset(plugin, {});

        setIsLoading(false);
      } catch (err) {
        console.error('Error loading protein structure:', err);
        if (mounted) {
          setError('Failed to load protein structure');
          setIsLoading(false);
        }
      }
    };

    initViewer();

    return () => {
      mounted = false;
      if (viewerInstanceRef.current) {
        viewerInstanceRef.current.dispose();
        viewerInstanceRef.current = null;
      }
    };
  }, [pdbId]);

  return (
    <div className="border border-[var(--border-color)] rounded-lg overflow-hidden">
      <div className="bg-[var(--background-card)]">
        <div className="relative">
          {/* Viewer container */}
          <div
            ref={viewerRef}
            className="w-full aspect-square bg-[var(--background)]"
            style={{ minHeight: '300px' }}
          />

          {/* Loading overlay */}
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-[var(--background)] bg-opacity-90">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--accent-primary)] mx-auto mb-3"></div>
                <p className="text-[var(--foreground-muted)] text-sm">
                  Loading structure...
                </p>
              </div>
            </div>
          )}

          {/* Error overlay */}
          {error && (
            <div className="absolute inset-0 flex items-center justify-center bg-[var(--background)] bg-opacity-90">
              <div className="text-center px-4">
                <p className="text-[var(--error)] mb-2">⚠️ {error}</p>
                <p className="text-[var(--foreground-muted)] text-xs">
                  PDB ID: {pdbId}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Description */}
        {description && (
          <div className="p-3 border-t border-[var(--border-color)]">
            <p className="text-xs text-[var(--foreground-muted)] text-center">
              {description}
            </p>
          </div>
        )}

        {/* PDB link */}
        <div className="p-2 border-t border-[var(--border-color)] bg-[var(--background)] text-center">
          <a
            href={`https://www.rcsb.org/structure/${pdbId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-[var(--info)] hover:text-[var(--accent-primary-hover)] font-mono"
          >
            View on RCSB PDB: {pdbId}
          </a>
        </div>
      </div>
    </div>
  );
}
